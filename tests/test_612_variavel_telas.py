"""
Sino 6.12 (experimental), Etapa 8 -- interface mínima das recorrências variáveis.

Nova conta e "Transformar em recorrente": Valor fixo (padrão) | Valor variável, só em
Mensal/Anual. "Valor pendente" no lugar do valor (nunca "R$ 0,00") na lista do mês, em
"Contas em atraso", nos Detalhes e em Editar; contagem à parte no total do mês, no aviso
dos próximos 7 dias e no Gráfico; pagamentos desativados com o motivo. Hoje fixo: 15/09/2026.
"""

import unittest

from apoio_banco import db
from test_612_parcelada_telas import BaseTelas
from test_tela_principal import Evento, percorrer

import flet as ft  # noqa: E402
import flet_charts as fch  # noqa: E402
import main  # noqa: E402
import pagamentos  # noqa: E402
from cores import PALETAS  # noqa: E402

CLARO = PALETAS["claro"]


class TestTextos(unittest.TestCase):
    def test_valor_do_periodo(self):
        self.assertEqual(main.texto_valor_do_periodo(0.0, 2), "Valor pendente")
        self.assertEqual(main.texto_valor_do_periodo(150.0, 1), "R$ 150,00\n+1 pendente")
        self.assertEqual(main.texto_valor_do_periodo(150.0, 3), "R$ 150,00\n+3 pendentes")
        self.assertEqual(main.texto_valor_do_periodo(0.0, 0), "R$ 0,00")            # 0,00 conhecido
        self.assertEqual(main.texto_do_total_da_categoria({"total": 0.0, "pendentes": 1}), "Valor pendente")
        self.assertEqual(main.texto_do_total_da_categoria({"total": 0.0}), "R$ 0,00")

    def test_total_dos_proximos_7_dias(self):
        conhecida = {"valor": 100.0, "saldo": 100.0, "valor_pendente": False}
        pendente = {"valor": 0.0, "saldo": 0.0, "valor_pendente": True}
        self.assertEqual(main.texto_total_proximas([conhecida]), "Total de R$ 100,00")
        self.assertEqual(main.texto_total_proximas([conhecida, pendente]),
                         "Total de R$ 100,00 · 1 conta com valor pendente")
        self.assertEqual(main.texto_total_proximas([pendente, pendente]), "2 contas com valor pendente")

    def test_frase_da_recorrencia(self):
        self.assertEqual(main.frase_recorrencia("mensal", None, True),
                         "Esta conta se repete mensalmente sem prazo definido para término. "
                         "O valor varia a cada ocorrência.")
        self.assertEqual(main.frase_recorrencia("anual", "2030-12"), "Esta conta se repete anualmente até "
                                                                     "dezembro de 2030.")


class BaseVariavelTelas(BaseTelas):
    def linha(self, nome):
        return next(c for c in self.controles(ft.Container) if c.data in ("linha_conta", "linha_conta_empilhada")
                    and nome in [t.value for t in percorrer(c) if isinstance(t, ft.Text)])

    def textos_da(self, controle):
        return [t.value for t in percorrer(controle) if isinstance(t, ft.Text)]

    def textos(self):
        return [t.value for t in self.controles(ft.Text)]

    def botao(self, texto):
        return next(c for c in self.controles((ft.Button, ft.OutlinedButton, ft.TextButton)) if c.content == texto)

    def pendentes(self):
        return {c for (c,) in self.consultar("SELECT conta_id FROM ocorrencias_valor_pendente")}


class TestNovaContaVariavel(BaseVariavelTelas):
    def setUp(self):
        super().setUp()
        self.entrar()
        self.clicar(next(c for c in self.controles() if getattr(c, "data", None) == "nova_conta"))

    def preencher(self, nome, valor):
        for c in self.controles(ft.TextField):
            if c.label == "Nome da conta":
                c.value = nome
            elif c.label == "Valor":
                c.value = valor
        seletor = next(o for o in self.pagina.overlay if isinstance(o, ft.DatePicker))
        from datetime import datetime
        seletor.value = datetime(2026, 9, 20)
        seletor.on_change(Evento(self.pagina, seletor))

    def test_opcao_so_em_mensal_e_anual(self):
        self.clicar(self.campo("Recorrência").suffix_icon)
        linha = self.no_dialogo("linha_comportamento_valor")
        bloco = next(c for c in percorrer(self.dlg().content) if isinstance(c, ft.Column) and linha in c.controls)
        self.assertEqual([b.content for b in linha.controls], ["Valor fixo", "Valor variável"])
        for tipo, visivel in (("unica", False), ("parcelada", False), ("mensal", True), ("anual", True)):
            with self.subTest(tipo=tipo):
                self.clicar(self.no_dialogo(f"tipo_recorrencia_{tipo}"))
                self.assertEqual(bloco.visible, visivel)
        ajuda = next(c for c in bloco.controls if isinstance(c, ft.Text))
        self.assertFalse(ajuda.visible)                                   # Fixo é o padrão
        self.clicar(self.no_dialogo("comportamento_variavel"))
        self.assertTrue(ajuda.visible)
        self.assertEqual(ajuda.value, main.TEXTO_AJUDA_VARIAVEL)

    def test_cria_mensal_variavel(self):
        self.preencher("Luz", "150,00")
        self.clicar(self.campo("Recorrência").suffix_icon)
        self.clicar(self.no_dialogo("tipo_recorrencia_mensal"))
        self.clicar(self.no_dialogo("comportamento_variavel"))
        chave = self.no_dialogo("sem_termino_recorrencia")
        chave.value = True
        chave.on_change(Evento(self.pagina, chave))
        self.clicar(self.acao("Confirmar"))
        self.assertEqual(self.campo("Recorrência").value, "Mensal, sem término, valor variável")
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Salvar conta"))
        serie_id = self.consultar("SELECT id FROM series_recorrencia")[0][0]
        self.assertTrue(db.serie_variavel(serie_id))
        ids = [i for (i,) in self.consultar("SELECT id FROM contas WHERE serie_id = ? ORDER BY posicao", (serie_id,))]
        self.assertEqual(self.pendentes(), set(ids[1:]))
        self.assertEqual(self.consultar("SELECT valor FROM contas WHERE id = ?", (ids[0],)), [(150.0,)])

    def test_mensal_fixa_continua_padrao(self):
        self.preencher("Aluguel", "900,00")
        self.clicar(self.campo("Recorrência").suffix_icon)
        self.clicar(self.no_dialogo("tipo_recorrencia_mensal"))
        self.clicar(self.acao("Confirmar"))
        self.assertEqual(self.campo("Recorrência").value.endswith("valor variável"), False)
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Salvar conta"))
        serie_id = self.consultar("SELECT id FROM series_recorrencia")[0][0]
        self.assertFalse(db.serie_variavel(serie_id))
        self.assertEqual(self.pendentes(), set())
        self.assertEqual({v for (v,) in self.consultar("SELECT valor FROM contas")}, {900.0})


class TestTransformarEmVariavel(BaseVariavelTelas):
    def test_unica_com_pagamento_vira_variavel_com_tudo_intacto(self):
        conta = db.criar_conta_unica(self.usuario_id, "Escola", 500.0, "2026-09-10")
        pagamentos.registrar_pagamento_parcial(conta, 100_00, "2026-09-05")
        antes = (self.consultar("SELECT valor, status, data_pagamento FROM contas WHERE id = ?", (conta,)),
                 self.consultar("SELECT * FROM pp_pagamentos"))
        self.entrar()
        self.clicar(self.linha("Escola"))
        self.clicar(self.botao("Editar"))
        menu = self.campo("Recorrência").suffix_icon
        item = next(i for i in menu.items if i.content == "Transformar em recorrente")
        item.on_click(Evento(self.pagina, item))
        linha = self.no_dialogo("comportamento_transformar")
        self.assertEqual([self.textos_da(c)[0] for c in linha.controls], ["Valor fixo", "Valor variável"])
        self.assertIn(main.TEXTO_AJUDA_VARIAVEL, self.textos_do_dialogo())
        self.clicar(linha.controls[1])
        self.clicar(self.acao("Transformar"))
        recorrencia = self.campo("Recorrência").value
        self.assertEqual(recorrencia, "Mensal · Variável · Sem término")  # 6.13 (E2): resumo curto
        self.clicar(self.botao("Salvar alterações"))
        serie_id = self.consultar("SELECT serie_id FROM contas WHERE id = ?", (conta,))[0][0]
        self.assertTrue(db.serie_variavel(serie_id))
        self.assertEqual((self.consultar("SELECT valor, status, data_pagamento FROM contas WHERE id = ?", (conta,)),
                          self.consultar("SELECT * FROM pp_pagamentos")), antes)
        outras = {i for (i,) in self.consultar("SELECT id FROM contas WHERE serie_id = ? AND id != ?",
                                                (serie_id, conta))}
        self.assertEqual(self.pendentes(), outras)


class TestValorPendenteNasTelas(BaseVariavelTelas):
    def setUp(self):
        super().setUp()
        # Luz: agosto com valor; setembro (atrasada) e seguintes com valor pendente.
        self.serie, self.ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-08-10", "mensal",
                                                         data_termino="2026-11", variavel=True)
        # Gás: pendente que vence em 20/09 (próximos 7 dias).
        _, self.gas = db.criar_serie_recorrente(self.usuario_id, "Gás", 60.0, "2026-08-20", "mensal",
                                                data_termino="2026-10", variavel=True)
        db.criar_conta_unica(self.usuario_id, "Internet", 100.0, "2026-09-18")
        self.entrar()

    def test_lista_total_e_aviso_do_mes(self):
        luz = self.linha("Luz")
        self.assertIn("Valor pendente", self.textos_da(luz))
        self.assertIn("Atrasado", self.textos_da(luz))
        self.assertNotIn("R$ 0,00", self.textos_da(luz))
        bloqueado = next(c for c in percorrer(luz) if getattr(c, "data", None) == "pagamento_bloqueado_valor_pendente")
        self.assertTrue(bloqueado.disabled)
        self.assertEqual((bloqueado.icon_color, bloqueado.icon.color), (CLARO["botao_desabilitado_texto"],) * 2)
        self.assertEqual(bloqueado.tooltip, db.MENSAGEM_PAGAMENTO_COM_VALOR_PENDENTE)
        internet = next(c for c in percorrer(self.linha("Internet")) if isinstance(c, ft.IconButton)
                        and c.tooltip == "Marcar como paga")
        self.assertFalse(internet.disabled)
        textos = self.textos()
        self.assertIn("R$ 100,00", textos)                                   # total: só valores conhecidos
        self.assertIn("2 contas com valor pendente, fora do total", textos)
        self.assertIn("Total de R$ 100,00 · 1 conta com valor pendente", textos)

    def test_mes_so_com_pendentes(self):
        self.clicar(next(c for c in self.controles(ft.IconButton) if c.data == "proximo_mes"))
        self.clicar(next(c for c in self.controles(ft.IconButton) if c.data == "proximo_mes"))   # novembro
        textos = self.textos()
        self.assertIn("Valor pendente", textos)
        aviso = next(c for c in self.controles(ft.Text) if c.data == "aviso_valores_pendentes_mes")
        self.assertEqual((aviso.visible, aviso.value), (True, "1 conta com valor pendente"))
        self.assertNotIn("R$ 0,00", [self.textos_da(self.linha("Luz"))[i] for i in range(2)])

    def test_contas_em_atraso(self):
        self.clicar(next(c for c in self.controles((ft.Container, ft.TextButton))
                         if c.on_click and "Ver essas contas" in self.textos_da(c)))
        self.assertIn("Contas em atraso", self.textos())
        linhas = [self.textos_da(c) for c in self.controles(ft.Container)
                  if c.data in ("linha_conta", "linha_conta_empilhada")]
        # Luz e Gás de agosto (com valor) e Luz de setembro (valor pendente), todas atrasadas.
        self.assertEqual([(t[0], t[2], t[3]) for t in linhas],
                         [("Luz", "R$ 150,00", "Atrasado"), ("Gás", "R$ 60,00", "Atrasado"),
                          ("Luz", "Valor pendente", "Atrasado")])

    def test_detalhes_da_pendente(self):
        self.clicar(self.linha("Luz"))
        textos = self.textos()
        self.assertIn("Valor pendente", textos)
        self.assertIn(main.TEXTO_INFORMAR_VALOR, textos)
        self.assertIn("—", textos)                                           # saldo devedor
        self.assertIn("R$ 0,00", textos)                                     # total pago (nada pago)
        self.assertIn(db.MENSAGEM_PAGAMENTO_COM_VALOR_PENDENTE, textos)
        for texto in ("Marcar como paga", "Registrar pagamento parcial"):
            botao = self.botao(texto)
            self.assertTrue(botao.disabled)
            self.assertEqual((botao.bgcolor, botao.style.color),
                             (CLARO["botao_desabilitado_fundo"], CLARO["botao_desabilitado_texto"]))
        self.assertTrue(any(t and t.endswith("O valor varia a cada ocorrência.") for t in textos))

    def test_detalhes_da_primeira_com_valor(self):
        self.clicar(next(c for c in self.controles(ft.IconButton) if c.data == "mes_anterior"))  # agosto
        self.clicar(self.linha("Luz"))
        textos = self.textos()
        self.assertIn("R$ 150,00", textos)
        self.assertNotIn(db.MENSAGEM_PAGAMENTO_COM_VALOR_PENDENTE, textos)
        self.assertFalse(self.botao("Marcar como paga").disabled)

    def test_editar_pendente_sem_alterar_frequencia(self):
        # Ajuste deliberado na Etapa 9: o campo Valor da pendente passou a ser editável (vazio,
        # com "Valor pendente" como dica); salvar só o nome mantém a ocorrência pendente.
        self.clicar(self.linha("Luz"))
        self.clicar(self.botao("Editar"))
        campo = self.campo("Valor")
        self.assertEqual((campo.value, campo.read_only, campo.hint_text, campo.helper),
                         ("", False, "Valor pendente", main.TEXTO_DIGITE_O_VALOR))
        menu = self.campo("Recorrência").suffix_icon
        self.assertEqual([i.content for i in menu.items], ["Alterar tipo de valor", "Alterar término da recorrência", "Encerrar recorrência"])  # ajuste D
        nome = self.campo("Nome da conta")
        nome.value = "Energia"
        nome.on_change(Evento(self.pagina, nome))
        self.clicar(self.botao("Salvar alterações"))
        self.clicar(self.acao("Somente este mês"))
        self.assertEqual(self.consultar("SELECT nome FROM contas WHERE id = ?", (self.ids[1],)), [("Energia",)])
        self.assertIn(self.ids[1], self.pendentes())

    def test_valor_em_diante_na_variavel_r5(self):
        # Ajuste deliberado na Etapa 9: antes recusado; agora R5 (só a selecionada e o modelo).
        # Ajustes pós-validação manual (C): só o valor não abre mais o diálogo; com outro campo
        # junto (aqui, o nome), o diálogo e a R5 continuam valendo.
        self.clicar(next(c for c in self.controles(ft.IconButton) if c.data == "mes_anterior"))  # agosto
        self.clicar(self.linha("Luz"))
        self.clicar(self.botao("Editar"))
        campo = self.campo("Valor")
        campo.value = "170,00"
        campo.on_change(Evento(self.pagina, campo))
        nome = self.campo("Nome da conta")
        nome.value = "Energia"
        nome.on_change(Evento(self.pagina, nome))
        self.clicar(self.botao("Salvar alterações"))
        self.assertIn(main.TEXTO_AVISO_R5, self.textos_do_dialogo())
        self.clicar(self.acao("Este mês em diante"))
        self.assertEqual(self.consultar("SELECT valor FROM contas WHERE serie_id = ? ORDER BY posicao",
                                        (self.serie,)), [(170.0,), (0.0,), (0.0,), (0.0,)])
        self.assertEqual(self.pendentes() & set(self.ids), set(self.ids[1:]))

    def test_fixa_sem_alterar_frequencia(self):
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "mensal")
        self.entrar()
        self.clicar(self.linha("Aluguel"))
        self.clicar(self.botao("Editar"))
        menu = self.campo("Recorrência").suffix_icon
        self.assertEqual([i.content for i in menu.items], ["Alterar tipo de valor", "Alterar término da recorrência", "Encerrar recorrência"])  # R6; ajuste D


class TestGraficoComPendentes(BaseVariavelTelas):
    def setUp(self):
        super().setUp()
        self.casa = db.criar_categoria(self.usuario_id, "Casa", "🏡")
        self.lazer = db.criar_categoria(self.usuario_id, "Lazer", "🎭")
        db.criar_conta_unica(self.usuario_id, "Aluguel", 1000.0, "2026-09-05", categoria_id=self.casa)
        # Lazer: agosto com valor, setembro em diante pendentes; novembro só com pendente.
        db.criar_serie_recorrente(self.usuario_id, "Clube", 80.0, "2026-08-12", "mensal", data_termino="2026-11",
                                  categoria_id=self.lazer, variavel=True)
        self.pagina.width = 1200
        self.entrar()

    def abrir_grafico(self):
        self.clicar(next(c for c in self.controles((ft.Container, ft.TextButton)) if c.on_click is not None and any(
            isinstance(t, ft.Text) and t.value == "Gráfico" for t in percorrer(c))))

    def test_totais_barras_e_categorias(self):
        self.abrir_grafico()
        textos = self.textos()
        self.assertIn("R$ 1.000,00", textos)
        explicacao = next(c for c in self.controles(ft.Text) if c.data == "explicacao_total").value
        self.assertTrue(explicacao.endswith("1 conta com valor pendente, fora do total."), explicacao)
        barras = self.controles(fch.BarChart)[0]
        valores = [g.rods[0].tooltip.text for g in barras.groups]
        self.assertEqual(valores[-2:], ["R$ 80,00", "R$ 1.000,00\n+1 pendente"])   # agosto, setembro
        self.assertIn("Valor pendente", textos)                               # legenda: Lazer só com pendente
        # Comparativo: um gráfico por categoria, com o valor acima da coluna e o rótulo no eixo.
        colunas = self.controles(fch.BarChart)[1:]
        self.assertEqual([g.groups[0].rods[0].tooltip.text for g in colunas], ["R$ 1.000,00", "Valor pendente"])
        self.assertEqual([g.bottom_axis.labels[0].label.content.tooltip for g in colunas],
                         ["Casa: R$ 1.000,00", "Lazer: Valor pendente"])

    def test_mes_so_com_pendentes(self):
        self.abrir_grafico()
        for _ in range(2):   # novembro
            self.clicar(next(b for b in self.controles(ft.IconButton) if b.tooltip == "Próximo período"))
        textos = self.textos()
        self.assertIn("Valor pendente", textos)
        self.assertIn("1 conta com valor pendente: a distribuição aparece quando os valores forem informados.",
                      textos)
        self.assertNotIn("Ainda não há dados para exibir neste período.", textos)
        barras = self.controles(fch.BarChart)[0]
        self.assertEqual(barras.groups[-1].rods[0].tooltip.text, "Valor pendente")


if __name__ == "__main__":
    unittest.main()
