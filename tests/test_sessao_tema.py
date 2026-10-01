"""
ERS v6.0, Etapa 6 (passo 3) — tema integrado à sessão e ao login (5.36,
5.38, P8; CT95-CT97, CT99, CT117): uma Paleta por página (`SessaoSino`),
autenticação sempre em Claro, tema do usuário aplicado após o login, duas
sessões com temas diferentes e a rotina real de logout (`SessaoSino.encerrar`,
a mesma que o botão "Sair da conta" chamará no passo 4).

Páginas falsas sobre bancos temporários v7; nenhuma janela é aberta.
"""

import os
import sys
import unittest
from unittest import mock

import apoio_banco
from apoio_banco import DataFixa, TesteComBancoTemporario, db
from test_tela_principal import Evento, percorrer

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import cores  # noqa: E402
import flet as ft  # noqa: E402
import main  # noqa: E402

CLARO, ESCURO = cores.PALETAS["claro"], cores.PALETAS["escuro"]
MODO_FLET = {"claro": ft.ThemeMode.LIGHT, "escuro": ft.ThemeMode.DARK}


class PaginaFalsa(mock.MagicMock):
    """MagicMock com controles, overlay e pilha de diálogos reais (mesma semântica do Flet)."""

    def configurar(self):
        self.controls = []
        self.overlay = []
        self.width = 1200
        self.on_resize = None
        self.dialogos = []
        self.add.side_effect = lambda *controles: self.controls.extend(controles)
        self.show_dialog.side_effect = self._abrir_dialogo
        self.pop_dialog.side_effect = self._fechar_dialogo
        return self

    def _abrir_dialogo(self, dialogo):
        dialogo.open = True
        self.dialogos.append(dialogo)

    def _fechar_dialogo(self):
        abertos = [d for d in self.dialogos if d.open]
        if not abertos:
            return None
        abertos[-1].open = False
        return abertos[-1]


class TesteDeSessao(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)

        # Captura as SessaoSino criadas por main() sem mudar o seu contrato.
        self.sessoes = []
        classe_original = main.SessaoSino

        def criar_sessao(page):
            sessao = classe_original(page)
            self.sessoes.append(sessao)
            return sessao

        patcher = mock.patch.object(main, "SessaoSino", side_effect=criar_sessao)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.ana = self.criar_usuario(email="ana@sino.com", senha="senha1234", nome="Ana")
        self.bia = self.criar_usuario(email="bia@sino.com", senha="senha5678", nome="Bia")
        db.definir_tema(self.ana, "escuro")

    def tearDown(self):
        # Nenhuma sessão pode ter alterado o tema do módulo (isolamento).
        self.assertEqual(cores.fundo_pagina, CLARO["fundo_pagina"])
        super().tearDown()

    # ---------------------------------------------------------------- auxiliares
    def abrir_app(self):
        pagina = PaginaFalsa().configurar()
        main.main(pagina)
        return pagina, self.sessoes[-1]

    @staticmethod
    def controles(pagina, tipo=None):
        todos = [c for raiz in pagina.controls for c in percorrer(raiz)]
        return [c for c in todos if tipo is None or isinstance(c, tipo)]

    def texto(self, pagina, valor):
        return next(t for t in self.controles(pagina, ft.Text) if t.value == valor)

    def entrar(self, pagina, email, senha):
        campos = {c.label: c for c in self.controles(pagina, ft.TextField)}
        campos["E-mail"].value = email
        campos["Senha"].value = senha
        botao = next(b for b in self.controles(pagina, ft.Button) if b.content == "Entrar")
        botao.on_click(Evento(pagina, botao))

    def abrir_aba(self, pagina, rotulo):
        aba = next(c for c in self.controles(pagina, ft.Container)
                   if c.on_click is not None and any(isinstance(t, ft.Text) and t.value == rotulo
                                                     for t in percorrer(c)))
        aba.on_click(Evento(pagina, aba))

    def assert_tema_da_pagina(self, pagina, sessao, tema):
        paleta = cores.PALETAS[tema]
        self.assertEqual(sessao.cores.tema, tema)
        self.assertEqual(pagina.theme_mode, MODO_FLET[tema])
        self.assertEqual(pagina.bgcolor, paleta["fundo_pagina"])

    def assert_na_tela_de_login_em_claro(self, pagina, sessao):
        self.assert_tema_da_pagina(pagina, sessao, "claro")
        self.assertEqual(self.texto(pagina, "Bem-vindo de volta").color, CLARO["texto_principal"])

    def assert_na_tela_principal_em(self, pagina, tema):
        self.assertEqual(self.texto(pagina, "Olá,").color, cores.PALETAS[tema]["texto_secundario"])
        barra = next(c for c in self.controles(pagina, ft.Container)
                     if isinstance(c.content, ft.Row) and any(
                         isinstance(t, ft.Text) and t.value == "Ajustes" for t in percorrer(c)))
        self.assertEqual(barra.bgcolor, cores.PALETAS[tema]["fundo_card"])


class TestLoginETema(TesteDeSessao):
    def test_abre_em_claro_com_paleta_propria(self):
        pagina, sessao = self.abrir_app()
        self.assertIsInstance(sessao.cores, cores.Paleta)
        self.assert_na_tela_de_login_em_claro(pagina, sessao)
        self.assertEqual(sessao.usuario, {"id": None, "nome": None})

    def test_login_aplica_o_tema_escuro_do_usuario(self):  # CT95/CT96
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "ana@sino.com", "senha1234")
        self.assertEqual(sessao.usuario, {"id": self.ana, "nome": "Ana"})
        self.assert_tema_da_pagina(pagina, sessao, "escuro")
        self.assert_na_tela_principal_em(pagina, "escuro")

    def test_login_de_usuario_em_claro(self):  # CT97
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "bia@sino.com", "senha5678")
        self.assert_tema_da_pagina(pagina, sessao, "claro")
        self.assert_na_tela_principal_em(pagina, "claro")

    def test_login_falho_nao_altera_tema_nem_sessao(self):
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "ana@sino.com", "errada")
        self.assertEqual(sessao.usuario, {"id": None, "nome": None})
        self.assert_na_tela_de_login_em_claro(pagina, sessao)
        self.assertIn("E-mail ou senha incorretos.", [t.value for t in self.controles(pagina, ft.Text)])

    def test_cadastro_permanece_em_claro(self):
        pagina, sessao = self.abrir_app()
        alternar = next(b for b in self.controles(pagina, ft.TextButton) if b.content == "Não tem conta? Criar conta")
        alternar.on_click(Evento(pagina, alternar))
        self.assertEqual(self.texto(pagina, "Crie sua conta").color, CLARO["texto_principal"])
        self.assert_tema_da_pagina(pagina, sessao, "claro")

    def test_tema_invalido_nao_preenche_a_sessao(self):
        pagina, sessao = self.abrir_app()
        with self.assertRaises(cores.TemaInvalidoError):
            sessao.autenticar({"id": self.ana, "nome": "Ana", "email": "ana@sino.com", "tema": "azul"})
        self.assertEqual(sessao.usuario, {"id": None, "nome": None})
        self.assert_tema_da_pagina(pagina, sessao, "claro")


class TestDuasSessoes(TesteDeSessao):
    def test_temas_diferentes_nao_se_misturam(self):
        pagina_a, sessao_a = self.abrir_app()
        pagina_b, sessao_b = self.abrir_app()
        self.assertIsNot(sessao_a.cores, sessao_b.cores)

        self.entrar(pagina_a, "ana@sino.com", "senha1234")   # escuro
        self.entrar(pagina_b, "bia@sino.com", "senha5678")   # claro, depois da troca em A
        self.assert_tema_da_pagina(pagina_a, sessao_a, "escuro")
        self.assert_tema_da_pagina(pagina_b, sessao_b, "claro")
        self.assert_na_tela_principal_em(pagina_a, "escuro")
        self.assert_na_tela_principal_em(pagina_b, "claro")

        # Redesenhar uma tela em B (navegação) continua em Claro; A continua em Escuro.
        self.abrir_aba(pagina_b, "Início")
        self.abrir_aba(pagina_a, "Início")
        self.assert_na_tela_principal_em(pagina_b, "claro")
        self.assert_na_tela_principal_em(pagina_a, "escuro")
        self.assertEqual((sessao_a.usuario["id"], sessao_b.usuario["id"]), (self.ana, self.bia))

    def test_logout_de_uma_sessao_nao_afeta_a_outra(self):
        pagina_a, sessao_a = self.abrir_app()
        pagina_b, sessao_b = self.abrir_app()
        self.entrar(pagina_a, "ana@sino.com", "senha1234")
        self.entrar(pagina_b, "ana@sino.com", "senha1234")
        sessao_a.encerrar()
        self.assert_na_tela_de_login_em_claro(pagina_a, sessao_a)
        self.assert_tema_da_pagina(pagina_b, sessao_b, "escuro")
        self.assertEqual(sessao_b.usuario["id"], self.ana)


class TestLogout(TesteDeSessao):
    def entrar_no_grafico_com_dialogos(self):
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "ana@sino.com", "senha1234")
        self.abrir_aba(pagina, "Gráfico")                 # a tela liga page.on_resize
        self.assertIsNotNone(pagina.on_resize)
        pagina.show_dialog(ft.AlertDialog(title=ft.Text("1")))
        pagina.show_dialog(ft.AlertDialog(title=ft.Text("2")))
        pagina.overlay.append(ft.Text("overlay"))
        return pagina, sessao

    def test_rotina_real_de_logout(self):  # 5.38, CT117
        pagina, sessao = self.entrar_no_grafico_com_dialogos()
        self.assertEqual(sessao.ao_encerrar.__name__, "mostrar_tela_login")

        sessao.encerrar()

        self.assertEqual(sessao.usuario, {"id": None, "nome": None})
        self.assertEqual([d.open for d in pagina.dialogos], [False, False])
        self.assertEqual(pagina.overlay, [])
        self.assertIsNone(pagina.on_resize)
        self.assert_na_tela_de_login_em_claro(pagina, sessao)

    def test_logout_sem_dialogos_abertos(self):
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "bia@sino.com", "senha5678")
        sessao.encerrar()
        self.assert_na_tela_de_login_em_claro(pagina, sessao)

    def test_sair_e_entrar_de_novo_mantem_dados_e_tema(self):  # CT99, CT117
        db.criar_conta_unica(self.ana, "Internet", 100.0, "2026-09-20")
        pagina, sessao = self.entrar_no_grafico_com_dialogos()
        antes = {t: self.consultar(f"SELECT COUNT(*) FROM {t}")[0][0]
                 for t in ("usuarios", "contas", "categorias", "series_recorrencia")}

        sessao.encerrar()
        self.entrar(pagina, "ana@sino.com", "senha1234")

        depois = {t: self.consultar(f"SELECT COUNT(*) FROM {t}")[0][0] for t in antes}
        self.assertEqual(depois, antes)
        self.assertEqual(db.obter_usuario(self.ana)["tema"], "escuro")
        self.assert_tema_da_pagina(pagina, sessao, "escuro")
        self.assert_na_tela_principal_em(pagina, "escuro")
        self.assertIn("Internet", [t.value for t in self.controles(pagina, ft.Text)])


if __name__ == "__main__":
    unittest.main()
