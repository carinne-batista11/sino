"""
Rolagem das telas de autenticação (Etapa 8, correção da validação manual):
na janela de 760 px, o cadastro com a mensagem de falha de conexão passava
da altura e "Já tem conta? Entrar" ficava fora de alcance. Login/cadastro,
código do cadastro e recuperação ficam numa única coluna que ocupa a altura
da janela e rola; o botão de navegação fica dentro dela e visível. Os testes
não medem pixels: conferem a estrutura que permite alcançar o botão.
"""

import io
import unittest
from contextlib import redirect_stderr

import flet as ft

from test_cadastro_codigo_interface import BaseCadastro
from test_recuperacao_interface import BaseRecuperacao

import fluxos_codigo as fc  # noqa: E402 -- backend/ entra no caminho pelos módulos de apoio
import servico_codigos as sc  # noqa: E402


class AssercoesDeRolagem:
    def assert_tela_rolavel_com(self, pagina, rotulo):
        """Uma só coluna na página, com rolagem e altura da janela, e `rotulo` visível dentro dela."""
        self.assertEqual(len(pagina.controls), 1)
        raiz = pagina.controls[0]
        self.assertIsInstance(raiz, ft.Column)
        self.assertEqual(raiz.scroll, ft.ScrollMode.AUTO)
        self.assertTrue(raiz.expand)
        self.assertTrue(any(isinstance(c, (ft.TextButton, ft.Button)) and c.content == rotulo
                            for c in self.visiveis(raiz)), rotulo)


class TestRolagemCadastroELogin(AssercoesDeRolagem, BaseCadastro):
    def test_login(self):
        pagina, _ = self.abrir_app()
        self.assert_tela_rolavel_com(pagina, "Não tem conta? Criar conta")
        self.assert_tela_rolavel_com(pagina, "Esqueci minha senha")

    def test_cadastro_apos_falha_de_conexao(self):  # caso da validação manual
        pagina, _ = self.abrir_cadastro()
        self.servidor.falhas = [sc.ErroDeConexao("ConnectError")] * 3
        self.preencher(pagina)
        with redirect_stderr(io.StringIO()):
            self.criar(pagina)
            pagina.executar_pendentes()
        self.assertTrue(any(t.startswith("Sem conexão") for t in self.textos_visiveis(pagina)))
        self.assert_tela_rolavel_com(pagina, "Já tem conta? Entrar")
        self.acionar(pagina, self.botao(pagina, "Já tem conta? Entrar"))
        self.assertIn("Bem-vindo de volta", self.textos_visiveis(pagina))

    def test_cadastro_ao_voltar_de_um_documento(self):
        pagina, _ = self.abrir_cadastro()
        self.acionar(pagina, self.botao(pagina, "Ler Termos de Uso"))
        self.acionar(pagina, self.botao(pagina, "Voltar"))
        self.assert_tela_rolavel_com(pagina, "Já tem conta? Entrar")

    def test_codigo_do_cadastro(self):
        pagina, _ = self.abrir_cadastro()
        self.ate_o_codigo(pagina)
        self.confirmar(pagina, "999999" if self.servidor.ultimo_codigo("carla@sino.com") != "999999" else "111111")
        pagina.executar_pendentes()
        self.assertIn("Código incorreto. Restam 4 tentativas.", self.textos_visiveis(pagina))
        self.assert_tela_rolavel_com(pagina, "Voltar")
        self.assert_tela_rolavel_com(pagina, "Reenviar código")


class TestRolagemRecuperacao(AssercoesDeRolagem, BaseRecuperacao):
    def test_os_tres_passos(self):
        pagina, _ = self.abrir_recuperacao()
        self.assert_tela_rolavel_com(pagina, "Voltar ao login")
        self.pedir(pagina, "bia@sino.com")
        self.assertIn(fc.MENSAGEM_RECUPERACAO_NEUTRA, self.textos_visiveis(pagina))
        self.assert_tela_rolavel_com(pagina, "Voltar ao login")
        self.confirmar(pagina, self.servidor.ultimo_codigo("bia@sino.com"))
        self.redefinir(pagina, "curta")
        self.assertIn("A senha deve ter pelo menos 8 caracteres.", self.textos_visiveis(pagina))
        self.assert_tela_rolavel_com(pagina, "Voltar ao login")

    def test_falha_de_conexao(self):
        self.servidor.falhas = [sc.ErroDeConexao("ConnectError")] * 3
        pagina, _ = self.abrir_recuperacao()
        with redirect_stderr(io.StringIO()):
            self.pedir(pagina, "bia@sino.com")
        self.assertTrue(any(t.startswith("Sem conexão") for t in self.textos_visiveis(pagina)))
        self.assert_tela_rolavel_com(pagina, "Voltar ao login")


if __name__ == "__main__":
    unittest.main()
