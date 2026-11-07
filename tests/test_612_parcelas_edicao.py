"""
Sino 6.12 (experimental), Etapa 7 -- edição e exclusão de parcelas (camada de dados).

Parcelamento de base: R$ 1.200,00 em 6 parcelas de R$ 200,00, de 10/09/2026 a
10/02/2027 (hoje fixo: 15/09/2026). PROTEGIDA = registro de pagamento (ativo ou
estornado) ou quitação; EDITADA = editada individualmente; LIVRE = nenhuma das duas.
D5, D6/E5/R12, D7/C2/C3, C4/E4, P1, P4/C7, E6 e D14 (rollback integral).
"""

import unittest
from unittest import mock

from apoio_banco import TesteComBancoTemporario, db

import pagamentos


class BaseParcelas(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()
        self.serie_id, self.p = db.criar_conta_parcelada(self.usuario_id, "Sofá", 1200.0, 6, "2026-09-10")

    def proteger(self, conta, estornar=False):
        pagamentos.registrar_pagamento_parcial(conta, 50_00, "2026-09-12")
        if estornar:
            pagamentos.estornar_pagamento(
                self.consultar("SELECT id FROM pp_pagamentos WHERE conta_id = ? ORDER BY id DESC", (conta,))[0][0],
                (50_00, "2026-09-12"))

    def linhas(self):
        return self.consultar("SELECT id, data_vencimento, valor, editado_individualmente FROM contas "
                              "WHERE serie_id = ? ORDER BY posicao", (self.serie_id,))

    def valores(self):
        return [v for _, _, v, _ in self.linhas()]

    def datas(self):
        return [d for _, d, _, _ in self.linhas()]

    def estado(self):
        return {t: self.consultar(f"SELECT * FROM {t} ORDER BY 1")
                for t in ("contas", "series_recorrencia", "parcelamentos", "pp_pagamentos")}

    def identificacoes(self):
        return [(db.obter_identificacao(self.serie_id, i)["posicao"], db.obter_identificacao(self.serie_id, i)["total"])
                for i, *_ in self.linhas()]

    def valido(self):
        resultado = db.validar_schema_atual()
        self.assertTrue(resultado["ok"], resultado)


class TestEdicaoIndividual(BaseParcelas):
    def test_d5_valor_de_parcela_livre_muda_o_total_sem_redistribuir(self):
        self.assertTrue(db.editar_conta_ocorrencia(self.p[2], valor=250.0))
        self.assertEqual(self.valores(), [200.0, 200.0, 250.0, 200.0, 200.0, 200.0])
        self.assertEqual(db.situacao_das_parcelas(self.p[0])["total_centavos"], 1250_00)
        self.assertEqual(self.linhas()[2][3], 1)                          # editada individualmente
        self.assertEqual(self.consultar("SELECT valor_total_original_centavos FROM parcelamentos"), [(1200_00,)])
        self.valido()

    def test_protegida_nao_muda_valor_nem_vencimento(self):
        self.proteger(self.p[1])
        self.proteger(self.p[3], estornar=True)
        antes = self.estado()
        for conta in (self.p[1], self.p[3]):
            for campos in ({"valor": 300.0}, {"data_vencimento": "2026-10-20"}):
                with self.subTest(conta=conta, campos=campos):
                    with self.assertRaisesRegex(db.ParcelamentoRecusadoError, "registros de pagamento"):
                        db.editar_conta_ocorrencia(conta, **campos)
        self.assertEqual(self.estado(), antes)
        self.assertTrue(db.editar_conta_ocorrencia(self.p[1], nome="Sofá novo"))   # nome continua editável

    def test_c7_vencimento_individual_sem_colidir(self):
        antes = self.estado()
        with self.assertRaisesRegex(db.ParcelamentoRecusadoError, "outra parcela"):
            db.editar_conta_ocorrencia(self.p[3], data_vencimento="2027-01-05")   # mês da 5ª parcela
        self.assertEqual(self.estado(), antes)
        self.assertTrue(db.editar_conta_ocorrencia(self.p[3], data_vencimento="2026-12-31"))  # mesmo mês, outro dia
        self.assertEqual(self.datas()[3], "2026-12-31")


class TestAlterarParcelamento(BaseParcelas):
    def preparar_fixas(self):
        self.proteger(self.p[1])                                      # 2ª: com pagamento
        db.editar_conta_ocorrencia(self.p[2], valor=250.0)            # 3ª: editada

    def test_d6_novo_total_so_nas_livres(self):
        self.preparar_fixas()
        previa = db.previa_alteracao_parcelamento(self.p[0], novo_total=1500.0)
        self.assertEqual([p["situacao"] for p in previa["parcelas"]],
                         ["recalculada", "com_pagamentos", "editada", "recalculada", "recalculada", "recalculada"])
        self.assertEqual(self.valores(), [200.0, 200.0, 250.0, 200.0, 200.0, 200.0])   # a prévia não grava
        db.alterar_parcelamento(self.p[0], novo_total=1500.0)
        self.assertEqual(self.valores(), [262.5, 200.0, 250.0, 262.5, 262.5, 262.5])
        self.assertEqual(db.situacao_das_parcelas(self.p[0])["total_centavos"], 1500_00)
        self.assertEqual(pagamentos.obter_situacao(self.p[1])["pago_centavos"], 50_00)
        self.valido()

    def test_d3_centavos_na_primeira_livre(self):
        self.proteger(self.p[0])                                      # a 1ª é fixa: a diferença vai na 2ª
        db.alterar_parcelamento(self.p[3], novo_total=1000.0)
        self.assertEqual(self.valores(), [200.0, 160.0, 160.0, 160.0, 160.0, 160.0])
        db.alterar_parcelamento(self.p[3], novo_total=1000.01)
        self.assertEqual(self.valores(), [200.0, 160.01, 160.0, 160.0, 160.0, 160.0])

    def test_e5_aumentar_a_quantidade(self):
        self.preparar_fixas()
        db.alterar_parcelamento(self.p[0], nova_quantidade=8)          # mesmo total (1.250,00)
        self.assertEqual(self.datas()[-2:], ["2027-03-10", "2027-04-10"])
        # 1.250,00 - 450,00 (fixas) = 800,00 em 6 livres: 133,33 × 6 = 799,98; os 2 centavos vão na 1ª livre (D3).
        self.assertEqual(self.valores(), [133.35, 200.0, 250.0, 133.33, 133.33, 133.33, 133.33, 133.33])
        self.assertEqual(db.situacao_das_parcelas(self.p[0])["total_centavos"], 1250_00)
        self.assertEqual(self.identificacoes()[-1], (8, 8))
        self.assertEqual(self.consultar("SELECT data_termino FROM series_recorrencia WHERE id = ?", (self.serie_id,)),
                         [("2027-04",)])
        self.valido()

    def test_e5_reduzir_so_com_livres_no_fim(self):
        db.alterar_parcelamento(self.p[0], nova_quantidade=4, novo_total=1200.0)
        self.assertEqual(self.valores(), [300.0] * 4)
        self.assertEqual(self.consultar("SELECT data_termino FROM series_recorrencia WHERE id = ?", (self.serie_id,)),
                         [("2026-12",)])
        self.valido()

    def test_r12_reducao_que_exclui_fixa_e_recusada(self):
        for preparar in (lambda: db.editar_conta_ocorrencia(self.p[5], valor=210.0), lambda: self.proteger(self.p[4])):
            with self.subTest():
                self.setUp()
                preparar()
                antes = self.estado()
                with self.assertRaisesRegex(db.ParcelamentoRecusadoError, "reduzir a quantidade"):
                    db.alterar_parcelamento(self.p[0], nova_quantidade=4)
                self.assertEqual(self.estado(), antes)

    def test_r12_livres_insuficientes(self):
        self.preparar_fixas()
        antes = self.estado()
        with self.assertRaisesRegex(db.ParcelamentoRecusadoError, "parcelas livres"):
            db.alterar_parcelamento(self.p[0], novo_total=450.03)       # 0,03 para 4 livres
        with self.assertRaisesRegex(db.ParcelamentoRecusadoError, "parcelas livres"):
            db.alterar_parcelamento(self.p[0], novo_total=400.0)        # menos que as fixas
        self.assertEqual(self.estado(), antes)

    def test_sem_livres(self):
        for conta in self.p:
            db.editar_conta_ocorrencia(conta, valor=200.0 + 1)
        antes = self.estado()
        with self.assertRaises(db.ParcelamentoRecusadoError):
            db.alterar_parcelamento(self.p[0], novo_total=2000.0)
        db.alterar_parcelamento(self.p[0], novo_total=1206.0)           # igual ao total atual: nada a mudar
        self.assertEqual(self.estado(), antes)

    def test_recusas_de_entrada(self):
        antes = self.estado()
        for argumentos in ({"nova_quantidade": 1}, {"nova_quantidade": 37}, {"novo_total": 0},
                           {"novo_total": -3.0}, {"nova_quantidade": "6"}):
            with self.subTest(argumentos=argumentos):
                with self.assertRaises(db.ParcelamentoRecusadoError):
                    db.alterar_parcelamento(self.p[0], **argumentos)
        conta = db.criar_conta_unica(self.usuario_id, "Luz", 100.0, "2026-09-10")
        with self.assertRaisesRegex(db.ParcelamentoRecusadoError, "não é parcelada"):
            db.alterar_parcelamento(conta, novo_total=50.0)
        self.assertEqual(self.estado(), {**antes, "contas": self.consultar("SELECT * FROM contas ORDER BY 1")})

    def test_rollback_no_meio(self):
        antes = self.estado()
        with mock.patch.object(db, "_inserir_ocorrencia", side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                db.alterar_parcelamento(self.p[0], novo_total=1500.0, nova_quantidade=8)
        self.assertEqual(self.estado(), antes)


class TestExclusao(BaseParcelas):
    def test_d7_c2_c3_excluir_livre_renumera_sem_redistribuir(self):
        self.proteger(self.p[4])
        pagamento_antes = self.consultar("SELECT * FROM pp_pagamentos")
        self.assertTrue(db.excluir_conta(self.p[2]))
        self.assertEqual(self.valores(), [200.0] * 5)
        self.assertEqual(self.identificacoes(), [(i, 5) for i in range(1, 6)])
        self.assertEqual(db.obter_identificacao(self.serie_id, self.p[4]), {"tipo": "parcela", "posicao": 4, "total": 5})
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos"), pagamento_antes)   # identidade intacta
        self.assertEqual(db.situacao_das_parcelas(self.p[0])["total_centavos"], 1000_00)
        self.valido()

    def test_c4_e4_protegida_nao_e_excluida(self):
        self.proteger(self.p[1])
        self.proteger(self.p[3], estornar=True)
        antes = self.estado()
        for conta in (self.p[1], self.p[3]):
            with self.assertRaisesRegex(db.ParcelamentoRecusadoError, "não pode ser excluída"):
                db.excluir_conta(conta)
        self.assertEqual(self.estado(), antes)

    def test_p1_este_mes_em_diante(self):
        self.proteger(self.p[3])
        antes = self.estado()
        for conta in (self.p[0], self.p[3]):
            with self.assertRaisesRegex(db.ParcelamentoRecusadoError, "a partir desta"):
                db.excluir_conta_serie(conta)
        self.assertEqual(self.estado(), antes)
        self.assertTrue(db.excluir_conta_serie(self.p[4]))               # depois da protegida: permitido
        self.assertEqual(len(self.linhas()), 4)
        self.valido()

    def test_excluir_todas_as_livres_e_a_serie(self):
        self.assertTrue(db.excluir_conta_serie(self.p[0]))
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM parcelamentos"), [(0,)])
        self.valido()

    def test_recorrencia_continua_com_as_regras_da_6_11(self):
        _, mensais = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-05", "mensal")
        pagamentos.registrar_pagamento_parcial(mensais[0], 100_00, "2026-09-05")
        self.assertTrue(db.excluir_conta(mensais[0]))                    # 5.54: apaga a ocorrência e os pagamentos
        self.assertTrue(db.editar_conta_serie(mensais[1], valor=950.0))  # valor coletivo continua
        self.valido()


class TestEsteMesEmDiante(BaseParcelas):
    def test_valor_coletivo_recusado(self):
        antes = self.estado()
        with self.assertRaisesRegex(db.ParcelamentoRecusadoError, "Alterar parcelamento"):
            db.editar_conta_serie(self.p[2], valor=300.0)
        self.assertEqual(self.estado(), antes)

    def test_nome_categoria_e_descricao(self):
        categoria = self.criar_categoria(self.usuario_id, "Lazer")
        self.proteger(self.p[3])
        self.assertTrue(db.editar_conta_serie(self.p[2], nome="Sofá 3 lugares", categoria_id=categoria,
                                              descricao="Loja Y"))
        nomes = self.consultar("SELECT nome, categoria_id, descricao FROM contas WHERE serie_id = ? ORDER BY posicao",
                               (self.serie_id,))
        self.assertEqual(nomes[:2], [("Sofá", None, None)] * 2)
        self.assertEqual(nomes[2:], [("Sofá 3 lugares", categoria, "Loja Y")] * 4)
        self.assertEqual(self.consultar("SELECT nome FROM series_recorrencia WHERE id = ?", (self.serie_id,)),
                         [("Sofá 3 lugares",)])

    def test_p4_dia_novo_e_protegida_mantem_o_vencimento(self):
        self.proteger(self.p[1])
        self.assertTrue(db.editar_conta_serie(self.p[0], data_vencimento="2026-09-30"))
        self.assertEqual(self.datas(), ["2026-09-30", "2026-10-10", "2026-11-30", "2026-12-30", "2027-01-30",
                                        "2027-02-28"])
        self.assertEqual(self.consultar("SELECT data_termino FROM series_recorrencia WHERE id = ?", (self.serie_id,)),
                         [("2027-02",)])
        self.valido()

    def test_c7_mes_novo_recalcula_o_termino(self):
        self.assertTrue(db.editar_conta_serie(self.p[2], data_vencimento="2026-12-05"))
        self.assertEqual(self.datas(), ["2026-09-10", "2026-10-10", "2026-12-05", "2027-01-05", "2027-02-05",
                                        "2027-03-05"])
        self.assertEqual(self.consultar("SELECT data_termino FROM series_recorrencia WHERE id = ?", (self.serie_id,)),
                         [("2027-03",)])
        self.assertEqual(self.identificacoes(), [(i, 6) for i in range(1, 7)])
        self.valido()

    def test_e6_protegida_intercalada_recusa_e_desfaz_tudo(self):
        self.proteger(self.p[4])
        antes = self.estado()
        with self.assertRaisesRegex(db.ParcelamentoRecusadoError, "mantém o vencimento"):
            db.editar_conta_serie(self.p[1], data_vencimento="2026-11-10")   # as livres antes dela já tinham mudado
        self.assertEqual(self.estado(), antes)

    def test_selecionada_protegida_ou_antes_da_anterior(self):
        self.proteger(self.p[2])
        antes = self.estado()
        with self.assertRaisesRegex(db.ParcelamentoRecusadoError, "registros de pagamento"):
            db.editar_conta_serie(self.p[2], data_vencimento="2026-11-20")
        with self.assertRaises(db.VencimentoAntesDaParcelaAnteriorError):
            db.editar_conta_serie(self.p[3], data_vencimento="2026-11-25")
        self.assertEqual(self.estado(), antes)

    def test_parcelada_nao_e_tratada_como_recorrencia(self):
        # Numa recorrência (6.10, H2) a ocorrência com pagamento recebe o novo dia; na parcela, não (P4).
        _, mensais = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-10", "mensal",
                                               data_termino="2027-02")
        pagamentos.registrar_pagamento_parcial(mensais[1], 100_00, "2026-09-12")
        self.proteger(self.p[1])
        db.editar_conta_serie(mensais[0], data_vencimento="2026-09-25")
        db.editar_conta_serie(self.p[0], data_vencimento="2026-09-25")
        self.assertEqual(self.consultar("SELECT data_vencimento FROM contas WHERE id = ?", (mensais[1],)),
                         [("2026-10-25",)])
        self.assertEqual(self.consultar("SELECT data_vencimento FROM contas WHERE id = ?", (self.p[1],)),
                         [("2026-10-10",)])


if __name__ == "__main__":
    unittest.main()
