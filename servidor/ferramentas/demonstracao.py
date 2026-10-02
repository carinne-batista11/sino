"""
Modo de DEMONSTRAÇÃO do Sino (desenvolvimento): app, serviço de códigos local
e caixa de mensagens numa pasta isolada, fora do projeto.

    .venv/bin/python servidor/ferramentas/demonstracao.py PASTA [--revisao REV] [--node-bin DIR]

O que faz, nesta ordem:
  1. confere que PASTA fica fora do projeto e que as portas 8787, 8025 e 9229
     de 127.0.0.1 estão livres;
  2. na primeira vez, extrai o código da revisão (padrão: HEAD) em PASTA/app
     com `git archive`; nas seguintes, reutiliza a cópia e os dados -- se a
     pasta for de outra revisão, para sem alterar nada;
  3. confere que db.py, banco e backups da cópia apontam para PASTA/app;
     o banco nasce vazio pelo inicializador normal do Sino na abertura do app
     (o banco real nunca é copiado);
  4. gera as chaves da demonstração (uma vez, permissão 600);
  5. sobe a caixa (com abertura das mensagens no editor) e o `wrangler dev`
     da configuração de desenvolvimento, só em 127.0.0.1;
  6. abre o app com SINO_MODO_DEMONSTRACAO=1: janela "Sino — Demonstração" e
     o aviso "Modo de demonstração — códigos recebidos neste computador".
Fechar a janela (ou Ctrl+C) encerra o serviço e a caixa -- só os processos
criados por este comando.

Limite: a conta fica com e-mail verificado no banco da demonstração, mas o
código foi lido neste computador; isso NÃO comprova acesso ao endereço.
As regras dos códigos (validade, tentativas, limites) são as normais.
"""

import argparse
import contextlib
import json
import os
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from http.server import HTTPServer

import caixa_dev as cd

PORTA_INSPETOR = 9229
PORTAS = (cd.PORTA_SERVICO, cd.PORTA_PADRAO, PORTA_INSPETOR)
PASTA_SERVIDOR = os.path.join(cd.RAIZ_DO_PROJETO, "servidor")
VARIAVEIS_DO_APP = ("SINO_SERVICO_URL", "SINO_SERVICO_CHAVES")
ESPERA_SERVICO_S = 90


class DemonstracaoIncompativel(SystemExit):
    """A pasta existente não serve para esta execução; nada foi alterado."""


def preparar_pasta(pasta):
    real = os.path.realpath(pasta)
    if real == cd.RAIZ_DO_PROJETO or real.startswith(cd.RAIZ_DO_PROJETO + os.sep):
        raise SystemExit("a pasta da demonstração não pode ficar dentro do projeto")
    os.makedirs(real, mode=0o700, exist_ok=True)
    conferir_fora_do_git(real)
    return cd.conferir_pasta(real)


def conferir_fora_do_git(pasta):
    """Mensagens, banco e chaves não podem cair num repositório Git sem estarem ignorados."""
    raiz = subprocess.run(["git", "-C", pasta, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if raiz.returncode != 0:
        return  # fora de qualquer repositório
    ignorada = subprocess.run(["git", "-C", pasta, "check-ignore", "-q", pasta], capture_output=True)
    if ignorada.returncode != 0:
        raise SystemExit(f"a pasta está dentro do repositório Git {raiz.stdout.strip()} e não está ignorada; "
                         "use outra pasta ou ignore-a (ex.: .git/info/exclude)")


def portas_ocupadas(portas=PORTAS):
    """
    Portas com algum processo escutando em 127.0.0.1. SO_REUSEADDR (como os
    próprios servidores usam) faz conexões já encerradas em TIME-WAIT não
    contarem como ocupadas; um listener ativo continua recusando o bind.
    """
    ocupadas = []
    for porta in portas:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((cd.ENDERECO, porta))
            except OSError:
                ocupadas.append(porta)
    return ocupadas


def git(*args, **kwargs):
    return subprocess.run(["git", "-C", cd.RAIZ_DO_PROJETO, *args], check=True, **kwargs)


def resolver_revisao(revisao):
    try:
        saida = git("rev-parse", "--verify", f"{revisao}^{{commit}}", capture_output=True, text=True)
    except subprocess.CalledProcessError:
        raise SystemExit(f"revisão inválida: {revisao}") from None
    return saida.stdout.strip()


def preparar_copia(raiz, commit):
    """Extrai a revisão em raiz/app na primeira vez; depois só confere a revisão."""
    app = os.path.join(raiz, "app")
    marca = os.path.join(raiz, "REVISAO")
    if os.path.exists(app) or os.path.exists(marca):
        atual = "desconhecida"
        if os.path.exists(marca):
            with open(marca, encoding="utf-8") as arquivo:
                atual = arquivo.read().strip()
        if atual != commit:
            raise DemonstracaoIncompativel(
                f"a pasta já tem uma demonstração da revisão {atual[:12]}; esta execução é da {commit[:12]}. "
                "Nada foi alterado: use a mesma revisão (--revisao) ou outra pasta.")
        return app, False
    pacote = git("archive", "--format=tar", commit, capture_output=True).stdout
    os.makedirs(app, mode=0o700)
    subprocess.run(["tar", "-x", "-C", app], input=pacote, check=True)
    with open(marca, "w", encoding="utf-8") as saida:
        saida.write(commit + "\n")
    return app, True


CONFERENCIA = """
import json, os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "database"))
import db
print(json.dumps({"db": os.path.realpath(db.__file__), "banco": os.path.realpath(db.NOME_DO_BANCO),
                  "backups": os.path.realpath(db.PASTA_BACKUPS), "versao": db.VERSAO_SCHEMA_ATUAL}))
"""


def ambiente_sem_pythonpath():
    ambiente = dict(os.environ)
    ambiente.pop("PYTHONPATH", None)
    return ambiente


def conferir_caminhos(app):
    """db.py, banco e backups resolvidos pela cópia precisam ficar dentro dela."""
    saida = subprocess.run([sys.executable, "-c", CONFERENCIA], cwd=os.path.join(app, "backend"),
                           env=ambiente_sem_pythonpath(), capture_output=True, text=True, check=True)
    caminhos = json.loads(saida.stdout)
    raiz_app = os.path.realpath(app) + os.sep
    for chave in ("db", "banco", "backups"):
        if not caminhos[chave].startswith(raiz_app):
            raise SystemExit(f"caminho fora da cópia ({chave}): {caminhos[chave]}")
    banco = caminhos["banco"]
    if os.path.exists(banco):
        conexao = sqlite3.connect(f"file:{banco}?mode=ro", uri=True)
        try:
            versao = conexao.execute("PRAGMA user_version").fetchone()[0]
        finally:
            conexao.close()
        if versao > caminhos["versao"]:
            raise DemonstracaoIncompativel(
                f"o banco da demonstração está na versão {versao}, mais nova que a do código "
                f"({caminhos['versao']}). Nada foi alterado.")
    return caminhos


def preparar_chaves(raiz):
    existentes = [n for n in ("segredos_dev.env", "app_dev.env") if os.path.exists(os.path.join(raiz, n))]
    if len(existentes) == 1:
        raise DemonstracaoIncompativel(f"só {existentes[0]} existe na pasta; não gero nem sobrescrevo chaves.")
    if not existentes:
        with open(os.devnull, "w") as nulo, contextlib.redirect_stdout(nulo):
            cd.gerar_chaves(raiz)
    return os.path.join(raiz, "segredos_dev.env"), os.path.join(raiz, "app_dev.env")


def ler_variaveis_do_app(caminho):
    """Lê app_dev.env como texto (sem executar), só com as chaves esperadas."""
    variaveis = {}
    with open(caminho, encoding="utf-8") as arquivo:
        for linha in arquivo.read().splitlines():
            if not linha:
                continue
            chave, separador, valor = linha.partition("=")
            if not separador or chave not in VARIAVEIS_DO_APP or chave in variaveis:
                raise DemonstracaoIncompativel("app_dev.env com conteúdo inesperado")
            variaveis[chave] = valor
    if set(variaveis) != set(VARIAVEIS_DO_APP):
        raise DemonstracaoIncompativel("app_dev.env incompleto")
    return variaveis


def localizar_npx(node_bin):
    candidato = os.path.join(node_bin, "npx") if node_bin else shutil.which("npx")
    if not candidato or not os.access(candidato, os.X_OK):
        raise SystemExit("npx (Node.js 24) não encontrado: informe --node-bin ou a variável SINO_NODE_BIN")
    return candidato


def iniciar_servico(npx, segredos, raiz, log):
    ambiente = dict(os.environ, WRANGLER_SEND_METRICS="false")
    ambiente["PATH"] = os.path.dirname(npx) + os.pathsep + ambiente.get("PATH", "")
    comando = [npx, "wrangler", "dev", "-c", "wrangler.dev.jsonc", "--env-file", segredos,
               "--persist-to", os.path.join(raiz, "servico_estado"), "--ip", cd.ENDERECO,
               "--inspector-ip", cd.ENDERECO, "--show-interactive-dev-session=false"]
    return subprocess.Popen(comando, cwd=PASTA_SERVIDOR, env=ambiente, stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)


def esperar_porta(porta, processo, prazo_s=ESPERA_SERVICO_S):
    limite = time.monotonic() + prazo_s
    while time.monotonic() < limite:
        if processo.poll() is not None:
            return False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex((cd.ENDERECO, porta)) == 0:
                return True
        time.sleep(0.5)
    return False


def iniciar_app(app, variaveis, log):
    ambiente = ambiente_sem_pythonpath()
    ambiente.update(variaveis)
    ambiente["SINO_MODO_DEMONSTRACAO"] = "1"
    return subprocess.Popen([sys.executable, os.path.join(app, "backend", "main.py")], cwd=app, env=ambiente,
                            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                            start_new_session=True)


def encerrar_processo(processo, prazo_s=15):
    """Encerra o grupo de processos criado por este comando (start_new_session), e só ele."""
    if processo is None or processo.poll() is not None:
        return
    for sinal in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(processo.pid, sinal)
        except ProcessLookupError:
            return
        try:
            processo.wait(prazo_s)
            return
        except subprocess.TimeoutExpired:
            continue


def demonstrar(pasta, revisao="HEAD", node_bin=None):
    raiz = preparar_pasta(pasta)
    ocupadas = portas_ocupadas()
    if ocupadas:
        raise SystemExit(f"portas ocupadas em {cd.ENDERECO}: {', '.join(map(str, ocupadas))}; nada foi iniciado")
    commit = resolver_revisao(revisao)
    try:
        git("diff", "--quiet", commit, "--", "backend", "database")
    except subprocess.CalledProcessError:
        print("demonstração: aviso -- há alterações em backend/ ou database/ fora da revisão usada; elas não entram")
    npx = localizar_npx(node_bin or os.environ.get("SINO_NODE_BIN"))
    app, nova = preparar_copia(raiz, commit)
    caminhos = conferir_caminhos(app)
    segredos, app_env = preparar_chaves(raiz)
    variaveis = ler_variaveis_do_app(app_env)
    caixa = cd.preparar_caixa(raiz)
    logs = os.path.join(raiz, "logs")
    os.makedirs(logs, mode=0o700, exist_ok=True)

    print(f"demonstração: pasta {raiz} ({'nova' if nova else 'reutilizada'}), revisão {commit[:12]}")
    print(f"demonstração: banco {caminhos['banco']}"
          f"{'' if os.path.exists(caminhos['banco']) else ' (será criado vazio ao abrir o app)'}")
    print(f"demonstração: mensagens em {caixa}; logs em {logs}")

    servidor_caixa = HTTPServer((cd.ENDERECO, cd.PORTA_PADRAO), cd.criar_receptor(caixa, cd.abrir_mensagem))
    threading.Thread(target=servidor_caixa.serve_forever, daemon=True).start()
    servico = app_processo = None
    try:
        with open(os.path.join(logs, "servico.log"), "ab") as log_servico, \
             open(os.path.join(logs, "app.log"), "ab") as log_app:
            servico = iniciar_servico(npx, segredos, raiz, log_servico)
            if not esperar_porta(cd.PORTA_SERVICO, servico):
                raise SystemExit("o serviço local não ficou pronto; veja logs/servico.log")
            print("demonstração: serviço e caixa prontos em 127.0.0.1; abrindo o app (feche a janela para encerrar)")
            app_processo = iniciar_app(app, variaveis, log_app)
            app_processo.wait()
    except KeyboardInterrupt:
        print("\ndemonstração: interrompida")
    finally:
        encerrar_processo(app_processo)
        encerrar_processo(servico)
        servidor_caixa.shutdown()
        servidor_caixa.server_close()
        restantes = portas_ocupadas()
        print("demonstração: encerrada" + (f"; portas ainda ocupadas: {restantes}" if restantes else "; portas livres"))
    return 0


def saida_por_linha(fluxo=None):
    """Cada mensagem do comando sai na hora, também quando a saída vai para um arquivo."""
    fluxo = sys.stdout if fluxo is None else fluxo
    fluxo.reconfigure(line_buffering=True)


def main(argv=None):
    saida_por_linha()
    analisador = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    analisador.add_argument("pasta")
    analisador.add_argument("--revisao", default="HEAD")
    analisador.add_argument("--node-bin", help="pasta com o npx do Node.js 24 (ou SINO_NODE_BIN)")
    args = analisador.parse_args(argv)
    return demonstrar(args.pasta, args.revisao, args.node_bin)


if __name__ == "__main__":
    sys.exit(main())
