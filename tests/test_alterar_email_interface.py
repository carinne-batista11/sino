"""
Alteração de e-mail em Ajustes (ERS v6.0, Etapa 8: RF36, 5.31, 5.32; CT87,
CT88, CT111, CT112): senha atual + novo e-mail, código enviado ao novo
endereço, e-mail antigo válido até a conclusão, selo "Verificado" só quando
confirmado. Cliente real sobre o ServidorFalso e bancos temporários.
"""

import asyncio
import hashlib
import io
import threading
import unittest
from contextlib import redirect_stderr
from unittest import mock

import flet as ft

from apoio_banco import db
from apoio_interface_codigos import ComServicoFalso
from test_sessao_tema import TesteDeSessao, main

import fluxos_codigo as fc  # noqa: E402 -- backend/ entra no caminho pelos módulos de apoio

NOVO = "Bia.Nova@Sino.com"


class BaseAlteracao(ComServicoFalso, TesteDeSessao):
    def abrir_ajustes(self, email="bia@sino.com", senha="senha5678"):
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, email, senha)
        self.abrir_aba(pagina, "Ajustes")
        return pagina, sessao

    def editar(self, pagina):
        botao = next(b for b in self.todos(pagina) if isinstance(b, ft.OutlinedButton) and b.data == "editar_email")
        self.acionar(pagina, botao)
        dialogo = next(d for d in pagina.dialogos if d.open)
        self.assertEqual(dialogo.title.value, "Alterar e-mail")
        return dialogo

    def pedir(self, pagina, senha="senha5678", novo=NOVO):
        self.campo(pagina, "Senha atual").value = senha
        self.campo(pagina, "Novo e-mail").value = novo
        self.acionar(pagina, self.botao(pagina, "Enviar código"))
        pagina.executar_pendentes()

    def confirmar(self, pagina, codigo):
        self.campo(pagina, "Código").value = codigo
        self.acionar(pagina, self.botao(pagina, "Confirmar"))
        pagina.executar_pendentes()

    def email_de(self, usuario_id):
        return self.consultar("SELECT email, email_verificado FROM usuarios WHERE id = ?", (usuario_id,))[0]

    def selo(self, pagina):
        return [c for c in self.todos(pagina) if getattr(c, "data", None) == "selo_verificado"]


class TestAlteracaoDeEmail(BaseAlteracao):
    def test_conta_antiga_sem_selo_e_conta_verificada_com_selo(self):
        pagina, _ = self.abrir_ajustes()
        self.assertEqual(self.selo(pagina), [])
        self.executar("UPDATE usuarios SET email_verificado = 1 WHERE id = ?", (self.bia,))
        self.abrir_aba(pagina, "Ajustes")
        self.assertEqual(len(self.selo(pagina)), 1)
        self.assertIn("Verificado", self.textos_visiveis(pagina))

    def test_fluxo_completo(self):  # CT88, CT112
        pagina, sessao = self.abrir_ajustes()
        self.editar(pagina)
        campo_senha = self.campo(pagina, "Senha atual")
        self.pedir(pagina)
        self.assertEqual(campo_senha.value, "")                       # a senha não fica no diálogo
        self.assertIn(f"Digite o código de 6 dígitos enviado para {NOVO}.", self.textos_visiveis(pagina))
        self.assertEqual(self.servidor.pedidos[0]["email"], NOVO)
        # Até concluir, o e-mail atual continua valendo (CT112).
        self.assertIsNotNone(db.verificar_login("bia@sino.com", "senha5678"))
        self.assertEqual(self.email_de(self.bia), ("bia@sino.com", 0))

        self.confirmar(pagina, self.servidor.ultimo_codigo(NOVO))

        self.assertFalse([d for d in pagina.dialogos if d.open])
        self.assertEqual(self.email_de(self.bia), (NOVO, 1))
        self.assertIn(NOVO, self.textos_visiveis(pagina))
        self.assertEqual(len(self.selo(pagina)), 1)
        self.assertIn("E-mail alterado com sucesso.", self.textos_visiveis(pagina))
        self.assertIsNone(db.verificar_login("bia@sino.com", "senha5678"))
        self.assertIsNotNone(db.verificar_login(NOVO.lower(), "senha5678"))
        self.assertEqual(sessao.usuario["id"], self.bia)
        self.abrir_aba(pagina, "Ajustes")                                # o aviso aparece uma vez só
        self.assertNotIn("E-mail alterado com sucesso.", self.textos_visiveis(pagina))

    def test_recusas_antes_do_codigo(self):  # CT111
        casos = [
            ("errada123", NOVO, "A senha atual está incorreta."),
            ("senha5678", "BIA@sino.com", "Esse já é o e-mail da sua conta."),
            ("senha5678", "Ana@SINO.com", "Já existe uma conta com esse e-mail."),
            ("senha5678", "josé@sino.com", "Informe um e-mail válido."),
            ("", NOVO, "Preencha a senha atual e o novo e-mail."),
        ]
        pagina, _ = self.abrir_ajustes()
        for senha, novo, mensagem in casos:
            with self.subTest(mensagem=mensagem):
                self.editar(pagina)
                self.pedir(pagina, senha, novo)
                self.assertIn(mensagem, self.textos_visiveis(pagina))
                self.assertTrue(self.campo(pagina, "Novo e-mail").visible)
                self.acionar(pagina, self.botao(pagina, "Cancelar"))
        self.assertEqual(self.servidor.pedidos, [])
        self.assertEqual(self.email_de(self.bia), ("bia@sino.com", 0))

    def test_senha_atual_antiga_continua_aceita(self):
        legado = hashlib.sha256("a b".encode()).hexdigest()           # formato antigo, curta e com espaço
        self.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (legado, self.bia))
        pagina, _ = self.abrir_ajustes(senha="a b")
        self.editar(pagina)
        self.pedir(pagina, senha="a b")
        self.confirmar(pagina, self.servidor.ultimo_codigo(NOVO))
        self.assertEqual(self.email_de(self.bia), (NOVO, 1))

    def test_cancelar_no_codigo_nao_altera_nada(self):  # CT87
        pagina, _ = self.abrir_ajustes()
        self.editar(pagina)
        self.pedir(pagina)
        codigo = self.servidor.ultimo_codigo(NOVO)
        self.acionar(pagina, self.botao(pagina, "Cancelar"))
        self.assertFalse([d for d in pagina.dialogos if d.open])
        self.assertEqual(self.email_de(self.bia), ("bia@sino.com", 0))
        self.assertIsNotNone(codigo)
        self.editar(pagina)                                             # reabre do início
        self.assertTrue(self.campo(pagina, "Senha atual").visible)

    def test_codigo_errado_e_servico_nao_configurado(self):
        pagina, _ = self.abrir_ajustes()
        self.editar(pagina)
        self.pedir(pagina)
        self.confirmar(pagina, "000000" if self.servidor.ultimo_codigo(NOVO) != "000000" else "111111")
        self.assertIn("Código incorreto. Restam 4 tentativas.", self.textos_visiveis(pagina))
        self.acionar(pagina, self.botao(pagina, "Cancelar"))

        self.servico_configurado = False
        pagina, _ = self.abrir_ajustes()
        self.editar(pagina)
        self.pedir(pagina)
        self.assertIn(fc.MENSAGEM_NAO_CONFIGURADO, self.textos_visiveis(pagina))

    def test_erro_na_tela_depois_de_gravar_nao_vira_falha(self):
        pagina, _ = self.abrir_ajustes()
        self.editar(pagina)
        self.pedir(pagina)
        saida = io.StringIO()
        # A gravação conclui; a releitura de Ajustes (só depois de gravar) quebra.
        with mock.patch.object(main.database, "obter_usuario", side_effect=RuntimeError(NOVO)), \
                redirect_stderr(saida):
            self.confirmar(pagina, self.servidor.ultimo_codigo(NOVO))
        self.assertEqual(self.email_de(self.bia), (NOVO, 1))           # transação concluída
        self.assertNotIn(fc.MENSAGEM_FALHA_GENERICA, self.textos_visiveis(pagina))
        self.assertIn("atualização da tela após gravar (RuntimeError)", saida.getvalue())
        self.assertNotIn(NOVO, saida.getvalue())
        self.assertNotIn(NOVO.lower(), saida.getvalue())

    def test_email_ocupado_antes_da_conclusao(self):
        pagina, _ = self.abrir_ajustes()
        self.editar(pagina)
        self.pedir(pagina)
        self.criar_usuario(email=NOVO.upper())
        self.confirmar(pagina, self.servidor.ultimo_codigo(NOVO))
        self.assertIn("Já existe uma conta com esse e-mail.", self.textos_visiveis(pagina))
        self.assertEqual(self.email_de(self.bia), ("bia@sino.com", 0))
        self.assertEqual(self.autorizacoes_usadas(), 0)


class TestAlteracaoCancelamento(BaseAlteracao, unittest.IsolatedAsyncioTestCase):
    async def test_sair_da_conta_durante_a_gravacao_nao_atualiza_a_sessao_de_ninguem(self):
        pagina, sessao = self.abrir_ajustes()
        self.editar(pagina)
        self.campo(pagina, "Senha atual").value = "senha5678"
        self.campo(pagina, "Novo e-mail").value = NOVO
        self.acionar(pagina, self.botao(pagina, "Enviar código"))
        await pagina.concluir_tarefas()

        comecou, liberar = threading.Event(), threading.Event()
        original = db.alterar_email_verificado

        def alterar_devagar(*args):
            comecou.set()
            liberar.wait(5)
            return original(*args)

        with mock.patch.object(main.database, "alterar_email_verificado", alterar_devagar):
            self.campo(pagina, "Código").value = self.servidor.ultimo_codigo(NOVO)
            self.acionar(pagina, self.botao(pagina, "Confirmar"))
            await asyncio.to_thread(comecou.wait, 5)
            self.assertTrue(self.botao(pagina, "Cancelar").disabled)
            sessao.encerrar()                                            # sai da conta no meio
            self.entrar(pagina, "ana@sino.com", "senha1234")             # outra pessoa entra
            liberar.set()
            await pagina.concluir_tarefas()

        self.assertEqual(self.email_de(self.bia), (NOVO, 1))             # gravado de verdade
        self.assertEqual(sessao.usuario["id"], self.ana)                 # a sessão de Ana não foi tocada
        self.assertNotIn("E-mail alterado com sucesso.", self.textos_visiveis(pagina))
        self.assertFalse([d for d in pagina.dialogos if d.open])

    async def test_cancelar_durante_o_pedido(self):
        pagina, _ = self.abrir_ajustes()
        self.editar(pagina)
        self.servidor.portao = portao = asyncio.Event()
        self.campo(pagina, "Senha atual").value = "senha5678"
        self.campo(pagina, "Novo e-mail").value = NOVO
        self.acionar(pagina, self.botao(pagina, "Enviar código"))
        for _ in range(50):
            await asyncio.sleep(0)
        self.acionar(pagina, self.botao(pagina, "Cancelar"))
        portao.set()
        await pagina.concluir_tarefas()
        self.assertFalse([d for d in pagina.dialogos if d.open])
        self.assertEqual(self.email_de(self.bia), ("bia@sino.com", 0))


if __name__ == "__main__":
    unittest.main()
