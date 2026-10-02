"""
Caixa de mensagens de DESENVOLVIMENTO do serviço de códigos (Etapa 8).

Só para a validação manual com o serviço local (wrangler.dev.jsonc); nunca
faz parte do serviço publicado nem do aplicativo.

    python caixa_dev.py chaves  PASTA   # gera os segredos da rodada (uma vez)
    python caixa_dev.py receber PASTA   # recebe as mensagens em PASTA/caixa_dev
    python caixa_dev.py receber PASTA --abrir   # e abre cada mensagem nova no editor padrão

`chaves` grava, com permissão 600 e sem sobrescrever:
  PASTA/segredos_dev.env  CHAVE_HMAC e CHAVE_ASSINATURA (para `wrangler dev --env-file`);
  PASTA/app_dev.env       SINO_SERVICO_URL e SINO_SERVICO_CHAVES (só a chave pública, para o app).
Usa o `cryptography` do .venv do projeto.

`receber` escuta somente em 127.0.0.1 e grava cada mensagem em um arquivo
600 dentro de PASTA/caixa_dev (700). Só responde 2xx depois de gravar; em
qualquer falha não grava e responde erro, que o serviço trata como falha de
envio. Repetição com a mesma chave e o mesmo conteúdo não grava de novo;
mesma chave com outro conteúdo é recusada. O terminal mostra só o número da
mensagem: nunca código, e-mail, assunto ou corpo.

Com `--abrir`, cada mensagem NOVA é aberta com `xdg-open` depois de gravada
(e de respondida ao serviço). Se a abertura falhar, a mensagem continua
gravada (a entrega não falhou) e o terminal mostra só o caminho do arquivo,
cujo nome não contém o código, para abri-lo manualmente.

O modo de demonstração (serviço + caixa + app numa pasta isolada) fica em
demonstracao.py, que reutiliza este módulo.
"""

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

ENDERECO = "127.0.0.1"
PORTA_PADRAO = 8025
PORTA_SERVICO = 8787
KID_DEV = "dev-1"
TAMANHO_MAXIMO = 64 * 1024
CAMPOS = ("para", "assunto", "texto", "chave")
RAIZ_DO_PROJETO = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ABRIDOR = ("xdg-open",)
ESPERA_ABRIDOR_S = 5


class MensagemInvalida(Exception):
    """Corpo que não é uma mensagem do serviço."""


class ChaveReutilizada(Exception):
    """Mesma chave de idempotência com outro conteúdo."""


def conferir_pasta(pasta):
    """A pasta da rodada existe e fica fora do projeto (mensagens e segredos fora do Git)."""
    real = os.path.realpath(pasta)
    if not os.path.isdir(real):
        raise SystemExit(f"pasta inexistente: {real}")
    if real == RAIZ_DO_PROJETO or real.startswith(RAIZ_DO_PROJETO + os.sep):
        raise SystemExit("a pasta da rodada não pode ficar dentro do projeto")
    return real


def ler_mensagem(corpo):
    try:
        dados = json.loads(corpo)
    except (UnicodeDecodeError, ValueError) as erro:
        raise MensagemInvalida("JSON inválido") from erro
    if not isinstance(dados, dict) or set(dados) != set(CAMPOS):
        raise MensagemInvalida("campos inesperados")
    if not all(isinstance(dados[c], str) and dados[c] for c in CAMPOS):
        raise MensagemInvalida("campos vazios ou não textuais")
    return dados


def gravar_mensagem(caixa, dados):
    """Grava a mensagem e devolve o número dela (o da original, se for repetição)."""
    marca = hashlib.sha256(dados["chave"].encode()).hexdigest()[:16]
    conteudo = f"Para: {dados['para']}\nAssunto: {dados['assunto']}\n\n{dados['texto']}"
    existentes = sorted(n for n in os.listdir(caixa) if n.endswith(".txt"))
    for nome in existentes:
        if nome.split("_", 2)[1] == marca:
            with open(os.path.join(caixa, nome), encoding="utf-8") as arquivo:
                anterior = arquivo.read().split("\n", 1)[1]  # sem a linha "Recebida em"
            if anterior != conteudo:
                raise ChaveReutilizada()
            return int(nome.split("_", 1)[0])
    numero = len(existentes) + 1
    caminho = os.path.join(caixa, f"{numero:04d}_{marca}_{datetime.now():%H%M%S}.txt")
    descritor = os.open(caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            arquivo.write(f"Recebida em: {datetime.now():%Y-%m-%d %H:%M:%S}\n{conteudo}")
            arquivo.flush()
            os.fsync(arquivo.fileno())
    except BaseException:
        os.unlink(caminho)
        raise
    return numero


def caminho_da_mensagem(caixa, numero):
    return next(os.path.join(caixa, n) for n in sorted(os.listdir(caixa)) if n.startswith(f"{numero:04d}_"))


def avisar_abertura_manual(numero, caminho):
    print(f"caixa: não foi possível abrir a mensagem {numero} automaticamente; abra manualmente: {caminho}",
          flush=True)


def abrir_mensagem(numero, caminho, popen=subprocess.Popen, espera_s=ESPERA_ABRIDOR_S):
    """Abre a mensagem no editor padrão sem bloquear; uma falha só gera o aviso com o caminho."""
    try:
        processo = popen([*ABRIDOR, caminho], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        avisar_abertura_manual(numero, caminho)
        return None

    def conferir():
        try:
            if processo.wait(espera_s) != 0:
                avisar_abertura_manual(numero, caminho)
        except subprocess.TimeoutExpired:
            pass  # o abridor segue com o editor aberto: considerado aberto

    tarefa = threading.Thread(target=conferir, daemon=True)
    tarefa.start()
    return tarefa


def criar_receptor(caixa, abrir=None):
    """`abrir(numero, caminho)` é chamado só para mensagens novas, depois da resposta ao serviço."""
    class Receptor(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/mensagens":
                return self.responder(404)
            try:
                tamanho = int(self.headers.get("Content-Length") or "")
            except ValueError:
                return self.responder(411)
            if not 0 < tamanho <= TAMANHO_MAXIMO:
                return self.responder(413)
            try:
                antes = sum(1 for n in os.listdir(caixa) if n.endswith(".txt"))
                numero = gravar_mensagem(caixa, ler_mensagem(self.rfile.read(tamanho)))
            except MensagemInvalida:
                print("caixa: mensagem recusada (formato)", flush=True)
                return self.responder(400)
            except ChaveReutilizada:
                print("caixa: mensagem recusada (chave já usada com outro conteúdo)", flush=True)
                return self.responder(409)
            except Exception as erro:  # noqa: BLE001 -- qualquer falha ao gravar = não entregue
                print(f"caixa: falha ao gravar ({type(erro).__name__})", flush=True)
                return self.responder(500)
            print(f"caixa: mensagem {numero} gravada", flush=True)
            self.responder(200)
            if abrir is not None and numero > antes:
                try:
                    abrir(numero, caminho_da_mensagem(caixa, numero))
                except Exception as erro:  # noqa: BLE001 -- abrir é conveniência; a entrega já ocorreu
                    print(f"caixa: falha ao abrir a mensagem {numero} ({type(erro).__name__})", flush=True)

        def do_GET(self):
            self.responder(405)

        def responder(self, status):
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):  # sem registro de requisições
            pass

    return Receptor


def preparar_caixa(pasta):
    caixa = os.path.join(conferir_pasta(pasta), "caixa_dev")
    os.makedirs(caixa, mode=0o700, exist_ok=True)
    os.chmod(caixa, 0o700)
    return caixa


def receber(pasta, porta, abrir=False):
    caixa = preparar_caixa(pasta)
    servidor = HTTPServer((ENDERECO, porta), criar_receptor(caixa, abrir_mensagem if abrir else None))
    print(f"caixa: recebendo em http://{ENDERECO}:{porta} -> {caixa} (Ctrl+C encerra)", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
        print("caixa: encerrada", flush=True)


def gravar_privado(caminho, texto):
    descritor = os.open(caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
        arquivo.write(texto)


def gerar_chaves(pasta):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    real = conferir_pasta(pasta)
    semente = secrets.token_bytes(32)
    publica = Ed25519PrivateKey.from_private_bytes(semente).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    segredos = os.path.join(real, "segredos_dev.env")
    app = os.path.join(real, "app_dev.env")
    if os.path.exists(segredos) or os.path.exists(app):
        raise SystemExit("chaves já geradas para esta pasta (não sobrescrevo)")
    gravar_privado(segredos, f"CHAVE_HMAC={secrets.token_hex(32)}\nCHAVE_ASSINATURA={semente.hex()}\n")
    gravar_privado(app, f"SINO_SERVICO_URL=http://{ENDERECO}:{PORTA_SERVICO}\n"
                        f"SINO_SERVICO_CHAVES={KID_DEV}:{publica.hex()}\n")
    print(f"chaves: {segredos}\nchaves: {app}")


def main(argv=None):
    analisador = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    comandos = analisador.add_subparsers(dest="comando", required=True)
    comandos.add_parser("chaves").add_argument("pasta")
    receptor = comandos.add_parser("receber")
    receptor.add_argument("pasta")
    receptor.add_argument("--porta", type=int, default=PORTA_PADRAO)
    receptor.add_argument("--abrir", action="store_true", help="abre cada mensagem nova no editor padrão")
    args = analisador.parse_args(argv)
    if args.comando == "chaves":
        gerar_chaves(args.pasta)
    else:
        receber(args.pasta, args.porta, args.abrir)


if __name__ == "__main__":
    sys.exit(main())
