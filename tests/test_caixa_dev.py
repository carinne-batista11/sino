"""
Caixa de mensagens de desenvolvimento (servidor/ferramentas/caixa_dev.py),
usada só na validação manual com o serviço local. Sem rede: as funções de
leitura, gravação e geração de chaves são testadas diretamente.
"""

import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "servidor", "ferramentas"))

import caixa_dev as cd  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
