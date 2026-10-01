"""
ERS v6.0, Etapa 6 (passo 4) — tela Ajustes (8.7, protótipo 12): RF35 (nome),
RF38 (seção Segurança), RF40 (tema), RF41 (documentos), RF42 (sair), com o
e-mail só para leitura e sem as ações das Etapas 8-9. Fluxos reais da interface sobre páginas
falsas e bancos temporários v7; nenhuma janela é aberta.
"""

import io
import sqlite3
import unittest
from contextlib import redirect_stderr
from unittest import mock

from apoio_banco import db
from test_cores import MINIMO_TEXTO, contraste
from test_sessao_tema import CLARO, ESCURO, MODO_FLET, TesteDeSessao, ft, main, percorrer
from test_tela_principal import Evento


class TesteDeAjustes(TesteDeSessao):
    def abrir_ajustes(self, email="bia@sino.com", senha="senha5678"):
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, email, senha)
        self.abrir_aba(pagina, "Ajustes")
        self.assertIsNotNone(self.tela(pagina))
        return pagina, sessao

    def tela(self, pagina):
        return next((c for c in self.controles(pagina) if getattr(c, "data", None) == "tela_ajustes"), None)

    def na_tela(self, pagina, tipo=None):
        return [c for c in percorrer(self.tela(pagina)) if tipo is None or isinstance(c, tipo)]

    def textos_da_tela(self, pagina):
        return [t.value for t in self.na_tela(pagina, ft.Text)]

    @staticmethod
    def clicar(pagina, controle):
        controle.on_click(Evento(pagina, controle))

    @staticmethod
    def dialogo_aberto(pagina):
        abertos = [d for d in pagina.dialogos if d.open]
        return abertos[-1] if abertos else None

    def no_dialogo(self, pagina, tipo):
        return [c for c in percorrer(self.dialogo_aberto(pagina)) if isinstance(c, tipo)]

    def botao_do_dialogo(self, pagina, rotulo):
        return next(b for b in self.no_dialogo(pagina, (ft.Button, ft.TextButton)) if b.content == rotulo)

    def opcao_tema(self, pagina, tema):
        return next(c for c in self.na_tela(pagina, ft.Container) if c.data == f"tema_{tema}")

    def item_sair(self, pagina):
        return next(c for c in self.na_tela(pagina, ft.Container)
                    if c.on_click is not None and "Sair da conta" in [t.value for t in percorrer(c)
                                                                       if isinstance(t, ft.Text)])

    # ---------------------------------------------------------------- nome
    def abrir_dialogo_nome(self, pagina):
        editar = next(b for b in self.na_tela(pagina, ft.OutlinedButton) if b.content == "Editar")
        self.clicar(pagina, editar)
        self.assertIsNotNone(self.dialogo_aberto(pagina))
        return self.no_dialogo(pagina, ft.TextField)[0], self.botao_do_dialogo(pagina, "Salvar")

    @staticmethod
    def digitar(pagina, campo, valor):
        campo.value = valor
        campo.on_change(Evento(pagina, campo))

    def erro_do_dialogo(self, pagina):
        return next(t for t in self.no_dialogo(pagina, ft.Text) if t.color == CLARO["texto_erro"]
                    or t.color == ESCURO["texto_erro"])

    def nome_no_banco(self, usuario_id):
        return self.consultar("SELECT nome FROM usuarios WHERE id = ?", (usuario_id,))[0][0]


class TestTelaAjustes(TesteDeAjustes):
    def test_conteudo_da_etapa_6(self):
        pagina, _ = self.abrir_ajustes()
        textos = self.textos_da_tela(pagina)
        for esperado in ("Ajustes", "Conta", "Nome", "Bia", "E-mail", "bia@sino.com", "Segurança",
                         "Alterar senha", "Aparência",
                         "Tema", "Claro", "Escuro", "Sobre e privacidade", "Termos de Uso",
                         "Política de Privacidade", "Conta e sessão", "Sair da conta"):
            self.assertIn(esperado, textos)
        for ausente in ("Verificado", "Excluir conta"):
            self.assertNotIn(ausente, textos)

    def test_email_tem_editar_proprio_e_conta_antiga_fica_sem_selo(self):
        # Etapa 8: o e-mail ganha o seu Editar (código no novo endereço); a
        # conta antiga de teste não é verificada e não tem selo nem "Verificar".
        pagina, _ = self.abrir_ajustes()
        editar = [b for b in self.na_tela(pagina, ft.OutlinedButton)]
        self.assertEqual([(b.content, b.data) for b in editar], [("Editar", None), ("Editar", "editar_email")])
        self.assertFalse([c for c in self.na_tela(pagina) if getattr(c, "data", None) == "selo_verificado"])
        linha_email = [c for c in self.na_tela(pagina, ft.Row)   # a mais interna (pré-ordem)
                       if "bia@sino.com" in [t.value for t in percorrer(c) if isinstance(t, ft.Text)]][-1]
        self.assertFalse([c for c in percorrer(linha_email)
                          if getattr(c, "on_click", None) is not None])
        self.assertNotIn("Verificar", [t.value for t in self.na_tela(pagina, ft.Text)])

    def test_nenhum_item_clicavel_sem_destino(self):
        pagina, _ = self.abrir_ajustes()
        clicaveis = [c for c in self.na_tela(pagina) if getattr(c, "on_click", None) is not None]
        rotulos = sorted({t.value for c in clicaveis for t in percorrer(c) if isinstance(t, ft.Text)}
                         | {c.content for c in clicaveis if isinstance(c.content, str)})
        self.assertEqual(rotulos, sorted(["Editar", "Alterar senha", "Defina uma nova senha para sua conta.",
                                          "Claro", "Escuro", "Termos de Uso", "Política de Privacidade",
                                          "Sair da conta", "Encerre sua sessão atual. Seus dados serão mantidos."]))

    def test_aba_ajustes_ativa_na_navegacao(self):
        pagina, _ = self.abrir_ajustes()
        rotulo = next(t for t in self.controles(pagina, ft.Text) if t.value == "Ajustes" and t.size == 11)
        self.assertEqual(rotulo.color, CLARO["nav_ativo"])

    def test_layout_centralizado_e_adaptavel(self):
        pagina, _ = self.abrir_ajustes()
        linha = next(c for c in self.controles(pagina, ft.ResponsiveRow))
        self.assertEqual(linha.alignment, ft.MainAxisAlignment.CENTER)
        self.assertEqual(self.tela(pagina).col, {"xs": 12, "md": 10, "xl": 8})

    def test_temas_do_flet_com_a_identidade_verde(self):
        pagina, _ = self.abrir_app()
        for tema_flet, paleta in ((pagina.theme, CLARO), (pagina.dark_theme, ESCURO)):
            self.assertEqual(tema_flet.color_scheme_seed, paleta["acao_primaria"])
            self.assertEqual(tema_flet.color_scheme.primary, paleta["acao_primaria"])
            self.assertEqual(tema_flet.color_scheme.surface, paleta["fundo_card"])
            self.assertEqual(tema_flet.color_scheme.on_surface, paleta["texto_principal"])


class TestEditarNome(TesteDeAjustes):
    def test_nome_salvo(self):  # RF35
        pagina, sessao = self.abrir_ajustes()
        campo, salvar = self.abrir_dialogo_nome(pagina)
        self.digitar(pagina, campo, "  Bia Souza  ")
        self.assertFalse(salvar.disabled)
        self.clicar(pagina, salvar)

        self.assertEqual(self.nome_no_banco(self.bia), "Bia Souza")
        self.assertEqual(sessao.usuario["nome"], "Bia Souza")
        self.assertIsNone(self.dialogo_aberto(pagina))
        self.assertIn("Bia Souza", self.textos_da_tela(pagina))
        self.assertEqual(self.nome_no_banco(self.ana), "Ana")   # outro usuário intacto

        self.abrir_aba(pagina, "Início")
        self.assertIn("Bia Souza", [t.value for t in self.controles(pagina, ft.Text)])

    def test_sessao_recebe_o_nome_devolvido_pelo_banco(self):
        pagina, sessao = self.abrir_ajustes()
        campo, salvar = self.abrir_dialogo_nome(pagina)
        self.digitar(pagina, campo, "Bia Nova")
        with mock.patch.object(main.database, "alterar_nome_usuario", return_value="Bia Gravada"):
            self.clicar(pagina, salvar)
        self.assertEqual(sessao.usuario["nome"], "Bia Gravada")

    def test_cancelar_nao_altera_nada(self):
        pagina, sessao = self.abrir_ajustes()
        campo, _ = self.abrir_dialogo_nome(pagina)
        self.digitar(pagina, campo, "Outro nome")
        self.clicar(pagina, self.botao_do_dialogo(pagina, "Cancelar"))
        self.assertIsNone(self.dialogo_aberto(pagina))
        self.assertEqual(self.nome_no_banco(self.bia), "Bia")
        self.assertEqual(sessao.usuario["nome"], "Bia")

    def test_salvar_desabilitado_sem_mudanca(self):
        pagina, _ = self.abrir_ajustes()
        campo, salvar = self.abrir_dialogo_nome(pagina)
        self.assertTrue(salvar.disabled)
        self.digitar(pagina, campo, "Bia X")
        self.assertFalse(salvar.disabled)
        self.digitar(pagina, campo, "   Bia ")           # normalizado = atual
        self.assertTrue(salvar.disabled)
        self.assertEqual(salvar.bgcolor, CLARO["botao_desabilitado_fundo"])
        with mock.patch.object(main.database, "alterar_nome_usuario") as alterar:
            self.clicar(pagina, salvar)
        alterar.assert_not_called()

    def test_nome_vazio(self):
        pagina, sessao = self.abrir_ajustes()
        campo, salvar = self.abrir_dialogo_nome(pagina)
        self.digitar(pagina, campo, "   ")
        with mock.patch.object(main.database, "alterar_nome_usuario") as alterar:
            self.clicar(pagina, salvar)
        alterar.assert_not_called()
        erro = self.erro_do_dialogo(pagina)
        self.assertTrue(erro.visible)
        self.assertEqual(erro.value, "O nome é obrigatório.")
        self.assertIsNotNone(self.dialogo_aberto(pagina))
        self.assertEqual((self.nome_no_banco(self.bia), sessao.usuario["nome"]), ("Bia", "Bia"))

    def test_limite_por_caracteres_percebidos(self):
        pagina, _ = self.abrir_ajustes()
        campo, salvar = self.abrir_dialogo_nome(pagina)
        self.assertEqual(campo.counter, "3/70")
        self.digitar(pagina, campo, "a" * 69 + "👩‍💻")
        self.assertEqual(campo.counter, "70/70")
        self.digitar(pagina, campo, "a" * 69 + "👩‍💻" + "b")   # 71º caractere: recusado
        self.assertEqual(campo.value, "a" * 69 + "👩‍💻")
        self.clicar(pagina, salvar)
        self.assertEqual(self.nome_no_banco(self.bia), "a" * 69 + "👩‍💻")

    def test_limite_excedido_em_nome_antigo(self):
        antigo = "n" * 75
        self.executar("UPDATE usuarios SET nome = ? WHERE id = ?", (antigo, self.bia))
        pagina, sessao = self.abrir_ajustes()
        campo, salvar = self.abrir_dialogo_nome(pagina)
        self.assertEqual(campo.value, antigo)                # exibido sem corte (P4)
        self.digitar(pagina, campo, "n" * 74)                # reduzir é permitido
        with mock.patch.object(main.database, "alterar_nome_usuario") as alterar:
            self.clicar(pagina, salvar)
        alterar.assert_not_called()
        self.assertIn("70", self.erro_do_dialogo(pagina).value)
        self.assertEqual((self.nome_no_banco(self.bia), sessao.usuario["nome"]), (antigo, antigo))

    def test_usuario_inexistente(self):
        pagina, sessao = self.abrir_ajustes()
        campo, salvar = self.abrir_dialogo_nome(pagina)
        self.digitar(pagina, campo, "Bia Nova")
        with mock.patch.object(main.database, "alterar_nome_usuario", return_value=None):
            self.clicar(pagina, salvar)
        self.assertEqual(self.erro_do_dialogo(pagina).value,
                         "Não encontramos a sua conta. Saia e entre novamente.")
        self.assertIsNotNone(self.dialogo_aberto(pagina))
        self.assertEqual(sessao.usuario["nome"], "Bia")

    def test_falha_de_gravacao_nao_altera_a_sessao(self):
        pagina, sessao = self.abrir_ajustes()
        campo, salvar = self.abrir_dialogo_nome(pagina)
        self.digitar(pagina, campo, "Bia Nova")
        with mock.patch.object(main.database, "alterar_nome_usuario",
                               side_effect=sqlite3.OperationalError("database is locked")), \
                redirect_stderr(io.StringIO()):
            self.clicar(pagina, salvar)
        self.assertEqual(self.erro_do_dialogo(pagina).value, "Não foi possível salvar o nome. Tente novamente.")
        self.assertIsNotNone(self.dialogo_aberto(pagina))
        self.assertEqual((self.nome_no_banco(self.bia), sessao.usuario["nome"]), ("Bia", "Bia"))
        self.assertIn("Bia", self.textos_da_tela(pagina))


class TestTrocarTema(TesteDeAjustes):
    def test_troca_so_depois_de_gravar(self):  # RF40, CT95
        pagina, sessao = self.abrir_ajustes()
        tema_na_gravacao = []
        original = db.definir_tema

        def definir_tema_espiao(usuario_id, tema):
            tema_na_gravacao.append((sessao.cores.tema, pagina.theme_mode))
            return original(usuario_id, tema)

        with mock.patch.object(main.database, "definir_tema", side_effect=definir_tema_espiao):
            self.clicar(pagina, self.opcao_tema(pagina, "escuro"))

        self.assertEqual(tema_na_gravacao, [("claro", MODO_FLET["claro"])])
        self.assertEqual(db.obter_usuario(self.bia)["tema"], "escuro")
        self.assert_tema_da_pagina(pagina, sessao, "escuro")
        titulo = next(t for t in self.na_tela(pagina, ft.Text) if t.value == "Ajustes")
        self.assertEqual(titulo.color, ESCURO["texto_principal"])   # Ajustes redesenhada
        self.assertEqual(self.opcao_tema(pagina, "escuro").border.top.width, 2)
        self.assertEqual(self.nome_no_banco(self.ana), "Ana")
        self.assertEqual(db.obter_usuario(self.ana)["tema"], "escuro")   # a outra usuária não mudou

    def test_voltar_para_claro(self):
        pagina, sessao = self.abrir_ajustes(email="ana@sino.com", senha="senha1234")  # Ana: escuro
        self.clicar(pagina, self.opcao_tema(pagina, "claro"))
        self.assertEqual(db.obter_usuario(self.ana)["tema"], "claro")
        self.assert_tema_da_pagina(pagina, sessao, "claro")

    def test_tema_atual_nao_grava_de_novo(self):
        pagina, _ = self.abrir_ajustes()
        with mock.patch.object(main.database, "definir_tema") as definir:
            self.clicar(pagina, self.opcao_tema(pagina, "claro"))
        definir.assert_not_called()

    def test_falha_preserva_o_tema_e_informa(self):
        for descricao, efeito in (("exceção", {"side_effect": sqlite3.OperationalError("locked")}),
                                  ("usuário inexistente", {"return_value": False})):
            with self.subTest(descricao):
                pagina, sessao = self.abrir_ajustes()
                with mock.patch.object(main.database, "definir_tema", **efeito), redirect_stderr(io.StringIO()):
                    self.clicar(pagina, self.opcao_tema(pagina, "escuro"))
                self.assert_tema_da_pagina(pagina, sessao, "claro")
                self.assertEqual(db.obter_usuario(self.bia)["tema"], "claro")
                aviso = next(t for t in self.na_tela(pagina, ft.Text)
                             if t.value == "Não foi possível salvar o tema. O tema atual foi mantido.")
                self.assertTrue(aviso.visible)
                self.assertEqual(self.opcao_tema(pagina, "claro").border.top.width, 2)


class TestSairDaConta(TesteDeAjustes):
    def abrir_confirmacao(self, pagina):
        self.clicar(pagina, self.item_sair(pagina))
        dialogo = self.dialogo_aberto(pagina)
        self.assertEqual(dialogo.title.value, "Sair da conta?")
        return dialogo

    def test_confirmacao_simples_sem_aparencia_destrutiva(self):
        pagina, _ = self.abrir_ajustes()
        self.abrir_confirmacao(pagina)
        sair = self.botao_do_dialogo(pagina, "Sair")
        self.assertEqual(sair.bgcolor, CLARO["acao_primaria"])
        self.assertNotEqual(sair.bgcolor, CLARO["acao_destrutiva"])
        self.assertEqual([b.content for b in self.no_dialogo(pagina, (ft.Button, ft.TextButton))],
                         ["Cancelar", "Sair"])

    def test_cancelar_mantem_a_sessao(self):
        pagina, sessao = self.abrir_ajustes()
        self.abrir_confirmacao(pagina)
        self.clicar(pagina, self.botao_do_dialogo(pagina, "Cancelar"))
        self.assertIsNone(self.dialogo_aberto(pagina))
        self.assertEqual(sessao.usuario["id"], self.bia)
        self.assertIsNotNone(self.tela(pagina))

    def test_confirmar_chama_a_rotina_real(self):  # RF42, CT99, CT117
        pagina, sessao = self.abrir_ajustes(email="ana@sino.com", senha="senha1234")  # escuro
        self.abrir_confirmacao(pagina)
        with mock.patch.object(sessao, "encerrar", wraps=sessao.encerrar) as encerrar:
            self.clicar(pagina, self.botao_do_dialogo(pagina, "Sair"))
        encerrar.assert_called_once_with()
        self.assertEqual(sessao.usuario, {"id": None, "nome": None})
        self.assertIsNone(self.dialogo_aberto(pagina))
        self.assert_na_tela_de_login_em_claro(pagina, sessao)
        self.assertEqual(db.obter_usuario(self.ana)["tema"], "escuro")

        self.entrar(pagina, "ana@sino.com", "senha1234")
        self.assert_tema_da_pagina(pagina, sessao, "escuro")


class TestLegibilidadeDeAjustes(TesteDeAjustes):
    """Controles novos de Ajustes e dos seus diálogos nos dois temas (RNF09, parcial)."""

    def verificar_textos(self, textos, fundo, paleta):
        for texto in textos:
            with self.subTest(texto=texto.value):
                self.assertIsNotNone(texto.color, "texto sem cor explícita")
                razao = contraste(texto.color, fundo)
                if texto.color == paleta["texto_secundario"] and paleta is CLARO:
                    # Limitação conhecida do Claro original (texto_secundario, 3,61:1).
                    self.assertGreaterEqual(razao, 3.0)
                else:
                    self.assertGreaterEqual(razao, MINIMO_TEXTO, f"{razao:.2f}")

    def test_tela_e_dialogos_nos_dois_temas(self):
        for email, senha, paleta in (("bia@sino.com", "senha5678", CLARO), ("ana@sino.com", "senha1234", ESCURO)):
            with self.subTest(tema="claro" if paleta is CLARO else "escuro"):
                pagina, _ = self.abrir_ajustes(email, senha)
                cabecalho = self.tela(pagina).controls[0]      # título e subtítulo, sobre a página
                textos_cabecalho = [t for t in percorrer(cabecalho) if isinstance(t, ft.Text)]
                textos_cards = [t for t in self.na_tela(pagina, ft.Text) if t not in textos_cabecalho]
                self.assertEqual(len(textos_cabecalho), 2)
                self.verificar_textos(textos_cabecalho, paleta["fundo_pagina"], paleta)
                self.verificar_textos(textos_cards, paleta["fundo_card"], paleta)

                self.abrir_dialogo_nome(pagina)
                dialogo = self.dialogo_aberto(pagina)
                self.assertEqual(dialogo.bgcolor, paleta["fundo_dialogo"])
                campo = self.no_dialogo(pagina, ft.TextField)[0]
                self.assertEqual(campo.color, paleta["texto_principal"])
                self.verificar_textos([dialogo.title], paleta["fundo_dialogo"], paleta)
                cancelar = self.botao_do_dialogo(pagina, "Cancelar")
                self.assertEqual(cancelar.style.color, paleta["texto_principal"])
                self.clicar(pagina, cancelar)

                self.clicar(pagina, self.item_sair(pagina))
                dialogo = self.dialogo_aberto(pagina)
                self.assertEqual(dialogo.bgcolor, paleta["fundo_dialogo"])
                self.verificar_textos([dialogo.title, dialogo.content], paleta["fundo_dialogo"], paleta)
                self.clicar(pagina, self.botao_do_dialogo(pagina, "Cancelar"))


if __name__ == "__main__":
    unittest.main()
