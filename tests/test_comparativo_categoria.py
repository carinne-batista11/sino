"""
Comparativo por categoria (ERS v7.0, 5.48, M7; Sino 6.9, E12).

F3-A: base comum da rosca de "Gastos por categoria" e do futuro comparativo
-- `main.distribuicao_por_categoria` (nomes, totais, ordem de RF22 e cores
de exibição, com o cinza de "Sem categoria" do tema). Função pura e
consultas sobre um banco temporário; nenhuma janela é aberta.
"""

import copy
import os
import sys
import unittest

import apoio_banco
from apoio_banco import TesteComBancoTemporario, db

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import cores  # noqa: E402
import main  # noqa: E402

CINZA = "#888780"


def item(categoria_id, nome, total, cor=None, icone=None):
    return {"categoria_id": categoria_id, "nome": nome, "icone": icone, "cor": cor, "total": total}


class TestDistribuicaoPorCategoria(unittest.TestCase):
    def test_nomes_totais_e_campos_preservados(self):
        itens = [item(1, "Alimentação e mercado do mês", 820.5, "#AABBCC", "🛒"),
                 item(None, "Sem categoria", 60.0)]
        resultado = main.distribuicao_por_categoria(itens, {1: "#AABBCC"}, CINZA)
        self.assertEqual([(i["nome"], i["total"], i["icone"]) for i in resultado],
                         [("Alimentação e mercado do mês", 820.5, "🛒"), ("Sem categoria", 60.0, None)])
        for original, novo in zip(itens, resultado):
            self.assertEqual({k: v for k, v in novo.items() if k != "cor_exibicao"}, original)

    def test_ordem_de_rf22_e_sem_categoria_por_ultimo(self):
        itens = [item(None, "Sem categoria", 900.0), item(2, "lazer", 100.0), item(3, "Casa", 500.0),
                 item(4, "Bar", 100.0)]
        resultado = main.distribuicao_por_categoria(itens, {}, CINZA)
        # Maior total primeiro; empate pelo nome sem diferenciar maiúsculas.
        self.assertEqual([i["nome"] for i in resultado], ["Casa", "Bar", "lazer", "Sem categoria"])
        self.assertEqual([i["nome"] for i in resultado], [i["nome"] for i in main.ordenar_distribuicao(itens)])

    def test_cores_de_exibicao_e_cor_gravada(self):
        itens = [item(1, "Casa", 300.0, cor="#111111"), item(2, "Lazer", 200.0, cor=None),
                 item(3, "Saúde", 100.0, cor="#333333")]
        resultado = main.distribuicao_por_categoria(itens, {1: "#111111", 2: "#222222"}, CINZA)
        # Categoria sem cor gravada: cor de exibição; fora do mapa: a gravada.
        self.assertEqual([i["cor_exibicao"] for i in resultado], ["#111111", "#222222", "#333333"])

    def test_sem_categoria_com_o_cinza_de_cada_tema(self):
        itens = [item(None, "Sem categoria", 5.0), item(1, "Casa", 10.0, cor="#111111")]
        for tema in ("claro", "escuro"):
            with self.subTest(tema=tema):
                cinza = cores.Paleta(tema).sem_categoria
                resultado = main.distribuicao_por_categoria(itens, {1: "#111111"}, cinza)
                self.assertEqual(resultado[-1]["nome"], "Sem categoria")
                self.assertEqual(resultado[-1]["cor_exibicao"], cinza)
        # Mesmo que o mapa traga uma cor para None, "Sem categoria" usa o cinza.
        resultado = main.distribuicao_por_categoria(itens, {None: "#FF0000", 1: "#111111"}, CINZA)
        self.assertEqual(resultado[-1]["cor_exibicao"], CINZA)

    def test_sem_dados(self):
        self.assertEqual(main.distribuicao_por_categoria([], {}, CINZA), [])
        self.assertEqual(main.distribuicao_por_categoria([], {1: "#111111"}, CINZA), [])

    def test_entrada_nao_e_alterada(self):
        itens = [item(None, "Sem categoria", 5.0), item(2, "Lazer", 1.0), item(1, "Casa", 10.0, cor="#111111")]
        cores_exibicao = {1: "#111111", 2: "#222222"}
        antes = (copy.deepcopy(itens), dict(cores_exibicao))
        resultado = main.distribuicao_por_categoria(itens, cores_exibicao, CINZA)
        self.assertEqual((itens, cores_exibicao), antes)
        self.assertTrue(all("cor_exibicao" not in i for i in itens))
        self.assertTrue(all(novo is not original for novo in resultado for original in itens))

    def test_totais_pequenos_e_extremos_preservados(self):  # F5: o valor exibido vem deste total
        itens = [item(1, "Grande", 1234567890123.45), item(2, "Teto", 9999999999999.99), item(3, "Pequena", 0.01)]
        resultado = main.distribuicao_por_categoria(itens, {}, CINZA)
        self.assertEqual([i["total"] for i in resultado], [9999999999999.99, 1234567890123.45, 0.01])
        self.assertEqual([main.formatar_moeda(i["total"]) for i in resultado],
                         ["R$ 9.999.999.999.999,99", "R$ 1.234.567.890.123,45", "R$ 0,01"])

    def test_ordem_estavel_ao_reaplicar(self):
        itens = [item(2, "Lazer", 100.0), item(1, "lazer", 100.0), item(None, "Sem categoria", 1.0)]
        uma_vez = main.distribuicao_por_categoria(itens, {}, CINZA)
        duas_vezes = main.distribuicao_por_categoria(uma_vez, {}, CINZA)
        self.assertEqual(duas_vezes, uma_vez)


FAMILIA = "👨‍👩‍👧"                  # um grafema (sequência com ZWJ)
ZALGO = "".join(c + ("̴̵" if c != " " else "") for c in "Zalgo com marcas")


class TestLarguraDoComparativo(unittest.TestCase):
    """F6 (D1): W = (T + L) / 2 + margem; heurística, não garantia universal."""

    def test_formula_com_nomes_curtos_e_longos(self):
        # Curto: o mínimo de 100 px prevalece; + 4 px de padding de cada lado.
        self.assertEqual(main.largura_do_rotulo(30.0, 30.0, 60.0), 108.0)
        # Longo em duas linhas: (T + L) / 2 + 2 = (200 + 80) / 2 + 2 = 142 -> 150.
        self.assertEqual(main.largura_do_rotulo(200.0, 80.0, 60.0), 150.0)
        # Uma palavra só (T = L): cabe numa linha.
        self.assertEqual(main.largura_do_rotulo(220.0, 220.0, 60.0), 230.0)
        # Valor mais largo que o nome: valor + 4.
        self.assertEqual(main.largura_do_rotulo(50.0, 50.0, 150.0), 162.0)

    def test_palavras_do_nome(self):
        self.assertEqual(main.palavras_do_nome("Mãe, família  e combinados"), ["Mãe,", "família", "e", "combinados"])
        self.assertEqual(main.palavras_do_nome("Água/luz/gás-internet"), ["Água/luz/gás-internet"])
        self.assertEqual(main.palavras_do_nome(FAMILIA * 3), [FAMILIA * 3])

    def test_estimativa_conta_grafemas(self):
        # O emoji de família conta 1 grafema, e não 5 pontos de código.
        self.assertEqual(main.largura_estimada_do_rotulo(FAMILIA * 30, "R$ 1,00"),
                         main.largura_estimada_do_rotulo("W" * 30, "R$ 1,00"))
        self.assertEqual(main.largura_estimada_do_rotulo(ZALGO, "R$ 1,00"),
                         main.largura_estimada_do_rotulo("Zalgo com marcas", "R$ 1,00"))
        # 30 grafemas: 30 x 1,3 x 12 / 2 + 2 = 236 -> + 8 = 244.
        self.assertEqual(main.largura_estimada_do_rotulo("a" * 30, "R$ 1,00"), 244.0)
        self.assertEqual(main.largura_estimada_do_rotulo("Casa", "R$ 1,00"), 108.0)   # mínimo

    def test_chaves_de_medicao(self):
        distribuicao = main.distribuicao_por_categoria(
            [item(1, "Mãe e família", 95.0), item(None, "Sem categoria", 1234567890123.45)], {}, CINZA)
        self.assertEqual(main.chaves_de_medicao_do_comparativo(distribuicao), {
            ("nome", "Mãe e família"), ("palavra", "Mãe"), ("palavra", "e"), ("palavra", "família"),
            ("valor", "R$ 95,00"), ("nome", "Sem categoria"), ("palavra", "Sem"), ("palavra", "categoria"),
            ("valor", "R$ 1.234.567.890.123,45")})

    def test_geometria_estimada_ate_todas_as_medidas(self):
        distribuicao = main.distribuicao_por_categoria([item(1, "Casa", 10.0)], {}, CINZA)
        parcial = {("nome", "Casa"): (30.0, 16.0)}
        geo = main.geometria_do_comparativo(distribuicao, parcial)
        self.assertFalse(geo["medida"])
        self.assertEqual(geo["larguras_rotulo"], [main.largura_estimada_do_rotulo("Casa", "R$ 10,00")])
        self.assertEqual((geo["altura_rotulos"], geo["altura_valor"]), (48 + 5, 18))   # + 5 acima do rótulo
        completas = {**parcial, ("palavra", "Casa"): (30.0, 16.0), ("valor", "R$ 10,00"): (55.0, 17.0)}
        geo = main.geometria_do_comparativo(distribuicao, completas)
        self.assertTrue(geo["medida"])
        self.assertEqual((geo["larguras_rotulo"], geo["larguras_grupo"]), ([108.0], [120.0]))
        self.assertEqual((geo["inicios"], geo["largura_total"]), ([0.0], 120.0))
        self.assertEqual((geo["altura_rotulos"], geo["altura_valor"]), (48 + 5, 17.0))

    def test_geometria_com_largura_por_categoria_e_posicoes_acumuladas(self):  # Sino 6.9, F7-A2
        distribuicao = main.distribuicao_por_categoria(
            [item(1, "Casa", 10.0), item(2, ZALGO, 5.0), item(None, "Sem categoria", 1.0)], {}, CINZA)
        medidas = {chave: (40.0, 16.0) for chave in main.chaves_de_medicao_do_comparativo(distribuicao)}
        medidas[("nome", ZALGO)] = (260.0, 24.0)       # marcas combinadas: linha mais alta
        medidas[("palavra", "Z\u0334\u0335a\u0334\u0335l\u0334\u0335g\u0334\u0335o\u0334\u0335")] = (70.0, 24.0)
        geo = main.geometria_do_comparativo(distribuicao, medidas)
        longa = main.largura_do_rotulo(260.0, 70.0, 40.0)
        # Cada categoria com a SUA largura (a do Zalgo não alarga as outras).
        self.assertEqual(geo["larguras_rotulo"], [108.0, longa, 108.0])
        self.assertEqual(geo["larguras_grupo"], [120.0, round(longa + 12, 1), 120.0])
        self.assertEqual(geo["inicios"], [0.0, 120.0, round(120.0 + longa + 12, 1)])
        self.assertEqual(geo["largura_total"], round(240.0 + longa + 12, 1))
        self.assertEqual(geo["altura_rotulos"], 2 * 24 + 8 + 5)   # a linha mais alta vale para todos

    def test_geometria_sem_dados(self):
        geo = main.geometria_do_comparativo([], {})
        self.assertTrue(geo["medida"])          # nada a medir
        self.assertEqual((geo["larguras_rotulo"], geo["inicios"], geo["largura_total"], geo["altura_rotulos"]),
                         ([], [], 0.0, 48 + 5))


class TestDeslocamentoParaMostrar(unittest.TestCase):
    """Rolagem híbrida (F7-A2): menor deslocamento que mostra o botão inteiro."""

    def test_botao_inteiro_nao_rola(self):
        self.assertIsNone(main.deslocamento_para_mostrar(100, 208, 0, 300))
        self.assertIsNone(main.deslocamento_para_mostrar(100, 208, 100, 108))     # exato
        self.assertIsNone(main.deslocamento_para_mostrar(100.3, 208.4, 100.7, 108))   # tolerância de 0,5 px

    def test_botao_a_direita_alinha_o_fim(self):
        self.assertEqual(main.deslocamento_para_mostrar(500, 608, 0, 300), 308)
        self.assertEqual(main.deslocamento_para_mostrar(250, 358, 0, 300), 58)   # parcialmente visível

    def test_botao_a_esquerda_alinha_o_inicio(self):
        self.assertEqual(main.deslocamento_para_mostrar(100, 208, 400, 300), 100)
        self.assertEqual(main.deslocamento_para_mostrar(6, 114, 50, 300), 6)

    def test_largura_visivel_desconhecida(self):
        self.assertIsNone(main.deslocamento_para_mostrar(500, 608, 0, None))      # não dá para saber: não rola
        self.assertEqual(main.deslocamento_para_mostrar(100, 208, 400, None), 100)   # começa antes: alinha o início

    def test_nunca_negativo(self):
        self.assertEqual(main.deslocamento_para_mostrar(-3, 105, 50, 300), 0.0)


class TestDistribuicaoComConsultas(TesteComBancoTemporario):
    """Mensal e anual sobre gastos_por_categoria, num banco temporário."""

    def setUp(self):
        super().setUp()
        self.uid = self.criar_usuario(email="comparativo@sino.com", senha="senha1234")
        self.casa = db.criar_categoria(self.uid, "Casa", "🏡")
        self.lazer = db.criar_categoria(self.uid, "Lazer", "🎭")
        db.criar_conta_unica(self.uid, "Aluguel", 1000.0, "2026-09-05", categoria_id=self.casa)
        db.criar_conta_unica(self.uid, "Cinema", 490.0, "2026-09-20", categoria_id=self.lazer)
        db.criar_conta_unica(self.uid, "Presente", 60.0, "2026-09-25")
        db.criar_conta_unica(self.uid, "Show", 800.0, "2026-03-15", categoria_id=self.lazer)

    def distribuicao(self, modo, ano, mes=None):
        itens = db.gastos_por_categoria(self.uid, *main.intervalo_do_periodo(modo, ano, mes))
        cores_exibicao = db.cores_de_exibicao(db.listar_categorias(self.uid))
        return main.distribuicao_por_categoria(itens, cores_exibicao, cores.sem_categoria), cores_exibicao

    def test_mensal(self):
        resultado, cores_exibicao = self.distribuicao("mensal", 2026, 9)
        self.assertEqual([(i["nome"], i["total"]) for i in resultado],
                         [("Casa", 1000.0), ("Lazer", 490.0), ("Sem categoria", 60.0)])
        self.assertEqual([i["cor_exibicao"] for i in resultado],
                         [cores_exibicao[self.casa], cores_exibicao[self.lazer], cores.sem_categoria])

    def test_anual_muda_a_ordem_pelos_totais_do_ano(self):
        resultado, cores_exibicao = self.distribuicao("anual", 2026)
        self.assertEqual([(i["nome"], i["total"]) for i in resultado],
                         [("Lazer", 1290.0), ("Casa", 1000.0), ("Sem categoria", 60.0)])
        self.assertEqual(resultado[0]["cor_exibicao"], cores_exibicao[self.lazer])   # cor estável entre períodos

    def test_periodo_sem_contas(self):
        self.assertEqual(self.distribuicao("mensal", 2026, 10)[0], [])


if __name__ == "__main__":
    unittest.main()
