"""
Protótipo 6.13 (E2-E4) -- modernização visual de Início (com Ver status e Contas em atraso),
Categorias e Gráfico.

Funções puras de disposição (largura útil, cartão de resumo, alertas, ícone da categoria, linha de
Categorias, layout do Gráfico e legenda compacta) e o fluxo real da interface numa página falsa sobre
banco temporário: os valores exibidos continuam vindo das mesmas funções (resumo_do_mes,
resumo_do_periodo, distribuicao_por_categoria), os controles do teclado são botões com nome e foco
visível, a barra inferior marca a aba ativa nas quatro telas, nenhuma categoria se perde na legenda
compacta e os botões das linhas de Categorias continuam todos presentes em janela estreita (P1).
"""
import os
import sys
import unittest
from unittest import mock

import apoio_banco
from apoio_banco import DataFixa, TesteComBancoTemporario, db

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import flet as ft  # noqa: E402
import flet_charts as fch  # noqa: E402
import main  # noqa: E402
from cores import PALETAS  # noqa: E402

CLARO = PALETAS["claro"]

V = "️"


class Evento:
    def __init__(self, pagina, controle=None):
        self.page = pagina
        self.control = controle


def percorrer(controle):
    yield controle
    for atributo in ("controls", "content", "actions", "title", "icon"):
        filho = getattr(controle, atributo, None)
        if isinstance(filho, list):
            for item in filho:
                yield from percorrer(item)
        elif isinstance(filho, ft.Control):
            yield from percorrer(filho)


def item(categoria_id, total, nome=None, pendentes=0):
    return {"categoria_id": categoria_id, "nome": nome or f"Cat {categoria_id}", "icone": None,
            "cor": "#64B5F6", "cor_exibicao": "#64B5F6", "total": total, "pendentes": pendentes}


# ===================================================================== funções puras
class TestDisposicoes(unittest.TestCase):
    def test_largura_util_desconta_a_margem_real_da_pagina(self):
        self.assertEqual(main.MARGEM_DA_PAGINA, 24)
        self.assertEqual(main.largura_util(380), 332)
        self.assertIsNone(main.largura_util(None))
        self.assertIsNone(main.largura_util(mock.MagicMock()))

    def test_cartao_de_resumo_de_inicio(self):
        self.assertEqual(main.disposicao_do_resumo(1000), "linha")
        self.assertEqual(main.disposicao_do_resumo(380), "duas_colunas")
        self.assertEqual(main.disposicao_do_resumo(320), "uma_coluna")
        self.assertEqual(main.disposicao_do_resumo(None), "linha")   # desconhecida = larga

    def test_alertas(self):
        self.assertTrue(main.alertas_lado_a_lado(1000))
        self.assertFalse(main.alertas_lado_a_lado(380))
        self.assertTrue(main.alerta_em_linha(1000))
        self.assertFalse(main.alerta_em_linha(380))
        self.assertFalse(main.alerta_em_linha(320))

    def test_linha_de_conta_considera_a_margem(self):
        # Início (dois botões): empilha abaixo de 418 px; Ver status/Atrasadas: abaixo de 318 px.
        self.assertFalse(main.linha_de_conta_empilhada(418, 2))
        self.assertTrue(main.linha_de_conta_empilhada(417, 2))
        self.assertTrue(main.linha_de_conta_empilhada(380, 2))
        self.assertFalse(main.linha_de_conta_empilhada(318, 0))
        self.assertTrue(main.linha_de_conta_empilhada(317, 0))

    def test_icone_da_categoria_so_com_folga_para_o_nome(self):
        self.assertTrue(main.linha_com_icone_de_categoria(1000, 2))
        self.assertFalse(main.linha_com_icone_de_categoria(380, 2))
        self.assertFalse(main.linha_com_icone_de_categoria(380, 0))   # Ver status a 380: nome primeiro
        self.assertTrue(main.linha_com_icone_de_categoria(600, 0))
        self.assertTrue(main.linha_com_icone_de_categoria(None, 2))
        # Sempre que mostra o ícone, a linha não empilha e o nome tem a folga mínima.
        for largura in range(300, 1200, 7):
            for acoes in (0, 2):
                if main.linha_com_icone_de_categoria(largura, acoes):
                    self.assertFalse(main.linha_de_conta_empilhada(largura, acoes))

    def test_linha_de_categorias(self):
        self.assertTrue(main.categoria_em_linha(1000))
        self.assertTrue(main.categoria_em_linha(408))
        self.assertFalse(main.categoria_em_linha(407))
        self.assertFalse(main.categoria_em_linha(380))
        self.assertFalse(main.categoria_em_linha(320))

    def test_layout_do_grafico(self):
        largo = main.layout_do_grafico(1000)
        self.assertTrue(largo["topo_lado_a_lado"] and largo["resumo_em_linha"] and largo["cabecalho_em_linha"])
        estreito = main.layout_do_grafico(380)
        self.assertFalse(estreito["topo_lado_a_lado"] or estreito["resumo_em_linha"] or estreito["legenda_ao_lado"])
        self.assertTrue(main.layout_do_grafico(None)["topo_lado_a_lado"])


class TestLegendaCompacta(unittest.TestCase):
    def test_ate_sete_categorias_sem_agrupar(self):
        distribuicao = [item(i, 100 - i) for i in range(1, 8)] + [item(None, 5, "Sem categoria")]
        itens, agrupadas = main.legenda_compacta(distribuicao, "#C9C2B0")
        self.assertEqual(itens, distribuicao)
        self.assertEqual(agrupadas, [])

    def test_mais_de_sete_agrupa_em_outras_sem_perder_nenhuma(self):
        distribuicao = [item(i, 300.0 - i * 7) for i in range(1, 31)] + [item(None, 42.5, "Sem categoria", 1)]
        distribuicao[10]["pendentes"] = 2
        itens, agrupadas = main.legenda_compacta(distribuicao, "#C9C2B0")
        self.assertEqual([i["categoria_id"] for i in itens], [1, 2, 3, 4, 5, 6, "outras", None])
        outras = itens[6]
        self.assertEqual(outras["nome"], "Outras (24)")
        self.assertEqual(outras["cor_exibicao"], "#C9C2B0")
        self.assertNotEqual(outras["cor_exibicao"], db.COR_RESERVADA_SEM_CATEGORIA)
        self.assertAlmostEqual(outras["total"], sum(i["total"] for i in distribuicao[6:30]))
        self.assertEqual(outras["pendentes"], 2)
        # Nenhuma categoria se perde: principais + agrupadas = todas com categoria, na mesma ordem.
        self.assertEqual(itens[:6] + agrupadas, distribuicao[:30])
        # A soma da legenda compacta é a soma da distribuição.
        self.assertAlmostEqual(sum(i["total"] for i in itens), sum(i["total"] for i in distribuicao))
        self.assertEqual(itens[-1]["categoria_id"], None)   # "Sem categoria" sempre à parte e por último

    def test_entrada_nao_e_alterada(self):
        distribuicao = [item(i, 50.0) for i in range(1, 12)]
        copia = [dict(i) for i in distribuicao]
        main.legenda_compacta(distribuicao, "#C9C2B0")
        self.assertEqual(distribuicao, copia)


# ===================================================================== interface
class BaseTelas(TesteComBancoTemporario):
    """Hoje fixo em 15/09/2026 (db e main)."""

    LARGURA = None   # None = desconhecida (larga); um número simula a janela

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.uid = self.criar_usuario(email="telas@sino.com", senha="senha1234")
        db.inicializar_categorias_padrao(self.uid)
        self.ids = {c["nome"]: c["id"] for c in db.listar_categorias(self.uid)}
        self.pagina = mock.MagicMock()
        self.pagina.controls = []
        self.pagina.width = self.LARGURA
        self.pagina.height = 900
        self.pagina.add.side_effect = lambda *controles: self.pagina.controls.extend(controles)
        self.dialogos = []
        self.pagina.show_dialog.side_effect = self.dialogos.append

    def controles(self, tipo=None, raizes=None):
        todos = [c for raiz in (raizes or self.pagina.controls) for c in percorrer(raiz)]
        return [c for c in todos if tipo is None or isinstance(c, tipo)]

    def textos(self, raizes=None):
        return [c.value for c in self.controles(ft.Text, raizes)]

    def com_data(self, data):
        return [c for c in self.controles() if getattr(c, "data", None) == data]

    def clicar(self, controle):
        controle.on_click(Evento(self.pagina, controle))

    def entrar(self):
        main.main(self.pagina)
        campos = {c.label: c for c in self.controles(ft.TextField)}
        campos["E-mail"].value = "telas@sino.com"
        campos["Senha"].value = "senha1234"
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Entrar"))

    def aba(self, nome_aba):
        return next(c for c in self.controles(ft.TextButton) if c.data == ("aba", nome_aba))

    def nome_acessivel(self, botao):
        return next(i.semantics_label for i in percorrer(botao) if getattr(i, "semantics_label", None))


class TestInicio(BaseTelas):
    def popular(self):
        db.criar_conta_unica(self.uid, "Mercado do mês", 300.0, "2026-09-20", categoria_id=self.ids["Mercado"])
        paga = db.criar_conta_unica(self.uid, "Ração", 90.0, "2026-09-18", categoria_id=self.ids["Animais"])
        db.marcar_conta_como_paga(paga, "2026-09-15")
        db.criar_conta_unica(self.uid, "Avulsa", 40.0, "2026-09-25")
        db.criar_conta_unica(self.uid, "Atrasada", 25.0, "2026-09-01")
        # 1ª ocorrência em agosto (valor conhecido); a de setembro fica com valor pendente.
        db.criar_serie_recorrente(self.uid, "Luz", 120.0, "2026-08-21", "mensal", variavel=True)

    def test_cartao_mostra_os_valores_de_resumo_do_mes(self):
        self.popular()
        self.entrar()
        contas = db.listar_contas(self.uid, "2026-09")
        total, pago, pendente = main.resumo_do_mes(contas)
        self.assertEqual(self.com_data("valor_total_mes")[0].value, main.formatar_moeda(total))
        self.assertEqual(self.com_data("valor_pago_mes")[0].value, main.formatar_moeda(pago))
        self.assertEqual(self.com_data("valor_pendente_mes")[0].value, main.formatar_moeda(pendente))
        textos = self.textos()
        for rotulo in ("Total do mês", "Pago", "Pendente"):
            self.assertIn(rotulo, textos)
        # A conta de valor variável continua fora do total, com o aviso (não vira R$ 0,00).
        aviso = self.com_data("aviso_valores_pendentes_mes")[0]
        self.assertTrue(aviso.visible)
        self.assertEqual(aviso.value, "1 conta com valor pendente, fora do total")
        self.assertEqual((total, pago), (455.0, 90.0))
        cartao = self.com_data("cartao_resumo_inicio")[0]
        self.assertIsInstance(cartao.gradient, ft.LinearGradient)
        self.assertEqual(cartao.bgcolor, CLARO["degrade_fim"])   # pior caso para o contraste

    def test_mes_so_com_valor_pendente_nao_mostra_zero_no_total(self):
        db.criar_serie_recorrente(self.uid, "Luz", 120.0, "2026-10-21", "mensal", variavel=True)
        self.entrar()
        self.clicar(next(b for b in self.controles(ft.IconButton) if b.data == "proximo_mes"))
        self.clicar(next(b for b in self.controles(ft.IconButton) if b.data == "proximo_mes"))
        self.assertEqual(self.com_data("valor_total_mes")[0].value, main.TEXTO_VALOR_PENDENTE)

    def test_botoes_do_teclado_e_destinos(self):
        self.popular()
        self.entrar()
        fab = self.com_data("nova_conta")[0]
        self.assertIsInstance(fab, ft.IconButton)
        self.assertEqual(self.nome_acessivel(fab), "Nova conta")
        self.assertIn(ft.ControlState.FOCUSED, fab.style.side)
        ver_status = self.com_data("ver_status")[0]
        ver_essas = self.com_data("ver_essas_contas")[0]
        for botao in (ver_status, ver_essas):
            self.assertIsInstance(botao, ft.TextButton)
            self.assertIn(ft.ControlState.FOCUSED, botao.style.side)
        self.clicar(ver_essas)
        self.assertIn("Contas em atraso", self.textos())
        self.assertIn("Atrasada", self.textos())

    def test_barra_inferior_nas_quatro_telas(self):
        self.entrar()
        for nome_aba, titulo in (("categorias", "Categorias"), ("grafico", "Gráfico"), ("ajustes", None),
                                 ("inicio", "Suas contas de setembro")):
            self.clicar(self.aba(nome_aba))
            abas = [c for c in self.controles(ft.TextButton) if isinstance(c.data, tuple) and c.data[0] == "aba"]
            self.assertEqual([a.data[1] for a in abas], ["inicio", "categorias", "grafico", "ajustes"])
            semanticas = [s for s in self.controles(ft.Semantics) if isinstance(s.content, ft.TextButton)
                          and isinstance(s.content.data, tuple) and s.content.data[0] == "aba"]
            self.assertEqual([s.selected for s in semanticas], [a == nome_aba for a in
                                                                 ("inicio", "categorias", "grafico", "ajustes")])
            for aba in abas:
                ativa = aba.data[1] == nome_aba
                self.assertEqual(aba.style.bgcolor, CLARO["nav_ativo_fundo"] if ativa else None)
                self.assertIn(ft.ControlState.FOCUSED, aba.style.side)
            if titulo:
                self.assertIn(titulo, self.textos())

    def test_icone_da_categoria_e_neutro_sem_categoria(self):
        self.popular()
        self.entrar()
        linhas = {next(t.value for t in percorrer(l) if isinstance(t, ft.Text) and t.weight == ft.FontWeight.BOLD): l
                  for l in self.controles(ft.Container) if l.data == "linha_conta"}
        mercado = [c for c in percorrer(linhas["Mercado do mês"]) if getattr(c, "data", None) == "avatar_categoria"]
        self.assertEqual(len(mercado), 1)
        self.assertEqual(mercado[0].bgcolor, "#43A047")
        self.assertIn("\U0001F6D2", self.textos([mercado[0]]))
        self.assertIn("Mercado · vence em 5 dias", self.textos([linhas["Mercado do mês"]]))   # nome no subtítulo
        avulsa = [c for c in percorrer(linhas["Avulsa"]) if getattr(c, "data", None) == "avatar_sem_categoria"]
        self.assertEqual(len(avulsa), 1)
        self.assertFalse([t for t in percorrer(avulsa[0]) if isinstance(t, ft.Text)])   # sem emoji inventado


class TestInicioEstreito(BaseTelas):
    LARGURA = 380

    def test_380_sem_icone_linhas_empilhadas_e_cartao_em_duas_colunas(self):
        db.criar_conta_unica(self.uid, "Mercado do mês", 300.0, "2026-09-20", categoria_id=self.ids["Mercado"])
        db.criar_conta_unica(self.uid, "Atrasada", 25.0, "2026-09-01")
        self.entrar()
        self.assertEqual(self.com_data(("disposicao_resumo", "duas_colunas")) and 1, 1)
        linhas = [c for c in self.controles(ft.Container) if c.data in ("linha_conta", "linha_conta_empilhada")]
        self.assertTrue(linhas)
        self.assertTrue(all(l.data == "linha_conta_empilhada" for l in linhas))
        self.assertFalse([c for c in self.controles() if getattr(c, "data", None) in ("avatar_categoria",
                                                                                      "avatar_sem_categoria")])
        self.assertIn("Mercado · vence em 5 dias", self.textos())
        self.assertEqual(self.com_data(("alertas_inicio", "empilhados")) and 1, 1)
        atraso = next(c for c in self.controles() if getattr(c, "data", None) == "atraso_empilhado")
        self.assertIsInstance(atraso, ft.Column)   # "Ver essas contas" embaixo do texto


class TestCategorias(BaseTelas):
    def abrir(self):
        self.entrar()
        self.clicar(self.aba("categorias"))

    def test_dezesseis_linhas_com_os_tres_botoes_e_nomes(self):
        self.abrir()
        linhas = [c for c in self.controles(ft.Container) if c.data == "linha_categoria"]
        self.assertEqual(len(linhas), 16)
        for linha in linhas:
            nome = next(t.value for t in percorrer(linha) if isinstance(t, ft.Text) and t.size == 16)
            botoes = [b for b in percorrer(linha) if isinstance(b, ft.IconButton)]
            self.assertEqual([self.nome_acessivel(b) for b in botoes],
                             [f"Nova conta na categoria {nome}", f"Editar categoria {nome}",
                              f"Excluir categoria {nome}"])
            for b in botoes:
                self.assertEqual((b.width, b.height), (40, 40))
                self.assertIn(ft.ControlState.FOCUSED, b.style.side)
        animais = next(l for l in linhas if "Animais" in self.textos([l]))
        avatar = next(c for c in percorrer(animais) if getattr(c, "data", None) == "avatar_categoria")
        # P2: mesmo emoji e mesma cor, ícone maior e com o centro clareado.
        self.assertEqual(avatar.bgcolor, "#FBC02D")
        self.assertEqual(avatar.gradient.colors[-1], "#FBC02D")
        self.assertEqual(avatar.width, 44)
        self.assertIn("\U0001F43E", self.textos([avatar]))

    def test_nova_categoria_abre_o_mesmo_formulario(self):
        self.abrir()
        botao = self.com_data("nova_categoria")[0]
        self.assertIsInstance(botao, ft.Button)
        self.assertIn("Nova categoria", self.textos([botao]))
        self.clicar(botao)
        self.assertEqual(self.dialogos[-1].title.value, "Nova categoria")


class TestCategoriasEstreita(BaseTelas):
    LARGURA = 320

    def test_p1_botoes_embaixo_do_nome_sem_perder_nenhum(self):
        self.entrar()
        self.clicar(self.aba("categorias"))
        linhas = [c for c in self.controles(ft.Container) if c.data in ("linha_categoria", "linha_categoria_empilhada")]
        self.assertEqual(len(linhas), 16)
        for linha in linhas:
            self.assertEqual(linha.data, "linha_categoria_empilhada")
            self.assertIsInstance(linha.content, ft.Column)
            self.assertEqual(len([b for b in percorrer(linha) if isinstance(b, ft.IconButton)]), 3)
            nome = next(t for t in percorrer(linha) if isinstance(t, ft.Text) and t.size == 16)
            self.assertIsNone(nome.max_lines)
            self.assertNotEqual(nome.overflow, ft.TextOverflow.ELLIPSIS)


class TestGrafico(BaseTelas):
    def popular_muitas(self):
        extras = [f"Extra {i:02d}" for i in range(14)]
        for nome in extras:
            db.criar_categoria(self.uid, nome)
        categorias = sorted(db.listar_categorias(self.uid), key=lambda c: c["id"])
        self.assertEqual(len(categorias), 30)
        for i, cat in enumerate(categorias):
            db.criar_conta_unica(self.uid, f"Gasto {i}", 10.0 + i, f"2026-09-{(i % 27) + 1:02d}", categoria_id=cat["id"])
        db.criar_conta_unica(self.uid, "Sem cat", 7.0, "2026-09-10")
        paga = db.criar_conta_unica(self.uid, "Paga", 50.0, "2026-09-11")
        db.marcar_conta_como_paga(paga, "2026-09-11")
        db.criar_serie_recorrente(self.uid, "Variável", 80.0, "2026-08-22", "mensal", variavel=True)

    def abrir(self):
        self.entrar()
        self.clicar(self.aba("grafico"))

    def test_resumo_com_os_numeros_de_resumo_do_periodo(self):
        self.popular_muitas()
        self.abrir()
        total, pago = db.resumo_do_periodo(self.uid, *main.intervalo_do_periodo("mensal", 2026, 9))
        resumo = self.com_data("resumo_do_grafico")[0]
        textos = self.textos([resumo])
        for esperado in ("Total do mês", main.formatar_moeda(total), "Total pago", main.formatar_moeda(pago),
                         "Pendente", main.formatar_moeda(total - pago)):
            self.assertIn(esperado, textos)
        # Mesmo pendente do cartão de Início para o mês (RF12/5.16).
        self.assertEqual(main.resumo_do_mes(db.listar_contas(self.uid, "2026-09"))[2], total - pago)
        self.assertIn("1 conta com valor pendente, fora do total.", " ".join(textos))

    def test_legenda_compacta_e_detalhamento_completo(self):
        self.popular_muitas()
        self.abrir()
        inicio, fim = main.intervalo_do_periodo("mensal", 2026, 9)
        distribuicao = main.distribuicao_por_categoria(
            db.gastos_por_categoria(self.uid, inicio, fim),
            db.cores_de_exibicao(db.listar_categorias(self.uid)), CLARO["sem_categoria"])
        pendentes = db.pendentes_por_categoria(self.uid, inicio, fim)
        for i in distribuicao:   # como a tela faz: a contagem das contas de valor pendente, nunca R$ 0,00
            i["pendentes"] = pendentes.get(i["categoria_id"], 0)
        self.assertEqual(len(distribuicao), 31)
        self.assertEqual(distribuicao[-1]["pendentes"], 1)   # a variável sem categoria, contada à parte
        legenda = [c.data[1] for c in self.controles(ft.Container)
                   if isinstance(c.data, tuple) and c.data[0] == "linha_legenda"]
        self.assertEqual(legenda, [i["categoria_id"] for i in distribuicao[:6]] + ["outras", None])
        self.assertIn("Outras (24)", self.textos())
        self.assertIn("31 categorias", self.textos())
        # Comparativo: todas as categorias, uma a uma (nenhuma some no agrupamento).
        graficos = [g for g in self.controles(fch.BarChart) if g.bottom_axis.labels
                    and isinstance(getattr(g.bottom_axis.labels[0].label, "content", None), ft.TextButton)]
        rotulos = [g.bottom_axis.labels[0].label.content for g in graficos]
        self.assertEqual([r.data[1] for r in rotulos], [i["categoria_id"] for i in distribuicao])
        # "Ver todas as categorias": detalhamento completo, na ordem da distribuição.
        ver_todas = self.com_data("ver_todas_as_categorias")[0]
        self.assertIn("Ver todas as categorias (31)", self.textos([ver_todas]))
        self.clicar(ver_todas)
        dialogo = self.dialogos[-1]
        linhas = [c.data[1] for c in percorrer(dialogo.content)
                  if isinstance(getattr(c, "data", None), tuple) and c.data[0] == "linha_legenda"]
        self.assertEqual(linhas, [i["categoria_id"] for i in distribuicao])
        for i in distribuicao:
            self.assertIn(main.texto_valor_do_periodo(i["total"], i.get("pendentes", 0)), self.textos([dialogo]))

    def test_janela_estreita_legenda_em_duas_linhas(self):
        self.pagina.width = 320
        self.popular_muitas()
        self.abrir()
        self.assertTrue(main.layout_do_grafico(320)["estreito"])
        linhas = [c for c in self.controles(ft.Container) if isinstance(c.data, tuple) and c.data[0] == "linha_legenda"]
        self.assertEqual(len(linhas), 8)
        for linha in linhas:
            marcador, nome_e_valor, percentual = linha.content.controls
            nome, valor = nome_e_valor.controls
            self.assertTrue(nome_e_valor.expand)
            self.assertIsNone(nome.max_lines)
            self.assertTrue(valor.value.startswith("R$"))
            self.assertTrue(percentual.value.endswith("%"))

    def test_alternadores_sao_botoes(self):
        self.abrir()
        opcoes = [c for c in self.controles(ft.TextButton) if isinstance(c.data, tuple) and c.data[0] == "alternador"]
        self.assertEqual([o.data[1] for o in opcoes], ["mensal", "anual", "seis_meses", "anual"])
        self.clicar(opcoes[1])
        self.assertIn("Total do ano", self.textos())


if __name__ == "__main__":
    unittest.main()
