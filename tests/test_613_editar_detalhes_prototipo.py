"""
Protótipo 6.13 -- Editar conta e Detalhes (ambiente isolado; dados fictícios).

1. Campo Recorrência de Editar com resumo curto ("Mensal · Fixo · Sem término").
2. "Transformar em recorrente" começa "Sem data de término"; Mês e Ano visíveis e desabilitados.
3. Contadores de Nome e Descrição dentro do campo, antes do lápis.
4. "Parcelar esta conta" saiu dos Detalhes e fica no lápis da Recorrência (abaixo de Transformar).
Hoje fixo: 15/09/2026.
"""

import unittest
from datetime import datetime

from apoio_banco import db
from test_612_parcelada_telas import BaseTelas
from test_tela_principal import Evento, percorrer

import flet as ft  # noqa: E402
import main  # noqa: E402
import pagamentos  # noqa: E402


# 6.13 (melhoria B): "Alterar término da recorrência" entre "Alterar tipo de valor" e "Encerrar".
MENU_SERIE = ["Alterar tipo de valor", "Alterar término da recorrência", "Encerrar recorrência"]


class Base(BaseTelas):
    def digitar(self, controle, texto):
        """6.13 (melhoria A): a quantidade de parcelas é digitada (on_change), não escolhida."""
        controle.value = texto
        controle.on_change(Evento(self.pagina, controle))

    def abrir_detalhes(self, nome):
        self.entrar()
        linha = next(c for c in self.controles(ft.Container)
                     if c.data in ("linha_conta", "linha_conta_empilhada")
                     and nome in [t.value for t in percorrer(c) if isinstance(t, ft.Text)])
        self.clicar(linha)
        self.assertTrue(self.existe("tela_detalhes"))

    def abrir_editar(self, nome):
        self.abrir_detalhes(nome)
        self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Editar"))

    def existe(self, data):
        return any(getattr(c, "data", None) == data for c in self.controles())

    def recorrencia(self):
        return self.campo("Recorrência")

    def itens(self):
        return [i.content for i in self.recorrencia().suffix_icon.items]

    def escolher_item(self, rotulo):
        item = next(i for i in self.recorrencia().suffix_icon.items if i.content == rotulo)
        item.on_click(Evento(self.pagina, item))

    def mudar_chave(self, chave, valor):
        chave.value = valor
        chave.on_change(Evento(self.pagina, chave))

    def botao_salvar(self):
        return next(c for c in self.controles(ft.Button) if c.content == "Salvar alterações")

    def series(self):
        return self.consultar("SELECT id, frequencia, data_termino FROM series_recorrencia ORDER BY id")

    def textos(self):
        return [t.value for t in self.controles(ft.Text)]


class TestResumoCurto(unittest.TestCase):
    def test_formatos(self):
        r = main.resumo_curto_recorrencia
        self.assertEqual(r("unica"), "Única · Sem repetição")
        self.assertEqual(r("parcelada", parcelas=11), "Parcelada · 11 parcelas")
        self.assertEqual(r("mensal"), "Mensal · Fixo · Sem término")
        self.assertEqual(r("mensal", True), "Mensal · Variável · Sem término")
        self.assertEqual(r("anual"), "Anual · Fixo · Sem término")
        self.assertEqual(r("mensal", False, "2027-09"), "Mensal · Fixo · Até set/2027")
        self.assertEqual(r("anual", True, "2030-03"), "Anual · Variável · Até mar/2030")
        self.assertEqual([r("mensal", False, f"2027-{m:02d}")[-8:-5] for m in range(1, 13)],
                         ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"])


class TestResumoNoEditar(Base):
    def test_cada_tipo_mostra_o_resumo_salvo(self):
        db.criar_conta_unica(self.usuario_id, "Escola", 500.0, "2026-09-10")
        db.criar_conta_parcelada(self.usuario_id, "Sofá", 1200.0, 11, "2026-09-25")
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-20", "mensal")
        db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-21", "mensal", variavel=True)
        db.criar_serie_recorrente(self.usuario_id, "IPVA", 800.0, "2026-09-22", "anual")
        db.criar_serie_recorrente(self.usuario_id, "Seguro", 80.0, "2026-09-23", "mensal", data_termino="2027-09")
        esperado = {
            "Escola": ("Única · Sem repetição", ["Transformar em recorrente", "Parcelar esta conta"]),
            "Sofá": ("Parcelada · 11 parcelas", ["Alterar parcelamento"]),
            "Aluguel": ("Mensal · Fixo · Sem término", MENU_SERIE),
            "Luz": ("Mensal · Variável · Sem término", MENU_SERIE),
            "IPVA": ("Anual · Fixo · Sem término", MENU_SERIE),
            "Seguro": ("Mensal · Fixo · Até set/2027", MENU_SERIE),
        }
        antes = (self.series(), self.contas())
        for nome, (resumo, itens) in esperado.items():
            with self.subTest(nome=nome):
                self.abrir_editar(nome)
                self.assertEqual(self.recorrencia().value, resumo)
                self.assertEqual(self.itens(), itens)
                self.assertIsNone(self.recorrencia().helper)
        # Abrir Editar nunca muda nada (o término salvo continua o mesmo).
        self.assertEqual((self.series(), self.contas()), antes)
        self.assertEqual([s[2] for s in self.series()], ["2027-07", None, None, None, "2027-09"])


class TestTransformarEmRecorrente(Base):
    def setUp(self):
        super().setUp()
        self.conta = db.criar_conta_unica(self.usuario_id, "Escola", 500.0, "2026-09-10")
        self.abrir_editar("Escola")

    def abrir_transformar(self):
        self.escolher_item("Transformar em recorrente")
        self.assertEqual(self.dlg().title.value, "Transformar em recorrente")
        chave = self.no_dialogo("sem_termino_transformar")
        linha = self.no_dialogo("termino_transformar")
        mes, ano = linha.controls
        return chave, linha, mes, ano

    def test_comeca_sem_termino_e_mes_ano_desabilitados(self):
        chave, linha, mes, ano = self.abrir_transformar()
        self.assertTrue(chave.value)
        self.assertTrue(linha.visible)
        self.assertEqual((mes.disabled, ano.disabled, linha.opacity), (True, True, 0.45))
        self.mudar_chave(chave, False)
        self.assertEqual((mes.disabled, ano.disabled, linha.opacity), (False, False, 1.0))
        self.mudar_chave(chave, True)
        self.assertEqual((mes.disabled, ano.disabled, linha.opacity, linha.visible), (True, True, 0.45, True))
        # Fixo e Variável disponíveis; Fixo por padrão.
        comportamento = self.no_dialogo("comportamento_transformar")
        self.assertEqual([b.content.value for b in comportamento.controls], ["Valor fixo", "Valor variável"])
        self.assertEqual(self.opcao("Mensal").bgcolor, self.opcao("Valor fixo").bgcolor)   # padrões ativos

    def test_mensal_sem_termino_salvo(self):
        self.abrir_transformar()
        self.clicar(self.acao("Transformar"))
        self.assertEqual(self.recorrencia().value, "Mensal · Fixo · Sem término")
        self.assertEqual(self.recorrencia().helper, "Alteração pendente: será aplicada ao salvar.")
        self.assertEqual(self.itens(), ["Desfazer esta alteração"])
        self.assertEqual(self.series(), [])                       # só no Salvar
        self.clicar(self.botao_salvar())
        serie_id, frequencia, termino = self.series()[0]
        self.assertEqual((frequencia, termino), ("mensal", None))
        self.assertEqual(len(self.consultar("SELECT id FROM contas WHERE serie_id = ?", (serie_id,))), 13)

    def test_anual_variavel_com_termino_salvo(self):
        chave, linha, mes, ano = self.abrir_transformar()
        self.clicar(self.opcao("Anual"))
        self.clicar(self.opcao("Valor variável"))
        self.mudar_chave(chave, False)
        mes.value, ano.value = "3", "2029"          # lidos ao confirmar (sem on_select)
        self.clicar(self.acao("Transformar"))
        self.assertEqual(self.recorrencia().value, "Anual · Variável · Até mar/2029")
        self.clicar(self.botao_salvar())
        serie_id, frequencia, termino = self.series()[0]
        self.assertEqual((frequencia, termino), ("anual", "2029-03"))
        self.assertTrue(db.serie_variavel(serie_id))
        self.assertEqual(len(self.consultar("SELECT id FROM contas WHERE serie_id = ?", (serie_id,))), 3)

    def opcao(self, rotulo):
        return next(c for c in percorrer(self.dlg().content) if isinstance(c, ft.Container)
                    and isinstance(c.content, ft.Text) and c.content.value == rotulo)

    def test_cancelar_nao_muda_nada(self):
        chave, linha, mes, ano = self.abrir_transformar()
        self.mudar_chave(chave, False)
        mes.value = "12"
        self.clicar(self.acao("Cancelar"))
        self.assertEqual(self.recorrencia().value, "Única · Sem repetição")
        self.assertIsNone(self.recorrencia().helper)
        self.assertTrue(self.botao_salvar().disabled)
        chave, linha, mes, ano = self.abrir_transformar()          # o diálogo recomeça do padrão
        self.assertTrue(chave.value)
        self.assertEqual((mes.disabled, ano.disabled), (True, True))
        self.clicar(self.acao("Cancelar"))
        self.assertEqual(self.series(), [])

    def test_janela_estreita_empilha_mes_e_ano(self):
        self.pagina.width = 380
        chave, linha, mes, ano = self.abrir_transformar()
        self.assertIsInstance(linha, ft.Column)
        self.assertEqual((mes.disabled, ano.disabled), (True, True))


class TestContadoresInternos(Base):
    def setUp(self):
        super().setUp()
        db.criar_conta_unica(self.usuario_id, "Mensalidade da escola Aurora", 500.0, "2026-09-10")
        self.abrir_editar("Mensalidade da escola Aurora")

    def partes(self, rotulo):
        campo = self.campo(rotulo)
        linha = campo.suffix_icon
        self.assertIsInstance(linha, ft.Row)
        contador, lapis = linha.controls
        return campo, contador, lapis

    def test_nome_e_descricao_com_contador_dentro_e_lapis(self):
        for rotulo, chave, texto, nome_lapis in (
                ("Nome da conta", "nome_conta", "28/30", "Editar nome da conta"),
                ("Descrição (opcional)", "descricao", "0/250", "Editar descrição")):
            with self.subTest(rotulo=rotulo):
                campo, contador, lapis = self.partes(rotulo)
                self.assertEqual((contador.data, contador.value), (f"contador_{chave}_edicao", texto))
                self.assertIsNone(campo.counter)                  # nenhuma linha reservada embaixo
                self.assertEqual(lapis.data, "pp_lapis")
                self.assertEqual(lapis.tooltip, nome_lapis)

    def test_limite_30_e_250_continuam(self):
        campo, contador, _ = self.partes("Nome da conta")
        campo.value = "Mensalidade da escola Auroras"
        campo.on_change(Evento(self.pagina, campo))
        self.assertEqual(contador.value, "29/30")
        self.assertFalse(self.botao_salvar().disabled)
        campo.value = "Mensalidade da escola Aurora 123"         # 32: recusado inteiro
        campo.on_change(Evento(self.pagina, campo))
        self.assertEqual((campo.value, contador.value, campo.helper),
                         ("Mensalidade da escola Auroras", "29/30", "Limite atingido"))
        descricao, contador_d, _ = self.partes("Descrição (opcional)")
        descricao.value = "d" * 250
        descricao.on_change(Evento(self.pagina, descricao))
        self.assertEqual(contador_d.value, "250/250")
        descricao.value = "d" * 251
        descricao.on_change(Evento(self.pagina, descricao))
        self.assertEqual((len(descricao.value), contador_d.value, descricao.helper), (250, "250/250", "Limite atingido"))


class TestParcelarEmEditar(Base):
    def test_detalhes_sem_parcelar_e_com_pagamentos_e_editar(self):
        db.criar_conta_unica(self.usuario_id, "Geladeira", 2400.0, "2026-09-30")
        self.abrir_detalhes("Geladeira")
        self.assertFalse(self.existe("parcelar_conta"))
        self.assertNotIn("Parcelar esta conta", [getattr(c, "content", None) for c in self.controles()])
        botoes = [getattr(c, "content", None) for c in self.controles((ft.Button, ft.OutlinedButton))]
        self.assertIn("Marcar como paga", botoes)
        self.assertIn("Registrar pagamento parcial", botoes)
        self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Editar"))
        self.assertEqual(self.recorrencia().label, "Recorrência")

    def test_parcelar_abaixo_de_transformar_e_cancelar_nao_grava(self):
        conta = db.criar_conta_unica(self.usuario_id, "Geladeira", 100.0, "2026-09-30")
        self.abrir_editar("Geladeira")
        self.assertEqual(self.itens(), ["Transformar em recorrente", "Parcelar esta conta"])
        antes = self.contas()
        self.escolher_item("Parcelar esta conta")
        self.assertEqual(self.dlg().data, "dialogo_parcelar")
        self.digitar(self.no_dialogo("quantidade_parcelas_parcelar"), "3")
        linhas = [t for t in self.textos_do_dialogo() if t.startswith("Parcela ")]
        self.assertEqual(linhas, ["Parcela 1 de 3 · 30/09/2026 · R$ 33,34", "Parcela 2 de 3 · 30/10/2026 · R$ 33,33",
                                  "Parcela 3 de 3 · 30/11/2026 · R$ 33,33"])
        self.clicar(self.acao("Cancelar"))
        self.assertEqual(self.contas(), antes)
        self.assertEqual(self.consultar("SELECT serie_id FROM contas WHERE id = ?", (conta,)), [(None,)])

    def test_parcelar_grava_e_volta_aos_detalhes(self):
        conta = db.criar_conta_unica(self.usuario_id, "Geladeira", 100.0, "2026-09-30")
        self.abrir_editar("Geladeira")
        self.escolher_item("Parcelar esta conta")
        self.digitar(self.no_dialogo("quantidade_parcelas_parcelar"), "3")
        self.clicar(self.acao("Parcelar"))
        serie_id = self.consultar("SELECT serie_id FROM contas WHERE id = ?", (conta,))[0][0]
        self.assertEqual(db.obter_identificacao(serie_id, conta), {"tipo": "parcela", "posicao": 1, "total": 3})
        self.assertEqual([v for (v,) in self.consultar("SELECT valor FROM contas ORDER BY data_vencimento")],
                         [33.34, 33.33, 33.33])
        self.assertTrue(self.existe("tela_detalhes"))
        self.assertIn("Parcela 1 de 3", self.textos())
        self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Editar"))
        self.assertEqual(self.recorrencia().value, "Parcelada · 3 parcelas")
        self.assertEqual(self.itens(), ["Alterar parcelamento"])

    def test_com_pagamento_mostra_o_motivo_e_nada_grava(self):
        conta = db.criar_conta_unica(self.usuario_id, "TV", 900.0, "2026-09-30")
        pagamentos.registrar_pagamento_parcial(conta, 100_00, "2026-09-10")
        antes = (self.contas(), self.consultar("SELECT * FROM pp_pagamentos"))
        self.abrir_editar("TV")
        self.assertIn("Parcelar esta conta", self.itens())
        self.escolher_item("Parcelar esta conta")
        self.assertEqual(self.dlg().data, "dialogo_parcelar_recusado")
        self.assertEqual(self.dlg().content.value, db.MENSAGEM_UNICA_COM_PAGAMENTOS)
        self.clicar(self.acao("Entendi"))
        self.assertEqual((self.contas(), self.consultar("SELECT * FROM pp_pagamentos")), antes)

    def test_com_alteracao_nao_salva_nao_abre(self):
        db.criar_conta_unica(self.usuario_id, "Geladeira", 100.0, "2026-09-30")
        self.abrir_editar("Geladeira")
        nome = self.campo("Nome da conta")
        nome.value = "Geladeira nova"
        nome.on_change(Evento(self.pagina, nome))
        antes = self.contas()
        self.escolher_item("Parcelar esta conta")
        self.assertNotEqual(self.dlg().data, "dialogo_parcelar")
        self.assertEqual((self.dlg().title.value, self.dlg().content.value),
                         ("Há alterações não salvas", main.TEXTO_SALVE_ANTES_DA_ACAO))
        self.assertEqual(self.contas(), antes)

    def test_recorrencia_e_parcela_sem_parcelar(self):
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-20", "mensal")
        db.criar_conta_parcelada(self.usuario_id, "Sofá", 1200.0, 6, "2026-09-25")
        for nome in ("Aluguel", "Sofá"):
            with self.subTest(nome=nome):
                self.abrir_editar(nome)
                self.assertNotIn("Parcelar esta conta", self.itens())
                self.assertNotIn("Transformar em recorrente", self.itens())

    def test_transformacao_pendente_esconde_parcelar(self):
        db.criar_conta_unica(self.usuario_id, "Escola", 500.0, "2026-09-10")
        self.abrir_editar("Escola")
        self.escolher_item("Transformar em recorrente")
        self.clicar(self.acao("Transformar"))
        self.assertEqual(self.itens(), ["Desfazer esta alteração"])
        self.escolher_item("Desfazer esta alteração")
        self.assertEqual(self.itens(), ["Transformar em recorrente", "Parcelar esta conta"])


class TestPagamentosNosDetalhes(Base):
    def test_pagamento_parcial_e_valor_pendente_continuam(self):
        conta = db.criar_conta_unica(self.usuario_id, "Escola", 500.0, "2026-09-10")
        pagamentos.registrar_pagamento_parcial(conta, 100_00, "2026-09-05")
        self.abrir_detalhes("Escola")
        self.assertIn("R$ 100,00", self.textos())                   # total pago
        self.assertIn("R$ 400,00", self.textos())                   # saldo devedor
        botoes = {c.content: c for c in self.controles((ft.Button, ft.OutlinedButton))}
        self.assertFalse(botoes["Marcar como paga"].disabled)
        self.assertFalse(botoes["Registrar pagamento parcial"].disabled)

    def test_valor_pendente_bloqueia_pagamentos_com_motivo(self):
        # Série variável iniciada em agosto: a ocorrência de setembro fica com valor pendente.
        db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-08-21", "mensal", variavel=True)
        self.abrir_detalhes("Luz")
        self.assertTrue(self.existe("motivo_pagamento_bloqueado"))
        botoes = {c.content: c for c in self.controles((ft.Button, ft.OutlinedButton))}
        self.assertTrue(botoes["Marcar como paga"].disabled)
        self.assertTrue(botoes["Registrar pagamento parcial"].disabled)
        self.assertFalse(self.existe("parcelar_conta"))


if __name__ == "__main__":
    unittest.main()
