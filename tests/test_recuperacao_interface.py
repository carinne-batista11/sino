"""
Recuperação de senha pelo login (ERS v6.0, Etapa 8: RF39, 5.35; CT89, CT90,
CT93, CT94, CT113): três passos na tela real, sempre no tema Claro, com
resposta e navegação neutras para conta verificada, conta antiga não
verificada e e-mail inexistente. Cliente real sobre o ServidorFalso,
relógio injetável e bancos temporários.
"""

import asyncio
import io
import threading
import unittest
from contextlib import redirect_stderr
from unittest import mock

from apoio_banco import db
from apoio_interface_codigos import ComServicoFalso
from test_sessao_tema import CLARO, TesteDeSessao, main

import fluxos_codigo as fc  # noqa: E402 -- backend/ entra no caminho pelos módulos de apoio
import servico_codigos as sc  # noqa: E402

NOVA = "novasenha9"


class BaseRecuperacao(ComServicoFalso, TesteDeSessao):
    def setUp(self):
        super().setUp()
        # Bia passa a ter o e-mail verificado; Ana continua uma conta antiga de teste.
        self.executar("UPDATE usuarios SET email_verificado = 1 WHERE id = ?", (self.bia,))

    def abrir_recuperacao(self):
        pagina, sessao = self.abrir_app()
        self.acionar(pagina, self.botao(pagina, "Esqueci minha senha"))
        return pagina, sessao

    def principal(self, pagina):
        return next(b for b in self.todos(pagina) if type(b).__name__ == "Button"
                    and b.content in ("Enviar código", "Confirmar código", "Redefinir senha"))

    def pedir(self, pagina, email):
        self.campo(pagina, "E-mail").value = email
        self.acionar(pagina, self.principal(pagina))
        pagina.executar_pendentes()

    def confirmar(self, pagina, codigo):
        self.campo(pagina, "Código").value = codigo
        self.acionar(pagina, self.principal(pagina))
        pagina.executar_pendentes()

    def redefinir(self, pagina, nova, confirmacao=None):
        self.campo(pagina, "Nova senha").value = nova
        self.campo(pagina, "Confirmar nova senha").value = nova if confirmacao is None else confirmacao
        self.acionar(pagina, self.principal(pagina))
        pagina.executar_pendentes()

    def passo_visivel(self, pagina):
        return {rotulo: self.campo(pagina, rotulo).visible
                for rotulo in ("E-mail", "Código", "Nova senha", "Confirmar nova senha")}

    def ate_a_nova_senha(self, pagina, email="bia@sino.com"):
        self.pedir(pagina, email)
        self.confirmar(pagina, self.servidor.ultimo_codigo(email))
        self.assertTrue(self.passo_visivel(pagina)["Nova senha"])


class TestRecuperacao(BaseRecuperacao):
    def test_link_so_no_login_e_tela_sempre_em_claro(self):
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "ana@sino.com", "senha1234")             # tema escuro
        sessao.encerrar()
        self.assertTrue(self.botao(pagina, "Esqueci minha senha").visible)
        self.acionar(pagina, self.botao(pagina, "Não tem conta? Criar conta"))
        self.assertFalse(self.botao(pagina, "Esqueci minha senha").visible)
        self.acionar(pagina, self.botao(pagina, "Já tem conta? Entrar"))
        self.acionar(pagina, self.botao(pagina, "Esqueci minha senha"))
        self.assert_tema_da_pagina(pagina, sessao, "claro")
        titulo = next(t for t in self.todos(pagina) if getattr(t, "value", None) == "Redefinir senha")
        self.assertEqual(titulo.color, CLARO["texto_principal"])

    def test_resposta_e_navegacao_neutras(self):  # CT93
        vistos = []
        for email in ("bia@sino.com", "ANA@sino.com", "ninguem@sino.com"):
            with self.subTest(email=email):
                pagina, _ = self.abrir_recuperacao()
                self.pedir(pagina, email)
                vistos.append((self.passo_visivel(pagina), [t for t in self.textos_visiveis(pagina)
                                                            if "@" not in t]))
        self.assertEqual(vistos[0], vistos[1])
        self.assertEqual(vistos[1], vistos[2])
        self.assertIn(fc.MENSAGEM_RECUPERACAO_NEUTRA, vistos[0][1])
        self.assertEqual([p["sem_envio"] for p in self.servidor.pedidos], [False, True, True])
        self.assertEqual([e for e, _ in self.servidor.enviados], ["bia@sino.com"])

    def test_codigo_errado_tem_a_mesma_resposta_com_e_sem_envio(self):
        respostas = []
        for email in ("bia@sino.com", "ninguem@sino.com"):
            pagina, _ = self.abrir_recuperacao()
            self.pedir(pagina, email)
            self.confirmar(pagina, "999999")
            respostas.append([t for t in self.textos_visiveis(pagina) if "@" not in t])
        self.assertEqual(respostas[0], respostas[1])
        self.assertIn("Código incorreto. Restam 4 tentativas.", respostas[0])

    def test_formato_recusado_antes_de_consultar_a_conta(self):
        with mock.patch.object(main.database, "existe_conta_verificada",
                               side_effect=AssertionError("consultou a conta")):
            for email in ("josé@sino.com", "sem-arroba", "bia@sino.com "):
                with self.subTest(email=repr(email)):
                    pagina, _ = self.abrir_recuperacao()
                    self.pedir(pagina, email)
                    self.assertIn("Informe um e-mail válido.", self.textos_visiveis(pagina))
                    self.assertTrue(self.passo_visivel(pagina)["E-mail"])
        self.assertEqual(self.servidor.pedidos, [])

    def test_fluxo_completo_com_recusas_que_nao_consomem(self):  # CT94
        pagina, _ = self.abrir_recuperacao()
        self.ate_a_nova_senha(pagina)
        recusas = [(NOVA, "outra-coisa1", "A confirmação não confere com a nova senha."),
                   ("curta", None, "A senha deve ter pelo menos 8 caracteres."),
                   ("senha5678", None, "A nova senha deve ser diferente da atual.")]
        for nova, confirmacao, mensagem in recusas:
            with self.subTest(mensagem=mensagem):
                self.redefinir(pagina, nova, confirmacao)
                self.assertIn(mensagem, self.textos_visiveis(pagina))
                self.assertTrue(self.passo_visivel(pagina)["Nova senha"])
                self.assertEqual(self.autorizacoes_usadas(), 0)
        self.redefinir(pagina, NOVA)
        self.assertIn("Senha redefinida. Entre com a nova senha.", self.textos_visiveis(pagina))
        self.assertIsNone(db.verificar_login("bia@sino.com", "senha5678"))
        self.assertIsNotNone(db.verificar_login("bia@sino.com", NOVA))
        self.assertEqual(self.autorizacoes_usadas(), 1)

    def test_prazo_vencido_volta_ao_inicio_sem_gravar(self):  # CT89
        pagina, _ = self.abrir_recuperacao()
        self.ate_a_nova_senha(pagina)
        self.relogio.avancar(600)
        self.redefinir(pagina, NOVA)
        self.assertIn(fc.MENSAGEM_EXPIRADA, self.textos_visiveis(pagina))
        self.assertTrue(self.passo_visivel(pagina)["E-mail"])
        self.assertIsNotNone(db.verificar_login("bia@sino.com", "senha5678"))

    def test_reenvio_antes_de_60_s(self):  # CT113
        pagina, _ = self.abrir_recuperacao()
        self.pedir(pagina, "ninguem@sino.com")
        self.acionar(pagina, self.botao(pagina, "Reenviar código"))
        pagina.executar_pendentes()
        self.assertTrue(any(t.startswith("Aguarde") for t in self.textos_visiveis(pagina)))
        self.assertTrue(self.servidor.pedidos[-1]["sem_envio"])        # mantém a decisão do primeiro pedido

    def test_servico_nao_configurado_e_sem_conexao(self):
        self.servico_configurado = False
        pagina, _ = self.abrir_recuperacao()
        self.pedir(pagina, "bia@sino.com")
        self.assertIn(fc.MENSAGEM_NAO_CONFIGURADO, self.textos_visiveis(pagina))
        self.servico_configurado = True
        self.servidor.falhas = [sc.ErroDeConexao("ConnectError")] * 3
        pagina, _ = self.abrir_recuperacao()
        with redirect_stderr(io.StringIO()) as saida:
            self.pedir(pagina, "bia@sino.com")
        self.assertTrue(any(t.startswith("Sem conexão") for t in self.textos_visiveis(pagina)))
        self.assertNotIn("bia@sino.com", saida.getvalue())

    def test_erro_inesperado_libera_a_tela_sem_dados_no_terminal(self):
        pagina, _ = self.abrir_recuperacao()
        saida = io.StringIO()
        with mock.patch.object(self.servico.cliente, "pedir_codigo",
                               side_effect=RuntimeError("bia@sino.com")), redirect_stderr(saida):
            self.pedir(pagina, "bia@sino.com")
        self.assertIn(fc.MENSAGEM_FALHA_GENERICA, self.textos_visiveis(pagina))
        self.assertFalse(self.principal(pagina).disabled)
        self.assertFalse(self.botao(pagina, "Voltar ao login").disabled)
        self.assertIn("(RuntimeError)", saida.getvalue())
        self.assertNotIn("bia@sino.com", saida.getvalue())

    def test_voltar_ao_login(self):
        pagina, sessao = self.abrir_recuperacao()
        self.acionar(pagina, self.botao(pagina, "Voltar ao login"))
        self.assertIn("Bem-vindo de volta", self.textos_visiveis(pagina))
        self.entrar(pagina, "bia@sino.com", "senha5678")
        self.assertEqual(sessao.usuario["id"], self.bia)


class TestRecuperacaoCancelamento(BaseRecuperacao, unittest.IsolatedAsyncioTestCase):
    async def test_voltar_durante_o_pedido_cancela(self):
        pagina, _ = self.abrir_recuperacao()
        self.servidor.portao = portao = asyncio.Event()
        self.campo(pagina, "E-mail").value = "bia@sino.com"
        self.acionar(pagina, self.principal(pagina))
        for _ in range(20):
            await asyncio.sleep(0)
        self.acionar(pagina, self.botao(pagina, "Voltar ao login"))
        portao.set()
        await pagina.concluir_tarefas()
        self.assertIn("Bem-vindo de volta", self.textos_visiveis(pagina))
        self.assertNotIn(fc.MENSAGEM_RECUPERACAO_NEUTRA, self.textos_visiveis(pagina))

    async def test_voltar_durante_a_gravacao_e_ignorado(self):
        pagina, _ = self.abrir_recuperacao()
        self.campo(pagina, "E-mail").value = "bia@sino.com"
        self.acionar(pagina, self.principal(pagina))
        await pagina.concluir_tarefas()
        self.campo(pagina, "Código").value = self.servidor.ultimo_codigo("bia@sino.com")
        self.acionar(pagina, self.principal(pagina))
        await pagina.concluir_tarefas()

        comecou, liberar = threading.Event(), threading.Event()
        original = db.redefinir_senha_por_autorizacao

        def redefinir_devagar(*args):
            comecou.set()
            liberar.wait(5)
            return original(*args)

        with mock.patch.object(main.database, "redefinir_senha_por_autorizacao", redefinir_devagar):
            self.campo(pagina, "Nova senha").value = NOVA
            self.campo(pagina, "Confirmar nova senha").value = NOVA
            self.acionar(pagina, self.principal(pagina))
            await asyncio.to_thread(comecou.wait, 5)
            voltar = self.botao(pagina, "Voltar ao login")
            self.assertTrue(voltar.disabled)
            self.acionar(pagina, voltar)
            liberar.set()
            await pagina.concluir_tarefas()
        self.assertIn("Senha redefinida. Entre com a nova senha.", self.textos_visiveis(pagina))
        self.assertIsNotNone(db.verificar_login("bia@sino.com", NOVA))


if __name__ == "__main__":
    unittest.main()
