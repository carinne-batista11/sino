"""
Etapa 10, Bloco 1 (B1) — nova tentativa depois de uma falha transitória da
gravação local, sem validar o código de novo, e confirmação da exclusão
desativada após uma recusa definitiva.

  * apoio (fluxos_codigo): o que é falha transitória; a gravação pendente
    guarda exatamente a mesma função e os mesmos argumentos (autorização já
    verificada e dados); a nova tentativa não grava de novo se a anterior
    chegou a gravar; `encerrar()` descarta a pendência;
  * camada de dados: `autorizacao_ja_usada`;
  * telas reais (cadastro, alteração de e-mail, recuperação) com o cliente
    real sobre o ServidorFalso: uma única validação do código, os mesmos
    dados na nova tentativa, autorização expirada, falha não transitória,
    saída do fluxo;
  * exclusão: botão desativado após senha alterada; falha com rollback
    permite repetir.

Bancos temporários e páginas falsas; nenhuma janela é aberta.
"""

import io
import sqlite3
import unittest
from contextlib import redirect_stderr
from unittest import mock

import flet as ft

from apoio_banco import TesteComBancoTemporario, db
from test_autorizacoes_locais import INICIO, Relogio, autorizacao
from test_cadastro_codigo_interface import SENHA, BaseCadastro
from test_alterar_email_interface import NOVO, BaseAlteracao
from test_excluir_usuario import SENHA_ANA, TesteDeExclusaoNaInterface, banco_inteiro
from test_recuperacao_interface import NOVA, BaseRecuperacao

import fluxos_codigo as fc  # noqa: E402 -- backend/ entra no caminho pelos módulos de apoio

TRAVADO = sqlite3.OperationalError("database is locked")


def falhar_uma_vez(original, erro=TRAVADO):
    """Substituto da gravação: a 1ª chamada falha (nada gravado); as seguintes chamam a original."""
    chamadas = []

    def gravacao(*args):
        chamadas.append(args)
        if len(chamadas) == 1:
            raise erro
        return original(*args)

    return gravacao, chamadas


def gravar_e_falhar_depois(original):
    """1ª chamada: grava de verdade e só então falha (ex.: erro depois do COMMIT)."""
    chamadas = []

    def gravacao(*args):
        chamadas.append(args)
        resultado = original(*args)
        if len(chamadas) == 1:
            raise TRAVADO
        return resultado

    return gravacao, chamadas


# ======================================================================
#  Apoio compartilhado
# ======================================================================
class TestFalhaTransitoria(unittest.TestCase):
    def test_so_erro_operacional_do_sqlite_e_transitorio(self):
        self.assertTrue(fc.falha_transitoria(sqlite3.OperationalError("database is locked")))
        self.assertTrue(fc.falha_transitoria(sqlite3.OperationalError("disk I/O error")))
        for erro in (sqlite3.IntegrityError("UNIQUE"), sqlite3.DatabaseError("malformed"), ValueError("x"),
                     db.AutorizacaoRecusadaError(), db.AutorizacaoExpiradaError(), db.EmailEmUsoError(),
                     TypeError("x"), RuntimeError("x")):
            with self.subTest(erro=type(erro).__name__):
                self.assertFalse(fc.falha_transitoria(erro))


class TestGravacaoPendente(unittest.IsolatedAsyncioTestCase):
    async def test_falha_transitoria_guarda_a_mesma_gravacao(self):
        controle = fc.ControleOperacao()
        dados = (object(), "Nome", "x@sino.com")

        def gravar(*args):
            raise TRAVADO

        with self.assertRaises(sqlite3.OperationalError), redirect_stderr(io.StringIO()):
            await controle.gravar_com_nova_tentativa(gravar, *dados)
        funcao, args = controle.gravacao_pendente
        self.assertIs(funcao, gravar)
        self.assertEqual(args, dados)
        self.assertTrue(all(a is b for a, b in zip(args, dados)))   # os mesmos objetos

    async def test_recusa_outro_erro_e_sucesso_nao_deixam_pendencia(self):
        for efeito in (db.AutorizacaoExpiradaError(), RuntimeError("bug"), None):
            with self.subTest(efeito=type(efeito).__name__):
                controle = fc.ControleOperacao()
                controle.gravacao_pendente = ("antiga", ())

                def gravar():
                    if efeito is not None:
                        raise efeito
                    return "ok"

                if efeito is None:
                    self.assertEqual(await controle.gravar_com_nova_tentativa(gravar), "ok")
                else:
                    with self.assertRaises(type(efeito)):
                        await controle.gravar_com_nova_tentativa(gravar)
                self.assertIsNone(controle.gravacao_pendente)

    async def test_repetir_usa_os_mesmos_argumentos(self):
        controle = fc.ControleOperacao()
        recebidos = []
        controle.gravacao_pendente = (lambda *a: recebidos.append(a) or "gravado", ("aut", "dado"))
        self.assertEqual(await controle.repetir_gravacao(lambda *a: False), "gravado")
        self.assertEqual(recebidos, [("aut", "dado")])
        self.assertIsNone(controle.gravacao_pendente)

    async def test_repetir_nao_grava_se_a_anterior_ja_gravou(self):
        controle = fc.ControleOperacao()
        funcao = mock.Mock()
        controle.gravacao_pendente = (funcao, ("aut", "dado"))
        lidos = []
        self.assertIsNone(await controle.repetir_gravacao(lambda *a: lidos.append(a) or True))
        funcao.assert_not_called()
        self.assertEqual(lidos, [("aut", "dado")])
        self.assertIsNone(controle.gravacao_pendente)

    async def test_falha_ao_conferir_o_uso(self):
        # Transitória: a pendência continua; outra falha: é descartada.
        for erro, mantem in ((TRAVADO, True), (RuntimeError("bug"), False)):
            with self.subTest(erro=type(erro).__name__):
                controle = fc.ControleOperacao()
                controle.gravacao_pendente = (mock.Mock(), ("aut",))

                def conferir(*_):
                    raise erro

                with self.assertRaises(type(erro)):
                    await controle.repetir_gravacao(conferir)
                self.assertEqual(controle.gravacao_pendente is not None, mantem)

    async def test_encerrar_descarta_a_pendencia(self):
        controle = fc.ControleOperacao()
        controle.gravacao_pendente = (mock.Mock(), ("aut",))
        controle.encerrar()
        self.assertIsNone(controle.gravacao_pendente)


class TestAutorizacaoJaUsada(TesteComBancoTemporario):
    def test_antes_e_depois_de_consumir(self):
        aut = autorizacao("cadastro", "carla@sino.com")
        self.assertFalse(db.autorizacao_ja_usada(aut))
        db.concluir_cadastro(aut, "Carla", "carla@sino.com", db.hash_de_nova_senha("senhaforte1"),
                             relogio=Relogio(INICIO))
        self.assertTrue(db.autorizacao_ja_usada(aut))

    def test_jti_fora_do_formato_ou_nao_usado(self):
        for jti in (None, 123, "", "curto", "A" * 21 + "B", "A" * 21 + "w"):  # o último: formato válido, sem uso
            with self.subTest(jti=jti):
                self.assertFalse(db.autorizacao_ja_usada(mock.Mock(jti=jti)))


# ======================================================================
#  Cadastro
# ======================================================================
class TestCadastro(BaseCadastro):
    def ate_a_falha(self, pagina, substituto):
        self.ate_o_codigo(pagina)
        with mock.patch.object(main_database(), "concluir_cadastro", substituto), \
                redirect_stderr(io.StringIO()) as terminal:
            self.confirmar(pagina, self.servidor.ultimo_codigo("carla@sino.com"))
            pagina.executar_pendentes()
        return terminal.getvalue()

    def tentar(self, pagina, substituto):
        with mock.patch.object(main_database(), "concluir_cadastro", substituto), redirect_stderr(io.StringIO()):
            self.acionar(pagina, self.botao(pagina, "Tentar novamente"))
            pagina.executar_pendentes()

    def test_nova_tentativa_grava_com_a_mesma_autorizacao_sem_validar_de_novo(self):
        pagina, _ = self.abrir_cadastro()
        substituto, chamadas = falhar_uma_vez(db.concluir_cadastro)
        terminal = self.ate_a_falha(pagina, substituto)
        self.assertIsNone(self.usuario())
        self.assertEqual(self.autorizacoes_usadas(), 0)
        self.assertIn(fc.MENSAGEM_NOVA_TENTATIVA, self.textos_visiveis(pagina))
        self.assertIn("OperationalError", terminal)
        self.assertNotIn("carla", terminal.lower())
        self.assertTrue(self.campo(pagina, "Código").disabled)
        self.assertFalse(reenvio_de(self, pagina).visible)
        validacoes = len(self.servidor.validacoes)

        self.tentar(pagina, substituto)
        self.assertEqual(len(self.servidor.validacoes), validacoes)        # o código não é validado de novo
        self.assertEqual(len(chamadas), 2)
        self.assertTrue(all(a is b for a, b in zip(chamadas[0], chamadas[1])))  # mesma autorização e dados
        self.assertEqual(self.usuario()[1:], ("Carla@Sino.com", 1))
        self.assertEqual(self.autorizacoes_usadas(), 1)
        self.assertIn("Conta criada com sucesso! Faça login para continuar.", self.textos_visiveis(pagina))

    def test_autorizacao_expirada_antes_da_nova_tentativa(self):
        pagina, _ = self.abrir_cadastro()
        substituto, chamadas = falhar_uma_vez(db.concluir_cadastro)
        self.ate_a_falha(pagina, substituto)
        self.relogio.avancar(3600)
        self.tentar(pagina, substituto)
        self.assertEqual(len(chamadas), 2)                                  # a camada de dados recusou
        self.assertIsNone(self.usuario())
        self.assertEqual(self.autorizacoes_usadas(), 0)
        self.assertIn("O código expirou. Solicite um novo código.", self.textos_visiveis(pagina))
        self.assertFalse(self.campo(pagina, "Código").disabled)            # volta ao pedido de código
        self.assertTrue(reenvio_de(self, pagina).visible)
        self.assertTrue(self.botao(pagina, "Confirmar").visible)

    def test_falha_nao_transitoria_nao_oferece_nova_tentativa(self):
        pagina, _ = self.abrir_cadastro()
        substituto, _ = falhar_uma_vez(db.concluir_cadastro, RuntimeError("bug"))
        self.ate_a_falha(pagina, substituto)
        self.assertIn(fc.MENSAGEM_FALHA_GENERICA, self.textos_visiveis(pagina))
        self.assertFalse(any(isinstance(b, ft.Button) and b.content == "Tentar novamente" for b in self.todos(pagina)))
        self.assertIsNone(self.usuario())

    def test_anterior_gravou_e_falhou_depois_nao_grava_de_novo(self):
        pagina, _ = self.abrir_cadastro()
        substituto, chamadas = gravar_e_falhar_depois(db.concluir_cadastro)
        self.ate_a_falha(pagina, substituto)
        self.tentar(pagina, substituto)
        self.assertEqual(len(chamadas), 1)                                  # não repetiu a gravação
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM usuarios WHERE lower(email) = 'carla@sino.com'"),
                         [(1,)])
        self.assertIn("Conta criada com sucesso! Faça login para continuar.", self.textos_visiveis(pagina))

    def test_voltar_descarta_a_nova_tentativa(self):
        pagina, _ = self.abrir_cadastro()
        substituto, chamadas = falhar_uma_vez(db.concluir_cadastro)
        self.ate_a_falha(pagina, substituto)
        tentar_novamente = self.botao(pagina, "Tentar novamente")
        self.acionar(pagina, self.botao(pagina, "Voltar"))
        self.tentar_botao_antigo(pagina, tentar_novamente, substituto)
        self.assertEqual(len(chamadas), 1)
        self.assertIsNone(self.usuario())
        self.assertIn("Crie sua conta", self.textos_visiveis(pagina))

    def tentar_botao_antigo(self, pagina, botao, substituto):
        with mock.patch.object(main_database(), "concluir_cadastro", substituto):
            self.acionar(pagina, botao)
            pagina.executar_pendentes()


def reenvio_de(teste, pagina):
    return next(b for b in teste.todos(pagina) if getattr(b, "data", None) == "reenviar_codigo")


def main_database():
    from test_sessao_tema import main
    return main.database


# ======================================================================
#  Alteração de e-mail
# ======================================================================
class TestAlteracaoDeEmail(BaseAlteracao):
    def ate_a_falha(self, pagina, substituto):
        self.editar(pagina)
        self.pedir(pagina)
        with mock.patch.object(main_database(), "alterar_email_verificado", substituto), \
                redirect_stderr(io.StringIO()):
            self.confirmar(pagina, self.servidor.ultimo_codigo(NOVO))

    def test_nova_tentativa_altera_o_email_sem_validar_de_novo(self):
        pagina, _ = self.abrir_ajustes()
        substituto, chamadas = falhar_uma_vez(db.alterar_email_verificado)
        self.ate_a_falha(pagina, substituto)
        self.assertEqual(self.email_de(self.bia), ("bia@sino.com", 0))
        self.assertIn(fc.MENSAGEM_NOVA_TENTATIVA, self.textos_visiveis(pagina))
        self.assertTrue(self.campo(pagina, "Código").disabled)
        self.assertFalse(reenvio_de(self, pagina).visible)
        validacoes = len(self.servidor.validacoes)

        with mock.patch.object(main_database(), "alterar_email_verificado", substituto):
            self.acionar(pagina, self.botao(pagina, "Tentar novamente"))
            pagina.executar_pendentes()
        self.assertEqual(len(self.servidor.validacoes), validacoes)
        self.assertTrue(all(a is b for a, b in zip(chamadas[0], chamadas[1])))
        self.assertEqual(self.email_de(self.bia), (NOVO, 1))
        self.assertEqual(self.autorizacoes_usadas(), 1)
        self.assertIn("E-mail alterado com sucesso.", self.textos_visiveis(pagina))
        self.assertFalse([d for d in pagina.dialogos if d.open])

    def test_cancelar_descarta_a_nova_tentativa(self):
        pagina, _ = self.abrir_ajustes()
        substituto, chamadas = falhar_uma_vez(db.alterar_email_verificado)
        self.ate_a_falha(pagina, substituto)
        tentar_novamente = self.botao(pagina, "Tentar novamente")
        self.acionar(pagina, self.botao(pagina, "Cancelar"))
        self.assertFalse([d for d in pagina.dialogos if d.open])
        with mock.patch.object(main_database(), "alterar_email_verificado", substituto):
            self.acionar(pagina, tentar_novamente)
            pagina.executar_pendentes()
        self.assertEqual(len(chamadas), 1)
        self.assertEqual(self.email_de(self.bia), ("bia@sino.com", 0))

    def test_autorizacao_expirada_antes_da_nova_tentativa(self):
        pagina, _ = self.abrir_ajustes()
        substituto, _ = falhar_uma_vez(db.alterar_email_verificado)
        self.ate_a_falha(pagina, substituto)
        self.relogio.avancar(3600)
        with mock.patch.object(main_database(), "alterar_email_verificado", substituto):
            self.acionar(pagina, self.botao(pagina, "Tentar novamente"))
            pagina.executar_pendentes()
        self.assertEqual(self.email_de(self.bia), ("bia@sino.com", 0))
        self.assertIn("O código expirou. Solicite um novo código.", self.textos_visiveis(pagina))
        self.assertTrue(reenvio_de(self, pagina).visible)
        self.assertFalse(self.campo(pagina, "Código").disabled)


# ======================================================================
#  Recuperação de senha
# ======================================================================
class TestRecuperacao(BaseRecuperacao):
    def ate_a_falha(self, pagina, substituto):
        self.pedir(pagina, "bia@sino.com")
        self.confirmar(pagina, self.servidor.ultimo_codigo("bia@sino.com"))
        with mock.patch.object(main_database(), "redefinir_senha_por_autorizacao", substituto), \
                redirect_stderr(io.StringIO()):
            self.redefinir(pagina, NOVA)

    def test_nova_tentativa_redefine_com_os_mesmos_dados(self):
        pagina, sessao = self.abrir_recuperacao()
        substituto, chamadas = falhar_uma_vez(db.redefinir_senha_por_autorizacao)
        self.ate_a_falha(pagina, substituto)
        self.assertIn(fc.MENSAGEM_NOVA_TENTATIVA, self.textos_visiveis(pagina))
        self.assertTrue(self.campo(pagina, "Nova senha").disabled)          # mesmos dados na nova tentativa
        self.assertTrue(self.campo(pagina, "Confirmar nova senha").disabled)
        validacoes = len(self.servidor.validacoes)

        with mock.patch.object(main_database(), "redefinir_senha_por_autorizacao", substituto):
            self.acionar(pagina, self.botao(pagina, "Tentar novamente"))
            pagina.executar_pendentes()
        self.assertEqual(len(self.servidor.validacoes), validacoes)
        self.assertEqual(chamadas[1][1:3], ("bia@sino.com", NOVA))
        self.assertIs(chamadas[1][0], chamadas[0][0])
        self.assertIn("Senha redefinida. Entre com a nova senha.", self.textos_visiveis(pagina))
        self.assertIsNotNone(db.verificar_login("bia@sino.com", NOVA))

    def test_falha_nao_transitoria_recomeca(self):
        pagina, _ = self.abrir_recuperacao()
        substituto, _ = falhar_uma_vez(db.redefinir_senha_por_autorizacao, RuntimeError("bug"))
        self.ate_a_falha(pagina, substituto)
        self.assertIn(fc.MENSAGEM_FALHA_GENERICA, self.textos_visiveis(pagina))
        self.assertTrue(self.campo(pagina, "E-mail").visible)               # passo 1
        self.assertFalse(self.campo(pagina, "Nova senha").visible)
        self.assertIsNotNone(db.verificar_login("bia@sino.com", "senha5678"))


# ======================================================================
#  Exclusão de conta
# ======================================================================
class TestConfirmacaoDaExclusao(TesteDeExclusaoNaInterface):
    def test_senha_alterada_desativa_a_confirmacao(self):
        pagina, _ = self.abrir_ajustes()
        dialogo = self.ir_para_confirmacao(pagina)
        self.assertTrue(db.alterar_senha(self.ana, SENHA_ANA, "trocada-123"))
        self.confirmar(pagina, dialogo)
        excluir = self.botao(dialogo, "Excluir conta")
        self.assertTrue(excluir.disabled)
        antes = banco_inteiro(self)
        with mock.patch.object(main_database(), "excluir_usuario") as chamada:
            self.confirmar(pagina, dialogo)          # clique direto no controle desativado
        chamada.assert_not_called()
        self.assertEqual(banco_inteiro(self), antes)
        self.assertFalse(self.botao(dialogo, "Cancelar").disabled)

    def test_conta_inexistente_desativa_a_confirmacao(self):
        pagina, _ = self.abrir_ajustes()
        dialogo = self.ir_para_confirmacao(pagina)
        db.excluir_usuario(db.conferir_senha_para_exclusao(self.ana, SENHA_ANA))
        self.confirmar(pagina, dialogo)
        self.assertTrue(self.botao(dialogo, "Excluir conta").disabled)

    def test_falha_com_rollback_permite_repetir(self):
        pagina, sessao = self.abrir_ajustes()
        dialogo = self.ir_para_confirmacao(pagina)
        substituto, chamadas = falhar_uma_vez(db.excluir_usuario)
        with mock.patch.object(main_database(), "excluir_usuario", substituto):
            self.confirmar(pagina, dialogo)
            self.assertFalse(self.botao(dialogo, "Excluir conta").disabled)
            self.assertEqual(self.consultar("SELECT COUNT(*) FROM usuarios WHERE id = ?", (self.ana,)), [(1,)])
            self.confirmar(pagina, dialogo)
        self.assertEqual(len(chamadas), 2)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM usuarios WHERE id = ?", (self.ana,)), [(0,)])
        self.assertEqual(sessao.usuario, {"id": None, "nome": None})


if __name__ == "__main__":
    unittest.main()
