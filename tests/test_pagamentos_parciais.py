"""
Pagamentos parciais (Sino 6.10) — contas comuns, camada de
banco: registro acumulativo em centavos, quitação pelo saldo, status,
isolamento entre ocorrências, compatibilidade com contas pagas sem registros,
totais (Início e Gráfico) e as operações recusadas enquanto as regras do
item 7 aguardam decisão.

Hoje fixo: 15/09/2026.
"""

from datetime import date
from unittest import mock

from apoio_banco import TesteComBancoTemporario, db

import pagamentos  # noqa: E402


class TestePagamentos(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def conta_unica(self, valor=400.0, vencimento="2026-09-20", nome="Internet"):
        db.criar_conta_unica(self.usuario_id, nome, valor, vencimento)
        return self.consultar("SELECT MAX(id) FROM contas")[0][0]

    def serie(self, valor=100.0, frequencia="mensal", vencimento="2026-09-10", termino=None):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Academia", valor, vencimento, frequencia,
                                                  data_termino=termino)
        return serie_id, ids

    def pagar(self, conta_id, centavos, data=None, saldo=None):
        return pagamentos.registrar_pagamento_parcial(conta_id, centavos, data, saldo)

    def linhas(self, conta_id):
        return self.consultar("SELECT valor_centavos, data_pagamento, tipo FROM pp_pagamentos "
                              "WHERE conta_id = ? ORDER BY id", (conta_id,))

    def status(self, conta_id):
        return self.consultar("SELECT status, data_pagamento FROM contas WHERE id = ?", (conta_id,))[0]


class TestRegistroAcumulativo(TestePagamentos):
    def test_exemplo_da_autora_400_150_100_e_marcar_como_paga(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 150_00, "2026-09-01")
        situacao = self.pagar(conta, 100_00, "2026-09-10")
        self.assertEqual((situacao["pago_centavos"], situacao["saldo_centavos"]), (250_00, 150_00))
        self.assertTrue(situacao["pago_parcialmente"])
        self.assertEqual(self.status(conta), ("pendente", None))

        self.assertTrue(db.marcar_conta_como_paga(conta))
        self.assertEqual(self.linhas(conta), [(150_00, "2026-09-01", "parcial"), (100_00, "2026-09-10", "parcial"),
                                              (150_00, "2026-09-15", "saldo")])
        self.assertEqual(self.status(conta), ("pago", "2026-09-15"))
        situacao = pagamentos.obter_situacao(conta)
        self.assertEqual((situacao["pago_centavos"], situacao["saldo_centavos"]), (400_00, 0))
        self.assertFalse(situacao["pago_parcialmente"])

    def test_marcar_como_paga_de_novo_nao_duplica(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 150_00)
        db.marcar_conta_como_paga(conta)
        self.assertFalse(db.marcar_conta_como_paga(conta))
        self.assertEqual(sum(v for v, _, _ in self.linhas(conta)), 400_00)

    def test_data_da_quitacao_e_a_do_pagamento_que_completou_o_valor(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 300_00, "2026-09-12")
        self.pagar(conta, 100_00, "2026-09-05")  # completou o valor, com data anterior
        self.assertEqual(self.status(conta), ("pago", "2026-09-05"))
        self.assertEqual(pagamentos.obter_situacao(conta)["saldo_centavos"], 0)

    def test_marcar_como_paga_sem_pagamentos_registra_pagamento_integral(self):
        conta = self.conta_unica(400.0)
        self.assertTrue(db.marcar_conta_como_paga(conta, "2026-09-14"))
        self.assertEqual(self.linhas(conta), [(400_00, "2026-09-14", "integral")])
        self.assertEqual(self.status(conta), ("pago", "2026-09-14"))
        situacao = pagamentos.obter_situacao(conta)
        self.assertEqual((situacao["pago_centavos"], situacao["saldo_centavos"]), (400_00, 0))
        self.assertEqual(situacao["ativos"][0]["rotulo"], "Pagamento integral")
        self.assertFalse(db.marcar_conta_como_paga(conta))  # sem duplicar
        self.assertEqual(len(self.linhas(conta)), 1)
        with self.assertRaises(db.PagamentosRegistradosError):  # desfazer é pela reversão
            db.marcar_conta_como_pendente(conta)
        pagamentos.desfazer_pagamentos(conta, "todos", [situacao["ativos"][0]["id"]])
        self.assertEqual(self.status(conta), ("pendente", None))
        self.assertEqual(self.consultar("SELECT valor_centavos, estornado_em FROM pp_pagamentos"),
                         [(400_00, "2026-09-15")])

    def test_centavos_exatos(self):
        conta = self.conta_unica(100.0)
        for _ in range(2):
            self.pagar(conta, 33_33)
        self.pagar(conta, 33_34)
        self.assertEqual(self.status(conta)[0], "pago")
        conta = self.conta_unica(0.3)
        self.pagar(conta, 10)
        self.pagar(conta, 20)
        self.assertEqual(self.status(conta)[0], "pago")

    def test_valor_digitado_em_centavos(self):
        casos = {"150": 150_00, "150,5": 150_50, "1.234,56": 1234_56, "R$ 99,90": 99_90, "1.234": 1234_00,
                 "0,01": 1, "0": None, "-5": None, "10,005": None, "abc": None, "": None, "NaN": None}
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(pagamentos.centavos_do_texto(texto), esperado)


class TestRecusas(TestePagamentos):
    def test_recusas_nao_gravam_nada(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 100_00)
        recusas = [
            (pagamentos.ValorDePagamentoInvalidoError, (0,)),
            (pagamentos.ValorDePagamentoInvalidoError, (-100,)),
            (pagamentos.ValorDePagamentoInvalidoError, (10.5,)),
            (pagamentos.PagamentoAcimaDoSaldoError, (300_01,)),
            (pagamentos.DataDePagamentoFuturaError, (10_00, "2026-09-16")),
            (pagamentos.SaldoDesatualizadoError, (10_00, None, 400_00)),
        ]
        for erro, argumentos in recusas:
            with self.subTest(erro=erro.__name__):
                with self.assertRaises(erro):
                    self.pagar(conta, *argumentos)
        self.assertEqual(self.linhas(conta), [(100_00, "2026-09-15", "parcial")])

    def test_saldo_esperado_impede_registro_duplicado(self):
        conta = self.conta_unica(400.0)
        saldo = pagamentos.obter_situacao(conta)["saldo_centavos"]
        self.pagar(conta, 150_00, saldo=saldo)
        with self.assertRaises(pagamentos.SaldoDesatualizadoError):
            self.pagar(conta, 150_00, saldo=saldo)  # mesmo clique repetido
        self.assertEqual(len(self.linhas(conta)), 1)

    def test_conta_paga_nao_recebe_pagamento(self):
        conta = self.conta_unica(400.0)
        db.marcar_conta_como_paga(conta)
        with self.assertRaises(pagamentos.ContaJaPagaError):
            self.pagar(conta, 1)
        with self.assertRaises(pagamentos.ContaNaoEncontradaError):
            self.pagar(99999, 1)


class TestStatus(TestePagamentos):
    def test_status_principal_continua_pendente_ou_atrasado(self):
        futura = self.conta_unica(400.0, "2026-09-20", "Futura")
        vencida = self.conta_unica(400.0, "2026-09-01", "Vencida")
        self.pagar(futura, 100_00)
        self.pagar(vencida, 100_00)
        contas = {c["nome"]: c for c in db.listar_contas(self.usuario_id, "2026-09")}
        self.assertEqual(contas["Futura"]["status"], "pendente")
        self.assertEqual(contas["Vencida"]["status"], "atrasado")
        self.assertTrue(contas["Vencida"]["pago_parcialmente"])
        self.assertEqual((contas["Vencida"]["total_pago"], contas["Vencida"]["saldo"]), (100.0, 300.0))
        atrasada = db.listar_contas_atrasadas(self.usuario_id)[0]
        self.assertEqual((atrasada["nome"], atrasada["saldo"]), ("Vencida", 300.0))
        self.assertEqual(pagamentos.obter_situacao(vencida)["status"], "atrasado")

    def test_conta_paga_legada_sem_registros(self):
        # Conta paga como na versão atual (só status/data), sem linhas inventadas.
        conta = self.conta_unica(400.0)
        self.executar("UPDATE contas SET status = 'pago', data_pagamento = '2026-08-30' WHERE id = ?", (conta,))
        situacao = pagamentos.obter_situacao(conta)
        self.assertEqual((situacao["pago_centavos"], situacao["saldo_centavos"]), (400_00, 0))
        self.assertTrue(situacao["paga_sem_registros"])
        self.assertEqual(situacao["pagamentos"], [])
        self.assertEqual(self.linhas(conta), [])
        listada = db.listar_contas(self.usuario_id, "2026-09")[0]
        self.assertEqual((listada["total_pago"], listada["saldo"], listada["pago_parcialmente"]), (400.0, 0.0, False))



class TestOcorrencias(TestePagamentos):
    def test_pagamento_nao_se_propaga_na_serie(self):
        serie_id, ids = self.serie(100.0, termino="2026-12")
        self.pagar(ids[1], 40_00)  # outubro, ocorrência futura
        db.marcar_conta_como_paga(ids[1])
        self.assertEqual(self.consultar("SELECT conta_id FROM pp_pagamentos GROUP BY conta_id"), [(ids[1],)])
        for outro in (ids[0], ids[2], ids[3]):
            self.assertEqual(self.status(outro), ("pendente", None))
            self.assertEqual(pagamentos.obter_situacao(outro)["pago_centavos"], 0)

    def test_geracao_sob_demanda_nao_herda_pagamentos(self):
        serie_id, ids = self.serie(100.0)
        self.pagar(ids[0], 30_00)
        db.gerar_ocorrencias_sob_demanda(serie_id, "2028-01")
        self.assertEqual(self.consultar("SELECT COUNT(DISTINCT conta_id) FROM pp_pagamentos"), [(1,)])

    def test_anual_e_parcelada(self):
        _, anual = self.serie(1200.0, "anual", "2026-09-10")
        _, parcelas = self.serie(250.0, "mensal", "2026-09-10", termino="2027-02")
        self.pagar(anual[0], 600_00)
        self.pagar(parcelas[2], 250_00)  # novembro quitado antecipadamente
        self.assertEqual(self.status(parcelas[2])[0], "pago")
        self.assertEqual([self.status(i)[0] for i in parcelas].count("pago"), 1)
        self.assertEqual(pagamentos.obter_situacao(anual[0])["saldo_centavos"], 600_00)
        self.assertEqual(pagamentos.obter_situacao(anual[1])["pago_centavos"], 0)


class TestTotais(TestePagamentos):
    def test_total_do_periodo_nao_e_reduzido_e_pago_inclui_parciais(self):
        a = self.conta_unica(400.0, "2026-09-20", "A")
        b = self.conta_unica(100.0, "2026-09-21", "B")
        self.conta_unica(50.0, "2026-09-22", "C")
        self.pagar(a, 250_00)
        db.marcar_conta_como_paga(b)
        self.assertEqual(db.resumo_do_periodo(self.usuario_id, "2026-09-01", "2026-09-30"), (550.0, 350.0))
        self.assertEqual(db.totais_por_mes(self.usuario_id, "2026-09", "2026-09"), {"2026-09": 550.0})
        self.assertEqual(db.totais_por_ano(self.usuario_id), [(2026, 550.0)])
        self.assertEqual(sum(i["total"] for i in db.gastos_por_categoria(self.usuario_id, "2026-09-01",
                                                                          "2026-09-30")), 550.0)


class TestOperacoesRecusadas(TestePagamentos):
    def assertRecusada(self, operacao, chamada):
        antes = (self.consultar("SELECT * FROM contas ORDER BY id"),
                 self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"),
                 self.consultar("SELECT * FROM series_recorrencia ORDER BY id"))
        with self.assertRaises(db.PagamentosRegistradosError) as contexto:
            chamada()
        self.assertEqual(contexto.exception.operacao, operacao)
        depois = (self.consultar("SELECT * FROM contas ORDER BY id"),
                  self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"),
                  self.consultar("SELECT * FROM series_recorrencia ORDER BY id"))
        self.assertEqual(antes, depois)

    def test_conta_com_pagamentos(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 150_00)
        # Etapa 4.2: em aberto com parciais não há data de quitação a alterar.
        self.assertRecusada("data", lambda: db.editar_data_pagamento(conta, "2026-09-01"))
        db.marcar_conta_como_paga(conta)
        self.assertRecusada("desmarcar", lambda: db.marcar_conta_como_pendente(conta))

    def test_encerrar_recorrencia_preserva_ocorrencia_com_pagamentos(self):
        serie_id, ids = self.serie(100.0)
        self.pagar(ids[3], 10_00)  # dezembro, além do corte
        resultado = db.encerrar_recorrencia(ids[0])
        restantes = [i for i, *_ in self.ocorrencias(serie_id)]
        self.assertIn(ids[3], restantes)
        self.assertNotIn(ids[2], restantes)
        self.assertEqual(resultado["ocorrencias_removidas"], len(ids) - 2)

    def test_excluir_usuario_apaga_os_pagamentos(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 150_00)
        outro = self.criar_usuario(email="outro@sino.com")
        db.criar_conta_unica(outro, "Luz", 80.0, "2026-09-20")
        conta_outro = self.consultar("SELECT MAX(id) FROM contas")[0][0]
        self.pagar(conta_outro, 10_00)
        db.excluir_usuario(db.conferir_senha_para_exclusao(self.usuario_id, "senha123"))
        self.assertEqual(self.consultar("SELECT conta_id FROM pp_pagamentos"), [(conta_outro,)])
        self.assertEqual(self.consultar("PRAGMA foreign_key_check"), [])


class TestBancoNovo(TestePagamentos):
    def test_schema_oficial_continua_valido(self):
        self.assertTrue(db.validar_schema_atual()["ok"])
        self.assertEqual(self.consultar("PRAGMA integrity_check"), [("ok",)])
        self.assertEqual(date(2026, 9, 15), db.date.today())


class TestReversao(TestePagamentos):
    """Desmarcar como paga com pagamentos registrados: estorno rastreável."""

    def quitar(self, vencimento="2026-09-20"):
        conta = self.conta_unica(400.0, vencimento)
        self.pagar(conta, 150_00, "2026-09-05")
        self.pagar(conta, 100_00, "2026-09-10")
        db.marcar_conta_como_paga(conta)
        return conta

    def ativos(self, conta):
        return [p["id"] for p in pagamentos.obter_situacao(conta)["ativos"]]

    def estornos(self, conta):
        return self.consultar("SELECT valor_centavos, data_pagamento, tipo, estornado_em FROM pp_pagamentos "
                              "WHERE conta_id = ? ORDER BY id", (conta,))

    def test_desfazer_ultimo(self):
        conta = self.quitar()
        previa = pagamentos.previa_da_reversao(pagamentos.obter_situacao(conta), "ultimo")
        self.assertEqual(previa, (150_00, 250_00, 150_00))
        situacao = pagamentos.desfazer_pagamentos(conta, "ultimo", self.ativos(conta))
        self.assertEqual((situacao["pago_centavos"], situacao["saldo_centavos"], situacao["status"]),
                         (250_00, 150_00, "pendente"))
        self.assertTrue(situacao["pago_parcialmente"])
        self.assertEqual(self.estornos(conta), [(150_00, "2026-09-05", "parcial", None),
                                                (100_00, "2026-09-10", "parcial", None),
                                                (150_00, "2026-09-15", "saldo", "2026-09-15")])
        self.assertEqual(self.status(conta), ("pendente", None))

    def test_desfazer_todos_conta_vencida_volta_atrasada(self):
        conta = self.quitar("2026-09-01")
        self.assertEqual(pagamentos.previa_da_reversao(pagamentos.obter_situacao(conta), "todos"),
                         (400_00, 0, 400_00))
        situacao = pagamentos.desfazer_pagamentos(conta, "todos", self.ativos(conta))
        self.assertEqual((situacao["pago_centavos"], situacao["status"]), (0, "atrasado"))
        self.assertFalse(situacao["pago_parcialmente"])
        self.assertEqual([e for *_, e in self.estornos(conta)], ["2026-09-15"] * 3)
        self.assertEqual(len(situacao["pagamentos"]), 3)  # continuam no histórico
        self.assertEqual(db.listar_contas_atrasadas(self.usuario_id)[0]["saldo"], 400.0)

    def test_reversao_repetida_e_recusada_sem_alterar_nada(self):
        conta = self.quitar()
        ids = self.ativos(conta)
        pagamentos.desfazer_pagamentos(conta, "ultimo", ids)
        antes = self.estornos(conta)
        for modo in ("ultimo", "todos"):
            with self.subTest(modo=modo), self.assertRaises(pagamentos.ReversaoDesatualizadaError):
                pagamentos.desfazer_pagamentos(conta, modo, ids)
        self.assertEqual(self.estornos(conta), antes)
        with self.assertRaises(pagamentos.ReversaoDesatualizadaError):  # já não está paga
            pagamentos.desfazer_pagamentos(conta, "ultimo", ids[:2])

    def test_ultimo_ativo_ignora_os_ja_estornados(self):
        conta = self.quitar()
        pagamentos.desfazer_pagamentos(conta, "ultimo", self.ativos(conta))   # estorna o saldo (id 3)
        self.pagar(conta, 150_00, "2026-09-14")                               # quita de novo (id 4)
        self.assertEqual(self.status(conta), ("pago", "2026-09-14"))
        ids = self.ativos(conta)
        self.assertEqual(len(ids), 3)
        situacao = pagamentos.desfazer_pagamentos(conta, "ultimo", ids)
        self.assertEqual(situacao["pago_centavos"], 250_00)
        self.assertEqual([e for *_, e in self.estornos(conta)], [None, None, "2026-09-15", "2026-09-15"])
        self.assertEqual(self.estornos(conta)[3][1], "2026-09-14")  # o novo, não o já estornado

    def test_ultimo_e_o_ultimo_lancado_nao_a_maior_data(self):
        # Etapa 4.1 (decisão da autora): ordem de lançamento, não a data informada.
        conta = self.conta_unica(400.0)
        self.pagar(conta, 150_00, "2026-09-12")
        self.pagar(conta, 250_00, "2026-09-02")  # lançado depois, com data anterior; quita
        self.assertEqual(self.status(conta), ("pago", "2026-09-02"))
        situacao = pagamentos.obter_situacao(conta)
        self.assertEqual(pagamentos.previa_da_reversao(situacao, "ultimo"), (250_00, 150_00, 250_00))
        situacao = pagamentos.desfazer_pagamentos(conta, "ultimo", self.ativos(conta))
        self.assertEqual((situacao["pago_centavos"], situacao["saldo_centavos"]), (150_00, 250_00))
        self.assertEqual([(d, e) for _, d, _, e in self.estornos(conta)],
                         [("2026-09-12", None), ("2026-09-02", "2026-09-15")])
        self.assertEqual(self.status(conta), ("pendente", None))

    def test_estornados_nao_contam_e_conta_pode_ser_quitada_de_novo(self):
        conta = self.quitar()
        pagamentos.desfazer_pagamentos(conta, "todos", self.ativos(conta))
        self.assertEqual(db.resumo_do_periodo(self.usuario_id, "2026-09-01", "2026-09-30"), (400.0, 0.0))
        self.assertEqual(pagamentos.obter_situacao(conta)["saldo_centavos"], 400_00)
        with self.assertRaises(pagamentos.PagamentoAcimaDoSaldoError):
            self.pagar(conta, 400_01)
        # requitação: um pagamento integral novo; os estornados ficam no histórico
        db.marcar_conta_como_paga(conta, "2026-09-14")
        self.assertEqual(self.estornos(conta)[-1], (400_00, "2026-09-14", "integral", None))
        self.assertEqual(len(self.estornos(conta)), 4)
        self.assertEqual(self.status(conta), ("pago", "2026-09-14"))
        # Etapa 4.2: editar_data_pagamento muda a data do pagamento que completou o valor (função do
        # banco mantida; desde a reorganização, etapa 2, a interface corrige a data pelo lápis).
        self.assertTrue(db.editar_data_pagamento(conta, "2026-09-13"))
        self.assertEqual(self.estornos(conta)[-1], (400_00, "2026-09-13", "integral", None))
        self.assertEqual(self.status(conta), ("pago", "2026-09-13"))

    def test_contas_sem_pagamentos_ativos_nao_tem_o_que_desfazer(self):
        legada = self.conta_unica(400.0)
        self.executar("UPDATE contas SET status = 'pago', data_pagamento = '2026-08-30' WHERE id = ?", (legada,))
        parcial = self.conta_unica(100.0)
        self.pagar(parcial, 10_00)
        for conta in (legada, parcial):
            with self.subTest(conta=conta), self.assertRaises(pagamentos.ReversaoDesatualizadaError):
                pagamentos.desfazer_pagamentos(conta, "todos", self.ativos(conta))
        db.marcar_conta_como_pendente(legada)  # paga antes da 6.10 (legado): desmarcar de sempre
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM pp_pagamentos WHERE conta_id = ?", (legada,)),
                         [(0,)])
        self.assertEqual(pagamentos.obter_situacao(legada)["saldo_centavos"], 400_00)

    def test_so_a_ocorrencia_selecionada(self):
        serie_id, ids = self.serie(100.0, termino="2027-01")
        for conta in ids[:3]:
            self.pagar(conta, 40_00)
            db.marcar_conta_como_paga(conta)
        pagamentos.desfazer_pagamentos(ids[1], "todos", self.ativos(ids[1]))
        self.assertEqual([self.status(i)[0] for i in ids[:4]], ["pago", "pendente", "pago", "pendente"])
        self.assertEqual(self.consultar("SELECT conta_id FROM pp_pagamentos WHERE estornado_em IS NOT NULL "
                                        "GROUP BY conta_id"), [(ids[1],)])
        _, anual = self.serie(1200.0, "anual")
        self.pagar(anual[0], 1200_00)
        pagamentos.desfazer_pagamentos(anual[0], "todos", self.ativos(anual[0]))
        self.assertEqual(pagamentos.obter_situacao(anual[1])["pagamentos"], [])

    def test_encerrar_recorrencia_preserva_historico_estornado(self):
        serie_id, ids = self.serie(100.0)
        self.pagar(ids[3], 100_00)
        pagamentos.desfazer_pagamentos(ids[3], "todos", self.ativos(ids[3]))
        db.encerrar_recorrencia(ids[0])  # não apaga a ocorrência com histórico (nem falha na FK)
        self.assertIn(ids[3], [i for i, *_ in self.ocorrencias(serie_id)])



class TestValorDaConta(TestePagamentos):
    """Editar o valor: nunca abaixo da soma dos pagamentos ativos."""

    def com_pagos(self, pago=250_00, valor=400.0, vencimento="2026-09-20"):
        conta = self.conta_unica(valor, vencimento)
        self.pagar(conta, 150_00, "2026-09-05")
        if pago > 150_00:
            self.pagar(conta, pago - 150_00, "2026-09-10")
        return conta

    def situacao(self, conta):
        s = pagamentos.obter_situacao(conta)
        return s["pago_centavos"], s["saldo_centavos"], s["status"]

    def test_exemplos_da_autora(self):
        for novo, saldo, status in ((500.0, 250_00, "pendente"), (300.0, 50_00, "pendente"),
                                    (250.0, 0, "pago")):
            with self.subTest(novo=novo):
                conta = self.com_pagos()
                self.assertTrue(db.editar_conta_ocorrencia(conta, valor=novo))
                self.assertEqual(self.situacao(conta), (250_00, saldo, status))
                self.assertEqual(len(self.linhas(conta)), 2)  # pagamentos preservados
        conta = self.com_pagos()
        with self.assertRaises(db.ValorMenorQuePagoError) as contexto:
            db.editar_conta_ocorrencia(conta, valor=200.0)
        self.assertEqual(contexto.exception.titulo, "O valor informado é menor que o total já pago.")
        self.assertEqual(str(contexto.exception), "Esta conta possui R$ 250,00 em pagamentos registrados. "
                                                  "Informe um valor igual ou superior a R$ 250,00 para continuar.")
        self.assertEqual(self.consultar("SELECT valor FROM contas WHERE id = ?", (conta,)), [(400.0,)])

    def test_reduzir_ate_o_pago_quita_com_a_data_do_ultimo_pagamento(self):
        conta = self.com_pagos()
        db.editar_conta_ocorrencia(conta, valor=250.0)
        self.assertEqual(self.status(conta), ("pago", "2026-09-10"))

    def test_aumentar_valor_de_conta_quitada_volta_a_pendente_ou_atrasada(self):
        conta = self.com_pagos(400_00)
        self.assertEqual(self.status(conta), ("pago", "2026-09-10"))
        db.editar_conta_ocorrencia(conta, valor=450.0)
        self.assertEqual(self.status(conta), ("pendente", None))
        self.assertEqual(self.situacao(conta), (400_00, 50_00, "pendente"))
        vencida = self.com_pagos(400_00, vencimento="2026-09-01")
        db.editar_conta_ocorrencia(vencida, valor=401.0)
        self.assertEqual(self.situacao(vencida), (400_00, 1_00, "atrasado"))

    def test_outros_campos_preservam_pagamentos_e_status(self):
        conta = self.com_pagos(400_00)
        db.editar_conta_ocorrencia(conta, nome="Internet fibra", data_vencimento="2026-09-25", descricao="Novo")
        self.assertEqual(self.status(conta), ("pago", "2026-09-10"))
        self.assertEqual(len(self.linhas(conta)), 2)

    def test_conta_paga_legada_segue_o_comportamento_de_sempre(self):
        conta = self.conta_unica(400.0)
        self.executar("UPDATE contas SET status = 'pago', data_pagamento = '2026-09-14' WHERE id = ?", (conta,))
        db.editar_conta_ocorrencia(conta, valor=100.0)
        self.assertEqual(self.status(conta), ("pago", "2026-09-14"))
        self.assertEqual(self.situacao(conta), (100_00, 0, "pago"))

    def test_estornados_nao_limitam_o_valor(self):
        conta = self.com_pagos(400_00)
        pagamentos.desfazer_pagamentos(conta, "ultimo", [p["id"] for p in pagamentos.obter_situacao(conta)["ativos"]])
        self.assertTrue(db.editar_conta_ocorrencia(conta, valor=150.0))
        self.assertEqual(self.situacao(conta), (150_00, 0, "pago"))

    def test_este_mes_em_diante(self):
        serie_id, ids = self.serie(100.0, termino="2027-02")
        self.pagar(ids[2], 80_00)                 # novembro, parcial
        self.pagar(ids[3], 70_00)                 # dezembro, parcial
        # Opção D: as ocorrências com pagamentos mantêm o valor; só a selecionada é conferida.
        self.assertTrue(db.editar_conta_serie(ids[0], valor=75.0))
        self.assertEqual(self.consultar("SELECT valor FROM contas WHERE serie_id = ? ORDER BY posicao",
                                        (serie_id,)), [(75.0,), (75.0,), (100.0,), (100.0,), (75.0,), (75.0,)])
        self.assertEqual(self.situacao(ids[2]), (80_00, 20_00, "pendente"))
        self.assertEqual(self.situacao(ids[3]), (70_00, 30_00, "pendente"))
        self.pagar(ids[1], 50_00)
        with self.assertRaises(db.ValorMenorQuePagoError):  # a selecionada abaixo do que ela já pagou
            db.editar_conta_serie(ids[1], valor=40.0)
        self.assertTrue(db.editar_conta_ocorrencia(ids[2], valor=80.0))       # somente este mês
        self.assertEqual(self.situacao(ids[2]), (80_00, 0, "pago"))

class TestPagamentoIndividual(TestePagamentos):
    """Editar e desfazer UM pagamento, na conta parcial ou quitada."""

    def com_dois(self, vencimento="2026-09-20"):
        conta = self.conta_unica(400.0, vencimento)
        self.pagar(conta, 150_00, "2026-09-05")
        self.pagar(conta, 100_00, "2026-09-10")
        p1, p2 = [p["id"] for p in pagamentos.obter_situacao(conta)["ativos"]]
        return conta, p1, p2

    def situacao(self, conta):
        s = pagamentos.obter_situacao(conta)
        return s["pago_centavos"], s["saldo_centavos"], s["status"]

    def test_editar_valor_e_data_no_proprio_registro(self):
        conta, p1, _ = self.com_dois()
        pagamentos.editar_pagamento(p1, 100_00, "2026-09-03", (150_00, "2026-09-05"))
        self.assertEqual(self.linhas(conta), [(100_00, "2026-09-03", "parcial"), (100_00, "2026-09-10", "parcial")])
        self.assertEqual(self.situacao(conta), (200_00, 200_00, "pendente"))
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM pp_pagamentos"), [(2,)])  # sem versões

    def test_editar_ate_quitar_e_depois_reabrir(self):
        conta, p1, p2 = self.com_dois()
        pagamentos.editar_pagamento(p2, 250_00, "2026-09-12", (100_00, "2026-09-10"))
        self.assertEqual(self.status(conta), ("pago", "2026-09-12"))
        pagamentos.editar_pagamento(p2, 200_00, "2026-09-12", (250_00, "2026-09-12"))
        self.assertEqual(self.status(conta), ("pendente", None))
        self.assertEqual(self.situacao(conta), (350_00, 50_00, "pendente"))

    def test_editar_a_data_muda_a_data_da_quitacao(self):
        conta, p1, p2 = self.com_dois()
        db.marcar_conta_como_paga(conta)
        saldo = pagamentos.obter_situacao(conta)["ativos"][-1]
        pagamentos.editar_pagamento(saldo["id"], saldo["valor_centavos"], "2026-09-11",
                                    (saldo["valor_centavos"], saldo["data_pagamento"]))
        self.assertEqual(self.status(conta), ("pago", "2026-09-11"))

    def test_recusas_ao_editar(self):
        conta, p1, p2 = self.com_dois()
        antes = self.linhas(conta)
        recusas = [
            (pagamentos.ValorDePagamentoInvalidoError, (p1, 0, "2026-09-05", (150_00, "2026-09-05"))),
            (pagamentos.ValorDePagamentoInvalidoError, (p1, 10.5, "2026-09-05", (150_00, "2026-09-05"))),
            (pagamentos.PagamentosAcimaDoValorError, (p1, 300_01, "2026-09-05", (150_00, "2026-09-05"))),
            (pagamentos.DataDePagamentoFuturaError, (p1, 100_00, "2026-09-16", (150_00, "2026-09-05"))),
            (pagamentos.PagamentoDesatualizadoError, (p1, 100_00, "2026-09-05", (140_00, "2026-09-05"))),
            (pagamentos.PagamentoDesatualizadoError, (99999, 100_00, "2026-09-05", (150_00, "2026-09-05"))),
        ]
        for erro, argumentos in recusas:
            with self.subTest(erro=erro.__name__), self.assertRaises(erro):
                pagamentos.editar_pagamento(*argumentos)
        pagamentos.editar_pagamento(p1, 300_00, "2026-09-05", (150_00, "2026-09-05"))  # limite exato
        self.assertEqual(self.situacao(conta), (400_00, 0, "pago"))
        self.assertNotEqual(antes, self.linhas(conta))

    def test_estornar_pagamento_de_conta_parcial(self):
        conta, p1, p2 = self.com_dois()
        situacao = pagamentos.estornar_pagamento(p2, (100_00, "2026-09-10"))
        self.assertEqual((situacao["pago_centavos"], situacao["saldo_centavos"]), (150_00, 250_00))
        self.assertEqual(self.consultar("SELECT estornado_em FROM pp_pagamentos WHERE id = ?", (p2,)),
                         [("2026-09-15",)])
        with self.assertRaises(pagamentos.PagamentoDesatualizadoError):  # duas vezes, não
            pagamentos.estornar_pagamento(p2, (100_00, "2026-09-10"))
        with self.assertRaises(pagamentos.PagamentoDesatualizadoError):  # estornado não se edita
            pagamentos.editar_pagamento(p2, 50_00, "2026-09-10", (100_00, "2026-09-10"))
        self.assertEqual(db.resumo_do_periodo(self.usuario_id, "2026-09-01", "2026-09-30"), (400.0, 150.0))

    def test_estornar_pagamento_intermediario_de_conta_quitada(self):
        conta, p1, p2 = self.com_dois("2026-09-01")
        db.marcar_conta_como_paga(conta)
        pagamentos.estornar_pagamento(p2, (100_00, "2026-09-10"))
        self.assertEqual(self.situacao(conta), (300_00, 100_00, "atrasado"))
        self.assertEqual(self.status(conta), ("pendente", None))
        self.assertEqual([e for (e,) in self.consultar("SELECT estornado_em FROM pp_pagamentos ORDER BY id")],
                         [None, "2026-09-15", None])
        # "Desmarcar" segue valendo depois de quitar de novo
        db.marcar_conta_como_paga(conta)
        ativos = [p["id"] for p in pagamentos.obter_situacao(conta)["ativos"]]
        pagamentos.desfazer_pagamentos(conta, "todos", ativos)
        self.assertEqual(self.situacao(conta), (0, 400_00, "atrasado"))

    def test_estornar_o_unico_pagamento_ativo_reabre_a_conta(self):
        conta = self.conta_unica(100.0)
        self.pagar(conta, 100_00, "2026-09-02")
        p = pagamentos.obter_situacao(conta)["ativos"][0]
        pagamentos.estornar_pagamento(p["id"], (100_00, "2026-09-02"))
        self.assertEqual(self.status(conta), ("pendente", None))


class TestExclusaoDeContas(TestePagamentos):
    def total(self):
        return db.resumo_do_periodo(self.usuario_id, "2026-09-01", "2026-09-30")

    def test_excluir_contas_em_qualquer_situacao_de_pagamento(self):
        parcial = self.conta_unica(400.0, nome="Parcial")
        self.pagar(parcial, 150_00)
        quitada = self.conta_unica(300.0, nome="Quitada")
        self.pagar(quitada, 100_00)
        db.marcar_conta_como_paga(quitada)
        direta = self.conta_unica(50.0, nome="Direta")
        db.marcar_conta_como_paga(direta)
        estornada = self.conta_unica(80.0, nome="Estornada")
        self.pagar(estornada, 80_00)
        pagamentos.desfazer_pagamentos(estornada, "todos",
                                       [p["id"] for p in pagamentos.obter_situacao(estornada)["ativos"]])
        fica = self.conta_unica(20.0, nome="Fica")
        self.pagar(fica, 5_00)
        self.assertEqual(self.total(), (850.0, 505.0))

        self.assertTrue(db.excluir_conta(parcial))       # -400 de despesa, -150 de pago, -250 pendente
        self.assertEqual(self.total(), (450.0, 355.0))
        for conta in (quitada, direta, estornada):
            self.assertTrue(db.excluir_conta(conta))
        self.assertEqual(self.total(), (20.0, 5.0))
        self.assertEqual(self.consultar("SELECT conta_id FROM pp_pagamentos"), [(fica,)])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM pp_pagamentos WHERE conta_id NOT IN "
                                        "(SELECT id FROM contas)"), [(0,)])
        self.assertEqual(self.consultar("PRAGMA foreign_key_check"), [])

    def test_series_somente_este_mes_e_este_mes_em_diante(self):
        serie_id, ids = self.serie(100.0, termino="2027-02")
        for conta in ids[:4]:
            self.pagar(conta, 40_00)
        db.marcar_conta_como_paga(ids[3])
        self.assertTrue(db.excluir_conta(ids[1]))           # somente este mês
        self.assertTrue(db.excluir_conta_serie(ids[2]))     # este mês em diante
        self.assertEqual([i for i, *_ in self.ocorrencias(serie_id)], [ids[0]])
        self.assertEqual(self.consultar("SELECT conta_id FROM pp_pagamentos"), [(ids[0],)])
        self.assertEqual(self.consultar("SELECT data_termino FROM series_recorrencia WHERE id = ?", (serie_id,)),
                         [("2027-02",)])
        _, parcelas = self.serie(250.0, termino="2026-12")
        self.pagar(parcelas[0], 250_00)
        self.assertTrue(db.excluir_conta_serie(parcelas[0]))  # a série inteira
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM pp_pagamentos WHERE conta_id IN (?, ?, ?, ?)",
                                        tuple(parcelas)), [(0,)])
        self.assertEqual(self.consultar("PRAGMA foreign_key_check"), [])


class TestAvisoDeVencimento(TestePagamentos):
    def test_proximas_trazem_o_saldo(self):
        conta = self.conta_unica(400.0, "2026-09-18")
        self.pagar(conta, 300_00)
        proxima = db.listar_contas_proximas(self.usuario_id)[0]
        self.assertEqual((proxima["valor"], proxima["saldo"]), (400.0, 100.0))
        db.marcar_conta_como_paga(conta)
        self.assertEqual(db.listar_contas_proximas(self.usuario_id), [])


class TestEtapa4Diferenca(TestePagamentos):
    """Aumentar o valor de conta quitada: registrar a diferença ou deixá-la em aberto."""

    def quitada(self, vencimento="2026-09-20"):
        conta = self.conta_unica(400.0, vencimento)
        db.marcar_conta_como_paga(conta, "2026-09-10")
        return conta

    def situacao(self, conta):
        s = pagamentos.obter_situacao(conta)
        return s["pago_centavos"], s["saldo_centavos"], s["status"]

    def test_registrar_a_diferenca_como_paga(self):
        conta = self.quitada()
        db.editar_conta_ocorrencia(conta, valor=450.0, pp_diferenca={"registrar": True, "esperado": (400_00, 400_00)})
        self.assertEqual(self.linhas(conta), [(400_00, "2026-09-10", "integral"), (50_00, "2026-09-15", "saldo")])
        self.assertEqual(self.situacao(conta), (450_00, 0, "pago"))
        self.assertEqual(self.status(conta), ("pago", "2026-09-15"))

    def test_manter_a_diferenca_em_aberto(self):
        for vencimento, status in (("2026-09-20", "pendente"), ("2026-09-01", "atrasado")):
            with self.subTest(vencimento=vencimento):
                conta = self.quitada(vencimento)
                db.editar_conta_ocorrencia(conta, valor=450.0,
                                           pp_diferenca={"registrar": False, "esperado": (400_00, 400_00)})
                self.assertEqual(self.linhas(conta), [(400_00, "2026-09-10", "integral")])
                self.assertEqual(self.situacao(conta), (400_00, 50_00, status))

    def test_confirmacao_repetida_ou_desatualizada_nao_grava(self):
        conta = self.quitada()
        escolha = {"registrar": True, "esperado": (400_00, 400_00)}
        db.editar_conta_ocorrencia(conta, valor=450.0, pp_diferenca=escolha)
        antes = (self.linhas(conta), self.consultar("SELECT valor, status FROM contas"))
        with self.assertRaises(db.DadosDesatualizadosError):
            db.editar_conta_ocorrencia(conta, valor=500.0, pp_diferenca=escolha)  # mesma escolha de novo
        self.assertEqual((self.linhas(conta), self.consultar("SELECT valor, status FROM contas")), antes)

    def test_alteracao_e_pagamento_sao_atomicos(self):
        conta = self.quitada()
        with mock.patch.object(db, "_sincronizar_quitacao", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                db.editar_conta_ocorrencia(conta, valor=450.0,
                                           pp_diferenca={"registrar": True, "esperado": (400_00, 400_00)})
        self.assertEqual(self.consultar("SELECT valor, status FROM contas"), [(400.0, "pago")])
        self.assertEqual(self.linhas(conta), [(400_00, "2026-09-10", "integral")])

    def test_valor_igual_ou_menor(self):
        conta = self.quitada()
        self.assertTrue(db.editar_conta_ocorrencia(conta, valor=400.0))  # igual: nada muda
        self.assertEqual(self.situacao(conta), (400_00, 0, "pago"))
        with self.assertRaises(db.ValorMenorQuePagoError):
            db.editar_conta_ocorrencia(conta, valor=399.99)

    def test_este_mes_em_diante_aplica_a_escolha_so_na_selecionada(self):
        serie_id, ids = self.serie(100.0, termino="2026-12")
        db.marcar_conta_como_paga(ids[1], "2026-09-12")  # outubro, quitada (a selecionada)
        self.pagar(ids[2], 60_00, "2026-09-12")          # novembro, parcial: protegida (opção D)
        db.editar_conta_serie(ids[1], valor=130.0, pp_diferenca={"registrar": True, "esperado": (100_00, 100_00)})
        self.assertEqual(self.situacao(ids[1]), (130_00, 0, "pago"))
        self.assertEqual(self.situacao(ids[2]), (60_00, 40_00, "pendente"))  # valor original, sem pagamento novo
        self.assertEqual(self.consultar("SELECT valor FROM contas WHERE id = ?", (ids[3],)), [(130.0,)])
        self.assertEqual(self.situacao(ids[0])[:2], (0, 100_00))

class TestEtapa4DataDaQuitacao(TestePagamentos):
    def ativos(self, conta):
        return pagamentos.obter_situacao(conta)["ativos"]

    def editar(self, p, valor=None, data=None):
        return pagamentos.editar_pagamento(p["id"], valor or p["valor_centavos"], data or p["data_pagamento"],
                                           (p["valor_centavos"], p["data_pagamento"]))

    def test_exemplo_da_autora_e_edicoes(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 150_00, "2026-09-05")
        self.pagar(conta, 100_00, "2026-09-10")
        self.pagar(conta, 150_00, "2026-09-12")
        self.assertEqual(self.status(conta), ("pago", "2026-09-12"))
        p1, p2, p3 = sorted(self.ativos(conta), key=lambda p: p["id"])
        self.editar(p3, data="2026-09-14")                      # o que completou: muda a data da conta
        self.assertEqual(self.status(conta), ("pago", "2026-09-14"))
        self.editar(p1, data="2026-09-13")                      # um anterior: a data da conta não muda
        self.assertEqual(self.status(conta), ("pago", "2026-09-14"))

    def test_estorno_do_que_completou_e_requitacao(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 250_00, "2026-09-05")
        db.marcar_conta_como_paga(conta, "2026-09-10")
        saldo = max(self.ativos(conta), key=lambda p: p["id"])
        pagamentos.estornar_pagamento(saldo["id"], (saldo["valor_centavos"], saldo["data_pagamento"]))
        self.assertEqual(self.status(conta), ("pendente", None))      # data do estorno nunca vira quitação
        self.pagar(conta, 150_00, "2026-09-08")
        self.assertEqual(self.status(conta), ("pago", "2026-09-08"))  # o novo que completou

    def test_quitar_editando_um_pagamento_anterior(self):
        # Caso registrado nas notas: quem "completa" é o último na ordem de registro.
        conta = self.conta_unica(400.0)
        self.pagar(conta, 150_00, "2026-09-05")
        self.pagar(conta, 100_00, "2026-09-10")
        p1 = min(self.ativos(conta), key=lambda p: p["id"])
        self.editar(p1, valor=300_00)
        self.assertEqual(self.status(conta), ("pago", "2026-09-10"))


class TestEtapa4Frequencia(TestePagamentos):
    def competencias(self, serie_id):
        return [d[:7] for _, d, *_ in self.ocorrencias(serie_id)]

    def test_preserva_ocorrencias_com_pagamentos_sem_duplicar(self):
        serie_id, ids = self.serie(100.0, termino="2027-02")       # set/2026 a fev/2027
        self.pagar(ids[2], 40_00, "2026-09-10")                      # novembro, parcial
        db.marcar_conta_como_paga(ids[3], "2026-09-11")              # dezembro, quitada
        outra, outras = self.serie(50.0, termino="2026-12")
        antes_outra = self.ocorrencias(outra)
        pagos_antes = self.consultar("SELECT * FROM pp_pagamentos ORDER BY id")
        self.assertEqual([o["id"] for o in db.ocorrencias_futuras_com_pagamentos(ids[0])], [ids[2], ids[3]])

        resultado = db.alterar_frequencia_serie(ids[0], "anual")
        self.assertEqual(set(resultado["ocorrencias_preservadas"]), {ids[2], ids[3]})
        self.assertEqual(self.competencias(serie_id), ["2026-09", "2026-11", "2026-12", "2027-09"])
        competencias = self.competencias(serie_id)
        self.assertEqual(len(competencias), len(set(competencias)))   # nenhuma cobrança duplicada
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"), pagos_antes)
        self.assertEqual((pagamentos.obter_situacao(ids[2])["pago_centavos"], self.status(ids[3])),
                         (40_00, ("pago", "2026-09-11")))
        self.assertEqual(self.ocorrencias(outra), antes_outra)       # série não relacionada
        self.assertEqual(self.consultar("PRAGMA foreign_key_check"), [])

    def test_anual_para_mensal_nao_cria_outra_cobranca_no_mes_preservado(self):
        serie_id, ids = self.serie(1200.0, "anual", "2026-09-10")    # set/2026 e set/2027
        self.pagar(ids[1], 100_00, "2026-09-12")                     # setembro/2027, antecipado
        db.alterar_frequencia_serie(ids[0], "mensal", data_termino="2027-10")
        competencias = self.competencias(serie_id)
        self.assertEqual(competencias.count("2027-09"), 1)
        self.assertIn("2027-10", competencias)
        self.assertEqual(len(competencias), len(set(competencias)))
        self.assertIn(ids[1], [i for i, *_ in self.ocorrencias(serie_id)])

    def test_sem_pagamentos_continua_como_antes(self):
        serie_id, ids = self.serie(100.0, termino="2027-02")
        resultado = db.alterar_frequencia_serie(ids[0], "anual")
        self.assertEqual(resultado["ocorrencias_preservadas"], [])
        self.assertEqual(self.competencias(serie_id), ["2026-09", "2027-09"])

    def test_falha_nao_grava_nada(self):
        serie_id, ids = self.serie(100.0, termino="2027-02")
        self.pagar(ids[2], 40_00)
        antes = self.ocorrencias(serie_id)
        with mock.patch.object(db, "_renumerar_segmento", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                db.alterar_frequencia_serie(ids[0], "anual")
        self.assertEqual(self.ocorrencias(serie_id), antes)


class TestEtapa41OpcaoD(TestePagamentos):
    """"Este mês em diante" preserva o valor das ocorrências com histórico de pagamentos."""

    def valores(self, serie_id):
        return [v for (v,) in self.consultar("SELECT valor FROM contas WHERE serie_id = ? ORDER BY posicao",
                                             (serie_id,))]

    def academia(self):
        # set/2026 a mar/2027 (7 ocorrências)
        serie_id, ids = self.serie(100.0, termino="2027-03")
        self.pagar(ids[2], 40_00, "2026-09-05")                          # novembro: parcial
        db.marcar_conta_como_paga(ids[3], "2026-09-06")                  # dezembro: quitada
        self.pagar(ids[5], 100_00, "2026-09-07")                         # fevereiro: só estornado
        p = pagamentos.obter_situacao(ids[5])["ativos"][0]
        pagamentos.estornar_pagamento(p["id"], (p["valor_centavos"], p["data_pagamento"]))
        return serie_id, ids

    def test_exemplo_da_autora(self):
        serie_id, ids = self.academia()
        outra, outras = self.serie(50.0, termino="2026-12")
        antes = {
            "ids": [i for i, *_ in self.ocorrencias(serie_id)],
            "pagamentos": self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"),
            "outra": self.ocorrencias(outra),
            "situacoes": {i: pagamentos.obter_situacao(i) for i in (ids[2], ids[3], ids[5])},
        }
        self.assertEqual([d[:7] for d in db.ocorrencias_protegidas_no_valor(ids[1])], ["2026-11", "2026-12", "2027-02"])
        self.assertTrue(db.editar_conta_serie(ids[1], valor=130.0))   # outubro em diante
        self.assertEqual(self.valores(serie_id), [100.0, 130.0, 100.0, 100.0, 130.0, 100.0, 130.0])
        self.assertEqual(self.consultar("SELECT valor FROM series_recorrencia WHERE id = ?", (serie_id,)),
                         [(130.0,)])                                    # modelo das próximas geradas
        self.assertEqual([i for i, *_ in self.ocorrencias(serie_id)], antes["ids"])     # mesmos ids
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"), antes["pagamentos"])
        for i in (ids[2], ids[3], ids[5]):
            self.assertEqual(pagamentos.obter_situacao(i), antes["situacoes"][i])  # saldo, status, histórico
        self.assertEqual(self.ocorrencias(outra), antes["outra"])
        competencias = [d[:7] for _, d, *_ in self.ocorrencias(serie_id)]
        self.assertEqual(len(competencias), len(set(competencias)))

    def test_sem_pagamentos_todas_recebem_o_valor(self):
        serie_id, ids = self.serie(100.0, termino="2027-01")
        self.assertEqual(db.ocorrencias_protegidas_no_valor(ids[0]), [])
        db.editar_conta_serie(ids[0], valor=130.0)
        self.assertEqual(self.valores(serie_id), [130.0] * 5)

    def test_meses_anteriores_nao_mudam(self):
        serie_id, ids = self.academia()
        db.editar_conta_serie(ids[4], valor=150.0)          # janeiro em diante
        self.assertEqual(self.valores(serie_id), [100.0, 100.0, 100.0, 100.0, 150.0, 100.0, 150.0])

    def test_quitada_nao_e_reaberta_nem_paga_de_novo(self):
        serie_id, ids = self.academia()
        db.editar_conta_serie(ids[0], valor=130.0)
        self.assertEqual(self.status(ids[3]), ("pago", "2026-09-06"))
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM pp_pagamentos WHERE conta_id = ?", (ids[3],)), [(1,)])

    def test_falha_nao_deixa_alteracao_parcial(self):
        serie_id, ids = self.academia()
        antes = (self.valores(serie_id), self.consultar("SELECT nome FROM contas WHERE serie_id = ?", (serie_id,)))
        with mock.patch.object(db, "_sincronizar_quitacao", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                db.editar_conta_serie(ids[1], valor=130.0, nome="Academia nova")
        self.assertEqual((self.valores(serie_id),
                          self.consultar("SELECT nome FROM contas WHERE serie_id = ?", (serie_id,))), antes)

    def test_outros_campos_continuam_indo_para_todas(self):
        serie_id, ids = self.academia()
        db.editar_conta_serie(ids[1], valor=130.0, nome="Academia nova")
        self.assertEqual({n for (n,) in self.consultar("SELECT nome FROM contas WHERE serie_id = ? AND posicao >= ?",
                                                       (serie_id, 2))}, {"Academia nova"})

    def test_compativel_com_a_mudanca_de_frequencia(self):
        serie_id, ids = self.academia()
        db.editar_conta_serie(ids[1], valor=130.0)
        resultado = db.alterar_frequencia_serie(ids[1], "anual")
        self.assertEqual(set(resultado["ocorrencias_preservadas"]), {ids[2], ids[3], ids[5]})
        competencias = [d[:7] for _, d, *_ in self.ocorrencias(serie_id)]
        self.assertEqual(len(competencias), len(set(competencias)))


class TestEtapa41UltimoLancado(TestePagamentos):
    def ativos(self, conta):
        return [p["id"] for p in pagamentos.obter_situacao(conta)["ativos"]]

    def lancar(self, conta, *pares):
        for valor, data in pares:
            self.pagar(conta, valor, data)

    def test_estornos_sucessivos_seguem_a_ordem_de_lancamento(self):
        conta = self.conta_unica(400.0)
        self.lancar(conta, (100_00, "2026-09-10"), (100_00, "2026-09-01"), (200_00, "2026-09-05"))
        ids = sorted(self.ativos(conta))
        pagamentos.desfazer_pagamentos(conta, "ultimo", self.ativos(conta))            # estorna o 3º lançado
        self.pagar(conta, 200_00, "2026-09-03")                                         # requita (4º)
        pagamentos.desfazer_pagamentos(conta, "ultimo", self.ativos(conta))             # estorna o 4º
        estornados = [i for (i,) in self.consultar("SELECT id FROM pp_pagamentos WHERE estornado_em IS NOT NULL "
                                                   "ORDER BY id")]
        self.assertEqual(estornados[0], ids[2])
        self.assertEqual(len(estornados), 2)
        self.assertEqual(sorted(self.ativos(conta)), ids[:2])

    def test_edicao_nao_muda_a_posicao(self):
        conta = self.conta_unica(400.0)
        self.lancar(conta, (150_00, "2026-09-05"), (100_00, "2026-09-06"))
        p1 = min(pagamentos.obter_situacao(conta)["ativos"], key=lambda p: p["id"])
        pagamentos.editar_pagamento(p1["id"], 300_00, "2026-09-14", (150_00, "2026-09-05"))  # quita editando o 1º
        situacao = pagamentos.obter_situacao(conta)
        self.assertEqual(pagamentos.previa_da_reversao(situacao, "ultimo")[0], 100_00)  # continua sendo o 2º
        pagamentos.desfazer_pagamentos(conta, "ultimo", self.ativos(conta))
        self.assertEqual(self.consultar("SELECT valor_centavos FROM pp_pagamentos WHERE estornado_em IS NOT NULL"),
                         [(100_00,)])

    def test_datas_iguais_e_estornados_anteriores(self):
        conta = self.conta_unica(300.0)
        self.lancar(conta, (100_00, "2026-09-10"), (100_00, "2026-09-10"))
        primeiro, segundo = sorted(self.ativos(conta))
        pagamentos.estornar_pagamento(segundo, (100_00, "2026-09-10"))           # já estornado
        self.lancar(conta, (100_00, "2026-09-10"), (100_00, "2026-09-10"))       # 3º e 4º, mesma data; quita
        terceiro, quarto = sorted(set(self.ativos(conta)) - {primeiro})
        self.assertEqual(self.status(conta), ("pago", "2026-09-10"))
        pagamentos.desfazer_pagamentos(conta, "ultimo", self.ativos(conta))
        self.assertEqual(self.consultar("SELECT id FROM pp_pagamentos WHERE estornado_em IS NOT NULL ORDER BY id"),
                         [(segundo,), (quarto,)])
        self.assertEqual(db.listar_contas(self.usuario_id, "2026-09")[0]["total_pago"], 200.0)

    def test_desfazer_todos_continua(self):
        conta = self.conta_unica(400.0)
        self.lancar(conta, (150_00, "2026-09-12"), (250_00, "2026-09-02"))
        pagamentos.desfazer_pagamentos(conta, "todos", self.ativos(conta))
        self.assertEqual(pagamentos.obter_situacao(conta)["pago_centavos"], 0)
        self.assertEqual(len(pagamentos.obter_situacao(conta)["pagamentos"]), 2)


class TestEtapa42AlterarDataDePagamento(TestePagamentos):
    def test_muda_a_data_do_pagamento_que_quitou(self):
        conta = self.conta_unica(100.0)
        db.marcar_conta_como_paga(conta, "2026-09-14")
        self.assertTrue(db.editar_data_pagamento(conta, "2026-09-12"))
        self.assertEqual(self.linhas(conta), [(100_00, "2026-09-12", "integral")])  # sem pagamento novo
        self.assertEqual(self.status(conta), ("pago", "2026-09-12"))
        situacao = pagamentos.obter_situacao(conta)
        self.assertEqual((situacao["pago_centavos"], situacao["saldo_centavos"]), (100_00, 0))

    def test_varios_pagamentos_so_o_que_completou_muda(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 150_00, "2026-09-12")
        self.pagar(conta, 250_00, "2026-09-02")  # lançado por último: completou o valor
        self.assertTrue(db.editar_data_pagamento(conta, "2026-09-05"))
        self.assertEqual(self.linhas(conta), [(150_00, "2026-09-12", "parcial"), (250_00, "2026-09-05", "parcial")])
        self.assertEqual(self.status(conta), ("pago", "2026-09-05"))

    def test_data_futura_e_conta_paga_legada(self):
        conta = self.conta_unica(100.0)
        db.marcar_conta_como_paga(conta, "2026-09-14")
        self.assertFalse(db.editar_data_pagamento(conta, "2026-09-16"))
        self.assertEqual(self.linhas(conta), [(100_00, "2026-09-14", "integral")])
        legada = self.conta_unica(50.0)
        self.executar("UPDATE contas SET status = 'pago', data_pagamento = '2026-09-01' WHERE id = ?", (legada,))
        self.assertTrue(db.editar_data_pagamento(legada, "2026-09-03"))
        self.assertEqual(self.status(legada), ("pago", "2026-09-03"))
        self.assertEqual(self.linhas(legada), [])


class TestReversaoDaEdicao(TestePagamentos):
    """Etapa 4.2, estorno pedido em Editar conta: conferido pelos próprios pagamentos
    (id, valor, data), não pelo status -- o mesmo Salvar pode ter reaberto a conta ao
    aumentar o valor. Detalhes continua exigindo a conta quitada."""

    def quitada(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 200_00, "2026-09-10")
        self.pagar(conta, 200_00, "2026-09-02")   # lançado depois, com data anterior
        return conta

    def esperados(self, conta):
        return pagamentos.pagamentos_da_escolha(pagamentos.obter_situacao(conta))

    def ativos(self, conta):
        return self.consultar("SELECT id FROM pp_pagamentos WHERE conta_id = ? AND estornado_em IS NULL "
                              "ORDER BY id", (conta,))

    def test_escolha_guarda_id_valor_e_data_na_ordem_da_situacao(self):
        conta = self.quitada()
        self.assertEqual(self.esperados(conta), [(2, 200_00, "2026-09-02"), (1, 200_00, "2026-09-10")])

    def test_conta_reaberta_pelo_valor_estorna_os_mesmos_pagamentos(self):
        conta = self.quitada()
        esperados = self.esperados(conta)
        db.editar_conta_ocorrencia(conta, valor=500.0)                     # o Salvar grava o valor antes
        self.assertEqual(self.status(conta), ("pendente", None))
        situacao = pagamentos.desfazer_pagamentos(conta, "todos", [p[0] for p in esperados],
                                                  pagamentos_esperados=esperados)
        self.assertEqual((situacao["pago_centavos"], situacao["saldo_centavos"]), (0, 500_00))
        self.assertEqual(self.ativos(conta), [])
        self.assertEqual(len(situacao["pagamentos"]), 2)                   # nada apagado

    def test_ultimo_e_o_ultimo_lancado(self):
        conta = self.quitada()
        esperados = self.esperados(conta)
        db.editar_conta_ocorrencia(conta, valor=500.0)
        situacao = pagamentos.desfazer_pagamentos(conta, "ultimo", [p[0] for p in esperados],
                                                  pagamentos_esperados=esperados)
        self.assertEqual(self.ativos(conta), [(1,)])                       # id 2 (data menor) estornado
        self.assertEqual((situacao["pago_centavos"], situacao["saldo_centavos"], situacao["status"]),
                         (200_00, 300_00, "pendente"))

    def test_pagamento_alterado_por_fora_e_recusado_sem_gravar(self):
        conta = self.quitada()
        esperados = self.esperados(conta)
        pagamentos.editar_pagamento(1, 200_00, "2026-09-01", (200_00, "2026-09-10"))   # mesmo id, outra data
        for modo in ("ultimo", "todos"):
            with self.assertRaises(pagamentos.ReversaoDesatualizadaError):
                pagamentos.desfazer_pagamentos(conta, modo, [p[0] for p in esperados],
                                               pagamentos_esperados=esperados)
        with self.assertRaises(pagamentos.ReversaoDesatualizadaError):
            pagamentos.conferir_reversao_da_edicao(conta, esperados)
        self.assertEqual(len(self.ativos(conta)), 2)
        self.assertEqual(self.status(conta)[0], "pago")

    def test_pagamento_a_mais_ou_a_menos_e_recusado(self):
        conta = self.quitada()
        esperados = self.esperados(conta)
        db.editar_conta_ocorrencia(conta, valor=500.0)
        self.pagar(conta, 50_00, "2026-09-12")                             # um a mais
        with self.assertRaises(pagamentos.ReversaoDesatualizadaError):
            pagamentos.desfazer_pagamentos(conta, "todos", [p[0] for p in esperados],
                                           pagamentos_esperados=esperados)
        self.assertEqual(len(self.ativos(conta)), 3)
        with self.assertRaises(pagamentos.ReversaoDesatualizadaError):    # um a menos
            pagamentos.desfazer_pagamentos(conta, "todos", [p[0] for p in esperados[:1]],
                                           pagamentos_esperados=esperados[:1])

    def test_conferencia_previa_exige_conta_quitada_e_nao_grava(self):
        conta = self.quitada()
        esperados = self.esperados(conta)
        pagamentos.conferir_reversao_da_edicao(conta, esperados)          # vale: nada a dizer
        self.assertEqual(len(self.ativos(conta)), 2)
        db.editar_conta_ocorrencia(conta, valor=500.0)
        with self.assertRaises(pagamentos.ReversaoDesatualizadaError):    # antes de gravar, só quitada
            pagamentos.conferir_reversao_da_edicao(conta, esperados)
        with self.assertRaises(pagamentos.ReversaoDesatualizadaError):
            pagamentos.conferir_reversao_da_edicao(conta, [])

    def test_detalhes_continua_exigindo_conta_quitada(self):
        conta = self.quitada()
        ids = [p[0] for p in self.esperados(conta)]
        db.editar_conta_ocorrencia(conta, valor=500.0)
        for modo in ("ultimo", "todos"):
            with self.assertRaises(pagamentos.ReversaoDesatualizadaError):
                pagamentos.desfazer_pagamentos(conta, modo, ids)
        self.assertEqual(len(self.ativos(conta)), 2)

    def test_estornado_antes_fica_como_estava(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 150_00, "2026-09-02")
        antigo = self.pagar(conta, 100_00, "2026-09-05")["ativos"][-1]
        pagamentos.estornar_pagamento(antigo["id"], (100_00, "2026-09-05"))
        estornado_em = self.consultar("SELECT estornado_em FROM pp_pagamentos WHERE id = ?", (antigo["id"],))
        self.pagar(conta, 250_00, "2026-09-10")
        esperados = self.esperados(conta)
        self.assertEqual([p[0] for p in esperados], [1, 3])
        pagamentos.desfazer_pagamentos(conta, "todos", [1, 3], pagamentos_esperados=esperados)
        self.assertEqual(self.ativos(conta), [])
        self.assertEqual(self.consultar("SELECT estornado_em FROM pp_pagamentos WHERE id = ?", (antigo["id"],)),
                         estornado_em)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM pp_pagamentos")[0][0], 3)


class TestSimplificacaoDoHistorico(TestePagamentos):
    """Simplificação da proteção do histórico (etapa 1, 28/10; substitui a
    alternativa C). A proteção das ocorrências nas operações coletivas da
    recorrência depende SÓ dos registros que existem em pp_pagamentos (ativos
    ou estornados). Excluir definitivamente o último estornado tira a proteção;
    não há marca permanente. A edição individual protege por conta própria. A
    tabela antiga da marca não existe no schema v10.
    Hoje fixo: 15/09/2026."""

    TABELA_ANTIGA = "pp_contas_com_historico"

    def estornar(self, pid):
        valor, data = self.consultar("SELECT valor_centavos, data_pagamento FROM pp_pagamentos WHERE id = ?",
                                     (pid,))[0]
        pagamentos.estornar_pagamento(pid, (valor, data))

    def ids(self, conta):
        return [i for (i,) in self.consultar("SELECT id FROM pp_pagamentos WHERE conta_id = ? ORDER BY id", (conta,))]

    def financeiro(self, conta):
        s = pagamentos.obter_situacao(conta)
        return (s["valor_centavos"], s["pago_centavos"], s["saldo_centavos"], s["status"], s["data_pagamento"],
                [(p["id"], p["valor_centavos"], p["data_pagamento"]) for p in s["ativos"]],
                [(p["id"], p["valor_centavos"]) for p in s["pagamentos"] if p.get("estornado_em")],
                pagamentos.pagamento_que_quitou(s))

    def protegida(self, conta):
        conexao = db.conectar()
        try:
            return db._contas_com_pagamentos(conexao.cursor(), "id = ?", (conta,)) == [conta]
        finally:
            conexao.close()

    def tabela_antiga_existe(self):
        return bool(self.consultar("SELECT 1 FROM sqlite_master WHERE name = ?", (self.TABELA_ANTIGA,)))

    def conteudo(self):
        """Tudo o que importa no banco, para comparar antes e depois da migração."""
        return {t: self.consultar(f"SELECT * FROM {t} ORDER BY 1")
                for t in ("usuarios", "categorias", "series_recorrencia", "contas", "pp_pagamentos")}

    def conta_com_estornados(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 150_00, "2026-09-05")
        self.pagar(conta, 100_00, "2026-09-08")
        self.pagar(conta, 50_00, "2026-09-10")
        p1, p2, p3 = self.ids(conta)
        self.estornar(p2)
        self.estornar(p3)
        return conta, p1, p2, p3

    def serie_nov(self, preparar=None):
        """Série set/2026-fev/2027 (dia 20); novembro (intermediária, ids[2]) preparada por `preparar`."""
        serie_id, ids = self.serie(100.0, vencimento="2026-09-20", termino="2027-02")
        if preparar is not None:
            preparar(ids[2])
        return serie_id, ids

    def valores(self, serie_id):
        return [v for (v,) in self.consultar("SELECT valor FROM contas WHERE serie_id = ? ORDER BY posicao",
                                             (serie_id,))]

    def so_estornado(self, conta, excluir):
        self.pagar(conta, 30_00, "2026-09-06")
        pid = self.ids(conta)[-1]
        self.estornar(pid)
        if excluir:
            pagamentos.excluir_estornado(pid, conta)

    # --------------------------------------------- 1-7: a regra em cada situação
    def test_situacoes_de_pagamento_e_protecao(self):
        casos = {}
        casos["nunca_pagou"] = self.conta_unica(100.0, nome="A")
        casos["parcial_ativo"] = self.conta_unica(100.0, nome="B")
        self.pagar(casos["parcial_ativo"], 40_00, "2026-09-05")
        casos["quitada"] = self.conta_unica(100.0, nome="C")
        db.marcar_conta_como_paga(casos["quitada"], "2026-09-05")
        casos["estornado_existente"] = self.conta_unica(100.0, nome="D")
        self.so_estornado(casos["estornado_existente"], excluir=False)
        casos["unico_estornado_excluido"] = self.conta_unica(100.0, nome="E")
        self.so_estornado(casos["unico_estornado_excluido"], excluir=True)
        esperado = {"nunca_pagou": False, "parcial_ativo": True, "quitada": True, "estornado_existente": True,
                    "unico_estornado_excluido": False}
        self.assertEqual({k: self.protegida(c) for k, c in casos.items()}, esperado)
        self.assertFalse(self.tabela_antiga_existe())                        # nenhuma marca em lugar nenhum

    def test_exclui_um_entre_varios_sem_mudar_o_financeiro_e_segue_protegida(self):
        conta, p1, p2, p3 = self.conta_com_estornados()
        antes = self.financeiro(conta)
        situacao = pagamentos.excluir_estornado(p2, conta)
        self.assertEqual(self.ids(conta), [p1, p3])
        self.assertEqual(self.financeiro(conta)[:6], antes[:6])
        self.assertEqual(self.financeiro(conta)[6], [(p3, 50_00)])
        self.assertEqual([p["id"] for p in situacao["pagamentos"]], [p1, p3])
        self.assertTrue(self.protegida(conta))

    def test_exclui_o_ultimo_registro_restante(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 150_00, "2026-09-05")
        self.pagar(conta, 100_00, "2026-09-08")
        p1, p2 = self.ids(conta)
        self.estornar(p1)
        self.estornar(p2)
        antes = self.financeiro(conta)
        pagamentos.excluir_estornado(p1, conta)
        self.assertTrue(self.protegida(conta))                                # ainda resta p2
        pagamentos.excluir_estornado(p2, conta)
        self.assertEqual(self.ids(conta), [])
        self.assertEqual(self.financeiro(conta)[:6], antes[:6])               # valor, pago, saldo, status...
        self.assertEqual(self.status(conta), ("pendente", None))
        self.assertFalse(self.protegida(conta))                               # sem registros, sem proteção

    def test_preserva_a_quitacao(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 100_00, "2026-09-05")
        self.pagar(conta, 150_00, "2026-09-06")
        pid_estornado = self.ids(conta)[1]
        self.estornar(pid_estornado)
        self.pagar(conta, 300_00, "2026-09-12")                             # quita
        antes = self.financeiro(conta)
        self.assertEqual(antes[3], "pago")
        pagamentos.excluir_estornado(pid_estornado, conta)
        self.assertEqual(self.financeiro(conta)[:6], antes[:6])
        self.assertEqual(self.status(conta), ("pago", "2026-09-12"))
        self.assertTrue(self.protegida(conta))                                # pagamentos ativos

    def test_recusa_ativo_inexistente_e_de_outra_conta(self):
        conta, p1, p2, _ = self.conta_com_estornados()
        outra = self.conta_unica(200.0, nome="Luz")
        antes = self.consultar("SELECT * FROM pp_pagamentos ORDER BY id")
        for pid, dona in ((p1, conta), (9999, conta), (p2, outra)):
            with self.subTest(pid=pid, dona=dona):
                with self.assertRaises(pagamentos.RegistroEstornadoIndisponivelError):
                    pagamentos.excluir_estornado(pid, dona)
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"), antes)

    def test_repetir_a_exclusao_e_recusado(self):
        conta, _, p2, _ = self.conta_com_estornados()
        pagamentos.excluir_estornado(p2, conta)
        with self.assertRaises(pagamentos.RegistroEstornadoIndisponivelError):
            pagamentos.excluir_estornado(p2, conta)

    def test_falha_na_exclusao_nao_grava_nada(self):
        conta, _, p2, _ = self.conta_com_estornados()
        antes = self.consultar("SELECT * FROM pp_pagamentos ORDER BY id")

        class Falha(Exception):
            pass

        real = db.conectar

        def conectar_que_falha_no_commit():
            conexao = real()

            class Proxy:
                in_transaction = property(lambda self: conexao.in_transaction)

                def __getattr__(self, nome):
                    return getattr(conexao, nome)

                def __setattr__(self, nome, valor):
                    setattr(conexao, nome, valor)

                def cursor(self):
                    cursor = conexao.cursor()

                    class CursorProxy:
                        def __getattr__(self, nome):
                            return getattr(cursor, nome)

                        def execute(self, sql, *args):
                            if sql.strip().upper().startswith("COMMIT"):
                                raise Falha("falha simulada no COMMIT")
                            return cursor.execute(sql, *args)

                    return CursorProxy()

            return Proxy()

        with mock.patch.object(db, "conectar", conectar_que_falha_no_commit):
            with self.assertRaises(Falha):
                pagamentos.excluir_estornado(p2, conta)
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"), antes)

    # --------------------------------------------- 8-13: recorrência
    def test_intermediaria_com_pagamento_existente_segue_protegida(self):
        for rotulo, preparar in (
            ("ativo", lambda c: self.pagar(c, 30_00, "2026-09-06")),
            ("estornado", lambda c: self.so_estornado(c, excluir=False)),
            ("quitada", lambda c: db.marcar_conta_como_paga(c, "2026-09-06")),
        ):
            with self.subTest(rotulo=rotulo):
                serie_id, ids = self.serie_nov(preparar)
                nov = ids[2]
                self.assertEqual(db.ocorrencias_protegidas_no_valor(ids[0]), ["2026-11-20"])
                self.assertEqual([o["id"] for o in db.ocorrencias_futuras_com_pagamentos(ids[0])], [nov])
                antes = self.financeiro(nov)
                db.editar_conta_serie(ids[0], valor=80.0)                                     # valor coletivo
                self.assertEqual(self.valores(serie_id), [80.0, 80.0, 100.0, 80.0, 80.0, 80.0])
                r = db.alterar_frequencia_serie(ids[0], "anual", data_termino="2027-12")    # mensal -> anual
                self.assertIn(nov, r["ocorrencias_preservadas"])
                self.assertEqual(self.financeiro(nov), antes)
                db.encerrar_recorrencia(ids[0])                                             # encerrar
                self.assertTrue(self.consultar("SELECT 1 FROM contas WHERE id = ?", (nov,)))
                self.assertEqual(self.financeiro(nov), antes)

    def test_sem_protecao_depois_de_excluir_o_ultimo_pagamento(self):
        serie_id, ids = self.serie_nov(lambda c: self.so_estornado(c, excluir=True))
        nov = ids[2]
        self.assertEqual(self.ids(nov), [])
        self.assertEqual(db.ocorrencias_protegidas_no_valor(ids[0]), [])
        self.assertEqual(db.ocorrencias_futuras_com_pagamentos(ids[0]), [])                # sem aviso
        db.editar_conta_serie(ids[0], valor=80.0)
        self.assertEqual(self.valores(serie_id), [80.0] * 6)                               # novembro também
        r = db.alterar_frequencia_serie(ids[0], "anual", data_termino="2027-12")
        self.assertIn(nov, r["ocorrencias_substituidas"])                                  # é regerada
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas WHERE id = ?", (nov,)), [(0,)])

    def test_encerrar_remove_a_que_ficou_sem_pagamentos(self):
        _, ids = self.serie_nov(lambda c: self.so_estornado(c, excluir=True))
        db.encerrar_recorrencia(ids[0])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas WHERE id = ?", (ids[2],)), [(0,)])

    def test_editada_continua_protegida_mesmo_sem_pagamentos(self):
        for excluir in (None, True):            # nunca pagou / último estornado excluído
            with self.subTest(excluir=excluir):
                serie_id, ids = self.serie_nov()
                nov = ids[2]
                if excluir:
                    self.so_estornado(nov, excluir=True)
                db.editar_conta_ocorrencia(nov, nome="Novembro editado")
                self.assertFalse(self.protegida(nov))
                r = db.alterar_frequencia_serie(ids[0], "anual", data_termino="2027-12")
                self.assertIn(nov, r["ocorrencias_preservadas"])                          # pela edição
                db.encerrar_recorrencia(ids[0])
                self.assertEqual(self.consultar("SELECT nome FROM contas WHERE id = ?", (nov,)),
                                 [("Novembro editado",)])

    def test_mesmo_resultado_sem_registro_e_sem_nunca_ter_pago(self):
        resultados = []
        for preparar in (None, lambda c: self.so_estornado(c, excluir=True)):
            serie_id, ids = self.serie_nov(preparar)
            resultados.append((db.ocorrencias_protegidas_no_valor(ids[0]),
                               db.ocorrencias_futuras_com_pagamentos(ids[0])))
        self.assertEqual(resultados, [([], []), ([], [])])

    # --------------------------------------------- 14: exclusões sem erro de FK
    def test_exclusoes_de_conta_sem_erro_de_chave_estrangeira(self):
        conta, _, p2, _ = self.conta_com_estornados()
        pagamentos.excluir_estornado(p2, conta)
        self.assertTrue(db.excluir_conta(conta))
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM pp_pagamentos"), [(0,)])
        serie_id, ids = self.serie_nov(lambda c: self.so_estornado(c, excluir=False))
        db.excluir_conta_serie(ids[1])                                                     # este mês em diante
        self.assertEqual(len(self.consultar("SELECT id FROM contas WHERE serie_id = ?", (serie_id,))), 1)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM pp_pagamentos"), [(0,)])
        self.assertEqual(self.consultar("PRAGMA foreign_key_check"), [])

    def test_persistencia_ao_reabrir(self):
        _, ids = self.serie_nov(lambda c: self.so_estornado(c, excluir=True))
        protegida = self.serie_nov(lambda c: self.so_estornado(c, excluir=False))[1][2]
        conexao = db.sqlite3.connect(f"file:{self.caminho_banco}?mode=ro", uri=True)       # outra conexão
        try:
            com_registro = {c for (c,) in conexao.execute("SELECT conta_id FROM pp_pagamentos")}
            self.assertEqual(conexao.execute("PRAGMA integrity_check").fetchone(), ("ok",))
        finally:
            conexao.close()
        self.assertEqual(com_registro, {protegida})
        self.assertEqual((self.protegida(ids[2]), self.protegida(protegida)), (False, True))


class TestIntegracao610(TestePagamentos):
    """Sino 6.10, etapa 3 da integração: exclusões atômicas (com falha e
    reversão), totais com estornados e contas legadas sem contagem dupla, e o
    invariante financeiro depois das operações de recorrência. Hoje: 15/09/2026."""

    def invariante(self):
        """Nenhuma conta paga com saldo, nenhuma com pago acima do valor, e o
        status de quem tem pagamentos ativos segue os próprios pagamentos."""
        problemas = []
        for (cid,) in self.consultar("SELECT id FROM contas"):
            s = pagamentos.obter_situacao(cid)
            if s["pago_centavos"] > s["valor_centavos"] or s["saldo_centavos"] < 0:
                problemas.append((cid, "pago acima do valor"))
            if s["status"] == "pago" and s["saldo_centavos"] != 0:
                problemas.append((cid, "paga com saldo"))
            if s["ativos"] and (s["status"] == "pago") != (s["saldo_centavos"] == 0):
                problemas.append((cid, "status diferente dos pagamentos"))
        self.assertEqual(problemas, [])
        self.assertEqual(self.consultar("PRAGMA foreign_key_check"), [])

    def test_exclusao_com_falha_reverte_tudo(self):
        conta = self.conta_unica(400.0)
        self.pagar(conta, 150_00, "2026-09-05")
        outra = self.conta_unica(100.0, nome="Luz")
        self.pagar(outra, 40_00, "2026-09-05")
        antes = (self.consultar("SELECT * FROM contas ORDER BY id"), self.consultar("SELECT * FROM pp_pagamentos"))
        real = db._apagar_pagamentos

        def apagar_e_falhar(*args, **kwargs):
            real(*args, **kwargs)
            raise db.sqlite3.OperationalError("falha simulada depois de apagar os pagamentos")

        for excluir in (db.excluir_conta, db.excluir_conta_serie):
            with self.subTest(excluir=excluir.__name__):
                with mock.patch.object(db, "_apagar_pagamentos", side_effect=apagar_e_falhar):
                    with self.assertRaises(db.sqlite3.OperationalError):
                        excluir(conta)
                self.assertEqual((self.consultar("SELECT * FROM contas ORDER BY id"),
                                  self.consultar("SELECT * FROM pp_pagamentos")), antes)

    def test_exclusao_so_leva_os_pagamentos_da_propria_conta(self):
        serie_id, ids = self.serie(100.0, vencimento="2026-09-10", termino="2027-02")
        for oc in ids[:4]:
            self.pagar(oc, 30_00, "2026-09-05")
        avulsa = self.conta_unica(200.0, nome="Luz")
        self.pagar(avulsa, 50_00, "2026-09-05")
        pid = self.consultar("SELECT MAX(id) FROM pp_pagamentos WHERE conta_id = ?", (avulsa,))[0][0]
        pagamentos.estornar_pagamento(pid, (50_00, "2026-09-05"))
        db.excluir_conta(ids[0])                                     # só esta ocorrência
        db.excluir_conta_serie(ids[2])                               # esta e as seguintes
        self.assertEqual(sorted(c for (c,) in self.consultar("SELECT DISTINCT conta_id FROM pp_pagamentos")),
                         [ids[1], avulsa])                           # a outra ocorrência e a avulsa intactas
        self.assertTrue(db.excluir_conta(avulsa))                    # só estornado: apaga junto
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM pp_pagamentos WHERE conta_id = ?", (avulsa,)), [(0,)])
        self.invariante()

    def test_totais_com_estornados_e_legadas_sem_contagem_dupla(self):
        parcial = self.conta_unica(400.0, "2026-09-20", "Parcial")
        self.pagar(parcial, 150_00, "2026-09-05")
        self.pagar(parcial, 100_00, "2026-09-06")
        pid = self.consultar("SELECT MAX(id) FROM pp_pagamentos WHERE conta_id = ?", (parcial,))[0][0]
        pagamentos.estornar_pagamento(pid, (100_00, "2026-09-06"))     # estornado não conta
        legada = self.conta_unica(80.0, "2026-09-21", "Legada")
        self.executar("UPDATE contas SET status = 'pago', data_pagamento = '2026-09-02' WHERE id = ?", (legada,))
        quitada = self.conta_unica(120.0, "2026-09-22", "Quitada")
        self.pagar(quitada, 20_00, "2026-09-05")
        db.marcar_conta_como_paga(quitada)                              # parcial + saldo = 120 uma vez só
        self.assertEqual(db.resumo_do_periodo(self.usuario_id, "2026-09-01", "2026-09-30"), (600.0, 350.0))
        self.assertEqual(db.totais_por_mes(self.usuario_id, "2026-09", "2026-09"), {"2026-09": 600.0})
        self.invariante()

    def test_recorrencias_nao_criam_inconsistencias_silenciosas(self):
        serie_id, ids = self.serie(100.0, vencimento="2026-09-20", termino="2027-06")
        self.pagar(ids[1], 40_00, "2026-09-05")                      # parcial
        db.marcar_conta_como_paga(ids[2], "2026-09-05")              # quitada com registro
        db.editar_conta_serie(ids[0], valor=80.0)                    # opção D: as com pagamento mantêm o valor
        self.invariante()
        self.assertEqual(self.consultar("SELECT valor FROM contas WHERE id IN (?, ?) ORDER BY id",
                                        (ids[1], ids[2])), [(100.0,), (100.0,)])
        r = db.alterar_frequencia_serie(ids[0], "anual", data_termino="2028-12")
        self.assertEqual(sorted(r["ocorrencias_preservadas"]), sorted([ids[1], ids[2]]))
        self.invariante()
        db.encerrar_recorrencia(ids[0])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas WHERE id IN (?, ?)", (ids[1], ids[2])), [(2,)])
        self.invariante()


class TestEtapa4VencimentoColetivo(TestePagamentos):
    """Sino 6.10, etapa 4 da integração: "Este mês em diante" com novo
    vencimento. H2: as ocorrências seguintes com pagamentos (ativos ou
    estornados) ficam no mesmo mês e ano, só com o novo dia; as demais seguem
    a série. I1: a selecionada pode mudar de mês com os próprios pagamentos.
    I2: numa série anual, o ano de uma ocorrência paga que era a cobrança do
    ano não ganha outra cobrança (mensais pagas só ocupam o próprio mês). I4:
    a selecionada no mês de uma seguinte com pagamentos, depois dele, ou num
    ano anual ocupado -- recusa integral, nada gravado. I3 (camada de banco):
    ocorrencias_mantidas_no_vencimento. Hoje fixo: 15/09/2026."""

    def da(self, serie_id, competencia):
        linhas = self.consultar("SELECT id FROM contas WHERE serie_id = ? AND data_vencimento LIKE ?",
                                (serie_id, f"{competencia}%"))
        self.assertEqual(len(linhas), 1, (competencia, linhas))
        return linhas[0][0]

    def preparar(self, conta, tipo):
        if tipo == "ativo":
            self.pagar(conta, 40_00, "2026-09-05")
        elif tipo == "quitada":
            db.marcar_conta_como_paga(conta, "2026-09-05")
        elif tipo in ("estornado", "excluido"):
            self.pagar(conta, 40_00, "2026-09-05")
            pid = self.consultar("SELECT MAX(id) FROM pp_pagamentos")[0][0]
            pagamentos.estornar_pagamento(pid, (40_00, "2026-09-05"))
            if tipo == "excluido":
                pagamentos.excluir_estornado(pid, conta)
        elif tipo == "varios":
            self.pagar(conta, 30_00, "2026-09-05")
            self.pagar(conta, 20_00, "2026-09-06")
            pid = self.consultar("SELECT MAX(id) FROM pp_pagamentos")[0][0]
            pagamentos.estornar_pagamento(pid, (20_00, "2026-09-06"))
        elif tipo == "editada":
            db.editar_conta_ocorrencia(conta, nome="Editada")
        elif tipo == "editada_paga":
            db.editar_conta_ocorrencia(conta, nome="Editada")
            self.pagar(conta, 40_00, "2026-09-05")
        else:
            self.assertEqual(tipo, "nenhum")

    def venc(self, conta):
        return self.consultar("SELECT data_vencimento FROM contas WHERE id = ?", (conta,))[0][0]

    def lista(self, serie_id):
        return [d for (d,) in self.consultar("SELECT data_vencimento FROM contas WHERE serie_id = ? ORDER BY posicao",
                                             (serie_id,))]

    def financeiro(self, conta):
        s = pagamentos.obter_situacao(conta)
        return (s["valor_centavos"], s["pago_centavos"], s["saldo_centavos"], s["status"], s["data_pagamento"],
                self.consultar("SELECT id, conta_id, valor_centavos, data_pagamento, tipo, estornado_em "
                               "FROM pp_pagamentos WHERE conta_id = ? ORDER BY id", (conta,)))

    def tudo(self):
        return (self.consultar("SELECT * FROM contas ORDER BY id"),
                self.consultar("SELECT * FROM series_recorrencia ORDER BY id"),
                self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"))

    def conferir_serie(self, serie_id):
        """Sem dois vencimentos no mesmo mês; posições 1..n em ordem de vaga; integridade e FK."""
        linhas = self.consultar("SELECT posicao, data_vencimento, data_prevista FROM contas WHERE serie_id = ? "
                                "ORDER BY posicao", (serie_id,))
        meses = [v[:7] for _, v, _ in linhas]
        self.assertEqual(len(meses), len(set(meses)), meses)
        self.assertEqual([p for p, _, _ in linhas], list(range(1, len(linhas) + 1)))
        self.assertEqual([pr for _, _, pr in linhas], sorted(pr for _, _, pr in linhas))
        self.assertEqual(self.consultar("PRAGMA integrity_check"), [("ok",)])
        self.assertEqual(self.consultar("PRAGMA foreign_key_check"), [])

    def mensal(self, inicio="2026-11-10", termino=None):
        serie_id, _ = self.serie(100.0, vencimento=inicio, termino=termino)
        return serie_id

    def anual(self, termino=None):
        serie_id, _ = self.serie(1800.0, frequencia="anual", vencimento="2026-11-10", termino=termino)
        return serie_id

    def anos(self, serie_id):
        return [int(v[:4]) for v in self.lista(serie_id)]

    # ------------------------------------------------ H2: proteção financeira
    def test_h2_tipos_de_pagamento_e_edicao(self):
        esperado = {"ativo": "2027-01", "quitada": "2027-01", "estornado": "2027-01", "varios": "2027-01",
                    "editada_paga": "2027-01",                                 # H2
                    "excluido": "2027-02", "nenhum": "2027-02", "editada": "2027-02"}  # seguem a série (D2)
        for tipo, mes in esperado.items():
            with self.subTest(tipo=tipo):
                serie_id = self.mensal()
                jan = self.da(serie_id, "2027-01")
                self.preparar(jan, tipo)
                antes = self.financeiro(jan)
                self.assertTrue(db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10"))
                self.assertEqual(self.venc(jan)[:7], mes)
                self.assertEqual(self.financeiro(jan), antes)                  # pagamentos e situação iguais
                self.conferir_serie(serie_id)

    def test_h2_quitada_integralmente_continua_quitada(self):
        serie_id = self.mensal()
        jan = self.da(serie_id, "2027-01")
        self.pagar(jan, 100_00, "2026-09-05")
        self.assertEqual(self.status(jan), ("pago", "2026-09-05"))
        db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-20")
        self.assertEqual((self.venc(jan), self.status(jan)), ("2027-01-20", ("pago", "2026-09-05")))
        self.conferir_serie(serie_id)

    def test_h2_so_o_dia_muda_dentro_do_mes(self):
        for inicio, nova, esperado in (("2026-11-10", "2026-11-20", "2027-01-20"),
                                       ("2026-11-20", "2026-11-10", "2027-01-10")):
            with self.subTest(nova=nova):
                serie_id = self.mensal(inicio)
                jan = self.da(serie_id, "2027-01")
                self.preparar(jan, "ativo")
                self.assertTrue(db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento=nova))
                self.assertEqual(self.venc(jan), esperado)
                self.conferir_serie(serie_id)

    def test_h2_novembro_para_dezembro_com_janeiro_protegido(self):
        serie_id = self.mensal()
        jan, dez = self.da(serie_id, "2027-01"), self.da(serie_id, "2026-12")
        self.preparar(jan, "ativo")
        total = len(self.lista(serie_id))
        db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10")
        self.assertEqual(self.lista(serie_id)[:4], ["2026-12-10", "2027-01-10", "2027-02-10", "2027-03-10"])
        self.assertEqual((self.venc(jan), self.venc(dez)), ("2027-01-10", "2027-02-10"))  # dez pula jan
        self.assertEqual(len(self.lista(serie_id)), total)
        self.conferir_serie(serie_id)

    def test_h2_janeiro_para_fevereiro_com_marco_protegido(self):
        serie_id = self.mensal()
        mar, fev = self.da(serie_id, "2027-03"), self.da(serie_id, "2027-02")
        self.preparar(mar, "quitada")
        db.editar_conta_serie(self.da(serie_id, "2027-01"), data_vencimento="2027-02-10")
        self.assertEqual(self.lista(serie_id)[:5], ["2026-11-10", "2026-12-10", "2027-02-10", "2027-03-10",
                                                    "2027-04-10"])
        self.assertEqual((self.venc(mar), self.venc(fev)), ("2027-03-10", "2027-04-10"))
        self.conferir_serie(serie_id)

    def test_h2_virada_de_ano(self):
        serie_id = self.mensal()
        fev = self.da(serie_id, "2027-02")
        self.preparar(fev, "estornado")
        db.editar_conta_serie(self.da(serie_id, "2026-12"), data_vencimento="2027-01-10")
        self.assertEqual(self.lista(serie_id)[:5], ["2026-11-10", "2027-01-10", "2027-02-10", "2027-03-10",
                                                    "2027-04-10"])
        self.assertEqual(self.venc(fev), "2027-02-10")
        self.conferir_serie(serie_id)

    def test_h2_protegida_fora_da_grade_anual(self):
        serie_id = self.mensal()
        jan = self.da(serie_id, "2027-01")
        self.preparar(jan, "ativo")
        db.alterar_frequencia_serie(self.da(serie_id, "2026-11"), "anual", data_termino=None)
        self.assertEqual(self.lista(serie_id), ["2026-11-10", "2027-01-10", "2027-11-10"])
        db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-11-20")
        self.assertEqual(self.lista(serie_id), ["2026-11-20", "2027-01-20", "2027-11-20"])  # nov/2027 continua
        self.conferir_serie(serie_id)

    def test_h2_varias_protegidas(self):
        serie_id = self.mensal()
        jan, mar = self.da(serie_id, "2027-01"), self.da(serie_id, "2027-03")
        self.preparar(jan, "ativo")
        self.preparar(mar, "varios")
        db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10")
        self.assertEqual(self.lista(serie_id)[:6], ["2026-12-10", "2027-01-10", "2027-02-10", "2027-03-10",
                                                    "2027-04-10", "2027-05-10"])
        self.assertEqual((self.venc(jan), self.venc(mar)), ("2027-01-10", "2027-03-10"))
        self.conferir_serie(serie_id)

    def test_h2_protegidas_antes_e_no_fim(self):
        serie_id = self.mensal("2026-10-10")
        primeira, ultima = self.da(serie_id, "2026-10"), self.da(serie_id, "2027-10")
        self.preparar(primeira, "ativo")
        self.preparar(ultima, "ativo")
        total = len(self.lista(serie_id))
        db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10")
        lista = self.lista(serie_id)
        self.assertEqual((self.venc(primeira), self.venc(ultima)), ("2026-10-10", "2027-10-10"))
        self.assertEqual((lista[0], lista[1], len(lista)), ("2026-10-10", "2026-12-10", total))
        self.assertIn("2027-11-10", lista)                                           # a que caía em out pula
        self.conferir_serie(serie_id)

    def test_h2_valor_e_vencimento_juntos(self):
        serie_id = self.mensal()
        jan, mar = self.da(serie_id, "2027-01"), self.da(serie_id, "2027-03")
        self.preparar(jan, "varios")
        self.preparar(mar, "estornado")
        ids_antes = sorted(i for (i,) in self.consultar("SELECT id FROM contas WHERE serie_id = ?", (serie_id,)))
        registros = self.consultar("SELECT * FROM pp_pagamentos ORDER BY id")
        self.assertTrue(db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10",
                                              valor=120.0))
        self.assertEqual(db.preparar_banco()["situacao"], "atual")                     # nova abertura
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"), registros)
        self.assertEqual(self.consultar("SELECT data_vencimento, valor FROM contas WHERE id IN (?, ?) ORDER BY id",
                                        (jan, mar)), [("2027-01-10", 100.0), ("2027-03-10", 100.0)])
        ids_depois = sorted(i for (i,) in self.consultar("SELECT id FROM contas WHERE serie_id = ?", (serie_id,)))
        self.assertEqual(ids_antes, ids_depois)                                        # nada apagado ou criado
        for conta in (jan, mar):
            s = pagamentos.obter_situacao(conta)
            self.assertEqual(s["pago_centavos"] + s["saldo_centavos"], s["valor_centavos"])
        self.conferir_serie(serie_id)

    def test_h2_termino_permite_so_o_dia_e_recusa_o_mes(self):
        serie_id = self.mensal(termino="2027-03")
        jan = self.da(serie_id, "2027-01")
        self.preparar(jan, "ativo")
        antes = self.tudo()
        self.assertFalse(db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10"))
        self.assertEqual(self.tudo(), antes)
        self.assertTrue(db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-11-20"))
        self.assertEqual(self.lista(serie_id), ["2026-11-20", "2026-12-20", "2027-01-20", "2027-02-20",
                                                "2027-03-20"])
        self.conferir_serie(serie_id)

    def test_d5_continua_valendo(self):
        serie_id = self.mensal()
        with self.assertRaises(db.VencimentoAntesDaParcelaAnteriorError):
            db.editar_conta_serie(self.da(serie_id, "2027-01"), data_vencimento="2026-12-20")

    # ------------------------------------------------ I1: a selecionada
    def test_i1_selecionada_com_pagamento_muda_de_mes(self):
        serie_id = self.mensal()
        jan, mar = self.da(serie_id, "2027-01"), self.da(serie_id, "2027-03")
        self.preparar(jan, "ativo")
        self.preparar(mar, "ativo")
        antes = self.financeiro(jan)
        self.assertTrue(db.editar_conta_serie(jan, data_vencimento="2027-02-10"))
        self.assertEqual(self.venc(jan), "2027-02-10")                                # a escolha expressa
        self.assertEqual(self.financeiro(jan), antes)                                 # mesmos pagamentos
        self.assertEqual(self.venc(mar), "2027-03-10")                                # a outra fica
        self.conferir_serie(serie_id)

    def test_i1_selecionada_quitada_e_estornada(self):
        for tipo in ("quitada", "estornado"):
            with self.subTest(tipo=tipo):
                serie_id = self.mensal()
                jan = self.da(serie_id, "2027-01")
                self.preparar(jan, tipo)
                antes = self.financeiro(jan)
                self.assertTrue(db.editar_conta_serie(jan, data_vencimento="2027-02-15"))
                self.assertEqual((self.venc(jan), self.financeiro(jan)), ("2027-02-15", antes))
                self.conferir_serie(serie_id)

    def test_i1_selecionada_sem_pagamento(self):
        serie_id = self.mensal()
        jan = self.da(serie_id, "2027-01")
        db.editar_conta_serie(jan, data_vencimento="2027-02-10")
        self.assertEqual(self.lista(serie_id)[2:4], ["2027-02-10", "2027-03-10"])
        self.conferir_serie(serie_id)

    # ------------------------------------------------ I2: anual
    def test_i2_ano_pago_nao_ganha_outra_cobranca(self):
        for tipo in ("ativo", "quitada", "estornado", "varios"):
            with self.subTest(tipo=tipo):
                serie_id = self.anual()
                nov27 = self.da(serie_id, "2027-11")
                self.preparar(nov27, tipo)
                self.assertTrue(db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10"))
                self.assertEqual(self.lista(serie_id), ["2026-12-10", "2027-11-10"])      # sem dez/2027
                self.assertEqual(self.consultar("SELECT horizonte_gerado_ate FROM series_recorrencia WHERE id = ?",
                                                (serie_id,)), [("2027-12-10",)])
                db.gerar_ocorrencias_sob_demanda(serie_id, "2029-12")                     # próximo ano elegível
                self.assertEqual(self.lista(serie_id), ["2026-12-10", "2027-11-10", "2028-12-10", "2029-12-10"])
                self.assertEqual(len(self.anos(serie_id)), len(set(self.anos(serie_id))))
                self.conferir_serie(serie_id)

    def test_i2_sem_protecao_depois_de_excluir_o_ultimo(self):
        serie_id = self.anual()
        nov27 = self.da(serie_id, "2027-11")
        self.preparar(nov27, "excluido")
        db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10")
        self.assertEqual(self.lista(serie_id), ["2026-12-10", "2027-12-10"])                # segue a série

    def test_i2_com_termino(self):
        for termino, aceita in (("2029-12", True), ("2029-11", False)):
            with self.subTest(termino=termino):
                serie_id = self.anual(termino)
                self.preparar(self.da(serie_id, "2027-11"), "ativo")
                antes = self.lista(serie_id)
                ok = db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10")
                self.assertEqual(ok, aceita)
                esperado = ["2026-12-10", "2027-11-10", "2028-12-10", "2029-12-10"] if aceita else antes
                self.assertEqual(self.lista(serie_id), esperado)

    def test_i2_selecionada_paga_muda_de_mes_no_mesmo_ano(self):
        serie_id = self.anual()
        nov27 = self.da(serie_id, "2027-11")
        self.preparar(nov27, "ativo")
        antes = self.financeiro(nov27)
        self.assertTrue(db.editar_conta_serie(nov27, data_vencimento="2027-12-10"))           # I1
        self.assertEqual(self.lista(serie_id), ["2026-11-10", "2027-12-10"])
        self.assertEqual(self.financeiro(nov27), antes)
        db.gerar_ocorrencias_sob_demanda(serie_id, "2028-12")
        self.assertEqual(self.lista(serie_id), ["2026-11-10", "2027-12-10", "2028-12-10"])

    def test_i2_editada_sem_pagamentos_segue_as_regras_proprias(self):
        serie_id = self.anual()
        nov27 = self.da(serie_id, "2027-11")
        self.preparar(nov27, "editada")
        db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10")
        self.assertEqual(self.venc(nov27), "2027-12-10")                                     # D2: na grade, anda

    def test_i2_pago_fora_da_grade_nao_ocupa_o_ano(self):
        """Um mês pago herdado de antes de mensal -> anual ocupa só o mês."""
        serie_id = self.mensal()
        self.preparar(self.da(serie_id, "2027-01"), "ativo")
        db.alterar_frequencia_serie(self.da(serie_id, "2026-11"), "anual", data_termino=None)
        db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10")
        self.assertEqual(self.lista(serie_id), ["2026-12-10", "2027-01-10", "2027-12-10"])

    def test_i2_mensal_paga_nao_bloqueia_o_ano(self):
        serie_id = self.mensal()
        jan = self.da(serie_id, "2027-01")
        self.preparar(jan, "quitada")
        db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10")
        lista = self.lista(serie_id)
        self.assertEqual(sum(1 for v in lista if v.startswith("2027-")), 12)                # o ano segue cheio
        self.conferir_serie(serie_id)

    def test_i2_reabrir_e_gerar_sem_duplicidade(self):
        serie_id = self.anual()
        self.preparar(self.da(serie_id, "2027-11"), "ativo")
        db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10")
        self.assertEqual(db.preparar_banco()["situacao"], "atual")                         # nova abertura
        for _ in range(2):
            db.gerar_ocorrencias_sob_demanda(serie_id, "2030-12")
        self.assertEqual(self.anos(serie_id), [2026, 2027, 2028, 2029, 2030])
        self.conferir_serie(serie_id)

    # ------------------------------------------------ I4: conflitos e atomicidade
    def recusa(self, conta, data, motivo):
        antes = self.tudo()
        with self.assertRaises(db.CompetenciaComPagamentosError) as ctx:
            db.editar_conta_serie(conta, data_vencimento=data, nome="Outro nome", valor=150.0)
        self.assertEqual(ctx.exception.motivo, motivo)
        self.assertEqual(str(ctx.exception), db.MENSAGENS_COMPETENCIA_COM_PAGAMENTOS[motivo])
        self.assertEqual(self.tudo(), antes)                                           # nada gravado

    def test_i4_mesmo_mes_de_uma_paga(self):
        for tipo in ("ativo", "quitada", "estornado"):
            with self.subTest(tipo=tipo):
                serie_id = self.mensal()
                self.preparar(self.da(serie_id, "2027-01"), tipo)
                self.recusa(self.da(serie_id, "2026-11"), "2027-01-20", "mesmo_mes")

    def test_i4_selecionada_paga_no_mes_de_outra_paga(self):
        serie_id = self.mensal()
        jan, mar = self.da(serie_id, "2027-01"), self.da(serie_id, "2027-03")
        self.preparar(jan, "ativo")
        self.preparar(mar, "ativo")
        self.recusa(jan, "2027-03-05", "mesmo_mes")

    def test_i4_depois_de_uma_paga(self):
        serie_id = self.mensal()
        self.preparar(self.da(serie_id, "2027-01"), "ativo")
        self.recusa(self.da(serie_id, "2026-11"), "2027-02-10", "depois")
        self.recusa(self.da(serie_id, "2026-11"), "2028-06-10", "depois")

    def test_i4_ate_o_mes_anterior_a_paga_e_permitido(self):
        serie_id = self.mensal()
        jan = self.da(serie_id, "2027-01")
        self.preparar(jan, "ativo")
        self.assertTrue(db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-31"))
        self.assertEqual(self.lista(serie_id)[:3], ["2026-12-31", "2027-01-31", "2027-02-28"])
        self.assertEqual(self.venc(jan), "2027-01-31")
        self.conferir_serie(serie_id)

    def test_i4_ano_anual_ocupado(self):
        serie_id = self.anual()
        self.preparar(self.da(serie_id, "2027-11"), "ativo")
        self.recusa(self.da(serie_id, "2026-11"), "2027-03-10", "ano")
        self.recusa(self.da(serie_id, "2026-11"), "2028-03-10", "depois")

    def test_i4_ano_livre_e_mensal_paga_fora_da_grade(self):
        """Na anual, um mês pago herdado de mensal ocupa só o próprio mês."""
        serie_id = self.mensal()
        self.preparar(self.da(serie_id, "2027-03"), "ativo")
        db.alterar_frequencia_serie(self.da(serie_id, "2026-11"), "anual", data_termino=None)
        self.assertTrue(db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2027-01-10"))
        self.assertEqual(self.lista(serie_id)[:2], ["2027-01-10", "2027-03-10"])
        self.conferir_serie(serie_id)

    def test_i4_editada_fora_da_grade_com_pagamentos(self):
        serie_id = self.mensal()
        jan = self.da(serie_id, "2027-01")
        self.preparar(jan, "ativo")
        db.alterar_frequencia_serie(self.da(serie_id, "2026-11"), "anual", data_termino=None)
        db.editar_conta_ocorrencia(jan, nome="Editada")                     # D2: fica, e com pagamentos
        self.recusa(self.da(serie_id, "2026-11"), "2027-01-05", "mesmo_mes")

    def test_i4_falha_no_meio_desfaz_tudo(self):
        serie_id = self.mensal()
        jan = self.da(serie_id, "2027-01")
        self.preparar(jan, "varios")
        antes = self.tudo()
        with mock.patch.object(db, "_renumerar_segmento", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                db.editar_conta_serie(self.da(serie_id, "2026-11"), data_vencimento="2026-12-10", valor=130.0)
        self.assertEqual(self.tudo(), antes)                                           # ROLLBACK completo
        self.conferir_serie(serie_id)

    # ------------------------------------------------ calendário
    def test_fevereiro_e_dias_29_30_31(self):
        casos = (("2026-11-15", "2026-11", "2026-11-29", "2027-02", "2027-02-28"),
                 ("2026-11-15", "2026-11", "2026-11-30", "2027-02", "2027-02-28"),
                 ("2026-12-15", "2026-12", "2026-12-31", "2027-02", "2027-02-28"),
                 ("2027-11-28", "2027-11", "2027-11-29", "2028-02", "2028-02-29"))   # bissexto
        for inicio, sel, nova, alvo, esperado in casos:
            with self.subTest(nova=nova):
                serie_id = self.mensal(inicio)
                conta = self.da(serie_id, alvo)
                self.preparar(conta, "ativo")
                self.assertTrue(db.editar_conta_serie(self.da(serie_id, sel), data_vencimento=nova))
                self.assertEqual(self.venc(conta), esperado)
                self.conferir_serie(serie_id)

    def test_dia_ajustado_volta_nos_meses_longos(self):
        """Sem arrasto: a protegida de fevereiro fica em 28, as de março em diante voltam a 31."""
        serie_id = self.mensal("2026-12-15")
        self.preparar(self.da(serie_id, "2027-02"), "ativo")
        db.editar_conta_serie(self.da(serie_id, "2026-12"), data_vencimento="2026-12-31")
        self.assertEqual(self.lista(serie_id)[:4], ["2026-12-31", "2027-01-31", "2027-02-28", "2027-03-31"])

    # ------------------------------------------------ I3 (camada de banco)
    def test_i3_mantidas(self):
        serie_id = self.mensal()
        nov, jan = self.da(serie_id, "2026-11"), self.da(serie_id, "2027-01")
        self.assertEqual(db.ocorrencias_mantidas_no_vencimento(nov, "2026-12-10"), [])     # sem pagamentos
        self.preparar(jan, "ativo")
        self.assertEqual(db.ocorrencias_mantidas_no_vencimento(nov, "2026-12-10"), ["2027-01-10"])
        self.assertEqual(db.ocorrencias_mantidas_no_vencimento(nov, "2026-11-20"), [])     # só o dia
        self.assertEqual(db.ocorrencias_mantidas_no_vencimento(jan, "2027-02-10"), [])     # a selecionada

    def test_i3_sem_aviso_quando_seria_recusado(self):
        serie_id = self.mensal(termino="2027-03")
        nov, dez, jan = self.da(serie_id, "2026-11"), self.da(serie_id, "2026-12"), self.da(serie_id, "2027-01")
        self.preparar(jan, "ativo")
        self.assertEqual(db.ocorrencias_mantidas_no_vencimento(nov, "2027-01-20"), [])     # I4 mesmo mês
        self.assertEqual(db.ocorrencias_mantidas_no_vencimento(nov, "2027-02-10"), [])     # I4 depois
        self.assertEqual(db.ocorrencias_mantidas_no_vencimento(nov, "2026-12-10"), [])     # término
        self.assertFalse(db.editar_conta_serie(nov, data_vencimento="2026-12-10"))
        self.assertEqual(db.ocorrencias_mantidas_no_vencimento(dez, "2026-11-20"), [])     # D5
        with self.assertRaises(db.VencimentoAntesDaParcelaAnteriorError):
            db.editar_conta_serie(dez, data_vencimento="2026-11-20")
