"""
Posição lógica das ocorrências de série (ERS v6.0, Etapa 2b).

`contas.posicao` define anteriores/selecionada/futuras e a parcela;
`contas.data_prevista` é a vaga da grade que a ocorrência ocupa;
`series_recorrencia.posicao_ancora` é a posição onde a grade atual foi
ancorada. "Somente este mês" só muda o vencimento real, que continua
definindo em que mês a conta aparece.

Decisões: D1 variante "d" (a nova grade continua a partir da vaga da
selecionada); D2 editadas preservadas fora da grade mantêm data e vaga; D4
editadas além do término são preservadas e contadas, sem novas vagas depois
dele. Uma editada preservada ocupa a própria competência prevista.
"""

import unittest
from collections import Counter
from datetime import date
from unittest import mock

from apoio_banco import TesteComBancoTemporario, db


class BasePosicao(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def posicoes(self, serie_id):
        """(id, posicao, data_prevista, data_vencimento) em ordem de posição."""
        return self.consultar(
            "SELECT id, posicao, data_prevista, data_vencimento FROM contas "
            "WHERE serie_id = ? ORDER BY posicao", (serie_id,),
        )

    def linha(self, conta_id):
        return self.consultar(
            "SELECT id, posicao, data_prevista, data_vencimento, valor, categoria_id, descricao, "
            "status, data_pagamento, editado_individualmente FROM contas WHERE id = ?", (conta_id,),
        )[0]

    def extra_serie(self, serie_id, coluna):
        return self.consultar(f"SELECT {coluna} FROM series_recorrencia WHERE id = ?", (serie_id,))[0][0]

    def competencias_previstas(self, serie_id):
        return Counter(p[:7] for _, _, p, _ in self.posicoes(serie_id))

    def assert_invariantes(self, serie_id):
        linhas = self.posicoes(serie_id)
        posicoes = [p for _, p, _, _ in linhas]
        self.assertNotIn(None, posicoes)
        self.assertEqual(len(set(posicoes)), len(posicoes))
        self.assertNotIn(None, [p for _, _, p, _ in linhas])
        ancora = self.extra_serie(serie_id, "posicao_ancora")
        segmento = [(prevista, conta_id) for conta_id, posicao, prevista, _ in linhas if posicao > ancora]
        self.assertEqual(segmento, sorted(segmento), "segmento fora da ordem (vaga, id)")

    def assert_sem_vaga_duplicada(self, serie_id):
        duplicadas = [c for c, n in self.competencias_previstas(serie_id).items() if n > 1]
        self.assertEqual(duplicadas, [])


class TestJaneiroMovidoParaDepoisDeFevereiro(BasePosicao):
    """O cenário do achado 5: janeiro movido para 20/02 com "Somente este mês"."""

    def setUp(self):
        super().setUp()
        self.casa = self.criar_categoria(self.usuario_id, "Casa")
        self.lazer = self.criar_categoria(self.usuario_id, "Lazer")
        self.serie_id, (self.jan, self.fev, self.mar) = db.criar_serie_recorrente(
            self.usuario_id, "Escola", 700.0, "2027-01-10", "mensal", data_termino="2027-03",
            categoria_id=self.casa, descricao="Original",
        )
        db.editar_conta_ocorrencia(self.jan, data_vencimento="2027-02-20")
        self.janeiro_antes = self.linha(self.jan)

    def test_somente_este_mes_nao_muda_posicao_nem_vaga(self):
        self.assertEqual(self.janeiro_antes[:4], (self.jan, 1, "2027-01-10", "2027-02-20"))

    def test_categoria_e_descricao_a_partir_de_fevereiro_nao_alcancam_janeiro(self):
        self.assertTrue(db.editar_conta_serie(self.fev, categoria_id=self.lazer, descricao="Nova"))

        self.assertEqual(self.linha(self.jan), self.janeiro_antes)
        for conta_id in (self.fev, self.mar):
            self.assertEqual(self.linha(conta_id)[5:7], (self.lazer, "Nova"))
        self.assertEqual(self.extra_serie(self.serie_id, "descricao"), "Nova")

    def test_mudanca_de_data_a_partir_de_fevereiro_nao_alcanca_janeiro(self):
        # Antes da Etapa 2b: recusada como "ultrapassaria o término".
        self.assertTrue(db.editar_conta_serie(self.fev, data_vencimento="2027-02-15"))

        self.assertEqual(self.linha(self.jan), self.janeiro_antes)
        self.assertEqual(self.posicoes(self.serie_id), [
            (self.jan, 1, "2027-01-10", "2027-02-20"),
            (self.fev, 2, "2027-02-15", "2027-02-15"),
            (self.mar, 3, "2027-03-15", "2027-03-15"),
        ])
        serie = self.serie(self.serie_id)
        self.assertEqual((serie["dia_ancora"], serie["horizonte_gerado_ate"]), (15, "2027-03-15"))
        self.assertEqual(self.extra_serie(self.serie_id, "posicao_ancora"), 2)

    def test_exclusao_a_partir_de_fevereiro_preserva_janeiro_pago(self):
        db.marcar_conta_como_paga(self.jan, "2026-09-10")
        self.assertTrue(db.excluir_conta_serie(self.fev))

        self.assertEqual([c for c, _, _, _ in self.posicoes(self.serie_id)], [self.jan])
        self.assertEqual(self.linha(self.jan)[7:9], ("pago", "2026-09-10"))
        self.assertEqual(self.serie(self.serie_id)["horizonte_gerado_ate"], "2027-01-10")

    def test_parcela_segue_a_posicao(self):
        self.assertEqual([db.obter_parcela(self.serie_id, c) for c in (self.jan, self.fev, self.mar)],
                         [(1, 3), (2, 3), (3, 3)])

    def test_encerrar_a_partir_de_fevereiro_preserva_janeiro(self):
        db.encerrar_recorrencia(self.fev)
        self.assertEqual([c for c, _, _, _ in self.posicoes(self.serie_id)], [self.jan, self.fev])
        self.assertEqual(self.linha(self.jan), self.janeiro_antes)

    def test_alterar_frequencia_a_partir_de_fevereiro_nao_trata_janeiro_como_futura(self):
        resultado = db.alterar_frequencia_serie(self.fev, "mensal", data_termino="2027-03")
        self.assertNotIn(self.jan, resultado["ocorrencias_preservadas"])
        self.assertEqual(self.linha(self.jan), self.janeiro_antes)
        self.assert_invariantes(self.serie_id)

    def test_listagem_por_mes_usa_o_vencimento_real(self):
        fevereiro = [c["id"] for c in db.listar_contas(self.usuario_id, "2027-02")]
        janeiro = [c["id"] for c in db.listar_contas(self.usuario_id, "2027-01")]
        self.assertEqual(fevereiro, [self.fev, self.jan])  # 10/02 e 20/02
        self.assertEqual(janeiro, [])


class TestMudancaDeDataEmSerieSemTermino(BasePosicao):
    def test_janeiro_movido_e_nova_ancora_em_fevereiro(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 50.0, "2027-01-10", "mensal")
        db.editar_conta_ocorrencia(ids[0], data_vencimento="2027-02-20")

        self.assertTrue(db.editar_conta_serie(ids[1], data_vencimento="2027-02-15"))
        self.assertEqual(self.linha(ids[0])[:4], (ids[0], 1, "2027-01-10", "2027-02-20"))
        self.assertEqual(self.linha(ids[2])[3], "2027-03-15")

        db.gerar_ocorrencias_sob_demanda(serie_id, "2028-04")
        self.assertEqual([v for _, _, _, v in self.posicoes(serie_id)][-3:],
                         ["2028-02-15", "2028-03-15", "2028-04-15"])
        self.assert_invariantes(serie_id)
        self.assert_sem_vaga_duplicada(serie_id)


class TestSomenteEsteMesMovendoDatas(BasePosicao):
    def setUp(self):
        super().setUp()
        self.serie_id, self.ids = db.criar_serie_recorrente(
            self.usuario_id, "Escola", 700.0, "2027-01-10", "mensal", data_termino="2027-04",
        )

    def test_mesma_data_de_outra_ocorrencia(self):
        jan, fev, mar, abr = self.ids
        db.editar_conta_ocorrencia(fev, data_vencimento="2027-03-10")
        self.assertEqual([db.obter_parcela(self.serie_id, c)[0] for c in self.ids], [1, 2, 3, 4])
        self.assertEqual([c["id"] for c in db.listar_contas(self.usuario_id, "2027-03")], [fev, mar])

    def test_mover_para_antes_da_primeira(self):
        jan, fev, mar, abr = self.ids
        db.editar_conta_ocorrencia(mar, data_vencimento="2026-12-01")
        self.assertEqual(db.obter_parcela(self.serie_id, mar), (3, 4))
        # a partir de fevereiro, março continua sendo futura
        self.assertTrue(db.editar_conta_serie(fev, valor=750.0))
        self.assertEqual([self.linha(c)[4] for c in self.ids], [700.0, 750.0, 750.0, 750.0])

    def test_mover_para_outro_mes_nao_suprime_a_vaga(self):
        # E4: a última gerada é movida para a data da próxima vaga
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 50.0, "2027-01-10", "mensal")
        ultima = ids[-1]
        self.assertEqual(self.linha(ultima)[2], "2028-01-10")
        db.editar_conta_ocorrencia(ultima, data_vencimento="2028-02-10")

        novos = db.gerar_ocorrencias_sob_demanda(serie_id, "2028-03")

        self.assertEqual([self.linha(c)[2] for c in novos], ["2028-02-10", "2028-03-10"])
        self.assertEqual([c["id"] for c in db.listar_contas(self.usuario_id, "2028-02")
                          if c["serie_id"] == serie_id], [ultima, novos[0]])
        self.assertEqual(db.obter_parcela(serie_id, ultima)[0] + 1, db.obter_parcela(serie_id, novos[0])[0])
        self.assert_invariantes(serie_id)


class TestReancoragemEmOcorrenciaMovidaParaAntesDoHistorico(BasePosicao):
    """D1, variante "d"."""

    def setUp(self):
        super().setUp()
        self.serie_id, self.ids = db.criar_serie_recorrente(
            self.usuario_id, "Luz", 50.0, "2027-01-10", "mensal",
        )
        self.abr = self.ids[3]
        db.editar_conta_ocorrencia(self.abr, data_vencimento="2026-11-05")
        self.anteriores = [self.linha(c) for c in self.ids[:3]]

    def test_mensal_nao_gera_vagas_por_cima_do_historico(self):
        db.alterar_frequencia_serie(self.abr, "mensal")

        self.assertEqual([self.linha(c) for c in self.ids[:3]], self.anteriores)
        self.assertEqual(self.linha(self.abr)[:4], (self.abr, 4, "2027-04-10", "2026-11-05"))
        seguintes = self.posicoes(self.serie_id)[4:]
        self.assertEqual(seguintes[0][2:], ("2027-05-05", "2027-05-05"))
        self.assertEqual(seguintes[-1][2], "2028-04-05")
        serie = self.serie(self.serie_id)
        self.assertEqual((serie["dia_ancora"], serie["data_inicio"], serie["horizonte_gerado_ate"]),
                         (5, "2027-04-05", "2028-04-05"))
        self.assertEqual(self.extra_serie(self.serie_id, "posicao_ancora"), 4)

        db.gerar_ocorrencias_sob_demanda(self.serie_id, "2028-12")
        self.assertEqual([self.linha(c) for c in self.ids[:3]], self.anteriores)
        self.assertEqual(self.posicoes(self.serie_id)[-1][2], "2028-12-05")
        self.assert_invariantes(self.serie_id)
        self.assert_sem_vaga_duplicada(self.serie_id)

    def test_encerrar_na_movida_nao_remove_as_anteriores(self):
        # corte = max(05/11/2026, hoje) -- as anteriores (jan–mar/2027, não
        # editadas) vencem depois do corte, mas vêm antes na posição.
        db.encerrar_recorrencia(self.abr)
        self.assertEqual([self.linha(c) for c in self.ids[:3]], self.anteriores)
        self.assertEqual([c for c, _, _, _ in self.posicoes(self.serie_id)], self.ids[:4])

    def test_anual_continua_depois_da_vaga(self):
        db.alterar_frequencia_serie(self.abr, "anual")
        self.assertEqual([self.linha(c) for c in self.ids[:3]], self.anteriores)
        self.assertEqual([p for _, _, p, _ in self.posicoes(self.serie_id)[4:]], ["2027-11-05"])
        db.gerar_ocorrencias_sob_demanda(self.serie_id, "2030-12")
        self.assertEqual([p for _, _, p, _ in self.posicoes(self.serie_id)[4:]],
                         ["2027-11-05", "2028-11-05", "2029-11-05", "2030-11-05"])
        self.assert_invariantes(self.serie_id)

    def test_sem_movimento_a_grade_e_a_mesma_de_antes(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "Plano", 50.0, "2026-01-10", "mensal", data_termino="2026-12",
        )
        db.alterar_frequencia_serie(ids[3], "anual", data_termino="2028-12")
        self.assertEqual([p for _, _, p, _ in self.posicoes(serie_id)],
                         ["2026-01-10", "2026-02-10", "2026-03-10", "2026-04-10", "2027-04-10", "2028-04-10"])


class TestPreservadasNasMudancasDeFrequencia(BasePosicao):
    def test_e1_mensal_com_agosto_editado_nao_duplica_agosto(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "Clube", 100.0, "2027-01-10", "mensal", data_termino="2027-12",
        )
        agosto = ids[7]
        db.editar_conta_ocorrencia(agosto, valor=999.0)

        db.alterar_frequencia_serie(ids[1], "mensal", data_termino="2027-12")

        self.assert_sem_vaga_duplicada(serie_id)
        self.assertEqual(len(self.posicoes(serie_id)), 12)
        self.assertEqual(db.obter_parcela(serie_id, agosto), (8, 12))
        self.assert_invariantes(serie_id)

    def test_e2_anual_para_mensal_nao_duplica_fevereiro(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "IPVA", 500.0, "2027-02-10", "anual", data_termino="2029-12",
        )
        fev_2028 = ids[1]
        db.editar_conta_ocorrencia(fev_2028, valor=777.0)

        db.alterar_frequencia_serie(ids[0], "mensal", data_termino="2028-04")

        fevereiros = [c for c, _, p, _ in self.posicoes(serie_id) if p.startswith("2028-02")]
        self.assertEqual(fevereiros, [fev_2028])
        self.assertIsNone(self.conta(ids[2]))  # fev/2029 não editada: substituída
        self.assertEqual(len(self.posicoes(serie_id)), 15)
        self.assert_invariantes(serie_id)

    def test_mensal_para_anual_preserva_editadas_fora_da_grade_com_a_mesma_vaga(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Clube", 100.0, "2027-01-10", "mensal")
        agosto, outubro = ids[7], ids[9]
        db.editar_conta_ocorrencia(agosto, valor=999.0)
        db.editar_conta_ocorrencia(outubro, data_vencimento="2027-11-20")

        db.alterar_frequencia_serie(ids[1], "anual")
        db.gerar_ocorrencias_sob_demanda(serie_id, "2030-12")

        self.assertEqual(self.posicoes(serie_id), [
            (ids[0], 1, "2027-01-10", "2027-01-10"),
            (ids[1], 2, "2027-02-10", "2027-02-10"),
            (agosto, 3, "2027-08-10", "2027-08-10"),
            (outubro, 4, "2027-10-10", "2027-11-20"),
            *[(c, p, v, v) for c, p, v, _ in self.posicoes(serie_id)[4:]],
        ])
        self.assertEqual([v for _, _, v, _ in self.posicoes(serie_id)[4:]],
                         ["2028-02-10", "2029-02-10", "2030-02-10"])
        self.assert_invariantes(serie_id)

    def test_anual_para_mensal_preservada_movida_ocupa_a_propria_vaga(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "IPVA", 500.0, "2027-02-10", "anual", data_termino="2030-12",
        )
        fev_2028, fev_2029 = ids[1], ids[2]
        db.editar_conta_ocorrencia(fev_2028, valor=777.0)
        db.editar_conta_ocorrencia(fev_2029, data_vencimento="2029-03-20")

        db.alterar_frequencia_serie(ids[0], "mensal", data_termino="2029-06")

        competencias = self.competencias_previstas(serie_id)
        self.assertEqual((competencias["2028-02"], competencias["2029-02"]), (1, 1))
        self.assertEqual(self.linha(fev_2029)[2:4], ("2029-02-10", "2029-03-20"))
        em_marco = [c["id"] for c in db.listar_contas(self.usuario_id, "2029-03") if c["serie_id"] == serie_id]
        self.assertEqual(len(em_marco), 2)
        self.assertIn(fev_2029, em_marco)
        self.assertIsNone(self.conta(ids[3]))  # fev/2030 não editada: substituída
        self.assert_invariantes(serie_id)

    def test_d4_editada_alem_do_termino_e_preservada_e_contada(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "IPVA", 500.0, "2027-02-10", "anual", data_termino="2030-12",
        )
        fev_2030 = ids[3]
        db.editar_conta_ocorrencia(fev_2030, valor=888.0)

        db.alterar_frequencia_serie(ids[0], "mensal", data_termino="2028-06")

        ultimas = self.posicoes(serie_id)[-2:]
        self.assertEqual([p for _, _, p, _ in ultimas], ["2028-06-10", "2030-02-10"])
        self.assertEqual(db.obter_parcela(serie_id, fev_2030), (18, 18))
        serie = self.serie(serie_id)
        self.assertEqual((serie["data_termino"], serie["horizonte_gerado_ate"]), ("2028-06", "2028-06-10"))
        self.assertEqual(db.gerar_ocorrencias_sob_demanda(serie_id, "2031-12"), [])

    def test_e3_horizonte_nao_salta_por_uma_preservada_distante(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 50.0, "2027-01-10", "mensal")
        db.gerar_ocorrencias_sob_demanda(serie_id, "2029-12")
        dezembro_2029 = self.id_por_data(serie_id, "2029-12-10")
        db.editar_conta_ocorrencia(dezembro_2029, valor=51.0)

        db.alterar_frequencia_serie(ids[1], "mensal")
        self.assertEqual(self.serie(serie_id)["horizonte_gerado_ate"], "2028-02-10")

        db.gerar_ocorrencias_sob_demanda(serie_id, "2029-12")
        competencias = self.competencias_previstas(serie_id)
        meses = [f"{a}-{m:02d}" for a in (2027, 2028, 2029) for m in range(1, 13)]
        self.assertEqual([m for m in meses if competencias[m] != 1], [])
        self.assertEqual(self.linha(dezembro_2029)[4], 51.0)
        self.assert_invariantes(serie_id)


class TestReorganizacaoDeDatasComPreservadasForaDaGrade(BasePosicao):
    """D2: só as futuras da grade são resequenciadas."""

    def test_preservada_fora_da_grade_mantem_data_e_nao_conta_para_o_termino(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "Clube", 100.0, "2027-01-10", "mensal", data_termino="2029-12",
        )
        agosto = ids[7]
        db.editar_conta_ocorrencia(agosto, valor=999.0)
        db.alterar_frequencia_serie(ids[1], "anual", data_termino="2029-12")

        # antes da Etapa 2b: False ("ultrapassaria o término")
        self.assertTrue(db.editar_conta_serie(ids[1], data_vencimento="2027-02-15"))

        self.assertEqual([(p, v) for _, _, p, v in self.posicoes(serie_id)], [
            ("2027-01-10", "2027-01-10"),
            ("2027-02-15", "2027-02-15"),
            ("2027-08-10", "2027-08-10"),
            ("2028-02-15", "2028-02-15"),
            ("2029-02-15", "2029-02-15"),
        ])
        self.assertEqual(self.serie(serie_id)["horizonte_gerado_ate"], "2029-02-15")
        self.assert_invariantes(serie_id)

    def test_nova_sequencia_pula_a_vaga_de_uma_preservada(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Clube", 100.0, "2027-01-10", "mensal")
        db.gerar_ocorrencias_sob_demanda(serie_id, "2028-12")
        agosto_2028 = self.id_por_data(serie_id, "2028-08-10")
        db.editar_conta_ocorrencia(agosto_2028, valor=999.0)
        db.alterar_frequencia_serie(ids[1], "anual")  # grade: fev/2028; agosto/2028 fica fora

        self.assertTrue(db.editar_conta_serie(ids[1], data_vencimento="2027-08-15"))

        self.assertEqual([p for _, _, p, _ in self.posicoes(serie_id)[1:]],
                         ["2027-08-15", "2028-08-10", "2029-08-15"])
        self.assert_sem_vaga_duplicada(serie_id)
        self.assert_invariantes(serie_id)


class TestTransformacaoERollback(BasePosicao):
    def test_transformar_em_recorrente_ancora_na_posicao_1(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-10-05")
        self.assertEqual(self.linha(conta_id)[1:3], (None, None))
        serie_id, novos = db.transformar_em_recorrente(conta_id, "mensal", data_termino="2027-01")
        self.assertEqual(self.posicoes(serie_id)[0], (conta_id, 1, "2026-10-05", "2026-10-05"))
        self.assertEqual([p for _, p, _, _ in self.posicoes(serie_id)], [1, 2, 3, 4])
        self.assertEqual(self.extra_serie(serie_id, "posicao_ancora"), 1)

    def test_falha_na_renumeracao_desfaz_a_alteracao_de_frequencia(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Clube", 100.0, "2027-01-10", "mensal")
        db.editar_conta_ocorrencia(ids[7], valor=999.0)
        antes = (self.posicoes(serie_id), self.serie(serie_id), self.extra_serie(serie_id, "posicao_ancora"))

        with mock.patch.object(db, "_renumerar_segmento", side_effect=RuntimeError("falha simulada")):
            with self.assertRaisesRegex(RuntimeError, "falha simulada"):
                db.alterar_frequencia_serie(ids[1], "anual")

        self.assertEqual((self.posicoes(serie_id), self.serie(serie_id),
                          self.extra_serie(serie_id, "posicao_ancora")), antes)

    def test_renumeracao_em_duas_fases_nao_colide_no_indice_unico(self):
        # inserir no meio do segmento exige deslocar posições já ocupadas
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Clube", 100.0, "2027-01-10", "mensal")
        db.gerar_ocorrencias_sob_demanda(serie_id, "2029-06")
        db.editar_conta_ocorrencia(self.id_por_data(serie_id, "2029-06-10"), valor=1.0)
        db.alterar_frequencia_serie(ids[0], "mensal")  # preservada distante no fim do segmento
        db.gerar_ocorrencias_sob_demanda(serie_id, "2029-12")  # novas vagas antes e depois dela
        self.assert_invariantes(serie_id)
        self.assert_sem_vaga_duplicada(serie_id)
        self.assertEqual(self.posicoes(serie_id)[-1][2], "2029-12-10")


class TestHorizonteNaExclusao(BasePosicao):
    """C1/C2: excluir uma ocorrência não mexe no horizonte da grade."""

    def test_exclusao_individual_com_preservada_distante_nao_salta_competencias(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 50.0, "2027-01-10", "mensal")
        db.gerar_ocorrencias_sob_demanda(serie_id, "2029-12")
        db.editar_conta_ocorrencia(self.id_por_data(serie_id, "2029-12-10"), valor=51.0)
        db.alterar_frequencia_serie(ids[1], "mensal")  # grade até 2028-02; dez/2029 preservada

        db.excluir_conta(self.id_por_data(serie_id, "2027-05-10"))

        self.assertEqual(self.serie(serie_id)["horizonte_gerado_ate"], "2028-02-10")
        db.gerar_ocorrencias_sob_demanda(serie_id, "2029-12")
        competencias = self.competencias_previstas(serie_id)
        meses = [f"{a}-{m:02d}" for a in (2027, 2028, 2029) for m in range(1, 13)]
        self.assertEqual([m for m in meses if competencias[m] != 1], ["2027-05"])  # só a excluída
        self.assert_invariantes(serie_id)

    def test_exclusao_da_propria_preservada_distante(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 50.0, "2027-01-10", "mensal")
        db.gerar_ocorrencias_sob_demanda(serie_id, "2029-12")
        distante = self.id_por_data(serie_id, "2029-12-10")
        db.editar_conta_ocorrencia(distante, valor=51.0)
        db.alterar_frequencia_serie(ids[1], "mensal")

        db.excluir_conta(distante)

        self.assertEqual(self.serie(serie_id)["horizonte_gerado_ate"], "2028-02-10")
        db.gerar_ocorrencias_sob_demanda(serie_id, "2029-12")
        self.assertEqual(self.competencias_previstas(serie_id)["2029-12"], 1)  # a vaga volta a ser da grade


class TestReorganizacaoComBlocoAntigo(BasePosicao):
    """C3: não editadas de um bloco antigo da grade são resequenciadas."""

    def test_mudanca_de_data_antes_da_ancora_resequencia_as_nao_editadas(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Plano", 50.0, "2027-01-10", "mensal")
        db.alterar_frequencia_serie(ids[5], "anual")  # âncora em jun/2027
        jan, fev, mar = (self.linha(c) for c in ids[:3])

        self.assertTrue(db.editar_conta_serie(ids[2], data_vencimento="2027-03-15"))

        self.assertEqual((self.linha(ids[0]), self.linha(ids[1])), (jan, fev))
        self.assertEqual([(p, v) for _, _, p, v in self.posicoes(serie_id)[2:]], [
            ("2027-03-15", "2027-03-15"),
            ("2028-03-15", "2028-03-15"),
            ("2029-03-15", "2029-03-15"),
            ("2030-03-15", "2030-03-15"),
            ("2031-03-15", "2031-03-15"),
        ])
        self.assert_sem_vaga_duplicada(serie_id)
        self.assert_invariantes(serie_id)

    def test_editada_do_bloco_antigo_fora_da_grade_continua_preservada(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Plano", 50.0, "2027-01-10", "mensal")
        db.editar_conta_ocorrencia(ids[3], valor=99.0)  # abril editado
        db.alterar_frequencia_serie(ids[5], "anual")

        self.assertTrue(db.editar_conta_serie(ids[2], data_vencimento="2027-03-15"))

        self.assertEqual(self.linha(ids[3])[2:5], ("2027-04-10", "2027-04-10", 99.0))
        self.assert_invariantes(serie_id)


class TestD5MesPosteriorAoDaParcelaAnterior(BasePosicao):
    """D5: mudança de vencimento com "Este mês em diante"."""

    def setUp(self):
        super().setUp()
        self.serie_id, self.ids = db.criar_serie_recorrente(
            self.usuario_id, "Escola", 700.0, "2027-01-10", "mensal", data_termino="2027-12",
        )

    def estado(self):
        return (self.consultar("SELECT * FROM contas ORDER BY id"),
                self.consultar("SELECT * FROM series_recorrencia ORDER BY id"))

    def assert_recusa(self, conta_id, **campos):
        antes = self.estado()
        with self.assertRaises(db.VencimentoAntesDaParcelaAnteriorError) as contexto:
            db.editar_conta_serie(conta_id, **campos)
        self.assertEqual(str(contexto.exception),
                         "Para alterar esta conta e as próximas, escolha um mês posterior ao da parcela anterior.")
        self.assertEqual(self.estado(), antes)

    def test_mes_igual_ao_da_parcela_anterior_e_recusado(self):
        self.assert_recusa(self.ids[3], data_vencimento="2027-03-25")

    def test_mes_anterior_ao_historico_e_recusado(self):
        self.assert_recusa(self.ids[3], data_vencimento="2026-11-05")

    def test_mes_seguinte_e_aceito(self):
        self.assertTrue(db.editar_conta_serie(self.ids[3], data_vencimento="2027-04-01"))
        self.assertEqual(self.linha(self.ids[3])[2:4], ("2027-04-01", "2027-04-01"))

    def test_primeira_ocorrencia_nao_tem_limite(self):
        self.assertTrue(db.editar_conta_serie(self.ids[0], data_vencimento="2026-06-01"))
        self.assertEqual(self.linha(self.ids[0])[2:4], ("2026-06-01", "2026-06-01"))
        self.assert_invariantes(self.serie_id)

    def test_compara_com_a_vaga_da_anterior_e_nao_com_o_vencimento_movido(self):
        mar, abr = self.ids[2], self.ids[3]
        db.editar_conta_ocorrencia(mar, data_vencimento="2027-05-20")  # vaga continua 2027-03
        self.assertTrue(db.editar_conta_serie(abr, data_vencimento="2027-04-05"))

    def test_anterior_movida_para_frente_nao_libera_o_mes_da_propria_vaga(self):
        fev, mar = self.ids[1], self.ids[2]
        db.editar_conta_ocorrencia(fev, data_vencimento="2026-12-01")  # vaga continua 2027-02
        self.assert_recusa(mar, data_vencimento="2027-02-20")

    def test_recusa_nao_grava_nenhum_campo_junto(self):
        categoria = self.criar_categoria(self.usuario_id, "Casa")
        self.assert_recusa(self.ids[3], valor=999.0, nome="Outra", categoria_id=categoria,
                           descricao="nova", data_vencimento="2027-02-01")

    def test_somente_este_mes_continua_livre(self):
        self.assertTrue(db.editar_conta_ocorrencia(self.ids[3], data_vencimento="2026-11-05"))
        self.assertEqual(self.linha(self.ids[3])[2:4], ("2027-04-10", "2026-11-05"))

    def test_serie_anual(self):
        serie_id, ids = db.criar_serie_recorrente(
            self.usuario_id, "IPVA", 500.0, "2027-02-10", "anual", data_termino="2030-12",
        )
        self.assert_recusa(ids[1], data_vencimento="2027-02-25")  # mesma competência da anterior
        self.assertTrue(db.editar_conta_serie(ids[1], data_vencimento="2027-12-10"))
        self.assertEqual([p for _, _, p, _ in self.posicoes(serie_id)],
                         ["2027-02-10", "2027-12-10", "2028-12-10", "2029-12-10"])
        self.assert_invariantes(serie_id)

    def test_data_nao_alterada_nao_e_verificada(self):
        # repetir a data atual (Etapa 0) não é mudança de vencimento
        self.assertTrue(db.editar_conta_serie(self.ids[3], valor=750.0, data_vencimento="2027-04-10"))


if __name__ == "__main__":
    unittest.main()
