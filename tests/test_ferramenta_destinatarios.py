"""
Ferramenta local da lista de destinatários (ERS v7.0, 5.49; contrato v1.1):
resumos iguais aos do serviço (vetores gerados pelo servidor em
servidor/test/conformidade/destinatarios.json), mesma regra de e-mail
(emails.json), limites, arquivo 600 sem sobrescrever e nenhum e-mail, chave
ou resumo no terminal. Sem rede.
"""

import contextlib
import io
import os
import stat
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "servidor", "ferramentas"))

import destinatarios as dt  # noqa: E402

from apoio_servico import carregar_conformidade  # noqa: E402

CHAVE = bytes.fromhex("11" * 32)


class EntradaFalsa(io.StringIO):
    def __init__(self, texto="", terminal=False):
        super().__init__(texto)
        self.terminal = terminal

    def isatty(self):
        return self.terminal


class TestConformidade(unittest.TestCase):
    def test_resumos_e_verificacao_iguais_aos_do_servidor(self):
        dados = carregar_conformidade("destinatarios.json")
        chave = bytes.fromhex(dados["chave_hmac_hex"])
        self.assertEqual(dt.verificacao(chave), dados["verificacao"])
        for caso in dados["casos"]:
            with self.subTest(entrada=caso["entrada"]):
                if caso["resumo"] is None:
                    self.assertFalse(dt.email_valido(caso["entrada"]))
                else:
                    self.assertEqual(dt.resumo(chave, caso["entrada"]), caso["resumo"])
        self.assertEqual(dt.montar(chave, dados["lista"]["emails"]), (dados["lista"]["texto"], 1))

    def test_mesma_regra_de_email_do_contrato(self):
        for caso in carregar_conformidade("emails.json")["casos"]:
            with self.subTest(entrada=caso["entrada"]):
                self.assertEqual(dt.email_valido(caso["entrada"]), caso["valido"])
                if caso["valido"]:
                    self.assertEqual(dt.normalizar(caso["entrada"]), caso["normalizado"])


class TestMontar(unittest.TestCase):
    def test_limite_de_50_enderecos_diferentes(self):
        cinquenta = [f"d{i}@exemplo.com" for i in range(50)]
        texto, repetidos = dt.montar(CHAVE, cinquenta + ["D0@Exemplo.com"])
        self.assertEqual((texto.count(","), repetidos), (50, 1))
        with self.assertRaises(dt.ListaInvalida):
            dt.montar(CHAVE, cinquenta + ["d50@exemplo.com"])

    def test_vazia_ou_invalida_nao_mostra_o_endereco(self):
        with self.assertRaises(dt.ListaInvalida):
            dt.montar(CHAVE, [])
        for invalido in ("josé@exemplo.com", "pessoa@exemplo.com ", "sem-arroba"):
            with self.subTest(invalido=invalido):
                with self.assertRaises(dt.ListaInvalida) as erro:
                    dt.montar(CHAVE, ["ok@exemplo.com", invalido])
                self.assertNotIn(invalido.strip(), str(erro.exception))
                self.assertIn("2º", str(erro.exception))

    def test_ficticios_da_demonstracao(self):
        self.assertEqual(dt.DESTINATARIOS_FICTICIOS, (
            "pessoa1@demonstracao.invalid", "pessoa2@demonstracao.invalid", "pessoa3@demonstracao.invalid"))
        texto, _ = dt.montar(CHAVE, list(dt.DESTINATARIOS_FICTICIOS))
        self.assertEqual(texto.count(","), 3)


class TestGerar(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp(prefix="sino_destinatarios_")
        self.addCleanup(lambda: [os.remove(os.path.join(self.pasta, n)) for n in os.listdir(self.pasta)]
                        or os.rmdir(self.pasta))
        self.chave = os.path.join(self.pasta, "segredos.env")
        with open(self.chave, "w") as arquivo:
            arquivo.write(f"CHAVE_HMAC={CHAVE.hex()}\nCHAVE_ASSINATURA={'22' * 32}\n")
        self.saida = os.path.join(self.pasta, "lista.txt")

    def gerar(self, entrada, pedir=None):
        with contextlib.redirect_stdout(io.StringIO()) as terminal:
            dt.gerar(self.chave, self.saida, entrada, pedir or (lambda _: ""))
        return terminal.getvalue()

    def test_entrada_por_linhas_arquivo_600_e_terminal_sem_dados(self):
        emails = ["Pessoa@Exemplo.com", "outra@exemplo.com", "pessoa@exemplo.com"]
        terminal = self.gerar(EntradaFalsa("\n".join(emails) + "\n\n"))
        with open(self.saida) as arquivo:
            texto = arquivo.read()
        self.assertEqual(texto, dt.montar(CHAVE, emails)[0] + "\n")
        self.assertEqual(stat.S_IMODE(os.stat(self.saida).st_mode), 0o600)
        self.assertIn("2 endereço(s)", terminal)
        self.assertIn("1 repetido(s)", terminal)
        for proibido in (*emails, "pessoa@exemplo.com", CHAVE.hex(), *texto.strip().split(",")):
            self.assertNotIn(proibido, terminal)
            self.assertNotIn(proibido.split(":")[-1], terminal)

    def test_terminal_sem_eco(self):
        respostas = iter(["pessoa@exemplo.com", "outra@exemplo.com", ""])
        pedidos = []

        def pedir(rotulo):
            pedidos.append(rotulo)
            return next(respostas)

        self.gerar(EntradaFalsa(terminal=True), pedir)
        self.assertEqual(len(pedidos), 3)
        with open(self.saida) as arquivo:
            self.assertEqual(arquivo.read().count(","), 2)

    def test_nao_sobrescreve_e_nao_grava_com_erro(self):
        self.gerar(EntradaFalsa("pessoa@exemplo.com\n"))
        with self.assertRaises(dt.ListaInvalida):
            self.gerar(EntradaFalsa("outra@exemplo.com\n"))
        os.remove(self.saida)
        with self.assertRaises(dt.ListaInvalida):
            self.gerar(EntradaFalsa("invalido\n"))
        self.assertFalse(os.path.exists(self.saida))

    def test_chave_so_hex_ou_linha_e_erros_sem_conteudo(self):
        with open(self.chave, "w") as arquivo:
            arquivo.write(CHAVE.hex() + "\n")
        self.assertEqual(dt.ler_chave(self.chave), CHAVE)
        for conteudo in ("CHAVE_HMAC=abc\n", "", f"CHAVE_HMAC={CHAVE.hex()}\nCHAVE_HMAC={CHAVE.hex()}\n", "x\ny\n"):
            with self.subTest(conteudo=conteudo):
                with open(self.chave, "w") as arquivo:
                    arquivo.write(conteudo)
                with self.assertRaises(dt.ListaInvalida) as erro:
                    dt.ler_chave(self.chave)
                self.assertNotIn("abc", str(erro.exception))

    def test_main_mostra_so_a_mensagem(self):
        with mock.patch.object(sys, "stdin", EntradaFalsa("invalido@\n")):
            with self.assertRaises(SystemExit) as saida:
                dt.main(["gerar", "--chave", self.chave, "--saida", self.saida])
        self.assertTrue(str(saida.exception.code).startswith("destinatarios: "))
        self.assertNotIn("invalido", str(saida.exception.code))


if __name__ == "__main__":
    unittest.main()
