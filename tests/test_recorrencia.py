"""
Regressão v5.0 — recorrência: criação de séries (5.2/5.3), geração sob
demanda (5.20), transformar em recorrente (RF28/5.4) e alterar frequência
(RF27/5.5).
"""

import unittest

from apoio_banco import TesteComBancoTemporario, db


class TestCriarSerie(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def test_conta_unica_nao_cria_serie(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 120.0, "2026-09-20")
        conta = self.conta(conta_id)
        self.assertIsNone(conta["serie_id"])
        self.assertEqual(conta["status"], "pendente")
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM series_recorrencia")[0][0], 0)

    def test_mensal_ancora_31_sem_arrasto(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "Aluguel", 1000.0, "2027-01-31", "mensal", data_termino="2027-06",
        )
        self.assertEqual(
            self.datas(serie_id),
            ["2027-01-31", "2027-02-28", "2027-03-31", "2027-04-30", "2027-05-31", "2027-06-30"],
        )
        self.assertEqual(len(ids), 6)
        serie = self.serie(serie_id)
        self.assertEqual(serie["dia_ancora"], 31)
        self.assertIsNone(serie["mes_ancora"])
        self.assertEqual(serie["horizonte_gerado_ate"], "2027-06-30")
        self.assertEqual(serie["ativa"], 1)

    def test_mensal_ancora_31_em_ano_bissexto(self):
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Aluguel", 1000.0, "2028-01-31", "mensal", data_termino="2028-03",
        )
        self.assertEqual(self.datas(serie_id), ["2028-01-31", "2028-02-29", "2028-03-31"])

    def test_anual_ancora_29_fevereiro_sem_arrasto(self):
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "IPVA", 500.0, "2028-02-29", "anual", data_termino="2032-12",
        )
        self.assertEqual(
            self.datas(serie_id),
            ["2028-02-29", "2029-02-28", "2030-02-28", "2031-02-28", "2032-02-29"],
        )
        serie = self.serie(serie_id)
        self.assertEqual((serie["dia_ancora"], serie["mes_ancora"]), (29, 2))

    def test_mensal_sem_termino_gera_12_meses_seguintes(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "Internet", 100.0, "2026-09-15", "mensal",
        )
        datas = self.datas(serie_id)
        self.assertEqual(len(ids), 13)
        self.assertEqual(datas[0], "2026-09-15")
        self.assertEqual(datas[-1], "2027-09-15")
        serie = self.serie(serie_id)
        self.assertIsNone(serie["data_termino"])
        self.assertEqual(serie["horizonte_gerado_ate"], "2027-09-15")

    def test_anual_sem_termino_gera_proxima_ocorrencia(self):
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Seguro", 900.0, "2026-09-15", "anual",
        )
        self.assertEqual(self.datas(serie_id), ["2026-09-15", "2027-09-15"])

    def test_termino_longo_gera_tudo_sem_limite_de_12_meses(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "Financiamento", 300.0, "2026-01-10", "mensal", data_termino="2028-12",
        )
        self.assertEqual(len(ids), 36)
        self.assertEqual(self.datas(serie_id)[-1], "2028-12-10")

    def test_serie_copia_categoria_para_ocorrencias(self):
        categoria_id = self.criar_categoria(self.usuario_id)
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Água", 80.0, "2026-09-10", "mensal", data_termino="2026-11",
            categoria_id=categoria_id,
        )
        self.assertEqual({o[4] for o in self.ocorrencias(serie_id)}, {categoria_id})
        self.assertEqual(self.serie(serie_id)["categoria_id"], categoria_id)

    def test_frequencia_invalida(self):
        with self.assertRaises(ValueError):
            db.criar_serie_recorrente(self.usuario_id, "X", 1.0, "2026-09-10", "semanal")
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas")[0][0], 0)


class TestGeracaoSobDemanda(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def test_gera_meses_faltantes_e_avanca_horizonte(self):
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-15", "mensal")
        novos = db.gerar_ocorrencias_sob_demanda(serie_id, "2028-03")
        self.assertEqual(len(novos), 6)
        self.assertEqual(self.datas(serie_id)[-6:], [
            "2027-10-15", "2027-11-15", "2027-12-15", "2028-01-15", "2028-02-15", "2028-03-15",
        ])
        self.assertEqual(self.serie(serie_id)["horizonte_gerado_ate"], "2028-03-15")

    def test_idempotente_sem_duplicacao(self):
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-15", "mensal")
        db.gerar_ocorrencias_sob_demanda(serie_id, "2028-03")
        total = len(self.datas(serie_id))
        self.assertEqual(db.gerar_ocorrencias_sob_demanda(serie_id, "2028-03"), [])
        self.assertEqual(db.gerar_ocorrencias_sob_demanda(serie_id, "2027-01"), [])
        self.assertEqual(len(self.datas(serie_id)), total)
        self.assertEqual(len(set(self.datas(serie_id))), total)

    def test_nao_duplica_data_ja_existente(self):
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-15", "mensal")
        self.executar(
            "INSERT INTO contas (usuario_id, serie_id, nome, valor, data_vencimento) VALUES (?, ?, ?, ?, ?)",
            (self.usuario_id, serie_id, "Internet", 100.0, "2027-10-15"),
        )
        novos = db.gerar_ocorrencias_sob_demanda(serie_id, "2027-11")
        self.assertEqual(len(novos), 1)
        self.assertEqual(self.datas(serie_id).count("2027-10-15"), 1)
        self.assertEqual(self.datas(serie_id)[-1], "2027-11-15")

    def test_sob_demanda_mantem_ancora_31(self):
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 1000.0, "2026-01-31", "mensal")
        db.gerar_ocorrencias_sob_demanda(serie_id, "2027-04")
        self.assertEqual(self.datas(serie_id)[-3:], ["2027-02-28", "2027-03-31", "2027-04-30"])

    def test_sob_demanda_usa_modelo_da_serie(self):
        categoria_id = self.criar_categoria(self.usuario_id)
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Internet", 100.0, "2026-09-15", "mensal", categoria_id=categoria_id,
        )
        novo_id = db.gerar_ocorrencias_sob_demanda(serie_id, "2027-10")[0]
        conta = self.conta(novo_id)
        self.assertEqual((conta["nome"], conta["valor"], conta["categoria_id"], conta["status"]),
                         ("Internet", 100.0, categoria_id, "pendente"))

    def test_serie_com_termino_nao_gera(self):
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Curso", 200.0, "2026-09-15", "mensal", data_termino="2026-12",
        )
        self.assertEqual(db.gerar_ocorrencias_sob_demanda(serie_id, "2027-06"), [])
        self.assertEqual(self.datas(serie_id)[-1], "2026-12-15")

    def test_serie_inativa_nao_gera(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-15", "mensal")
        db.encerrar_recorrencia(ids[0])
        self.assertEqual(db.gerar_ocorrencias_sob_demanda(serie_id, "2028-12"), [])

    def test_serie_inexistente(self):
        with self.assertRaises(ValueError):
            db.gerar_ocorrencias_sob_demanda(999, "2027-01")


class TestTransformarEmRecorrente(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def test_avulsa_vira_ancora_da_nova_serie(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Academia", 90.0, "2026-03-31")
        db.marcar_conta_como_paga(conta_id, "2026-03-30")
        serie_id, novos = db.transformar_em_recorrente(conta_id, "mensal", data_termino="2026-06")

        self.assertEqual(self.datas(serie_id), ["2026-03-31", "2026-04-30", "2026-05-31", "2026-06-30"])
        self.assertNotIn(conta_id, novos)
        ancora = self.conta(conta_id)
        self.assertEqual(ancora["serie_id"], serie_id)
        self.assertEqual((ancora["status"], ancora["data_pagamento"]), ("pago", "2026-03-30"))
        self.assertEqual({self.conta(i)["status"] for i in novos}, {"pendente"})
        self.assertEqual(self.serie(serie_id)["dia_ancora"], 31)

    def test_sem_termino_gera_horizonte_inicial(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Academia", 90.0, "2026-09-15")
        serie_id, novos = db.transformar_em_recorrente(conta_id, "mensal")
        self.assertEqual(len(novos), 12)
        self.assertIsNone(self.serie(serie_id)["data_termino"])

    def test_anual(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "IPVA", 500.0, "2028-02-29")
        serie_id, _ = db.transformar_em_recorrente(conta_id, "anual", data_termino="2030-12")
        self.assertEqual(self.datas(serie_id), ["2028-02-29", "2029-02-28", "2030-02-28"])

    def test_rejeita_conta_de_serie_ativa(self):
        _, ids = db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-15", "mensal")
        with self.assertRaises(ValueError):
            db.transformar_em_recorrente(ids[0], "mensal")

    def test_aceita_conta_de_serie_encerrada_e_preserva_serie_antiga(self):
        serie_antiga, ids = db.criar_serie_recorrente(
            self.usuario_id, "Internet", 100.0, "2026-09-15", "mensal", data_termino="2026-12",
        )
        db.encerrar_recorrencia(ids[0])
        datas_antigas = self.datas(serie_antiga)

        serie_nova, _ = db.transformar_em_recorrente(ids[0], "anual", data_termino="2027-12")
        self.assertNotEqual(serie_nova, serie_antiga)
        self.assertEqual(self.conta(ids[0])["serie_id"], serie_nova)
        self.assertIsNotNone(self.serie(serie_antiga))
        self.assertEqual(self.serie(serie_antiga)["ativa"], 0)
        self.assertEqual(self.datas(serie_antiga), [d for d in datas_antigas if d != "2026-09-15"])

    def test_frequencia_invalida(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Academia", 90.0, "2026-09-15")
        with self.assertRaises(ValueError):
            db.transformar_em_recorrente(conta_id, "diaria")
        with self.assertRaises(ValueError):
            db.transformar_em_recorrente(999, "mensal")


class TestAlterarFrequencia(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()
        self.serie_id, self.ids = db.criar_serie_recorrente(
            self.usuario_id, "Plano", 50.0, "2026-01-10", "mensal", data_termino="2026-12",
        )
        self.id_marco = self.id_por_data(self.serie_id, "2026-03-10")
        self.id_abril = self.id_por_data(self.serie_id, "2026-04-10")
        self.id_junho = self.id_por_data(self.serie_id, "2026-06-10")
        db.marcar_conta_como_paga(self.id_marco, "2026-03-09")
        db.editar_conta_ocorrencia(self.id_junho, valor=77.0)

    def test_mensal_para_anual_a_partir_da_selecionada(self):
        resultado = db.alterar_frequencia_serie(self.id_abril, "anual", data_termino="2028-12")

        self.assertEqual(resultado["ocorrencias_preservadas"], [self.id_junho])
        self.assertEqual(
            self.datas(self.serie_id),
            ["2026-01-10", "2026-02-10", "2026-03-10", "2026-04-10", "2026-06-10",
             "2027-04-10", "2028-04-10"],
        )
        marco = self.conta(self.id_marco)
        self.assertEqual((marco["status"], marco["data_pagamento"]), ("pago", "2026-03-09"))
        self.assertEqual(self.conta(self.id_junho)["valor"], 77.0)

        serie = self.serie(self.serie_id)
        self.assertEqual(serie["frequencia"], "anual")
        self.assertEqual((serie["dia_ancora"], serie["mes_ancora"]), (10, 4))
        self.assertEqual(serie["data_inicio"], "2026-04-10")
        self.assertEqual(serie["data_termino"], "2028-12")
        self.assertEqual(serie["horizonte_gerado_ate"], "2028-04-10")

    def test_sem_termino_torna_serie_aberta(self):
        db.alterar_frequencia_serie(self.id_abril, "anual")
        serie = self.serie(self.serie_id)
        self.assertIsNone(serie["data_termino"])
        self.assertIn("2027-04-10", self.datas(self.serie_id))

    def test_rejeicoes(self):
        conta_avulsa = db.criar_conta_unica(self.usuario_id, "X", 1.0, "2026-05-05")
        with self.assertRaises(ValueError):
            db.alterar_frequencia_serie(conta_avulsa, "anual")
        with self.assertRaises(ValueError):
            db.alterar_frequencia_serie(self.id_abril, "semanal")
        db.encerrar_recorrencia(self.id_abril)
        datas_antes = self.datas(self.serie_id)
        with self.assertRaises(ValueError):
            db.alterar_frequencia_serie(self.id_abril, "anual")
        self.assertEqual(self.datas(self.serie_id), datas_antes)


if __name__ == "__main__":
    unittest.main()
