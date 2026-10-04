"""
Etapa 10, Bloco 2 — fechamento seguro da janela (fluxos_codigo.Fechamento
e a ligação em main.py com `prevent_close`).

Cobre só o comportamento novo: fechar na hora sem gravação; com gravação,
aviso, janela aberta e espera sem tempo limite antes do destroy(); falha da
gravação; falha do aviso (não pula a espera); falha da própria espera
(fecha e registra o limite); pedidos repetidos (X várias vezes, fim de
sessão) com uma única rotina; nenhuma ação ou gravação nova depois que o
fechamento começa. Bancos temporários e páginas falsas; nenhuma janela.
"""

import asyncio
import io
import threading
import unittest
from contextlib import redirect_stderr
from unittest import mock

import flet as ft

from test_cadastro_codigo_interface import TestCadastroCancelamento

import fluxos_codigo as fc  # noqa: E402 -- backend/ entra no caminho pelos módulos de apoio


class Registro:
    """Fakes do Fechamento que anotam a ordem das chamadas."""

    def __init__(self, avisar_falha=None):
        self.ordem = []
        self._avisar_falha = avisar_falha

    def avisar(self):
        self.ordem.append("aviso")
        if self._avisar_falha is not None:
            raise self._avisar_falha

    async def fechar_janela(self):
        self.ordem.append("destroy")

    def encerrar_operacoes(self):
        self.ordem.append("operacoes")

    async def ao_terminar(self):
        self.ordem.append("transporte")

    def fechamento(self):
        return fc.Fechamento(avisar=self.avisar, fechar_janela=self.fechar_janela,
                             encerrar_operacoes=self.encerrar_operacoes, ao_terminar=self.ao_terminar)


class BaseFechamento(unittest.IsolatedAsyncioTestCase):
    async def iniciar_gravacao(self, efeito=None):
        """Gravação real (ControleOperacao.gravar) presa até `liberar`; `efeito`: exceção ao terminar."""
        comecou, liberar = threading.Event(), threading.Event()
        controle = fc.ControleOperacao()
        gravados = []

        def gravar():
            comecou.set()
            liberar.wait(5)
            if efeito is not None:
                raise efeito
            gravados.append("gravado")

        async def acao():
            await controle.gravar(gravar)

        controle.reservar()
        tarefa = asyncio.create_task(controle.executar(acao))
        await asyncio.to_thread(comecou.wait, 5)
        return liberar, tarefa, gravados

    @staticmethod
    async def ceder(vezes=20):
        for _ in range(vezes):
            await asyncio.sleep(0)


class TestSemGravacao(BaseFechamento):
    async def test_fecha_na_hora_sem_aviso(self):
        registro = Registro()
        confirmado = await registro.fechamento().pedir(pela_janela=True)
        self.assertTrue(confirmado)
        self.assertEqual(registro.ordem, ["operacoes", "transporte", "destroy"])

    async def test_fim_de_sessao_nao_fecha_a_janela(self):
        registro = Registro()
        await registro.fechamento().pedir(pela_janela=False)
        self.assertEqual(registro.ordem, ["operacoes", "transporte"])


class TestComGravacao(BaseFechamento):
    async def test_avisa_mantem_aberta_e_so_fecha_depois_da_gravacao(self):
        liberar, tarefa, gravados = await self.iniciar_gravacao()
        registro = Registro()
        rotina = registro.fechamento().pedir(pela_janela=True)
        await self.ceder()
        self.assertFalse(rotina.done())                       # sem tempo limite: espera
        self.assertEqual(registro.ordem, ["operacoes", "aviso"])
        liberar.set()
        self.assertTrue(await rotina)
        await tarefa
        self.assertEqual(gravados, ["gravado"])
        self.assertEqual(registro.ordem, ["operacoes", "aviso", "transporte", "destroy"])

    async def test_falha_da_gravacao_nao_impede_o_fechamento(self):
        liberar, tarefa, _ = await self.iniciar_gravacao(efeito=RuntimeError("segredo@sino.com"))
        registro = Registro()
        terminal = io.StringIO()
        with redirect_stderr(terminal):
            rotina = registro.fechamento().pedir(pela_janela=True)
            await self.ceder()
            liberar.set()
            await rotina
            await tarefa
        self.assertEqual(registro.ordem[-1], "destroy")
        self.assertIn("RuntimeError", terminal.getvalue())
        self.assertNotIn("segredo", terminal.getvalue())

    async def test_falha_do_aviso_so_e_registrada_e_nao_pula_a_espera(self):
        liberar, tarefa, gravados = await self.iniciar_gravacao()
        registro = Registro(avisar_falha=RuntimeError("tela"))
        terminal = io.StringIO()
        with redirect_stderr(terminal):
            rotina = registro.fechamento().pedir(pela_janela=True)
            await self.ceder()
            self.assertFalse(rotina.done())                   # continua esperando
            self.assertNotIn("destroy", registro.ordem)
            liberar.set()
            await rotina
            await tarefa
        self.assertEqual(gravados, ["gravado"])
        self.assertEqual(registro.ordem, ["operacoes", "aviso", "transporte", "destroy"])
        self.assertIn("Sino: falha em aviso de fechamento (RuntimeError).", terminal.getvalue())

    async def test_falha_da_espera_fecha_e_registra_o_limite(self):
        liberar, tarefa, _ = await self.iniciar_gravacao()
        registro = Registro()
        terminal = io.StringIO()

        async def espera_quebrada():
            raise OSError("x")

        with mock.patch.object(fc, "aguardar_todas_as_gravacoes", espera_quebrada), redirect_stderr(terminal):
            confirmado = await registro.fechamento().pedir(pela_janela=True)
        self.assertFalse(confirmado)                          # não afirma que a gravação terminou
        self.assertEqual(registro.ordem[-1], "destroy")
        self.assertIn("espera das gravações no fechamento (OSError)", terminal.getvalue())
        self.assertIn("sem confirmar o fim da gravação", terminal.getvalue())
        liberar.set()
        await tarefa


class TestPedidosRepetidos(BaseFechamento):
    async def test_x_varias_vezes_e_fim_de_sessao_usam_uma_rotina(self):
        liberar, tarefa, _ = await self.iniciar_gravacao()
        registro = Registro()
        fechamento = registro.fechamento()
        primeira = fechamento.pedir(pela_janela=True)
        await self.ceder()
        self.assertIs(fechamento.pedir(pela_janela=True), primeira)
        self.assertIs(fechamento.pedir(pela_janela=False), primeira)
        liberar.set()
        await primeira
        await tarefa
        self.assertIs(fechamento.pedir(pela_janela=True), primeira)   # depois de fechar: nada novo
        await self.ceder()
        self.assertEqual(registro.ordem.count("aviso"), 1)
        self.assertEqual(registro.ordem.count("destroy"), 1)
        self.assertEqual(registro.ordem.count("operacoes"), 1)

    async def test_fim_de_sessao_e_depois_x_fecha_uma_vez(self):
        registro = Registro()
        fechamento = registro.fechamento()
        await fechamento.pedir(pela_janela=False)
        await fechamento.pedir(pela_janela=True)
        await fechamento.pedir(pela_janela=True)
        self.assertEqual(registro.ordem, ["operacoes", "transporte", "destroy"])


class TestBloqueio(BaseFechamento):
    async def test_nenhuma_acao_ou_gravacao_nova_depois_do_inicio(self):
        registro = Registro()
        fechamento = registro.fechamento()
        controle = fc.ControleOperacao(fechamento=fechamento)
        self.assertTrue(controle.reservar())                  # antes: ação permitida (em andamento)
        gravar = mock.Mock()
        mostrados = []

        async def acao():
            await asyncio.sleep(0)
            await controle.gravar(gravar)                     # chega à gravação depois do início
            mostrados.append("tela")

        tarefa = asyncio.create_task(controle.executar(acao))
        await fechamento.pedir(pela_janela=True)
        await tarefa
        gravar.assert_not_called()
        self.assertEqual(mostrados, [])
        novo = fc.ControleOperacao(fechamento=fechamento)
        self.assertFalse(novo.reservar())                     # nada novo começa
        with self.assertRaises(asyncio.CancelledError):
            await novo.gravar(gravar)
        gravar.assert_not_called()


# ======================================================================
#  Ligação em main.py
# ======================================================================
class TestJanelaNoApp(TestCadastroCancelamento):
    def configurar_janela(self, pagina):
        pagina.window.destroy = mock.AsyncMock()
        return pagina.window

    async def fechar(self, janela, tipo=ft.WindowEventType.CLOSE):
        return asyncio.create_task(janela.on_event(mock.Mock(type=tipo)))

    async def test_x_sem_gravacao_fecha_na_hora(self):
        pagina, _ = self.abrir_cadastro()
        janela = self.configurar_janela(pagina)
        self.assertTrue(janela.prevent_close)
        await (await self.fechar(janela, ft.WindowEventType.FOCUS))
        janela.destroy.assert_not_called()                    # outros eventos não fecham
        await (await self.fechar(janela))
        janela.destroy.assert_awaited_once()
        self.assertFalse([d for d in pagina.dialogos if d.open and d.data == "aviso_fechamento"])

    async def test_x_durante_a_gravacao_do_cadastro(self):
        pagina, _ = self.abrir_cadastro()
        janela = self.configurar_janela(pagina)
        liberar = await self.gravacao_segura(pagina)
        primeiro = await self.fechar(janela)
        segundo = await self.fechar(janela)                   # X de novo
        await self.ceder()
        janela.destroy.assert_not_called()
        aviso = [d for d in pagina.dialogos if d.open and d.data == "aviso_fechamento"]
        self.assertEqual(len(aviso), 1)
        self.assertTrue(aviso[0].modal)
        self.assertEqual(aviso[0].actions, [])
        self.assertIn("Salvando… a janela será fechada quando terminar.", self.textos_visiveis(pagina))
        liberar.set()
        await primeiro
        await segundo
        await pagina.concluir_tarefas()
        janela.destroy.assert_awaited_once()
        self.assertEqual(self.usuario()[2], 1)                # a gravação terminou de verdade

    @staticmethod
    async def ceder(vezes=20):
        for _ in range(vezes):
            await asyncio.sleep(0)


if __name__ == "__main__":
    unittest.main()
