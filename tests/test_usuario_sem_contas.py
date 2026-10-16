"""
ERS v7.0, E7 (M2) — usuário sem contas e mês vazio em Início (5.43, RF05;
CT126, CT127; RNF09; decisões U1–U4).

Usuário sem nenhuma conta, em nenhum mês (calculado pelos dados atuais, sem
marca de primeiro acesso): no lugar de "Suas contas estão em dia!", a
orientação "Registre suas primeiras contas e tenha tudo sob controle.", com
ícone de adicionar na cor de ação e texto na cor principal, sem aparência de
sucesso e sem clique; a lista do mês não mostra "Nenhuma conta neste mês.".
Usuário com contas e mês vazio: tudo como antes. Fluxos reais da interface
sobre páginas falsas e bancos temporários; nenhuma janela é aberta.
"""

import unittest

from apoio_banco import TesteComBancoTemporario, db
from test_cores import MINIMO_TEXTO, contraste
from test_sessao_tema import CLARO, ESCURO, TesteDeSessao, ft, percorrer
from test_tela_principal import Evento

ORIENTACAO = "Registre suas primeiras contas e tenha tudo sob controle."
EM_DIA = "Suas contas estão em dia!"
EM_ATRASO = "Você possui contas em atraso!"
MES_VAZIO = "Nenhuma conta neste mês."
# Hoje fixo (apoio_banco.DataFixa): 15/09/2026; Início abre em Setembro 2026.


class TestUsuarioTemContas(TesteComBancoTemporario):
    """U1 na camada de dados: só leitura, pelos dados atuais, por usuário."""

    def setUp(self):
        super().setUp()
        self.ana = self.criar_usuario(email="ana@sino.com")
        self.bia = self.criar_usuario(email="bia@sino.com")

    def test_zero_uma_e_varias_contas(self):
        self.assertFalse(db.usuario_tem_contas(self.ana))
        primeira = db.criar_conta_unica(self.ana, "Luz", 10.0, "2026-10-05")
        self.assertTrue(db.usuario_tem_contas(self.ana))
        db.criar_serie_recorrente(self.ana, "Escola", 700.0, "2027-01-10", "mensal", data_termino="2027-03")
        self.assertTrue(db.usuario_tem_contas(self.ana))
        db.excluir_conta(primeira)
        self.assertTrue(db.usuario_tem_contas(self.ana))     # a série continua

    def test_isolamento_entre_usuarios(self):
        db.criar_conta_unica(self.ana, "Luz", 10.0, "2026-10-05")
        self.assertEqual((db.usuario_tem_contas(self.ana), db.usuario_tem_contas(self.bia)), (True, False))
        self.assertFalse(db.usuario_tem_contas(999_999))

    def test_volta_a_falso_quando_todas_sao_excluidas(self):
        ids = [db.criar_conta_unica(self.ana, f"Conta {i}", 10.0, "2026-10-05") for i in range(3)]
        for conta_id in ids:
            db.excluir_conta(conta_id)
        self.assertFalse(db.usuario_tem_contas(self.ana))

    def test_nao_grava_nada(self):
        antes = self.consultar("SELECT COUNT(*) FROM contas")
        db.usuario_tem_contas(self.ana)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas"), antes)


class TestInicioSemContas(TesteDeSessao):
    """Bia: tema Claro; Ana: tema Escuro (TesteDeSessao). Ninguém começa com contas."""

    def abrir_inicio(self, email="bia@sino.com", senha="senha5678"):
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, email, senha)
        return pagina, sessao

    def textos(self, pagina):
        return [t.value for t in self.controles(pagina, ft.Text)]

    def orientacao(self, pagina):
        """(linha, ícone, texto) da orientação; None se não estiver na tela."""
        for linha in self.controles(pagina, ft.Row):
            textos = [c for c in linha.controls if isinstance(c, ft.Text) and c.value == ORIENTACAO]
            if textos:
                icone = next(c for c in linha.controls if isinstance(c, ft.Icon))
                return linha, icone, textos[0]
        return None

    def mudar_mes(self, pagina, icone):
        seta = next(b for b in self.controles(pagina, ft.IconButton) if b.icon == icone)
        seta.on_click(Evento(pagina, seta))

    def recarregar_inicio(self, pagina):
        self.abrir_aba(pagina, "Início")

    def assert_orientacao(self, pagina, paleta):
        encontrada = self.orientacao(pagina)
        self.assertIsNotNone(encontrada)
        linha, icone, texto = encontrada
        self.assertEqual((icone.icon, icone.size, icone.color),
                         (ft.Icons.ADD_CIRCLE_OUTLINE, 16, paleta["acao_primaria"]))
        self.assertEqual((texto.value, texto.size, texto.weight, texto.color),
                         (ORIENTACAO, 13, ft.FontWeight.BOLD, paleta["texto_principal"]))
        textos = self.textos(pagina)
        self.assertNotIn(EM_DIA, textos)
        self.assertNotIn(MES_VAZIO, textos)
        self.assertFalse([i for i in self.controles(pagina, ft.Icon) if i.icon == ft.Icons.CHECK_CIRCLE_OUTLINE])

    # CT126 ------------------------------------------------------------------
    def test_ct126_orientacao_no_lugar_do_aviso_de_em_dia(self):
        pagina, _ = self.abrir_inicio()
        self.assert_orientacao(pagina, CLARO)
        textos = self.textos(pagina)
        self.assertEqual(textos[textos.index("Total do mês") + 1], "R$ 0,00")   # total inalterado
        self.assertIn("Setembro 2026", textos)
        self.assertTrue([c for c in self.controles(pagina, ft.Container) if c.data == "nova_conta"])  # "+" mantido

    def test_u4_orientacao_sem_acao_de_clique(self):
        pagina, _ = self.abrir_inicio()
        linha, _, _ = self.orientacao(pagina)
        self.assertFalse([c for c in percorrer(linha) if getattr(c, "on_click", None) is not None])
        bloco = next(c for c in self.controles(pagina, ft.Container) if c.content is linha)
        self.assertIsNone(bloco.on_click)

    def test_navegacao_entre_meses_mantem_a_orientacao(self):
        pagina, _ = self.abrir_inicio()
        for icone, mes in ((ft.Icons.CHEVRON_RIGHT, "Outubro 2026"), (ft.Icons.CHEVRON_RIGHT, "Novembro 2026"),
                           (ft.Icons.CHEVRON_LEFT, "Outubro 2026")):
            self.mudar_mes(pagina, icone)
            self.assertIn(mes, self.textos(pagina))
            self.assert_orientacao(pagina, CLARO)

    def test_tema_escuro(self):
        pagina, _ = self.abrir_inicio("ana@sino.com", "senha1234")
        self.assert_orientacao(pagina, ESCURO)

    def test_contraste_nos_dois_temas(self):  # RNF09
        for tema, paleta in (("claro", CLARO), ("escuro", ESCURO)):
            with self.subTest(tema=tema):
                self.assertGreaterEqual(contraste(paleta["texto_principal"], paleta["fundo_pagina"]), MINIMO_TEXTO)
                self.assertGreaterEqual(contraste(paleta["acao_primaria"], paleta["fundo_pagina"]), 3.0)

    # U1 dinâmico -------------------------------------------------------------
    def test_primeira_conta_tira_a_orientacao_e_excluir_todas_devolve(self):
        pagina, _ = self.abrir_inicio()
        self.assertIsNotNone(self.orientacao(pagina))

        conta_id = db.criar_conta_unica(self.bia, "Luz", 10.0, "2026-09-20")
        self.recarregar_inicio(pagina)
        self.assertIsNone(self.orientacao(pagina))
        self.assertIn(EM_DIA, self.textos(pagina))
        self.assertIn("Luz", self.textos(pagina))

        db.excluir_conta(conta_id)
        self.recarregar_inicio(pagina)
        self.assert_orientacao(pagina, CLARO)

    def test_serie_recorrente_em_outro_mes_nao_e_usuario_sem_contas(self):
        db.criar_serie_recorrente(self.bia, "Escola", 700.0, "2027-01-10", "mensal", data_termino="2027-03")
        pagina, _ = self.abrir_inicio()                       # setembro/2026: vazio
        self.assertIsNone(self.orientacao(pagina))
        self.assertIn(MES_VAZIO, self.textos(pagina))
        self.assertIn(EM_DIA, self.textos(pagina))

    # CT127 / U3 -------------------------------------------------------------
    def test_ct127_contas_so_em_outro_mes(self):
        db.criar_conta_unica(self.bia, "Luz", 10.0, "2026-11-05")
        pagina, _ = self.abrir_inicio()                       # setembro/2026: vazio
        self.assertIsNone(self.orientacao(pagina))
        textos = self.textos(pagina)
        self.assertIn(MES_VAZIO, textos)
        self.assertIn(EM_DIA, textos)
        self.mudar_mes(pagina, ft.Icons.CHEVRON_RIGHT)
        self.mudar_mes(pagina, ft.Icons.CHEVRON_RIGHT)        # novembro: a conta aparece
        self.assertIn("Luz", self.textos(pagina))
        self.assertNotIn(MES_VAZIO, self.textos(pagina))
        self.assertIsNone(self.orientacao(pagina))

    def test_contas_atrasadas_mantem_o_aviso_de_atraso(self):
        db.criar_conta_unica(self.bia, "Água", 30.0, "2026-08-10")   # vencida antes de 15/09/2026
        pagina, _ = self.abrir_inicio()
        textos = self.textos(pagina)
        self.assertIn(EM_ATRASO, textos)
        self.assertNotIn(EM_DIA, textos)
        self.assertIsNone(self.orientacao(pagina))
        self.assertIn(MES_VAZIO, textos)                       # setembro continua vazio

    def test_contas_de_outro_usuario_nao_contam(self):
        db.criar_conta_unica(self.ana, "Luz", 10.0, "2026-09-20")
        pagina, _ = self.abrir_inicio()                       # Bia continua sem contas
        self.assert_orientacao(pagina, CLARO)


if __name__ == "__main__":
    unittest.main()
