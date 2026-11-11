"""
Sino 6.12 (experimental), Etapa 11 -- consolidação da interface funcional mínima.

Matriz de consistência dos seis tipos de conta (Única, Parcelada, Mensal fixa/variável, Anual
fixa/variável) e da avulsa de série encerrada: ações dos Detalhes, menu de Recorrência em Editar,
frase da Recorrência e campos da Nova conta. Ajustes desta etapa: ícone de pagamento desativado
distinguível (opacidade), aviso dos 7 dias e alerta de atraso sem cortar texto em janela estreita,
ajuda curta no Valor da pendente e ajuda do Transformar só com "Valor variável".
Hoje fixo: 15/09/2026.
"""

import unittest

from apoio_banco import db
from test_612_variavel_telas import BaseVariavelTelas
from test_tela_principal import Evento, percorrer

import flet as ft  # noqa: E402
import main  # noqa: E402

ACOES_DETALHES = ("parcelar_conta", "alterar_parcelamento", "mudar_comportamento_valor", "informar_valor")


class BaseInterface(BaseVariavelTelas):
    def setUp(self):
        super().setUp()
        u = self.usuario_id
        self.unica = db.criar_conta_unica(u, "Água", 80.0, "2026-09-18")
        db.criar_conta_parcelada(u, "Sofá", 600.0, 3, "2026-09-22")
        db.criar_serie_recorrente(u, "Aluguel", 900.0, "2026-09-25", "mensal")
        db.criar_serie_recorrente(u, "Luz", 150.0, "2026-08-20", "mensal", variavel=True)      # set. pendente
        db.criar_serie_recorrente(u, "IPVA", 1800.0, "2026-09-26", "anual", data_termino="2030-12")
        db.criar_serie_recorrente(u, "Seguro", 640.0, "2025-09-27", "anual", variavel=True)     # 2026 pendente
        _, gas = db.criar_serie_recorrente(u, "Gás", 60.0, "2026-09-28", "mensal", data_termino="2026-12")
        db.encerrar_recorrencia(gas[0])                                                       # avulsa

    def acoes_dos_detalhes(self, nome):
        self.entrar()
        self.clicar(self.linha(nome))
        return {c.data for c in self.controles() if getattr(c, "data", None) in ACOES_DETALHES}

    def menu_do_editar(self):
        self.clicar(self.botao("Editar"))
        menu = self.campo("Recorrência").suffix_icon
        return None if menu is None else [i.content for i in menu.items]


class TestMatrizDosTipos(BaseInterface):
    ESPERADO = {
        # nome: (ações nos Detalhes, menu de Recorrência em Editar, início da frase de Recorrência)
        "Água": (set(), ["Transformar em recorrente", "Parcelar esta conta"], "Esta conta não é recorrente."),
        "Sofá": (set(), ["Alterar parcelamento"], "Esta conta é parcelada em 3 parcelas mensais"),  # ajuste A
        "Aluguel": (set(), ["Alterar tipo de valor", "Alterar término da recorrência", "Encerrar recorrência"], "Esta conta se repete mensalmente"),
        "Luz": ({"informar_valor"}, ["Alterar tipo de valor", "Alterar término da recorrência", "Encerrar recorrência"],
                "Esta conta se repete mensalmente"),
        "IPVA": (set(), ["Alterar tipo de valor", "Alterar término da recorrência", "Encerrar recorrência"], "Esta conta se repete anualmente"),
        "Seguro": ({"informar_valor"}, ["Alterar tipo de valor", "Alterar término da recorrência", "Encerrar recorrência"],
                   "Esta conta se repete anualmente"),
        "Gás": (set(), ["Transformar em recorrente", "Parcelar esta conta"], "Esta conta não é recorrente."),
    }

    def test_acoes_menu_e_frase_de_cada_tipo(self):
        for nome, (acoes, menu, frase) in self.ESPERADO.items():
            with self.subTest(nome=nome):
                self.assertEqual(self.acoes_dos_detalhes(nome), acoes)
                # Ajustes pós-validação manual (D1): conversão nunca nos Detalhes.
                self.assertNotIn("mudar_comportamento_valor", [getattr(c, "data", None) for c in self.controles()])
                recorrencia = next(t for t in self.textos() if t and t.startswith(
                    ("Esta conta se repete", "Esta conta é parcelada", "Esta conta não é recorrente")))
                self.assertTrue(recorrencia.startswith(frase), recorrencia)
                self.assertEqual(recorrencia.endswith("O valor varia a cada ocorrência."), nome in ("Luz", "Seguro"))
                self.assertEqual(self.menu_do_editar(), menu)
                self.assertNotIn("Alterar frequência", menu or [])          # R6

    def test_valor_pendente_e_pagamento_nos_detalhes(self):
        for nome, pendente in (("Luz", True), ("Seguro", True), ("Aluguel", False), ("Sofá", False), ("Água", False)):
            with self.subTest(nome=nome):
                self.entrar()
                self.clicar(self.linha(nome))
                self.assertEqual("Valor pendente" in self.textos(), pendente)
                self.assertEqual(self.botao("Marcar como paga").disabled, pendente)
                self.assertEqual(self.botao("Registrar pagamento parcial").disabled, pendente)


class TestAjustesDaEtapa11(BaseInterface):
    def test_icone_de_pagamento_desativado_distinguivel(self):
        self.entrar()
        luz = next(c for c in percorrer(self.linha("Luz")) if isinstance(c, ft.IconButton)
                   and c.data == "pagamento_bloqueado_valor_pendente")
        agua = next(c for c in percorrer(self.linha("Água")) if isinstance(c, ft.IconButton)
                    and c.tooltip == "Marcar como paga")
        self.assertEqual((luz.disabled, luz.opacity), (True, main.OPACIDADE_DESATIVADO))
        self.assertIn(agua.opacity, (None, 1, 1.0))
        self.assertIn("indisponível, valor pendente", luz.icon.semantics_label)   # nome acessível

    def test_avisos_quebram_linha_em_vez_de_cortar(self):
        self.entrar()
        aviso = next(c for c in self.controles(ft.Column)
                     if any(isinstance(t, ft.Text) and t.value and "vencem nos próximos 7 dias" in t.value
                            for t in c.controls))
        self.assertTrue(aviso.expand)
        self.assertIn("Total de R$ 280,00 · 1 conta com valor pendente", self.textos())     # Água + Sofá; Luz contada
        alerta = next(c for c in self.controles(ft.Row) if any(
            isinstance(t, ft.Container) and "Ver essas contas" in self.textos_da(t) for t in c.controls))
        self.assertTrue(alerta.controls[0].expand)                            # o título quebra linha
        titulo = next(t for t in alerta.controls[0].controls if isinstance(t, ft.Text))
        self.assertTrue(titulo.expand)

    def test_ajuda_curta_no_valor_da_pendente(self):
        self.entrar()
        self.clicar(self.linha("Luz"))
        self.clicar(self.botao("Editar"))
        self.assertEqual(self.campo("Valor").helper, "R$ 0,00 também é um valor.")

    def test_ajuda_do_transformar_so_com_variavel(self):
        self.entrar()
        self.clicar(self.linha("Água"))
        self.clicar(self.botao("Editar"))
        item = next(i for i in self.campo("Recorrência").suffix_icon.items if i.content == "Transformar em recorrente")
        item.on_click(Evento(self.pagina, item))
        ajuda = self.no_dialogo("ajuda_variavel_transformar")
        linha = self.no_dialogo("comportamento_transformar")
        self.assertFalse(ajuda.visible)
        self.clicar(linha.controls[1])
        self.assertTrue(ajuda.visible)
        self.clicar(linha.controls[0])
        self.assertFalse(ajuda.visible)


class TestNovaContaPorTipo(BaseVariavelTelas):
    def test_campos_e_resumo_de_cada_tipo(self):
        self.entrar()
        self.clicar(next(c for c in self.controles(ft.Container) if c.data == "nova_conta"))
        casos = (("unica", False, False, False, "Valor", "Única"),
                 ("parcelada", True, False, False, "Valor total", "Parcelada em 2 parcelas"),
                 ("mensal", False, True, True, "Valor", "Mensal até setembro de 2026"),
                 ("anual", False, True, True, "Valor", "Anual até setembro de 2026, valor variável"))
        for tipo, quantidade, comportamento, termino, rotulo_valor, resumo in casos:
            with self.subTest(tipo=tipo):
                self.clicar(self.campo("Recorrência").suffix_icon)
                self.clicar(self.no_dialogo(f"tipo_recorrencia_{tipo}"))
                if tipo == "anual":
                    self.clicar(self.no_dialogo("comportamento_variavel"))
                elif tipo == "mensal":
                    self.clicar(self.no_dialogo("comportamento_fixo"))
                self.assertEqual(self.no_dialogo("quantidade_parcelas_nova_conta").visible, quantidade)
                linha = self.no_dialogo("linha_comportamento_valor")
                bloco = next(c for c in percorrer(self.dlg().content) if isinstance(c, ft.Column)
                             and linha in c.controls)
                self.assertEqual(bloco.visible, comportamento)
                chave = self.no_dialogo("sem_termino_recorrencia")
                linha_chave = next(c for c in percorrer(self.dlg().content)
                                   if isinstance(c, ft.Row) and chave in c.controls)
                self.assertEqual(linha_chave.visible, termino)
                self.clicar(self.acao("Confirmar"))
                self.assertEqual(self.campo("Recorrência").value, resumo)
                self.assertIsNotNone(next(c for c in self.controles(ft.TextField) if c.label == rotulo_valor))


if __name__ == "__main__":
    unittest.main()
