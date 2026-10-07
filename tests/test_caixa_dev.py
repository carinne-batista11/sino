"""
Caixa de mensagens de desenvolvimento (servidor/ferramentas/caixa_dev.py),
usada na validação manual e no modo de demonstração. As funções de leitura,
gravação, abertura e geração de chaves são testadas diretamente; o receptor
HTTP só em 127.0.0.1, porta efêmera (sem rede externa).
"""

import contextlib
import http.client
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import HTTPServer
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "servidor", "ferramentas"))

import caixa_dev as cd  # noqa: E402
import destinatarios as dt  # noqa: E402

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat  # noqa: E402

MENSAGEM = {"para": "pessoa@sino.teste", "assunto": "Código do Sino", "texto": "Seu código:\n\n042137\n", "chave": "sino/cadastro/d1"}


class TestLerMensagem(unittest.TestCase):
    def test_valida(self):
        self.assertEqual(cd.ler_mensagem(json.dumps(MENSAGEM).encode()), MENSAGEM)

    def test_invalidas(self):
        for corpo in [b"{", b"\xff", b"[]", json.dumps({**MENSAGEM, "extra": "x"}).encode(),
                      json.dumps({k: v for k, v in MENSAGEM.items() if k != "chave"}).encode(),
                      json.dumps({**MENSAGEM, "texto": ""}).encode(), json.dumps({**MENSAGEM, "para": 1}).encode()]:
            with self.subTest(corpo=corpo), self.assertRaises(cd.MensagemInvalida):
                cd.ler_mensagem(corpo)


class TestGravarMensagem(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory(prefix="sino_caixa_")
        self.addCleanup(pasta.cleanup)
        self.caixa = pasta.name

    def arquivos(self):
        return sorted(os.listdir(self.caixa))

    def test_grava_com_permissao_600(self):
        self.assertEqual(cd.gravar_mensagem(self.caixa, MENSAGEM), 1)
        [nome] = self.arquivos()
        caminho = os.path.join(self.caixa, nome)
        self.assertEqual(stat.S_IMODE(os.stat(caminho).st_mode), 0o600)
        with open(caminho, encoding="utf-8") as arquivo:
            conteudo = arquivo.read()
        self.assertIn("Para: pessoa@sino.teste", conteudo)
        self.assertIn("042137", conteudo)
        self.assertNotIn(MENSAGEM["chave"], nome)

    def test_repeticao_idempotente_e_chave_reutilizada(self):
        cd.gravar_mensagem(self.caixa, MENSAGEM)
        self.assertEqual(cd.gravar_mensagem(self.caixa, MENSAGEM), 1)
        self.assertEqual(len(self.arquivos()), 1)
        with self.assertRaises(cd.ChaveReutilizada):
            cd.gravar_mensagem(self.caixa, {**MENSAGEM, "texto": "outro 111111"})
        self.assertEqual(cd.gravar_mensagem(self.caixa, {**MENSAGEM, "chave": "sino/cadastro/d2"}), 2)
        self.assertEqual(len(self.arquivos()), 2)

    def test_falha_na_escrita_nao_deixa_arquivo(self):
        with mock.patch.object(cd.os, "fsync", side_effect=OSError("disco")), self.assertRaises(OSError):
            cd.gravar_mensagem(self.caixa, MENSAGEM)
        self.assertEqual(self.arquivos(), [])


def ler(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        return arquivo.read()


class TestPastaEChaves(unittest.TestCase):
    def test_pasta_dentro_do_projeto_recusada(self):
        with self.assertRaises(SystemExit):
            cd.conferir_pasta(cd.RAIZ_DO_PROJETO)
        with self.assertRaises(SystemExit):
            cd.conferir_pasta(os.path.join(cd.RAIZ_DO_PROJETO, "database"))

    def test_chaves(self):
        with tempfile.TemporaryDirectory(prefix="sino_chaves_") as pasta:
            with contextlib.redirect_stdout(io.StringIO()) as saida:
                cd.gerar_chaves(pasta)
            segredos = dict(l.split("=", 1) for l in ler(os.path.join(pasta, "segredos_dev.env")).split())
            app = dict(l.split("=", 1) for l in ler(os.path.join(pasta, "app_dev.env")).split())
            for nome in ("segredos_dev.env", "app_dev.env"):
                self.assertEqual(stat.S_IMODE(os.stat(os.path.join(pasta, nome)).st_mode), 0o600)
            self.assertNotIn(segredos["CHAVE_ASSINATURA"], saida.getvalue())
            self.assertNotIn(segredos["CHAVE_HMAC"], saida.getvalue())
            self.assertEqual(len(bytes.fromhex(segredos["CHAVE_HMAC"])), 32)
            publica = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(segredos["CHAVE_ASSINATURA"])) \
                .public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
            self.assertEqual(app["SINO_SERVICO_CHAVES"], f"dev-1:{publica.hex()}")
            self.assertEqual(app["SINO_SERVICO_URL"], "http://127.0.0.1:8787")
            self.assertNotIn("CHAVE_ASSINATURA", ler(os.path.join(pasta, "app_dev.env")))
            with self.assertRaises(SystemExit):
                cd.gerar_chaves(pasta)  # não sobrescreve

    def test_chaves_com_destinatarios_ficticios(self):  # contrato v1.1
        with tempfile.TemporaryDirectory(prefix="sino_chaves_") as pasta:
            with contextlib.redirect_stdout(io.StringIO()) as saida:
                cd.gerar_chaves(pasta)
            segredos = dict(l.split("=", 1) for l in ler(os.path.join(pasta, "segredos_dev.env")).split())
            chave = bytes.fromhex(segredos["CHAVE_HMAC"])
            esperado, _ = dt.montar(chave, list(dt.DESTINATARIOS_FICTICIOS))
            self.assertEqual(segredos["DESTINATARIOS_PERMITIDOS"], esperado)
            for resumo in esperado.split(","):
                self.assertNotIn(resumo.split(":")[-1], saida.getvalue())
            orientacao = os.path.join(pasta, cd.ORIENTACAO_DESTINATARIOS)
            self.assertEqual(stat.S_IMODE(os.stat(orientacao).st_mode), 0o600)
            texto = ler(orientacao)
            for email in ("pessoa1@demonstracao.invalid", "pessoa2@demonstracao.invalid", "pessoa3@demonstracao.invalid"):
                self.assertIn(email, texto)
            self.assertIn("O envio de códigos está restrito nesta fase do Sino.", texto)


class ProcessoFalso:
    def __init__(self, codigo=0, demora=False):
        self.codigo, self.demora = codigo, demora

    def wait(self, timeout=None):
        if self.demora:
            raise subprocess.TimeoutExpired("xdg-open", timeout)
        return self.codigo


class TestAbrirMensagem(unittest.TestCase):
    CAMINHO = "/caixa/0001_abcd_120000.txt"

    def abrir(self, popen):
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            tarefa = cd.abrir_mensagem(1, self.CAMINHO, popen=popen, espera_s=0)
            if tarefa is not None:
                tarefa.join(2)
        return saida.getvalue()

    def test_abre_com_xdg_open_sem_aviso(self):
        chamadas = []
        saida = self.abrir(lambda args, **kw: chamadas.append(args) or ProcessoFalso(0))
        self.assertEqual(chamadas, [["xdg-open", self.CAMINHO]])
        self.assertEqual(saida, "")

    def test_editor_ainda_aberto_conta_como_aberto(self):
        self.assertEqual(self.abrir(lambda args, **kw: ProcessoFalso(demora=True)), "")

    def test_falha_so_informa_o_caminho(self):
        def sem_abridor(args, **kw):
            raise FileNotFoundError("xdg-open")
        for popen in (sem_abridor, lambda args, **kw: ProcessoFalso(3)):
            saida = self.abrir(popen)
            self.assertIn("não foi possível abrir a mensagem 1 automaticamente; abra manualmente: " + self.CAMINHO, saida)


class TestReceptorComAbertura(unittest.TestCase):
    """Receptor real em 127.0.0.1 (porta efêmera): abre só mensagens novas, depois de responder."""

    def setUp(self):
        pasta = tempfile.TemporaryDirectory(prefix="sino_caixa_")
        self.addCleanup(pasta.cleanup)
        self.caixa = pasta.name
        self.abertas = []
        self.servidor = HTTPServer(("127.0.0.1", 0), cd.criar_receptor(self.caixa, self.abrir))
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.addCleanup(self.servidor.server_close)
        self.addCleanup(self.servidor.shutdown)

    def abrir(self, numero, caminho):
        self.abertas.append((numero, os.path.basename(caminho)))
        if numero == 2:
            raise RuntimeError("abridor quebrado")

    def enviar(self, mensagem):
        conexao = http.client.HTTPConnection("127.0.0.1", self.servidor.server_address[1], timeout=5)
        try:
            corpo = json.dumps(mensagem).encode()
            conexao.request("POST", "/mensagens", corpo, {"Content-Type": "application/json"})
            return conexao.getresponse().status
        finally:
            conexao.close()

    def test_abre_so_mensagens_novas_e_falha_ao_abrir_nao_e_falha_de_entrega(self):
        with contextlib.redirect_stdout(io.StringIO()) as saida:
            self.assertEqual(self.enviar(MENSAGEM), 200)
            self.assertEqual(self.enviar(MENSAGEM), 200)  # repetição: não abre de novo
            self.assertEqual(self.enviar({**MENSAGEM, "chave": "sino/cadastro/d2"}), 200)
            self.servidor.shutdown()  # o receptor abre depois de responder: espera o último pedido terminar
        self.assertEqual([n for n, _ in self.abertas], [1, 2])
        self.assertTrue(all(nome.startswith(f"{n:04d}_") for n, nome in self.abertas))
        self.assertEqual(len(os.listdir(self.caixa)), 2)
        self.assertIn("falha ao abrir a mensagem 2 (RuntimeError)", saida.getvalue())
        self.assertNotIn("042137", saida.getvalue())


if __name__ == "__main__":
    unittest.main()
