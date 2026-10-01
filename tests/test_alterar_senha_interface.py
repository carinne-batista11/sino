"""
ERS v6.0, Etapa 7 (passo 3) — Ajustes > Segurança > Alterar senha (5.34,
RF38; CT81, CT83-CT86): diálogo com senha atual, nova senha e confirmação,
ocultas e com opção de mostrar; Salvar só com os três campos preenchidos;
erros com o diálogo aberto e a sessão intacta; sucesso com campos limpos,
diálogo fechado e usuário conectado. Nenhuma senha aparece em mensagens ou
no terminal. Fluxos reais sobre páginas falsas e bancos temporários.
"""

import io
import sqlite3
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from apoio_banco import db
from test_cores import MINIMO_TEXTO, contraste
from test_sessao_tema import CLARO, ESCURO, TesteDeSessao, ft, main, percorrer
from test_tela_principal import Evento

SENHA_BIA = "senha5678"           # definida em TesteDeSessao
NOVA = "Nova-Senhá#1"             # válida; enviada exatamente como digitada
EMOJI_COMPOSTO = "👩‍💻"


class TesteDeAlterarSenha(TesteDeSessao):
    @staticmethod
    def clicar(pagina, controle):
        controle.on_click(Evento(pagina, controle))

    def abrir_ajustes(self, email="bia@sino.com", senha=SENHA_BIA):
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, email, senha)
        self.abrir_aba(pagina, "Ajustes")
        return pagina, sessao

    def item(self, pagina):
        return next(c for c in self.controles(pagina, ft.Container) if c.data == "abrir_alterar_senha")

    @staticmethod
    def dialogo(pagina):
        abertos = [d for d in pagina.dialogos if d.open]
        return abertos[-1] if abertos else None

    def abrir_dialogo(self, pagina):
        self.clicar(pagina, self.item(pagina))
        dialogo = self.dialogo(pagina)
        self.assertEqual(dialogo.title.value, "Alterar senha")
        return dialogo

    def campos(self, dialogo):
        return {c.label: c for c in percorrer(dialogo) if isinstance(c, ft.TextField)}

    def botao(self, dialogo, rotulo):
        return next(b for b in percorrer(dialogo) if isinstance(b, (ft.Button, ft.TextButton)) and b.content == rotulo)

    @staticmethod
    def digitar(pagina, campo, valor):
        campo.value = valor
        campo.on_change(Evento(pagina, campo))

    def preencher(self, pagina, dialogo, atual, nova, confirmacao=None):
        campos = self.campos(dialogo)
        self.digitar(pagina, campos["Senha atual"], atual)
        self.digitar(pagina, campos["Nova senha"], nova)
        self.digitar(pagina, campos["Confirmar nova senha"], nova if confirmacao is None else confirmacao)

    def salvar(self, pagina, dialogo):
        terminal = io.StringIO()
        with mock.patch.object(main.database, "alterar_senha", wraps=db.alterar_senha) as alterar, \
                redirect_stderr(terminal), redirect_stdout(terminal):
            self.clicar(pagina, self.botao(dialogo, "Salvar"))
        return alterar, terminal.getvalue()

    def erro_visivel(self, dialogo):
        erros = [t for t in percorrer(dialogo) if isinstance(t, ft.Text) and t.visible and t.value
                 and t.color in (CLARO["texto_erro"], ESCURO["texto_erro"])]
        return erros[0].value if erros else None

    def hash_de(self, usuario_id):
        return self.consultar("SELECT senha_hash FROM usuarios WHERE id = ?", (usuario_id,))[0][0]

    def linhas(self):
        return self.consultar("SELECT * FROM usuarios ORDER BY id")

    def aviso_de_sucesso(self, pagina):
        return [c for c in self.controles(pagina, ft.Row)   # a mais interna (pré-ordem)
                if "Senha alterada com sucesso." in [t.value for t in percorrer(c) if isinstance(t, ft.Text)]][-1]

    def assert_recusa(self, pagina, sessao, dialogo, mensagem, chamou_o_banco, senhas):
        antes = self.linhas()
        alterar, terminal = self.salvar(pagina, dialogo)
        self.assertEqual(alterar.called, chamou_o_banco)
        self.assertEqual(self.erro_visivel(dialogo), mensagem)
        self.assertIs(self.dialogo(pagina), dialogo)                         # continua aberto
        self.assertEqual(self.linhas(), antes)                               # nada gravado
        self.assertEqual(sessao.usuario, {"id": self.bia, "nome": "Bia"})     # sessão intacta
        self.assertFalse(self.aviso_de_sucesso(pagina).visible)
        textos = [t.value for t in percorrer(dialogo) if isinstance(t, ft.Text) and t.value]
        for senha in senhas:                                                 # nenhuma senha exposta
            if senha.strip():
                self.assertFalse(any(senha in texto for texto in textos))
                self.assertNotIn(senha, terminal)


class TestSecaoSeguranca(TesteDeAlterarSenha):
    def test_entre_conta_e_aparencia(self):
        pagina, _ = self.abrir_ajustes()
        tela = next(c for c in self.controles(pagina) if getattr(c, "data", None) == "tela_ajustes")
        titulos = [t.value for c in tela.controls[1:] for t in percorrer(c)
                   if isinstance(t, ft.Text) and t.size == 18]
        self.assertEqual(titulos, ["Conta", "Segurança", "Aparência", "Sobre e privacidade", "Conta e sessão"])
        textos = [t.value for t in self.controles(pagina, ft.Text)]
        for esperado in ("Mantenha sua conta protegida.", "Alterar senha", "Defina uma nova senha para sua conta."):
            self.assertIn(esperado, textos)
        self.assertFalse(self.aviso_de_sucesso(pagina).visible)


class TestDialogo(TesteDeAlterarSenha):
    def test_campos_ocultos_com_opcao_de_mostrar_e_ajuda(self):
        pagina, _ = self.abrir_ajustes()
        campos = self.campos(self.abrir_dialogo(pagina))
        self.assertEqual(list(campos), ["Senha atual", "Nova senha", "Confirmar nova senha"])
        for campo in campos.values():
            self.assertTrue(campo.password)
            self.assertTrue(campo.can_reveal_password)
            self.assertFalse(campo.value)
            self.assertIsNone(campo.max_length)
        self.assertEqual(campos["Nova senha"].helper, "Mínimo de 8 caracteres")
        self.assertIsNone(campos["Senha atual"].helper)

    def test_salvar_so_com_os_tres_campos_preenchidos(self):
        pagina, _ = self.abrir_ajustes()
        dialogo = self.abrir_dialogo(pagina)
        campos, salvar = self.campos(dialogo), self.botao(dialogo, "Salvar")
        self.assertTrue(salvar.disabled)
        self.digitar(pagina, campos["Senha atual"], SENHA_BIA)
        self.assertTrue(salvar.disabled)
        self.digitar(pagina, campos["Nova senha"], "nova-senha")
        self.assertTrue(salvar.disabled)
        self.digitar(pagina, campos["Confirmar nova senha"], "nova-senha")
        self.assertFalse(salvar.disabled)
        self.assertEqual(salvar.bgcolor, CLARO["acao_primaria"])
        self.digitar(pagina, campos["Senha atual"], "")
        self.assertTrue(salvar.disabled)
        self.assertEqual(salvar.bgcolor, CLARO["botao_desabilitado_fundo"])
        self.digitar(pagina, campos["Senha atual"], " ")                    # espaço conta como preenchido
        self.assertFalse(salvar.disabled)
        with mock.patch.object(main.database, "alterar_senha") as alterar:
            self.digitar(pagina, campos["Nova senha"], "")
            self.clicar(pagina, salvar)                                     # desabilitado: nada acontece
        alterar.assert_not_called()


class TestErros(TesteDeAlterarSenha):
    def test_ct84_confirmacao_diferente(self):
        pagina, sessao = self.abrir_ajustes()
        dialogo = self.abrir_dialogo(pagina)
        self.preencher(pagina, dialogo, SENHA_BIA, "nova-senha-1", "nova-senha-2")
        self.assert_recusa(pagina, sessao, dialogo, "A confirmação não confere com a nova senha.", False,
                           [SENHA_BIA, "nova-senha-1", "nova-senha-2"])

    def test_ct81_nova_senha_curta(self):
        pagina, sessao = self.abrir_ajustes()
        dialogo = self.abrir_dialogo(pagina)
        self.preencher(pagina, dialogo, SENHA_BIA, "abcdef" + EMOJI_COMPOSTO)   # 7 percebidos
        self.assert_recusa(pagina, sessao, dialogo, "A senha deve ter pelo menos 8 caracteres.", False, [SENHA_BIA])

    def test_nova_senha_com_espacos(self):
        for nova in (" " * 10, " nova-senha", "nova-senha ", "nova senha1", "nova\tsenha1", "nova\nsenha1"):
            with self.subTest(nova=repr(nova)):
                pagina, sessao = self.abrir_ajustes()
                dialogo = self.abrir_dialogo(pagina)
                self.preencher(pagina, dialogo, SENHA_BIA, nova)
                self.assert_recusa(pagina, sessao, dialogo, "A senha não pode conter espaços.", False,
                                   [SENHA_BIA, nova])

    def test_senha_atual_antiga_com_espacos_e_substituida(self):
        antiga = "  senha antiga  "
        self.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (db._gerar_hash_senha(antiga), self.bia))
        pagina, sessao = self.abrir_ajustes(senha=antiga)                   # o login antigo continua valendo
        self.assertEqual(sessao.usuario["id"], self.bia)
        dialogo = self.abrir_dialogo(pagina)
        self.preencher(pagina, dialogo, antiga, NOVA)
        alterar, _ = self.salvar(pagina, dialogo)
        alterar.assert_called_once_with(self.bia, antiga, NOVA)            # a atual vai sem transformação
        self.assertIsNone(self.dialogo(pagina))
        self.assertIsNotNone(db.verificar_login("bia@sino.com", NOVA))
        self.assertIsNone(db.verificar_login("bia@sino.com", antiga))

    def test_ct83_senha_atual_incorreta(self):
        pagina, sessao = self.abrir_ajustes()
        dialogo = self.abrir_dialogo(pagina)
        self.preencher(pagina, dialogo, "senha-errada", "nova-senha-1")
        self.assert_recusa(pagina, sessao, dialogo, "A senha atual está incorreta.", True,
                           ["senha-errada", "nova-senha-1"])

    def test_ct85_nova_igual_a_atual(self):
        pagina, sessao = self.abrir_ajustes()
        dialogo = self.abrir_dialogo(pagina)
        self.preencher(pagina, dialogo, SENHA_BIA, SENHA_BIA)
        self.assert_recusa(pagina, sessao, dialogo, "A nova senha deve ser diferente da atual.", True, [SENHA_BIA])

    def test_usuario_inexistente(self):
        pagina, sessao = self.abrir_ajustes()
        dialogo = self.abrir_dialogo(pagina)
        self.preencher(pagina, dialogo, SENHA_BIA, "nova-senha-1")
        with mock.patch.object(main.database, "alterar_senha", return_value=False):
            self.clicar(pagina, self.botao(dialogo, "Salvar"))
        self.assertEqual(self.erro_visivel(dialogo), "Não encontramos a sua conta. Saia e entre novamente.")
        self.assertIs(self.dialogo(pagina), dialogo)
        self.assertEqual(sessao.usuario["id"], self.bia)

    def test_falha_de_gravacao_sem_senha_no_terminal(self):
        pagina, sessao = self.abrir_ajustes()
        dialogo = self.abrir_dialogo(pagina)
        self.preencher(pagina, dialogo, SENHA_BIA, "nova-senha-1")
        self.executar("CREATE TRIGGER falha_senha BEFORE UPDATE OF senha_hash ON usuarios "
                      "BEGIN SELECT RAISE(ABORT, 'falha simulada'); END")
        self.assert_recusa(pagina, sessao, dialogo, "Não foi possível alterar a senha. Tente novamente.", True,
                           [SENHA_BIA, "nova-senha-1"])

    def test_falha_inesperada_registra_so_o_tipo(self):
        pagina, _ = self.abrir_ajustes()
        dialogo = self.abrir_dialogo(pagina)
        self.preencher(pagina, dialogo, SENHA_BIA, "nova-senha-1")
        terminal = io.StringIO()
        with mock.patch.object(main.database, "alterar_senha",
                               side_effect=sqlite3.OperationalError(f"erro com {SENHA_BIA} nova-senha-1")), \
                redirect_stderr(terminal):
            self.clicar(pagina, self.botao(dialogo, "Salvar"))
        self.assertEqual(terminal.getvalue().strip(), "Sino: falha ao alterar a senha (OperationalError).")
        self.assertEqual(self.erro_visivel(dialogo), "Não foi possível alterar a senha. Tente novamente.")

    def test_erro_some_ao_editar(self):
        pagina, _ = self.abrir_ajustes()
        dialogo = self.abrir_dialogo(pagina)
        self.preencher(pagina, dialogo, SENHA_BIA, "nova-senha-1", "outra")
        self.salvar(pagina, dialogo)
        self.assertIsNotNone(self.erro_visivel(dialogo))
        self.digitar(pagina, self.campos(dialogo)["Confirmar nova senha"], "nova-senha-1")
        self.assertIsNone(self.erro_visivel(dialogo))


class TestCancelar(TesteDeAlterarSenha):
    def test_cancelar_descarta_e_reabre_vazio(self):
        pagina, sessao = self.abrir_ajustes()
        antes = self.linhas()
        dialogo = self.abrir_dialogo(pagina)
        self.preencher(pagina, dialogo, SENHA_BIA, "nova-senha-1")
        campos_antigos = list(self.campos(dialogo).values())
        self.clicar(pagina, self.botao(dialogo, "Cancelar"))
        self.assertIsNone(self.dialogo(pagina))
        self.assertEqual([c.value for c in campos_antigos], ["", "", ""])      # descartados
        self.assertEqual(self.linhas(), antes)
        self.assertEqual(sessao.usuario["id"], self.bia)

        novos = self.campos(self.abrir_dialogo(pagina))
        self.assertTrue(all(not c.value and c.password for c in novos.values()))
        self.assertFalse(set(novos.values()) & set(campos_antigos))           # campos novos, ocultos

    def test_fechar_o_dialogo_descarta(self):
        pagina, _ = self.abrir_ajustes()
        dialogo = self.abrir_dialogo(pagina)
        self.preencher(pagina, dialogo, SENHA_BIA, "nova-senha-1")
        dialogo.on_dismiss(Evento(pagina, dialogo))
        self.assertEqual([c.value for c in self.campos(dialogo).values()], ["", "", ""])


class TestSucesso(TesteDeAlterarSenha):
    def test_ct86_alteracao_valida(self):
        pagina, sessao = self.abrir_ajustes()
        hash_ana = self.hash_de(self.ana)
        dialogo = self.abrir_dialogo(pagina)
        campos = list(self.campos(dialogo).values())
        self.preencher(pagina, dialogo, SENHA_BIA, NOVA)
        alterar, terminal = self.salvar(pagina, dialogo)

        alterar.assert_called_once_with(self.bia, SENHA_BIA, NOVA)            # exatamente como digitada
        self.assertIsNone(self.dialogo(pagina))
        self.assertEqual([c.value for c in campos], ["", "", ""])
        self.assertTrue(self.aviso_de_sucesso(pagina).visible)
        self.assertEqual(sessao.usuario, {"id": self.bia, "nome": "Bia"})     # continua conectada
        self.assertTrue(any(getattr(c, "data", None) == "tela_ajustes" for c in self.controles(pagina)))
        self.assertNotIn(NOVA, terminal)

        self.assertIsNotNone(db.verificar_login("bia@sino.com", NOVA))
        self.assertIsNone(db.verificar_login("bia@sino.com", NOVA.lower()))
        self.assertIsNone(db.verificar_login("bia@sino.com", SENHA_BIA))
        self.assertEqual(self.hash_de(self.ana), hash_ana)                    # outra usuária intacta
        self.assertIsNotNone(db.verificar_login("ana@sino.com", "senha1234"))

    def test_entrar_de_novo_pela_tela_com_a_nova_senha(self):
        pagina, sessao = self.abrir_ajustes()
        dialogo = self.abrir_dialogo(pagina)
        self.preencher(pagina, dialogo, SENHA_BIA, NOVA)
        self.salvar(pagina, dialogo)
        sessao.encerrar()
        self.entrar(pagina, "bia@sino.com", SENHA_BIA)
        self.assertIsNone(sessao.usuario["id"])
        self.entrar(pagina, "bia@sino.com", NOVA)
        self.assertEqual(sessao.usuario["id"], self.bia)

    def test_aviso_some_ao_reabrir(self):
        pagina, _ = self.abrir_ajustes()
        dialogo = self.abrir_dialogo(pagina)
        self.preencher(pagina, dialogo, SENHA_BIA, NOVA)
        self.salvar(pagina, dialogo)
        self.assertTrue(self.aviso_de_sucesso(pagina).visible)
        self.abrir_dialogo(pagina)
        self.assertFalse(self.aviso_de_sucesso(pagina).visible)


class TestLegibilidadeDoDialogo(TesteDeAlterarSenha):
    def test_dois_temas(self):
        for email, senha, paleta in (("bia@sino.com", SENHA_BIA, CLARO), ("ana@sino.com", "senha1234", ESCURO)):
            with self.subTest(tema="claro" if paleta is CLARO else "escuro"):
                pagina, _ = self.abrir_ajustes(email, senha)
                dialogo = self.abrir_dialogo(pagina)
                self.assertEqual(dialogo.bgcolor, paleta["fundo_dialogo"])
                self.assertEqual(dialogo.title.color, paleta["texto_principal"])
                for campo in self.campos(dialogo).values():
                    self.assertEqual(campo.color, paleta["texto_principal"])
                    self.assertEqual(campo.border_color, paleta["borda_campo"])
                    self.assertEqual(campo.label_style.color, paleta["texto_secundario"])
                    self.assertEqual(campo.helper_style.color, paleta["texto_secundario"])
                self.assertEqual(self.botao(dialogo, "Cancelar").style.color, paleta["texto_principal"])
                aviso = next(t for t in percorrer(self.aviso_de_sucesso(pagina)) if isinstance(t, ft.Text))
                self.assertGreaterEqual(contraste(aviso.color, paleta["fundo_card"]), MINIMO_TEXTO)
                if paleta is ESCURO:
                    erro = next(t for t in percorrer(dialogo) if isinstance(t, ft.Text) and not t.visible)
                    self.assertGreaterEqual(contraste(erro.color, paleta["fundo_dialogo"]), MINIMO_TEXTO)


if __name__ == "__main__":
    unittest.main()
