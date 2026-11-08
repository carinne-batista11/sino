"""
Sino 6.12 (experimental), Etapa 7 -- interface mínima de edição e exclusão de parcelas.

Detalhes da parcela: "Alterar parcelamento" (valor total e quantidade, com prévia que
marca as parcelas mantidas); recusas de exclusão (C4/P1) e de edição (D5/P4) aparecem
nos diálogos de sempre, sem gravar nada. Hoje fixo: 15/09/2026.
"""

import unittest

from apoio_banco import db
from test_612_parcelada_telas import BaseTelas
from test_tela_principal import Evento, percorrer

import flet as ft  # noqa: E402
import pagamentos  # noqa: E402


class TestTelasDasParcelas(BaseTelas):
    def setUp(self):
        super().setUp()
        self.serie_id, self.p = db.criar_conta_parcelada(self.usuario_id, "Sofá", 1200.0, 6, "2026-09-20")

    def abrir_detalhes(self, nome="Sofá"):
        self.entrar()
        linha = next(c for c in self.controles(ft.Container)
                     if c.data in ("linha_conta", "linha_conta_empilhada")
                     and nome in [t.value for t in percorrer(c) if isinstance(t, ft.Text)])
        self.clicar(linha)

    def valores(self):
        return [v for (v,) in self.consultar("SELECT valor FROM contas WHERE serie_id = ? ORDER BY posicao",
                                             (self.serie_id,))]

    def estado(self):
        return {t: self.consultar(f"SELECT * FROM {t} ORDER BY 1") for t in ("contas", "pp_pagamentos",
                                                                              "series_recorrencia")}

    def menu_recorrencia(self):
        return self.campo("Recorrência").suffix_icon

    def abrir_alterar(self):
        # Ajustes pós-validação manual (A): só pelo campo Recorrência de Editar.
        self.abrir_detalhes()
        self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Editar"))
        self.clicar(next(i for i in self.menu_recorrencia().items if i.content == "Alterar parcelamento"))
        self.assertEqual(self.dlg().data, "dialogo_alterar_parcelamento")

    def em_detalhes(self):
        return any(getattr(c, "data", None) == "tela_detalhes" for c in self.controles())

    def previa(self):
        return [t for t in self.textos_do_dialogo() if t.startswith("Parcela ") or "serão excluídas" in t]

    def test_dialogo_com_total_quantidade_e_previa(self):
        pagamentos.registrar_pagamento_parcial(self.p[1], 50_00, "2026-09-12")
        self.abrir_alterar()
        self.assertEqual(self.no_dialogo("total_alterar_parcelamento").value, "1.200,00")
        self.assertEqual(self.no_dialogo("quantidade_alterar_parcelamento").value, "6")
        self.assertEqual(len(self.previa()), 6)
        self.assertIn("Parcela 2 de 6 · 20/10/2026 · R$ 200,00 · com pagamentos (mantida)", self.previa())
        self.escolher(self.no_dialogo("quantidade_alterar_parcelamento"), "8")
        previa = self.previa()
        self.assertEqual(len(previa), 8)
        self.assertEqual(previa[-1], "Parcela 8 de 8 · 20/04/2027 · R$ 142,85 · nova")
        self.assertEqual(self.valores(), [200.0] * 6)                     # a prévia não grava
        self.clicar(self.acao("Aplicar"))
        self.assertEqual(self.abertos(), [])
        self.assertEqual(self.valores(), [142.9, 200.0] + [142.85] * 6)
        self.assertTrue(self.em_detalhes())                               # ajuste A: volta aos Detalhes
        self.assertIn("Parcela 1 de 8", [t.value for t in self.controles(ft.Text)])

    def test_reducao_recusada_aparece_no_dialogo(self):
        db.editar_conta_ocorrencia(self.p[5], valor=210.0)
        antes = self.estado()
        self.abrir_alterar()
        self.escolher(self.no_dialogo("quantidade_alterar_parcelamento"), "4")
        self.assertIn(db.MENSAGEM_REDUCAO_COM_FIXAS, self.textos_do_dialogo())
        self.clicar(self.acao("Aplicar"))
        self.assertIn(db.MENSAGEM_REDUCAO_COM_FIXAS, self.textos_do_dialogo())
        self.assertEqual(self.estado(), antes)

    def test_total_invalido(self):
        self.abrir_alterar()
        campo = self.no_dialogo("total_alterar_parcelamento")
        campo.value = "abc"
        campo.on_change(Evento(self.pagina, campo))
        self.assertIn(db.MENSAGEM_VALOR_TOTAL_INVALIDO, self.textos_do_dialogo())
        antes = self.estado()
        self.clicar(self.acao("Aplicar"))
        self.assertEqual(self.estado(), antes)

    def test_botao_so_em_parcela(self):
        # Ajustes pós-validação manual (A): nunca nos Detalhes; em Editar, só na parcelada.
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "mensal")
        db.criar_conta_unica(self.usuario_id, "Luz", 90.0, "2026-09-28")
        for nome, esperado in (("Sofá", True), ("Aluguel", False), ("Luz", False)):
            self.abrir_detalhes(nome)
            self.assertEqual([c for c in self.controles() if getattr(c, "data", None) == "alterar_parcelamento"],
                             [], nome)
            self.assertNotIn("Alterar parcelamento", [getattr(c, "content", None) for c in self.controles()])
            self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Editar"))
            itens = [i.content for i in self.menu_recorrencia().items]
            self.assertEqual("Alterar parcelamento" in itens, esperado, nome)

    def test_exclusao_de_parcela_protegida_mostra_o_motivo(self):
        pagamentos.registrar_pagamento_parcial(self.p[0], 50_00, "2026-09-12")
        antes = self.estado()
        for escopo, mensagem in (("Somente este mês", db.MENSAGEM_PARCELA_PROTEGIDA_EXCLUSAO),
                                 ("Este mês em diante", db.MENSAGEM_EM_DIANTE_COM_PROTEGIDAS)):
            with self.subTest(escopo=escopo):
                self.abrir_detalhes()
                self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Excluir"))
                self.clicar(self.acao(escopo))
                self.assertEqual(self.dlg().title.value, "Não é possível excluir")
                self.assertEqual(self.dlg().content.value, mensagem)
                self.clicar(self.acao("Entendi"))
        self.assertEqual(self.estado(), antes)

    def test_exclusao_de_parcela_livre(self):
        self.abrir_detalhes()
        self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Excluir"))
        self.clicar(self.acao("Somente este mês"))
        self.assertEqual(len(self.valores()), 5)
        self.assertEqual(db.obter_identificacao(self.serie_id, self.p[1]), {"tipo": "parcela", "posicao": 1, "total": 5})

    def test_edicao_do_valor_de_parcela_protegida_e_recusada(self):
        pagamentos.registrar_pagamento_parcial(self.p[0], 50_00, "2026-09-12")
        antes = self.estado()
        self.abrir_detalhes()
        self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Editar"))
        campo = next(c for c in self.controles(ft.TextField) if c.label == "Valor")
        campo.value = "300,00"
        campo.on_change(Evento(self.pagina, campo))
        self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Salvar alterações"))
        self.clicar(self.acao("Somente este mês"))
        self.assertIn(db.MENSAGEM_PARCELA_PROTEGIDA_EDICAO, [t.value for t in self.controles(ft.Text)])
        self.assertEqual(self.estado(), antes)


if __name__ == "__main__":
    unittest.main()
