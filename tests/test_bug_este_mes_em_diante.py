"""
Bug da v5.0 encontrado no diagnóstico da v6.0 — "Este mês em diante".

A tela de edição (backend/main.py, salvar_edicao) sempre enviava a
`editar_conta_serie` TODOS os campos (nome, valor, vencimento, categoria),
inclusive os que o usuário não alterou. Como consequência:

  * a data de vencimento repetida redefinia a âncora da série para o dia
    da ocorrência selecionada (ex.: 28/02 numa série de âncora 31),
    arrastando todas as ocorrências seguintes (viola 5.2, "sem arrasto");
  * um campo não alterado (ex.: valor) sobrescrevia silenciosamente o valor
    diferente de ocorrências futuras editadas individualmente.

Estes testes chamam `editar_conta_serie` exatamente como a tela chamava —
campos não alterados repetindo o valor atual da ocorrência selecionada — e
falhavam antes da correção. A regra corrigida: só os campos realmente
modificados em relação à ocorrência selecionada são propagados, e a âncora
só muda quando a data de vencimento muda de verdade.
"""

import unittest

from apoio_banco import TesteComBancoTemporario, db


class TestEsteMesEmDianteSemArrasto(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def editar_como_a_tela(self, conta_id, **alteracoes):
        """Chama editar_conta_serie repetindo os valores atuais dos campos não alterados."""
        atual = self.conta(conta_id)
        campos = {
            "nome": atual["nome"],
            "valor": atual["valor"],
            "data_vencimento": atual["data_vencimento"],
            "categoria_id": atual["categoria_id"],
            "remover_categoria": atual["categoria_id"] is None,
        }
        campos.update(alteracoes)
        return db.editar_conta_serie(conta_id, **campos)

    def test_mensal_ancora_31_alterar_so_valor_em_fevereiro(self):
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Aluguel", 1000.0, "2027-01-31", "mensal", data_termino="2027-06",
        )
        id_fevereiro = self.id_por_data(serie_id, "2027-02-28")

        self.assertTrue(self.editar_como_a_tela(id_fevereiro, valor=1100.0))

        self.assertEqual(
            self.datas(serie_id),
            ["2027-01-31", "2027-02-28", "2027-03-31", "2027-04-30", "2027-05-31", "2027-06-30"],
        )
        serie = self.serie(serie_id)
        self.assertEqual(serie["dia_ancora"], 31)
        self.assertEqual(serie["data_inicio"], "2027-01-31")
        self.assertEqual([o[3] for o in self.ocorrencias(serie_id)],
                         [1000.0, 1100.0, 1100.0, 1100.0, 1100.0, 1100.0])

    def test_mensal_ancora_31_meses_gerados_depois_seguem_ancora_original(self):
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 1000.0, "2027-01-31", "mensal")
        id_fevereiro = self.id_por_data(serie_id, "2027-02-28")

        self.editar_como_a_tela(id_fevereiro, valor=1100.0)
        db.gerar_ocorrencias_sob_demanda(serie_id, "2028-04")

        self.assertEqual(self.datas(serie_id)[-4:], ["2028-01-31", "2028-02-29", "2028-03-31", "2028-04-30"])

    def test_anual_ancora_29_fevereiro_alterar_so_nome(self):
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "IPVA", 500.0, "2028-02-29", "anual", data_termino="2033-12",
        )
        id_2029 = self.id_por_data(serie_id, "2029-02-28")

        self.assertTrue(self.editar_como_a_tela(id_2029, nome="IPVA carro"))

        self.assertEqual(
            self.datas(serie_id),
            ["2028-02-29", "2029-02-28", "2030-02-28", "2031-02-28", "2032-02-29", "2033-02-28"],
        )
        serie = self.serie(serie_id)
        self.assertEqual((serie["dia_ancora"], serie["mes_ancora"]), (29, 2))

    def test_data_futura_editada_individualmente_nao_e_recalculada(self):
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Escola", 700.0, "2027-01-10", "mensal", data_termino="2027-06",
        )
        id_maio = self.id_por_data(serie_id, "2027-05-10")
        db.editar_conta_ocorrencia(id_maio, data_vencimento="2027-05-20")
        id_fevereiro = self.id_por_data(serie_id, "2027-02-10")

        self.editar_como_a_tela(id_fevereiro, valor=750.0)

        self.assertEqual(self.conta(id_maio)["data_vencimento"], "2027-05-20")

    def test_alterar_so_categoria_preserva_valor_editado_individualmente(self):
        categoria_casa = self.criar_categoria(self.usuario_id, "Casa")
        categoria_lazer = self.criar_categoria(self.usuario_id, "Lazer")
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Clube", 200.0, "2027-01-10", "mensal", data_termino="2027-06",
            categoria_id=categoria_casa,
        )
        id_maio = self.id_por_data(serie_id, "2027-05-10")
        db.editar_conta_ocorrencia(id_maio, valor=999.0, nome="Clube (anual)")
        id_fevereiro = self.id_por_data(serie_id, "2027-02-10")

        self.assertTrue(self.editar_como_a_tela(id_fevereiro, categoria_id=categoria_lazer,
                                                remover_categoria=False))

        maio = self.conta(id_maio)
        self.assertEqual((maio["valor"], maio["nome"]), (999.0, "Clube (anual)"))
        self.assertEqual(maio["categoria_id"], categoria_lazer)
        self.assertEqual(self.conta(self.id_por_data(serie_id, "2027-01-10"))["categoria_id"], categoria_casa)
        serie = self.serie(serie_id)
        self.assertEqual((serie["categoria_id"], serie["valor"], serie["nome"]), (categoria_lazer, 200.0, "Clube"))

    def test_contraprova_valor_alterado_propaga_inclusive_para_editadas(self):
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Clube", 200.0, "2027-01-10", "mensal", data_termino="2027-06",
        )
        id_maio = self.id_por_data(serie_id, "2027-05-10")
        db.editar_conta_ocorrencia(id_maio, valor=999.0)
        id_fevereiro = self.id_por_data(serie_id, "2027-02-10")

        self.assertTrue(self.editar_como_a_tela(id_fevereiro, valor=250.0))

        self.assertEqual(self.conta(id_maio)["valor"], 250.0)
        self.assertEqual(self.conta(self.id_por_data(serie_id, "2027-01-10"))["valor"], 200.0)
        self.assertEqual(self.serie(serie_id)["valor"], 250.0)

    def test_contraprova_data_alterada_de_verdade_redefine_ancora(self):
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Aluguel", 1000.0, "2027-01-31", "mensal", data_termino="2027-06",
        )
        id_fevereiro = self.id_por_data(serie_id, "2027-02-28")

        self.editar_como_a_tela(id_fevereiro, data_vencimento="2027-02-15")

        self.assertEqual(self.datas(serie_id)[1:],
                         ["2027-02-15", "2027-03-15", "2027-04-15", "2027-05-15", "2027-06-15"])
        self.assertEqual(self.serie(serie_id)["dia_ancora"], 15)

    def test_nada_alterado_nao_modifica_nada(self):
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Aluguel", 1000.0, "2027-01-31", "mensal", data_termino="2027-06",
        )
        id_fevereiro = self.id_por_data(serie_id, "2027-02-28")
        antes = (self.ocorrencias(serie_id), self.serie(serie_id))

        self.assertTrue(self.editar_como_a_tela(id_fevereiro))

        self.assertEqual((self.ocorrencias(serie_id), self.serie(serie_id)), antes)


if __name__ == "__main__":
    unittest.main()
