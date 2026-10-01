"""
fluxos_codigo (Etapa 8): mensagens dos resultados do serviço de códigos e o
ControleOperacao das telas -- cliques repetidos, cancelamento antes da
gravação e gravação protegida (o resultado real é sempre obtido; uma
gravação concluída nunca é tratada como cancelada). Sem Flet, rede ou banco.
"""

import asyncio
import io
import threading
import unittest
from contextlib import redirect_stderr

import apoio_servico  # noqa: F401 -- coloca backend/ no caminho

import fluxos_codigo as fc
import servico_codigos as sc


class TestMensagens(unittest.TestCase):
    def test_pedido(self):
        casos = {
            sc.CodigoSolicitado(): ("Enviamos um código de 6 dígitos para a@b.com.", False),
            sc.Aguarde(segundos=12.2): ("Aguarde 13 s para pedir outro código.", True),
            sc.Aguarde(segundos=0.1): ("Aguarde 1 s para pedir outro código.", True),
            sc.FalhaEnvio(segundos_para_reenvio=60): ("Não foi possível enviar o código. Tente novamente em instantes.", True),
            sc.LimiteExcedido(): ("Limite de pedidos de código atingido. Tente novamente mais tarde.", True),
            sc.SemConexao(): ("Sem conexão com a internet. Verifique sua conexão e tente novamente.", True),
            sc.ServicoIndisponivel(): ("O serviço de confirmação por e-mail não está disponível agora. "
                                       "Tente novamente mais tarde.", True),
            sc.RespostaInvalida(): (fc.MENSAGEM_FALHA_GENERICA, True),
        }
        for resultado, esperado in casos.items():
            with self.subTest(resultado=type(resultado).__name__):
                self.assertEqual(fc.mensagem_do_pedido(resultado, email="a@b.com"), esperado)
        self.assertIsNone(fc.mensagem_do_pedido(sc.OperacaoCancelada()))

    def test_recuperacao_e_sempre_neutra(self):
        self.assertEqual(fc.mensagem_do_pedido(sc.CodigoSolicitado(), email="x@y.z", recuperacao=True),
                         (fc.MENSAGEM_RECUPERACAO_NEUTRA, False))
        self.assertNotIn("x@y.z", fc.MENSAGEM_RECUPERACAO_NEUTRA)

    def test_validacao(self):
        self.assertEqual(fc.mensagem_da_validacao(sc.CodigoInvalido(4)), ("Código incorreto. Restam 4 tentativas.", True))
        self.assertEqual(fc.mensagem_da_validacao(sc.CodigoInvalido(1)), ("Código incorreto. Restam 1 tentativa.", True))
        self.assertEqual(fc.mensagem_da_validacao(sc.CodigoInvalido(0)),
                         ("Código incorreto. Solicite um novo código.", True))
        self.assertEqual(fc.mensagem_da_validacao(sc.DesafioEncerrado())[1], True)
        self.assertEqual(fc.mensagem_da_validacao(sc.SemConexao()), fc.mensagem_do_pedido(sc.SemConexao()))


class OperacaoFalsa:
    def __init__(self):
        self.descartada = False

    def descartar(self):
        self.descartada = True


class TestControleOperacao(unittest.IsolatedAsyncioTestCase):
    async def test_reserva_impede_clique_repetido_e_tela_encerrada(self):
        controle = fc.ControleOperacao()
        self.assertTrue(controle.reservar())
        self.assertFalse(controle.reservar())          # segundo clique antes de a ação começar
        await controle.executar(asyncio.sleep, 0)
        self.assertTrue(controle.reservar())
        controle.ocupado = False
        controle.encerrar()
        self.assertFalse(controle.reservar())

    async def test_encerrar_cancela_acao_antes_da_gravacao_e_descarta_a_operacao(self):
        encerrados = []
        controle = fc.ControleOperacao(ao_encerrar=encerrados.append)
        controle.operacao = OperacaoFalsa()
        evento = asyncio.Event()
        controle.reservar()
        tarefa = asyncio.create_task(controle.executar(evento.wait))
        await asyncio.sleep(0)
        controle.encerrar()
        self.assertIsNone(await tarefa)                 # cancelada e encerrada sem erro
        self.assertTrue(controle.operacao.descartada)
        self.assertFalse(controle.ativo)
        self.assertFalse(controle.ocupado)
        self.assertEqual(encerrados, [controle])
        controle.encerrar()                             # idempotente
        self.assertEqual(encerrados, [controle])

    async def test_leitura_em_thread_pode_ser_abandonada(self):
        controle = fc.ControleOperacao()
        comecou, liberar = threading.Event(), threading.Event()

        def ler_devagar():
            comecou.set()
            liberar.wait(5)

        controle.reservar()
        tarefa = asyncio.create_task(controle.executar(controle.em_thread, ler_devagar))
        await asyncio.to_thread(comecou.wait, 5)
        controle.encerrar()
        self.assertIsNone(await tarefa)
        liberar.set()

    async def test_gravacao_devolve_o_resultado_ou_a_excecao_real(self):
        controle = fc.ControleOperacao()
        self.assertEqual(await controle.gravar(lambda: 42), 42)
        with self.assertRaises(ValueError):
            await controle.gravar(self.falhar)
        self.assertFalse(controle.em_gravacao)

    @staticmethod
    def falhar():
        raise ValueError("falha da gravação")

    async def test_cancelar_durante_a_gravacao_espera_o_resultado_real(self):
        controle = fc.ControleOperacao()
        controle.operacao = OperacaoFalsa()
        comecou, liberar = threading.Event(), threading.Event()
        gravados = []

        def gravar_devagar():
            comecou.set()
            liberar.wait(5)
            gravados.append("gravado")
            return "id-7"

        mostrados = []

        async def acao():
            resultado = await controle.gravar(gravar_devagar)
            mostrados.append(resultado)          # só chega aqui se a tarefa não foi cancelada

        controle.reservar()
        tarefa = asyncio.create_task(controle.executar(acao))
        await asyncio.to_thread(comecou.wait, 5)
        # encerrar() durante a gravação não cancela a tarefa...
        controle.encerrar()
        self.assertFalse(tarefa.cancelled())
        # ...e um cancelamento externo (ex.: fim da sessão) também não perde o resultado.
        tarefa.cancel()
        for _ in range(5):
            await asyncio.sleep(0)                       # só cede a vez ao loop
        self.assertFalse(tarefa.done())                  # ainda esperando a thread
        liberar.set()
        await tarefa
        self.assertEqual(gravados, ["gravado"])
        self.assertEqual(controle.resultado_gravacao, "id-7")
        self.assertEqual(mostrados, [])                  # a tela fechada não é atualizada
        self.assertFalse(controle.em_gravacao)

    async def test_cancelamento_com_falha_na_gravacao_registra_so_o_tipo(self):
        controle = fc.ControleOperacao()
        comecou, liberar = threading.Event(), threading.Event()

        def gravar_e_falhar():
            comecou.set()
            liberar.wait(5)
            raise RuntimeError("detalhe sensível")

        tarefa = asyncio.create_task(controle.gravar(gravar_e_falhar))
        await asyncio.to_thread(comecou.wait, 5)
        tarefa.cancel()
        await asyncio.sleep(0)
        liberar.set()
        saida = io.StringIO()
        with redirect_stderr(saida):
            with self.assertRaises(asyncio.CancelledError):
                await tarefa
        self.assertIsInstance(controle.resultado_gravacao, RuntimeError)
        self.assertIn("(RuntimeError)", saida.getvalue())
        self.assertNotIn("sensível", saida.getvalue())

    async def test_erro_inesperado_antes_da_gravacao_libera_a_tela_so_com_o_tipo(self):
        mostrados = []
        controle = fc.ControleOperacao(ao_falhar=mostrados.append)

        async def acao():
            raise ValueError("pessoa@exemplo.com 123456")

        controle.reservar()
        saida = io.StringIO()
        with redirect_stderr(saida):
            self.assertIsNone(await controle.executar(acao))
        self.assertEqual(mostrados, [(fc.MENSAGEM_FALHA_GENERICA, True)])
        self.assertFalse(controle.ocupado)
        self.assertTrue(controle.reservar())                 # a tela volta a aceitar ações
        self.assertIn("(ValueError)", saida.getvalue())
        self.assertNotIn("pessoa@exemplo.com", saida.getvalue())
        self.assertNotIn("123456", saida.getvalue())

    async def test_erro_na_tela_depois_de_gravar_nao_e_falha_da_operacao(self):
        mostrados = []
        controle = fc.ControleOperacao(ao_falhar=mostrados.append)

        async def acao():
            await controle.gravar(lambda: "id-9")
            raise RuntimeError("tela quebrou com pessoa@exemplo.com")

        controle.reservar()
        saida = io.StringIO()
        with redirect_stderr(saida):
            await controle.executar(acao)
        self.assertEqual(controle.resultado_gravacao, "id-9")
        self.assertEqual(mostrados, [(fc.MENSAGEM_CONCLUIDA_SEM_ATUALIZAR, False)])
        self.assertIn("atualização da tela após gravar (RuntimeError)", saida.getvalue())
        self.assertNotIn("pessoa@exemplo.com", saida.getvalue())

    async def test_tela_inativa_nao_e_atualizada_e_falha_ao_liberar_so_e_registrada(self):
        mostrados = []
        controle = fc.ControleOperacao(ao_falhar=mostrados.append)

        async def encerrar_e_falhar():
            controle.encerrar()
            raise RuntimeError("x")

        controle.reservar()
        with redirect_stderr(io.StringIO()):
            await controle.executar(encerrar_e_falhar)
        self.assertEqual(mostrados, [])

        def liberar_quebrado(_conteudo):
            raise KeyError("segredo")

        outro = fc.ControleOperacao(ao_falhar=liberar_quebrado)

        async def falhar():
            raise RuntimeError("y")

        outro.reservar()
        saida = io.StringIO()
        with redirect_stderr(saida):
            await outro.executar(falhar)
        self.assertIn("liberação da tela após erro (KeyError)", saida.getvalue())
        self.assertNotIn("segredo", saida.getvalue())
        self.assertFalse(outro.ocupado)

    async def test_aguardar_todas_as_gravacoes(self):
        controle = fc.ControleOperacao()
        comecou, liberar = threading.Event(), threading.Event()

        def gravar_devagar():
            comecou.set()
            return liberar.wait(5) and "ok"

        tarefa = asyncio.create_task(controle.gravar(gravar_devagar))
        await asyncio.to_thread(comecou.wait, 5)
        self.assertTrue(fc._GRAVACOES)
        espera = asyncio.create_task(fc.aguardar_todas_as_gravacoes())
        for _ in range(5):
            await asyncio.sleep(0)
        self.assertFalse(espera.done())
        liberar.set()
        await espera
        self.assertEqual(await tarefa, "ok")


if __name__ == "__main__":
    unittest.main()
