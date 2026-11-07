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
        controle.on_select(Evento(self.pagina, controle))

    def contas(self):
        return self.consultar("SELECT nome, valor, data_vencimento, serie_id FROM contas ORDER BY id")


class TestNovaContaParcelada(BaseTelas):
    def setUp(self):
        super().setUp()
        self.entrar()
        self.clicar(next(c for c in self.controles(ft.Container) if c.data == "nova_conta"))

    def configurar_parcelada(self, quantidade):
        self.clicar(self.campo("Recorrência").suffix_icon)
        self.clicar(self.no_dialogo("tipo_recorrencia_parcelada"))
        self.escolher(self.no_dialogo("quantidade_parcelas_nova_conta"), quantidade)
        self.clicar(self.acao("Confirmar"))

    def preencher(self, nome, valor, data):
        for c in self.controles(ft.TextField):
            if c.label == "Nome da conta":
                c.value = nome
            elif c.label in ("Valor", "Valor total"):
                c.value = valor
        seletor = next(o for o in self.pagina.overlay if isinstance(o, ft.DatePicker))
        seletor.value = datetime(*data)
        seletor.on_change(Evento(self.pagina, seletor))

    def salvar(self):
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Salvar conta"))

    def test_quatro_tipos_e_campos_da_parcelada(self):
        self.clicar(self.campo("Recorrência").suffix_icon)
        botoes = [c for c in percorrer(self.dlg().content) if str(getattr(c, "data", "")).startswith("tipo_recorrencia_")]
        self.assertEqual([b.content for b in botoes], ["Única", "Parcelada", "Mensal", "Anual"])
        quantidade = self.no_dialogo("quantidade_parcelas_nova_conta")
        self.assertFalse(quantidade.visible)
        self.clicar(self.no_dialogo("tipo_recorrencia_parcelada"))
        self.assertTrue(quantidade.visible)
        chave = self.no_dialogo("sem_termino_recorrencia")
        linha_da_chave = next(c for c in percorrer(self.dlg().content)
                              if isinstance(c, ft.Row) and chave in c.controls)
        self.assertFalse(linha_da_chave.visible)                  # sem término/término só em Mensal e Anual
        self.clicar(self.no_dialogo("tipo_recorrencia_mensal"))
        self.assertTrue(linha_da_chave.visible)
        self.assertFalse(quantidade.visible)
        self.clicar(self.no_dialogo("tipo_recorrencia_parcelada"))
        self.assertEqual([o.key for o in quantidade.options], [str(n) for n in range(2, 37)])
        self.escolher(quantidade, "12")
        self.clicar(self.acao("Confirmar"))
        self.assertEqual(self.campo("Recorrência").value, "Parcelada em 12 parcelas")
        self.assertIn("Valor total", [c.label for c in self.controles(ft.TextField)])

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
        self.clicar(self.campo("Recorrência").suffix_icon)
        self.clicar(self.no_dialogo("tipo_recorrencia_mensal"))
        self.assertFalse(self.no_dialogo("quantidade_parcelas_nova_conta").visible)
        self.clicar(self.acao("Confirmar"))
        self.assertIn("Valor", [c.label for c in self.controles(ft.TextField)])
        self.assertNotIn("Valor total", [c.label for c in self.controles(ft.TextField)])


class TestDetalhesEEditar(BaseTelas):
    def abrir_detalhes(self, nome):
        self.entrar()
        linha = next(c for c in self.controles(ft.Container)
                     if c.data in ("linha_conta", "linha_conta_empilhada")
                     and nome in [t.value for t in percorrer(c) if isinstance(t, ft.Text)])
        self.clicar(linha)

    def botao_parcelar(self):
        return [c for c in self.controles() if getattr(c, "data", None) == "parcelar_conta"]

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
        self.assertEqual(recorrencia.value, "Esta conta é parcelada em 6 parcelas mensais, até fevereiro de 2027.")
        self.assertIsNone(recorrencia.suffix_icon)              # sem Alterar frequência / Encerrar

    def test_recorrencia_continua_com_o_menu(self):
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-20", "mensal")
        self.abrir_detalhes("Aluguel")
        self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Editar"))
        menu = next(c for c in self.controles(ft.TextField) if c.label == "Recorrência").suffix_icon
        self.assertEqual([i.content for i in menu.items], ["Encerrar recorrência"])     # Etapa 10: R6


if __name__ == "__main__":
    unittest.main()
