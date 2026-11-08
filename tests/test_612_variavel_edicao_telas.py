"""
Sino 6.12 (experimental), Etapa 9 -- interface mínima da edição de recorrências variáveis.

Informar o valor de uma ocorrência pendente em Editar (inclusive R$ 0,00), "Informar valor"
nos Detalhes, aviso da R5 no diálogo de escopo e "Mudar para valor variável/fixo" nos
Detalhes (R3/R4, com prévia, sugestão e recusas no diálogo). Hoje fixo: 15/09/2026.
"""

import unittest

from apoio_banco import db
from test_612_variavel_telas import BaseVariavelTelas
from test_tela_principal import Evento

import flet as ft  # noqa: E402
import main  # noqa: E402


class TestTextos(unittest.TestCase):
    def test_valor_informado_aceita_zero(self):
        for texto, esperado in (("0,00", 0.0), ("0", 0.0), ("R$ 0,00", 0.0), ("12,50", 12.5), ("1.234,56", 1234.56),
                                ("", None), ("abc", None), ("-1", None)):
            with self.subTest(texto=texto):
                self.assertEqual(main.parse_valor_informado(texto), esperado)
        self.assertIsNone(main.parse_valor("0,00"))                         # a regra geral da 6.11 não muda

    def test_mensagem_de_valor_informado(self):
        from datetime import date
        d = date(2026, 9, 10)
        self.assertEqual(main.montar_mensagem_alteracao("Luz", "Luz", None, 0.0, d, d),
                         "Você alterou o valor de Valor pendente para R$ 0,00.")


class BaseEdicaoTelas(BaseVariavelTelas):
    def setUp(self):
        super().setUp()
        self.serie, self.ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-08-10", "mensal",
                                                         data_termino="2026-12", variavel=True)

    def editar_luz_de_setembro(self):
        self.entrar()
        self.clicar(self.linha("Luz"))
        self.clicar(self.botao("Editar"))

    def digitar_valor(self, texto):
        campo = self.campo("Valor")
        campo.value = texto
        campo.on_change(Evento(self.pagina, campo))

    def salvar(self):
        return self.botao("Salvar alterações")

    def valor(self, conta_id):
        return self.consultar("SELECT valor FROM contas WHERE id = ?", (conta_id,))[0][0]


class TestInformarValorNaTela(BaseEdicaoTelas):
    def test_informar_zero(self):
        self.editar_luz_de_setembro()
        self.assertTrue(self.salvar().disabled)                             # campo vazio: nada mudou
        self.digitar_valor("0,00")
        self.assertFalse(self.salvar().disabled)
        self.clicar(self.salvar())                                           # ajuste C: sem diálogo de escopo
        self.assertEqual(self.dlg().title.value, "Alteração salva")
        self.assertEqual(self.valor(self.ids[1]), 0.0)
        self.assertNotIn(self.ids[1], self.pendentes())
        self.assertIn("Você alterou o valor de Valor pendente para R$ 0,00.", self.textos_do_dialogo())

    def test_valor_invalido(self):
        self.editar_luz_de_setembro()
        self.digitar_valor("abc")
        self.clicar(self.salvar())
        self.assertIn("Informe um valor válido.", self.textos())
        self.assertIn(self.ids[1], self.pendentes())

    def test_botao_informar_valor_nos_detalhes(self):
        self.entrar()
        self.clicar(self.linha("Luz"))
        botao = next(c for c in self.controles(ft.TextButton) if c.data == "informar_valor")
        self.clicar(botao)
        self.assertEqual(self.campo("Valor").data, "valor_pendente_edicao")
        self.digitar_valor("98,40")
        self.clicar(self.salvar())                                           # ajuste C: sem diálogo de escopo
        self.assertEqual(self.dlg().title.value, "Alteração salva")
        self.assertEqual([self.valor(i) for i in self.ids], [150.0, 98.4, 0.0, 0.0, 0.0])
        self.assertEqual(self.consultar("SELECT valor FROM series_recorrencia WHERE id = ?", (self.serie,)),
                         [(150.0,)])                                         # o modelo não muda
        self.assertEqual(self.pendentes(), set(self.ids[2:]))

    def test_pagamento_liberado_depois_de_informar(self):
        db.editar_conta_ocorrencia(self.ids[1], valor=120.0)
        self.entrar()
        self.clicar(self.linha("Luz"))
        self.assertFalse(self.botao("Marcar como paga").disabled)
        self.assertNotIn(db.MENSAGEM_PAGAMENTO_COM_VALOR_PENDENTE, self.textos())
        self.assertIn("R$ 120,00", self.textos())

    def test_avulsa_de_serie_encerrada(self):
        db.encerrar_recorrencia(self.ids[1])
        self.editar_luz_de_setembro()
        self.digitar_valor("75,00")
        self.clicar(self.salvar())                                           # sem diálogo de escopo
        self.assertEqual(self.valor(self.ids[1]), 75.0)
        self.assertNotIn(self.ids[1], self.pendentes())


class TestMudarComportamento(BaseEdicaoTelas):
    def abrir_dialogo(self, nome, anterior=False):
        self.entrar()
        if anterior:
            self.clicar(next(c for c in self.controles(ft.IconButton) if c.data == "mes_anterior"))
        self.clicar(self.linha(nome))
        # Ajustes pós-validação manual (D1): só por Editar > Recorrência > "Alterar tipo de valor".
        self.clicar(self.botao("Editar"))
        self.clicar(next(i for i in self.campo("Recorrência").suffix_icon.items
                         if i.content == "Alterar tipo de valor"))
        self.assertEqual(self.dlg().data, "dialogo_comportamento_valor")
        return self.dlg().title.value

    def test_fixo_para_variavel(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "mensal",
                                               data_termino="2026-12")
        db.editar_conta_ocorrencia(ids[2], valor=950.0)
        self.assertEqual(self.abrir_dialogo("Aluguel"), "Mudar para valor variável")  # título do diálogo
        textos = " ".join(self.textos_do_dialogo())
        self.assertIn("(2 ocorrências) ficarão com “Valor pendente”; 1 ocorrência com pagamentos ou editadas", textos)
        self.clicar(self.acao("Mudar para variável"))
        self.assertTrue(db.serie_variavel(serie))
        self.assertEqual(self.pendentes() & set(ids), {ids[1], ids[3]})

    def test_variavel_para_fixo_com_sugestao(self):
        db.editar_conta_ocorrencia(self.ids[2], valor=130.0)
        self.assertEqual(self.abrir_dialogo("Luz"), "Mudar para valor fixo")
        campo = self.no_dialogo("valor_fixo_comportamento")
        self.assertEqual(campo.value, "130,00")                              # último valor informado
        campo.value = "140,00"
        self.clicar(self.acao("Mudar para fixo"))
        self.assertFalse(db.serie_variavel(self.serie))
        self.assertEqual([self.valor(i) for i in self.ids], [150.0, 140.0, 130.0, 140.0, 140.0])
        self.assertEqual(self.pendentes(), set())

    def test_variavel_para_fixo_recusado_com_pendentes_anteriores(self):
        # Outubro: setembro (anterior) continua pendente -- a recusa aparece ao abrir e ao confirmar.
        db.editar_conta_ocorrencia(self.ids[2], nome="Luz outubro")
        self.entrar()
        self.clicar(next(c for c in self.controles(ft.IconButton) if c.data == "proximo_mes"))
        self.clicar(self.linha("Luz outubro"))
        self.clicar(self.botao("Editar"))
        self.clicar(next(i for i in self.campo("Recorrência").suffix_icon.items
                         if i.content == "Alterar tipo de valor"))
        self.assertIn(db.MENSAGEM_PENDENTES_ANTERIORES, self.textos_do_dialogo())
        antes = self.consultar("SELECT * FROM contas ORDER BY id")
        self.clicar(self.acao("Mudar para fixo"))
        self.assertIn(db.MENSAGEM_PENDENTES_ANTERIORES, self.textos_do_dialogo())
        self.assertEqual(self.consultar("SELECT * FROM contas ORDER BY id"), antes)
        self.assertTrue(db.serie_variavel(self.serie))

    def test_valor_fixo_invalido(self):
        self.abrir_dialogo("Luz")
        self.no_dialogo("valor_fixo_comportamento").value = "abc"
        self.clicar(self.acao("Mudar para fixo"))
        self.assertIn(db.MENSAGEM_VALOR_INVALIDO, self.textos_do_dialogo())
        self.assertTrue(db.serie_variavel(self.serie))

    def test_sem_botao_em_unica_e_parcelada(self):
        # D1: e também em nenhuma recorrência (a conversão saiu dos Detalhes).
        db.criar_conta_unica(self.usuario_id, "Água", 80.0, "2026-09-18")
        db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-09-20")
        self.entrar()
        for nome in ("Água", "Sofá", "Luz"):
            self.entrar()
            self.clicar(self.linha(nome))
            self.assertEqual([c for c in self.controles(ft.TextButton)
                              if c.data == "mudar_comportamento_valor"], [], nome)


if __name__ == "__main__":
    unittest.main()
