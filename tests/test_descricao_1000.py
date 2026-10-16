"""
ERS v7.0, E6 (M4) — descrição de até 1000 caracteres (5.45, RF32, RF33;
CT133; decisões M4-1 e M4-2).

Na interface: contador "x/1000" e dica "Até 1000 caracteres" (Q1: sem
separador); campo de 2 a 8 linhas, com rolagem interna depois; recusa do
1001º caractere com "Limite atingido" e som; descrição legada acima do
limite exibida inteira, salva só depois de reduzida; Detalhes mostra a
descrição inteira. Fluxos reais da interface sobre páginas falsas e bancos
temporários; o som é simulado e nenhuma janela é aberta.
"""

import unittest
from unittest import mock

import test_tela_principal
from apoio_banco import DataFixa, TesteComBancoTemporario, db
from test_tela_principal import Evento, ft, main, percorrer


EMOJI_COMPOSTO = "👩‍💻"                    # 3 pontos de código, 1 caractere percebido
MIL = "d" * 999 + EMOJI_COMPOSTO            # 1000 caracteres percebidos
MIL_COM_QUEBRAS = ("linha\n" * 166) + "fim!"  # 1000, com quebras internas
LEGADA = "x" * 1100                          # acima do limite (dado antigo)
ROTULO = "Descrição (opcional)"


def som_simulado():
    """Substitui o som da recusa (a suíte nunca toca áudio)."""
    return mock.patch.object(main.aviso_sonoro.aviso_limite, "tocar", return_value=True)


class BaseDescricao1000(TesteComBancoTemporario):
    """Hoje fixo em 15/09/2026; as contas ficam em outubro/2026 (como em test_tela_principal)."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.usuario_id = self.criar_usuario(email="tela@sino.com", senha="senha1234")  # usado por entrar()
        self.pagina = mock.MagicMock()
        self.pagina.controls = []
        self.pagina.add.side_effect = lambda *controles: self.pagina.controls.extend(controles)

    # Só os auxiliares da tela principal. A classe de lá não fica no espaço de
    # nomes deste módulo: senão a descoberta do unittest rodaria os testes dela
    # de novo aqui.
    controles = test_tela_principal.TestFluxoDaTelaPrincipal.controles
    textos = test_tela_principal.TestFluxoDaTelaPrincipal.textos
    clicar = test_tela_principal.TestFluxoDaTelaPrincipal.clicar
    entrar = test_tela_principal.TestFluxoDaTelaPrincipal.entrar
    na_tela_de_detalhes = test_tela_principal.TestFluxoDaTelaPrincipal.na_tela_de_detalhes
    icones = test_tela_principal.TestFluxoDaTelaPrincipal.icones
    ir_para_outubro = test_tela_principal.TestFluxoDaTelaPrincipal.ir_para_outubro
    botao = test_tela_principal.TestFluxoDaTelaPrincipal.botao

    def campo_descricao(self):
        return next(c for c in self.controles(ft.TextField) if c.label == ROTULO)

    def digitar(self, campo, valor):
        campo.value = valor
        campo.on_change(Evento(self.pagina, campo))

    def descricao_no_banco(self, conta_id):
        return self.consultar("SELECT descricao FROM contas WHERE id = ?", (conta_id,))[0][0]

    def abrir_nova_conta(self):
        self.entrar()
        self.clicar(next(c for c in self.controles(ft.Container) if c.data == "nova_conta"))
        self.assertIn("Nova conta", self.textos())

    def abrir_edicao_pelo_lapis(self):
        self.entrar()
        self.ir_para_outubro()
        self.clicar(self.icones("Editar conta")[0])

    def assert_campo_da_m4(self, campo, contador):
        self.assertEqual((campo.multiline, campo.min_lines, campo.max_lines), (True, 2, 8))  # M4-2
        self.assertEqual(campo.hint_text, "Até 1000 caracteres")                           # Q1
        self.assertEqual(campo.counter, contador)
        self.assertIsNone(getattr(campo, "max_length", None))                              # sem corte

    def assert_recusa_do_1001(self, campo):
        self.digitar(campo, MIL)
        self.assertEqual((campo.value, campo.counter, campo.helper), (MIL, "1000/1000", None))
        with som_simulado() as tocar:
            self.digitar(campo, MIL + "!")
        self.assertEqual((campo.value, campo.counter, campo.helper), (MIL, "1000/1000", "Limite atingido"))
        tocar.assert_called_once_with()


class TestNovaConta(BaseDescricao1000):
    def test_campo_contador_e_dica(self):  # CT133
        self.abrir_nova_conta()
        self.assert_campo_da_m4(self.campo_descricao(), "0/1000")

    def test_1000_aceito_e_1001_recusado_com_aviso_e_som(self):  # CT133
        self.abrir_nova_conta()
        self.assert_recusa_do_1001(self.campo_descricao())


class TestEditarConta(BaseDescricao1000):
    def test_campo_contador_e_recusa(self):  # CT133
        db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-05", descricao="Curta")
        self.abrir_edicao_pelo_lapis()
        campo = self.campo_descricao()
        self.assert_campo_da_m4(campo, "5/1000")
        self.assert_recusa_do_1001(campo)

    def test_salvar_conta_unica_com_1000(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-05")
        self.abrir_edicao_pelo_lapis()
        self.digitar(self.campo_descricao(), MIL_COM_QUEBRAS)
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.pagina.show_dialog.call_args[0][0].title.value, "Alteração salva")
        self.assertEqual(self.descricao_no_banco(conta_id), MIL_COM_QUEBRAS)

    def salvar_serie_com_escopo(self, escopo):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Escola", 700.0, "2026-10-10", "mensal",
                                                  data_termino="2027-01", descricao="Curta")
        self.abrir_edicao_pelo_lapis()
        self.digitar(self.campo_descricao(), MIL)
        self.clicar(self.botao("Salvar alterações"))
        dialogo = self.pagina.show_dialog.call_args[0][0]
        next(a for a in dialogo.actions if a.content == escopo).on_click(Evento(self.pagina))
        return serie_id, ids

    def test_salvar_serie_somente_este_mes_com_1000(self):
        serie_id, ids = self.salvar_serie_com_escopo("Somente este mês")
        self.assertEqual([self.descricao_no_banco(c) for c in ids], [MIL, "Curta", "Curta", "Curta"])
        self.assertEqual(self.descricao_do_modelo(serie_id), "Curta")

    def test_salvar_serie_este_mes_em_diante_com_1000(self):
        serie_id, ids = self.salvar_serie_com_escopo("Este mês em diante")
        self.assertEqual({self.descricao_no_banco(c) for c in ids}, {MIL})
        self.assertEqual(self.descricao_do_modelo(serie_id), MIL)

    def descricao_do_modelo(self, serie_id):
        return self.consultar("SELECT descricao FROM series_recorrencia WHERE id = ?", (serie_id,))[0][0]


class TestDescricaoLegada(BaseDescricao1000):
    """CT109 / P4 com o novo limite: exibida inteira; só salva depois de reduzida."""

    def test_legada_acima_de_1000(self):
        conta_id = self.executar(
            "INSERT INTO contas (usuario_id, nome, valor, data_vencimento, status, descricao) "
            "VALUES (?, 'Antiga', 10.0, '2026-10-05', 'pendente', ?)",
            (self.usuario_id, LEGADA),
        )
        self.abrir_edicao_pelo_lapis()
        campo = self.campo_descricao()
        self.assertEqual((campo.value, campo.counter), (LEGADA, "1100/1000"))   # sem corte
        self.assertEqual(campo.error, "A descrição pode ter no máximo 1000 caracteres (atual: 1100).")

        self.clicar(self.botao("Salvar alterações"))                            # sem reduzir: recusado
        self.assertIn("A descrição pode ter no máximo 1000 caracteres (atual: 1100).", self.textos())
        self.assertEqual(self.descricao_no_banco(conta_id), LEGADA)

        with som_simulado() as tocar:
            self.digitar(campo, LEGADA + "x")                                   # não cresce
        self.assertEqual(campo.value, LEGADA)
        tocar.assert_called_once_with()

        self.digitar(campo, "x" * 1000)                                         # reduzir é permitido
        self.assertEqual((campo.counter, campo.error), ("1000/1000", None))
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.descricao_no_banco(conta_id), "x" * 1000)


class TestDetalhes(BaseDescricao1000):
    def test_descricao_de_1000_inteira_com_quebras(self):  # 5.45 / 5.22 (CT58)
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-05", descricao=MIL_COM_QUEBRAS)
        self.entrar()
        self.ir_para_outubro()
        linha = next(c for c in self.controles(ft.Container)
                     if c.on_click is not None and isinstance(c.content, ft.Row) and c.border is not None
                     and any(isinstance(t, ft.Text) and t.value == "Luz" for t in percorrer(c)))
        self.clicar(linha)
        self.assertTrue(self.na_tela_de_detalhes())
        valor = next(t for t in self.controles(ft.Text) if t.value == MIL_COM_QUEBRAS)
        self.assertIsNone(valor.max_lines)                                       # sem corte
        self.assertEqual(valor.value, self.descricao_no_banco(conta_id))


if __name__ == "__main__":
    unittest.main()
