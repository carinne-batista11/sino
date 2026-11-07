"""
Sino 6.12 (experimental), Etapa 8 -- recorrências de valor variável (camada de dados).

Criação Fixa/Variável (a primeira ocorrência sempre com valor), geração sob demanda,
Única -> Recorrente variável com o histórico financeiro intacto (R2), bloqueios
estruturais (R6 para as variáveis, X1), valor pendente diferente de R$ 0,00 em listas,
totais e gráficos (R8/R9), recusa de pagamento também na camada de dados e
atomicidade. Hoje fixo: 15/09/2026.
"""

import sqlite3
import unittest
from unittest import mock

from apoio_banco import TesteComBancoTemporario, db

import pagamentos


class Interrupcao(BaseException):
    """Interrupção que não é Exception (como KeyboardInterrupt)."""


class BaseVariavel(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def estado(self):
        return {t: self.consultar(f"SELECT * FROM {t} ORDER BY 1") for t in (
            "contas", "series_recorrencia", "pp_pagamentos", "series_valor_variavel",
            "ocorrencias_valor_pendente", "parcelamentos")}

    def pendentes(self):
        return {c for (c,) in self.consultar("SELECT conta_id FROM ocorrencias_valor_pendente")}

    def valores(self, serie_id):
        return [v for (v,) in self.consultar("SELECT valor FROM contas WHERE serie_id = ? ORDER BY posicao",
                                             (serie_id,))]

    def assert_banco_valido(self):
        resultado = db.validar_schema_atual()
        self.assertTrue(resultado["ok"], resultado)
        self.assertEqual(resultado["dados_v11_invalidos"], 0)


class TestCriacao(BaseVariavel):
    def test_mensal_variavel_sem_termino(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-20", "mensal",
                                                  variavel=True)
        self.assertEqual(len(ids), 13)                                   # mesmo horizonte da 6.11
        self.assertTrue(db.serie_variavel(serie_id))
        self.assertEqual(self.pendentes(), set(ids[1:]))                 # só as seguintes
        self.assertFalse(db.conta_com_valor_pendente(ids[0]))
        self.assertEqual(self.valores(serie_id), [150.0] + [0.0] * 12)   # 0 = marcador interno
        self.assertEqual(self.consultar("SELECT valor FROM series_recorrencia WHERE id = ?", (serie_id,)),
                         [(150.0,)])
        self.assert_banco_valido()

    def test_anual_variavel_com_termino(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "IPVA", 1800.0, "2027-02-28", "anual",
                                                  data_termino="2030-12", variavel=True)
        datas = [d for (d,) in self.consultar("SELECT data_vencimento FROM contas WHERE serie_id = ? "
                                              "ORDER BY posicao", (serie_id,))]
        self.assertEqual(datas, ["2027-02-28", "2028-02-28", "2029-02-28", "2030-02-28"])
        self.assertEqual(self.pendentes(), set(ids[1:]))
        self.assert_banco_valido()

    def test_mesmas_datas_da_fixa(self):
        for data, frequencia, termino in (("2026-01-31", "mensal", "2026-12"), ("2028-02-29", "anual", "2033-12"),
                                          ("2026-10-30", "mensal", None)):
            with self.subTest(data=data, frequencia=frequencia):
                fixa, _ = db.criar_serie_recorrente(self.usuario_id, "F", 10.0, data, frequencia, data_termino=termino)
                variavel, _ = db.criar_serie_recorrente(self.usuario_id, "V", 10.0, data, frequencia,
                                                        data_termino=termino, variavel=True)
                datas = [self.consultar("SELECT data_vencimento, data_prevista, posicao FROM contas WHERE serie_id = ? "
                                        "ORDER BY posicao", (s,)) for s in (fixa, variavel)]
                self.assertEqual(datas[0], datas[1])

    def test_fixa_continua_como_na_611(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "mensal")
        self.assertFalse(db.serie_variavel(serie_id))
        self.assertEqual(self.valores(serie_id), [900.0] * 13)
        self.assertEqual(self.pendentes(), set())
        self.assertEqual(self.consultar("SELECT * FROM series_valor_variavel"), [])

    def test_primeiro_valor_obrigatorio(self):
        antes = self.estado()
        for valor in (None, "100", -1.0, True):
            with self.subTest(valor=valor), self.assertRaises(db.ValorVariavelRecusadoError) as recusa:
                db.criar_serie_recorrente(self.usuario_id, "Luz", valor, "2026-09-20", "mensal", variavel=True)
            self.assertEqual(str(recusa.exception), db.MENSAGEM_PRIMEIRO_VALOR_OBRIGATORIO)
        self.assertEqual(self.estado(), antes)

    def test_zero_informado_e_valor_conhecido(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Taxa", 0.0, "2026-09-20", "mensal",
                                                  data_termino="2026-11", variavel=True)
        contas = db.listar_contas(self.usuario_id)
        self.assertEqual([c["valor_pendente"] for c in contas], [False, True, True])
        self.assertEqual(db.valor_conhecido(contas[0]), 0.0)             # R$ 0,00 informado ≠ pendente
        self.assertIsNone(db.valor_conhecido(contas[1]))

    def test_rollback_na_marcacao_das_pendentes(self):
        antes = self.estado()
        original = db._marcar_valor_pendente

        def marcar_e_interromper(cursor, ids):
            original(cursor, ids[:3])
            raise Interrupcao()

        with mock.patch.object(db, "_marcar_valor_pendente", marcar_e_interromper), self.assertRaises(Interrupcao):
            db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-20", "mensal", variavel=True)
        self.assertEqual(self.estado(), antes)


class TestGeracaoSobDemanda(BaseVariavel):
    def test_novas_ocorrencias_pendentes(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-20", "mensal",
                                                  variavel=True)
        novos = db.gerar_ocorrencias_sob_demanda(serie_id, "2028-03")
        self.assertEqual(len(novos), 6)
        self.assertTrue(set(novos) <= self.pendentes())
        self.assertEqual(self.valores(serie_id)[-6:], [0.0] * 6)
        self.assertEqual(db.gerar_ocorrencias_sob_demanda(serie_id, "2028-03"), [])   # idempotente
        self.assert_banco_valido()

    def test_fixa_continua_copiando_o_valor(self):
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "mensal")
        novos = db.gerar_ocorrencias_sob_demanda(serie_id, "2028-03")
        self.assertEqual(self.valores(serie_id)[-len(novos):], [900.0] * len(novos))
        self.assertEqual(self.pendentes(), set())

    def test_com_termino_nao_gera(self):
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-20", "mensal",
                                                data_termino="2027-02", variavel=True)
        self.assertEqual(db.gerar_ocorrencias_sob_demanda(serie_id, "2028-03"), [])

    def test_rollback_na_geracao(self):
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-20", "mensal",
                                                variavel=True)
        antes = self.estado()
        with mock.patch.object(db, "_renumerar_segmento", side_effect=RuntimeError("falha")), \
                self.assertRaises(RuntimeError):
            db.gerar_ocorrencias_sob_demanda(serie_id, "2028-03")
        self.assertEqual(self.estado(), antes)


class TestTransformacao(BaseVariavel):
    """R2: a Única vira a primeira ocorrência com tudo intacto; as seguintes ficam pendentes."""

    def financeiro(self, conta_id):
        return (self.consultar("SELECT valor, status, data_pagamento, data_vencimento, nome FROM contas WHERE id = ?",
                               (conta_id,)),
                self.consultar("SELECT * FROM pp_pagamentos WHERE conta_id = ? ORDER BY id", (conta_id,)))

    def test_unica_sem_pagamentos(self):
        conta = db.criar_conta_unica(self.usuario_id, "Água", 80.0, "2026-09-18")
        serie_id, novos = db.transformar_em_recorrente(conta, "mensal", variavel=True)
        self.assertEqual(self.pendentes(), set(novos))
        self.assertEqual(self.valores(serie_id), [80.0] + [0.0] * 12)
        self.assertTrue(db.serie_variavel(serie_id))
        self.assert_banco_valido()

    def test_preserva_pagamentos_estornos_status_e_historico(self):
        casos = {}
        parcial = db.criar_conta_unica(self.usuario_id, "Parcial", 300.0, "2026-09-10")
        pagamentos.registrar_pagamento_parcial(parcial, 100_00, "2026-09-05")
        casos["parcial"] = parcial
        quitada = db.criar_conta_unica(self.usuario_id, "Quitada", 200.0, "2026-09-12")
        pagamentos.registrar_pagamento_parcial(quitada, 50_00, "2026-09-01")
        pagamentos.registrar_pagamento_parcial(quitada, 150_00, "2026-09-11")
        casos["quitada"] = quitada
        estornada = db.criar_conta_unica(self.usuario_id, "Estornada", 120.0, "2026-09-14")
        pagamentos.registrar_pagamento_parcial(estornada, 20_00, "2026-09-13")
        p = pagamentos.obter_situacao(estornada)["ativos"][0]
        pagamentos.estornar_pagamento(p["id"], (p["valor_centavos"], p["data_pagamento"]))
        casos["estornada"] = estornada
        marcada = db.criar_conta_unica(self.usuario_id, "Marcada", 90.0, "2026-09-01")
        db.marcar_conta_como_paga(marcada, "2026-09-02")
        casos["marcada"] = marcada
        for nome, conta in casos.items():
            with self.subTest(caso=nome):
                antes = self.financeiro(conta)
                situacao_antes = pagamentos.obter_situacao(conta)
                _, novos = db.transformar_em_recorrente(conta, "anual" if nome == "marcada" else "mensal",
                                                        variavel=True)
                self.assertEqual(self.financeiro(conta), antes)
                self.assertEqual(pagamentos.obter_situacao(conta), situacao_antes)
                self.assertFalse(db.conta_com_valor_pendente(conta))
                self.assertTrue(set(novos) <= self.pendentes())
                self.assertEqual(self.consultar("SELECT COUNT(*) FROM pp_pagamentos WHERE conta_id IN (%s)"
                                                % ",".join("?" * len(novos)), tuple(novos)), [(0,)])
        self.assert_banco_valido()

    def test_fixa_com_pagamentos_como_na_611(self):
        conta = db.criar_conta_unica(self.usuario_id, "Escola", 500.0, "2026-09-10")
        pagamentos.registrar_pagamento_parcial(conta, 100_00, "2026-09-05")
        serie_id, novos = db.transformar_em_recorrente(conta, "mensal")
        self.assertEqual(self.valores(serie_id), [500.0] * 13)
        self.assertEqual(self.pendentes(), set())
        self.assertFalse(db.serie_variavel(serie_id))

    def test_rollback_mantem_a_unica(self):
        conta = db.criar_conta_unica(self.usuario_id, "Água", 80.0, "2026-09-18")
        pagamentos.registrar_pagamento_parcial(conta, 10_00, "2026-09-14")
        antes = self.estado()
        with mock.patch.object(db, "_marcar_valor_pendente", side_effect=Interrupcao()), \
                self.assertRaises(Interrupcao):
            db.transformar_em_recorrente(conta, "mensal", variavel=True)
        self.assertEqual(self.estado(), antes)

    def test_x1_serie_ativa_nao_e_transformada(self):
        _, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-20", "mensal", variavel=True)
        antes = self.estado()
        with self.assertRaises(ValueError):
            db.transformar_em_recorrente(ids[0], "anual", variavel=True)
        self.assertEqual(self.estado(), antes)

    def test_r6_variavel_nao_muda_de_frequencia(self):
        _, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-20", "mensal", variavel=True)
        antes = self.estado()
        with self.assertRaises(db.ValorVariavelRecusadoError) as recusa:
            db.alterar_frequencia_serie(ids[2], "anual")
        self.assertEqual(str(recusa.exception), db.MENSAGEM_VARIAVEL_NAO_MUDA_FREQUENCIA)
        self.assertEqual(self.estado(), antes)

    def test_pendente_avulsa_nao_e_transformada_nem_parcelada(self):
        # Série variável encerrada (6.11/R7): as ocorrências passadas ficam avulsas, ainda pendentes.
        _, ids = db.criar_serie_recorrente(self.usuario_id, "Gás", 70.0, "2026-07-10", "mensal", variavel=True)
        db.encerrar_recorrencia(ids[1])
        self.assertIn(ids[1], self.pendentes())
        antes = self.estado()
        with self.assertRaises(db.ValorVariavelRecusadoError) as recusa:
            db.transformar_em_recorrente(ids[1], "mensal")
        self.assertEqual(str(recusa.exception), db.MENSAGEM_TRANSFORMAR_COM_VALOR_PENDENTE)
        with self.assertRaises(db.ParcelamentoRecusadoError) as recusa:
            db.transformar_unica_em_parcelada(ids[1], 3)
        self.assertEqual(str(recusa.exception), db.MENSAGEM_PARCELAR_COM_VALOR_PENDENTE)
        self.assertEqual(self.estado(), antes)
        self.assert_banco_valido()


class TestValoresPendentesNasConsultas(BaseVariavel):
    """R8/V5-V7: pendentes aparecem nas listas, contados à parte, nunca somados como R$ 0,00."""

    def setUp(self):
        super().setUp()
        self.casa = self.criar_categoria(self.usuario_id, "Casa")
        # Variável desde julho: julho com valor; agosto e setembro pendentes (atrasadas); outubro em diante pendentes.
        self.serie, self.ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-07-10", "mensal",
                                                         data_termino="2026-12", categoria_id=self.casa,
                                                         variavel=True)
        # Pendente que vence dentro de 7 dias (20/09).
        self.serie2, self.ids2 = db.criar_serie_recorrente(self.usuario_id, "Gás", 60.0, "2026-08-20", "mensal",
                                                           data_termino="2026-10", variavel=True)
        self.aluguel = db.criar_conta_unica(self.usuario_id, "Aluguel", 900.0, "2026-09-25", categoria_id=self.casa)
        self.zero = db.criar_conta_unica(self.usuario_id, "Cortesia", 0.0, "2026-09-16")

    def test_listar_contas_marca_pendentes(self):
        contas = {c["nome"]: c for c in db.listar_contas(self.usuario_id, "2026-09")}
        self.assertTrue(contas["Luz"]["valor_pendente"])
        self.assertEqual(contas["Luz"]["status"], "atrasado")
        self.assertTrue(contas["Gás"]["valor_pendente"])
        self.assertFalse(contas["Aluguel"]["valor_pendente"])
        self.assertFalse(contas["Cortesia"]["valor_pendente"])               # R$ 0,00 informado
        self.assertEqual(db.soma_dos_valores_conhecidos(contas.values()), 900.0)
        self.assertEqual(db.quantidade_com_valor_pendente(contas.values()), 2)

    def test_atrasadas_e_proximas_incluem_pendentes(self):
        atrasadas = {c["id"]: c for c in db.listar_contas_atrasadas(self.usuario_id)}
        # 10/07 (Luz) e 20/08 (Gás) com valor; 10/08 e 10/09 (Luz) com valor pendente -- todas atrasadas.
        self.assertEqual({i: c["valor_pendente"] for i, c in atrasadas.items()},
                         {self.ids[0]: False, self.ids2[0]: False, self.ids[1]: True, self.ids[2]: True})
        proximas = {c["id"]: c for c in db.listar_contas_proximas(self.usuario_id)}
        self.assertEqual(set(proximas), {self.ids2[1], self.zero})          # Aluguel (25/09) fica fora dos 7 dias
        self.assertTrue(proximas[self.ids2[1]]["valor_pendente"])
        self.assertFalse(proximas[self.zero]["valor_pendente"])

    def test_totais_e_graficos_so_com_valores_conhecidos(self):
        self.assertEqual(db.resumo_do_periodo(self.usuario_id, "2026-09-01", "2026-09-30"), (900.0, 0.0))
        self.assertEqual(db.pendentes_do_periodo(self.usuario_id, "2026-09-01", "2026-09-30"), 2)
        totais = db.totais_por_mes(self.usuario_id, "2026-07", "2026-12")
        self.assertEqual(totais, {"2026-07": 150.0, "2026-08": 60.0, "2026-09": 900.0, "2026-10": 0.0,
                                  "2026-11": 0.0, "2026-12": 0.0})
        self.assertEqual(db.pendentes_por_mes(self.usuario_id, "2026-07", "2026-12"),
                         {"2026-08": 1, "2026-09": 2, "2026-10": 2, "2026-11": 1, "2026-12": 1})
        self.assertEqual(db.totais_por_ano(self.usuario_id), [(2026, 1110.0)])
        self.assertEqual(db.pendentes_por_ano(self.usuario_id), {2026: 7})
        categorias = {i["categoria_id"]: i["total"] for i in
                      db.gastos_por_categoria(self.usuario_id, "2026-09-01", "2026-09-30")}
        self.assertEqual(categorias, {self.casa: 900.0, None: 0.0})
        self.assertEqual(db.pendentes_por_categoria(self.usuario_id, "2026-09-01", "2026-09-30"),
                         {self.casa: 1, None: 1})

    def test_mes_so_com_pendentes(self):
        self.assertEqual(db.listar_contas(self.usuario_id, "2026-11")[0]["valor_pendente"], True)
        self.assertEqual(db.totais_por_mes(self.usuario_id, "2026-11", "2026-11"), {"2026-11": 0.0})
        self.assertEqual(db.pendentes_por_mes(self.usuario_id, "2026-11", "2026-11"), {"2026-11": 1})

    def test_situacao_do_pagamento(self):
        self.assertTrue(pagamentos.obter_situacao(self.ids[1])["valor_pendente"])
        self.assertFalse(pagamentos.obter_situacao(self.ids[0])["valor_pendente"])
        self.assertFalse(pagamentos.obter_situacao(self.aluguel)["valor_pendente"])


class TestProtecaoDosPagamentos(BaseVariavel):
    def setUp(self):
        super().setUp()
        self.serie, self.ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-08-10", "mensal",
                                                         data_termino="2026-12", variavel=True)

    def test_marcar_como_paga_recusada(self):
        antes = self.estado()
        with self.assertRaises(db.ValorVariavelRecusadoError) as recusa:
            db.marcar_conta_como_paga(self.ids[1])
        self.assertEqual(str(recusa.exception), db.MENSAGEM_PAGAMENTO_COM_VALOR_PENDENTE)
        self.assertEqual(self.estado(), antes)

    def test_pagamento_parcial_recusado(self):
        antes = self.estado()
        with self.assertRaises(pagamentos.ContaComValorPendenteError) as recusa:
            pagamentos.registrar_pagamento_parcial(self.ids[2], 10_00, "2026-09-15")
        self.assertIsInstance(recusa.exception, pagamentos.PagamentoError)
        self.assertIsInstance(recusa.exception, db.ValorVariavelRecusadoError)
        self.assertEqual(str(recusa.exception), db.MENSAGEM_PAGAMENTO_COM_VALOR_PENDENTE)
        self.assertEqual(self.estado(), antes)

    def test_primeira_ocorrencia_paga_como_sempre(self):
        situacao = pagamentos.registrar_pagamento_parcial(self.ids[0], 50_00, "2026-09-01")
        self.assertEqual(situacao["saldo_centavos"], 100_00)
        self.assertTrue(db.marcar_conta_como_paga(self.ids[0]))
        self.assertEqual(pagamentos.obter_situacao(self.ids[0])["status"], "pago")
        self.assert_banco_valido()

    def test_pendente_nunca_tem_registros(self):
        pagamentos.registrar_pagamento_parcial(self.ids[0], 50_00, "2026-09-01")
        # O gatilho da v11 impede marcar como pendente uma ocorrência com registros, inclusive numa transação.
        antes = self.estado()
        with self.assertRaises(sqlite3.IntegrityError):
            with db.transacao() as cursor:
                db._marcar_valor_pendente(cursor, [self.ids[0]])
        self.assertEqual(self.estado(), antes)
        self.assert_banco_valido()

    def test_valor_invalido_na_pendente_recusado(self):
        # Ajuste deliberado na Etapa 9: informar o valor passou a ser permitido (ver
        # test_612_variavel_edicao); continua recusado um valor inválido, sem gravar nada.
        antes = self.estado()
        for valor in (-1.0, "80", True):
            with self.subTest(valor=valor), self.assertRaises(db.ValorVariavelRecusadoError) as recusa:
                db.editar_conta_ocorrencia(self.ids[1], valor=valor)
            self.assertEqual(str(recusa.exception), db.MENSAGEM_VALOR_INVALIDO)
        self.assertEqual(self.estado(), antes)

    def test_nome_e_vencimento_da_pendente_editaveis(self):
        self.assertTrue(db.editar_conta_ocorrencia(self.ids[2], nome="Luz (set)", data_vencimento="2026-10-01"))
        self.assertIn(self.ids[2], self.pendentes())
        self.assert_banco_valido()

    def test_valor_da_primeira_editavel(self):
        self.assertTrue(db.editar_conta_ocorrencia(self.ids[0], valor=170.0))
        self.assertEqual(self.valores(self.serie)[0], 170.0)

    def test_nome_e_vencimento_em_diante_mantem_pendentes(self):
        pendentes = self.pendentes()
        self.assertTrue(db.editar_conta_serie(self.ids[1], nome="Energia", data_vencimento="2026-09-12"))
        self.assertEqual(self.pendentes(), pendentes)
        self.assertEqual(self.valores(self.serie), [150.0] + [0.0] * 4)
        self.assert_banco_valido()

    def test_fixa_em_diante_como_na_611(self):
        _, ids = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "mensal",
                                           data_termino="2026-12")
        self.assertTrue(db.editar_conta_serie(ids[1], valor=950.0))
        self.assertEqual([v for (v,) in self.consultar("SELECT valor FROM contas WHERE id IN (?, ?, ?, ?) "
                                                       "ORDER BY posicao", tuple(ids))], [900.0, 950.0, 950.0, 950.0])

    def test_exclusoes_nao_deixam_orfaos(self):
        db.excluir_conta(self.ids[1])
        db.excluir_conta_serie(self.ids[3])
        self.assertEqual(self.pendentes(), {self.ids[2]})
        self.assert_banco_valido()


if __name__ == "__main__":
    unittest.main()
