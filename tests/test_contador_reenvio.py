"""
Etapa 10, Bloco 3 — campos bloqueados durante o envio (B3) e contador do
reenvio ("Reenviar código em N s").

  * ContadorReenvio (fluxos_codigo): rótulo, referência em
    `segundos_para_reenvio`, tique até o próximo segundo inteiro, parada ao
    sair da tela, no fechamento e ao reiniciar, sem atualizar controles
    antigos. Relógio controlado: nenhuma espera real;
  * telas reais (cadastro, recuperação, alteração de e-mail) com o cliente
    real sobre o ServidorFalso: campos capturados desativados durante o
    envio e reativados no desfecho; Voltar/Cancelar e links que cancelam
    continuam ativos; reenvio desativado durante a espera e o envio; recusa
    do serviço respeitada com o contador em zero; nada de reenvio no modo
    "Tentar novamente" (Bloco 1).
"""

import asyncio
import io
import unittest
from contextlib import redirect_stderr
from unittest import mock

import flet as ft

from apoio_banco import db
from apoio_interface_codigos import iso
from apoio_servico import Esperas, resposta
from test_alterar_email_interface import NOVO, BaseAlteracao
from test_cadastro_codigo_interface import BaseCadastro
from test_nova_tentativa import falhar_uma_vez, main_database
from test_recuperacao_interface import BaseRecuperacao

import fluxos_codigo as fc  # noqa: E402 -- backend/ entra no caminho pelos módulos de apoio
import servico_codigos as sc  # noqa: E402


class OperacaoFalsa:
    def __init__(self, relogio, segundos):
        self.limite = relogio() + segundos

    def segundos_para_reenvio(self, agora):
        return max(0.0, self.limite - agora)


class RelogioFalso:
    def __init__(self):
        self.agora = 1000.0

    def __call__(self):
        return self.agora


class ControleFalso:
    def __init__(self):
        self.ativo = True
        self.fechando = False


class PassoManual:
    """Espera do contador que só termina quando o teste libera (e então avança o relógio)."""

    def __init__(self, relogio):
        self.relogio = relogio
        self.liberar = asyncio.Event()
        self.pedidas = []

    async def __call__(self, segundos):
        self.pedidas.append(segundos)
        await self.liberar.wait()
        self.liberar.clear()
        self.relogio.agora += segundos


async def ate(condicao, limite_s=5):
    """Espera curta (threads reais de hash/leitura), nunca o intervalo de reenvio."""
    for _ in range(int(limite_s / 0.01)):
        if condicao():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condição não atingida")


def reenvio(teste, pagina):
    return next(b for b in teste.todos(pagina) if getattr(b, "data", None) == "reenviar_codigo")


# ======================================================================
#  ContadorReenvio
# ======================================================================
class TestTexto(unittest.TestCase):
    def test_rotulos(self):
        self.assertEqual(fc.texto_reenvio(0), "Reenviar código")
        self.assertEqual(fc.texto_reenvio(-1), "Reenviar código")
        self.assertEqual(fc.texto_reenvio(60), "Reenviar código em 60 s")
        self.assertEqual(fc.texto_reenvio(59.2), "Reenviar código em 60 s")
        self.assertEqual(fc.texto_reenvio(0.1), "Reenviar código em 1 s")


class TestContador(unittest.IsolatedAsyncioTestCase):
    def novo(self, esperar="avanca"):
        self.relogio, self.controle, self.mostrados = RelogioFalso(), ControleFalso(), []

        async def avanca(segundos):
            self.relogio.agora += segundos

        espera = avanca if esperar == "avanca" else esperar
        return fc.ContadorReenvio(self.controle, self.relogio, espera, self.mostrados.append)

    async def test_conta_a_partir_de_segundos_para_reenvio_ate_zero(self):
        contador = self.novo()
        operacao = OperacaoFalsa(self.relogio, 3.4)
        self.assertTrue(contador.iniciar(operacao))
        await contador.rodar(contador.geracao)
        rotulos = [fc.texto_reenvio(s) for s in self.mostrados]
        self.assertEqual(rotulos, ["Reenviar código em 4 s", "Reenviar código em 3 s", "Reenviar código em 2 s",
                                   "Reenviar código em 1 s", "Reenviar código"])
        self.assertAlmostEqual(self.relogio.agora, 1003.4)           # esperou só o necessário
        self.assertEqual(contador.restante(), 0)

    async def test_sem_tique_automatico_mostra_uma_vez(self):
        contador = self.novo(esperar=None)
        self.assertFalse(contador.iniciar(OperacaoFalsa(self.relogio, 60)))
        self.assertEqual(self.mostrados, [60])
        self.relogio.agora += 60
        self.assertEqual(contador.restante(), 0)                       # a guarda do clique lê ao vivo

    async def test_sem_espera_nao_roda(self):
        contador = self.novo()
        self.assertFalse(contador.iniciar(OperacaoFalsa(self.relogio, 0)))
        self.assertEqual(self.mostrados, [0])

    async def test_para_ao_sair_da_tela_sem_atualizar_controles_antigos(self):
        for motivo in ("tela", "fechamento", "parar", "reiniciar"):
            with self.subTest(motivo=motivo):
                relogio = RelogioFalso()
                passo = PassoManual(relogio)
                contador = self.novo(esperar=passo)
                contador._relogio = relogio
                contador.iniciar(OperacaoFalsa(relogio, 60))
                tarefa = asyncio.create_task(contador.rodar(contador.geracao))
                await asyncio.sleep(0)
                antes = list(self.mostrados)
                if motivo == "tela":
                    self.controle.ativo = False
                elif motivo == "fechamento":
                    self.controle.fechando = True
                elif motivo == "parar":
                    contador.parar()
                else:
                    contador.iniciar(OperacaoFalsa(relogio, 30))
                    antes = list(self.mostrados)
                passo.liberar.set()
                await asyncio.wait_for(tarefa, 2)                     # termina (falha, não trava, se regredir)
                self.assertEqual(self.mostrados, antes)               # nada depois da parada
                self.assertTrue(tarefa.done())

    async def test_mostrar_nao_toca_tela_inativa(self):
        contador = self.novo()
        contador.iniciar(OperacaoFalsa(self.relogio, 10))
        self.controle.ativo = False
        contador.mostrar()
        self.assertEqual(self.mostrados, [10])


# ======================================================================
#  Cadastro
# ======================================================================
class TestCadastroEnvio(BaseCadastro, unittest.IsolatedAsyncioTestCase):
    def campos(self, pagina):
        return [self.campo(pagina, r) for r in ("Nome completo", "E-mail", "Senha", "Confirmar senha")] + \
            [next(c for c in self.todos(pagina) if isinstance(c, ft.Checkbox))]

    async def enviar_preso(self, pagina):
        self.preencher(pagina)
        self.servidor.portao = portao = asyncio.Event()
        self.criar(pagina)
        await ate(lambda: self.servidor.portao is None)                 # o pedido chegou ao portão
        return portao

    async def test_campos_desativados_durante_o_envio_e_links_ativos(self):
        pagina, _ = self.abrir_cadastro()
        portao = await self.enviar_preso(pagina)
        self.assertTrue(all(c.disabled for c in self.campos(pagina)))
        for rotulo in ("Ler Termos de Uso", "Ler Política de Privacidade", "Já tem conta? Entrar"):
            self.assertFalse(self.botao(pagina, rotulo).disabled)      # cancelam o pedido
        portao.set()
        await pagina.concluir_tarefas()
        self.assertIn("Confirme seu e-mail", self.textos_visiveis(pagina))
        self.acionar(pagina, self.botao(pagina, "Voltar"))
        self.assertFalse(any(c.disabled for c in self.campos(pagina)))  # Voltar reativa

    async def test_falha_do_envio_reativa_os_campos(self):
        pagina, _ = self.abrir_cadastro()
        self.servidor.falhas = [sc.ErroDeConexao("ConnectError")] * 3
        self.preencher(pagina)
        with redirect_stderr(io.StringIO()):
            self.criar(pagina)
            await pagina.concluir_tarefas()
        self.assertFalse(any(c.disabled for c in self.campos(pagina)))
        self.assertIn("Sem conexão com a internet. Verifique sua conexão e tente novamente.",
                      self.textos_visiveis(pagina))

    async def test_trocar_de_modo_durante_o_envio_reativa_os_campos(self):
        pagina, _ = self.abrir_cadastro()
        portao = await self.enviar_preso(pagina)
        self.acionar(pagina, self.botao(pagina, "Já tem conta? Entrar"))
        portao.set()
        await pagina.concluir_tarefas()
        self.assertFalse(self.campo(pagina, "E-mail").disabled)
        self.assertFalse(self.campo(pagina, "Senha").disabled)

    async def test_contador_com_tique_chega_a_zero_e_libera(self):
        esperas = Esperas(self.relogio)
        self.servico.esperar = esperas
        pagina, _ = self.abrir_cadastro()
        self.preencher(pagina)
        self.criar(pagina)
        await pagina.concluir_tarefas()
        self.assertAlmostEqual(sum(esperas.feitas), 60)                 # relógio controlado, sem espera real
        botao = reenvio(self, pagina)
        self.assertEqual(botao.content, "Reenviar código")
        self.assertFalse(botao.disabled)

    async def test_voltar_durante_a_contagem_nao_atualiza_o_botao_antigo(self):
        relogio_passo = PassoManual(RelogioFalso())
        self.servico.esperar = relogio_passo
        pagina, _ = self.abrir_cadastro()
        self.preencher(pagina)
        self.criar(pagina)
        await ate(lambda: relogio_passo.pedidas)                        # contador rodando, preso no tique
        botao = reenvio(self, pagina)
        self.assertEqual(botao.content, "Reenviar código em 60 s")
        self.acionar(pagina, self.botao(pagina, "Voltar"))
        self.relogio.avancar(30)
        relogio_passo.liberar.set()
        await asyncio.wait_for(pagina.concluir_tarefas(), 2)
        self.assertEqual(botao.content, "Reenviar código em 60 s")      # controle antigo intocado


class TestCadastroReenvio(BaseCadastro):
    def test_espera_envio_e_recusa_do_servico_em_zero(self):
        pagina, _ = self.abrir_cadastro()
        self.ate_o_codigo(pagina)
        botao = reenvio(self, pagina)
        self.assertEqual(botao.content, "Reenviar código em 60 s")
        self.assertTrue(botao.disabled)
        self.relogio.avancar(60)
        # O contador chegou a zero, mas o serviço ainda recusa: a recusa vale.
        agora = self.servidor.agora()
        self.servidor.falhas = [resposta(429, {"erro": "aguarde", "reenvio_permitido_em": iso(agora + 20_000),
                                               "agora": iso(agora)})]
        self.acionar(pagina, botao)
        self.assertTrue(botao.disabled)                                 # durante o envio
        self.assertTrue(self.campo(pagina, "Código").disabled)
        pagina.executar_pendentes()
        self.assertIn("Aguarde 20 s para pedir outro código.", self.textos_visiveis(pagina))
        self.assertEqual(botao.content, "Reenviar código em 20 s")      # recomeça pelo prazo do serviço
        self.assertTrue(botao.disabled)
        self.assertFalse(self.campo(pagina, "Código").disabled)

    def test_confirmar_desativa_codigo_e_reenvio(self):
        pagina, _ = self.abrir_cadastro()
        self.ate_o_codigo(pagina)
        self.relogio.avancar(60)
        self.campo(pagina, "Código").value = "000000"
        self.acionar(pagina, self.botao(pagina, "Confirmar"))
        self.assertTrue(self.campo(pagina, "Código").disabled)
        self.assertTrue(reenvio(self, pagina).disabled)
        pagina.executar_pendentes()
        self.assertFalse(self.campo(pagina, "Código").disabled)
        self.assertFalse(reenvio(self, pagina).disabled)                 # sem espera: volta

    def test_codigo_errado_durante_a_espera_nao_libera_o_reenvio(self):
        pagina, _ = self.abrir_cadastro()
        self.ate_o_codigo(pagina)
        self.relogio.avancar(15)
        self.confirmar(pagina, "000000" if self.servidor.ultimo_codigo("carla@sino.com") != "000000" else "111111")
        pagina.executar_pendentes()
        self.assertIn("Código incorreto. Restam 4 tentativas.", self.textos_visiveis(pagina))
        botao = reenvio(self, pagina)
        self.assertEqual(botao.content, "Reenviar código em 45 s")
        self.assertTrue(botao.disabled)

    def test_sem_reenvio_no_modo_tentar_novamente(self):
        pagina, _ = self.abrir_cadastro()
        self.ate_o_codigo(pagina)
        self.relogio.avancar(60)                                        # mesmo sem espera
        substituto, _ = falhar_uma_vez(db.concluir_cadastro)
        with mock.patch.object(main_database(), "concluir_cadastro", substituto), redirect_stderr(io.StringIO()):
            self.confirmar(pagina, self.servidor.ultimo_codigo("carla@sino.com"))
            pagina.executar_pendentes()
        botao = reenvio(self, pagina)
        self.assertFalse(botao.visible)
        self.assertTrue(botao.disabled)
        pedidos = len(self.servidor.pedidos)
        self.acionar(pagina, botao)
        pagina.executar_pendentes()
        self.assertEqual(len(self.servidor.pedidos), pedidos)


# ======================================================================
#  Recuperação e alteração de e-mail
# ======================================================================
class TestRecuperacaoEnvio(BaseRecuperacao, unittest.IsolatedAsyncioTestCase):
    async def test_email_desativado_durante_o_envio_e_voltar_ativo(self):
        pagina, _ = self.abrir_recuperacao()
        self.campo(pagina, "E-mail").value = "bia@sino.com"
        self.servidor.portao = portao = asyncio.Event()
        self.acionar(pagina, self.principal(pagina))
        await ate(lambda: self.servidor.portao is None)
        self.assertTrue(self.campo(pagina, "E-mail").disabled)
        self.assertFalse(self.botao(pagina, "Voltar ao login").disabled)
        portao.set()
        await pagina.concluir_tarefas()
        self.assertFalse(self.campo(pagina, "Código").disabled)
        botao = reenvio(self, pagina)
        self.assertEqual(botao.content, "Reenviar código em 60 s")
        self.assertTrue(botao.disabled)

    async def test_codigo_errado_durante_a_espera_nao_libera_o_reenvio(self):
        pagina, _ = self.abrir_recuperacao()
        self.pedir(pagina, "bia@sino.com")
        await pagina.concluir_tarefas()
        self.relogio.avancar(10)
        self.confirmar(pagina, "000000" if self.servidor.ultimo_codigo("bia@sino.com") != "000000" else "111111")
        await pagina.concluir_tarefas()
        botao = reenvio(self, pagina)
        self.assertEqual(botao.content, "Reenviar código em 50 s")
        self.assertTrue(botao.disabled)

    async def test_passo_da_nova_senha_para_o_contador(self):
        pagina, _ = self.abrir_recuperacao()
        self.pedir(pagina, "bia@sino.com")
        await pagina.concluir_tarefas()
        self.confirmar(pagina, self.servidor.ultimo_codigo("bia@sino.com"))
        await pagina.concluir_tarefas()
        self.assertFalse(reenvio(self, pagina).visible)
        botao = reenvio(self, pagina)
        conteudo = botao.content
        self.relogio.avancar(60)
        self.assertEqual(botao.content, conteudo)                       # parado: nada é redesenhado


class TestAlteracaoEnvio(BaseAlteracao, unittest.IsolatedAsyncioTestCase):
    async def test_senha_e_email_desativados_durante_o_envio_e_cancelar_ativo(self):
        pagina, _ = self.abrir_ajustes()
        self.editar(pagina)
        self.campo(pagina, "Senha atual").value = "senha5678"
        self.campo(pagina, "Novo e-mail").value = NOVO
        self.servidor.portao = portao = asyncio.Event()
        self.acionar(pagina, self.botao(pagina, "Enviar código"))
        await ate(lambda: self.servidor.portao is None)
        self.assertTrue(self.campo(pagina, "Senha atual").disabled)
        self.assertTrue(self.campo(pagina, "Novo e-mail").disabled)
        self.assertFalse(self.botao(pagina, "Cancelar").disabled)
        portao.set()
        await pagina.concluir_tarefas()
        self.assertFalse(self.campo(pagina, "Código").disabled)
        botao = reenvio(self, pagina)
        self.assertEqual(botao.content, "Reenviar código em 60 s")
        self.assertTrue(botao.disabled)

    async def test_cancelar_durante_a_contagem_nao_atualiza_o_dialogo_antigo(self):
        passo = PassoManual(RelogioFalso())
        self.servico.esperar = passo
        pagina, _ = self.abrir_ajustes()
        self.editar(pagina)
        self.campo(pagina, "Senha atual").value = "senha5678"
        self.campo(pagina, "Novo e-mail").value = NOVO
        self.acionar(pagina, self.botao(pagina, "Enviar código"))
        await ate(lambda: passo.pedidas)                                # contador rodando, preso no tique
        botao = reenvio(self, pagina)
        self.assertEqual(botao.content, "Reenviar código em 60 s")
        self.acionar(pagina, self.botao(pagina, "Cancelar"))
        self.relogio.avancar(30)
        passo.liberar.set()
        await asyncio.wait_for(pagina.concluir_tarefas(), 2)
        self.assertEqual(botao.content, "Reenviar código em 60 s")


if __name__ == "__main__":
    unittest.main()
