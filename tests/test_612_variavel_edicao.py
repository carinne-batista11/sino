"""
Sino 6.12 (experimental), Etapa 9 -- edição de recorrências variáveis (camada de dados).

Informar o valor de uma ocorrência pendente (R$ 0,00 é valor conhecido), R5 ("Este mês em
diante" numa variável: só a selecionada e o valor-modelo), R3 (Fixo -> Variável) e R4
(Variável -> Fixo) com o alcance da X3, Encerrar (R7) e exclusões com pendentes, atomicidade
e integridade da v11. Hoje fixo: 15/09/2026.
"""

import unittest
from unittest import mock

from apoio_banco import db

import pagamentos
from test_612_variavel import BaseVariavel, Interrupcao


class BaseEdicao(BaseVariavel):
    def criar(self, variavel=True, frequencia="mensal", inicio="2026-08-10", termino="2027-01", valor=150.0):
        return db.criar_serie_recorrente(self.usuario_id, "Luz", valor, inicio, frequencia, data_termino=termino,
                                         variavel=variavel)

    def linha(self, conta_id):
        return self.consultar("SELECT nome, valor, categoria_id, descricao, data_vencimento, status, data_pagamento, "
                              "editado_individualmente FROM contas WHERE id = ?", (conta_id,))[0]

    def pagamentos_registrados(self):
        return self.consultar("SELECT * FROM pp_pagamentos ORDER BY id")

    def estornar_unico(self, conta_id, centavos, data):
        pagamentos.registrar_pagamento_parcial(conta_id, centavos, data)
        p = pagamentos.obter_situacao(conta_id)["ativos"][0]
        pagamentos.estornar_pagamento(p["id"], (p["valor_centavos"], p["data_pagamento"]))

    def modelo(self, serie_id):
        return self.consultar("SELECT valor, frequencia FROM series_recorrencia WHERE id = ?", (serie_id,))[0]


class TestInformarValor(BaseEdicao):
    def setUp(self):
        super().setUp()
        self.casa = self.criar_categoria(self.usuario_id, "Casa")
        self.serie, self.ids = self.criar()
        db.editar_conta_ocorrencia(self.ids[2], categoria_id=self.casa, descricao="leitura de outubro")

    def test_informar_valor_preserva_o_resto(self):
        antes = self.linha(self.ids[2])
        self.assertTrue(db.editar_conta_ocorrencia(self.ids[2], valor=95.5))
        depois = self.linha(self.ids[2])
        self.assertEqual(depois[1], 95.5)
        self.assertEqual(depois[:1] + depois[2:], antes[:1] + antes[2:])          # nome, categoria, descrição...
        self.assertNotIn(self.ids[2], self.pendentes())
        self.assertEqual(self.pendentes(), set(self.ids[1:2] + self.ids[3:]))     # as outras continuam
        self.assertEqual(db.resumo_do_periodo(self.usuario_id, "2026-10-01", "2026-10-31"), (95.5, 0.0))
        self.assertEqual(db.pendentes_do_periodo(self.usuario_id, "2026-10-01", "2026-10-31"), 0)
        outubro = db.listar_contas(self.usuario_id, "2026-10")[0]
        self.assertFalse(outubro["valor_pendente"])
        self.assertFalse(pagamentos.obter_situacao(self.ids[2])["valor_pendente"])
        self.assert_banco_valido()

    def test_zero_e_valor_conhecido(self):
        db.editar_conta_ocorrencia(self.ids[2], valor=0.0)
        self.assertNotIn(self.ids[2], self.pendentes())
        outubro = db.listar_contas(self.usuario_id, "2026-10")[0]
        self.assertEqual(db.valor_conhecido(outubro), 0.0)
        self.assertEqual(db.totais_por_mes(self.usuario_id, "2026-10", "2026-10"), {"2026-10": 0.0})
        self.assertEqual(db.pendentes_por_mes(self.usuario_id, "2026-10", "2026-10"), {})
        # Pagamento: deixa de ser recusado por valor pendente; vale a regra de sempre (sem saldo, nada a pagar).
        self.assertFalse(db.marcar_conta_como_paga(self.ids[2]))
        self.assert_banco_valido()

    def test_zero_em_diante_na_pendente_nao_e_ignorado(self):
        self.assertTrue(db.editar_conta_serie(self.ids[1], valor=0.0))
        self.assertNotIn(self.ids[1], self.pendentes())
        self.assertEqual(self.linha(self.ids[1])[1], 0.0)

    def test_pagamentos_depois_de_informar(self):
        db.editar_conta_ocorrencia(self.ids[1], valor=120.0)
        situacao = pagamentos.registrar_pagamento_parcial(self.ids[1], 20_00, "2026-09-14")
        self.assertEqual(situacao["saldo_centavos"], 100_00)
        self.assertTrue(db.marcar_conta_como_paga(self.ids[1]))
        self.assertEqual(pagamentos.obter_situacao(self.ids[1])["status"], "pago")
        self.assert_banco_valido()

    def test_rollback_mantem_a_pendencia(self):
        antes = self.estado()
        with mock.patch.object(db, "_sincronizar_quitacao", side_effect=Interrupcao()), \
                self.assertRaises(Interrupcao):
            db.editar_conta_ocorrencia(self.ids[2], valor=95.5, nome="Energia")
        self.assertEqual(self.estado(), antes)
        self.assertIn(self.ids[2], self.pendentes())

    def test_avulsa_de_variavel_encerrada(self):
        db.encerrar_recorrencia(self.ids[1])                  # corte = hoje: agosto e setembro ficam, avulsas
        self.assertIn(self.ids[1], self.pendentes())
        self.assert_banco_valido()
        self.assertTrue(db.editar_conta_ocorrencia(self.ids[1], valor=88.0))
        self.assertNotIn(self.ids[1], self.pendentes())
        serie_nova, _ = db.transformar_em_recorrente(self.ids[1], "mensal", data_termino="2026-12")
        self.assertFalse(db.serie_variavel(serie_nova))
        self.assert_banco_valido()


class TestR5(BaseEdicao):
    def setUp(self):
        super().setUp()
        self.serie, self.ids = self.criar()
        pagamentos.registrar_pagamento_parcial(self.ids[0], 50_00, "2026-08-10")
        db.editar_conta_ocorrencia(self.ids[2], valor=130.0)              # outubro informado (editado)

    def test_so_a_selecionada_e_o_modelo(self):
        pagos = self.pagamentos_registrados()
        linhas = {i: self.linha(i) for i in self.ids}
        self.assertTrue(db.editar_conta_serie(self.ids[1], valor=200.0))
        self.assertEqual(self.linha(self.ids[1])[1], 200.0)
        self.assertEqual(self.linha(self.ids[1])[7], 0)                   # "Este mês em diante" não marca edição
        self.assertNotIn(self.ids[1], self.pendentes())
        for i in (self.ids[0], self.ids[2], *self.ids[3:]):
            self.assertEqual(self.linha(i), linhas[i])                    # futuros informados e pendentes intactos
        self.assertEqual(self.pendentes(), set(self.ids[3:]))
        self.assertEqual(self.modelo(self.serie), (200.0, "mensal"))
        self.assertEqual(self.pagamentos_registrados(), pagos)
        self.assert_banco_valido()

    def test_selecionada_com_pagamentos(self):
        pagos = self.pagamentos_registrados()
        self.assertTrue(db.editar_conta_serie(self.ids[0], valor=180.0))
        self.assertEqual([self.linha(i)[1] for i in self.ids], [180.0, 0.0, 130.0, 0.0, 0.0, 0.0])
        self.assertEqual(pagamentos.obter_situacao(self.ids[0])["saldo_centavos"], 130_00)
        self.assertEqual(self.pagamentos_registrados(), pagos)
        antes = self.estado()
        with self.assertRaises(db.ValorMenorQuePagoError):                 # regra financeira de sempre
            db.editar_conta_serie(self.ids[0], valor=40.0)
        self.assertEqual(self.estado(), antes)

    def test_novas_ocorrencias_continuam_pendentes(self):
        serie, ids = self.criar(termino=None)
        db.editar_conta_serie(ids[0], valor=210.0)
        novos = db.gerar_ocorrencias_sob_demanda(serie, "2028-03")
        self.assertTrue(novos and set(novos) <= self.pendentes())

    def test_anual(self):
        serie, ids = self.criar(frequencia="anual", inicio="2026-03-20", termino="2029-12", valor=900.0)
        db.editar_conta_serie(ids[1], valor=950.0)
        self.assertEqual([self.linha(i)[1] for i in ids], [900.0, 950.0, 0.0, 0.0])
        self.assertEqual(self.modelo(serie), (950.0, "anual"))

    def test_rollback(self):
        antes = self.estado()
        with mock.patch.object(db, "_informar_valor_no_cursor", side_effect=Interrupcao()), \
                self.assertRaises(Interrupcao):
            db.editar_conta_serie(self.ids[1], valor=200.0, nome="Energia")
        self.assertEqual(self.estado(), antes)


class TestR3FixoParaVariavel(BaseEdicao):
    def setUp(self):
        super().setUp()
        self.serie, self.ids = self.criar(variavel=False)                 # ago..jan, R$ 150,00
        db.marcar_conta_como_paga(self.ids[0], "2026-08-10")              # protegida (quitada)
        self.estornar_unico(self.ids[4], 10_00, "2026-09-14")              # protegida (só estorno)
        db.editar_conta_ocorrencia(self.ids[3], valor=999.0)              # editada

    def test_selecionada_mantem_seguintes_livres_ficam_pendentes(self):
        pagos = self.pagamentos_registrados()
        previa = db.previa_tornar_variavel(self.ids[2])
        self.assertEqual(previa, {"pendentes": [self.ids[5]], "mantidas": [self.ids[3], self.ids[4]]})
        self.assertEqual(db.tornar_variavel(self.ids[2]), [self.ids[5]])
        self.assertEqual([self.linha(i)[1] for i in self.ids], [150.0, 150.0, 150.0, 999.0, 150.0, 0.0])
        self.assertEqual(self.pendentes(), {self.ids[5]})
        self.assertTrue(db.serie_variavel(self.serie))
        self.assertEqual(self.modelo(self.serie), (150.0, "mensal"))        # frequência intacta
        self.assertEqual(self.pagamentos_registrados(), pagos)
        self.assert_banco_valido()

    def test_anteriores_nunca_mudam(self):
        db.tornar_variavel(self.ids[4])                                   # a selecionada é protegida
        self.assertEqual(self.pendentes(), {self.ids[5]})
        self.assertEqual([self.linha(i)[1] for i in self.ids[:5]], [150.0, 150.0, 150.0, 999.0, 150.0])

    def test_desde_a_primeira(self):
        db.tornar_variavel(self.ids[0])
        self.assertEqual(self.pendentes(), {self.ids[1], self.ids[2], self.ids[5]})
        self.assert_banco_valido()

    def test_anual_e_geracao_depois(self):
        serie, ids = self.criar(variavel=False, frequencia="anual", inicio="2026-03-20", termino=None, valor=900.0)
        db.tornar_variavel(ids[0])
        self.assertEqual(self.modelo(serie), (900.0, "anual"))
        novos = db.gerar_ocorrencias_sob_demanda(serie, "2030-12")
        self.assertTrue(novos and set(novos) <= self.pendentes())
        self.assert_banco_valido()

    def test_recusas(self):
        _, variavel = self.criar()
        _, parcelas = db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-10-05")
        unica = db.criar_conta_unica(self.usuario_id, "Água", 80.0, "2026-09-18")
        _, encerrada = self.criar(variavel=False, inicio="2026-10-10")
        db.encerrar_recorrencia(encerrada[0])
        antes = self.estado()
        for conta, mensagem in ((variavel[1], db.MENSAGEM_JA_VARIAVEL),
                                (parcelas[0], db.MENSAGEM_PARCELADA_NAO_MUDA_DE_TIPO),
                                (unica, db.MENSAGEM_SO_RECORRENCIA_ATIVA),
                                (encerrada[0], db.MENSAGEM_SO_RECORRENCIA_ATIVA)):
            with self.subTest(conta=conta):
                for funcao in (db.previa_tornar_variavel, db.tornar_variavel):
                    with self.assertRaises(db.ValorVariavelRecusadoError) as recusa:
                        funcao(conta)
                    self.assertEqual(str(recusa.exception), mensagem)
        self.assertEqual(self.estado(), antes)

    def test_rollback(self):
        antes = self.estado()
        original = db._marcar_valor_pendente

        def marcar_e_interromper(cursor, ids):
            original(cursor, ids)
            raise Interrupcao()

        with mock.patch.object(db, "_marcar_valor_pendente", marcar_e_interromper), self.assertRaises(Interrupcao):
            db.tornar_variavel(self.ids[1])
        self.assertEqual(self.estado(), antes)


class TestR4VariavelParaFixo(BaseEdicao):
    def setUp(self):
        super().setUp()
        self.serie, self.ids = self.criar()                               # ago (150) + set..jan pendentes
        pagamentos.registrar_pagamento_parcial(self.ids[0], 50_00, "2026-08-10")
        db.editar_conta_ocorrencia(self.ids[3], valor=130.0)              # novembro informado

    def test_preenche_selecionada_e_seguintes_pendentes(self):
        pagos = self.pagamentos_registrados()
        previa = db.previa_tornar_fixa(self.ids[1])
        self.assertEqual(previa, {"sugestao": 130.0, "preencher": [self.ids[1], self.ids[2], self.ids[4],
                                                                   self.ids[5]], "recusa": None})
        self.assertEqual(db.tornar_fixa(self.ids[1], 140.0), previa["preencher"])
        self.assertEqual([self.linha(i)[1] for i in self.ids], [150.0, 140.0, 140.0, 130.0, 140.0, 140.0])
        self.assertEqual(self.pendentes(), set())
        self.assertFalse(db.serie_variavel(self.serie))
        self.assertEqual(self.modelo(self.serie), (140.0, "mensal"))
        self.assertEqual(self.pagamentos_registrados(), pagos)
        self.assertEqual(self.linha(self.ids[3])[7], 1)                   # edição individual preservada
        self.assert_banco_valido()

    def test_selecionada_com_valor_mantem(self):
        db.editar_conta_ocorrencia(self.ids[1], valor=111.0)
        db.editar_conta_ocorrencia(self.ids[2], valor=112.0)
        db.tornar_fixa(self.ids[2], 140.0)
        self.assertEqual([self.linha(i)[1] for i in self.ids], [150.0, 111.0, 112.0, 130.0, 140.0, 140.0])
        self.assert_banco_valido()

    def test_pendentes_anteriores_recusam(self):
        self.assertEqual(db.previa_tornar_fixa(self.ids[4])["recusa"], db.MENSAGEM_PENDENTES_ANTERIORES)
        antes = self.estado()
        with self.assertRaises(db.ValorVariavelRecusadoError) as recusa:
            db.tornar_fixa(self.ids[4], 140.0)
        self.assertEqual(str(recusa.exception), db.MENSAGEM_PENDENTES_ANTERIORES)
        self.assertEqual(self.estado(), antes)

    def test_valor_obrigatorio_e_zero_aceito(self):
        antes = self.estado()
        for valor in (None, -1.0, "140", True):
            with self.subTest(valor=valor), self.assertRaises(db.ValorVariavelRecusadoError):
                db.tornar_fixa(self.ids[1], valor)
        self.assertEqual(self.estado(), antes)
        db.tornar_fixa(self.ids[1], 0.0)
        self.assertEqual(self.linha(self.ids[2])[1], 0.0)
        self.assert_banco_valido()

    def test_recusas(self):
        _, fixa = self.criar(variavel=False)
        antes = self.estado()
        with self.assertRaises(db.ValorVariavelRecusadoError) as recusa:
            db.tornar_fixa(fixa[0], 100.0)
        self.assertEqual(str(recusa.exception), db.MENSAGEM_JA_FIXA)
        db.encerrar_recorrencia(self.ids[3])
        with self.assertRaises(db.ValorVariavelRecusadoError) as recusa:
            db.tornar_fixa(self.ids[1], 100.0)
        self.assertEqual(str(recusa.exception), db.MENSAGEM_SO_RECORRENCIA_ATIVA)
        self.assertNotEqual(self.estado(), antes)                         # só o encerramento gravou

    def test_geracao_depois_copia_o_valor(self):
        serie, ids = self.criar(termino=None)
        db.tornar_fixa(ids[1], 175.0)
        novos = db.gerar_ocorrencias_sob_demanda(serie, "2028-03")
        self.assertEqual({self.linha(i)[1] for i in novos}, {175.0})
        self.assertEqual(self.pendentes() & set(ids + novos), set())

    def test_anual(self):
        serie, ids = self.criar(frequencia="anual", inicio="2026-03-20", termino="2029-12", valor=900.0)
        db.tornar_fixa(ids[1], 920.0)
        self.assertEqual([self.linha(i)[1] for i in ids], [900.0, 920.0, 920.0, 920.0])
        self.assertEqual(self.modelo(serie), (920.0, "anual"))

    def test_ida_e_volta_preserva_protegidas_e_editadas(self):
        db.tornar_fixa(self.ids[1], 140.0)
        db.tornar_variavel(self.ids[1])
        # a selecionada mantém; novembro (editada) mantém; as livres seguintes voltam a ficar pendentes
        self.assertEqual([self.linha(i)[1] for i in self.ids], [150.0, 140.0, 0.0, 130.0, 0.0, 0.0])
        self.assertEqual(self.pendentes(), {self.ids[2], self.ids[4], self.ids[5]})
        self.assert_banco_valido()

    def test_rollback_no_meio_do_preenchimento(self):
        antes = self.estado()
        original = db._informar_valor_no_cursor
        chamadas = []

        def informar_e_falhar(cursor, conta_id, valor):
            chamadas.append(conta_id)
            if len(chamadas) == 3:
                raise Interrupcao()
            original(cursor, conta_id, valor)

        with mock.patch.object(db, "_informar_valor_no_cursor", informar_e_falhar), self.assertRaises(Interrupcao):
            db.tornar_fixa(self.ids[1], 140.0)
        self.assertEqual(self.estado(), antes)


class TestEncerrarEExclusoes(BaseEdicao):
    def setUp(self):
        super().setUp()
        self.serie, self.ids = self.criar()
        pagamentos.registrar_pagamento_parcial(self.ids[0], 50_00, "2026-08-10")
        self.estornar_unico(self.ids[0], 10_00, "2026-08-11")

    def test_encerrar_preserva_pendentes_remanescentes(self):
        pagos = self.pagamentos_registrados()
        db.encerrar_recorrencia(self.ids[2])                  # outubro (futuro): fica até outubro
        restantes = [i for (i,) in self.consultar("SELECT id FROM contas WHERE serie_id = ? ORDER BY posicao",
                                                  (self.serie,))]
        self.assertEqual(restantes, self.ids[:3])
        self.assertEqual(self.pendentes(), {self.ids[1], self.ids[2]})
        self.assertEqual(self.pagamentos_registrados(), pagos)
        self.assertEqual(self.consultar("PRAGMA foreign_key_check"), [])
        self.assert_banco_valido()
        db.editar_conta_ocorrencia(self.ids[2], valor=77.0)           # informar depois
        self.assertEqual(self.pendentes(), {self.ids[1]})
        self.assert_banco_valido()

    def test_exclusoes_limpam_complementos_e_preservam_historico(self):
        pagos = self.pagamentos_registrados()
        db.excluir_conta(self.ids[5])
        db.excluir_conta_serie(self.ids[3])                   # novembro em diante
        self.assertEqual(self.pendentes(), {self.ids[1], self.ids[2]})
        self.assertEqual(self.pagamentos_registrados(), pagos)            # agosto (com pagamentos) intacto
        self.assertEqual(self.consultar("PRAGMA foreign_key_check"), [])
        self.assert_banco_valido()

    def test_excluir_serie_inteira(self):
        outra_serie, outra = self.criar(inicio="2026-10-01")
        db.excluir_conta_serie(outra[0])
        # A série excluída inteira deixa de ser variável (sem órfão); a outra continua.
        self.assertEqual(self.consultar("SELECT serie_id FROM series_valor_variavel"), [(self.serie,)])
        self.assertTrue(self.pendentes() <= set(self.ids))
        self.assert_banco_valido()


if __name__ == "__main__":
    unittest.main()
