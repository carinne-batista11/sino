"""
ERS v7.0, E11 (M3) — seletor de mês e ano em Início (5.44, RF44, RNF09,
RNF14, P19; CT128–CT132; decisões M3-1 a M3-4 e a faixa que inclui o ano
exibido, aprovada em 16/10/2026).

Mês e ano de Início com seta para baixo, numa única área clicável (botão,
com dica e nome acessível), separada das setas; diálogo com o ano (setas
limitadas à faixa) e a grade 4 × 3 dos meses abreviados; destaques do
período exibido (fundo) e do mês de hoje (contorno); "Mês atual" e
"Cancelar". Abrir, trocar o ano e cancelar não navegam nem geram
ocorrências; escolher um mês navega pelo mesmo caminho das setas (5.20).
Fluxos reais da interface sobre páginas falsas e bancos temporários;
nenhuma janela é aberta. Foco visível e leitura do nome acessível pelo
leitor de tela só se confirmam na validação manual.
"""

import unittest
from unittest import mock

import test_tela_principal
from apoio_banco import DataFixa, TesteComBancoTemporario, db
from test_cores import MINIMO_NAO_TEXTO, MINIMO_TEXTO, contraste
from test_sessao_tema import CLARO, ESCURO, PaginaFalsa
from test_tela_principal import Evento, ft, main, percorrer

ABREVIADOS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


class TestFuncoesDoSeletor(unittest.TestCase):
    def test_faixa_sem_contas(self):  # M3-2
        self.assertEqual(main.faixa_de_anos([], 2026, 2026), (2026, 2031))

    def test_faixa_com_contas_antes_e_depois(self):  # CT130
        self.assertEqual(main.faixa_de_anos([2019, 2026, 2035], 2026, 2026), (2019, 2035))
        self.assertEqual(main.faixa_de_anos([2027, 2028], 2026, 2026), (2026, 2031))

    def test_faixa_inclui_o_ano_exibido(self):  # decisão de 16/10/2026
        self.assertEqual(main.faixa_de_anos([], 2026, 2040), (2026, 2040))
        self.assertEqual(main.faixa_de_anos([2024], 2026, 2010), (2010, 2031))

    def test_nome_acessivel_dos_meses(self):  # M3-4
        self.assertEqual(main.nome_do_mes_no_seletor(2026, 10, False, False), "Outubro de 2026")
        self.assertEqual(main.nome_do_mes_no_seletor(2026, 10, True, False), "Outubro de 2026, exibido")
        self.assertEqual(main.nome_do_mes_no_seletor(2026, 9, False, True), "Setembro de 2026, mês atual")
        self.assertEqual(main.nome_do_mes_no_seletor(2026, 9, True, True), "Setembro de 2026, exibido, mês atual")


class BaseSeletor(TesteComBancoTemporario):
    """Hoje fixo em 15/09/2026 (db e main); páginas falsas com pilha de diálogos."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.usuario_id = self.criar_usuario(email="tela@sino.com", senha="senha1234")
        self.pagina = PaginaFalsa().configurar()

    controles = test_tela_principal.TestFluxoDaTelaPrincipal.controles
    textos = test_tela_principal.TestFluxoDaTelaPrincipal.textos
    clicar = test_tela_principal.TestFluxoDaTelaPrincipal.clicar
    entrar = test_tela_principal.TestFluxoDaTelaPrincipal.entrar
    icones = test_tela_principal.TestFluxoDaTelaPrincipal.icones
    botao = test_tela_principal.TestFluxoDaTelaPrincipal.botao
    abrir_ver_status = test_tela_principal.TestFluxoDaTelaPrincipal.abrir_ver_status

    # ---------------------------------------------------------------- auxiliares
    def seta_de_inicio(self, icone):
        return next(b for b in self.controles(ft.IconButton) if b.icon == icone)

    def abertura(self):
        return next(c for c in self.controles(ft.TextButton) if c.data == "escolher_mes_e_ano")

    def semantica_da_abertura(self):
        return next(c for c in self.controles(ft.Semantics) if c.content is self.abertura())

    def abrir(self):
        self.clicar(self.abertura())
        return self.dialogo()

    def dialogo(self):
        abertos = [d for d in self.pagina.dialogos if d.open]
        self.assertEqual(len(abertos), 1)
        self.assertEqual(abertos[0].title.value, "Escolher mês e ano")
        return abertos[0]

    def no_dialogo(self, dialogo, tipo=None):
        return [c for c in percorrer(dialogo) if tipo is None or isinstance(c, tipo)]

    def ano_do_dialogo(self, dialogo):
        linha_do_ano = dialogo.content.controls[0]
        return linha_do_ano.controls[1].value

    def seta_de_ano(self, dialogo, dica):
        return next(b for b in self.no_dialogo(dialogo, ft.IconButton) if b.tooltip == dica)

    def trocar_ano(self, dica):
        self.clicar(self.seta_de_ano(self.dialogo(), dica))

    def meses(self, dialogo):
        """{abreviação: (Semantics, Button)} na ordem da grade."""
        return {s.content.content: (s, s.content) for s in self.no_dialogo(dialogo, ft.Semantics)}

    def escolher(self, abreviacao):
        self.clicar(self.meses(self.dialogo())[abreviacao][1])

    def acao(self, dialogo, rotulo):
        return next(a for a in dialogo.actions if a.content == rotulo)

    def ocorrencias(self, serie_id):
        return [linha[0] for linha in self.consultar(
            "SELECT data_vencimento FROM contas WHERE serie_id = ? ORDER BY data_vencimento", (serie_id,))]

    def sem_dialogo_aberto(self):
        return not any(d.open for d in self.pagina.dialogos)


class TestAbertura(BaseSeletor):
    def test_area_unica_com_icone_dica_e_nome_acessivel(self):  # M3-3, CT132
        self.entrar()
        abertura = self.abertura()
        self.assertIsInstance(abertura, ft.TextButton)            # recebe foco (Tab) e abre com Enter/Espaço
        self.assertEqual(abertura.tooltip, "Escolher mês e ano")
        texto, icone = abertura.content.controls
        self.assertEqual(texto.value, "Setembro 2026")             # texto visível no formato atual
        self.assertEqual((icone.icon, icone.color), (ft.Icons.ARROW_DROP_DOWN, CLARO["texto_principal"]))
        self.assertEqual(texto.color, CLARO["texto_principal"])
        self.assertEqual(abertura.style.side[ft.ControlState.FOCUSED].color, CLARO["acao_primaria"])
        semantica = self.semantica_da_abertura()
        self.assertTrue(semantica.button)
        self.assertEqual(semantica.label, "Escolher mês e ano, Setembro de 2026")

    def test_setas_preservadas_e_separadas(self):
        self.entrar()
        linha = next(c for c in self.controles(ft.Row) if self.semantica_da_abertura() in c.controls)
        esquerda, abertura, direita = linha.controls
        self.assertEqual((esquerda.icon, direita.icon), (ft.Icons.CHEVRON_LEFT, ft.Icons.CHEVRON_RIGHT))
        self.clicar(direita)
        self.assertIn("Outubro 2026", self.textos())
        self.assertEqual(self.semantica_da_abertura().label, "Escolher mês e ano, Outubro de 2026")
        self.assertTrue(self.sem_dialogo_aberto())
        self.clicar(self.seta_de_inicio(ft.Icons.CHEVRON_LEFT))
        self.assertIn("Setembro 2026", self.textos())

    def test_dialogo_com_ano_grade_4x3_e_acoes(self):  # M3-1
        self.entrar()
        dialogo = self.abrir()
        self.assertEqual(dialogo.bgcolor, CLARO["fundo_dialogo"])
        self.assertEqual(self.ano_do_dialogo(dialogo), "2026")
        linhas = dialogo.content.controls[1:]
        self.assertEqual([len(linha.controls) for linha in linhas], [3, 3, 3, 3])
        self.assertEqual([s.content.content for linha in linhas for s in linha.controls], ABREVIADOS)
        self.assertEqual([a.content for a in dialogo.actions], ["Mês atual", "Cancelar"])

    def test_controles_do_dialogo_focaveis(self):  # CT132 (parte automatizável)
        self.entrar()
        dialogo = self.abrir()
        for semantica, botao in self.meses(dialogo).values():
            self.assertIsInstance(botao, ft.Button)
            self.assertTrue(semantica.button)
            self.assertEqual(botao.style.side[ft.ControlState.FOCUSED].color, CLARO["texto_principal"])
        self.assertEqual(len(self.no_dialogo(dialogo, ft.IconButton)), 2)
        self.assertTrue(all(isinstance(a, ft.TextButton) for a in dialogo.actions))


class TestCancelarETrocarAno(BaseSeletor):
    def test_abrir_trocar_ano_e_cancelar_nao_navegam_nem_geram(self):  # CT128
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-10", "mensal")
        self.entrar()
        antes = self.ocorrencias(serie_id)
        with mock.patch.object(main.database, "gerar_ocorrencias_sob_demanda",
                               wraps=db.gerar_ocorrencias_sob_demanda) as gerar:
            dialogo = self.abrir()
            self.trocar_ano("Próximo ano")
            self.trocar_ano("Próximo ano")
            self.assertEqual(self.ano_do_dialogo(self.dialogo()), "2028")
            self.clicar(self.acao(dialogo, "Cancelar"))
            gerar.assert_not_called()
        self.assertTrue(self.sem_dialogo_aberto())
        self.assertIn("Setembro 2026", self.textos())
        self.assertEqual(self.ocorrencias(serie_id), antes)

    def test_trocar_ano_tira_os_destaques(self):
        self.entrar()
        self.abrir()
        self.trocar_ano("Próximo ano")
        for semantica, botao in self.meses(self.dialogo()).values():
            self.assertEqual(botao.bgcolor, CLARO["fundo_dialogo"])
            self.assertNotIn(ft.ControlState.DEFAULT, botao.style.side)
            self.assertFalse(semantica.selected)


class TestEscolherMes(BaseSeletor):
    def test_mes_futuro_navega_e_gera_como_as_setas(self):  # CT129
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-10", "mensal")
        self.entrar()
        with mock.patch.object(main.database, "gerar_ocorrencias_sob_demanda",
                               wraps=db.gerar_ocorrencias_sob_demanda) as gerar:
            self.abrir()
            self.trocar_ano("Próximo ano")
            gerar.assert_not_called()
            self.escolher("Mar")
            gerar.assert_called_with(serie_id, "2027-03")
        self.assertTrue(self.sem_dialogo_aberto())
        self.assertIn("Março 2027", self.textos())
        self.assertIn("Suas contas de março", self.textos())
        esperado = [f"{a}-{m:02d}-10" for a, m in [(2026, m) for m in range(9, 13)] + [(2027, m) for m in range(1, 4)]]
        self.assertEqual(self.ocorrencias(serie_id)[:7], esperado)
        self.assertEqual(len(set(self.ocorrencias(serie_id))), len(self.ocorrencias(serie_id)))  # sem duplicar

        # Mesmo resultado por setas: voltar e avançar não duplica nada.
        for _ in range(2):
            self.clicar(self.seta_de_inicio(ft.Icons.CHEVRON_RIGHT))
        self.assertIn("Maio 2027", self.textos())
        self.assertEqual(len(set(self.ocorrencias(serie_id))), len(self.ocorrencias(serie_id)))

    def test_mes_passado(self):
        db.criar_conta_unica(self.usuario_id, "Antiga", 20.0, "2025-02-03")
        self.entrar()
        self.abrir()
        self.trocar_ano("Ano anterior")
        self.escolher("Fev")
        self.assertIn("Fevereiro 2025", self.textos())
        self.assertIn("Antiga", self.textos())

    def test_dezembro_e_janeiro(self):
        self.entrar()
        self.abrir()
        self.escolher("Dez")
        self.assertIn("Dezembro 2026", self.textos())
        self.clicar(self.seta_de_inicio(ft.Icons.CHEVRON_RIGHT))
        self.assertIn("Janeiro 2027", self.textos())
        self.clicar(self.seta_de_inicio(ft.Icons.CHEVRON_LEFT))
        self.assertIn("Dezembro 2026", self.textos())
        self.abrir()
        self.trocar_ano("Próximo ano")
        self.escolher("Jan")
        self.assertIn("Janeiro 2027", self.textos())

    def test_ver_status_e_volta_da_edicao_usam_o_mes_escolhido(self):
        db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-11-05")
        self.entrar()
        self.abrir()
        self.escolher("Nov")
        self.abrir_ver_status()
        self.assertIn("Novembro de 2026", self.textos())
        self.clicar(next(b for b in self.controles(ft.IconButton) if b.icon == ft.Icons.ARROW_BACK))
        self.assertIn("Novembro 2026", self.textos())

        self.clicar(self.icones("Editar conta")[0])
        self.clicar(self.botao("Cancelar"))
        self.assertIn("Novembro 2026", self.textos())
        self.assertEqual(self.semantica_da_abertura().label, "Escolher mês e ano, Novembro de 2026")


class TestFaixaNoDialogo(BaseSeletor):
    def percorrer_ate_o_limite(self, dica):
        for _ in range(30):
            seta = self.seta_de_ano(self.dialogo(), dica)
            if seta.disabled:
                return self.ano_do_dialogo(self.dialogo())
            self.clicar(seta)
        self.fail("a seta de ano não parou")

    def test_contas_antes_do_ano_atual_e_depois_de_mais_cinco(self):  # CT130
        db.criar_conta_unica(self.usuario_id, "Antiga", 20.0, "2019-05-03")
        db.criar_conta_unica(self.usuario_id, "Distante", 20.0, "2035-01-03")
        self.entrar()
        self.abrir()
        self.assertEqual(self.percorrer_ate_o_limite("Ano anterior"), "2019")
        self.assertEqual(self.percorrer_ate_o_limite("Próximo ano"), "2035")

    def test_sem_contas(self):  # M3-2
        self.entrar()
        self.abrir()
        self.assertEqual(self.percorrer_ate_o_limite("Ano anterior"), "2026")
        self.assertEqual(self.percorrer_ate_o_limite("Próximo ano"), "2031")

    def test_ocorrencias_geradas_contam_na_faixa(self):  # M3-2: inclui ocorrências já geradas
        db.criar_serie_recorrente(self.usuario_id, "Escola", 700.0, "2026-09-10", "anual", data_termino="2034-09")
        self.entrar()
        self.abrir()
        self.assertEqual(self.percorrer_ate_o_limite("Próximo ano"), "2034")

    def test_ano_exibido_fora_da_faixa(self):  # decisão de 16/10/2026
        self.entrar()
        for _ in range(9):                           # setas de Início livres: Dezembro de 2025
            self.clicar(self.seta_de_inicio(ft.Icons.CHEVRON_LEFT))
        self.assertIn("Dezembro 2025", self.textos())
        dialogo = self.abrir()
        self.assertEqual(self.ano_do_dialogo(dialogo), "2025")
        self.assertTrue(self.seta_de_ano(dialogo, "Ano anterior").disabled)
        semantica, botao = self.meses(dialogo)["Dez"]
        self.assertEqual(botao.bgcolor, CLARO["acao_primaria"])
        self.assertEqual(self.percorrer_ate_o_limite("Próximo ano"), "2031")


class TestDestaquesEMesAtual(BaseSeletor):
    def assert_destaques(self, paleta):
        self.clicar(self.seta_de_inicio(ft.Icons.CHEVRON_RIGHT))      # Outubro exibido; hoje = setembro
        meses = self.meses(self.abrir())
        exibido_s, exibido = meses["Out"]
        hoje_s, hoje = meses["Set"]
        self.assertEqual((exibido.bgcolor, exibido.color), (paleta["acao_primaria"], paleta["texto_sobre_acao"]))
        self.assertNotIn(ft.ControlState.DEFAULT, exibido.style.side)
        self.assertEqual((exibido_s.selected, exibido_s.label), (True, "Outubro de 2026, exibido"))
        self.assertEqual((hoje.bgcolor, hoje.color), (paleta["fundo_dialogo"], paleta["texto_principal"]))
        self.assertEqual(hoje.style.side[ft.ControlState.DEFAULT].color, paleta["acao_primaria"])
        self.assertEqual((hoje_s.selected, hoje_s.label), (False, "Setembro de 2026, mês atual"))
        for abreviacao in set(ABREVIADOS) - {"Out", "Set"}:
            semantica, botao = meses[abreviacao]
            self.assertEqual((botao.bgcolor, botao.color), (paleta["fundo_dialogo"], paleta["texto_principal"]))
            self.assertNotIn(ft.ControlState.DEFAULT, botao.style.side)
            self.assertNotIn(",", semantica.label)
        self.pagina.pop_dialog()

        self.clicar(self.seta_de_inicio(ft.Icons.CHEVRON_LEFT))       # os dois juntos
        juntos_s, juntos = self.meses(self.abrir())["Set"]
        self.assertEqual((juntos.bgcolor, juntos.color), (paleta["acao_primaria"], paleta["texto_sobre_acao"]))
        anel = juntos.style.side[ft.ControlState.DEFAULT]
        self.assertEqual(anel.color, paleta["texto_principal"])     # visível em volta do fundo preenchido
        self.assertEqual(juntos_s.label, "Setembro de 2026, exibido, mês atual")

    def test_destaques_no_claro(self):  # M3-4
        self.entrar()
        self.assert_destaques(CLARO)

    def test_destaques_no_escuro(self):  # M3-4, RNF09
        db.definir_tema(self.usuario_id, "escuro")
        self.entrar()
        self.assert_destaques(ESCURO)
        self.assertEqual(self.dialogo().bgcolor, ESCURO["fundo_dialogo"])
        texto, icone = self.abertura().content.controls
        self.assertEqual((texto.color, icone.color), (ESCURO["texto_principal"], ESCURO["texto_principal"]))

    def test_contraste_dos_destaques_nos_dois_temas(self):  # RNF09
        for paleta in (CLARO, ESCURO):
            with self.subTest(fundo=paleta["fundo_dialogo"]):
                self.assertGreaterEqual(contraste(paleta["texto_sobre_acao"], paleta["acao_primaria"]), MINIMO_TEXTO)
                self.assertGreaterEqual(contraste(paleta["texto_principal"], paleta["fundo_dialogo"]), MINIMO_TEXTO)
                # contornos (hoje; hoje exibido; foco) sobre o fundo do diálogo
                self.assertGreaterEqual(contraste(paleta["acao_primaria"], paleta["fundo_dialogo"]), MINIMO_NAO_TEXTO)
                self.assertGreaterEqual(contraste(paleta["texto_principal"], paleta["fundo_dialogo"]), MINIMO_NAO_TEXTO)
                # foco da abertura sobre o fundo da página
                self.assertGreaterEqual(contraste(paleta["acao_primaria"], paleta["fundo_pagina"]), MINIMO_NAO_TEXTO)

    def test_mes_atual_desativado_quando_ja_exibido(self):  # CT131
        self.entrar()
        botao = self.acao(self.abrir(), "Mês atual")
        self.assertTrue(botao.disabled)
        self.assertEqual(botao.style.color, CLARO["botao_desabilitado_texto"])

    def test_mes_atual_navega_e_fecha(self):  # CT131
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-10", "mensal")
        self.entrar()
        self.abrir()
        self.trocar_ano("Próximo ano")
        self.escolher("Jun")
        self.assertIn("Junho 2027", self.textos())
        dialogo = self.abrir()
        self.trocar_ano("Ano anterior")
        botao = self.acao(dialogo, "Mês atual")
        self.assertFalse(botao.disabled)
        self.assertEqual(botao.style.color, CLARO["acao_primaria"])
        antes = self.ocorrencias(serie_id)
        self.clicar(botao)
        self.assertTrue(self.sem_dialogo_aberto())
        self.assertIn("Setembro 2026", self.textos())
        self.assertEqual(self.ocorrencias(serie_id), antes)


class TestUsuarioSemContas(BaseSeletor):
    def test_orientacao_mantida_ao_navegar_pelo_seletor(self):  # M2 + M3
        orientacao = "Registre suas primeiras contas e tenha tudo sob controle."
        self.entrar()
        self.assertIn(orientacao, self.textos())
        self.abrir()
        self.trocar_ano("Próximo ano")
        self.escolher("Abr")
        self.assertIn("Abril 2027", self.textos())
        self.assertIn(orientacao, self.textos())
        self.assertNotIn("Nenhuma conta neste mês.", self.textos())


class TestOutroUsuario(BaseSeletor):
    def test_faixa_so_com_as_contas_do_proprio_usuario(self):
        outro = self.criar_usuario(email="outra@sino.com", senha="senha9999")
        db.criar_conta_unica(outro, "De outra", 20.0, "2015-05-03")
        self.entrar()
        self.abrir()
        self.assertTrue(self.seta_de_ano(self.dialogo(), "Ano anterior").disabled)


if __name__ == "__main__":
    unittest.main()
