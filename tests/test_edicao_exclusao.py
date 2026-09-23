"""
Regressão v5.0 — edição (RF20/5.6), exclusão (RF08/5.7) e encerramento de
recorrência (RF29/5.8, decisão D7).

O comportamento de "Este mês em diante" quando campos NÃO alterados são
enviados junto (bug corrigido na Etapa 0 da v6.0) está em
test_bug_este_mes_em_diante.py.
"""

import unittest
from datetime import date

from apoio_banco import TesteComBancoTemporario, db


class TestEditarOcorrencia(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()
        self.categoria_id = self.criar_categoria(self.usuario_id)
        self.serie_id, self.ids = db.criar_serie_recorrente(
            self.usuario_id, "Internet", 100.0, "2026-09-10", "mensal", data_termino="2026-12",
            categoria_id=self.categoria_id,
        )

    def test_somente_este_mes_altera_so_a_ocorrencia(self):
        alvo = self.ids[1]
        self.assertTrue(db.editar_conta_ocorrencia(alvo, nome="Internet Fibra", valor=130.0))
        conta = self.conta(alvo)
        self.assertEqual((conta["nome"], conta["valor"], conta["editado_individualmente"]),
                         ("Internet Fibra", 130.0, 1))
        for outro in (self.ids[0], self.ids[2], self.ids[3]):
            self.assertEqual((self.conta(outro)["nome"], self.conta(outro)["valor"]), ("Internet", 100.0))
        serie = self.serie(self.serie_id)
        self.assertEqual((serie["nome"], serie["valor"]), ("Internet", 100.0))

    def test_none_significa_nao_alterar(self):
        alvo = self.ids[0]
        db.editar_conta_ocorrencia(alvo, valor=150.0)
        conta = self.conta(alvo)
        self.assertEqual(conta["nome"], "Internet")
        self.assertEqual(conta["categoria_id"], self.categoria_id)
        self.assertEqual(conta["data_vencimento"], "2026-09-10")

    def test_remover_categoria(self):
        db.editar_conta_ocorrencia(self.ids[0], remover_categoria=True)
        self.assertIsNone(self.conta(self.ids[0])["categoria_id"])
        self.assertEqual(self.conta(self.ids[1])["categoria_id"], self.categoria_id)

    def test_sem_campos_nao_marca_editado(self):
        self.assertTrue(db.editar_conta_ocorrencia(self.ids[0]))
        self.assertEqual(self.conta(self.ids[0])["editado_individualmente"], 0)

    def test_conta_avulsa_nao_marca_editado(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 120.0, "2026-09-20")
        db.editar_conta_ocorrencia(conta_id, valor=140.0, data_vencimento="2026-09-25")
        conta = self.conta(conta_id)
        self.assertEqual((conta["valor"], conta["data_vencimento"], conta["editado_individualmente"]),
                         (140.0, "2026-09-25", 0))

    def test_conta_inexistente(self):
        self.assertFalse(db.editar_conta_ocorrencia(999, valor=1.0))


class TestEditarSerie(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()
        self.categoria_id = self.criar_categoria(self.usuario_id)
        self.serie_id, self.ids = db.criar_serie_recorrente(
            self.usuario_id, "Internet", 100.0, "2026-09-10", "mensal", data_termino="2027-02",
            categoria_id=self.categoria_id,
        )

    def test_este_mes_em_diante_altera_selecionada_futuras_e_modelo(self):
        db.marcar_conta_como_paga(self.ids[2], "2026-09-01")
        self.assertTrue(db.editar_conta_serie(self.ids[1], nome="Internet Fibra", valor=130.0))

        self.assertEqual(self.conta(self.ids[0])["valor"], 100.0)
        for conta_id in self.ids[1:]:
            conta = self.conta(conta_id)
            self.assertEqual((conta["nome"], conta["valor"]), ("Internet Fibra", 130.0))
        pago = self.conta(self.ids[2])
        self.assertEqual((pago["status"], pago["data_pagamento"]), ("pago", "2026-09-01"))
        serie = self.serie(self.serie_id)
        self.assertEqual((serie["nome"], serie["valor"]), ("Internet Fibra", 130.0))

    def test_alterar_data_redefine_ancora(self):
        db.editar_conta_serie(self.ids[1], data_vencimento="2026-10-20")
        self.assertEqual(
            self.datas(self.serie_id),
            ["2026-09-10", "2026-10-20", "2026-11-20", "2026-12-20", "2027-01-20", "2027-02-20"],
        )
        serie = self.serie(self.serie_id)
        self.assertEqual((serie["dia_ancora"], serie["data_inicio"]), (20, "2026-10-20"))
        self.assertEqual(serie["horizonte_gerado_ate"], "2027-02-20")

    def test_nova_data_alem_do_termino_e_rejeitada(self):
        datas_antes = self.datas(self.serie_id)
        self.assertFalse(db.editar_conta_serie(self.ids[1], valor=999.0, data_vencimento="2026-11-10"))
        self.assertEqual(self.datas(self.serie_id), datas_antes)
        self.assertEqual(self.conta(self.ids[1])["valor"], 100.0)

    def test_remover_categoria_vale_para_modelo(self):
        db.editar_conta_serie(self.ids[2], remover_categoria=True)
        self.assertEqual(self.conta(self.ids[1])["categoria_id"], self.categoria_id)
        self.assertIsNone(self.conta(self.ids[2])["categoria_id"])
        self.assertIsNone(self.serie(self.serie_id)["categoria_id"])

    def test_serie_inativa_e_rejeitada(self):
        db.encerrar_recorrencia(self.ids[0])
        self.assertFalse(db.editar_conta_serie(self.ids[0], valor=500.0))
        self.assertEqual(self.conta(self.ids[0])["valor"], 100.0)

    def test_conta_avulsa_edita_direto(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 120.0, "2026-09-20")
        self.assertTrue(db.editar_conta_serie(conta_id, valor=140.0))
        self.assertEqual(self.conta(conta_id)["valor"], 140.0)

    def test_modelo_alterado_vale_para_geracao_sob_demanda(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Streaming", 40.0, "2026-09-05", "mensal")
        db.editar_conta_serie(ids[3], nome="Streaming Plus", valor=55.0, remover_categoria=True)
        novo = db.gerar_ocorrencias_sob_demanda(serie_id, "2027-10")[0]
        conta = self.conta(novo)
        self.assertEqual((conta["nome"], conta["valor"], conta["categoria_id"]),
                         ("Streaming Plus", 55.0, None))


class TestExcluir(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def test_excluir_conta_avulsa(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 120.0, "2026-09-20")
        self.assertTrue(db.excluir_conta(conta_id))
        self.assertIsNone(self.conta(conta_id))
        self.assertFalse(db.excluir_conta(conta_id))

    def test_somente_este_mes_inclusive_primeira_ocorrencia(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "Curso", 200.0, "2026-09-10", "mensal", data_termino="2026-12",
        )
        self.assertTrue(db.excluir_conta(ids[0]))
        self.assertEqual(self.datas(serie_id), ["2026-10-10", "2026-11-10", "2026-12-10"])
        db.excluir_conta(ids[3])
        self.assertEqual(self.serie(serie_id)["horizonte_gerado_ate"], "2026-11-10")

    def test_excluir_ultima_ocorrencia_remove_serie(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "Curso", 200.0, "2026-09-10", "mensal", data_termino="2026-09",
        )
        db.excluir_conta(ids[0])
        self.assertIsNone(self.serie(serie_id))

    def test_este_mes_em_diante(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "Curso", 200.0, "2026-09-10", "mensal", data_termino="2026-12",
        )
        db.marcar_conta_como_paga(ids[2], "2026-09-01")
        self.assertTrue(db.excluir_conta_serie(ids[1]))
        self.assertEqual(self.datas(serie_id), ["2026-09-10"])
        serie = self.serie(serie_id)
        self.assertEqual(serie["horizonte_gerado_ate"], "2026-09-10")
        self.assertEqual(serie["data_termino"], "2026-12")

    def test_este_mes_em_diante_a_partir_da_primeira_remove_serie(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "Curso", 200.0, "2026-09-10", "mensal", data_termino="2026-12",
        )
        db.excluir_conta_serie(ids[0])
        self.assertEqual(self.datas(serie_id), [])
        self.assertIsNone(self.serie(serie_id))

    def test_este_mes_em_diante_fecha_serie_sem_termino(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-10", "mensal")
        db.excluir_conta_serie(ids[3])
        serie = self.serie(serie_id)
        self.assertEqual(serie["data_termino"], "2026-11")
        self.assertEqual(db.gerar_ocorrencias_sob_demanda(serie_id, "2027-12"), [])


class TestEncerrarRecorrencia(TesteComBancoTemporario):
    HOJE = date(2026, 9, 15)

    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()
        self.serie_id, self.ids = db.criar_serie_recorrente(
            self.usuario_id, "Academia", 90.0, "2026-06-10", "mensal", data_termino="2027-01",
        )

    def test_selecionada_passada_corta_em_hoje(self):
        id_junho = self.id_por_data(self.serie_id, "2026-06-10")
        resultado = db.encerrar_recorrencia(id_junho)
        self.assertEqual(self.datas(self.serie_id),
                         ["2026-06-10", "2026-07-10", "2026-08-10", "2026-09-10"])
        self.assertEqual(resultado["ocorrencias_removidas"], 4)
        serie = self.serie(self.serie_id)
        self.assertEqual((serie["ativa"], serie["horizonte_gerado_ate"]), (0, "2026-09-10"))

    def test_selecionada_futura_e_preservada(self):
        id_novembro = self.id_por_data(self.serie_id, "2026-11-10")
        db.encerrar_recorrencia(id_novembro)
        self.assertEqual(self.datas(self.serie_id)[-1], "2026-11-10")
        self.assertNotIn("2026-12-10", self.datas(self.serie_id))

    def test_protege_futuras_pagas_ou_editadas(self):
        id_outubro = self.id_por_data(self.serie_id, "2026-10-10")
        id_dezembro = self.id_por_data(self.serie_id, "2026-12-10")
        id_janeiro = self.id_por_data(self.serie_id, "2027-01-10")
        db.marcar_conta_como_paga(id_dezembro, "2026-09-14")
        db.editar_conta_ocorrencia(id_janeiro, valor=95.0)

        db.encerrar_recorrencia(id_outubro)
        datas = self.datas(self.serie_id)
        self.assertNotIn("2026-11-10", datas)
        self.assertIn("2026-12-10", datas)
        self.assertIn("2027-01-10", datas)
        self.assertEqual(self.serie(self.serie_id)["horizonte_gerado_ate"], "2027-01-10")

    def test_rejeicoes(self):
        conta_avulsa = db.criar_conta_unica(self.usuario_id, "X", 1.0, "2026-09-20")
        with self.assertRaises(ValueError):
            db.encerrar_recorrencia(conta_avulsa)
        with self.assertRaises(ValueError):
            db.encerrar_recorrencia(999)
        db.encerrar_recorrencia(self.ids[0])
        with self.assertRaises(ValueError):
            db.encerrar_recorrencia(self.ids[0])


if __name__ == "__main__":
    unittest.main()
