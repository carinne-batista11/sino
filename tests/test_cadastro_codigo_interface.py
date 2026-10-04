"""
Cadastro com confirmação do e-mail por código (ERS v6.0, Etapa 8: RF01,
5.31, 5.32; CT110, CT91, CT113) pela tela real, com o cliente real do serviço
de códigos sobre o ServidorFalso, relógio injetável e bancos temporários.
"""

import asyncio
import io
import threading
import unittest
from contextlib import redirect_stderr
from unittest import mock

import flet as ft

from apoio_banco import db
from apoio_interface_codigos import ComServicoFalso
from apoio_servico import resposta
from test_sessao_tema import TesteDeSessao, main

import fluxos_codigo as fc  # noqa: E402 -- backend/ entra no caminho pelos módulos de apoio
import servico_codigos as sc  # noqa: E402

SENHA = "senhaforte1"


class BaseCadastro(ComServicoFalso, TesteDeSessao):
    def abrir_cadastro(self):
        pagina, sessao = self.abrir_app()
        self.acionar(pagina, self.botao(pagina, "Não tem conta? Criar conta"))
        return pagina, sessao

    def preencher(self, pagina, email="Carla@Sino.com", senha=SENHA, nome="Carla", aceite=True, confirmacao=None):
        self.campo(pagina, "Nome completo").value = nome
        self.campo(pagina, "E-mail").value = email
        self.campo(pagina, "Senha").value = senha
        self.campo(pagina, "Confirmar senha").value = senha if confirmacao is None else confirmacao
        next(c for c in self.todos(pagina) if isinstance(c, ft.Checkbox)).value = aceite

    def criar(self, pagina):
        self.acionar(pagina, self.botao(pagina, "Criar conta"))

    def confirmar(self, pagina, codigo):
        self.campo(pagina, "Código").value = codigo
        self.acionar(pagina, self.botao(pagina, "Confirmar"))

    def ate_o_codigo(self, pagina, **kwargs):
        self.preencher(pagina, **kwargs)
        self.criar(pagina)
        pagina.executar_pendentes()
        self.assertIn("Confirme seu e-mail", self.textos_visiveis(pagina))

    def reenvio(self, pagina):
        return next(b for b in self.todos(pagina) if getattr(b, "data", None) == "reenviar_codigo")

    def usuario(self, email="carla@sino.com"):
        linhas = self.consultar("SELECT id, email, email_verificado FROM usuarios WHERE lower(email) = ?", (email,))
        return linhas[0] if linhas else None


class TestCadastroComCodigo(BaseCadastro):
    def test_fluxo_completo_cria_conta_verificada(self):  # CT110
        pagina, sessao = self.abrir_cadastro()
        campo_senha = self.campo(pagina, "Senha")
        self.ate_o_codigo(pagina)
        self.assertEqual(campo_senha.value, "")                       # a senha não fica no formulário
        self.assertIsNone(self.usuario())                              # nenhuma conta antes do código
        self.assertEqual(self.servidor.pedidos[0]["finalidade"], "cadastro")
        self.assertIn("Enviamos um código de 6 dígitos para Carla@Sino.com. Digite-o abaixo para concluir o cadastro.",
                      self.textos_visiveis(pagina))

        self.confirmar(pagina, self.servidor.ultimo_codigo("carla@sino.com"))
        pagina.executar_pendentes()

        self.assertIn("Conta criada com sucesso! Faça login para continuar.", self.textos_visiveis(pagina))
        self.assertIn("Bem-vindo de volta", self.textos_visiveis(pagina))
        usuario_id, email, verificado = self.usuario()
        self.assertEqual((email, verificado), ("Carla@Sino.com", 1))
        self.assertEqual(len(db.listar_categorias(usuario_id)), len(db.CATEGORIAS_PRE_CRIADAS))
        self.assertEqual(self.autorizacoes_usadas(), 1)
        self.assertIsNotNone(db.verificar_login("carla@sino.com", SENHA))
        self.assertEqual(sessao.usuario, {"id": None, "nome": None})

    def test_recusas_antes_do_pedido_nao_pedem_codigo(self):
        casos = [("ANA@sino.com", "Já existe uma conta com esse e-mail."),
                 ("josé@sino.com", "Informe um e-mail válido."),
                 ("carla@sino.com ", "Informe um e-mail válido.")]
        for email, mensagem in casos:
            with self.subTest(email=repr(email)):
                pagina, _ = self.abrir_cadastro()
                self.preencher(pagina, email=email)
                self.criar(pagina)
                pagina.executar_pendentes()
                self.assertIn(mensagem, self.textos_visiveis(pagina))
                self.assertIn("Crie sua conta", self.textos_visiveis(pagina))
                self.assertFalse(self.botao(pagina, "Criar conta").disabled)
        self.assertEqual(self.servidor.pedidos, [])

    def test_servico_nao_configurado_e_login_offline(self):
        self.servico_configurado = False
        pagina, sessao = self.abrir_cadastro()
        self.preencher(pagina)
        self.criar(pagina)
        self.assertIn(fc.MENSAGEM_NAO_CONFIGURADO, self.textos_visiveis(pagina))
        self.assertIsNone(self.usuario())
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "ana@sino.com", "senha1234")               # login local continua funcionando
        self.assertEqual(sessao.usuario["id"], self.ana)

    def test_falhas_do_servico_mostram_mensagem_e_liberam_o_botao(self):
        casos = [
            ([resposta(503, {"erro": "servico_indisponivel"})], "O serviço de confirmação por e-mail não está disponível agora."),
            ([sc.ErroDeConexao("ConnectError")] * 3, "Sem conexão com a internet."),
            ([resposta(429, {"erro": "limite_excedido"})], "Limite de pedidos de código atingido."),
        ]
        for falhas, inicio in casos:
            with self.subTest(inicio=inicio):
                self.servidor.falhas = list(falhas)
                pagina, _ = self.abrir_cadastro()
                self.preencher(pagina)
                with redirect_stderr(io.StringIO()):
                    self.criar(pagina)
                    pagina.executar_pendentes()
                self.assertTrue(any(t.startswith(inicio) for t in self.textos_visiveis(pagina)))
                self.assertFalse(self.botao(pagina, "Criar conta").disabled)
                self.assertEqual(self.campo(pagina, "Senha").value, SENHA)  # pode tentar de novo
                self.assertIsNone(self.usuario())

    def test_codigo_errado_esgotado_reenvio_e_codigo_anterior(self):  # CT90, CT91, CT113
        pagina, _ = self.abrir_cadastro()
        self.ate_o_codigo(pagina)
        primeiro = self.servidor.ultimo_codigo("carla@sino.com")
        errado = "000000" if primeiro != "000000" else "111111"
        for restantes in (4, 3, 2, 1):
            self.confirmar(pagina, errado)
            pagina.executar_pendentes()
            plural = "tentativa" if restantes == 1 else "tentativas"
            self.assertIn(f"Código incorreto. Restam {restantes} {plural}.", self.textos_visiveis(pagina))
        self.confirmar(pagina, errado)
        pagina.executar_pendentes()
        self.assertIn("Código incorreto. Solicite um novo código.", self.textos_visiveis(pagina))

        # Antes de 60 s (Etapa 10, Bloco 3): contagem no botão, desativado; um
        # clique que chegue mesmo assim não envia nada.
        reenvio = self.reenvio(pagina)
        self.assertTrue(reenvio.content.startswith("Reenviar código em "))
        self.assertTrue(reenvio.disabled)
        pedidos = len(self.servidor.pedidos)
        self.acionar(pagina, reenvio)
        pagina.executar_pendentes()
        self.assertEqual(len(self.servidor.pedidos), pedidos)

        self.relogio.avancar(60)
        self.acionar(pagina, self.reenvio(pagina))
        pagina.executar_pendentes()
        self.assertIn("Enviamos um novo código para Carla@Sino.com.", self.textos_visiveis(pagina))
        novo = self.servidor.ultimo_codigo("carla@sino.com")
        self.assertNotEqual(novo, primeiro)
        self.confirmar(pagina, primeiro)                               # o anterior não vale
        pagina.executar_pendentes()
        self.assertIn("Código incorreto. Restam 4 tentativas.", self.textos_visiveis(pagina))
        self.confirmar(pagina, novo)
        pagina.executar_pendentes()
        self.assertEqual(self.usuario()[2], 1)

    def test_codigo_fora_do_formato_e_prazo_local_vencido(self):
        pagina, _ = self.abrir_cadastro()
        self.ate_o_codigo(pagina)
        self.confirmar(pagina, "12a45")
        self.assertIn(fc.MENSAGEM_CODIGO_FORMATO, self.textos_visiveis(pagina))
        self.relogio.avancar(600)
        self.confirmar(pagina, self.servidor.ultimo_codigo("carla@sino.com"))
        pagina.executar_pendentes()
        self.assertIn("Este código não vale mais. Solicite um novo código.", self.textos_visiveis(pagina))
        self.assertEqual(self.servidor.validacoes, [])                 # nem chegou ao serviço
        self.assertIsNone(self.usuario())

    def test_voltar_mantem_nome_e_email_e_descarta_a_operacao(self):
        pagina, _ = self.abrir_cadastro()
        self.ate_o_codigo(pagina)
        codigo = self.servidor.ultimo_codigo("carla@sino.com")
        self.acionar(pagina, self.botao(pagina, "Voltar"))
        self.assertIn("Crie sua conta", self.textos_visiveis(pagina))
        self.assertEqual((self.campo(pagina, "Nome completo").value, self.campo(pagina, "E-mail").value,
                          self.campo(pagina, "Senha").value), ("Carla", "Carla@Sino.com", ""))
        self.assertFalse(self.botao(pagina, "Criar conta").disabled)
        self.assertIsNone(self.usuario())
        self.assertIsNotNone(codigo)

    def test_email_ocupado_entre_o_pedido_e_a_conclusao(self):
        pagina, _ = self.abrir_cadastro()
        self.ate_o_codigo(pagina)
        self.criar_usuario(email="CARLA@sino.com")                     # outra instalação/conta ocupa o e-mail
        self.confirmar(pagina, self.servidor.ultimo_codigo("carla@sino.com"))
        pagina.executar_pendentes()
        self.assertIn("Já existe uma conta com esse e-mail.", self.textos_visiveis(pagina))
        self.assertEqual(self.autorizacoes_usadas(), 0)

    def test_cliques_repetidos_geram_um_unico_pedido_e_uma_unica_validacao(self):
        pagina, _ = self.abrir_cadastro()
        self.preencher(pagina)
        self.criar(pagina)
        self.criar(pagina)
        pagina.executar_pendentes()
        self.assertEqual(len(self.servidor.pedidos), 1)
        self.campo(pagina, "Código").value = self.servidor.ultimo_codigo("carla@sino.com")
        confirmar = self.botao(pagina, "Confirmar")
        self.acionar(pagina, confirmar)
        self.acionar(pagina, confirmar)
        pagina.executar_pendentes()
        self.assertEqual(len(self.servidor.validacoes), 1)
        self.assertEqual(self.usuario()[2], 1)

    def test_erro_inesperado_antes_da_gravacao_libera_a_etapa(self):
        pagina, _ = self.abrir_cadastro()
        self.ate_o_codigo(pagina)
        codigo = self.servidor.ultimo_codigo("carla@sino.com")
        saida = io.StringIO()
        with mock.patch.object(self.servico.cliente, "validar_codigo",
                               side_effect=RuntimeError(f"carla@sino.com {codigo}")), redirect_stderr(saida):
            self.confirmar(pagina, codigo)
            pagina.executar_pendentes()
        self.assertIn(fc.MENSAGEM_FALHA_GENERICA, self.textos_visiveis(pagina))
        self.assertFalse(self.botao(pagina, "Confirmar").disabled)
        self.assertFalse(self.botao(pagina, "Voltar").disabled)
        self.assertIsNone(self.usuario())
        self.assertIn("(RuntimeError)", saida.getvalue())
        self.assertNotIn("carla@sino.com", saida.getvalue())
        self.assertNotIn(codigo, saida.getvalue())
        self.confirmar(pagina, codigo)                                 # a etapa continua utilizável
        pagina.executar_pendentes()
        self.assertEqual(self.usuario()[2], 1)

    def test_nada_sensivel_no_terminal(self):
        self.servidor.falhas = [sc.ErroDeConexao("ReadTimeout")]
        saida = io.StringIO()
        with redirect_stderr(saida):
            pagina, _ = self.abrir_cadastro()
            self.ate_o_codigo(pagina)
            codigo = self.servidor.ultimo_codigo("carla@sino.com")
            self.confirmar(pagina, "000000" if codigo != "000000" else "111111")
            pagina.executar_pendentes()
            self.confirmar(pagina, codigo)
            pagina.executar_pendentes()
        texto = saida.getvalue()
        for proibido in (SENHA, codigo, "carla@sino.com", "Carla@Sino.com"):
            self.assertNotIn(proibido, texto)


class TestCadastroCancelamento(BaseCadastro, unittest.IsolatedAsyncioTestCase):
    async def test_trocar_para_entrar_durante_o_pedido_cancela_sem_pedir(self):
        pagina, _ = self.abrir_cadastro()
        self.servidor.portao = portao = asyncio.Event()
        self.preencher(pagina)
        self.criar(pagina)
        while not any(not t.done() for t in pagina.tarefas):
            await asyncio.sleep(0)
        for _ in range(20):
            await asyncio.sleep(0)
        self.acionar(pagina, self.botao(pagina, "Já tem conta? Entrar"))
        portao.set()
        await pagina.concluir_tarefas()
        self.assertIn("Bem-vindo de volta", self.textos_visiveis(pagina))
        self.assertNotIn("Confirme seu e-mail", self.textos_visiveis(pagina))
        self.assertIsNone(self.usuario())

    async def test_voltar_durante_a_validacao_cancela_sem_gravar(self):
        pagina, _ = self.abrir_cadastro()
        self.preencher(pagina)
        self.criar(pagina)
        await pagina.concluir_tarefas()
        self.servidor.portao = portao = asyncio.Event()
        self.confirmar(pagina, self.servidor.ultimo_codigo("carla@sino.com"))
        for _ in range(20):
            await asyncio.sleep(0)
        self.acionar(pagina, self.botao(pagina, "Voltar"))
        portao.set()
        await pagina.concluir_tarefas()
        self.assertIn("Crie sua conta", self.textos_visiveis(pagina))
        self.assertIsNone(self.usuario())
        self.assertEqual(self.autorizacoes_usadas(), 0)

    async def gravacao_segura(self, pagina):
        """Começa a confirmação com a gravação local presa até o teste liberar."""
        comecou, liberar = threading.Event(), threading.Event()
        original = db.concluir_cadastro

        def concluir_devagar(*args):
            comecou.set()
            liberar.wait(5)
            return original(*args)

        patcher = mock.patch.object(main.database, "concluir_cadastro", concluir_devagar)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.preencher(pagina)
        self.criar(pagina)
        await pagina.concluir_tarefas()
        self.confirmar(pagina, self.servidor.ultimo_codigo("carla@sino.com"))
        await asyncio.to_thread(comecou.wait, 5)
        return liberar

    async def test_voltar_durante_a_gravacao_e_ignorado_e_o_resultado_real_aparece(self):
        pagina, _ = self.abrir_cadastro()
        liberar = await self.gravacao_segura(pagina)
        voltar = self.botao(pagina, "Voltar")
        self.assertTrue(voltar.disabled)
        self.acionar(pagina, voltar)                                   # mesmo que o clique chegue
        self.assertIn("Salvando…", self.textos_visiveis(pagina))
        liberar.set()
        await pagina.concluir_tarefas()
        self.assertIn("Conta criada com sucesso! Faça login para continuar.", self.textos_visiveis(pagina))
        self.assertEqual(self.usuario()[2], 1)

    async def test_fim_da_sessao_durante_a_gravacao_espera_e_nao_mexe_na_tela(self):
        pagina, _ = self.abrir_cadastro()
        liberar = await self.gravacao_segura(pagina)
        encerramento = asyncio.create_task(pagina.on_disconnect(None))
        for _ in range(20):
            await asyncio.sleep(0)
        self.assertFalse(encerramento.done())                          # espera a gravação real
        liberar.set()
        await encerramento
        await pagina.concluir_tarefas()
        self.assertEqual(self.usuario()[2], 1)                         # gravado
        self.assertNotIn("Conta criada com sucesso! Faça login para continuar.", self.textos_visiveis(pagina))


if __name__ == "__main__":
    unittest.main()
