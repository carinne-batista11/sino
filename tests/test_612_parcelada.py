"""
Sino 6.12 (experimental), Etapa 6 -- contas Parceladas (camada de dados).

D2 (valor total + quantidade), D3 (diferença de centavos na 1ª parcela), D4 (2 a
36), D13 (só mensal), D10 (registro em `parcelamentos`), D14 (uma transação),
P6 (Única -> Parcelada: a própria conta é a parcela 1, no mesmo mês; valor em
centavos >= quantidade), R1 (Única com qualquer registro de pagamento não é
parcelada) e a regra estrutural (parcelada não muda de tipo). Hoje fixo: 15/09/2026.
"""

import unittest
from unittest import mock

from apoio_banco import TesteComBancoTemporario, db

import pagamentos


class TestDivisao(unittest.TestCase):
    def test_diferenca_de_centavos_na_primeira(self):
        self.assertEqual(db.dividir_em_parcelas(100000, 3), [33334, 33333, 33333])
        self.assertEqual(db.dividir_em_parcelas(1000, 7), [148, 142, 142, 142, 142, 142, 142])
        self.assertEqual(db.dividir_em_parcelas(120000, 12), [10000] * 12)
        self.assertEqual(db.dividir_em_parcelas(2, 2), [1, 1])

    def test_soma_sempre_igual_ao_total(self):
        for total in (1, 2, 99, 100, 101, 999_99, 1_234_567, 3_600_00):
            for quantidade in range(2, 37):
                if total >= quantidade:
                    with self.subTest(total=total, quantidade=quantidade):
                        partes = db.dividir_em_parcelas(total, quantidade)
                        self.assertEqual(sum(partes), total)
                        self.assertEqual(len(partes), quantidade)
                        self.assertTrue(all(p == partes[1] for p in partes[1:]))
                        self.assertLess(partes[0] - partes[1], quantidade)

    def test_previa(self):
        previa = db.previa_parcelamento(1000.0, 3, "2026-01-31")
        self.assertEqual([(p["posicao"], p["vencimento"], p["valor_centavos"]) for p in previa],
                         [(1, "2026-01-31", 33334), (2, "2026-02-28", 33333), (3, "2026-03-31", 33333)])
        self.assertEqual({p["quantidade"] for p in previa}, {3})
        self.assertEqual(previa[0]["valor"], 333.34)

    def test_meses_curtos_e_virada_de_ano(self):
        datas = [p["vencimento"] for p in db.previa_parcelamento(500.0, 5, "2027-10-31")]
        self.assertEqual(datas, ["2027-10-31", "2027-11-30", "2027-12-31", "2028-01-31", "2028-02-29"])
        datas = [p["vencimento"] for p in db.previa_parcelamento(300.0, 3, "2026-12-30")]
        self.assertEqual(datas, ["2026-12-30", "2027-01-30", "2027-02-28"])
        datas = [p["vencimento"] for p in db.previa_parcelamento(300.0, 3, "2028-02-29")]
        self.assertEqual(datas, ["2028-02-29", "2028-03-29", "2028-04-29"])
        self.assertEqual(len(db.previa_parcelamento(3600.0, 36, "2026-09-10")), 36)
        self.assertEqual(db.previa_parcelamento(3600.0, 36, "2026-09-10")[-1]["vencimento"], "2029-08-10")

    def test_recusas(self):
        for valor, quantidade, mensagem in (
            (100.0, 1, db.MENSAGEM_QUANTIDADE_DE_PARCELAS), (100.0, 37, db.MENSAGEM_QUANTIDADE_DE_PARCELAS),
            (100.0, True, db.MENSAGEM_QUANTIDADE_DE_PARCELAS), (100.0, "12", db.MENSAGEM_QUANTIDADE_DE_PARCELAS),
            (100.0, 2.0, db.MENSAGEM_QUANTIDADE_DE_PARCELAS), (0, 2, db.MENSAGEM_VALOR_TOTAL_INVALIDO),
            (-5.0, 2, db.MENSAGEM_VALOR_TOTAL_INVALIDO), (None, 2, db.MENSAGEM_VALOR_TOTAL_INVALIDO),
            (0.01, 2, db.MENSAGEM_VALOR_PEQUENO_PARA_PARCELAS), (0.35, 36, db.MENSAGEM_VALOR_PEQUENO_PARA_PARCELAS),
        ):
            with self.subTest(valor=valor, quantidade=quantidade):
                with self.assertRaisesRegex(db.ParcelamentoRecusadoError, mensagem):
                    db.previa_parcelamento(valor, quantidade, "2026-09-10")
        self.assertEqual(len(db.previa_parcelamento(0.36, 36, "2026-09-10")), 36)  # 1 centavo cada


class BaseParcelada(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def parcelas(self, serie_id):
        return self.consultar("SELECT id, data_vencimento, valor, status, posicao, editado_individualmente "
                              "FROM contas WHERE serie_id = ? ORDER BY posicao", (serie_id,))

    def estado(self):
        return {t: self.consultar(f"SELECT * FROM {t} ORDER BY 1")
                for t in ("contas", "series_recorrencia", "parcelamentos", "pp_pagamentos")}


class TestCriarContaParcelada(BaseParcelada):
    def test_cria_todas_as_parcelas_numa_gravacao(self):
        categoria = self.criar_categoria(self.usuario_id, "Lazer")
        serie_id, ids = db.criar_conta_parcelada(self.usuario_id, "Notebook", 1000.0, 3, "2026-09-30",
                                                 categoria_id=categoria, descricao="  Loja X  ")
        self.assertEqual(len(ids), 3)
        self.assertEqual([(d, v, s, p, e) for _, d, v, s, p, e in self.parcelas(serie_id)],
                         [("2026-09-30", 333.34, "pendente", 1, 0), ("2026-10-30", 333.33, "pendente", 2, 0),
                          ("2026-11-30", 333.33, "pendente", 3, 0)])
        self.assertEqual(self.consultar("SELECT quantidade_original, valor_total_original_centavos FROM parcelamentos "
                                        "WHERE serie_id = ?", (serie_id,)), [(3, 100000)])
        self.assertEqual(self.consultar("SELECT frequencia, data_termino, valor, ativa FROM series_recorrencia "
                                        "WHERE id = ?", (serie_id,)), [("mensal", "2026-11", 333.33, 1)])
        self.assertEqual({r[0] for r in self.consultar("SELECT categoria_id FROM contas WHERE serie_id = ?",
                                                       (serie_id,))}, {categoria})
        self.assertEqual({r[0] for r in self.consultar("SELECT descricao FROM contas WHERE serie_id = ?",
                                                       (serie_id,))}, {"Loja X"})
        self.assertEqual([db.obter_identificacao(serie_id, i) for i in ids],
                         [{"tipo": "parcela", "posicao": p, "total": 3} for p in (1, 2, 3)])
        self.assertTrue(db.validar_schema_atual()["ok"])

    def test_totais_e_graficos_sem_duplicidade(self):
        db.criar_conta_parcelada(self.usuario_id, "Notebook", 1000.0, 3, "2026-09-30")
        self.assertEqual(db.totais_por_mes(self.usuario_id, "2026-09", "2026-11"),
                         {"2026-09": 333.34, "2026-10": 333.33, "2026-11": 333.33})
        self.assertEqual(db.resumo_do_periodo(self.usuario_id, "2026-01-01", "2026-12-31"), (1000.0, 0))

    def test_nao_gera_alem_da_ultima_parcela(self):
        serie_id, _ = db.criar_conta_parcelada(self.usuario_id, "Curso", 600.0, 2, "2026-09-10")
        self.assertEqual(db.gerar_ocorrencias_sob_demanda(serie_id, "2027-12"), [])
        self.assertEqual(len(self.parcelas(serie_id)), 2)

    def test_recusas_sem_gravar(self):
        antes = self.estado()
        for argumentos in ((100.0, 1), (100.0, 37), (0.01, 2), (-1.0, 3)):
            with self.subTest(argumentos=argumentos):
                with self.assertRaises(db.ParcelamentoRecusadoError):
                    db.criar_conta_parcelada(self.usuario_id, "X", argumentos[0], argumentos[1], "2026-09-10")
        with self.assertRaises(db.LimiteDeCaracteresError):
            db.criar_conta_parcelada(self.usuario_id, "N" * 31, 100.0, 2, "2026-09-10")
        self.assertEqual(self.estado(), antes)

    def test_falha_no_meio_desfaz_tudo(self):
        antes = self.estado()
        with mock.patch.object(db, "_registrar_parcelamento", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                db.criar_conta_parcelada(self.usuario_id, "Notebook", 1000.0, 3, "2026-09-30")
        self.assertEqual(self.estado(), antes)
        original = db._inserir_ocorrencia
        chamadas = []

        def falhar_na_terceira(*args, **kwargs):
            chamadas.append(1)
            if len(chamadas) == 3:
                raise KeyboardInterrupt()
            return original(*args, **kwargs)

        with mock.patch.object(db, "_inserir_ocorrencia", falhar_na_terceira):
            with self.assertRaises(KeyboardInterrupt):
                db.criar_conta_parcelada(self.usuario_id, "Notebook", 1000.0, 5, "2026-09-30")
        self.assertEqual(self.estado(), antes)

    def test_pagamentos_e_estornos_das_parcelas_seguem_as_regras_de_sempre(self):
        serie_id, ids = db.criar_conta_parcelada(self.usuario_id, "Notebook", 1000.0, 3, "2026-09-10")
        pagamentos.registrar_pagamento_parcial(ids[0], 100_00, "2026-09-10")
        self.assertEqual(pagamentos.obter_situacao(ids[0])["saldo_centavos"], 233_34)
        self.assertTrue(db.marcar_conta_como_paga(ids[0], "2026-09-12"))
        self.assertEqual(self.consultar("SELECT status FROM contas WHERE id = ?", (ids[0],)), [("pago",)])
        pagamento = self.consultar("SELECT id, valor_centavos, data_pagamento FROM pp_pagamentos ORDER BY id DESC")[0]
        pagamentos.estornar_pagamento(pagamento[0], pagamento[1:])
        self.assertEqual(self.consultar("SELECT status FROM contas WHERE id = ?", (ids[0],)), [("pendente",)])
        self.assertEqual([v for _, _, v, _, _, _ in self.parcelas(serie_id)][1:], [333.33, 333.33])
        self.assertTrue(db.validar_schema_atual()["ok"])


class TestUnicaParaParcelada(BaseParcelada):
    def test_a_propria_conta_e_a_parcela_1(self):
        conta = db.criar_conta_unica(self.usuario_id, "Geladeira", 2400.0, "2026-09-30", descricao="Loja")
        serie_id, ids = db.transformar_unica_em_parcelada(conta, 12)
        self.assertEqual(ids[0], conta)
        linhas = self.parcelas(serie_id)
        self.assertEqual(len(linhas), 12)
        self.assertEqual(linhas[0][:5], (conta, "2026-09-30", 200.0, "pendente", 1))
        self.assertEqual([d for _, d, *_ in linhas][:6],
                         ["2026-09-30", "2026-10-30", "2026-11-30", "2026-12-30", "2027-01-30", "2027-02-28"])
        self.assertEqual(sum(v for _, _, v, *_ in linhas), 2400.0)
        self.assertEqual(self.consultar("SELECT quantidade_original, valor_total_original_centavos FROM parcelamentos"),
                         [(12, 240000)])
        self.assertEqual(db.obter_identificacao(serie_id, conta), {"tipo": "parcela", "posicao": 1, "total": 12})
        self.assertEqual({r[0] for r in self.consultar("SELECT descricao FROM contas")}, {"Loja"})
        self.assertTrue(db.validar_schema_atual()["ok"])

    def test_centavos_na_primeira(self):
        conta = db.criar_conta_unica(self.usuario_id, "TV", 1000.0, "2026-09-15")
        serie_id, _ = db.transformar_unica_em_parcelada(conta, 3)
        self.assertEqual([v for _, _, v, *_ in self.parcelas(serie_id)], [333.34, 333.33, 333.33])

    def test_recusas_r1_sem_gravar(self):
        casos = {}
        casos["pagamento parcial ativo"] = db.criar_conta_unica(self.usuario_id, "A", 300.0, "2026-09-10")
        pagamentos.registrar_pagamento_parcial(casos["pagamento parcial ativo"], 50_00, "2026-09-05")
        casos["só pagamento estornado"] = db.criar_conta_unica(self.usuario_id, "B", 300.0, "2026-09-10")
        pagamentos.registrar_pagamento_parcial(casos["só pagamento estornado"], 300_00, "2026-09-05")
        pagamentos.estornar_pagamento(self.consultar("SELECT id FROM pp_pagamentos ORDER BY id DESC")[0][0],
                                      (300_00, "2026-09-05"))
        casos["quitada por Marcar como paga"] = db.criar_conta_unica(self.usuario_id, "C", 300.0, "2026-09-10")
        db.marcar_conta_como_paga(casos["quitada por Marcar como paga"], "2026-09-10")
        casos["paga antes da 6.10, sem registro"] = db.criar_conta_unica(self.usuario_id, "D", 300.0, "2026-09-10")
        self.executar("UPDATE contas SET status = 'pago', data_pagamento = '2026-09-01' WHERE id = ?",
                      (casos["paga antes da 6.10, sem registro"],))
        antes = self.estado()
        for nome, conta in casos.items():
            with self.subTest(caso=nome):
                with self.assertRaisesRegex(db.ParcelamentoRecusadoError, "registros de pagamento"):
                    db.transformar_unica_em_parcelada(conta, 3)
                with self.assertRaises(db.ParcelamentoRecusadoError):
                    db.conferir_unica_para_parcelar(conta)
        self.assertEqual(self.estado(), antes)

    def test_so_unica(self):
        _, mensais = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-05", "mensal")
        _, parcelas = db.criar_conta_parcelada(self.usuario_id, "TV", 600.0, 3, "2026-09-20")
        antes = self.estado()
        for conta in (mensais[0], mensais[2], parcelas[0], parcelas[1]):
            with self.subTest(conta=conta):
                with self.assertRaisesRegex(db.ParcelamentoRecusadoError, db.MENSAGEM_NAO_E_UNICA):
                    db.transformar_unica_em_parcelada(conta, 3)
        with self.assertRaisesRegex(db.ParcelamentoRecusadoError, "não encontrada"):
            db.transformar_unica_em_parcelada(999, 3)
        self.assertEqual(self.estado(), antes)

    def test_ocorrencia_de_serie_encerrada_e_unica(self):
        # R7/X2: depois de "Encerrar recorrência", a ocorrência restante é tratada como avulsa.
        serie_antiga, mensais = db.criar_serie_recorrente(self.usuario_id, "Academia", 120.0, "2026-10-05", "mensal")
        db.encerrar_recorrencia(mensais[0])
        serie_id, ids = db.transformar_unica_em_parcelada(mensais[0], 2)
        self.assertNotEqual(serie_id, serie_antiga)
        self.assertEqual([v for _, _, v, *_ in self.parcelas(serie_id)], [60.0, 60.0])
        self.assertTrue(db.validar_schema_atual()["ok"])

    def test_valor_pequeno_e_quantidade(self):
        conta = db.criar_conta_unica(self.usuario_id, "Bala", 0.05, "2026-09-10")
        antes = self.estado()
        with self.assertRaisesRegex(db.ParcelamentoRecusadoError, db.MENSAGEM_VALOR_PEQUENO_PARA_PARCELAS):
            db.transformar_unica_em_parcelada(conta, 6)
        for quantidade in (1, 37):
            with self.assertRaisesRegex(db.ParcelamentoRecusadoError, db.MENSAGEM_QUANTIDADE_DE_PARCELAS):
                db.transformar_unica_em_parcelada(conta, quantidade)
        self.assertEqual(self.estado(), antes)

    def test_falha_no_meio_mantem_a_unica(self):
        conta = db.criar_conta_unica(self.usuario_id, "Geladeira", 2400.0, "2026-09-30")
        antes = self.estado()
        with mock.patch.object(db, "_registrar_parcelamento", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                db.transformar_unica_em_parcelada(conta, 12)
        self.assertEqual(self.estado(), antes)
        self.assertEqual(self.consultar("SELECT serie_id, valor, posicao FROM contas WHERE id = ?", (conta,)),
                         [(None, 2400.0, None)])


class TestParceladaNaoMudaDeTipo(BaseParcelada):
    def test_alterar_frequencia_encerrar_e_transformar_recusados(self):
        _, ids = db.criar_conta_parcelada(self.usuario_id, "TV", 600.0, 3, "2026-09-20")
        antes = self.estado()
        with self.assertRaises(db.EstruturaRecusadaError):          # Etapa 10: R6 para todas as séries
            db.alterar_frequencia_serie(ids[1], "anual")
        with self.assertRaisesRegex(db.ParcelamentoRecusadoError, db.MENSAGEM_PARCELADA_NAO_MUDA_DE_TIPO):
            db.encerrar_recorrencia(ids[0])
        with self.assertRaises(ValueError):
            db.transformar_em_recorrente(ids[0], "mensal")
        self.assertEqual(self.estado(), antes)

    def test_recorrencias_continuam_com_as_regras_de_sempre(self):
        _, mensais = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-05", "mensal",
                                               data_termino="2026-12")
        # Ajuste deliberado na Etapa 10: a frequência não muda mais (R6), também nas recorrências.
        with self.assertRaises(db.EstruturaRecusadaError):
            db.alterar_frequencia_serie(mensais[1], "anual")
        _, outras = db.criar_serie_recorrente(self.usuario_id, "Água", 80.0, "2026-09-12", "mensal")
        db.encerrar_recorrencia(outras[0])
        self.assertTrue(db.validar_schema_atual()["ok"])


if __name__ == "__main__":
    unittest.main()
