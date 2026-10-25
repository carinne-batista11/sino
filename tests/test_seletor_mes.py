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
from collections import namedtuple
from unittest import mock

import test_tela_principal
from apoio_banco import DataFixa, TesteComBancoTemporario, db
from test_cores import MINIMO_NAO_TEXTO, MINIMO_TEXTO, contraste
from test_sessao_tema import CLARO, ESCURO, PaginaFalsa
from test_tela_principal import Evento, ft, main, percorrer

ABREVIADOS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# Sino 6.9 (E11, variante EB): cada mês é MergeSemantics -> Semantics(selected)
# -> Button -> Text(semantics_label); nome e estado no próprio botão focável.
Mes = namedtuple("Mes", "merge semantica botao texto")


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
        # o ícone das setas de Início é um ft.Icon (com o nome acessível, RNF14)
        return next(b for b in self.controles(ft.IconButton) if getattr(b.icon, "icon", None) == icone)

    def abertura(self):
        return next(c for c in self.controles(ft.TextButton) if c.data == "escolher_mes_e_ano")

    def nome_da_abertura(self):
        """Nome acessível do botão de abertura (semantics_label do texto do mês)."""
        texto, _ = self.abertura().content.controls
        return texto.semantics_label

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
        """{abreviação: Mes(merge, semantica, botao, texto)} na ordem da grade."""
        resultado = {}
        for merge in self.no_dialogo(dialogo, ft.MergeSemantics):
            semantica = merge.content
            botao = semantica.content
            resultado[botao.content.value] = Mes(merge, semantica, botao, botao.content)
        return resultado

    def escolher(self, abreviacao):
        self.clicar(self.meses(self.dialogo())[abreviacao].botao)

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
        # Sino 6.9: o nome acessível fica no próprio botão (texto do mês), sem
        # um Semantics externo que repetiria o elemento.
        self.assertEqual(texto.semantics_label, "Escolher mês e ano, Setembro de 2026")
        self.assertFalse(any(isinstance(c, ft.Semantics) and c.content is abertura for c in self.controles()))

    def test_setas_preservadas_e_separadas(self):
        self.entrar()
        linha = next(c for c in self.controles(ft.Row) if self.abertura() in c.controls)
        esquerda, abertura, direita = linha.controls
        self.assertIs(abertura, self.abertura())
        self.assertEqual((esquerda.icon.icon, direita.icon.icon), (ft.Icons.CHEVRON_LEFT, ft.Icons.CHEVRON_RIGHT))
        self.clicar(direita)
        self.assertIn("Outubro 2026", self.textos())
        self.assertEqual(self.nome_da_abertura(), "Escolher mês e ano, Outubro de 2026")
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
        self.assertTrue(all(isinstance(m, ft.MergeSemantics) and m.expand for linha in linhas for m in linha.controls))
        self.assertEqual([m.content.content.content.value for linha in linhas for m in linha.controls], ABREVIADOS)
        self.assertEqual([a.content for a in dialogo.actions], ["Mês atual", "Cancelar"])

    def test_controles_do_dialogo_focaveis(self):  # CT132 (parte automatizável)
        self.entrar()
        dialogo = self.abrir()
        meses = self.meses(dialogo)
        self.assertEqual(list(meses), ABREVIADOS)
        for mes in meses.values():
            self.assertIsInstance(mes.merge, ft.MergeSemantics)
            self.assertIsInstance(mes.semantica, ft.Semantics)
            self.assertIsInstance(mes.botao, ft.Button)               # o papel de botão vem do próprio Button
            self.assertFalse(mes.semantica.button)                    # sem um segundo elemento de botão
            self.assertIsNone(mes.semantica.label)                    # o nome fica no texto do botão
            self.assertEqual(mes.botao.style.side[ft.ControlState.FOCUSED].color, CLARO["texto_principal"])
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
        for mes in self.meses(self.dialogo()).values():
            self.assertEqual(mes.botao.bgcolor, CLARO["fundo_dialogo"])
            self.assertNotIn(ft.ControlState.DEFAULT, mes.botao.style.side)
            self.assertFalse(mes.semantica.selected)
            self.assertNotIn(",", mes.texto.semantics_label)


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
        self.clicar(next(b for b in self.controles(ft.IconButton) if getattr(b.icon, "icon", None) == ft.Icons.ARROW_BACK))
        self.assertIn("Novembro 2026", self.textos())

        self.clicar(self.icones("Editar conta")[0])
        self.clicar(self.botao("Cancelar"))
        self.assertIn("Novembro 2026", self.textos())
        self.assertEqual(self.nome_da_abertura(), "Escolher mês e ano, Novembro de 2026")


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
        dezembro = self.meses(dialogo)["Dez"]
        self.assertEqual(dezembro.botao.bgcolor, CLARO["acao_primaria"])
        self.assertTrue(dezembro.semantica.selected)
        self.assertEqual(dezembro.texto.semantics_label, "Dezembro de 2025, exibido")
        self.assertEqual(self.percorrer_ate_o_limite("Próximo ano"), "2031")


class TestDestaquesEMesAtual(BaseSeletor):
    def assert_destaques(self, paleta):
        self.clicar(self.seta_de_inicio(ft.Icons.CHEVRON_RIGHT))      # Outubro exibido; hoje = setembro
        meses = self.meses(self.abrir())
        exibido = meses["Out"]
        hoje = meses["Set"]
        self.assertEqual((exibido.botao.bgcolor, exibido.botao.color),
                         (paleta["acao_primaria"], paleta["texto_sobre_acao"]))
        self.assertEqual(exibido.texto.color, paleta["texto_sobre_acao"])
        self.assertNotIn(ft.ControlState.DEFAULT, exibido.botao.style.side)
        self.assertEqual((exibido.semantica.selected, exibido.texto.semantics_label), (True, "Outubro de 2026, exibido"))
        self.assertEqual((hoje.botao.bgcolor, hoje.botao.color), (paleta["fundo_dialogo"], paleta["texto_principal"]))
        self.assertEqual(hoje.texto.color, paleta["texto_principal"])
        self.assertEqual(hoje.botao.style.side[ft.ControlState.DEFAULT].color, paleta["acao_primaria"])
        self.assertEqual((hoje.semantica.selected, hoje.texto.semantics_label), (False, "Setembro de 2026, mês atual"))
        for abreviacao in set(ABREVIADOS) - {"Out", "Set"}:
            mes = meses[abreviacao]
            self.assertEqual((mes.botao.bgcolor, mes.botao.color), (paleta["fundo_dialogo"], paleta["texto_principal"]))
            self.assertEqual(mes.texto.color, paleta["texto_principal"])
            self.assertNotIn(ft.ControlState.DEFAULT, mes.botao.style.side)
            self.assertFalse(mes.semantica.selected)
            self.assertNotIn(",", mes.texto.semantics_label)
        self.pagina.pop_dialog()

        self.clicar(self.seta_de_inicio(ft.Icons.CHEVRON_LEFT))       # os dois juntos
        juntos = self.meses(self.abrir())["Set"]
        self.assertEqual((juntos.botao.bgcolor, juntos.botao.color),
                         (paleta["acao_primaria"], paleta["texto_sobre_acao"]))
        anel = juntos.botao.style.side[ft.ControlState.DEFAULT]
        self.assertEqual(anel.color, paleta["texto_principal"])     # visível em volta do fundo preenchido
        self.assertEqual((juntos.semantica.selected, juntos.texto.semantics_label),
                         (True, "Setembro de 2026, exibido, mês atual"))

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


class TestAcessibilidadeVarianteEB(BaseSeletor):
    """
    Sino 6.9 (correção da E11, variante EB validada na prova isolada v3): nome
    acessível e estado "selecionado" no próprio botão focável, sem Semantics
    externo com o nome repetido. Leitor de tela e AT-SPI: só na validação manual.
    """

    def test_nenhum_semantics_com_nome_em_volta_da_abertura_e_dos_meses(self):
        self.entrar()
        self.assertEqual([c for c in self.controles(ft.Semantics) if c.label], [])
        dialogo = self.abrir()
        semanticas = self.no_dialogo(dialogo, ft.Semantics)
        self.assertEqual(len(semanticas), 12)
        for semantica in semanticas:
            self.assertIsNone(semantica.label)
            self.assertFalse(semantica.button)
            self.assertIsInstance(semantica.content, ft.Button)
        self.assertEqual(len(self.no_dialogo(dialogo, ft.MergeSemantics)), 12)

    def test_nome_e_estado_de_cada_mes_vem_do_seletor(self):
        self.entrar()
        meses = self.meses(self.abrir())
        for numero, abreviacao in enumerate(ABREVIADOS, start=1):
            mes = meses[abreviacao]
            exibido = de_hoje = numero == 9                          # setembro de 2026 exibido e hoje
            self.assertEqual(mes.texto.semantics_label, main.nome_do_mes_no_seletor(2026, numero, exibido, de_hoje))
            self.assertEqual(mes.semantica.selected, exibido)
            self.assertEqual(mes.texto.color, mes.botao.color)       # a cor do texto acompanha o botão
            self.assertEqual(mes.botao.data, ("mes_do_seletor", 2026, numero))
        self.assertEqual([a for a, m in meses.items() if m.semantica.selected], ["Set"])

    def test_nome_da_abertura_acompanha_a_navegacao(self):
        self.entrar()
        self.assertEqual(self.nome_da_abertura(), "Escolher mês e ano, Setembro de 2026")
        self.clicar(self.seta_de_inicio(ft.Icons.CHEVRON_RIGHT))
        self.assertEqual(self.nome_da_abertura(), "Escolher mês e ano, Outubro de 2026")
        self.abrir()
        self.trocar_ano("Próximo ano")
        self.escolher("Mar")
        self.assertEqual(self.nome_da_abertura(), "Escolher mês e ano, Março de 2027")
        self.clicar(self.acao(self.abrir(), "Mês atual"))
        self.assertEqual(self.nome_da_abertura(), "Escolher mês e ano, Setembro de 2026")
        self.assertIn("Setembro 2026", self.textos())

    def test_estado_selecionado_acompanha_o_ano_do_dialogo(self):
        self.entrar()
        self.abrir()
        self.trocar_ano("Próximo ano")
        self.assertEqual([a for a, m in self.meses(self.dialogo()).items() if m.semantica.selected], [])
        self.trocar_ano("Ano anterior")
        self.assertEqual([a for a, m in self.meses(self.dialogo()).items() if m.semantica.selected], ["Set"])


class TestNomesDasSetasDeInicio(BaseSeletor):
    """
    RNF14 (pendência de 23/10/2026, 15.3): nome acessível das setas de mês de
    Início no próprio botão focável (semantics_label do ícone), sem dica visível,
    sem Semantics externo e com a mesma aparência. Leitor de tela e AT-SPI: só na
    validação manual.
    """

    def setas(self):
        linha = next(c for c in self.controles(ft.Row) if self.abertura() in c.controls)
        esquerda, _, direita = linha.controls
        return esquerda, direita

    def assert_setas(self, paleta):
        esquerda, direita = self.setas()
        for seta, icone, nome, data in ((esquerda, ft.Icons.CHEVRON_LEFT, "Mês anterior", "mes_anterior"),
                                        (direita, ft.Icons.CHEVRON_RIGHT, "Próximo mês", "proximo_mes")):
            self.assertIsInstance(seta, ft.IconButton)                 # continua focável (Tab; Enter/Espaço)
            self.assertIsInstance(seta.icon, ft.Icon)
            self.assertEqual((seta.icon.icon, seta.icon.semantics_label), (icone, nome))
            self.assertEqual(seta.data, data)
            self.assertIsNone(seta.tooltip)                            # sem dica visível nova
            # mesma aparência de antes: tamanho 18 e texto secundário, no botão e no ícone
            self.assertEqual((seta.icon_size, seta.icon.size), (18, 18))
            self.assertEqual((seta.icon_color, seta.icon.color), (paleta["texto_secundario"],) * 2)

    def test_nomes_no_claro(self):
        self.entrar()
        self.assert_setas(CLARO)

    def test_nomes_no_escuro(self):  # RNF09: as cores seguem o tema
        db.definir_tema(self.usuario_id, "escuro")
        self.entrar()
        self.assert_setas(ESCURO)

    def test_nomes_mantidos_ao_navegar(self):
        self.entrar()
        _, direita = self.setas()
        self.clicar(direita)
        self.assertIn("Outubro 2026", self.textos())
        self.assert_setas(CLARO)
        self.clicar(self.setas()[0])
        self.clicar(self.setas()[0])
        self.assertIn("Agosto 2026", self.textos())
        self.assert_setas(CLARO)
        self.assertEqual(self.nome_da_abertura(), "Escolher mês e ano, Agosto de 2026")

    def test_sem_semantics_externo_em_volta_das_setas(self):
        self.entrar()
        self.assertEqual([c for c in self.controles(ft.Semantics) if c.label], [])
        self.assertEqual(self.controles(ft.MergeSemantics), [])


class TestNomesDasSetasDeAno(BaseSeletor):
    """
    RNF14 (achado de 24/10/2026): o tooltip das setas de ano do diálogo não dá
    nome acessível no Linux (AT-SPI); o nome vai no semantics_label do ícone,
    com a mesma dica do mouse, a mesma aparência e os mesmos limites da faixa.
    Leitor de tela e AT-SPI: só na validação manual.
    """

    def assert_setas(self, paleta, anterior_desabilitada, proxima_desabilitada):
        dialogo = self.dialogo()
        linha_do_ano = dialogo.content.controls[0]
        esquerda, _, direita = linha_do_ano.controls
        for seta, icone, nome, desabilitada in (
                (esquerda, ft.Icons.CHEVRON_LEFT, "Ano anterior", anterior_desabilitada),
                (direita, ft.Icons.CHEVRON_RIGHT, "Próximo ano", proxima_desabilitada)):
            self.assertIsInstance(seta, ft.IconButton)                 # continua focável (Tab; Enter/Espaço)
            self.assertIsInstance(seta.icon, ft.Icon)
            self.assertEqual((seta.icon.icon, seta.icon.semantics_label), (icone, nome))
            self.assertEqual(seta.tooltip, nome)                       # a dica do mouse continua a mesma
            self.assertEqual(seta.disabled, desabilitada)
            # mesma aparência de antes: tamanho padrão; ícone na cor do texto
            # principal também quando desabilitada (como já aparecia na janela real)
            self.assertEqual((seta.icon_size, seta.icon.size), (None, None))
            self.assertEqual((seta.icon_color, seta.disabled_color),
                             (paleta["texto_principal"], paleta["botao_desabilitado_texto"]))
            self.assertEqual(seta.icon.color, paleta["texto_principal"])

    def test_nomes_no_claro(self):
        self.entrar()
        self.abrir()
        self.assert_setas(CLARO, True, False)                          # faixa 2026–2031, aberto em 2026

    def test_nomes_no_escuro(self):  # RNF09: as cores seguem o tema
        db.definir_tema(self.usuario_id, "escuro")
        self.entrar()
        self.abrir()
        self.assert_setas(ESCURO, True, False)

    def test_nomes_e_limites_acompanham_a_troca_de_ano(self):
        self.entrar()
        self.abrir()
        self.trocar_ano("Próximo ano")
        self.assertEqual(self.ano_do_dialogo(self.dialogo()), "2027")
        self.assert_setas(CLARO, False, False)
        for _ in range(4):
            self.trocar_ano("Próximo ano")
        self.assertEqual(self.ano_do_dialogo(self.dialogo()), "2031")
        self.assert_setas(CLARO, False, True)                          # limite da faixa mantido
        self.trocar_ano("Ano anterior")
        self.assert_setas(CLARO, False, False)

    def test_sem_semantics_externo_em_volta_das_setas(self):
        self.entrar()
        dialogo = self.abrir()
        linha_do_ano = dialogo.content.controls[0]
        self.assertEqual([c for c in percorrer(linha_do_ano) if isinstance(c, (ft.Semantics, ft.MergeSemantics))], [])


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
