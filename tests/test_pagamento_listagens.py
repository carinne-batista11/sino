"""
Regressão v5.0 — pagamento e data efetiva (RF06/RF24/5.9/5.10), cálculo de
status atrasado (RF13), contas atrasadas de qualquer mês (RF25), próximos 7
dias (RF17), listagem do mês (RF05) e posição na série (RF26).
"""

import unittest
from datetime import date

from apoio_banco import TesteComBancoTemporario, db


class TestPagamento(TesteComBancoTemporario):
    HOJE = date(2026, 9, 15)

    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()
        self.serie_id, self.ids = db.criar_serie_recorrente(
            self.usuario_id, "Internet", 100.0, "2026-09-10", "mensal", data_termino="2026-12",
        )

    def test_marcar_paga_sem_data_usa_hoje(self):
        self.assertTrue(db.marcar_conta_como_paga(self.ids[0]))
        conta = self.conta(self.ids[0])
        self.assertEqual((conta["status"], conta["data_pagamento"]), ("pago", "2026-09-15"))

    def test_marcar_paga_com_data_passada(self):
        self.assertTrue(db.marcar_conta_como_paga(self.ids[0], "2026-09-01"))
        self.assertEqual(self.conta(self.ids[0])["data_pagamento"], "2026-09-01")

    def test_rejeita_data_de_pagamento_futura(self):
        self.assertFalse(db.marcar_conta_como_paga(self.ids[0], "2026-09-16"))
        conta = self.conta(self.ids[0])
        self.assertEqual((conta["status"], conta["data_pagamento"]), ("pendente", None))

    def test_status_independente_por_ocorrencia(self):
        db.marcar_conta_como_paga(self.ids[1])
        self.assertEqual([self.conta(i)["status"] for i in self.ids],
                         ["pendente", "pago", "pendente", "pendente"])

    def test_voltar_para_pendente_remove_data(self):
        db.marcar_conta_como_paga(self.ids[0], "2026-09-01")
        db.marcar_conta_como_pendente(self.ids[0])
        conta = self.conta(self.ids[0])
        self.assertEqual((conta["status"], conta["data_pagamento"]), ("pendente", None))

    def test_editar_data_de_pagamento(self):
        db.marcar_conta_como_paga(self.ids[0], "2026-09-01")
        self.assertTrue(db.editar_data_pagamento(self.ids[0], "2026-09-05"))
        self.assertFalse(db.editar_data_pagamento(self.ids[0], "2026-10-01"))
        conta = self.conta(self.ids[0])
        self.assertEqual((conta["data_pagamento"], conta["data_vencimento"]), ("2026-09-05", "2026-09-10"))


class TestListagens(TesteComBancoTemporario):
    HOJE = date(2026, 9, 15)

    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()
        self.outro_usuario = self.criar_usuario(email="outro@sino.com")
        self.agosto_atrasada = db.criar_conta_unica(self.usuario_id, "Multa", 50.0, "2026-08-20")
        self.setembro_atrasada = db.criar_conta_unica(self.usuario_id, "Luz", 120.0, "2026-09-14")
        self.setembro_paga = db.criar_conta_unica(self.usuario_id, "Água", 80.0, "2026-09-05")
        self.hoje_pendente = db.criar_conta_unica(self.usuario_id, "Gás", 60.0, "2026-09-15")
        self.daqui_7_dias = db.criar_conta_unica(self.usuario_id, "Escola", 700.0, "2026-09-22")
        self.daqui_8_dias = db.criar_conta_unica(self.usuario_id, "Clube", 90.0, "2026-09-23")
        db.marcar_conta_como_paga(self.setembro_paga, "2026-09-05")
        db.criar_conta_unica(self.outro_usuario, "Alheia", 1.0, "2026-09-01")

    def test_status_calculado_na_listagem_do_mes(self):
        contas = {c["id"]: c for c in db.listar_contas(self.usuario_id, "2026-09")}
        self.assertEqual(set(contas), {self.setembro_atrasada, self.setembro_paga, self.hoje_pendente,
                                       self.daqui_7_dias, self.daqui_8_dias})
        self.assertEqual(contas[self.setembro_atrasada]["status"], "atrasado")
        self.assertEqual(contas[self.setembro_paga]["status"], "pago")
        self.assertEqual(contas[self.hoje_pendente]["status"], "pendente")
        self.assertEqual(self.conta(self.setembro_atrasada)["status"], "pendente")

    def test_listagem_ordenada_e_isolada_por_usuario(self):
        datas = [c["data_vencimento"] for c in db.listar_contas(self.usuario_id)]
        self.assertEqual(datas, sorted(datas))
        self.assertEqual(len(datas), 6)

    def test_paga_nunca_aparece_como_atrasada(self):
        atrasadas = {c["id"] for c in db.listar_contas_atrasadas(self.usuario_id)}
        self.assertEqual(atrasadas, {self.agosto_atrasada, self.setembro_atrasada})
        db.marcar_conta_como_paga(self.agosto_atrasada)
        atrasadas = {c["id"] for c in db.listar_contas_atrasadas(self.usuario_id)}
        self.assertEqual(atrasadas, {self.setembro_atrasada})

    def test_atrasadas_de_qualquer_mes(self):
        atrasadas = db.listar_contas_atrasadas(self.usuario_id)
        self.assertEqual([c["data_vencimento"] for c in atrasadas], ["2026-08-20", "2026-09-14"])
        self.assertTrue(all(c["status"] == "atrasado" for c in atrasadas))

    def test_proximos_7_dias(self):
        proximas = {c["id"] for c in db.listar_contas_proximas(self.usuario_id, dias=7)}
        self.assertEqual(proximas, {self.hoje_pendente, self.daqui_7_dias})


class TestParcela(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def test_parcela_com_termino(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "Curso", 200.0, "2026-09-10", "mensal", data_termino="2026-12",
        )
        self.assertEqual(db.obter_parcela(serie_id, ids[1]), (2, 4))

    def test_parcela_sem_termino(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-10", "mensal")
        self.assertEqual(db.obter_parcela(serie_id, ids[2]), (3, None))

    def test_conta_avulsa_sem_parcela(self):
        self.assertIsNone(db.obter_parcela(None, 1))

    def test_info_serie(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "Curso", 200.0, "2026-09-10", "anual", data_termino="2030-12",
        )
        self.assertEqual(db.obter_info_serie(serie_id),
                         {"frequencia": "anual", "data_termino": "2030-12", "ativa": True})
        self.assertTrue(db.serie_esta_ativa(serie_id))
        db.encerrar_recorrencia(ids[0])
        self.assertFalse(db.serie_esta_ativa(serie_id))
        self.assertIsNone(db.obter_info_serie(None))


if __name__ == "__main__":
    unittest.main()
