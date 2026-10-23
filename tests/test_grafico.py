"""
Tela Gráfico (ERS v6.0, Etapa 5): RF21-RF23, RF34, 5.24-5.30,
CT63-CT80 e CT114.

Funções puras, consultas somente leitura (todas as contas registradas, pelo
vencimento real e pela categoria de cada ocorrência, sem gerar recorrências)
e o fluxo real da tela com uma página falsa sobre um banco temporário v7.
Hoje fixo em 15/09/2026. Nenhuma janela é aberta.
"""

import asyncio
import os
import sys
import unittest
from unittest import mock

import apoio_banco
from apoio_banco import DataFixa, TesteComBancoTemporario, db
from test_tela_principal import Evento
from test_tela_principal import percorrer as percorrer_tudo

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import cores  # noqa: E402
import flet as ft  # noqa: E402
import flet_charts as fch  # noqa: E402
import main  # noqa: E402


def percorrer(controle):
    """
    Controles VISÍVEIS da árvore: como test_tela_principal.percorrer, sem a faixa
    de medição invisível do comparativo (Sino 6.9, F6), que repete os nomes e
    os valores só para medi-los. A faixa é examinada à parte (faixa_de_medicao).
    """
    if isinstance(controle, ft.Container) and controle.data == main.MARCA_MEDICAO_INVISIVEL:
        return
    yield controle
    for atributo in ("controls", "content", "actions"):
        filho = getattr(controle, atributo, None)
        if isinstance(filho, list):
            for item in filho:
                yield from percorrer(item)
        elif isinstance(filho, ft.Control):
            yield from percorrer(filho)


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
        self.assertEqual(sem_categoria.color, cores.texto_sem_categoria)   # rótulo legível (Etapa 10); a fatia segue #888780

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

    def rosca_e_legenda(self):
        """[(valor da fatia, cor)] da rosca e nomes da legenda, na ordem da tela."""
        rosca = self.controles(fch.PieChart)[0]
        nomes = [t for t in self.textos() if t in ("Casa", "Lazer", "Sem categoria")]
        return [(s.value, s.color) for s in rosca.sections], nomes

    def distribuicao_esperada(self, modo, ano, mes=None):
        itens = db.gastos_por_categoria(self.uid, *main.intervalo_do_periodo(modo, ano, mes))
        return main.distribuicao_por_categoria(
            itens, db.cores_de_exibicao(db.listar_categorias(self.uid)), cores.sem_categoria)

    def test_rosca_usa_a_base_comum_no_mensal_e_no_anual(self):  # Sino 6.9, F3-A
        self.entrar_e_abrir_grafico()
        for modo, ano, mes in (("mensal", 2026, 9), ("anual", 2026, None)):
            with self.subTest(modo=modo):
                if modo == "anual":
                    self.clicar(self.clicavel_com_texto("Anual"))
                esperada = self.distribuicao_esperada(modo, ano, mes)
                secoes, nomes = self.rosca_e_legenda()
                self.assertEqual(secoes, [(i["total"], i["cor_exibicao"]) for i in esperada])
                self.assertEqual(nomes, [i["nome"] for i in esperada])
                self.assertEqual(nomes[-1], "Sem categoria")
                self.assertEqual(secoes[-1][1], cores.sem_categoria)

    # ------------------------------------------- comparativo (5.48; Sino 6.9, F3-B; um gráfico por categoria, F7-A2)
    def cartao_do_comparativo(self):
        return next((c for c in self.controles(ft.Container)
                     if getattr(c.content, "data", None) == "comparativo_por_categoria"), None)

    def graficos_do_comparativo(self):
        """Um BarChart por categoria (F7-A2), na ordem da tela."""
        return [c for c in percorrer(self.cartao_do_comparativo()) if isinstance(c, fch.BarChart)]

    def colunas_do_comparativo(self):
        graficos = self.graficos_do_comparativo()
        botoes = [g.bottom_axis.labels[0].label.content for g in graficos]   # Container -> TextButton (F4)
        return graficos, [g.groups[0].rods[0] for g in graficos], [b.content.value for b in botoes]

    def botoes_do_comparativo(self):
        return [g.bottom_axis.labels[0].label.content for g in self.graficos_do_comparativo()]

    def test_comparativo_logo_depois_de_gastos_por_categoria(self):
        self.entrar_e_abrir_grafico()
        cartao = self.cartao_do_comparativo()
        self.assertIsNotNone(cartao)
        secoes = next(c.controls for c in self.controles(ft.Column) if cartao in c.controls)
        posicao = secoes.index(cartao)
        anterior = list(percorrer(secoes[posicao - 1]))
        self.assertTrue(any(isinstance(c, fch.PieChart) for c in anterior))
        self.assertIn("Gastos por categoria", [getattr(c, "value", None) for c in anterior])
        self.assertIn("Comparado a agosto", [getattr(c, "value", None) for c in percorrer(secoes[posicao + 1])])
        textos_do_cartao = [getattr(c, "value", None) for c in percorrer(cartao)]
        self.assertIn("Comparativo por categoria", textos_do_cartao)

    def test_comparativo_com_os_dados_ordem_e_cores_da_rosca_no_mensal_e_no_anual(self):
        self.entrar_e_abrir_grafico()
        for modo, subtitulo in (("mensal", "Total de cada categoria no mês"),
                                ("anual", "Total de cada categoria no ano")):
            with self.subTest(modo=modo):
                if modo == "anual":
                    self.clicar(self.clicavel_com_texto("Anual"))
                secoes_da_rosca, nomes_da_legenda = self.rosca_e_legenda()
                _, colunas, rotulos = self.colunas_do_comparativo()
                self.assertEqual([(c.to_y, c.color) for c in colunas], secoes_da_rosca)
                self.assertEqual(rotulos, nomes_da_legenda)
                self.assertEqual((rotulos[-1], colunas[-1].color), ("Sem categoria", cores.sem_categoria))
                self.assertIn(subtitulo, [getattr(c, "value", None) for c in percorrer(self.cartao_do_comparativo())])
        # Totais esperados: setembro (Casa 1000, Lazer 490, Sem 60) e 2026 (Casa 2000).
        _, colunas, _ = self.colunas_do_comparativo()
        self.assertEqual([c.to_y for c in colunas], [2000.0, 490.0, 60.0])

    def test_comparativo_totais_do_mes(self):
        self.entrar_e_abrir_grafico()
        _, colunas, rotulos = self.colunas_do_comparativo()
        self.assertEqual(list(zip(rotulos, [c.to_y for c in colunas])),
                         [("Casa", 1000.0), ("Lazer", 490.0), ("Sem categoria", 60.0)])

    def test_um_grafico_por_categoria_com_a_mesma_escala(self):  # F7-A2
        self.entrar_e_abrir_grafico()
        graficos, colunas, _ = self.colunas_do_comparativo()
        self.assertEqual(len(graficos), 3)
        for g in graficos:
            self.assertEqual((len(g.groups), len(g.groups[0].rods), len(g.bottom_axis.labels)), (1, 1, 1))
            self.assertEqual(g.group_alignment, ft.MainAxisAlignment.CENTER)
            self.assertFalse(g.interactive)
        self.assertEqual(len({g.max_y for g in graficos}), 1)                  # escala compartilhada
        self.assertEqual(len({g.height for g in graficos}), 1)                 # mesma base e mesma altura
        self.assertTrue(all(g.horizontal_grid_lines.interval == g.max_y for g in graficos))

    def test_comparativo_colunas_com_contorno_e_sem_interacao(self):
        self.entrar_e_abrir_grafico()
        graficos, colunas, _ = self.colunas_do_comparativo()
        for coluna in colunas:
            self.assertEqual((coluna.border_side.width, coluna.border_side.color), (1, cores.texto_principal))
            self.assertNotEqual(coluna.color, cores.texto_principal)   # preenchimento é a cor da categoria
        evolucao = self.controles(fch.BarChart)[0]
        self.assertNotIn(evolucao, graficos)
        self.assertTrue(all(g.rods[0].border_side is None for g in evolucao.groups))   # evolução inalterada

    # ------------------------------------------- rótulos acessíveis (5.48; Sino 6.9, F4)
    def test_rotulos_sao_botoes_com_nome_acessivel_e_dica(self):
        self.entrar_e_abrir_grafico()
        botoes = self.botoes_do_comparativo()
        esperado = [("Casa", "R$ 1.000,00"), ("Lazer", "R$ 490,00"), ("Sem categoria", "R$ 60,00")]
        self.assertEqual(len(botoes), 3)
        for botao, (nome, valor) in zip(botoes, esperado):
            with self.subTest(nome=nome):
                self.assertIsInstance(botao, ft.TextButton)                          # alternativa A
                self.assertEqual(botao.content.value, nome)                          # nome completo
                self.assertEqual(botao.content.semantics_label, f"{nome}, {valor}")  # nome acessível
                self.assertEqual(botao.tooltip, f"{nome}: {valor}")                  # dica do mouse
                self.assertEqual(botao.style.side[ft.ControlState.FOCUSED].color, cores.acao_primaria)  # foco visível
        sem_categoria = botoes[-1]
        self.assertEqual((sem_categoria.content.color, sem_categoria.style.color),
                         (cores.texto_sem_categoria, cores.texto_sem_categoria))
        self.assertEqual(botoes[0].content.color, cores.texto_principal)

    def test_rotulos_sem_semantics_externo_e_com_espaco_acima(self):
        # `percorrer` não desce nos eixos do gráfico: confere o eixo diretamente.
        self.entrar_e_abrir_grafico()
        for g in self.graficos_do_comparativo():
            caixa = g.bottom_axis.labels[0].label
            self.assertIsInstance(caixa, ft.Container)                  # só o espaço acima do botão (F7-A2)
            self.assertEqual(caixa.padding, ft.Padding(0, main.COMPARATIVO_ESPACO_ACIMA_DO_ROTULO, 0, 0))
            self.assertIsInstance(caixa.content, ft.TextButton)
            self.assertIsInstance(caixa.content.content, ft.Text)        # sem Semantics por dentro
        self.assertEqual(main.COMPARATIVO_ESPACO_ACIMA_DO_ROTULO, 5)
        self.assertEqual([c for c in percorrer(self.cartao_do_comparativo()) if isinstance(c, ft.Semantics)], [])

    def test_ordem_dos_rotulos_segue_as_colunas(self):  # ordem de foco pelo Tab
        self.entrar_e_abrir_grafico()
        self.assertEqual([b.data for b in self.botoes_do_comparativo()],
                         [("rotulo_do_comparativo", self.casa), ("rotulo_do_comparativo", self.lazer),
                          ("rotulo_do_comparativo", None)])

    def test_ativar_rotulo_mostra_o_aviso_com_nome_e_valor(self):  # D2; clique, toque e Enter chamam on_click
        self.entrar_e_abrir_grafico()
        for botao, texto in zip(self.botoes_do_comparativo(),
                                ("Casa: R$ 1.000,00", "Lazer: R$ 490,00", "Sem categoria: R$ 60,00")):
            with self.subTest(texto=texto):
                self.pagina.show_dialog.reset_mock()
                self.clicar(botao)
                aviso = self.pagina.show_dialog.call_args[0][0]
                self.assertIsInstance(aviso, ft.SnackBar)
                self.assertEqual(aviso.content.value, texto)
                self.assertEqual((aviso.content.color, aviso.bgcolor), (cores.fundo_card, cores.texto_principal))

    def test_rotulos_acompanham_o_periodo_anual(self):
        self.entrar_e_abrir_grafico()
        self.clicar(self.clicavel_com_texto("Anual"))
        casa = self.botoes_do_comparativo()[0]
        self.assertEqual((casa.content.semantics_label, casa.tooltip), ("Casa, R$ 2.000,00", "Casa: R$ 2.000,00"))
        self.pagina.show_dialog.reset_mock()
        self.clicar(casa)
        self.assertEqual(self.pagina.show_dialog.call_args[0][0].content.value, "Casa: R$ 2.000,00")

    # ------------------------------------------- valores acima das colunas (5.48; Sino 6.9, F5)
    def test_valor_em_reais_acima_de_cada_coluna(self):
        self.entrar_e_abrir_grafico()
        _, colunas, rotulos = self.colunas_do_comparativo()
        self.assertEqual([(r, c.tooltip.text) for r, c in zip(rotulos, colunas)],
                         [("Casa", "R$ 1.000,00"), ("Lazer", "R$ 490,00"), ("Sem categoria", "R$ 60,00")])
        for coluna in colunas:
            self.assertTrue(coluna.selected)                                   # valor fixo, sem passar o mouse
            self.assertEqual(coluna.tooltip.text, main.formatar_moeda(coluna.to_y))   # texto vem do mesmo total
            estilo = coluna.tooltip.text_style
            self.assertEqual((estilo.size, estilo.weight, estilo.color),
                             (13, ft.FontWeight.BOLD, cores.texto_principal))
        for valor in ("R$ 1.000,00", "R$ 490,00", "R$ 60,00"):                # os mesmos valores da legenda
            self.assertIn(valor, self.textos())

    def test_valores_do_ano(self):
        self.entrar_e_abrir_grafico()
        self.clicar(self.clicavel_com_texto("Anual"))
        _, colunas, _ = self.colunas_do_comparativo()
        self.assertEqual([c.tooltip.text for c in colunas], ["R$ 2.000,00", "R$ 490,00", "R$ 60,00"])

    def test_g4_largura_posicionamento_e_reserva_vertical(self):
        self.entrar_e_abrir_grafico()
        graficos, colunas, _ = self.colunas_do_comparativo()
        maior = max(c.to_y for c in colunas)
        for g, botao in zip(graficos, self.botoes_do_comparativo()):
            balao = g.tooltip
            # F7-A2: max_width = largura do gráfico da categoria = rótulo + espaço entre grupos.
            self.assertEqual((balao.max_width, balao.fit_inside_horizontally, balao.fit_inside_vertically),
                             (round(botao.width + main.COMPARATIVO_ESPACO_ENTRE_GRUPOS, 1), True, True))
            self.assertEqual(g.width, balao.max_width)
            self.assertEqual((balao.bgcolor, balao.padding, balao.margin), (ft.Colors.TRANSPARENT, 0, 4))
            # Reserva: acima da coluna mais alta sobram ao menos 28 px dos 200 px da área.
            area = g.height - g.bottom_axis.label_size
            self.assertEqual(area, 200)
            self.assertGreaterEqual(round((g.max_y - maior) / g.max_y * area, 6), 28)
            self.assertEqual(g.horizontal_grid_lines.interval, g.max_y)

    def test_evolucao_dos_gastos_inalterada(self):
        self.entrar_e_abrir_grafico()
        evolucao = self.controles(fch.BarChart)[0]
        self.assertIsNone(evolucao.tooltip.max_width)
        self.assertFalse(evolucao.tooltip.fit_inside_horizontally or evolucao.tooltip.fit_inside_vertically)
        self.assertEqual(evolucao.max_y, 1550.0 * 1.3)
        self.assertTrue(all(g.rods[0].border_side is None for g in evolucao.groups))

    def test_valores_pequenos_e_extremos_sem_alteracao(self):
        db.criar_conta_unica(self.uid, "Grande", 1234567890123.45, "2026-11-05", categoria_id=self.casa)
        db.criar_conta_unica(self.uid, "Pequena", 0.01, "2026-11-06", categoria_id=self.lazer)
        antes = self.consultar("SELECT COUNT(*) FROM contas")
        self.entrar_e_abrir_grafico()
        for _ in range(2):
            self.clicar(self.seta(ft.Icons.CHEVRON_RIGHT))                # novembro de 2026
        _, colunas, rotulos = self.colunas_do_comparativo()
        self.assertEqual(list(zip(rotulos, [c.tooltip.text for c in colunas])),
                         [("Casa", "R$ 1.234.567.890.123,45"), ("Lazer", "R$ 0,01")])
        self.assertEqual([c.to_y for c in colunas], [1234567890123.45, 0.01])
        self.assertIn("R$ 1.234.567.890.123,45", self.textos())        # o mesmo texto da legenda
        casa = self.botoes_do_comparativo()[0]
        self.assertEqual(casa.content.semantics_label, "Casa, R$ 1.234.567.890.123,45")
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas"), antes)

    # ------------------------------------------- medição invisível e largura (5.48; Sino 6.9, F6/F7-A2)
    def faixa_de_medicao(self):
        return next(c for c in percorrer_tudo(self.cartao_do_comparativo())
                    if isinstance(c, ft.Container) and c.data == main.MARCA_MEDICAO_INVISIVEL)

    def textos_de_medicao(self):
        return [c for c in percorrer_tudo(self.faixa_de_medicao()) if isinstance(c, ft.Text)]

    @staticmethod
    def medida_ficticia(texto):
        """Medição determinística: 7 px por caractere, linha de 16 px (valor: 17)."""
        return mock.Mock(width=7.0 * len(texto.value), height=17.0 if texto.weight else 16.0)

    def medir_tudo(self, medida=None):
        for texto in self.textos_de_medicao():
            texto.on_size_change((medida or self.medida_ficticia)(texto))

    def test_faixa_invisivel_fora_da_acessibilidade_e_sem_foco(self):  # DF3 (estrutura)
        self.entrar_e_abrir_grafico()
        faixa = self.faixa_de_medicao()
        self.assertEqual((faixa.opacity, faixa.height, faixa.clip_behavior), (0, 0, ft.ClipBehavior.HARD_EDGE))
        self.assertIsInstance(faixa.content, ft.Semantics)
        self.assertTrue(faixa.content.exclude_semantics)
        tipos = {type(c) for c in percorrer_tudo(faixa)}
        self.assertLessEqual(tipos, {ft.Container, ft.Semantics, ft.Column, ft.Row, ft.Text})   # nada focável
        for texto in self.textos_de_medicao():
            self.assertEqual((texto.no_wrap, texto.max_lines, texto.size_change_interval), (True, 1, 0))
            self.assertIsNone(texto.semantics_label)
            self.assertIsNotNone(texto.on_size_change)
        medidos = {(("valor" if t.weight else "texto"), t.value) for t in self.textos_de_medicao()}
        self.assertEqual(medidos, {("texto", "Casa"), ("texto", "Lazer"), ("texto", "Sem categoria"),
                                   ("texto", "Sem"), ("texto", "categoria"),
                                   ("valor", "R$ 1.000,00"), ("valor", "R$ 490,00"), ("valor", "R$ 60,00")})
        # A faixa fica fora da coluna espaçada do cartão (sem 16 px a mais).
        pai = next(c for c in percorrer_tudo(self.cartao_do_comparativo())
                   if isinstance(c, ft.Column) and faixa in c.controls)
        self.assertEqual(pai.spacing, 0)

    def test_largura_estimada_antes_da_medicao_por_categoria(self):
        self.entrar_e_abrir_grafico()
        graficos = self.graficos_do_comparativo()
        esperadas = [main.largura_estimada_do_rotulo(n, v) for n, v in
                     (("Casa", "R$ 1.000,00"), ("Lazer", "R$ 490,00"), ("Sem categoria", "R$ 60,00"))]
        self.assertEqual([b.width for b in self.botoes_do_comparativo()], esperadas)
        for g in graficos:
            self.assertEqual(g.bottom_axis.label_size, 48 + 5)              # 2 x 18 (< 40) -> 40 + 8, + 5 acima
            self.assertEqual(g.height - g.bottom_axis.label_size, 200)

    def test_largura_medida_atualiza_no_lugar_uma_vez(self):  # F7-A2: botões e gráficos preservados
        self.entrar_e_abrir_grafico()
        graficos_antes, botoes_antes = self.graficos_do_comparativo(), self.botoes_do_comparativo()
        self.pagina.update.reset_mock()
        self.medir_tudo()
        self.assertEqual(self.pagina.update.call_count, 1)                   # só quando a última medição chega
        graficos, botoes = self.graficos_do_comparativo(), self.botoes_do_comparativo()
        self.assertTrue(all(a is b for a, b in zip(graficos_antes, graficos)))    # mesmos objetos: foco preservado
        self.assertTrue(all(a is b for a, b in zip(botoes_antes, botoes)))
        # T, L e valor fictícios (7 px/caractere): as três categorias ficam no mínimo de 100 + 8.
        self.assertEqual([b.width for b in botoes], [108.0, 108.0, 108.0])
        for g in graficos:
            self.assertEqual(g.tooltip.max_width, 120.0)
            self.assertEqual(g.bottom_axis.label_size, 48 + 5)               # 2 x 16 < 40 -> 40 + 8, + 5 acima
            self.assertAlmostEqual(g.max_y, 1000.0 * 200 / (200 - 27))         # valor medido 17 + 10
        self.medir_tudo()                                                     # mesmas medidas de novo
        self.medir_tudo()
        self.assertEqual(self.pagina.update.call_count, 1)

    def test_larguras_individuais_e_largura_total(self):  # F7-A2
        db.editar_categoria(self.uid, self.casa, nome="Alimentação e mercado do mês")
        self.entrar_e_abrir_grafico()
        self.medir_tudo()
        graficos, botoes = self.graficos_do_comparativo(), self.botoes_do_comparativo()
        longa = main.largura_do_rotulo(7.0 * 28, 7.0 * len("Alimentação"), 7.0 * len("R$ 1.000,00"))
        self.assertEqual([b.width for b in botoes], [longa, 108.0, 108.0])  # cada uma com a sua largura
        self.assertGreater(longa, 108.0)
        self.assertEqual([g.width for g in graficos], [round(b.width + 12, 1) for b in botoes])
        self.assertEqual(sum(g.width for g in graficos), round(longa + 12 + 120 + 120, 1))

    def test_nomes_longos_e_altura_de_duas_linhas(self):
        db.editar_categoria(self.uid, self.casa, nome="Alimentação e mercado do mês")
        self.entrar_e_abrir_grafico()
        self.medir_tudo(lambda t: mock.Mock(width=7.0 * len(t.value), height=22.0))
        graficos, _, rotulos = self.colunas_do_comparativo()
        nome = "Alimentação e mercado do mês"
        self.assertEqual(rotulos[0], nome)                                    # inteiro, sem reticências
        self.assertEqual(self.botoes_do_comparativo()[0].width,
                         main.largura_do_rotulo(7.0 * len(nome), 7.0 * len("Alimentação"), 7.0 * len("R$ 1.000,00")))
        for g in graficos:
            self.assertEqual(g.bottom_axis.label_size, 2 * 22 + 8 + 5)        # duas linhas medidas + folga + 5
            self.assertEqual(g.height - g.bottom_axis.label_size, 200)        # área das colunas mantida
        texto = self.botoes_do_comparativo()[0].content
        self.assertIsNone(texto.max_lines)                                    # sem corte por linhas
        self.assertNotEqual(texto.overflow, ft.TextOverflow.ELLIPSIS)
        self.assertEqual(texto.semantics_label, f"{nome}, R$ 1.000,00")       # nome acessível completo

    def test_redesenhos_limitados_se_as_medidas_oscilarem(self):
        self.entrar_e_abrir_grafico()
        self.pagina.update.reset_mock()
        for passo in range(6):
            self.medir_tudo(lambda t, passo=passo: mock.Mock(width=200.0 + passo * 10, height=16.0))
        self.assertEqual(self.pagina.update.call_count, 3)

    def test_periodo_ja_medido_nao_volta_a_estimativa(self):
        self.entrar_e_abrir_grafico()
        self.medir_tudo()
        medida = self.botoes_do_comparativo()[0].width
        self.clicar(self.seta(ft.Icons.CHEVRON_LEFT))                        # agosto (só Casa)
        self.clicar(self.seta(ft.Icons.CHEVRON_RIGHT))                       # setembro de novo
        self.pagina.update.reset_mock()
        self.assertEqual(self.botoes_do_comparativo()[0].width, medida)       # já medida ao montar
        self.medir_tudo()
        self.assertEqual(self.pagina.update.call_count, 0)

    # ------------------------------------------- rolagem horizontal (5.48; Sino 6.9, F7-A2, híbrida)
    def area_rolavel(self):
        return next(c for c in percorrer_tudo(self.cartao_do_comparativo())
                    if isinstance(c, ft.Row) and c.data == "rolagem_do_comparativo")

    def focar(self, botao):
        asyncio.run(botao.on_focus(Evento(self.pagina, botao)))

    def criar_muitas_categorias(self, quantidade=12):
        for n in range(quantidade):
            categoria = db.criar_categoria(self.uid, f"Categoria fictícia {n:02d}")
            db.criar_conta_unica(self.uid, f"Conta {n}", 100.0 + n, "2026-09-10", categoria_id=categoria)

    def limites_do_botao(self, indice):
        """[início, fim] do botão `indice` na área rolável: grupos acumulados + metade do espaço entre grupos."""
        graficos, botoes = self.graficos_do_comparativo(), self.botoes_do_comparativo()
        inicio = round(sum(g.width for g in graficos[:indice]) + main.COMPARATIVO_ESPACO_ENTRE_GRUPOS / 2, 1)
        return inicio, round(inicio + botoes[indice].width, 1)

    def test_area_rolavel_so_no_comparativo_com_espaco_para_a_barra(self):
        self.entrar_e_abrir_grafico()
        area = self.area_rolavel()
        self.assertEqual(area.scroll, ft.ScrollMode.AUTO)
        self.assertEqual(len(area.controls), 1)
        caixa = area.controls[0]
        self.assertEqual(caixa.padding, ft.Padding(0, 0, 0, main.COMPARATIVO_ESPACO_DA_BARRA_DE_ROLAGEM))
        self.assertEqual(main.COMPARATIVO_ESPACO_DA_BARRA_DE_ROLAGEM, 10)
        self.assertEqual(caixa.content.controls, self.graficos_do_comparativo())
        self.assertEqual(caixa.content.spacing, 0)
        self.assertNotIn(self.faixa_de_medicao(), list(percorrer_tudo(area)))   # faixa fora da rolagem
        rolaveis = [c for c in self.controles(ft.Row) if c.scroll is not None]
        self.assertEqual(rolaveis, [area])                                        # rosca e evolução sem rolagem
        self.assertIsNone(self.controles(fch.BarChart)[0].width)                  # evolução inalterada

    def test_muitas_categorias_sem_comprimir(self):
        self.criar_muitas_categorias()
        self.entrar_e_abrir_grafico()
        graficos, colunas, rotulos = self.colunas_do_comparativo()
        self.assertEqual(len(colunas), 15)
        self.assertEqual(rotulos[-1], "Sem categoria")
        botoes = self.botoes_do_comparativo()
        self.assertEqual([g.width for g in graficos], [round(b.width + 12, 1) for b in botoes])  # nenhuma comprimida
        self.assertGreater(sum(g.width for g in graficos), 380)
        # Coluna, valor e rótulo continuam juntos, na ordem da rosca.
        secoes, nomes = self.rosca_e_legenda_completa()
        self.assertEqual([(c.to_y, c.color) for c in colunas], secoes)
        self.assertEqual(rotulos, nomes)
        self.assertEqual([c.tooltip.text for c in colunas], [main.formatar_moeda(c.to_y) for c in colunas])
        for botao, coluna in zip(botoes, colunas):
            self.assertEqual(botao.content.semantics_label,
                             f"{botao.content.value}, {main.formatar_moeda(coluna.to_y)}")

    def rosca_e_legenda_completa(self):
        rosca = self.controles(fch.PieChart)[0]
        nomes = [t.value for t in self.controles(ft.Text)
                 if t.value in {"Casa", "Lazer", "Sem categoria"} or str(t.value).startswith("Categoria fictícia")]
        return [(s.value, s.color) for s in rosca.sections], nomes

    def test_rolagem_hibrida_so_quando_o_botao_nao_esta_inteiro(self):
        self.criar_muitas_categorias()
        self.entrar_e_abrir_grafico()
        area, botoes = self.area_rolavel(), self.botoes_do_comparativo()
        self.pagina.show_dialog.reset_mock()
        with mock.patch.object(main, "COMPARATIVO_ESPERA_ROLAGEM_DO_FLUTTER", 0), \
                mock.patch.object(area, "scroll_to", new=mock.AsyncMock()) as rolar:
            self.focar(botoes[0])                                    # já no início: não rola
            self.focar(botoes[5])                                    # largura visível ainda desconhecida: não rola
            rolar.assert_not_called()
            area.on_size_change(mock.Mock(width=300.0))               # área de ~300 px
            inicio5, _ = self.limites_do_botao(5)
            area.on_scroll(mock.Mock(pixels=inicio5, viewport_dimension=300.0))   # o Flutter já trouxe o 5 (Tab)
            self.focar(botoes[5])                                    # inteiro: não rola (sem rolagem dupla)
            rolar.assert_not_called()
            _, fim9 = self.limites_do_botao(9)
            self.focar(botoes[9])                                    # fora da vista (ex.: foco pelo AT-SPI)
            rolar.assert_awaited_once_with(offset=fim9 - 300.0, duration=150)   # mínimo: até a borda do botão
            rolar.reset_mock()
            area.on_scroll(mock.Mock(pixels=fim9 - 300.0, viewport_dimension=300.0))
            inicio2, _ = self.limites_do_botao(2)
            self.focar(botoes[2])                                    # à esquerda: alinha o início do botão
            rolar.assert_awaited_once_with(offset=inicio2, duration=150)
        self.pagina.show_dialog.assert_not_called()                  # foco não abre o aviso (D2)

    def test_rolagem_hibrida_ignora_foco_que_ja_mudou(self):
        self.criar_muitas_categorias()
        self.entrar_e_abrir_grafico()
        area, botoes = self.area_rolavel(), self.botoes_do_comparativo()
        area.on_size_change(mock.Mock(width=1000.0))
        area.on_scroll(mock.Mock(pixels=0.0, viewport_dimension=1000.0))

        async def dois_focos():
            # O foco vai ao 9 e, antes do fim da espera, ao 2: só o último conta.
            await asyncio.gather(botoes[9].on_focus(Evento(self.pagina, botoes[9])),
                                 botoes[2].on_focus(Evento(self.pagina, botoes[2])))

        with mock.patch.object(main, "COMPARATIVO_ESPERA_ROLAGEM_DO_FLUTTER", 0.05), \
                mock.patch.object(area, "scroll_to", new=mock.AsyncMock()) as rolar:
            asyncio.run(dois_focos())
        _, fim2 = self.limites_do_botao(2)
        _, fim9 = self.limites_do_botao(9)
        self.assertLessEqual(fim2, 1000.0)                            # o 2 já está inteiro: ninguém rola
        self.assertGreater(fim9, 1000.0)                              # (o 9 teria exigido rolagem)
        rolar.assert_not_called()

    def test_clique_mostra_o_aviso_sem_rolar(self):  # F7-A2 (D): clique não desloca o gráfico
        self.criar_muitas_categorias()
        self.entrar_e_abrir_grafico()
        area, botoes = self.area_rolavel(), self.botoes_do_comparativo()
        area.on_size_change(mock.Mock(width=300.0))
        with mock.patch.object(area, "scroll_to", new=mock.AsyncMock()) as rolar:
            self.pagina.show_dialog.reset_mock()
            self.clicar(botoes[12])                                   # rótulo fora da vista
            rolar.assert_not_called()
        self.assertIsInstance(self.pagina.show_dialog.call_args[0][0], ft.SnackBar)

    def test_ordem_de_foco_segue_as_colunas_com_rolagem(self):
        self.criar_muitas_categorias()
        self.entrar_e_abrir_grafico()
        botoes = self.botoes_do_comparativo()
        self.assertTrue(all(b.on_focus is not None for b in botoes))
        self.assertEqual([b.data[1] for b in botoes][-1], None)                  # "Sem categoria" por último
        self.assertEqual(botoes, [g.bottom_axis.labels[0].label.content for g in self.graficos_do_comparativo()])

    def test_comparativo_some_sem_contas_e_nao_gera_ocorrencias(self):
        antes = self.consultar("SELECT COUNT(*) FROM contas")
        self.entrar_e_abrir_grafico()
        for _ in range(3):
            self.clicar(self.seta(ft.Icons.CHEVRON_RIGHT))             # outubro a dezembro, sem contas
            self.assertIsNone(self.cartao_do_comparativo())
            self.assertNotIn("Comparativo por categoria", self.textos())
            self.assertEqual(len(self.controles(fch.BarChart)), 1)     # só a evolução
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas"), antes)

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
