"""
Tela Gráfico (ERS v6.0, Etapa 5): RF21-RF23, RF34, 5.24-5.30,
CT63-CT80 e CT114.

Funções puras, consultas somente leitura (todas as contas registradas, pelo
vencimento real e pela categoria de cada ocorrência, sem gerar recorrências)
e o fluxo real da tela com uma página falsa sobre um banco temporário v7.
Hoje fixo em 15/09/2026. Nenhuma janela é aberta.
"""

import os
import sys
import unittest
from unittest import mock

import apoio_banco
from apoio_banco import DataFixa, TesteComBancoTemporario, db
from test_tela_principal import Evento, percorrer

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import cores  # noqa: E402
import flet as ft  # noqa: E402
import flet_charts as fch  # noqa: E402
import main  # noqa: E402


class TestFuncoesDoGrafico(unittest.TestCase):
    def test_percentual_com_casa_decimal_so_quando_necessaria(self):
        self.assertEqual(main.formatar_percentual(490 / 2000 * 100), "24,5%")  # CT73
        self.assertEqual(main.formatar_percentual(840 / 2000 * 100), "42%")    # CT74
        self.assertEqual(main.formatar_percentual(8.33), "8,3%")
        self.assertEqual(main.formatar_percentual(0), "0%")

    def test_ct66_total_pago(self):
        self.assertEqual(main.texto_total_pago(2000.0, 2340.0), "R$ 2.000,00 de R$ 2.340,00 pagos — 85,5%")
        self.assertEqual(main.texto_total_pago(0.0, 0.0), "R$ 0,00 de R$ 0,00 pagos — 0%")

    def test_ct77_a_ct80_comparacao(self):
        self.assertEqual(main.comparacao_com_anterior(2340.0, 2090.0),
                         {"tipo": "aumento", "destaque": "▲ 12%", "complemento": "R$ 250,00 a mais"})
        self.assertEqual(main.comparacao_com_anterior(1500.0, 1500.0)["destaque"], "0% — Sem alteração")
        self.assertEqual(main.comparacao_com_anterior(500.0, 0.0),
                         {"tipo": "sem_base", "destaque": "Não há base de comparação",
                          "complemento": "R$ 500,00 a mais"})
        self.assertEqual(main.comparacao_com_anterior(0.0, 0.0)["destaque"], "Sem gastos nos dois períodos.")
        self.assertEqual(main.comparacao_com_anterior(1800.0, 2000.0),
                         {"tipo": "reducao", "destaque": "▼ 10%", "complemento": "R$ 200,00 a menos"})

    def test_janela_de_seis_meses_cruza_o_ano(self):
        self.assertEqual(main.janela_seis_meses(2026, 9), [(2026, m) for m in range(4, 10)])  # CT68
        self.assertEqual(main.janela_seis_meses(2026, 2),
                         [(2025, 9), (2025, 10), (2025, 11), (2025, 12), (2026, 1), (2026, 2)])

    def test_periodos_e_ano_inicial(self):
        self.assertEqual(main.intervalo_do_periodo("mensal", 2028, 2), ("2028-02-01", "2028-02-29"))
        self.assertEqual(main.intervalo_do_periodo("anual", 2026), ("2026-01-01", "2026-12-31"))
        self.assertEqual(main.rotulo_periodo("mensal", 2026, 9), "Setembro de 2026")
        self.assertEqual(main.rotulo_periodo("anual", 2026), "2026")
        self.assertEqual(main.ano_inicial_anual([2024, 2026], 2026), 2026)
        self.assertEqual(main.ano_inicial_anual([2024, 2025], 2026), 2025)
        self.assertEqual(main.ano_inicial_anual([], 2026), 2026)

    def test_sem_categoria_sempre_por_ultimo(self):
        itens = [{"categoria_id": None, "nome": "Sem categoria", "total": 900.0},
                 {"categoria_id": 2, "nome": "Lazer", "total": 100.0},
                 {"categoria_id": 1, "nome": "Casa", "total": 500.0}]
        self.assertEqual([i["nome"] for i in main.ordenar_distribuicao(itens)], ["Casa", "Lazer", "Sem categoria"])


class TestConsultasDoGrafico(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.uid = self.criar_usuario()
        self.casa = db.criar_categoria(self.uid, "Casa", "🏡")
        self.lazer = db.criar_categoria(self.uid, "Lazer", "🎭")

    def resumo(self, ano, mes):
        return db.resumo_do_periodo(self.uid, *main.intervalo_do_periodo("mensal", ano, mes))

    def distribuicao(self, ano, mes):
        return {i["nome"]: i["total"] for i in db.gastos_por_categoria(self.uid, *main.intervalo_do_periodo("mensal", ano, mes))}

    def test_ct63_ct65_total_com_todos_os_status_e_pagar_nao_muda_o_total(self):
        pago = db.criar_conta_unica(self.uid, "A", 100.0, "2026-09-05")
        db.criar_conta_unica(self.uid, "B", 50.0, "2026-09-10")   # atrasada
        pendente = db.criar_conta_unica(self.uid, "C", 25.5, "2026-09-20")
        db.marcar_conta_como_paga(pago, "2026-09-05")
        self.assertEqual(self.resumo(2026, 9), (175.5, 100.0))
        db.marcar_conta_como_paga(pendente, "2026-09-12")
        self.assertEqual(self.resumo(2026, 9), (175.5, 125.5))

    def test_ct64_contas_futuras_entram_no_ano(self):
        db.criar_conta_unica(self.uid, "Hoje", 10.0, "2026-09-15")
        db.criar_conta_unica(self.uid, "Dezembro", 90.0, "2026-12-20")
        db.criar_conta_unica(self.uid, "Outro ano", 1000.0, "2027-01-02")
        self.assertEqual(db.resumo_do_periodo(self.uid, *main.intervalo_do_periodo("anual", 2026)), (100.0, 0.0))

    def test_ct69_anos_sem_contas_nao_aparecem(self):
        db.criar_conta_unica(self.uid, "A", 10.0, "2024-03-01")
        db.criar_conta_unica(self.uid, "B", 20.0, "2026-03-01")
        self.assertEqual(db.totais_por_ano(self.uid), [(2024, 10.0), (2026, 20.0)])
        self.assertEqual(db.anos_com_contas(self.uid), [2024, 2026])

    def test_totais_por_mes_so_meses_com_contas(self):
        db.criar_conta_unica(self.uid, "A", 10.0, "2026-04-01")
        db.criar_conta_unica(self.uid, "B", 20.0, "2026-04-30")
        db.criar_conta_unica(self.uid, "C", 5.0, "2026-10-01")
        self.assertEqual(db.totais_por_mes(self.uid, "2026-04", "2026-09"), {"2026-04": 30.0})

    def test_vencimento_real_de_ocorrencia_movida(self):
        serie_id, ids = db.criar_serie_recorrente(self.uid, "Escola", 700.0, "2026-10-10", "mensal")
        db.editar_conta_ocorrencia(ids[0], data_vencimento="2026-11-20")
        self.assertEqual(self.resumo(2026, 10), (0, 0))
        self.assertEqual(self.resumo(2026, 11), (1400.0, 0))

    def test_ct103_ct104_categoria_efetiva_da_ocorrencia(self):
        serie_id, ids = db.criar_serie_recorrente(self.uid, "Clube", 100.0, "2026-10-10", "mensal",
                                                  categoria_id=self.casa)
        db.editar_conta_ocorrencia(ids[0], categoria_id=self.lazer)          # Somente este mês (outubro)
        self.assertEqual(self.distribuicao(2026, 10), {"Lazer": 100.0})
        self.assertEqual(self.distribuicao(2026, 11), {"Casa": 100.0})
        db.editar_conta_serie(ids[2], remover_categoria=True)               # dezembro em diante
        self.assertEqual(self.distribuicao(2026, 11), {"Casa": 100.0})
        self.assertEqual(self.distribuicao(2026, 12), {"Sem categoria": 100.0})

    def test_ct70_ct72_so_categorias_do_periodo_e_sem_categoria_so_quando_existe(self):
        db.criar_conta_unica(self.uid, "A", 10.0, "2026-09-01", categoria_id=self.casa)
        self.assertEqual(self.distribuicao(2026, 9), {"Casa": 10.0})
        db.criar_conta_unica(self.uid, "B", 5.0, "2026-09-02")
        itens = db.gastos_por_categoria(self.uid, *main.intervalo_do_periodo("mensal", 2026, 9))
        sem = [i for i in itens if i["categoria_id"] is None]
        self.assertEqual((sem[0]["nome"], sem[0]["icone"], sem[0]["total"]), ("Sem categoria", None, 5.0))

    def test_sem_categoria_em_cada_tema(self):
        # A cor armazenada/reservada é uma só; só a de exibição muda no escuro (5.36).
        self.assertEqual(db.COR_RESERVADA_SEM_CATEGORIA, "#888780")
        with self.subTest(tema="claro"):
            self.assertEqual(cores.Paleta("claro").sem_categoria, db.COR_RESERVADA_SEM_CATEGORIA)
            self.assertEqual(cores.sem_categoria, db.COR_RESERVADA_SEM_CATEGORIA)
        with self.subTest(tema="escuro"):
            cinza_escuro = cores.Paleta("escuro").sem_categoria
            self.assertNotEqual(cinza_escuro, db.COR_RESERVADA_SEM_CATEGORIA)
            self.assertNotIn(cinza_escuro, db.PALETA_CORES_CATEGORIAS)
            self.assertNotIn(cinza_escuro, db.CORES_CATEGORIAS_PRE_CRIADAS)

    def test_ct76_cinza_reservado_recusado_na_gravacao(self):
        self.assertNotIn(db.COR_RESERVADA_SEM_CATEGORIA, db.PALETA_CORES_CATEGORIAS)
        with self.assertRaises(db.CorReservadaError):
            db.criar_categoria(self.uid, "Cinza", None, "#888780")
        with self.assertRaises(db.CorReservadaError):
            db.editar_categoria(self.uid, self.casa, cor="#888780")
        self.assertNotEqual(self.consultar("SELECT cor FROM categorias WHERE id = ?", (self.casa,))[0][0], "#888780")

    def test_cores_de_exibicao_estaveis_e_sem_cinza(self):
        sem_cor_1 = self.executar("INSERT INTO categorias (usuario_id, nome, icone, cor) VALUES (?, 'X', '🧺', NULL)",
                                  (self.uid,))
        sem_cor_2 = self.executar("INSERT INTO categorias (usuario_id, nome, icone, cor) VALUES (?, 'Y', NULL, NULL)",
                                  (self.uid,))
        categorias = db.listar_categorias(self.uid)
        exibicao = db.cores_de_exibicao(categorias)
        usadas = {c["cor"] for c in categorias if c["cor"]}
        self.assertNotIn(exibicao[sem_cor_1], usadas)
        self.assertNotIn(exibicao[sem_cor_2], usadas | {exibicao[sem_cor_1]})
        self.assertNotIn(db.COR_RESERVADA_SEM_CATEGORIA, exibicao.values())
        self.assertEqual(db.cores_de_exibicao(list(reversed(categorias))), exibicao)  # estável
        self.assertEqual(self.consultar("SELECT cor FROM categorias WHERE id = ?", (sem_cor_1,))[0][0], None)

    def test_cores_de_exibicao_sem_cor_livre_reaproveita_a_paleta(self):
        categorias = [{"id": i, "cor": cor} for i, cor in enumerate(db.PALETA_CORES_CATEGORIAS)]
        categorias.append({"id": 99, "cor": None})
        cor = db.cores_de_exibicao(categorias)[99]
        self.assertIn(cor, db.PALETA_CORES_CATEGORIAS)
        self.assertNotEqual(cor, db.COR_RESERVADA_SEM_CATEGORIA)

    def test_ct114_consultas_nao_geram_recorrencias(self):
        serie_id, _ = db.criar_serie_recorrente(self.uid, "Luz", 50.0, "2026-09-10", "mensal")
        antes = (self.consultar("SELECT COUNT(*) FROM contas"), self.serie(serie_id)["horizonte_gerado_ate"])
        for ano in (2026, 2027, 2028, 2030):
            db.resumo_do_periodo(self.uid, *main.intervalo_do_periodo("anual", ano))
            db.gastos_por_categoria(self.uid, *main.intervalo_do_periodo("anual", ano))
            db.totais_por_mes(self.uid, f"{ano}-01", f"{ano}-12")
        db.totais_por_ano(self.uid)
        self.assertEqual((self.consultar("SELECT COUNT(*) FROM contas"), self.serie(serie_id)["horizonte_gerado_ate"]),
                         antes)


class TestTelaGrafico(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.uid = self.criar_usuario(email="grafico@sino.com", senha="senha1234")
        self.casa = db.criar_categoria(self.uid, "Casa", "🏡")
        self.lazer = db.criar_categoria(self.uid, "Lazer", "🎭")
        aluguel = db.criar_conta_unica(self.uid, "Aluguel", 1000.0, "2026-09-05", categoria_id=self.casa)
        db.marcar_conta_como_paga(aluguel, "2026-09-05")
        db.criar_conta_unica(self.uid, "Cinema", 490.0, "2026-09-20", categoria_id=self.lazer)
        db.criar_conta_unica(self.uid, "Presente", 60.0, "2026-09-25")       # sem categoria, 3,9%
        db.criar_conta_unica(self.uid, "Agosto", 1000.0, "2026-08-10", categoria_id=self.casa)
        db.criar_conta_unica(self.uid, "Dois anos atrás", 300.0, "2024-12-10")   # sem contas em 2025
        self.serie_id, _ = db.criar_serie_recorrente(self.uid, "Luz", 0.01, "2022-01-10", "mensal",
                                                     data_termino="2022-01")    # sem contas em 2023
        self.pagina = mock.MagicMock()
        self.pagina.controls = []
        self.pagina.width = 1200
        self.pagina.add.side_effect = lambda *controles: self.pagina.controls.extend(controles)

    # ---------------------------------------------------------------- auxiliares
    def controles(self, tipo=None):
        todos = [c for raiz in self.pagina.controls for c in percorrer(raiz)]
        return [c for c in todos if tipo is None or isinstance(c, tipo)]

    def textos(self):
        return [c.value for c in self.controles(ft.Text)]

    def clicar(self, controle):
        controle.on_click(Evento(self.pagina, controle))

    def clicavel_com_texto(self, texto):
        return next(c for c in self.controles(ft.Container)
                    if c.on_click is not None and any(isinstance(t, ft.Text) and t.value == texto for t in percorrer(c)))

    def entrar_e_abrir_grafico(self):
        main.main(self.pagina)
        campos = {c.label: c for c in self.controles(ft.TextField)}
        campos["E-mail"].value = "grafico@sino.com"
        campos["Senha"].value = "senha1234"
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Entrar"))
        self.clicar(self.clicavel_com_texto("Gráfico"))
        self.assertTrue(any(getattr(c, "data", None) == "tela_grafico" for c in self.controles()))

    def seta(self, icone):
        return next(b for b in self.controles(ft.IconButton) if b.icon == icone)

    def barras(self):
        grafico = self.controles(fch.BarChart)[0]
        rotulos = [l.label.value for l in grafico.bottom_axis.labels]
        valores = [g.rods[0].tooltip.text for g in grafico.groups]
        destaque = [g.rods[0].color == cores.grafico_barra_destaque for g in grafico.groups]
        return rotulos, valores, destaque

    # ---------------------------------------------------------------- mensal
    def test_mes_atual_totais_barras_rosca_legenda_e_comparacao(self):
        self.entrar_e_abrir_grafico()
        textos = self.textos()
        self.assertIn("Setembro de 2026", textos)
        self.assertIn("Total do mês", textos)
        self.assertIn("R$ 1.550,00", textos)
        self.assertIn("R$ 1.000,00 de R$ 1.550,00 pagos", textos)
        self.assertIn("64,5%", textos)

        rotulos, valores, destaque = self.barras()
        self.assertEqual(rotulos, ["Abr", "Mai", "Jun", "Jul", "Ago", "Set"])  # CT68
        self.assertEqual(valores, ["R$ 0,00", "R$ 0,00", "R$ 0,00", "R$ 0,00", "R$ 1.000,00", "R$ 1.550,00"])
        self.assertEqual(destaque, [False] * 5 + [True])
        self.assertTrue(all(g.rods[0].selected for g in self.controles(fch.BarChart)[0].groups))  # rótulo fixo

        rosca = self.controles(fch.PieChart)[0]
        self.assertEqual([s.title for s in rosca.sections], ["", "", ""])  # percentuais só na legenda
        self.assertEqual(rosca.sections[-1].color, cores.sem_categoria)
        self.assertIn("R$ 1.550,00", [t.value for t in self.controles(ft.Text)])  # total no centro
        for percentual in ("64,5%", "31,6%"):
            self.assertIn(percentual, textos)
        nomes = [t for t in textos if t in ("Casa", "Lazer", "Sem categoria")]
        self.assertEqual(nomes, ["Casa", "Lazer", "Sem categoria"])  # CT71
        self.assertIn("3,9%", textos)  # continua na legenda
        sem_categoria = next(c for c in self.controles(ft.Text) if c.value == "Sem categoria")
        self.assertEqual(sem_categoria.color, cores.sem_categoria)

        self.assertIn("Comparado a agosto", textos)
        self.assertIn("▲ 55%", textos)
        self.assertIn("(R$ 550,00 a mais)", textos)

    def test_cartoes_de_totais_com_a_mesma_altura_e_comparacao_em_largura_total(self):
        self.entrar_e_abrir_grafico()
        total = next(c for c in self.controles(ft.Container) if c.bgcolor == cores.grafico_total_fundo)
        pago = next(c for c in self.controles(ft.Container) if c.bgcolor == cores.grafico_pago_fundo)
        self.assertIsNotNone(total.height)
        self.assertEqual(total.height, pago.height)
        self.assertEqual((total.col, pago.col), ({"xs": 12, "md": 6}, {"xs": 12, "md": 6}))

        corpo = next(c for c in self.controles(ft.Column)
                     if c.horizontal_alignment == ft.CrossAxisAlignment.STRETCH and any(
                         isinstance(filho, ft.Container) and filho.bgcolor == cores.grafico_comparacao_fundo
                         for filho in c.controls))
        comparacao = next(c for c in corpo.controls if isinstance(c, ft.Container)
                          and c.bgcolor == cores.grafico_comparacao_fundo)
        linha = comparacao.content
        self.assertIsInstance(linha, ft.ResponsiveRow)  # empilha em janela estreita
        texto, variacao = linha.controls
        self.assertEqual((texto.col, variacao.col), ({"xs": 12, "sm": 8}, {"xs": 12, "sm": 4}))
        self.assertIn("Comparado a agosto", [t.value for t in percorrer(texto) if isinstance(t, ft.Text)])
        self.assertEqual([t.value for t in percorrer(variacao) if isinstance(t, ft.Text)],
                         ["▲ 55%", "(R$ 550,00 a mais)"])
        self.assertEqual(variacao.horizontal_alignment, ft.CrossAxisAlignment.END)

    def legenda(self, nome):
        """(nome, valor, percentual) da linha da legenda com esse nome."""
        linha = next(c for c in self.controles(ft.Row)
                     if len(c.controls) == 4 and isinstance(c.controls[1], ft.Text) and c.controls[1].value == nome)
        return linha.controls[1:]

    def test_legenda_em_colunas_proximas_e_rosca_maior_em_janela_larga(self):
        nome_longo = "Assinaturas e serviços online"[:30].ljust(30, "x")
        self.assertEqual(len(nome_longo), 30)
        categoria = db.criar_categoria(self.uid, nome_longo, "📺")
        db.criar_conta_unica(self.uid, "Streaming", 45.0, "2026-09-12", categoria_id=categoria)
        self.entrar_e_abrir_grafico()

        rosca = self.controles(fch.PieChart)[0]
        self.assertEqual((rosca.width, rosca.height), (320, 320))
        linhas = [self.legenda(nome) for nome in ("Casa", "Lazer", nome_longo, "Sem categoria")]
        for nome, valor, percentual in linhas:
            self.assertEqual((nome.width, valor.width, percentual.width), (240, 130, 60))  # colunas alinhadas
            self.assertFalse(nome.expand)
            self.assertIsNone(nome.max_lines)  # nunca cortado: sem limite de linhas
            self.assertFalse(nome.no_wrap)     # e com quebra de linha permitida
            self.assertEqual(valor.text_align, ft.TextAlign.RIGHT)
        self.assertEqual(linhas[2][0].value, nome_longo)  # nome completo

    def test_janela_estreita_legenda_embaixo_com_quebra_de_linha(self):
        self.pagina.width = 420
        self.entrar_e_abrir_grafico()
        rosca = self.controles(fch.PieChart)[0]
        self.assertEqual(rosca.width, 300)
        nome, valor, percentual = self.legenda("Casa")
        self.assertTrue(nome.expand)          # ocupa o espaço e quebra linha
        self.assertIsNone(nome.width)
        self.assertEqual((valor.width, percentual.width), (112, 56))
        blocos = next(c for c in self.controles(ft.ResponsiveRow)
                      if any(isinstance(x, ft.Container) and x.content is not None and rosca in percorrer(x.content)
                             for x in c.controls))
        self.assertEqual([x.col for x in blocos.controls], [{"xs": 12, "lg": 5}, {"xs": 12, "lg": 7}])

    def test_redimensionar_redesenha_so_quando_o_layout_muda(self):
        self.entrar_e_abrir_grafico()
        self.assertEqual(self.controles(fch.PieChart)[0].width, 320)
        self.pagina.width = 1000
        self.pagina.on_resize(Evento(self.pagina))
        self.assertEqual(self.controles(fch.PieChart)[0].width, 320)
        self.pagina.width = 400
        self.pagina.on_resize(Evento(self.pagina))
        self.assertEqual(self.controles(fch.PieChart)[0].width, 300)
        self.assertTrue(self.legenda("Casa")[0].expand)
        self.pagina.width = 330
        self.pagina.on_resize(Evento(self.pagina))
        self.assertEqual(self.controles(fch.PieChart)[0].width, 240)

    def test_layout_de_gastos_por_categoria(self):
        self.assertEqual(main.layout_gastos_por_categoria(1200)["largura_nome"], 240)
        self.assertEqual(main.layout_gastos_por_categoria(700)["tamanho_rosca"], 320)
        self.assertEqual(main.layout_gastos_por_categoria(699)["largura_nome"], None)
        self.assertEqual(main.layout_gastos_por_categoria(250)["tamanho_rosca"], 200)
        self.assertEqual(main.layout_gastos_por_categoria(None)["estreita"], False)

    def test_ct67_mes_vazio(self):
        self.entrar_e_abrir_grafico()
        self.clicar(self.seta(ft.Icons.CHEVRON_RIGHT))
        textos = self.textos()
        self.assertIn("Outubro de 2026", textos)
        self.assertIn("R$ 0,00", textos)
        self.assertIn("0%", textos)
        self.assertIn("Ainda não há dados para exibir neste período.", textos)
        self.assertEqual(self.controles(fch.PieChart), [])  # sem dados artificiais
        self.assertIn("▼ 100%", textos)

    # ---------------------------------------------------------------- anual
    def test_modo_anual_e_navegacao_so_entre_anos_com_contas(self):
        self.entrar_e_abrir_grafico()
        self.clicar(self.clicavel_com_texto("Anual"))
        textos = self.textos()
        self.assertIn("2026", textos)
        self.assertIn("Total do ano", textos)
        self.assertIn("R$ 2.550,00", textos)
        rotulos, _, destaque = self.barras()
        self.assertEqual(rotulos, ["2022", "2024", "2026"])  # CT69; perspectiva anual acompanha o modo
        self.assertEqual(destaque, [False, False, True])
        self.assertIn("Comparado a 2025", textos)          # ano imediatamente anterior
        self.assertIn("Não há base de comparação", textos)  # 2025 sem contas (CT79)
        self.assertIn("(R$ 2.550,00 a mais)", textos)

        self.assertTrue(self.seta(ft.Icons.CHEVRON_RIGHT).disabled)
        self.clicar(self.seta(ft.Icons.CHEVRON_LEFT))
        self.assertIn("2024", self.textos())  # pula 2025, sem contas
        self.clicar(self.seta(ft.Icons.CHEVRON_LEFT))
        self.assertIn("2022", self.textos())
        self.assertTrue(self.seta(ft.Icons.CHEVRON_LEFT).disabled)

    def test_seis_meses_no_modo_anual_vai_de_julho_a_dezembro(self):
        self.entrar_e_abrir_grafico()
        self.clicar(self.clicavel_com_texto("Anual"))
        self.clicar(self.clicavel_com_texto("6 meses"))
        rotulos, valores, destaque = self.barras()
        self.assertEqual(rotulos, ["Jul", "Ago", "Set", "Out", "Nov", "Dez"])
        self.assertEqual(valores[1:3], ["R$ 1.000,00", "R$ 1.550,00"])
        self.assertNotIn(True, destaque)
        self.assertIn("2026", self.textos())  # o período geral não muda

    def test_ct114_abrir_e_navegar_nao_gera_recorrencias(self):
        serie_id, _ = db.criar_serie_recorrente(self.uid, "Internet", 99.0, "2026-09-12", "mensal")
        antes = (self.consultar("SELECT COUNT(*) FROM contas"), self.serie(serie_id)["horizonte_gerado_ate"])
        self.entrar_e_abrir_grafico()
        for _ in range(30):
            self.clicar(self.seta(ft.Icons.CHEVRON_RIGHT))
        self.assertIn("Março de 2029", self.textos())
        self.clicar(self.clicavel_com_texto("Anual"))
        self.assertEqual((self.consultar("SELECT COUNT(*) FROM contas"), self.serie(serie_id)["horizonte_gerado_ate"]),
                         antes)

    def test_ct75_sem_categoria_nao_aparece_em_categorias(self):
        self.entrar_e_abrir_grafico()
        self.clicar(self.clicavel_com_texto("Categorias"))
        self.assertNotIn("Sem categoria", self.textos())


if __name__ == "__main__":
    unittest.main()
