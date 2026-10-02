"""
Modo de demonstração (desenvolvimento): só com SINO_MODO_DEMONSTRACAO=1 E o
serviço em 127.0.0.1, a janela vira "Sino — Demonstração" e as telas com
código mostram o aviso de que os códigos chegam a este computador. Fora
disso, nada muda. Bancos temporários; serviço falso, sem rede.
"""

import os
import unittest
from unittest import mock

import flet as ft

from test_alterar_email_interface import BaseAlteracao
from test_cadastro_codigo_interface import BaseCadastro
from test_recuperacao_interface import BaseRecuperacao

import fluxos_codigo as fc  # noqa: E402 -- backend/ entra no caminho pelos módulos de apoio

DEMONSTRACAO = {"SINO_MODO_DEMONSTRACAO": "1", "SINO_SERVICO_URL": "http://127.0.0.1:8787"}


class TestAtivacao(unittest.TestCase):
    def test_exige_a_variavel_e_o_servico_local(self):
        self.assertTrue(fc.modo_demonstracao(DEMONSTRACAO))
        self.assertTrue(fc.modo_demonstracao({**DEMONSTRACAO, "SINO_SERVICO_URL": "http://127.0.0.1:8787/"}))
        for ambiente in [
            {},
            {"SINO_SERVICO_URL": "http://127.0.0.1:8787"},
            {**DEMONSTRACAO, "SINO_MODO_DEMONSTRACAO": "sim"},
            {**DEMONSTRACAO, "SINO_MODO_DEMONSTRACAO": "0"},
            {"SINO_MODO_DEMONSTRACAO": "1"},
            {**DEMONSTRACAO, "SINO_SERVICO_URL": "https://codigos.sino.exemplo"},
            {**DEMONSTRACAO, "SINO_SERVICO_URL": "http://localhost:8787"},
            {**DEMONSTRACAO, "SINO_SERVICO_URL": "http://127.0.0.1.exemplo.com:8787"},
            {**DEMONSTRACAO, "SINO_SERVICO_URL": "https://127.0.0.1:8787"},
        ]:
            with self.subTest(ambiente=ambiente):
                self.assertFalse(fc.modo_demonstracao(ambiente))


class ComAmbiente:
    ambiente = {}

    def setUp(self):
        sem_modo = {k: v for k, v in os.environ.items() if k not in ("SINO_MODO_DEMONSTRACAO", "SINO_SERVICO_URL")}
        patcher = mock.patch.dict(os.environ, {**sem_modo, **self.ambiente}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        super().setUp()

    def avisos(self, pagina):
        raizes = list(pagina.controls) + [d for d in pagina.dialogos if d.open]
        return [c for raiz in raizes for c in self.visiveis(raiz) if getattr(c, "data", None) == "aviso_demonstracao"]

    def assert_aviso(self, pagina):
        [aviso] = self.avisos(pagina)
        self.assertEqual(aviso.content.value, fc.AVISO_DEMONSTRACAO)


class TestCadastroEmDemonstracao(ComAmbiente, BaseCadastro):
    ambiente = DEMONSTRACAO

    def test_titulo_e_aviso_no_login_cadastro_e_codigo(self):
        pagina, _ = self.abrir_app()
        self.assertEqual(pagina.title, fc.TITULO_DEMONSTRACAO)
        self.assert_aviso(pagina)                       # login
        pagina, _ = self.abrir_cadastro()
        self.assert_aviso(pagina)                       # cadastro
        self.ate_o_codigo(pagina)
        self.assert_aviso(pagina)                       # tela de código


class TestRecuperacaoEmDemonstracao(ComAmbiente, BaseRecuperacao):
    ambiente = DEMONSTRACAO

    def test_aviso_nos_passos_da_recuperacao(self):
        pagina, _ = self.abrir_recuperacao()
        self.assert_aviso(pagina)
        self.pedir(pagina, "bia@sino.com")
        self.assert_aviso(pagina)


class TestAlteracaoEmDemonstracao(ComAmbiente, BaseAlteracao):
    ambiente = DEMONSTRACAO

    def test_aviso_no_dialogo_de_alterar_email(self):
        pagina, _ = self.abrir_ajustes()
        self.assertEqual(self.avisos(pagina), [])       # só nas telas com código
        self.editar(pagina)
        self.assert_aviso(pagina)


class TestForaDaDemonstracao(ComAmbiente, BaseCadastro):
    ambiente = {}

    def test_sem_aviso_e_titulo_normal(self):
        pagina, _ = self.abrir_app()
        self.assertEqual(pagina.title, "Sino")
        self.assertEqual(self.avisos(pagina), [])
        pagina, _ = self.abrir_cadastro()
        self.ate_o_codigo(pagina)
        self.assertEqual(self.avisos(pagina), [])
        self.assertNotIn(fc.AVISO_DEMONSTRACAO, self.textos_visiveis(pagina))


class TestServicoNaoLocal(ComAmbiente, BaseCadastro):
    ambiente = {**DEMONSTRACAO, "SINO_SERVICO_URL": "https://codigos.sino.exemplo"}

    def test_variavel_sozinha_nao_ativa(self):
        pagina, _ = self.abrir_app()
        self.assertEqual(pagina.title, "Sino")
        self.assertEqual(self.avisos(pagina), [])


if __name__ == "__main__":
    unittest.main()
