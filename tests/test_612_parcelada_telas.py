"""
Sino 6.12 (experimental), Etapa 6 -- interface mínima da conta Parcelada.

Nova conta: "Parcelada" no diálogo "Configurar recorrência" (Única, Parcelada,
Mensal, Anual), quantidade de 2 a 36, "Valor total" e prévia antes de salvar.
Detalhes: "Parcelar esta conta" só para Única (R1: com registro de pagamento,
só o motivo), com quantidade e prévia; parcela mostra a frase do parcelamento e,
em Editar, a Recorrência não oferece "Alterar frequência" nem "Encerrar".
Hoje fixo: 15/09/2026; nenhuma janela é aberta.
"""

import unittest
from datetime import datetime

from apoio_banco import db
from test_nova_conta_recorrencia import Base
from test_tela_principal import Evento, percorrer

import flet as ft  # noqa: E402
import main  # noqa: E402
import pagamentos  # noqa: E402


class BaseTelas(Base):
    def campo(self, rotulo, raizes=None):
        return next(c for c in self.controles((ft.TextField, ft.Dropdown), raizes) if c.label == rotulo)

    def abertos(self):
        return [d for d in self.pagina.dialogos if d.open]

    def dlg(self):
        return self.abertos()[-1]

    def no_dialogo(self, data):
        return next(c for c in percorrer(self.dlg().content) if getattr(c, "data", None) == data)

    def textos_do_dialogo(self):
        return [t.value for t in percorrer(self.dlg().content) if isinstance(t, ft.Text)]

    def acao(self, texto):
        return next(b for b in self.dlg().actions if b.content == texto)

    def escolher(self, controle, valor):
        controle.value = valor
        if isinstance(controle, ft.Dropdown):
            controle.on_select(Evento(self.pagina, controle))
        else:  # 6.13 (E5): a quantidade de parcelas é digitada (com setas), não escolhida numa lista
            controle.on_change(Evento(self.pagina, controle))

    def contas(self):
        return self.consultar("SELECT nome, valor, data_vencimento, serie_id FROM contas ORDER BY id")

    # Sino 6.13.1: Nova conta da 6.13 -- tipo nos cartões do formulário (tipo_conta_*), valor em
    # "valor_nova_conta" (rótulo conforme o tipo) e término em campo e diálogo próprios.
    def nc_controle(self, data, raizes=None):
        return next(c for c in self.controles(None, raizes) if getattr(c, "data", None) == data)

    def nc_existe(self, data):
        return any(getattr(c, "data", None) == data for c in self.controles())

    def nc_tipo(self, valor):
        self.clicar(self.nc_controle(f"tipo_conta_{valor}"))

    def nc_rotulos_dos_tipos(self):
        return [[t.value for t in percorrer(self.nc_controle(f"tipo_conta_{v}")) if isinstance(t, ft.Text)][0]
                for v in ("unica", "parcelada", "mensal", "anual")]

    def nc_definir_termino(self, sem_termino, mes=None, ano=None):
        self.clicar(self.nc_controle("termino_nova_conta").suffix_icon)
        self.assertEqual(self.dlg().data, "dialogo_termino")
        chave = self.no_dialogo("sem_termino_recorrencia")
        chave.value = sem_termino
        chave.on_change(Evento(self.pagina, chave))
        if mes is not None:
            self.escolher(self.campo("Mês", [self.dlg().content]), mes)
            self.escolher(self.campo("Ano", [self.dlg().content]), ano)
        self.clicar(self.acao("Confirmar"))
        self.assertEqual([d for d in self.abertos() if d.data == "dialogo_termino"], [])

    def nc_preencher(self, nome, valor, data=(2026, 9, 20)):
        """Nome, valor (qualquer rótulo do tipo) e a data pelo calendário da conta comum (1º do overlay)."""
        self.campo("Nome da conta").value = nome
        campo_valor = self.nc_controle("valor_nova_conta")
        campo_valor.value = valor
        if campo_valor.on_change:
            campo_valor.on_change(Evento(self.pagina, campo_valor))
        seletor = next(o for o in self.pagina.overlay if isinstance(o, ft.DatePicker))
        seletor.value = datetime(*data)
        seletor.on_change(Evento(self.pagina, seletor))


class TestNovaContaParcelada(BaseTelas):
    def setUp(self):
        super().setUp()
        self.entrar()
        self.clicar(next(c for c in self.controles() if getattr(c, "data", None) == "nova_conta"))

    # Sino 6.13.1: tipo no cartão "Parcelada" e quantidade digitada no formulário (6.13).
    def configurar_parcelada(self, quantidade):
        self.nc_tipo("parcelada")
        self.escolher(self.nc_controle("quantidade_parcelas_nova_conta"), quantidade)

    def preencher(self, nome, valor, data):
        self.nc_preencher(nome, valor, data)

    def salvar(self):
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Salvar conta"))

    def test_quatro_tipos_e_campos_da_parcelada(self):
        self.assertEqual(self.nc_rotulos_dos_tipos(), ["Única", "Parcelada", "Recorrente mensal", "Recorrente anual"])
        self.assertFalse(self.nc_existe("quantidade_parcelas_nova_conta"))
        self.nc_tipo("parcelada")
        self.assertTrue(self.nc_existe("quantidade_parcelas_nova_conta"))
        self.assertFalse(self.nc_existe("termino_nova_conta"))         # sem término/término só em Mensal e Anual
        self.nc_tipo("mensal")
        self.assertTrue(self.nc_existe("termino_nova_conta"))
        self.assertFalse(self.nc_existe("quantidade_parcelas_nova_conta"))
        self.nc_tipo("parcelada")
        quantidade = self.nc_controle("quantidade_parcelas_nova_conta")
        estimado = self.nc_controle("valor_por_parcela_estimado")
        self.nc_controle("valor_nova_conta").value = "1.000,00"
        for digitado, valido in (("1", False), ("2", True), ("36", True), ("37", False)):   # 2 a 36 (D4)
            with self.subTest(quantidade=digitado):
                self.escolher(quantidade, digitado)
                self.assertEqual(main.quantidade_de_parcelas(quantidade.value) is not None, valido)
                self.assertEqual(estimado.value != "—", valido)
        self.escolher(quantidade, "12")
        self.assertEqual(estimado.value, "R$ 83,33 (1ª: R$ 83,37)")    # 12 parcelas de R$ 1.000,00
        self.assertEqual(self.nc_controle("valor_nova_conta").label, "Valor total da conta")

    def test_previa_antes_de_salvar_e_gravacao(self):
        self.configurar_parcelada("12")
        self.preencher("Notebook", "1.000,00", (2026, 10, 31))
        self.salvar()
        self.assertEqual(self.dlg().data, "dialogo_previa_parcelamento")
        linhas = [t for t in self.textos_do_dialogo() if t.startswith("Parcela ")]
        self.assertEqual(len(linhas), 12)
        self.assertEqual(linhas[0], "Parcela 1 de 12 · 31/10/2026 · R$ 83,37")
        self.assertEqual(linhas[1], "Parcela 2 de 12 · 30/11/2026 · R$ 83,33")
        self.assertEqual(linhas[4], "Parcela 5 de 12 · 28/02/2027 · R$ 83,33")
        self.assertEqual(self.contas(), [])                       # nada gravado antes de confirmar
        self.clicar(self.acao("Cancelar"))
        self.assertEqual(self.abertos(), [])
        self.assertEqual(self.contas(), [])
        self.salvar()
        self.clicar(self.acao("Salvar conta"))
        contas = self.contas()
        self.assertEqual(len(contas), 12)
        self.assertEqual(round(sum(v for _, v, _, _ in contas), 2), 1000.0)
        self.assertEqual(self.consultar("SELECT quantidade_original, valor_total_original_centavos FROM parcelamentos"),
                         [(12, 100000)])

    def test_recusa_aparece_no_formulario(self):
        self.configurar_parcelada("2")
        self.preencher("Bala", "0,01", (2026, 10, 5))
        self.salvar()
        self.assertEqual(self.abertos(), [])
        self.assertIn(db.MENSAGEM_VALOR_PEQUENO_PARA_PARCELAS, [t.value for t in self.controles(ft.Text)])
        self.assertEqual(self.contas(), [])

    def test_mensal_continua_igual(self):
        self.nc_tipo("mensal")
        self.assertFalse(self.nc_existe("quantidade_parcelas_nova_conta"))
        self.assertFalse(self.nc_existe("valor_por_parcela_estimado"))
        rotulos = [c.label for c in self.controles(ft.TextField)]
        self.assertIn(main.ROTULO_VALOR_RECORRENTE["mensal"], rotulos)     # "Valor do primeiro mês"
        self.assertNotIn("Valor total da conta", rotulos)


class TestDetalhesEEditar(BaseTelas):
    def abrir_detalhes(self, nome):
        self.entrar()
        linha = next(c for c in self.controles(ft.Container)
                     if c.data in ("linha_conta", "linha_conta_empilhada")
                     and nome in [t.value for t in percorrer(c) if isinstance(t, ft.Text)])
        self.clicar(linha)

    def botao_parcelar(self):
        # Protótipo 6.13 (E1): "Parcelar esta conta" é item do lápis da Recorrência em Editar.
        editar = [c for c in self.controles(ft.Button) if c.content == "Editar"]
        if editar:
            self.clicar(editar[0])
        campo = next(c for c in self.controles(ft.TextField) if c.label == "Recorrência")
        return [i for i in (campo.suffix_icon.items or []) if i.content == "Parcelar esta conta"]

    def test_unica_parcelada_pelos_detalhes(self):
        conta = db.criar_conta_unica(self.usuario_id, "Geladeira", 2400.0, "2026-09-30")
        self.abrir_detalhes("Geladeira")
        self.clicar(self.botao_parcelar()[0])
        self.assertEqual(self.dlg().data, "dialogo_parcelar")
        self.assertEqual(len([t for t in self.textos_do_dialogo() if t.startswith("Parcela ")]), 2)
        self.escolher(self.no_dialogo("quantidade_parcelas_parcelar"), "12")
        linhas = [t for t in self.textos_do_dialogo() if t.startswith("Parcela ")]
        self.assertEqual(linhas[0], "Parcela 1 de 12 · 30/09/2026 · R$ 200,00")
        self.assertEqual(linhas[-1], "Parcela 12 de 12 · 30/08/2027 · R$ 200,00")
        self.assertEqual(self.consultar("SELECT serie_id FROM contas WHERE id = ?", (conta,)), [(None,)])
        self.clicar(self.acao("Parcelar"))
        serie_id = self.consultar("SELECT serie_id FROM contas WHERE id = ?", (conta,))[0][0]
        self.assertEqual(db.obter_identificacao(serie_id, conta), {"tipo": "parcela", "posicao": 1, "total": 12})
        self.assertEqual(len(self.contas()), 12)

    def test_unica_com_pagamento_mostra_o_motivo(self):
        conta = db.criar_conta_unica(self.usuario_id, "TV", 900.0, "2026-09-30")
        pagamentos.registrar_pagamento_parcial(conta, 100_00, "2026-09-10")
        antes = self.contas()
        self.abrir_detalhes("TV")
        self.clicar(self.botao_parcelar()[0])
        self.assertEqual(self.dlg().data, "dialogo_parcelar_recusado")
        self.assertIn(db.MENSAGEM_UNICA_COM_PAGAMENTOS, [self.dlg().content.value])
        self.clicar(self.acao("Entendi"))
        self.assertEqual(self.contas(), antes)

    def test_recorrencia_e_parcela_sem_botao_parcelar(self):
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-20", "mensal")
        db.criar_conta_parcelada(self.usuario_id, "Sofá", 1200.0, 6, "2026-09-25")
        self.abrir_detalhes("Aluguel")
        self.assertEqual(self.botao_parcelar(), [])
        self.abrir_detalhes("Sofá")
        self.assertEqual(self.botao_parcelar(), [])

    def test_parcela_detalhes_e_editar_sem_mudar_de_tipo(self):
        db.criar_conta_parcelada(self.usuario_id, "Sofá", 1200.0, 6, "2026-09-25")
        self.abrir_detalhes("Sofá")
        textos = [t.value for t in self.controles(ft.Text)]
        self.assertIn("Esta conta é parcelada em 6 parcelas mensais, até fevereiro de 2027.", textos)
        self.assertIn("Parcela 1 de 6", textos)
        self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Editar"))
        recorrencia = next(c for c in self.controles(ft.TextField) if c.label == "Recorrência")
        self.assertEqual(recorrencia.value, "Parcelada · 6 parcelas")  # 6.13 (E2): resumo curto em Editar
        # Ajustes pós-validação manual (A): só "Alterar parcelamento" -- sem Alterar frequência / Encerrar.
        self.assertEqual([i.content for i in recorrencia.suffix_icon.items], ["Alterar parcelamento"])

    def test_recorrencia_continua_com_o_menu(self):
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-20", "mensal")
        self.abrir_detalhes("Aluguel")
        self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Editar"))
        menu = next(c for c in self.controles(ft.TextField) if c.label == "Recorrência").suffix_icon
        self.assertEqual([i.content for i in menu.items], ["Alterar tipo de valor", "Alterar término da recorrência", "Encerrar recorrência"])  # R6; ajuste D


if __name__ == "__main__":
    unittest.main()
