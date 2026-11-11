"""
Sino 6.12 (decisão da autora, 07/11/2026) — descrição de até 250 caracteres.

Substitui o limite de 1000 da ERS v7.0 (5.45, E6/M4; antes 500). Sucede
`test_descricao_1000.py` com os mesmos fluxos (CT133, decisões M4-1 e M4-2)
e os casos pedidos na decisão: vazia, 1, 249, 250 e 251 caracteres, na
criação e na edição, na interface e no banco; descrição antiga acima do
limite (P4) exibida inteira e salva só depois de reduzida, sem perder os
dados financeiros.

Na interface: contador "x/250" e dica "Até 250 caracteres"; campo de 2 a 8
linhas; recusa do 251º caractere com "Limite atingido" e som. Fluxos reais da
interface sobre páginas falsas e bancos temporários; o som é simulado e
nenhuma janela é aberta.
"""

import unittest
from unittest import mock

import test_tela_principal
from apoio_banco import DataFixa, TesteComBancoTemporario, db
import limites  # noqa: E402  (depois de apoio_banco, que põe database/ no caminho)
import pagamentos  # noqa: E402
from test_tela_principal import Evento, ft, main, percorrer


EMOJI_COMPOSTO = "👩‍💻"                       # 3 pontos de código, 1 caractere percebido
LIMITE = 250
NO_LIMITE = "d" * 249 + EMOJI_COMPOSTO         # 250 caracteres percebidos
UM_ABAIXO = "d" * 249                          # 249
COM_QUEBRAS = ("linha\n" * 41) + "fim!"        # 250, com quebras internas
LEGADA = "x" * 300                             # acima do limite (dado antigo)


# Protótipo 6.13 (E3): Nome e Descrição de Editar têm o contador DENTRO do campo, antes do lápis
# (suffix_icon = Row(contador, lápis)). Só os contadores de Editar (data "contador_*_edicao").
def lapis_de(campo):
    s = campo.suffix_icon
    return s.controls[-1] if isinstance(s, ft.Row) else s


def contador_de(campo):
    s = campo.suffix_icon
    if isinstance(s, ft.Row):
        for c in s.controls:
            if isinstance(c, ft.Text) and str(c.data or "").startswith("contador_") and str(c.data).endswith("_edicao"):
                return c.value
    return campo.counter

ROTULO = "Descrição (opcional)"


def som_simulado():
    """Substitui o som da recusa (a suíte nunca toca áudio)."""
    return mock.patch.object(main.aviso_sonoro.aviso_limite, "tocar", return_value=True)


class BaseDescricao250(TesteComBancoTemporario):
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

    def assert_campo(self, campo, contador):
        self.assertEqual((campo.multiline, campo.min_lines, campo.max_lines), (True, 2, 8))  # M4-2
        self.assertEqual(campo.hint_text, "Até 250 caracteres")                            # Q1
        self.assertEqual(contador_de(campo), contador)
        self.assertIsNone(getattr(campo, "max_length", None))                              # sem corte

    def assert_recusa_do_251(self, campo):
        self.digitar(campo, NO_LIMITE)
        self.assertEqual((campo.value, contador_de(campo), campo.helper), (NO_LIMITE, "250/250", None))
        with som_simulado() as tocar:
            self.digitar(campo, NO_LIMITE + "!")
        self.assertEqual((campo.value, contador_de(campo), campo.helper), (NO_LIMITE, "250/250", "Limite atingido"))
        tocar.assert_called_once_with()


class TestLimiteNoBanco(TesteComBancoTemporario):
    """Backend: criação (única e série) e edição (Somente este mês / Este mês em diante)."""

    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def test_constante(self):
        self.assertEqual(limites.LIMITE_DESCRICAO, LIMITE)

    def test_criacao_vazia_1_249_250_aceitas_e_251_recusada(self):
        for descricao, esperado in ((None, None), ("", None), ("   ", None), ("a", "a"),
                                    (UM_ABAIXO, UM_ABAIXO), (NO_LIMITE, NO_LIMITE), (COM_QUEBRAS, COM_QUEBRAS)):
            with self.subTest(n=limites.contar_caracteres(descricao)):
                conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-01", descricao=descricao)
                self.assertEqual(self.consultar("SELECT descricao FROM contas WHERE id = ?", (conta_id,))[0][0],
                                 esperado)
        total = self.consultar("SELECT COUNT(*) FROM contas")[0][0]
        with self.assertRaises(limites.LimiteDeCaracteresError) as contexto:
            db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-01", descricao=NO_LIMITE + "x")
        self.assertEqual(str(contexto.exception), "A descrição pode ter no máximo 250 caracteres (atual: 251).")
        with self.assertRaises(limites.LimiteDeCaracteresError):
            db.criar_serie_recorrente(self.usuario_id, "Luz", 10.0, "2026-10-01", "mensal", descricao="d" * 251)
        with self.assertRaises(limites.LimiteDeCaracteresError):
            db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-10-01", descricao="d" * 251)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas")[0][0], total)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM series_recorrencia")[0][0], 0)

    def test_edicao_250_aceita_e_251_recusada_sem_gravar(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Escola", 700.0, "2026-10-10", "mensal",
                                                  data_termino="2027-01", descricao="Curta")
        self.assertTrue(db.editar_conta_ocorrencia(ids[0], descricao=NO_LIMITE))
        self.assertTrue(db.editar_conta_serie(ids[1], descricao=UM_ABAIXO))
        antes = self.consultar("SELECT * FROM contas ORDER BY id"), self.consultar("SELECT * FROM series_recorrencia")
        for funcao in (db.editar_conta_ocorrencia, db.editar_conta_serie):
            with self.subTest(funcao=funcao.__name__), self.assertRaises(limites.LimiteDeCaracteresError):
                funcao(ids[2], valor=1.0, descricao="d" * 251)
        self.assertEqual((self.consultar("SELECT * FROM contas ORDER BY id"),
                          self.consultar("SELECT * FROM series_recorrencia")), antes)

    def test_parcelada_com_250(self):
        serie_id, ids = db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-10-01",
                                                 descricao=NO_LIMITE)
        self.assertEqual({self.consultar("SELECT descricao FROM contas WHERE id = ?", (i,))[0][0] for i in ids},
                         {NO_LIMITE})


class TestNovaConta(BaseDescricao250):
    def test_campo_contador_e_dica(self):  # CT133
        self.abrir_nova_conta()
        self.assert_campo(self.campo_descricao(), "0/250")

    def test_250_aceito_e_251_recusado_com_aviso_e_som(self):  # CT133
        self.abrir_nova_conta()
        self.assert_recusa_do_251(self.campo_descricao())

    def test_contador_com_1_e_249(self):
        self.abrir_nova_conta()
        campo = self.campo_descricao()
        for texto, contador in (("a", "1/250"), (UM_ABAIXO, "249/250"), ("", "0/250")):
            self.digitar(campo, texto)
            self.assertEqual((contador_de(campo), campo.helper), (contador, None))


class TestEditarConta(BaseDescricao250):
    def test_campo_contador_e_recusa(self):  # CT133
        db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-05", descricao="Curta")
        self.abrir_edicao_pelo_lapis()
        campo = self.campo_descricao()
        self.assert_campo(campo, "5/250")
        self.assert_recusa_do_251(campo)

    def test_salvar_conta_unica_com_250(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-05")
        self.abrir_edicao_pelo_lapis()
        self.digitar(self.campo_descricao(), COM_QUEBRAS)
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.pagina.show_dialog.call_args[0][0].title.value, "Alteração salva")
        self.assertEqual(self.descricao_no_banco(conta_id), COM_QUEBRAS)

    def test_remover_descricao(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-05", descricao="Curta")
        self.abrir_edicao_pelo_lapis()
        self.digitar(self.campo_descricao(), "")
        self.clicar(self.botao("Salvar alterações"))
        self.assertIsNone(self.descricao_no_banco(conta_id))

    def salvar_serie_com_escopo(self, escopo):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Escola", 700.0, "2026-10-10", "mensal",
                                                  data_termino="2027-01", descricao="Curta")
        self.abrir_edicao_pelo_lapis()
        self.digitar(self.campo_descricao(), NO_LIMITE)
        self.clicar(self.botao("Salvar alterações"))
        dialogo = self.pagina.show_dialog.call_args[0][0]
        next(a for a in dialogo.actions if a.content == escopo).on_click(Evento(self.pagina))
        return serie_id, ids

    def test_salvar_serie_somente_este_mes_com_250(self):
        serie_id, ids = self.salvar_serie_com_escopo("Somente este mês")
        self.assertEqual([self.descricao_no_banco(c) for c in ids], [NO_LIMITE, "Curta", "Curta", "Curta"])
        self.assertEqual(self.descricao_do_modelo(serie_id), "Curta")

    def test_salvar_serie_este_mes_em_diante_com_250(self):
        serie_id, ids = self.salvar_serie_com_escopo("Este mês em diante")
        self.assertEqual({self.descricao_no_banco(c) for c in ids}, {NO_LIMITE})
        self.assertEqual(self.descricao_do_modelo(serie_id), NO_LIMITE)

    def descricao_do_modelo(self, serie_id):
        return self.consultar("SELECT descricao FROM series_recorrencia WHERE id = ?", (serie_id,))[0][0]


class TestDescricaoLegada(BaseDescricao250):
    """CT109 / P4 com o novo limite: dado antigo acima de 250 (por exemplo, gravado com o
    limite de 1000) é exibido inteiro, não é cortado nem apagado; só salva depois de reduzido;
    valor e pagamentos não mudam por causa disso."""

    def inserir_legada(self):
        return self.executar(
            "INSERT INTO contas (usuario_id, nome, valor, data_vencimento, status, descricao) "
            "VALUES (?, 'Antiga', 10.0, '2026-10-05', 'pendente', ?)",
            (self.usuario_id, LEGADA),
        )

    def test_legada_acima_de_250(self):
        conta_id = self.inserir_legada()
        pagamentos.registrar_pagamento_parcial(conta_id, 4_00, "2026-09-10")
        financeiro = self.consultar("SELECT valor, status FROM contas WHERE id = ?", (conta_id,))
        pagos = self.consultar("SELECT * FROM pp_pagamentos")
        self.abrir_edicao_pelo_lapis()
        campo = self.campo_descricao()
        self.assertEqual((campo.value, contador_de(campo)), (LEGADA, "300/250"))     # sem corte
        self.assertEqual(campo.error, "A descrição pode ter no máximo 250 caracteres (atual: 300).")

        self.clicar(self.botao("Salvar alterações"))                            # sem reduzir: recusado
        self.assertIn("A descrição pode ter no máximo 250 caracteres (atual: 300).", self.textos())
        self.assertEqual(self.descricao_no_banco(conta_id), LEGADA)

        with som_simulado() as tocar:
            self.digitar(campo, LEGADA + "x")                                   # não cresce
        self.assertEqual(campo.value, LEGADA)
        tocar.assert_called_once_with()

        self.digitar(campo, "x" * 250)                                          # reduzir é permitido
        self.assertEqual((contador_de(campo), campo.error), ("250/250", None))
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.descricao_no_banco(conta_id), "x" * 250)
        self.assertEqual(self.consultar("SELECT valor, status FROM contas WHERE id = ?", (conta_id,)), financeiro)
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos"), pagos)

    def test_legada_nos_detalhes_inteira_e_pagamento_continua(self):
        conta_id = self.inserir_legada()
        self.assertTrue(db.marcar_conta_como_paga(conta_id, "2026-09-12"))   # não envia a descrição
        self.assertEqual(self.descricao_no_banco(conta_id), LEGADA)


class TestDetalhes(BaseDescricao250):
    def test_descricao_de_250_inteira_com_quebras(self):  # 5.45 / 5.22 (CT58)
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-05", descricao=COM_QUEBRAS)
        self.entrar()
        self.ir_para_outubro()
        linha = next(c for c in self.controles(ft.Container)
                     if c.on_click is not None and isinstance(c.content, ft.Row) and c.border is not None
                     and any(isinstance(t, ft.Text) and t.value == "Luz" for t in percorrer(c)))
        self.clicar(linha)
        self.assertTrue(self.na_tela_de_detalhes())
        valor = next(t for t in self.controles(ft.Text) if t.value == COM_QUEBRAS)
        self.assertIsNone(valor.max_lines)                                       # sem corte
        self.assertEqual(valor.value, self.descricao_no_banco(conta_id))


if __name__ == "__main__":
    unittest.main()
