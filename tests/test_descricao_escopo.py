"""
ERS v6.0, Etapa 2 — descrição da conta (5.22, RF32) e escopo de edição de
categoria e descrição em séries (5.6, RF20; CT58, CT103–CT107).

"Este mês em diante" propaga só os campos efetivamente alterados em relação
à ocorrência selecionada: para ela, para as futuras existentes (inclusive
editadas individualmente) e para o modelo da série, de onde a geração sob
demanda copia. Campos não alterados, status e data de pagamento de cada
ocorrência e ocorrências anteriores ficam intactos.
"""

import os
import sys
import unittest
from datetime import date

import apoio_banco
from apoio_banco import TesteComBancoTemporario, db

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import main  # noqa: E402


class BaseDescricao(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def descricao(self, conta_id):
        return self.consultar("SELECT descricao FROM contas WHERE id = ?", (conta_id,))[0][0]

    def descricoes(self, serie_id):
        return [linha[0] for linha in self.consultar(
            "SELECT descricao FROM contas WHERE serie_id = ? ORDER BY data_vencimento", (serie_id,),
        )]

    def descricao_modelo(self, serie_id):
        return self.consultar("SELECT descricao FROM series_recorrencia WHERE id = ?", (serie_id,))[0][0]

    def criar_serie(self, descricao=None, categoria_id=None, data_termino="2027-06", inicio="2027-01-10"):
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Escola", 700.0, inicio, "mensal",
            data_termino=data_termino, categoria_id=categoria_id, descricao=descricao,
        )
        return serie_id


class TestDescricaoContaUnica(BaseDescricao):
    """CT58 (camada de dados; a exibição em Detalhes é da Etapa 4)."""

    def test_criar_sem_descricao_grava_null(self):
        for texto in (None, "", "   \n "):
            with self.subTest(texto=texto):
                conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-01", descricao=texto)
                self.assertIsNone(self.descricao(conta_id))

    def test_adicionar_editar_remover(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-01")

        db.editar_conta_ocorrencia(conta_id, descricao="  Medidor 123\nApto 4  ")
        self.assertEqual(self.descricao(conta_id), "Medidor 123\nApto 4")

        db.editar_conta_ocorrencia(conta_id, descricao="Medidor 456")
        self.assertEqual(self.descricao(conta_id), "Medidor 456")

        db.editar_conta_ocorrencia(conta_id, remover_descricao=True)
        self.assertIsNone(self.descricao(conta_id))

    def test_descricao_vazia_enviada_equivale_a_remover(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-01", descricao="x")
        db.editar_conta_ocorrencia(conta_id, descricao="   ")
        self.assertIsNone(self.descricao(conta_id))

    def test_none_nao_altera_descricao(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-01", descricao="x")
        db.editar_conta_ocorrencia(conta_id, valor=20.0)
        self.assertEqual(self.descricao(conta_id), "x")

    def test_remover_tem_prioridade_sobre_texto(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-01", descricao="x")
        db.editar_conta_ocorrencia(conta_id, descricao="y", remover_descricao=True)
        self.assertIsNone(self.descricao(conta_id))

    def test_conta_avulsa_via_editar_conta_serie(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-01")
        self.assertTrue(db.editar_conta_serie(conta_id, descricao="nova"))
        self.assertEqual(self.descricao(conta_id), "nova")
        self.assertEqual(self.conta(conta_id)["editado_individualmente"], 0)

    def test_listagens_devolvem_descricao(self):
        self.definir_hoje(date(2026, 9, 15))
        atrasada = db.criar_conta_unica(self.usuario_id, "A", 1.0, "2026-09-01", descricao="atrasada")
        proxima = db.criar_conta_unica(self.usuario_id, "B", 1.0, "2026-09-17", descricao="próxima")
        self.assertEqual({c["id"]: c["descricao"] for c in db.listar_contas(self.usuario_id)},
                         {atrasada: "atrasada", proxima: "próxima"})
        self.assertEqual(db.listar_contas_atrasadas(self.usuario_id)[0]["descricao"], "atrasada")
        self.assertEqual(db.listar_contas_proximas(self.usuario_id)[0]["descricao"], "próxima")


class TestDescricaoNaSerie(BaseDescricao):
    def test_criar_serie_copia_descricao_para_modelo_e_ocorrencias(self):
        serie_id = self.criar_serie(descricao=" Mensalidade ")
        self.assertEqual(self.descricao_modelo(serie_id), "Mensalidade")
        self.assertEqual(set(self.descricoes(serie_id)), {"Mensalidade"})

    def test_ct105_adicionar_este_mes_em_diante_e_gerar_sob_demanda(self):
        serie_id = self.criar_serie(data_termino=None)
        id_mar = self.id_por_data(serie_id, "2027-03-10")

        self.assertTrue(db.editar_conta_serie(id_mar, descricao="Com material"))

        self.assertEqual(self.descricoes(serie_id)[:3], [None, None, "Com material"])
        self.assertEqual(set(self.descricoes(serie_id)[2:]), {"Com material"})
        self.assertEqual(self.descricao_modelo(serie_id), "Com material")

        novos = db.gerar_ocorrencias_sob_demanda(serie_id, "2028-06")
        self.assertTrue(novos)
        for conta_id in novos:
            self.assertEqual(self.descricao(conta_id), "Com material")

    def test_ct106_remover_somente_este_mes(self):
        serie_id = self.criar_serie(descricao="Com material")
        id_mar = self.id_por_data(serie_id, "2027-03-10")

        db.editar_conta_ocorrencia(id_mar, remover_descricao=True)

        self.assertEqual(self.descricoes(serie_id),
                         ["Com material", "Com material", None, "Com material", "Com material", "Com material"])
        self.assertEqual(self.descricao_modelo(serie_id), "Com material")
        self.assertEqual(self.conta(id_mar)["editado_individualmente"], 1)

    def test_remover_este_mes_em_diante_limpa_modelo_e_geracao(self):
        serie_id = self.criar_serie(descricao="Com material", data_termino=None)
        id_mar = self.id_por_data(serie_id, "2027-03-10")

        self.assertTrue(db.editar_conta_serie(id_mar, remover_descricao=True))

        self.assertEqual(self.descricoes(serie_id)[:2], ["Com material", "Com material"])
        self.assertEqual(set(self.descricoes(serie_id)[2:]), {None})
        self.assertIsNone(self.descricao_modelo(serie_id))
        for conta_id in db.gerar_ocorrencias_sob_demanda(serie_id, "2028-06"):
            self.assertIsNone(self.descricao(conta_id))

    def test_alterar_descricao_este_mes_em_diante_sobrescreve_futura_editada(self):
        serie_id = self.criar_serie(descricao="A")
        id_mai = self.id_por_data(serie_id, "2027-05-10")
        db.editar_conta_ocorrencia(id_mai, descricao="Própria", valor=999.0)
        id_fev = self.id_por_data(serie_id, "2027-02-10")

        self.assertTrue(db.editar_conta_serie(id_fev, descricao="B"))

        maio = self.conta(id_mai)
        self.assertEqual(self.descricao(id_mai), "B")
        self.assertEqual((maio["valor"], maio["editado_individualmente"]), (999.0, 1))
        self.assertEqual(self.descricoes(serie_id)[0], "A")

    def test_descricao_repetida_nao_sobrescreve_futura_editada(self):
        serie_id = self.criar_serie(descricao="A")
        id_mai = self.id_por_data(serie_id, "2027-05-10")
        db.editar_conta_ocorrencia(id_mai, descricao="Própria")
        id_fev = self.id_por_data(serie_id, "2027-02-10")

        # A tela reenviando a mesma descrição (com espaços) junto de outro campo.
        self.assertTrue(db.editar_conta_serie(id_fev, valor=750.0, descricao=" A "))

        self.assertEqual(self.descricao(id_mai), "Própria")
        self.assertEqual(self.conta(id_mai)["valor"], 750.0)

    def test_remover_descricao_ja_vazia_nao_altera_nada(self):
        serie_id = self.criar_serie()
        id_mai = self.id_por_data(serie_id, "2027-05-10")
        db.editar_conta_ocorrencia(id_mai, descricao="Própria")
        id_fev = self.id_por_data(serie_id, "2027-02-10")
        antes = (self.descricoes(serie_id), self.descricao_modelo(serie_id))

        self.assertTrue(db.editar_conta_serie(id_fev, remover_descricao=True))

        self.assertEqual((self.descricoes(serie_id), self.descricao_modelo(serie_id)), antes)

    def test_transformar_em_recorrente_copia_descricao(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-10-05", descricao="Apólice 77")
        serie_id, novos = db.transformar_em_recorrente(conta_id, "mensal", data_termino="2027-01")
        self.assertEqual(self.descricao_modelo(serie_id), "Apólice 77")
        self.assertEqual(len(novos), 3)
        self.assertEqual(set(self.descricoes(serie_id)), {"Apólice 77"})

    def test_transformar_sem_descricao_gera_null(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-10-05")
        serie_id, _ = db.transformar_em_recorrente(conta_id, "anual")
        self.assertIsNone(self.descricao_modelo(serie_id))
        self.assertEqual(set(self.descricoes(serie_id)), {None})

    def test_alterar_frequencia_usa_descricao_do_modelo_e_preserva_editadas(self):
        serie_id = self.criar_serie(descricao="Modelo", data_termino="2027-12")
        id_jun = self.id_por_data(serie_id, "2027-06-10")
        db.editar_conta_ocorrencia(id_jun, descricao="Editada")
        id_fev = self.id_por_data(serie_id, "2027-02-10")
        db.editar_conta_ocorrencia(id_fev, descricao="Só fevereiro")

        resultado = db.alterar_frequencia_serie(id_fev, "mensal", data_termino="2027-12")

        self.assertIn(id_jun, resultado["ocorrencias_preservadas"])
        self.assertEqual(self.descricao(id_jun), "Editada")
        self.assertEqual(self.descricao(id_fev), "Só fevereiro")
        for conta_id in resultado["ocorrencias_novas"]:
            self.assertEqual(self.descricao(conta_id), "Modelo")
        self.assertEqual(self.descricao(self.id_por_data(serie_id, "2027-01-10")), "Modelo")


class TestCategoriaNoEscopo(BaseDescricao):
    def setUp(self):
        super().setUp()
        self.casa = self.criar_categoria(self.usuario_id, "Casa")
        self.lazer = self.criar_categoria(self.usuario_id, "Lazer")

    def categorias(self, serie_id):
        return [linha[4] for linha in self.ocorrencias(serie_id)]

    def test_ct103_categoria_somente_este_mes(self):
        serie_id = self.criar_serie(categoria_id=self.casa)
        id_mar = self.id_por_data(serie_id, "2027-03-10")

        db.editar_conta_ocorrencia(id_mar, categoria_id=self.lazer)

        self.assertEqual(self.categorias(serie_id),
                         [self.casa, self.casa, self.lazer, self.casa, self.casa, self.casa])
        self.assertEqual(self.serie(serie_id)["categoria_id"], self.casa)

    def test_ct104_categoria_este_mes_em_diante_com_sob_demanda(self):
        serie_id = self.criar_serie(categoria_id=self.casa, data_termino=None)
        id_mar = self.id_por_data(serie_id, "2027-03-10")

        self.assertTrue(db.editar_conta_serie(id_mar, categoria_id=self.lazer))

        categorias = self.categorias(serie_id)
        self.assertEqual(categorias[:2], [self.casa, self.casa])
        self.assertEqual(set(categorias[2:]), {self.lazer})
        self.assertEqual(self.serie(serie_id)["categoria_id"], self.lazer)
        for conta_id in db.gerar_ocorrencias_sob_demanda(serie_id, "2028-06"):
            self.assertEqual(self.conta(conta_id)["categoria_id"], self.lazer)

    def test_remover_categoria_este_mes_em_diante_com_sob_demanda(self):
        serie_id = self.criar_serie(categoria_id=self.casa, data_termino=None)
        id_mar = self.id_por_data(serie_id, "2027-03-10")

        self.assertTrue(db.editar_conta_serie(id_mar, remover_categoria=True))

        self.assertEqual(set(self.categorias(serie_id)[2:]), {None})
        self.assertIsNone(self.serie(serie_id)["categoria_id"])
        for conta_id in db.gerar_ocorrencias_sob_demanda(serie_id, "2028-06"):
            self.assertIsNone(self.conta(conta_id)["categoria_id"])


class TestVariosCamposNoMesmoEscopo(BaseDescricao):
    """CT107: um único escopo aplicado a nome, valor, categoria e descrição."""

    def test_combinacao_este_mes_em_diante(self):
        self.definir_hoje(date(2027, 4, 15))
        casa = self.criar_categoria(self.usuario_id, "Casa")
        lazer = self.criar_categoria(self.usuario_id, "Lazer")
        serie_id = self.criar_serie(categoria_id=casa, descricao="Antiga", data_termino=None)
        id_jan = self.id_por_data(serie_id, "2027-01-10")
        id_fev = self.id_por_data(serie_id, "2027-02-10")
        id_mar = self.id_por_data(serie_id, "2027-03-10")
        id_mai = self.id_por_data(serie_id, "2027-05-10")
        db.marcar_conta_como_paga(id_mar, data_pagamento="2027-03-09")
        db.marcar_conta_como_paga(id_mai, data_pagamento="2027-04-10")
        db.editar_conta_ocorrencia(id_mai, valor=999.0)
        antes_jan = self.conta(id_jan), self.descricao(id_jan)

        self.assertTrue(db.editar_conta_serie(
            id_fev, nome="Escola nova", valor=800.0, categoria_id=lazer, descricao="Nova",
        ))

        self.assertEqual((self.conta(id_jan), self.descricao(id_jan)), antes_jan)
        for conta_id in (id_fev, id_mar, id_mai):
            conta = self.conta(conta_id)
            self.assertEqual((conta["nome"], conta["valor"], conta["categoria_id"]),
                             ("Escola nova", 800.0, lazer))
            self.assertEqual(self.descricao(conta_id), "Nova")
        # Status e data de pagamento pertencem à ocorrência (5.9).
        self.assertEqual((self.conta(id_mar)["status"], self.conta(id_mar)["data_pagamento"]),
                         ("pago", "2027-03-09"))
        self.assertEqual((self.conta(id_mai)["status"], self.conta(id_mai)["data_pagamento"]),
                         ("pago", "2027-04-10"))
        self.assertEqual(self.conta(id_fev)["status"], "pendente")
        serie = self.serie(serie_id)
        self.assertEqual((serie["nome"], serie["valor"], serie["categoria_id"]), ("Escola nova", 800.0, lazer))
        self.assertEqual(self.descricao_modelo(serie_id), "Nova")
        # Âncora e datas intactas: a data não foi alterada.
        self.assertEqual((serie["dia_ancora"], serie["data_inicio"]), (10, "2027-01-10"))
        self.assertEqual(self.datas(serie_id)[:4], ["2027-01-10", "2027-02-10", "2027-03-10", "2027-04-10"])

    def test_combinacao_somente_este_mes(self):
        casa = self.criar_categoria(self.usuario_id, "Casa")
        serie_id = self.criar_serie(descricao="Antiga")
        id_fev = self.id_por_data(serie_id, "2027-02-10")
        antes_modelo = (self.serie(serie_id), self.descricao_modelo(serie_id))

        db.editar_conta_ocorrencia(id_fev, nome="Só fev", valor=1.0, categoria_id=casa, descricao="Nova")

        self.assertEqual(self.descricoes(serie_id), ["Antiga", "Nova", "Antiga", "Antiga", "Antiga", "Antiga"])
        self.assertEqual([o[2] for o in self.ocorrencias(serie_id)].count("Só fev"), 1)
        self.assertEqual((self.serie(serie_id), self.descricao_modelo(serie_id)), antes_modelo)


class TestAncoraPreservada(BaseDescricao):
    def test_ancora_31_descricao_e_categoria_em_fevereiro(self):
        casa = self.criar_categoria(self.usuario_id, "Casa")
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Aluguel", 1000.0, "2027-01-31", "mensal",
        )
        id_fev = self.id_por_data(serie_id, "2027-02-28")

        # Como a tela: só os campos alterados; a data não vai.
        campos = main.campos_alterados_edicao(
            "Aluguel", "Aluguel", 1000.0, 1000.0, date(2027, 2, 28), date(2027, 2, 28),
            None, casa, None, "Reajuste em março",
        )
        self.assertNotIn("data_vencimento", campos)
        self.assertTrue(db.editar_conta_serie(id_fev, **campos))

        serie = self.serie(serie_id)
        self.assertEqual((serie["dia_ancora"], serie["data_inicio"]), (31, "2027-01-31"))
        db.gerar_ocorrencias_sob_demanda(serie_id, "2028-04")
        self.assertEqual(self.datas(serie_id)[-4:], ["2028-01-31", "2028-02-29", "2028-03-31", "2028-04-30"])
        ultima = self.id_por_data(serie_id, "2028-04-30")
        self.assertEqual((self.conta(ultima)["categoria_id"], self.descricao(ultima)), (casa, "Reajuste em março"))

    def test_anual_29_fevereiro_so_descricao(self):
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "IPVA", 500.0, "2028-02-29", "anual", data_termino="2033-12",
        )
        id_2029 = self.id_por_data(serie_id, "2029-02-28")
        self.assertTrue(db.editar_conta_serie(id_2029, descricao="Placa ABC"))
        self.assertEqual(
            self.datas(serie_id),
            ["2028-02-29", "2029-02-28", "2030-02-28", "2031-02-28", "2032-02-29", "2033-02-28"],
        )
        self.assertEqual((self.serie(serie_id)["dia_ancora"], self.serie(serie_id)["mes_ancora"]), (29, 2))


class TestInterfaceDescricao(unittest.TestCase):
    ORIGINAL = ("Aluguel", 1000.0, date(2027, 2, 28), 3)

    def campos(self, descricao_original, descricao_nova, categoria=3):
        nome, valor, data, categoria_o = self.ORIGINAL
        return main.campos_alterados_edicao(nome, nome, valor, valor, data, data, categoria_o, categoria,
                                            descricao_original, descricao_nova)

    def test_adicionar_alterar_remover(self):
        self.assertEqual(self.campos(None, "  Nova \n"), {"descricao": "Nova"})
        self.assertEqual(self.campos("A", "B"), {"descricao": "B"})
        self.assertEqual(self.campos("A", "   "), {"remover_descricao": True})
        self.assertEqual(self.campos("A", ""), {"remover_descricao": True})

    def test_sem_mudanca_real_nao_envia(self):
        self.assertEqual(self.campos(None, ""), {})
        self.assertEqual(self.campos("A", "  A  "), {})
        self.assertEqual(self.campos(None, None), {})

    def test_combinada_com_remocao_de_categoria(self):
        self.assertEqual(self.campos("A", None, categoria=None),
                         {"remover_categoria": True, "remover_descricao": True})

    def test_chamada_posicional_antiga_continua_valida(self):
        nome, valor, data, categoria = self.ORIGINAL
        self.assertEqual(main.campos_alterados_edicao(nome, nome, valor, valor, data, data, categoria, categoria), {})

    def mensagem(self, descricao_antiga, descricao_nova, **extras):
        argumentos = dict(nome_antigo="Luz", nome_novo="Luz", valor_antigo=10.0, valor_novo=10.0,
                          data_antiga=date(2027, 1, 1), data_nova=date(2027, 1, 1),
                          descricao_antiga=descricao_antiga, descricao_nova=descricao_nova)
        argumentos.update(extras)
        return main.montar_mensagem_alteracao(**argumentos)

    def test_mensagens_de_descricao(self):
        self.assertEqual(self.mensagem(None, "x"), "Você adicionou uma descrição.")
        self.assertEqual(self.mensagem("x", "y"), "Você alterou a descrição.")
        self.assertEqual(self.mensagem("x", "  "), "Você removeu a descrição.")
        self.assertIsNone(self.mensagem("x", " x "))

    def test_mensagem_ct107(self):
        self.assertEqual(
            self.mensagem("x", "y", nome_novo="Energia", valor_novo=12.5,
                          categoria_nome_antiga="Casa", categoria_nome_nova="Lazer"),
            "Você alterou o nome de 'Luz' para 'Energia', o valor de R$ 10,00 para R$ 12,50, "
            "a categoria de 'Casa' para 'Lazer' e a descrição.",
        )

    def test_mensagem_remove_categoria_e_adiciona_descricao(self):
        self.assertEqual(
            self.mensagem(None, "x", categoria_nome_antiga="Casa", categoria_nome_nova=None),
            "Você removeu a categoria 'Casa'. Você adicionou uma descrição.",
        )


if __name__ == "__main__":
    unittest.main()
