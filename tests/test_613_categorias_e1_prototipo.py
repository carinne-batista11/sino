"""
Protótipo 6.13 (E1) -- catálogo de 16 categorias predefinidas aprovado pela autora em 11/11.

Nomes, ícones e cores exatos; ausência de duplicidade; criação para usuários novos (inclusive pelo
cadastro); sugestões de emoji dos nomes novos (e as dos nomes antigos, para quem já tem categorias);
vínculos por categoria_id preservados numa renomeação; categorias personalizadas, unicidade de cor e
limite de 30; e o Gráfico agrupando por categoria.
"""
import os
import sys
import unittest

import apoio_banco
from apoio_banco import TesteComBancoTemporario, db

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import main  # noqa: E402

V = "️"
CATALOGO = [
    ("Moradia", "\U0001F3E0", "#96E199"),
    ("Transporte", "\U0001F697", "#FFD54F"),
    ("Lazer", "\U0001F3A1", "#FFAB91"),
    ("Estudos", "\U0001F4DA", "#64B5F6"),
    ("Esportes", "\U0001F3CB" + V, "#CE93D8"),
    ("Saúde", "\U0001F3E5", "#80CBC4"),
    ("Cartão de crédito", "\U0001F4B3", "#A990D8"),
    ("Beleza", "\U0001F484", "#F48FB1"),
    ("Assinaturas", "\U0001F4FA", "#F3756A"),
    ("Crianças", "\U0001F476", "#77E3D3"),
    ("Outros", "\U0001F4E6", "#EF9A9A"),
    ("Mercado", "\U0001F6D2", "#43A047"),
    ("Lanches", "\U0001F354", "#F57C00"),
    ("Animais", "\U0001F43E", "#FBC02D"),
    ("Compras", "\U0001F6CD" + V, "#8E24AA"),
    ("Finanças", "\U0001F4B0", "#00897B"),
]
CATALOGO_ANTERIOR = ["Casa", "Automóvel", "Lazer", "Faculdade", "Academia", "Saúde", "Cartão de crédito",
                     "Beleza", "Streaming", "Creche", "Outro"]


class TestCatalogo(unittest.TestCase):
    def test_nomes_icones_e_cores_exatos_na_ordem(self):
        self.assertEqual([(n, i, c) for (n, i), c in zip(db.CATEGORIAS_PRE_CRIADAS, db.CORES_CATEGORIAS_PRE_CRIADAS)],
                         CATALOGO)
        self.assertEqual(len(db.CATEGORIAS_PRE_CRIADAS), len(db.CORES_CATEGORIAS_PRE_CRIADAS))

    def test_sem_duplicidade_e_dentro_das_regras(self):
        nomes = [n.casefold() for n, _ in db.CATEGORIAS_PRE_CRIADAS]
        icones = [i for _, i in db.CATEGORIAS_PRE_CRIADAS]
        cores = [c.upper() for c in db.CORES_CATEGORIAS_PRE_CRIADAS]
        self.assertEqual(len(set(nomes)), 16)
        self.assertEqual(len(set(icones)), 16)
        self.assertEqual(len(set(cores)), 16)
        self.assertTrue(set(cores) <= {c.upper() for c in db.PALETA_CORES_CATEGORIAS})
        self.assertNotIn(db.COR_RESERVADA_SEM_CATEGORIA, cores)
        self.assertLessEqual(len(db.CATEGORIAS_PRE_CRIADAS), db.LIMITE_CATEGORIAS_POR_USUARIO)
        self.assertEqual(db.LIMITE_CATEGORIAS_POR_USUARIO, 30)
        self.assertEqual(len(db.PALETA_CORES_CATEGORIAS), 30)
        for nome, _ in db.CATEGORIAS_PRE_CRIADAS:
            self.assertLessEqual(len(nome), db.LIMITE_NOME_CATEGORIA)

    def test_sugestoes_dos_nomes_novos_comecam_pelo_icone_padrao(self):
        for nome, icone in db.CATEGORIAS_PRE_CRIADAS:
            with self.subTest(nome=nome):
                sugestoes = main.sugestoes_emoji_para(nome)
                self.assertEqual(len(sugestoes), 5)
                self.assertEqual(len(set(sugestoes)), 5)
                self.assertEqual(sugestoes[0], icone)
                self.assertEqual(main.sugestoes_emoji_para(f"  {nome.upper()} "), sugestoes)

    def test_nomes_antigos_mantem_as_sugestoes(self):
        # Usuários já cadastrados continuam com os nomes antigos (a lista só vale para usuários novos).
        for nome in CATALOGO_ANTERIOR:
            with self.subTest(nome=nome):
                self.assertEqual(len(main.sugestoes_emoji_para(nome)), 5)
        self.assertEqual(main.sugestoes_emoji_para("Casa")[0], "\U0001F3E1")


class TestUsuariosNovos(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.uid = self.criar_usuario()

    def categorias(self, uid=None):
        return self.consultar("SELECT nome, icone, cor FROM categorias WHERE usuario_id = ? ORDER BY id",
                              (uid or self.uid,))

    def test_inicializar_cria_as_16_com_icone_e_cor(self):
        ids = db.inicializar_categorias_padrao(self.uid)
        self.assertEqual(len(ids), 16)
        self.assertEqual(self.categorias(), CATALOGO)
        self.assertEqual(db.inicializar_categorias_padrao(self.uid), [])   # idempotente
        self.assertEqual(len(self.categorias()), 16)

    def test_cadastro_confirmado_cria_as_16(self):
        # Mesmo caminho do cadastro real (_inserir_categorias_padrao na transação do cadastro).
        conexao = apoio_banco._conectar_original(self.caminho_banco)
        try:
            cursor = conexao.cursor()
            cursor.execute("INSERT INTO usuarios (nome, email, senha_hash, termos_aceitos_em) "
                           "VALUES ('B', 'b@sino.com', 'x', '2026-09-15')")
            outro = cursor.lastrowid
            db._inserir_categorias_padrao(cursor, outro)
            conexao.commit()
        finally:
            conexao.close()
        self.assertEqual(self.categorias(outro), CATALOGO)

    def test_usuario_com_o_catalogo_antigo_nao_e_alterado(self):
        # A lista nova não mexe em quem já tem categorias.
        for nome in CATALOGO_ANTERIOR:
            db.criar_categoria(self.uid, nome)
        antes = self.categorias()
        self.assertEqual(db.inicializar_categorias_padrao(self.uid), [])
        self.assertEqual(self.categorias(), antes)


class TestRenomeacaoPreservaVinculos(TesteComBancoTemporario):
    """Renomear (como a atualização do banco fictício fez) mantém o id e, com ele, contas, séries e Gráfico."""

    def setUp(self):
        super().setUp()
        self.uid = self.criar_usuario()
        self.casa = db.criar_categoria(self.uid, "Casa", "\U0001F3E1", cor="#96E199")
        self.conta = db.criar_conta_unica(self.uid, "Luz", 120.0, "2026-10-05", categoria_id=self.casa)
        self.serie, self.ocorrencias = db.criar_serie_recorrente(self.uid, "Internet", 100.0, "2026-10-12",
                                                                 "mensal", categoria_id=self.casa)
        db.marcar_conta_como_paga(self.ocorrencias[0], "2026-10-12")

    def distribuicao(self, ano, mes):
        return {i["nome"]: (i["categoria_id"], i["total"])
                for i in db.gastos_por_categoria(self.uid, *main.intervalo_do_periodo("mensal", ano, mes))}

    def test_contas_series_pagamentos_e_grafico_seguem_o_id(self):
        contas_antes = self.consultar("SELECT * FROM contas ORDER BY id")
        series_antes = self.consultar("SELECT * FROM series_recorrencia ORDER BY id")
        self.assertEqual(self.distribuicao(2026, 10), {"Casa": (self.casa, 220.0)})

        self.assertTrue(db.editar_categoria(self.uid, self.casa, nome="Moradia", icone="\U0001F3E0"))

        self.assertEqual(self.consultar("SELECT * FROM contas ORDER BY id"), contas_antes)
        self.assertEqual(self.consultar("SELECT * FROM series_recorrencia ORDER BY id"), series_antes)
        self.assertEqual(self.distribuicao(2026, 10), {"Moradia": (self.casa, 220.0)})
        # Ocorrências geradas depois continuam herdando a categoria (agora "Moradia").
        db.gerar_ocorrencias_sob_demanda(self.serie, "2028-01")
        categorias = {c for (c,) in self.consultar("SELECT categoria_id FROM contas WHERE serie_id = ?", (self.serie,))}
        self.assertEqual(categorias, {self.casa})
        self.assertEqual(db.listar_categorias(self.uid)[0]["nome"], "Moradia")


class TestPersonalizadasELimite(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.uid = self.criar_usuario()
        db.inicializar_categorias_padrao(self.uid)

    def test_cabem_14_personalizadas_ate_o_limite_de_30(self):
        for i in range(14):
            db.criar_categoria(self.uid, f"Minha {i}")
        categorias = db.listar_categorias(self.uid)
        self.assertEqual(len(categorias), 30)
        self.assertEqual(len({c["cor"] for c in categorias}), 30)    # cor automática nunca repete
        with self.assertRaises(ValueError):
            db.criar_categoria(self.uid, "Uma a mais")

    def test_cor_automatica_e_a_primeira_livre_da_paleta(self):
        nova = db.criar_categoria(self.uid, "Viagens")
        cor = next(c["cor"] for c in db.listar_categorias(self.uid) if c["id"] == nova)
        self.assertEqual(cor, "#1976D2")   # #64B5F6 (Estudos) já está em uso

    def test_cor_de_predefinida_e_recusada_e_edicao_funciona(self):
        with self.assertRaises(ValueError):
            db.criar_categoria(self.uid, "Feira", cor="#43A047")       # cor de Mercado
        feira = db.criar_categoria(self.uid, "Feira", "\U0001F955")
        with self.assertRaises(ValueError):
            db.editar_categoria(self.uid, feira, cor="#8E24AA")        # cor de Compras
        self.assertTrue(db.editar_categoria(self.uid, feira, nome="Hortifrúti", cor="#AFB42B"))
        self.assertIn(("Hortifrúti", "#AFB42B"), [(c["nome"], c["cor"]) for c in db.listar_categorias(self.uid)])
        # Uma predefinida pode ser renomeada e excluída como qualquer outra.
        mercado = next(c["id"] for c in db.listar_categorias(self.uid) if c["nome"] == "Mercado")
        conta = db.criar_conta_unica(self.uid, "Compra do mês", 300.0, "2026-09-20", categoria_id=mercado)
        self.assertTrue(db.excluir_categoria(self.uid, mercado))
        self.assertIsNone(self.consultar("SELECT categoria_id FROM contas WHERE id = ?", (conta,))[0][0])
        db.criar_categoria(self.uid, "Mercado", cor="#43A047")         # a cor liberada pode voltar

    def test_grafico_agrupa_pelas_categorias_novas(self):
        ids = {c["nome"]: c["id"] for c in db.listar_categorias(self.uid)}
        db.criar_conta_unica(self.uid, "Feira", 80.0, "2026-09-03", categoria_id=ids["Mercado"])
        db.criar_conta_unica(self.uid, "Supermercado", 220.0, "2026-09-10", categoria_id=ids["Mercado"])
        db.criar_conta_unica(self.uid, "Pizza", 60.0, "2026-09-12", categoria_id=ids["Lanches"])
        db.criar_conta_unica(self.uid, "Ração", 90.0, "2026-09-14", categoria_id=ids["Animais"])
        db.criar_conta_unica(self.uid, "Avulsa", 10.0, "2026-09-16")
        itens = db.gastos_por_categoria(self.uid, *main.intervalo_do_periodo("mensal", 2026, 9))
        self.assertEqual({i["nome"]: i["total"] for i in itens},
                         {"Mercado": 300.0, "Lanches": 60.0, "Animais": 90.0, "Sem categoria": 10.0})
        self.assertEqual({i["nome"]: i["cor"] for i in itens if i["categoria_id"]},
                         {"Mercado": "#43A047", "Lanches": "#F57C00", "Animais": "#FBC02D"})
        cores_exibicao = db.cores_de_exibicao(db.listar_categorias(self.uid))
        self.assertEqual(cores_exibicao[ids["Finanças"]], "#00897B")


if __name__ == "__main__":
    unittest.main()
