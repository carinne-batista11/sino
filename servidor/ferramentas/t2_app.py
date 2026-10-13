"""
Cópia isolada do aplicativo para o AMBIENTE T2 (ERS v7.0, E4): o Sino de uma
revisão publicada, numa pasta própria, com banco próprio, falando com o
Worker sino-servico-codigos-t2. A instalação principal não é tocada.

    python t2_app.py preparar --destino DESTINO --revisao SHA
    python t2_app.py abrir    --destino DESTINO --segredos PASTA [--python PYTHON]
    python t2_app.py remover  --destino DESTINO [--confirmar]

preparar  confere a revisão (SHA completo de 40 caracteres, commit já
          publicado em origin/main, sem links simbólicos nem submódulos, com
          o cliente com token, src/t2.ts e wrangler.t2.jsonc), cria DESTINO
          (caminho absoluto fora do repositório e de qualquer repositório Git;
          novo ou vazio; 700), grava a marca .sino_t2_copia como "incompleta",
          extrai a revisão em DESTINO/app com `git archive`, confere que
          db.py, banco e backups da cópia apontam para dentro dela e só então
          marca "concluida". Não abre o aplicativo. Se falhar no meio, a marca
          fica "incompleta" e `remover --confirmar` limpa a cópia.
abrir     ação explícita: confere a cópia (marca "concluida", ligada à pasta
          por dispositivo e inode), a configuração do T2 (PASTA/app_t2.json de
          uma preparação concluída por t2_segredos.py: URL HTTPS do Worker T2,
          chave pública do KID t2-1 e token) e o interpretador (Flet, httpx e
          cryptography disponíveis com -E -s, sem executar o app). Abre o app
          da cópia com `python -E -s` e um ambiente FECHADO: só as variáveis
          do sistema necessárias (VARIAVEIS_DO_SISTEMA) e SINO_SERVICO_URL,
          SINO_SERVICO_CHAVES e SINO_SERVICO_TOKEN (nunca na linha de comando).
          Enquanto o app roda, a cópia fica travada (.em_uso). Saída do app em
          DESTINO/app.log (600).
remover   recusa se a cópia estiver em uso (trava, ou processo com a pasta
          como diretório de trabalho ou nos argumentos) ou se houver arquivos
          temporários do SQLite; sem --confirmar, só mostra as contagens. Com
          --confirmar, apaga o conteúdo ancorado nos descritores das pastas
          (sem seguir links simbólicos, sem atravessar pontos de montagem e
          parando se uma pasta for trocada durante a remoção). A pasta
          DESTINO só é removida se tiver sido criada pela ferramenta.

Nada sensível aparece no terminal: nem o token, nem a chave pública inteira,
nem e-mails; só caminhos, a revisão e contagens. Limite: a marca e as travas
evitam acidentes; não protegem contra outro processo do mesmo usuário.
"""

import argparse
import ast
import contextlib
import fcntl
import json
import os
import re
import secrets
import stat
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t2_segredos as t2s  # noqa: E402
from t2_segredos import Falha  # noqa: E402

MARCA = ".sino_t2_copia"
TIPO_MARCA = "sino-t2-copia"
INCOMPLETA, CONCLUIDA = "incompleta", "concluida"
TRAVA = ".em_uso"
REGISTRO_DO_APP = "app.log"
REF_PUBLICADA = "refs/remotes/origin/main"
RE_SHA = re.compile(r"[0-9a-f]{40}")
RE_ID = re.compile(r"[0-9a-f]{32}")
ARQUIVOS_EXIGIDOS = ("backend/main.py", "backend/servico_codigos.py", "database/db.py",
                     "servidor/src/t2.ts", "servidor/wrangler.t2.jsonc")
SUFIXOS_SQLITE = ("-journal", "-wal", "-shm")
MODULOS_NECESSARIOS = ("flet", "httpx", "cryptography")
VERSAO_MINIMA_PYTHON = (3, 10)

# Ambiente FECHADO do processo da cópia (I1): só o necessário para o app
# gráfico no Ubuntu, com o motivo de cada variável. Credenciais (Cloudflare,
# Resend, nuvem, SSH), variáveis do Python (PYTHON*) e do carregador (LD_*)
# nunca passam.
VARIAVEIS_DO_SISTEMA = {
    "PATH": "localizar programas auxiliares (cliente gráfico da Flet, programas de som do aviso)",
    "HOME": "a Flet guarda o cliente gráfico em ~/.flet; o GTK lê as configurações do usuário",
    "LANG": "idioma e codificação de texto",
    "LANGUAGE": "ordem de idiomas das mensagens do sistema",
    "TZ": "fuso horário usado nas datas de vencimento, quando definido",
    "TMPDIR": "pasta de arquivos temporários",
    "DISPLAY": "sessões X11: em qual tela abrir a janela",
    "XAUTHORITY": "sessões X11: autorização para abrir a janela",
    "WAYLAND_DISPLAY": "sessões Wayland: em qual compositor abrir a janela",
    "XDG_RUNTIME_DIR": "sockets do Wayland, do D-Bus e do áudio da sessão",
    "XDG_SESSION_TYPE": "o GTK escolhe entre X11 e Wayland",
    "XDG_CURRENT_DESKTOP": "integração do GTK com o ambiente gráfico (tema, portais)",
    "XDG_DATA_DIRS": "temas, ícones e fontes do sistema",
    "DBUS_SESSION_BUS_ADDRESS": "barramento da sessão (acessibilidade, portais)",
}
PREFIXOS_DO_SISTEMA = ("LC_",)   # formatos regionais (datas, números)
VARIAVEIS_DO_T2 = ("SINO_SERVICO_URL", "SINO_SERVICO_CHAVES", "SINO_SERVICO_TOKEN")

CONFERENCIA = """
import json, os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "database"))
import db
print(json.dumps({"db": os.path.realpath(db.__file__), "banco": os.path.realpath(db.NOME_DO_BANCO),
                  "backups": os.path.realpath(db.PASTA_BACKUPS)}))
"""

VERIFICACAO_DO_PYTHON = """
import importlib.util, json, sys
print(json.dumps({"faltam": [m for m in %r if importlib.util.find_spec(m) is None],
                  "versao": list(sys.version_info[:2]),
                  "E": sys.flags.ignore_environment, "s": sys.flags.no_user_site}))
""" % (MODULOS_NECESSARIOS,)

# Só para os testes: chamado antes de entrar em cada subpasta durante a remoção.
_antes_de_entrar = None


# ======================================================================
#  Revisão
# ======================================================================

def _cliente_tem_token(fonte):
    """O cliente da revisão lê SINO_SERVICO_TOKEN na configuração e envia Authorization."""
    try:
        arvore = ast.parse(fonte)
    except (SyntaxError, ValueError):
        return False
    funcoes = {no.name: no for no in arvore.body if isinstance(no, ast.FunctionDef)}
    configuracao = funcoes.get("configuracao_do_ambiente")
    if "ler_token_de_acesso" not in funcoes or configuracao is None:
        return False
    def constantes(no):
        return {n.value for n in ast.walk(no) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    return "SINO_SERVICO_TOKEN" in constantes(configuracao) and "Authorization" in constantes(arvore)


def validar_revisao(revisao, raiz=t2s.RAIZ_REPOSITORIO):
    """
    SHA completo de um commit existente, já publicado (ancestral da referência
    LOCAL refs/remotes/origin/main, sem acesso à rede), sem links simbólicos
    nem submódulos, com os arquivos do T2 e o cliente com token.
    """
    if not isinstance(revisao, str) or not RE_SHA.fullmatch(revisao):
        raise Falha("informe a revisão pelo SHA completo (40 caracteres hexadecimais minúsculos)")
    if t2s.git(raiz, "cat-file", "-e", f"{revisao}^{{commit}}").returncode != 0:
        raise Falha("revisão inexistente neste repositório")
    if t2s.git(raiz, "merge-base", "--is-ancestor", revisao, REF_PUBLICADA).returncode != 0:
        raise Falha("revisão não autorizada: ainda não publicada em origin/main")
    arvore = t2s.git(raiz, "ls-tree", "-r", "-z", "--full-tree", revisao)
    if arvore.returncode != 0:
        raise Falha("não foi possível ler a árvore da revisão")
    caminhos = set()
    for entrada in arvore.stdout.split(b"\0"):
        if not entrada:
            continue
        modo, _, resto = entrada.partition(b" ")
        if modo in (b"120000", b"160000"):
            raise Falha("a revisão tem links simbólicos ou submódulos; não extraio")
        caminhos.add(resto.partition(b"\t")[2].decode("utf-8", "replace"))
    faltam = [c for c in ARQUIVOS_EXIGIDOS if c not in caminhos]
    if faltam:
        raise Falha(f"a revisão não tem os arquivos do T2: {', '.join(faltam)}")
    cliente = t2s.git(raiz, "cat-file", "-p", f"{revisao}:backend/servico_codigos.py")
    if cliente.returncode != 0 or not _cliente_tem_token(cliente.stdout):
        raise Falha("revisão sem o suporte ao token do T2 no cliente do aplicativo")
    entrada_t2 = t2s.git(raiz, "cat-file", "-p", f"{revisao}:servidor/src/t2.ts")
    if entrada_t2.returncode != 0 or b"comToken" not in entrada_t2.stdout or b"TOKEN_ACESSO" not in entrada_t2.stdout:
        raise Falha("revisão sem a entrada do T2 com token (servidor/src/t2.ts)")
    return revisao


# ======================================================================
#  Cópia
# ======================================================================

def ambiente_da_copia(variaveis, base=None):
    """Ambiente fechado: só VARIAVEIS_DO_SISTEMA, LC_* e as variáveis do T2 informadas."""
    base = os.environ if base is None else base
    ambiente = {k: v for k, v in base.items()
                if k in VARIAVEIS_DO_SISTEMA or any(k.startswith(p) for p in PREFIXOS_DO_SISTEMA)}
    desconhecidas = set(variaveis) - set(VARIAVEIS_DO_T2)
    if desconhecidas:
        raise Falha("variável inesperada para o aplicativo")
    ambiente.update(variaveis)
    return ambiente


def conferir_caminhos(app):
    """db.py, banco e backups resolvidos pela própria cópia precisam ficar dentro dela."""
    r = subprocess.run([sys.executable, "-I", "-c", CONFERENCIA], cwd=os.path.join(app, "backend"),
                       env=ambiente_da_copia({}), capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise Falha("não foi possível conferir os caminhos do banco da cópia")
    caminhos = json.loads(r.stdout)
    raiz_app = os.path.realpath(app)
    for chave in ("db", "banco", "backups"):
        if not t2s.dentro(caminhos[chave], raiz_app) or caminhos[chave] == raiz_app:
            raise Falha(f"caminho fora da cópia ({chave})")
    return caminhos


def _texto_marca(marca):
    return json.dumps(marca, indent=2, sort_keys=True) + "\n"


def preparar(destino, revisao, raiz=t2s.RAIZ_REPOSITORIO, saida=None, _extrair=None):
    saida = sys.stdout if saida is None else saida
    commit = validar_revisao(revisao, raiz)
    real, fd, criada = t2s.criar_pasta_privada(destino, raiz)
    try:
        info = os.fstat(fd)
        marca = {"tipo": TIPO_MARCA, "estado": INCOMPLETA, "commit": commit, "id": secrets.token_hex(16),
                 "dev": info.st_dev, "ino": info.st_ino, "pasta_criada": criada}
        t2s.criar_privado(fd, MARCA, _texto_marca(marca))
        os.fsync(fd)
        try:
            os.mkdir("app", 0o700, dir_fd=fd)
            app = os.path.join(real, "app")
            (_extrair or _extrair_revisao)(raiz, commit, app)
            caminhos = conferir_caminhos(app)
            if os.path.lexists(caminhos["banco"]) or os.path.lexists(caminhos["backups"]):
                raise Falha("a cópia não deveria trazer banco nem backups")
            t2s.substituir_privado(fd, MARCA, _texto_marca({**marca, "estado": CONCLUIDA}))
        except BaseException:
            print(f"t2-app: a preparação ficou incompleta em {real}; "
                  "use `remover --destino ... --confirmar` para limpar", file=saida)
            raise
    finally:
        os.close(fd)
    print(f"t2-app: cópia da revisão {commit[:12]} em {app}", file=saida)
    print(f"t2-app: banco próprio (criado vazio ao abrir): {caminhos['banco']}", file=saida)
    print("t2-app: o aplicativo não foi aberto (use o comando abrir)", file=saida)
    return real


def _extrair_revisao(raiz, commit, app):
    pacote = t2s.git(raiz, "archive", "--format=tar", commit)
    if pacote.returncode != 0:
        raise Falha("git archive falhou")
    extracao = subprocess.run(["tar", "-x", "--no-same-owner", "--no-same-permissions", "-C", app],
                              input=pacote.stdout, capture_output=True)
    if extracao.returncode != 0:
        raise Falha("a extração da revisão falhou")


def _ler_marca(fd):
    try:
        marca = json.loads(t2s.ler_privado(MARCA, dir_fd=fd))
    except ValueError:
        raise Falha("marca da cópia ilegível") from None
    tipos = {"tipo": str, "estado": str, "commit": str, "id": str, "dev": int, "ino": int, "pasta_criada": bool}
    if not isinstance(marca, dict) or set(marca) != set(tipos) or \
            any(type(marca[k]) is not t for k, t in tipos.items()) or marca["tipo"] != TIPO_MARCA or \
            marca["estado"] not in (INCOMPLETA, CONCLUIDA) or not RE_SHA.fullmatch(marca["commit"]) or \
            not RE_ID.fullmatch(marca["id"]):
        raise Falha("a pasta não é uma cópia do T2 preparada por esta ferramenta")
    return marca


def conferir_copia(destino, raiz=t2s.RAIZ_REPOSITORIO, exigir_concluida=True):
    """
    Pasta 700 do usuário com a marca da ferramenta, ligada a ESTA pasta por
    dispositivo e inode. Devolve (pasta, descritor, app, marca); quem chama
    fecha o descritor.
    """
    real = t2s.conferir_destino(destino, raiz)
    fd = t2s.abrir_pasta(real)
    try:
        info = os.fstat(fd)
        marca = _ler_marca(fd)
        if (info.st_dev, info.st_ino) != (marca["dev"], marca["ino"]):
            raise Falha("a marca não pertence a esta pasta (foi copiada de outra); nada foi feito")
        if exigir_concluida:
            if marca["estado"] != CONCLUIDA:
                raise Falha("a preparação da cópia não foi concluída (use remover --confirmar)")
            app = os.stat("app", dir_fd=fd, follow_symlinks=False)
            if not stat.S_ISDIR(app.st_mode):
                raise Falha("a cópia está incompleta")
    except BaseException:
        os.close(fd)
        raise
    return real, fd, os.path.join(real, "app"), marca


# ======================================================================
#  Abertura (ação explícita)
# ======================================================================

def ler_configuracao(pasta_segredos, raiz=t2s.RAIZ_REPOSITORIO):
    """Variáveis do app a partir de app_t2.json de uma preparação concluída; nunca mostradas."""
    real = t2s.conferir_destino(pasta_segredos, raiz)
    fd = t2s.abrir_pasta(real)
    try:
        estado, _ = t2s.ler_estado(fd)
        if estado != t2s.CONCLUIDO:
            raise Falha("a preparação dos segredos não foi concluída")
        dados = t2s.ler_json_privado(t2s.ARQUIVO_APP, t2s.CAMPOS_APP, dir_fd=fd)
    finally:
        os.close(fd)
    url = t2s.validar_url(dados["url"])
    t2s.validar_chaves_publicas(dados["chaves"])
    token = t2s.validar_token(dados["token"])
    return {"SINO_SERVICO_URL": url, "SINO_SERVICO_CHAVES": dados["chaves"], "SINO_SERVICO_TOKEN": token}


def validar_interpretador(python, executar=subprocess.run):
    """O Python escolhido aceita -E -s e tem as dependências do app (sem importá-las nem abrir o app)."""
    if not isinstance(python, str) or not os.path.isabs(python) or not os.access(python, os.X_OK):
        raise Falha("interpretador Python inválido (informe um caminho absoluto executável)")
    r = executar([python, "-E", "-s", "-c", VERIFICACAO_DO_PYTHON], env=ambiente_da_copia({}),
                 capture_output=True, text=True, stdin=subprocess.DEVNULL)
    try:
        dados = json.loads(r.stdout) if r.returncode == 0 else None
    except ValueError:
        dados = None
    if not isinstance(dados, dict):
        raise Falha("o interpretador Python não respondeu à conferência")
    if dados.get("faltam"):
        raise Falha(f"faltam dependências no interpretador: {', '.join(dados['faltam'])}")
    if tuple(dados.get("versao", ())) < VERSAO_MINIMA_PYTHON or dados.get("E") != 1 or dados.get("s") != 1:
        raise Falha("interpretador Python incompatível (versão ou opções -E -s)")
    return python


def _travar(fd):
    """Trava exclusiva da cópia (.em_uso), ancorada na pasta; devolve o descritor ou None se já em uso."""
    trava = os.open(TRAVA, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=fd)
    try:
        fcntl.flock(trava, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(trava)
        return None
    return trava


def abrir(destino, pasta_segredos, raiz=t2s.RAIZ_REPOSITORIO, popen=subprocess.Popen, python=None,
          executar=subprocess.run, saida=None):
    saida = sys.stdout if saida is None else saida
    python = python or sys.executable
    real, fd, app, marca = conferir_copia(destino, raiz)
    trava = log = None
    try:
        conferir_caminhos(app)
        variaveis = ler_configuracao(pasta_segredos, raiz)
        validar_interpretador(python, executar)
        trava = _travar(fd)
        if trava is None:
            raise Falha("a cópia já está em uso")
        log = os.open(REGISTRO_DO_APP, os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                      0o600, dir_fd=fd)
        print(f"t2-app: abrindo a cópia da revisão {marca['commit'][:12]} (feche a janela para encerrar)", file=saida)
        processo = popen([python, "-E", "-s", os.path.join(app, "backend", "main.py")], cwd=app,
                         env=ambiente_da_copia(variaveis), stdin=subprocess.DEVNULL, stdout=log,
                         stderr=subprocess.STDOUT, start_new_session=True)
        codigo = processo.wait()
    finally:
        for descritor in (log, trava, fd):
            if descritor is not None:
                os.close(descritor)
    print(f"t2-app: aplicativo encerrado (código {codigo})", file=saida)
    return codigo


# ======================================================================
#  Remoção controlada
# ======================================================================

def processos_da_copia(real, proc="/proc"):
    """PIDs com diretório de trabalho ou argumento dentro da cópia (Linux, /proc)."""
    if not os.path.isdir(proc):
        raise Falha("não foi possível verificar os processos em execução; nada foi apagado")
    ativos = []
    for nome in os.listdir(proc):
        if not nome.isdigit() or int(nome) == os.getpid():
            continue
        with contextlib.suppress(OSError):
            if t2s.dentro(os.readlink(os.path.join(proc, nome, "cwd")), real):
                ativos.append(int(nome))
                continue
        with contextlib.suppress(OSError):
            with open(os.path.join(proc, nome, "cmdline"), "rb") as arquivo:
                argumentos = arquivo.read().split(b"\0")
            if any(t2s.dentro(a.decode("utf-8", "replace"), real) for a in argumentos if a.startswith(b"/")):
                ativos.append(int(nome))
    return ativos


def _sqlite_temporarios(app_fd):
    with contextlib.suppress(FileNotFoundError, NotADirectoryError):
        banco = os.open("database", t2s.FLAGS_PASTA, dir_fd=app_fd)
        try:
            return [n for n in os.listdir(banco) if n.endswith(SUFIXOS_SQLITE)]
        finally:
            os.close(banco)
    return []


def _contar(fd):
    arquivos = pastas = 0
    for entrada in os.scandir(fd):
        if entrada.is_dir(follow_symlinks=False):
            pastas += 1
            sub = os.open(entrada.name, t2s.FLAGS_PASTA, dir_fd=fd)
            try:
                a, p = _contar(sub)
            finally:
                os.close(sub)
            arquivos, pastas = arquivos + a, pastas + p
        else:
            arquivos += 1
    return arquivos, pastas


def _apagar_conteudo(fd, dispositivo, pular=()):
    """Apaga o conteúdo da pasta aberta em `fd`, por nome relativo ao descritor, sem seguir links."""
    with os.scandir(fd) as entradas:
        nomes = [e.name for e in entradas if e.name not in pular]
    for nome in nomes:
        info = os.stat(nome, dir_fd=fd, follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode):
            os.unlink(nome, dir_fd=fd)          # arquivo ou link: nunca o alvo
            continue
        if info.st_dev != dispositivo:
            raise Falha("ponto de montagem dentro da cópia; parei sem atravessá-lo")
        if _antes_de_entrar is not None:
            _antes_de_entrar(fd, nome)
        try:
            sub = os.open(nome, t2s.FLAGS_PASTA, dir_fd=fd)   # O_NOFOLLOW: um link aqui falha
        except OSError:
            raise Falha("uma pasta da cópia foi trocada durante a remoção; parei") from None
        try:
            if (os.fstat(sub).st_dev, os.fstat(sub).st_ino) != (info.st_dev, info.st_ino):
                raise Falha("uma pasta da cópia foi trocada durante a remoção; parei")
            _apagar_conteudo(sub, dispositivo)
        finally:
            os.close(sub)
        os.rmdir(nome, dir_fd=fd)


def remover(destino, confirmar=False, raiz=t2s.RAIZ_REPOSITORIO, saida=None, processos=processos_da_copia):
    saida = sys.stdout if saida is None else saida
    real, fd, _, marca = conferir_copia(destino, raiz, exigir_concluida=False)
    trava = None
    try:
        trava = _travar(fd)
        if trava is None or processos(real):
            raise Falha("a cópia está em uso (feche o aplicativo); nada foi apagado")
        temporarios = []
        with contextlib.suppress(FileNotFoundError, NotADirectoryError):
            app_fd = os.open("app", t2s.FLAGS_PASTA, dir_fd=fd)
            try:
                temporarios = _sqlite_temporarios(app_fd)
            finally:
                os.close(app_fd)
        if temporarios:
            raise Falha("há arquivos temporários do banco da cópia (possível uso em andamento); nada foi apagado")
        arquivos, pastas = _contar(fd)
        if not confirmar:
            print(f"t2-app: seriam apagados {arquivos} arquivo(s) e {pastas} pasta(s) da cópia "
                  f"{marca['commit'][:12]} ({marca['estado']}) em {real}; repita com --confirmar", file=saida)
            return False
        # Tudo, menos a trava e a marca; a marca por último, para uma nova tentativa reconhecer a pasta.
        _apagar_conteudo(fd, os.fstat(fd).st_dev, pular=(TRAVA, MARCA))
        os.unlink(TRAVA, dir_fd=fd)
        os.unlink(MARCA, dir_fd=fd)
        os.fsync(fd)
    finally:
        if trava is not None:
            os.close(trava)
        os.close(fd)
    if marca["pasta_criada"]:
        os.rmdir(real)
    print(f"t2-app: cópia {marca['commit'][:12]} removida ({arquivos} arquivo(s), {pastas} pasta(s))"
          + ("" if marca["pasta_criada"] else "; a pasta existia antes e foi mantida, vazia"), file=saida)
    return True


def main(argv=None):
    analisador = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    comandos = analisador.add_subparsers(dest="comando", required=True)
    p = comandos.add_parser("preparar")
    p.add_argument("--destino", required=True)
    p.add_argument("--revisao", required=True)
    a = comandos.add_parser("abrir")
    a.add_argument("--destino", required=True)
    a.add_argument("--segredos", required=True)
    a.add_argument("--python", help="interpretador com Flet, httpx e cryptography (padrão: o que roda esta ferramenta)")
    r = comandos.add_parser("remover")
    r.add_argument("--destino", required=True)
    r.add_argument("--confirmar", action="store_true")
    args = analisador.parse_args(argv)
    try:
        if args.comando == "preparar":
            preparar(args.destino, args.revisao)
        elif args.comando == "abrir":
            return abrir(args.destino, args.segredos, python=args.python)
        else:
            remover(args.destino, args.confirmar)
    except (Falha, OSError) as erro:
        detalhe = erro if isinstance(erro, Falha) else type(erro).__name__
        raise SystemExit(f"t2-app: {detalhe}") from None
    return 0


if __name__ == "__main__":
    sys.exit(main())
