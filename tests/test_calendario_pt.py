"""
ERS v7.0, E8 (M6) — calendário em português e contraste do dia atual
(5.47, P22, CT135, T11, RNF09; decisões M6-A e M6-B).

No tema do Flet, o número de hoje usa a cor de texto sobre ação quando
selecionado e a cor de ação sem seleção (4,5:1 nos dois temas); a página
declara português do Brasil ao Flutter; os três calendários (vencimento em
Nova conta e em Editar conta, data de pagamento em Editar conta) usam os
textos próprios em português; a data escolhida continua exibida em
dd/mm/aaaa e gravada em ISO. Fluxos reais da interface sobre páginas falsas
e bancos temporários; nenhuma janela é aberta.

O desenho interno do calendário (nomes dos meses e dos dias, semana a
partir do domingo, interpretação da data digitada) vem do Flutter com o
idioma pt-BR e só é conferido na validação manual.
"""

import unittest
from datetime import datetime
from unittest import mock

import test_tela_principal
from apoio_banco import DataFixa, TesteComBancoTemporario, db
from test_cores import MINIMO_TEXTO, contraste
from test_tela_principal import Evento, ft, main

TEXTOS = {
    "help_text": "Selecione a data",
    "cancel_text": "Cancelar",
    "confirm_text": "OK",
    "field_label_text": "Data (dd/mm/aaaa)",
    "error_format_text": "Formato inválido. Use dd/mm/aaaa.",
    "error_invalid_text": "Data fora do intervalo permitido.",
}


class TestTemaDoCalendario(unittest.TestCase):
    def test_cor_do_numero_de_hoje_por_estado_nos_dois_temas(self):  # CT135
        for tema in ("claro", "escuro"):
            paleta = main.modulo_cores.PALETAS[tema]
            with self.subTest(tema=tema):
                calendario = main.tema_flet(tema).date_picker_theme
                cores_de_hoje = calendario.today_foreground_color
                self.assertEqual(cores_de_hoje[ft.ControlState.SELECTED], paleta["texto_sobre_acao"])
                self.assertEqual(cores_de_hoje[ft.ControlState.DEFAULT], paleta["acao_primaria"])
                self.assertEqual(calendario.today_border_side.color, paleta["acao_primaria"])

    def test_numero_de_hoje_legivel_selecionado_ou_nao(self):  # CT135, RNF09
        for tema in ("claro", "escuro"):
            paleta = main.modulo_cores.PALETAS[tema]
            tema_flet = main.tema_flet(tema)
            cores_de_hoje = tema_flet.date_picker_theme.today_foreground_color
            # Selecionado: fundo do dia = primary do esquema de cores.
            selecionado = contraste(cores_de_hoje[ft.ControlState.SELECTED], tema_flet.color_scheme.primary)
            sem_selecao = contraste(cores_de_hoje[ft.ControlState.DEFAULT], tema_flet.date_picker_theme.bgcolor)
            with self.subTest(tema=tema):
                self.assertEqual(tema_flet.color_scheme.primary, paleta["acao_primaria"])
                self.assertGreaterEqual(selecionado, MINIMO_TEXTO, f"{selecionado:.2f}")
                self.assertGreaterEqual(sem_selecao, MINIMO_TEXTO, f"{sem_selecao:.2f}")

    def test_demais_cores_do_calendario_preservadas(self):
        for tema in ("claro", "escuro"):
            paleta = main.modulo_cores.PALETAS[tema]
            with self.subTest(tema=tema):
                calendario = main.tema_flet(tema).date_picker_theme
                self.assertEqual(calendario.bgcolor, paleta["fundo_dialogo"])
                self.assertEqual(calendario.header_bgcolor, paleta["fundo_dialogo"])
                self.assertEqual(calendario.header_foreground_color, paleta["texto_principal"])
                self.assertEqual(calendario.today_border_side.width, 1)
                self.assertEqual(calendario.cancel_button_style.color, paleta["acao_primaria"])
                self.assertEqual(calendario.confirm_button_style.color, paleta["acao_primaria"])


class TestIdiomaETextos(unittest.TestCase):
    def test_configuracao_pt_br(self):  # P22
        configuracao = main.configuracao_de_idioma()
        self.assertEqual(configuracao.current_locale, ft.Locale("pt", "BR"))
        self.assertEqual(configuracao.supported_locales, [ft.Locale("pt", "BR")])

    def test_textos_do_calendario(self):  # 5.47
        self.assertEqual(main.TEXTOS_CALENDARIO, TEXTOS)

    def test_seletor_com_textos_e_entrada_digitavel(self):  # M6-A
        seletor = main.criar_seletor_data(first_date=datetime(2000, 1, 1), last_date=datetime(2100, 12, 31))
        for atributo, texto in TEXTOS.items():
            self.assertEqual(getattr(seletor, atributo), texto)
        # O lápis (troca para a entrada digitada) continua disponível: modo
        # inicial de calendário, sem restringir a só calendário.
        self.assertEqual(seletor.entry_mode, ft.DatePickerEntryMode.CALENDAR)
        self.assertEqual(seletor.first_date, datetime(2000, 1, 1))
        self.assertEqual(seletor.last_date, datetime(2100, 12, 31))


class TestCalendariosNaInterface(TesteComBancoTemporario):
    """Hoje fixo em 15/09/2026; as contas ficam em outubro/2026."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.usuario_id = self.criar_usuario(email="tela@sino.com", senha="senha1234")
        self.pagina = mock.MagicMock()
        self.pagina.controls = []
        self.pagina.add.side_effect = lambda *controles: self.pagina.controls.extend(controles)

    controles = test_tela_principal.TestFluxoDaTelaPrincipal.controles
    textos = test_tela_principal.TestFluxoDaTelaPrincipal.textos
    clicar = test_tela_principal.TestFluxoDaTelaPrincipal.clicar
    entrar = test_tela_principal.TestFluxoDaTelaPrincipal.entrar
    icones = test_tela_principal.TestFluxoDaTelaPrincipal.icones
    ir_para_outubro = test_tela_principal.TestFluxoDaTelaPrincipal.ir_para_outubro
    botao = test_tela_principal.TestFluxoDaTelaPrincipal.botao

    def seletores(self):
        return [chamada.args[0] for chamada in self.pagina.overlay.append.call_args_list
                if isinstance(chamada.args[0], ft.DatePicker)]

    def assert_textos_em_portugues(self, seletor):
        for atributo, texto in TEXTOS.items():
            self.assertEqual(getattr(seletor, atributo), texto, atributo)

    def escolher(self, seletor, dia):
        seletor.value = dia
        seletor.on_change(Evento(self.pagina, seletor))

    def campo(self, rotulo):
        return next(c for c in self.controles(ft.TextField) if c.label == rotulo)

    def test_pagina_declara_pt_br(self):  # P22
        main.main(self.pagina)
        self.assertEqual(self.pagina.locale_configuration.current_locale, ft.Locale("pt", "BR"))

    def test_nova_conta(self):  # CT135
        self.entrar()
        self.clicar(next(c for c in self.controles(ft.Container) if c.data == "nova_conta"))
        (seletor,) = self.seletores()
        self.assert_textos_em_portugues(seletor)
        self.escolher(seletor, datetime(2026, 10, 20))
        self.assertEqual(self.campo("Data de vencimento").value, "20/10/2026")

    def test_editar_conta_grava_iso(self):  # CT135; armazenamento inalterado
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-05")
        self.entrar()
        self.ir_para_outubro()
        self.clicar(self.icones("Editar conta")[0])
        (seletor,) = self.seletores()
        self.assert_textos_em_portugues(seletor)
        self.escolher(seletor, datetime(2026, 10, 20))
        self.assertEqual(self.campo("Data de vencimento").value, "20/10/2026")
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.consultar("SELECT data_vencimento FROM contas WHERE id = ?", (conta_id,))[0][0],
                         "2026-10-20")

    def test_data_de_pagamento_em_editar_conta(self):  # CT135; regra de data futura inalterada
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-05")
        db.marcar_conta_como_paga(conta_id, "2026-09-10")
        self.entrar()
        self.ir_para_outubro()
        self.clicar(self.icones("Editar conta")[0])
        # O bloco de status é montado mais de uma vez ao abrir a edição (cada
        # montagem cria o seu calendário); vale o da última montagem.
        pagamento = [s for s in self.seletores() if s.on_change.__name__ == "ao_escolher_data_pagamento"]
        self.assertGreaterEqual(len(pagamento), 1)
        for seletor in pagamento:
            self.assert_textos_em_portugues(seletor)
        seletor = pagamento[-1]
        self.assertEqual(seletor.first_date, main.date(2000, 1, 1))
        self.assertEqual(seletor.last_date, main.date(2100, 12, 31))
        self.escolher(seletor, datetime(2026, 9, 20))   # depois de "hoje" (15/09)
        self.assertEqual(self.pagina.show_dialog.call_args[0][0].title.value, "Data inválida")
        self.assertEqual(self.consultar("SELECT data_pagamento FROM contas WHERE id = ?", (conta_id,))[0][0],
                         "2026-09-10")


if __name__ == "__main__":
    unittest.main()
