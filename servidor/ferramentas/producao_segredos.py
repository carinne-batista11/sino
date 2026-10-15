"""
Segredos da PRODUÇÃO RESTRITA do serviço de códigos (ERS v7.0, E4/M8; decisão
5 de 15/10/2026): Worker sino-servico-codigos (wrangler.jsonc, entrada
src/index.ts). Só biblioteca padrão e o `cryptography` do .venv do projeto.

    python producao_segredos.py preparar     --pasta PASTA --url URL
    python producao_segredos.py chave-resend --pasta PASTA
    python producao_segredos.py conferir     --pasta PASTA
    python producao_segredos.py descartar    --pasta PASTA

preparar      cria PASTA (caminho absoluto, fora do repositório e de qualquer
              repositório Git; nova ou vazia; permissão 700) com segredos NOVOS,
              exclusivos da produção (nunca os do desenvolvimento, do T1 ou do
              T2), em arquivos 600 que nunca são sobrescritos:
                segredos.json     CHAVE_HMAC, CHAVE_ASSINATURA e
                                  DESTINATARIOS_PERMITIDOS (para `wrangler
                                  deploy --secrets-file`; RESEND_API_KEY entra
                                  depois, pelo comando chave-resend);
                recuperacao.json  cópia de recuperação da CHAVE_HMAC e da
                                  semente Ed25519 (CHAVE_ASSINATURA), com o KID
                                  e a chave pública, para o gerenciador de
                                  senhas da autora;
                app_producao.json só valores públicos: URL e chave pública do
                                  KID prod-1 (para a versão do aplicativo);
                .producao_segredos_estado  "incompleto" durante a gravação e
                                  "concluido" no fim (troca atômica).
              O KID é conferido contra servidor/wrangler.jsonc. Os e-mails
              autorizados são lidos sem eco (um por vez; vazio termina), como
              em destinatarios.py. Se algo falhar durante a gravação, os
              arquivos criados nesta execução são apagados (e a pasta, se foi
              criada agora). URL aceita:
              https://sino-servico-codigos.<subdomínio>.workers.dev
chave-resend  só num terminal interativo (entrada redirecionada ou por pipe é
              recusada): lê a chave da API da Resend de PRODUÇÃO sem eco e a
              acrescenta a segredos.json por substituição atômica (600).
              Recusa se a chave já estiver lá ou se a preparação não estiver
              concluída.
conferir      confere a pasta sem mostrar nenhum valor: formatos; lista de
              destinatários gerada com a mesma CHAVE_HMAC; cópia de
              recuperação igual aos segredos; chave pública derivada da semente
              e aceita pelo cliente do aplicativo; uma autorização FICTÍCIA,
              no formato do Worker, assinada com a semente e verificada pelo
              código do aplicativo; KID igual ao de wrangler.jsonc; presença da
              chave da Resend. Mostra só "ok", contagens e o que falta.
descartar     recuperação de uma preparação INCOMPLETA (interrompida): apaga
              só os arquivos que esta ferramenta cria, e a pasta se ela tiver
              sido criada pela ferramenta. Recusa pastas concluídas ou com
              qualquer outro arquivo.

Nada sensível aparece no terminal nem nas mensagens de erro: nem chaves, nem a
semente, nem os e-mails ou seus resumos; só caminhos e contagens. Deploy (só
com autorização da autora), na pasta servidor/:

    npx wrangler deploy --secrets-file PASTA/segredos.json

Depois do deploy conferido e da cópia de recuperação guardada pela autora, os
arquivos da pasta são apagados um a um (o encerramento é manual). Apagar os
arquivos remove as entradas da pasta, mas não garante a eliminação física dos
dados em SSDs, sistemas com instantâneos ou armazenamento com cópia na escrita.

As operações de pasta e de arquivo privado são as de t2_segredos.py (descritor
da pasta, sem seguir links simbólicos, 700/600, nunca sobrescrever). Limite:
outro processo do mesmo usuário continua podendo ler e alterar a pasta; as
conferências evitam acidentes, não um processo malicioso.
"""

import argparse
import contextlib
import getpass
import hmac
import json
import os
import re
import secrets
import stat
import sys
import time
import urllib.parse

_FERRAMENTAS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _FERRAMENTAS)
import destinatarios  # noqa: E402
import t2_segredos as base  # noqa: E402
from t2_segredos import Falha  # noqa: E402

NOME_WORKER = "sino-servico-codigos"
KID_PRODUCAO = "prod-1"
ARQUIVO_SEGREDOS = "segredos.json"
ARQUIVO_RECUPERACAO = "recuperacao.json"
ARQUIVO_APP = "app_producao.json"
ARQUIVO_ESTADO = ".producao_segredos_estado"
CABECALHO_ESTADO = "sino-producao-segredos"
INCOMPLETO, CONCLUIDO = base.INCOMPLETO, base.CONCLUIDO
SUFIXO_TEMPORARIO = base.SUFIXO_TEMPORARIO
ARQUIVOS_DA_FERRAMENTA = (ARQUIVO_SEGREDOS, ARQUIVO_RECUPERACAO, ARQUIVO_APP, ARQUIVO_ESTADO,
                          ARQUIVO_SEGREDOS + SUFIXO_TEMPORARIO, ARQUIVO_ESTADO + SUFIXO_TEMPORARIO)
CAMPOS_SEGREDOS = ("CHAVE_HMAC", "CHAVE_ASSINATURA", "DESTINATARIOS_PERMITIDOS")
CAMPOS_RECUPERACAO = ("ambiente", "kid", "CHAVE_HMAC", "CHAVE_ASSINATURA", "chave_publica")
CAMPOS_APP = ("url", "chaves")
RAIZ_REPOSITORIO = base.RAIZ_REPOSITORIO
CONFIGURACAO_PRODUCAO = os.path.join(RAIZ_REPOSITORIO, "servidor", "wrangler.jsonc")
PASTA_BACKEND = os.path.join(RAIZ_REPOSITORIO, "backend")

RE_HEX_32 = base.RE_HEX_32
RE_VERIFICACAO = re.compile(r"v1:[0-9a-f]{64}")


# ======================================================================
#  Formatos e conferências (sem mostrar valores)
# ======================================================================

def validar_url(url):
    """Só o endereço do Worker de produção em workers.dev, com HTTPS, sem porta nem caminho."""
    if not isinstance(url, str):
        raise Falha("URL ausente")
    partes = urllib.parse.urlsplit(url)
    if partes.path not in ("", "/") or partes.query or partes.fragment or partes.username or partes.password:
        raise Falha("URL com caminho, consulta ou credenciais")
    host = partes.hostname or ""
    prefixo, sufixo = f"{NOME_WORKER}.", ".workers.dev"
    sub = host[len(prefixo):-len(sufixo)] if host.startswith(prefixo) and host.endswith(sufixo) else ""
    if partes.scheme != "https" or partes.port is not None or not sub or "." in sub:
        raise Falha(f"URL precisa ser https://{NOME_WORKER}.<subdomínio>.workers.dev")
    return f"https://{host}"


def kid_da_configuracao(caminho=CONFIGURACAO_PRODUCAO):
    """KID_ASSINATURA de wrangler.jsonc (só comentários em linha própria); precisa ser o da produção."""
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            linhas = [l for l in arquivo.read().splitlines() if not l.strip().startswith("//")]
        configuracao = json.loads("\n".join(linhas))
        kid = configuracao["vars"]["KID_ASSINATURA"]
    except (OSError, ValueError, KeyError, TypeError):
        raise Falha("não foi possível ler KID_ASSINATURA de wrangler.jsonc") from None
    if kid != KID_PRODUCAO:
        raise Falha(f"KID_ASSINATURA de wrangler.jsonc não é {KID_PRODUCAO}; nada foi feito")
    return kid


def _modulos_do_app():
    """Cliente do aplicativo (backend/): o mesmo código que vai conferir as autorizações."""
    if PASTA_BACKEND not in sys.path:
        sys.path.insert(0, PASTA_BACKEND)
    import autorizacao_servico
    import servico_codigos
    return autorizacao_servico, servico_codigos


def resumos_da_lista(lista, chave_hmac):
    """Resumos da lista se ela foi gerada com esta CHAVE_HMAC e está no formato; senão Falha."""
    if not isinstance(lista, str):
        raise Falha("lista de destinatários ausente")
    verificacao, *resumos = lista.split(",")
    # Formato antes da comparação (compare_digest só aceita texto ASCII).
    if not RE_VERIFICACAO.fullmatch(verificacao) \
            or not hmac.compare_digest(verificacao, destinatarios.verificacao(chave_hmac)):
        raise Falha("a lista de destinatários não foi gerada com a CHAVE_HMAC desta pasta")
    if not 1 <= len(resumos) <= destinatarios.LIMITE or len(set(resumos)) != len(resumos) \
            or not all(RE_HEX_32.fullmatch(r) for r in resumos):
        raise Falha("lista de destinatários fora do formato")
    return resumos


def _hex_32(texto, nome):
    if not isinstance(texto, str) or not RE_HEX_32.fullmatch(texto):
        raise Falha(f"{nome} ausente ou fora do formato (64 hexadecimais minúsculos)")
    return bytes.fromhex(texto)


def autorizacao_ficticia(semente, kid, aleatorio=secrets.token_bytes, agora=None):
    """
    Autorização no formato do Worker (src/nucleo/autorizacao.ts), com jti e
    contexto aleatórios e sem relação com nenhum pedido real.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    agora = int(time.time()) if agora is None else agora
    conteudo = {"v": 1, "kid": kid, "jti": base.base64url(aleatorio(16)), "fin": "cadastro",
                "ctx": aleatorio(32).hex(), "iat": agora, "exp": agora + 600}
    payload = base.base64url(json.dumps(conteudo, separators=(",", ":")).encode("utf-8"))
    assinatura = Ed25519PrivateKey.from_private_bytes(semente).sign(b"sino-autorizacao-v1." + payload.encode("ascii"))
    return f"{payload}.{base.base64url(assinatura)}"


# ======================================================================
#  Estado da pasta
# ======================================================================

def texto_do_estado(estado, criada):
    return f"{CABECALHO_ESTADO}\n{estado}\n{'criada' if criada else 'existente'}\n"


def ler_estado(dir_fd):
    """(estado, pasta_criada_pela_ferramenta) de .producao_segredos_estado."""
    linhas = base.ler_privado(ARQUIVO_ESTADO, dir_fd).splitlines()
    if len(linhas) != 3 or linhas[0] != CABECALHO_ESTADO or linhas[1] not in (INCOMPLETO, CONCLUIDO) \
            or linhas[2] not in ("criada", "existente"):
        raise Falha("estado da pasta ilegível")
    return linhas[1], linhas[2] == "criada"


def abrir_concluida(pasta, raiz):
    real = base.conferir_destino(pasta, raiz)
    fd = base.abrir_pasta(real)
    try:
        estado, _ = ler_estado(fd)
        if estado != CONCLUIDO:
            raise Falha("a preparação desta pasta não foi concluída (use descartar e prepare de novo)")
    except BaseException:
        os.close(fd)
        raise
    return real, fd


# ======================================================================
#  Geração
# ======================================================================

def gerar_segredos(emails, aleatorio=secrets.token_bytes):
    """
    (segredos, recuperação, app sem a URL, total de destinatários, repetidos).
    `emails`: os endereços autorizados (validados e normalizados por
    destinatarios.montar; nunca mostrados).
    """
    chave_hmac = aleatorio(32)
    semente = aleatorio(32)
    lista, repetidos = destinatarios.montar(chave_hmac, list(emails))
    publica = base.chave_publica_de_semente(semente).hex()
    segredos = {
        "CHAVE_HMAC": chave_hmac.hex(),
        "CHAVE_ASSINATURA": semente.hex(),
        "DESTINATARIOS_PERMITIDOS": lista,
    }
    recuperacao = {
        "ambiente": f"produção restrita ({NOME_WORKER})",
        "kid": KID_PRODUCAO,
        "CHAVE_HMAC": segredos["CHAVE_HMAC"],
        "CHAVE_ASSINATURA": segredos["CHAVE_ASSINATURA"],
        "chave_publica": publica,
    }
    app = {"chaves": f"{KID_PRODUCAO}:{publica}"}
    return segredos, recuperacao, app, lista.count(","), repetidos


# ======================================================================
#  Comandos
# ======================================================================

def preparar(pasta, url, entrada=None, pedir=getpass.getpass, raiz=RAIZ_REPOSITORIO, saida=None,
             _criar=base.criar_privado, configuracao=CONFIGURACAO_PRODUCAO):
    saida = sys.stdout if saida is None else saida
    url = validar_url(url)
    kid_da_configuracao(configuracao)
    base.conferir_destino(pasta, raiz)
    if os.path.lexists(pasta) and os.path.isdir(pasta) and not os.path.islink(pasta) and os.listdir(pasta):
        raise Falha("a pasta já existe e não está vazia (nada é sobrescrito)")
    # Os e-mails são lidos e validados antes de criar qualquer arquivo.
    emails = destinatarios.ler_emails(entrada, pedir)
    try:
        segredos, recuperacao, app, total, repetidos = gerar_segredos(emails)
    except destinatarios.ListaInvalida as erro:
        raise Falha(str(erro)) from None
    finally:
        emails.clear()
    real, fd, criada = base.criar_pasta_privada(pasta, raiz)
    criados = []
    try:
        for nome, dados in (
            (ARQUIVO_ESTADO, texto_do_estado(INCOMPLETO, criada)),
            (ARQUIVO_SEGREDOS, json.dumps(segredos, indent=2) + "\n"),
            (ARQUIVO_RECUPERACAO, json.dumps(recuperacao, indent=2, ensure_ascii=False) + "\n"),
            (ARQUIVO_APP, json.dumps({"url": url, **app}, indent=2) + "\n"),
        ):
            _criar(fd, nome, dados)
            criados.append(nome)
        os.fsync(fd)
        base.substituir_privado(fd, ARQUIVO_ESTADO, texto_do_estado(CONCLUIDO, criada))
    except BaseException:
        base._desfazer(fd, criados + [ARQUIVO_ESTADO + SUFIXO_TEMPORARIO] if criados else criados)
        os.close(fd)
        if criada:
            with contextlib.suppress(OSError):
                os.rmdir(real)
        raise
    os.close(fd)
    print(f"producao: pasta {real} (700)", file=saida)
    print(f"producao: arquivos (600): {ARQUIVO_SEGREDOS}, {ARQUIVO_RECUPERACAO}, {ARQUIVO_APP}", file=saida)
    print(f"producao: destinatários autorizados: {total}"
          + (f"; {repetidos} repetido(s) ignorado(s)" if repetidos else ""), file=saida)
    print(f"producao: guarde a cópia de {ARQUIVO_RECUPERACAO} no gerenciador de senhas", file=saida)
    print("producao: falta a chave da Resend (comando chave-resend, num terminal); nada foi publicado", file=saida)
    return real


def chave_resend(pasta, ler_chave=base.ler_chave_do_terminal, raiz=RAIZ_REPOSITORIO, saida=None):
    saida = sys.stdout if saida is None else saida
    real, fd = abrir_concluida(pasta, raiz)
    try:
        segredos = base.ler_json_privado(ARQUIVO_SEGREDOS, CAMPOS_SEGREDOS, dir_fd=fd)
        if "RESEND_API_KEY" in segredos:
            raise Falha("a chave da Resend já está em segredos.json (nada é sobrescrito)")
        segredos["RESEND_API_KEY"] = base.validar_chave_resend(ler_chave())
        base.substituir_privado(fd, ARQUIVO_SEGREDOS, json.dumps(segredos, indent=2) + "\n")
    finally:
        os.close(fd)
    print(f"producao: chave da Resend acrescentada a {os.path.join(real, ARQUIVO_SEGREDOS)} (600)", file=saida)


def conferir(pasta, raiz=RAIZ_REPOSITORIO, saida=None, configuracao=CONFIGURACAO_PRODUCAO):
    """
    Confere a pasta sem mostrar valores. Devolve True se está pronta para o
    deploy (inclusive com a chave da Resend); Falha em qualquer divergência.
    """
    saida = sys.stdout if saida is None else saida
    autorizacao, cliente = _modulos_do_app()
    real, fd = abrir_concluida(pasta, raiz)
    try:
        segredos = base.ler_json_privado(ARQUIVO_SEGREDOS, CAMPOS_SEGREDOS, dir_fd=fd)
        recuperacao = base.ler_json_privado(ARQUIVO_RECUPERACAO, CAMPOS_RECUPERACAO, dir_fd=fd)
        app = base.ler_json_privado(ARQUIVO_APP, CAMPOS_APP, dir_fd=fd)
    finally:
        os.close(fd)
    if set(segredos) - {*CAMPOS_SEGREDOS, "RESEND_API_KEY"}:
        raise Falha(f"{ARQUIVO_SEGREDOS} com campos inesperados")

    chave_hmac = _hex_32(segredos["CHAVE_HMAC"], "CHAVE_HMAC")
    semente = _hex_32(segredos["CHAVE_ASSINATURA"], "CHAVE_ASSINATURA")
    total = len(resumos_da_lista(segredos["DESTINATARIOS_PERMITIDOS"], chave_hmac))
    print(f"producao: segredos no formato; lista com {total} destinatário(s), da mesma CHAVE_HMAC", file=saida)

    publica = base.chave_publica_de_semente(semente).hex()
    _hex_32(recuperacao["CHAVE_HMAC"], f"CHAVE_HMAC de {ARQUIVO_RECUPERACAO}")
    _hex_32(recuperacao["CHAVE_ASSINATURA"], f"CHAVE_ASSINATURA de {ARQUIVO_RECUPERACAO}")
    if recuperacao["kid"] != KID_PRODUCAO \
            or not hmac.compare_digest(recuperacao["CHAVE_HMAC"], segredos["CHAVE_HMAC"]) \
            or not hmac.compare_digest(recuperacao["CHAVE_ASSINATURA"], segredos["CHAVE_ASSINATURA"]) \
            or recuperacao["chave_publica"] != publica:
        raise Falha(f"{ARQUIVO_RECUPERACAO} não corresponde a {ARQUIVO_SEGREDOS}")
    print(f"producao: cópia de recuperação igual aos segredos (KID {KID_PRODUCAO})", file=saida)

    validar_url(app["url"])
    if app["chaves"] != f"{KID_PRODUCAO}:{publica}":
        raise Falha(f"a chave pública de {ARQUIVO_APP} não corresponde à CHAVE_ASSINATURA")
    try:
        chaves = cliente.ler_chaves_publicas(app["chaves"])
        conteudo = autorizacao.verificar_assinatura(autorizacao_ficticia(semente, KID_PRODUCAO), chaves)
    except (ValueError, autorizacao.AutorizacaoInvalidaError):
        raise Falha("o aplicativo não aceitaria a assinatura desta CHAVE_ASSINATURA") from None
    if conteudo.kid != KID_PRODUCAO:
        raise Falha("KID inesperado na autorização de conferência")
    print("producao: autorização fictícia assinada com a semente e aceita pelo cliente do aplicativo", file=saida)

    kid_da_configuracao(configuracao)
    print(f"producao: KID de wrangler.jsonc = {KID_PRODUCAO}", file=saida)

    if "RESEND_API_KEY" not in segredos:
        print("producao: falta a chave da Resend (comando chave-resend); ainda NÃO está pronta para o deploy",
              file=saida)
        return False
    base.validar_chave_resend(segredos["RESEND_API_KEY"])
    print(f"producao: chave da Resend presente; pasta {real} pronta para o deploy (nada foi publicado)",
          file=saida)
    return True


def descartar(pasta, raiz=RAIZ_REPOSITORIO, saida=None):
    """Recuperação de uma preparação incompleta: só os arquivos da ferramenta."""
    saida = sys.stdout if saida is None else saida
    real = base.conferir_destino(pasta, raiz)
    fd = base.abrir_pasta(real)
    try:
        estado, criada = ler_estado(fd)
        if estado != INCOMPLETO:
            raise Falha("a preparação está concluída; não descarto (o encerramento é manual)")
        nomes = os.listdir(fd)
        if any(n not in ARQUIVOS_DA_FERRAMENTA for n in nomes):
            raise Falha("a pasta tem arquivos que não foram criados por esta ferramenta; nada foi apagado")
        for nome in nomes:
            info = os.stat(nome, dir_fd=fd, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise Falha("arquivo inesperado na pasta; nada mais foi apagado")
        for nome in sorted(nomes, key=lambda n: n == ARQUIVO_ESTADO):   # o estado por último
            os.unlink(nome, dir_fd=fd)
        os.fsync(fd)
    finally:
        os.close(fd)
    if criada:
        os.rmdir(real)
    print(f"producao: preparação incompleta descartada ({len(nomes)} arquivo(s))"
          + ("" if criada else "; a pasta existia antes e foi mantida, vazia"), file=saida)


def main(argv=None):
    analisador = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    comandos = analisador.add_subparsers(dest="comando", required=True)
    p = comandos.add_parser("preparar")
    p.add_argument("--pasta", required=True)
    p.add_argument("--url", required=True)
    for nome in ("chave-resend", "conferir", "descartar"):
        comandos.add_parser(nome).add_argument("--pasta", required=True)
    args = analisador.parse_args(argv)
    try:
        if args.comando == "preparar":
            preparar(args.pasta, args.url)
        elif args.comando == "chave-resend":
            chave_resend(args.pasta)   # sempre do terminal; sem alternativa na linha de comando
        elif args.comando == "conferir":
            return 0 if conferir(args.pasta) else 1
        else:
            descartar(args.pasta)
    except (Falha, OSError) as erro:
        detalhe = erro if isinstance(erro, Falha) else type(erro).__name__
        raise SystemExit(f"producao: {detalhe}") from None
    return 0


if __name__ == "__main__":
    sys.exit(main())
