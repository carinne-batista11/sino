"""
Segredos do AMBIENTE T2 do serviço de códigos (ERS v7.0, E4): Worker
sino-servico-codigos-t2 (wrangler.t2.jsonc, entrada src/t2.ts), primeiro envio
real pela Resend. Só biblioteca padrão e o `cryptography` do .venv do projeto.

    python t2_segredos.py preparar     --pasta PASTA --url URL
    python t2_segredos.py chave-resend --pasta PASTA
    python t2_segredos.py descartar    --pasta PASTA

preparar      cria PASTA (caminho absoluto, fora do repositório e de qualquer
              repositório Git; nova ou vazia; permissão 700) com segredos NOVOS
              e exclusivos do T2, em arquivos 600 que nunca são sobrescritos:
                segredos.json  CHAVE_HMAC, CHAVE_ASSINATURA, DESTINATARIOS_PERMITIDOS
                               e TOKEN_ACESSO (para `wrangler deploy
                               --secrets-file`; RESEND_API_KEY entra depois);
                app_t2.json    URL, chave pública do KID t2-1 e token (só para
                               t2_app.py abrir a cópia isolada do aplicativo);
                .t2_segredos_estado  "incompleto" durante a gravação e
                               "concluido" no fim (troca atômica).
              Os e-mails autorizados são lidos sem eco (um por vez; vazio
              termina), como em destinatarios.py. Se algo falhar durante a
              gravação, os arquivos criados nesta execução são apagados (e a
              pasta, se foi criada agora). URL aceita:
              https://sino-servico-codigos-t2.<subdomínio>.workers.dev
chave-resend  só num terminal interativo (entrada redirecionada ou por pipe é
              recusada): lê a chave da API da Resend sem eco e a acrescenta a
              segredos.json por substituição atômica (600). Recusa se a chave
              já estiver lá ou se a preparação não estiver concluída.
descartar     recuperação de uma preparação INCOMPLETA (interrompida): apaga
              só os arquivos que esta ferramenta cria, e a pasta se ela tiver
              sido criada pela ferramenta. Recusa pastas concluídas ou com
              qualquer outro arquivo.

Nada sensível aparece no terminal nem nas mensagens de erro: nem chaves, nem o
token, nem os e-mails ou seus resumos; só caminhos e contagens. Depois do
deploy (só com autorização da autora), por exemplo:

    npx wrangler deploy -c wrangler.t2.jsonc --secrets-file PASTA/segredos.json

Encerramento: excluir o Worker e revogar a chave da Resend (é a revogação que
invalida a chave). Apagar os arquivos remove as entradas da pasta, mas não
garante a eliminação física dos dados em SSDs, sistemas com instantâneos ou
armazenamento com cópia na escrita.

Operações sobre a pasta usam o descritor dela (sem seguir links simbólicos),
para que trocar um caminho depois da conferência não desvie a gravação.
Limite: outro processo do mesmo usuário continua podendo ler e alterar a
pasta; as conferências evitam acidentes, não um processo malicioso.
"""

import argparse
import base64
import contextlib
import getpass
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import destinatarios  # noqa: E402

NOME_WORKER = "sino-servico-codigos-t2"
KID_T2 = "t2-1"
ARQUIVO_SEGREDOS = "segredos.json"
ARQUIVO_APP = "app_t2.json"
ARQUIVO_ESTADO = ".t2_segredos_estado"
CABECALHO_ESTADO = "sino-t2-segredos"
INCOMPLETO, CONCLUIDO = "incompleto", "concluido"
SUFIXO_TEMPORARIO = ".novo"
ARQUIVOS_DA_FERRAMENTA = (ARQUIVO_SEGREDOS, ARQUIVO_APP, ARQUIVO_ESTADO,
                          ARQUIVO_SEGREDOS + SUFIXO_TEMPORARIO, ARQUIVO_ESTADO + SUFIXO_TEMPORARIO)
CAMPOS_SEGREDOS = ("CHAVE_HMAC", "CHAVE_ASSINATURA", "DESTINATARIOS_PERMITIDOS", "TOKEN_ACESSO")
CAMPOS_APP = ("url", "chaves", "token")
RAIZ_REPOSITORIO = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
# Pastas do projeto cuja identidade (dispositivo, inode) também é conferida,
# para recusar o mesmo diretório visto por outro caminho (ex.: bind mount).
PASTAS_PROTEGIDAS = ("", "database", os.path.join("database", "backups"), "backend", "servidor")
TAMANHO_MAXIMO_PRIVADO = 1024 * 1024

RE_HEX_32 = re.compile(r"[0-9a-f]{64}")
RE_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")
# A documentação da Resend não define o formato da chave (só mostra exemplos
# "re_..."). Aqui só o necessário para o cabeçalho `Authorization: Bearer`:
# ASCII visível, sem espaços; o limite de 512 é desta ferramenta.
RE_CHAVE_RESEND = re.compile(r"[\x21-\x7e]{1,512}")

FLAGS_PASTA = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


class Falha(Exception):
    """Operação recusada; a mensagem nunca contém segredos nem e-mails."""


# ======================================================================
#  Git com ambiente controlado
# ======================================================================

def ambiente_git():
    """Sem GIT_DIR, GIT_WORK_TREE, configuração do usuário ou do sistema, nem objetos substitutos."""
    ambiente = {k: os.environ[k] for k in ("PATH", "HOME") if k in os.environ}
    ambiente.update({
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
    })
    return ambiente


def git(raiz, *args, texto=False):
    return subprocess.run(["git", "-C", raiz, *args], capture_output=True, text=texto,
                          stdin=subprocess.DEVNULL, env=ambiente_git())


# ======================================================================
#  Caminhos
# ======================================================================

def dentro(caminho, raiz):
    return caminho == raiz or caminho.startswith(raiz.rstrip(os.sep) + os.sep)


def em_repositorio_git(caminho):
    """True se `caminho` (ou o diretório existente mais próximo) está num repositório Git."""
    alvo = caminho
    while not os.path.isdir(alvo):
        alvo = os.path.dirname(alvo)
    r = git(alvo, "rev-parse", "--is-inside-work-tree", texto=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


def identidades_protegidas(raiz):
    identidades = set()
    for base in {os.path.realpath(raiz), RAIZ_REPOSITORIO}:
        for relativa in PASTAS_PROTEGIDAS:
            with contextlib.suppress(OSError):
                info = os.stat(os.path.join(base, relativa))
                identidades.add((info.st_dev, info.st_ino))
    return identidades


def conferir_destino(pasta, raiz=RAIZ_REPOSITORIO):
    """
    Caminho absoluto, sem link simbólico no último componente, fora do
    repositório (também depois de resolver links e pela identidade das pastas
    principais do projeto) e de qualquer repositório Git, que não seja a raiz
    nem a pasta pessoal, com o diretório pai existente. Devolve o caminho
    resolvido. Limite: um bind mount de uma subpasta não listada em
    PASTAS_PROTEGIDAS não é detectado.
    """
    if not isinstance(pasta, str) or not os.path.isabs(pasta):
        raise Falha("informe um caminho absoluto")
    if os.path.islink(pasta.rstrip(os.sep) or os.sep):
        raise Falha("o caminho é um link simbólico")
    real = os.path.realpath(pasta)
    if real in (os.sep, os.path.realpath(os.path.expanduser("~"))):
        raise Falha("caminho perigoso (raiz ou pasta pessoal)")
    # O repositório real do Sino é sempre recusado, mesmo quando `raiz` é outro.
    for proibida in {os.path.realpath(raiz), RAIZ_REPOSITORIO}:
        if dentro(real, proibida):
            raise Falha("o caminho não pode ficar dentro do repositório do Sino")
    identidades = identidades_protegidas(raiz)
    alvo = real
    while True:
        with contextlib.suppress(OSError):
            info = os.stat(alvo)
            if (info.st_dev, info.st_ino) in identidades:
                raise Falha("o caminho é uma pasta do repositório do Sino vista por outro caminho")
        if alvo == os.sep:
            break
        alvo = os.path.dirname(alvo)
    if not os.path.isdir(os.path.dirname(real)):
        raise Falha("o diretório pai não existe")
    if em_repositorio_git(real):
        raise Falha("o caminho fica dentro de um repositório Git; use outra pasta")
    return real


# ======================================================================
#  Arquivos privados, ancorados no descritor da pasta
# ======================================================================

def abrir_pasta(caminho, dir_fd=None):
    """Descritor de uma pasta do usuário com permissão 700, sem seguir link simbólico."""
    try:
        fd = os.open(caminho, FLAGS_PASTA, dir_fd=dir_fd)
    except FileNotFoundError:
        raise Falha("a pasta não existe") from None
    except OSError:
        raise Falha("o caminho não é uma pasta acessível (ou é um link simbólico)") from None
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        os.close(fd)
        raise Falha("a pasta precisa ser do usuário atual e ter permissão 700")
    return fd


def criar_pasta_privada(pasta, raiz=RAIZ_REPOSITORIO):
    """
    Pasta nova (ou vazia, do próprio usuário) com permissão 700. Devolve
    (caminho, descritor, criada_agora); quem chama fecha o descritor.
    """
    real = conferir_destino(pasta, raiz)
    criada = False
    if not os.path.lexists(real):
        os.mkdir(real, 0o700)
        criada = True
    try:
        fd = os.open(real, FLAGS_PASTA)
    except OSError:
        raise Falha("o caminho já existe e não é uma pasta (ou é um link simbólico)") from None
    try:
        info = os.fstat(fd)
        if info.st_uid != os.getuid():
            raise Falha("a pasta existente pertence a outro usuário")
        if os.listdir(fd):
            raise Falha("a pasta já existe e não está vazia (nada é sobrescrito)")
        os.fchmod(fd, 0o700)
    except BaseException:
        os.close(fd)
        raise
    return real, fd, criada


def criar_privado(dir_fd, nome, dados):
    """Arquivo novo 600 dentro da pasta aberta; nunca sobrescreve; gravado e sincronizado."""
    fd = os.open(nome, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=dir_fd)
    try:
        visao = memoryview(dados.encode("utf-8") if isinstance(dados, str) else dados)
        while visao:
            visao = visao[os.write(fd, visao):]
        os.fsync(fd)
    except BaseException:
        os.close(fd)
        with contextlib.suppress(OSError):
            os.unlink(nome, dir_fd=dir_fd)   # o arquivo foi criado agora, por esta função
        raise
    os.close(fd)


def gravar_privado(caminho, texto):
    """Arquivo novo 600 por caminho (pasta = diretório do caminho); nunca sobrescreve."""
    pasta = os.open(os.path.dirname(caminho) or ".", FLAGS_PASTA)
    try:
        criar_privado(pasta, os.path.basename(caminho), texto)
    finally:
        os.close(pasta)


def substituir_privado(dir_fd, nome, dados):
    """Troca atômica de um arquivo 600 da pasta, por um temporário novo; sincroniza a pasta."""
    temporario = nome + SUFIXO_TEMPORARIO
    try:
        criar_privado(dir_fd, temporario, dados)
    except FileExistsError:
        raise Falha(f"existe {temporario} de uma execução interrompida (pode conter segredos); "
                    "confira e apague-o antes de repetir") from None
    try:
        os.replace(temporario, nome, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporario, dir_fd=dir_fd)
        raise
    os.fsync(dir_fd)


def ler_privado(caminho, dir_fd=None):
    """
    Lê um arquivo regular do usuário com permissão 600: abre sem seguir link e
    confere tipo, dono e permissão no próprio descritor aberto.
    """
    nome = os.path.basename(caminho)
    try:
        fd = os.open(caminho, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=dir_fd)
    except FileNotFoundError:
        raise Falha(f"arquivo ausente: {nome}") from None
    except OSError:
        raise Falha(f"{nome} não pôde ser aberto (link simbólico ou sem acesso)") from None
    with os.fdopen(fd, "rb") as arquivo:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise Falha(f"{nome} não é um arquivo regular")
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise Falha(f"{nome} precisa ser do usuário atual e ter permissão 600")
        if info.st_size > TAMANHO_MAXIMO_PRIVADO:
            raise Falha(f"{nome} grande demais")
        dados = arquivo.read(TAMANHO_MAXIMO_PRIVADO + 1)
    try:
        return dados.decode("utf-8")
    except UnicodeDecodeError:
        raise Falha(f"{nome} ilegível") from None


def ler_json_privado(caminho, campos, dir_fd=None):
    nome = os.path.basename(caminho)
    try:
        dados = json.loads(ler_privado(caminho, dir_fd))
    except ValueError:
        raise Falha(f"{nome} ilegível") from None
    if not isinstance(dados, dict) or not set(campos) <= set(dados) or \
            not all(isinstance(v, str) for v in dados.values()):
        raise Falha(f"{nome} com conteúdo inesperado")
    return dados


def texto_do_estado(estado, criada):
    return f"{CABECALHO_ESTADO}\n{estado}\n{'criada' if criada else 'existente'}\n"


def ler_estado(dir_fd):
    """(estado, pasta_criada_pela_ferramenta) de .t2_segredos_estado."""
    linhas = ler_privado(ARQUIVO_ESTADO, dir_fd).splitlines()
    if len(linhas) != 3 or linhas[0] != CABECALHO_ESTADO or linhas[1] not in (INCOMPLETO, CONCLUIDO) \
            or linhas[2] not in ("criada", "existente"):
        raise Falha("estado da pasta ilegível")
    return linhas[1], linhas[2] == "criada"


# ======================================================================
#  Formatos (os do serviço: src/nucleo/cripto.ts, destinatarios.ts,
#  acesso_teste.ts; e do cliente: backend/servico_codigos.py)
# ======================================================================

def validar_url(url):
    """Só o endereço do Worker T2 em workers.dev, com HTTPS, sem porta nem caminho."""
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


def chave_publica_de_semente(semente):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    privada = Ed25519PrivateKey.from_private_bytes(semente)
    return privada.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


def validar_chaves_publicas(texto):
    """'t2-1:<64 hex>' com uma chave pública Ed25519 válida; devolve os bytes."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    kid, separador, hexa = (texto or "").partition(":")
    if kid != KID_T2 or not separador or not RE_HEX_32.fullmatch(hexa):
        raise Falha(f"chave pública ausente ou fora do formato ({KID_T2}:<64 hexadecimais>)")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(hexa))
    except ValueError:
        raise Falha("chave pública inválida") from None
    return bytes.fromhex(hexa)


def validar_token(token):
    if not isinstance(token, str) or not RE_TOKEN.fullmatch(token):
        raise Falha("token ausente ou fora do formato (43 caracteres base64url)")
    return token


def validar_chave_resend(chave):
    if not isinstance(chave, str) or not RE_CHAVE_RESEND.fullmatch(chave):
        raise Falha("chave da Resend vazia ou com espaços ou caracteres inválidos; nada foi gravado")
    return chave


def base64url(dados):
    """32 bytes -> 43 caracteres base64url sem preenchimento (formato do token)."""
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode("ascii")


def gerar_segredos(emails, aleatorio=secrets.token_bytes):
    """
    Segredos novos do T2 e a configuração da cópia do app, sem a URL.
    `emails`: os endereços autorizados (validados e normalizados por
    destinatarios.montar; nunca mostrados).
    """
    chave_hmac = aleatorio(32)
    semente = aleatorio(32)
    token = base64url(aleatorio(32))
    lista, repetidos = destinatarios.montar(chave_hmac, list(emails))
    segredos = {
        "CHAVE_HMAC": chave_hmac.hex(),
        "CHAVE_ASSINATURA": semente.hex(),
        "DESTINATARIOS_PERMITIDOS": lista,
        "TOKEN_ACESSO": token,
    }
    app = {"chaves": f"{KID_T2}:{chave_publica_de_semente(semente).hex()}", "token": token}
    return segredos, app, lista.count(","), repetidos


# ======================================================================
#  Comandos
# ======================================================================

def _desfazer(dir_fd, nomes):
    """Apaga só os arquivos que esta execução criou."""
    for nome in reversed(nomes):
        with contextlib.suppress(FileNotFoundError):
            os.unlink(nome, dir_fd=dir_fd)
    with contextlib.suppress(OSError):
        os.fsync(dir_fd)


def preparar(pasta, url, entrada=None, pedir=getpass.getpass, raiz=RAIZ_REPOSITORIO, saida=None,
             _criar=criar_privado):
    saida = sys.stdout if saida is None else saida
    url = validar_url(url)
    conferir_destino(pasta, raiz)
    if os.path.lexists(pasta) and os.path.isdir(pasta) and not os.path.islink(pasta) and os.listdir(pasta):
        raise Falha("a pasta já existe e não está vazia (nada é sobrescrito)")
    # Os e-mails são lidos e validados antes de criar qualquer arquivo.
    emails = destinatarios.ler_emails(entrada, pedir)
    try:
        segredos, app, total, repetidos = gerar_segredos(emails)
    except destinatarios.ListaInvalida as erro:
        raise Falha(str(erro)) from None
    finally:
        emails.clear()
    real, fd, criada = criar_pasta_privada(pasta, raiz)
    criados = []
    try:
        for nome, dados in (
            (ARQUIVO_ESTADO, texto_do_estado(INCOMPLETO, criada)),
            (ARQUIVO_SEGREDOS, json.dumps(segredos, indent=2) + "\n"),
            (ARQUIVO_APP, json.dumps({"url": url, **app}, indent=2) + "\n"),
        ):
            _criar(fd, nome, dados)
            criados.append(nome)
        os.fsync(fd)
        substituir_privado(fd, ARQUIVO_ESTADO, texto_do_estado(CONCLUIDO, criada))
    except BaseException:
        _desfazer(fd, criados + [ARQUIVO_ESTADO + SUFIXO_TEMPORARIO] if criados else criados)
        os.close(fd)
        if criada:
            with contextlib.suppress(OSError):
                os.rmdir(real)
        raise
    os.close(fd)
    print(f"t2: pasta {real} (700)", file=saida)
    print(f"t2: arquivos (600): {ARQUIVO_SEGREDOS}, {ARQUIVO_APP}", file=saida)
    print(f"t2: destinatários autorizados: {total}"
          + (f"; {repetidos} repetido(s) ignorado(s)" if repetidos else ""), file=saida)
    print("t2: falta a chave da Resend (comando chave-resend, num terminal); nada foi publicado", file=saida)
    return real


def ler_chave_do_terminal(entrada=None, pedir=getpass.getpass):
    """Só num terminal interativo: entrada redirecionada ou por pipe é recusada."""
    entrada = sys.stdin if entrada is None else entrada
    if not entrada.isatty():
        raise Falha("a chave da Resend só pode ser digitada num terminal interativo "
                    "(entrada redirecionada ou por pipe recusada); nada foi gravado")
    return pedir("Chave da API da Resend (não aparece na tela): ")


def chave_resend(pasta, ler_chave=ler_chave_do_terminal, raiz=RAIZ_REPOSITORIO, saida=None):
    saida = sys.stdout if saida is None else saida
    real = conferir_destino(pasta, raiz)
    fd = abrir_pasta(real)
    try:
        estado, _ = ler_estado(fd)
        if estado != CONCLUIDO:
            raise Falha("a preparação desta pasta não foi concluída (use descartar e prepare de novo)")
        segredos = ler_json_privado(ARQUIVO_SEGREDOS, CAMPOS_SEGREDOS, dir_fd=fd)
        if "RESEND_API_KEY" in segredos:
            raise Falha("a chave da Resend já está em segredos.json (nada é sobrescrito)")
        segredos["RESEND_API_KEY"] = validar_chave_resend(ler_chave())
        substituir_privado(fd, ARQUIVO_SEGREDOS, json.dumps(segredos, indent=2) + "\n")
    finally:
        os.close(fd)
    print(f"t2: chave da Resend acrescentada a {os.path.join(real, ARQUIVO_SEGREDOS)} (600)", file=saida)


def descartar(pasta, raiz=RAIZ_REPOSITORIO, saida=None):
    """Recuperação de uma preparação incompleta: só os arquivos da ferramenta."""
    saida = sys.stdout if saida is None else saida
    real = conferir_destino(pasta, raiz)
    fd = abrir_pasta(real)
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
    print(f"t2: preparação incompleta descartada ({len(nomes)} arquivo(s))"
          + ("" if criada else "; a pasta existia antes e foi mantida, vazia"), file=saida)


def main(argv=None):
    analisador = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    comandos = analisador.add_subparsers(dest="comando", required=True)
    p = comandos.add_parser("preparar")
    p.add_argument("--pasta", required=True)
    p.add_argument("--url", required=True)
    for nome in ("chave-resend", "descartar"):
        comandos.add_parser(nome).add_argument("--pasta", required=True)
    args = analisador.parse_args(argv)
    try:
        if args.comando == "preparar":
            preparar(args.pasta, args.url)
        elif args.comando == "chave-resend":
            chave_resend(args.pasta)   # sempre do terminal; sem alternativa na linha de comando
        else:
            descartar(args.pasta)
    except (Falha, OSError) as erro:
        detalhe = erro if isinstance(erro, Falha) else type(erro).__name__
        raise SystemExit(f"t2: {detalhe}") from None
    return 0


if __name__ == "__main__":
    sys.exit(main())
