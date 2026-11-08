"""
Sino 6.12 (experimental), Etapa 10 -- restrições estruturais (R6, X1, X2).

R6: a frequência não muda (Mensal <-> Anual), em séries fixas, variáveis e parceladas,
recusada no banco sem gravar nada; edições comuns continuam. X1: "Transformar" só em conta
Única ou em ocorrência de recorrência encerrada. X2: "Encerrar" e "Transformar" são duas
ações explícitas; o encerramento preserva pagamentos, estornos e valores pendentes. Interface:
sem "Alterar frequência" e sem "Transformar" com um encerramento ainda não salvo.
Hoje fixo: 15/09/2026.
"""

import unittest
from datetime import datetime  # noqa: F401
from unittest import mock

from apoio_banco import db
from test_612_variavel import BaseVariavel, Interrupcao
from test_612_variavel_telas import BaseVariavelTelas
from test_tela_principal import Evento

import flet as ft  # noqa: E402
import pagamentos  # noqa: E402


class BaseEstrutura(BaseVariavel):
    def pagamentos_registrados(self):
        return self.consultar("SELECT * FROM pp_pagamentos ORDER BY id")

    def estornar_unico(self, conta_id, centavos, data):
        pagamentos.registrar_pagamento_parcial(conta_id, centavos, data)
        p = pagamentos.obter_situacao(conta_id)["ativos"][0]
        pagamentos.estornar_pagamento(p["id"], (p["valor_centavos"], p["data_pagamento"]))


class TestR6FrequenciaNaoMuda(BaseEstrutura):
    def test_recusada_em_todos_os_tipos_sem_gravar(self):
        _, mensal = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-08-05", "mensal")
        _, anual = db.criar_serie_recorrente(self.usuario_id, "IPVA", 1800.0, "2026-03-20", "anual")
        _, var_m = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-08-10", "mensal", variavel=True)
        _, var_a = db.criar_serie_recorrente(self.usuario_id, "Seguro", 700.0, "2026-05-02", "anual",
                                             data_termino="2030-12", variavel=True)
        _, parcelas = db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-10-05")
        unica = db.criar_conta_unica(self.usuario_id, "Água", 80.0, "2026-09-18")
        pagamentos.registrar_pagamento_parcial(mensal[0], 100_00, "2026-08-05")
        self.estornar_unico(anual[0], 50_00, "2026-03-20")
        antes = self.estado()
        casos = ((mensal[1], "anual"), (mensal[0], "anual"), (anual[0], "mensal"), (var_m[2], "anual"),
                 (var_a[1], "mensal"), (parcelas[0], "anual"), (unica, "mensal"), (mensal[1], "mensal"))
        for conta, frequencia in casos:
            for termino in (None, "2030-12"):
                with self.subTest(conta=conta, frequencia=frequencia, termino=termino), \
                        self.assertRaises(db.EstruturaRecusadaError) as recusa:
                    db.alterar_frequencia_serie(conta, frequencia, data_termino=termino)
                self.assertEqual(str(recusa.exception), db.MENSAGEM_FREQUENCIA_NAO_MUDA)
        self.assertEqual(self.estado(), antes)
        self.assert_banco_valido()

    def test_recusa_nao_le_nem_abre_o_banco(self):
        with mock.patch.object(db, "conectar", side_effect=AssertionError("não deveria abrir")):
            with self.assertRaises(db.EstruturaRecusadaError):
                db.alterar_frequencia_serie(1, "anual")

    def test_edicoes_comuns_continuam(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-05", "mensal",
                                               data_termino="2026-12")
        self.assertTrue(db.editar_conta_serie(ids[1], nome="Aluguel novo", valor=950.0, data_vencimento="2026-10-08"))
        self.assertTrue(db.editar_conta_ocorrencia(ids[3], valor=990.0))
        self.assertEqual(self.consultar("SELECT frequencia, dia_ancora FROM series_recorrencia WHERE id = ?",
                                        (serie,)), [("mensal", 8)])
        self.assertEqual(self.valores(serie), [900.0, 950.0, 950.0, 990.0])
        self.assert_banco_valido()

    def test_app_nao_usa_o_corpo_da_611(self):
        import inspect
        import main
        fonte = inspect.getsource(main)
        self.assertNotIn("alterar_frequencia_serie(", fonte)                  # nenhuma chamada (só comentários)
        self.assertNotIn("_alterar_frequencia_serie_611", fonte)


class TestX1Transformar(BaseEstrutura):
    def test_recusado_em_serie_ativa_e_parcelada(self):
        _, fixa = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-08-05", "mensal")
        _, variavel = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-08-10", "mensal", variavel=True)
        _, parcelas = db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-10-05")
        antes = self.estado()
        for conta in (fixa[0], fixa[2], variavel[0], parcelas[0], parcelas[2]):
            for variavel_nova in (False, True):
                with self.subTest(conta=conta, variavel=variavel_nova), \
                        self.assertRaises(db.EstruturaRecusadaError) as recusa:
                    db.transformar_em_recorrente(conta, "anual", variavel=variavel_nova)
                self.assertEqual(str(recusa.exception), db.MENSAGEM_TRANSFORMAR_SO_UNICA)
        for conta in (fixa[1], parcelas[1]):
            with self.assertRaises(db.ParcelamentoRecusadoError):
                db.transformar_unica_em_parcelada(conta, 3)
        self.assertEqual(self.estado(), antes)

    def test_permitido_em_unica_com_e_sem_pagamentos(self):
        sem = db.criar_conta_unica(self.usuario_id, "Água", 80.0, "2026-09-18")
        com = db.criar_conta_unica(self.usuario_id, "Escola", 500.0, "2026-09-10")
        pagamentos.registrar_pagamento_parcial(com, 100_00, "2026-09-05")
        self.estornar_unico(com, 30_00, "2026-09-06")
        pagos = self.pagamentos_registrados()
        db.transformar_em_recorrente(sem, "mensal")
        db.transformar_em_recorrente(com, "anual", variavel=True)
        self.assertEqual(self.pagamentos_registrados(), pagos)
        self.assert_banco_valido()

    def test_rollback_mantem_a_unica_e_os_pagamentos(self):
        conta = db.criar_conta_unica(self.usuario_id, "Escola", 500.0, "2026-09-10")
        pagamentos.registrar_pagamento_parcial(conta, 100_00, "2026-09-05")
        antes = self.estado()
        original = db._inserir_ocorrencia
        chamadas = []

        def inserir_e_falhar(*args, **kwargs):
            chamadas.append(1)
            if len(chamadas) == 3:
                raise Interrupcao()
            return original(*args, **kwargs)

        with mock.patch.object(db, "_inserir_ocorrencia", inserir_e_falhar), self.assertRaises(Interrupcao):
            db.transformar_em_recorrente(conta, "mensal", variavel=True)
        self.assertEqual(self.estado(), antes)


class TestX2EncerrarDepoisTransformar(BaseEstrutura):
    def setUp(self):
        super().setUp()
        # Mensal desde julho: julho pago, agosto com pagamento estornado, novembro pago adiantado.
        self.serie, self.ids = db.criar_serie_recorrente(self.usuario_id, "Academia", 100.0, "2026-07-10", "mensal",
                                                         data_termino="2027-03")
        db.marcar_conta_como_paga(self.ids[0], "2026-07-10")
        self.estornar_unico(self.ids[1], 20_00, "2026-08-10")
        pagamentos.registrar_pagamento_parcial(self.ids[4], 100_00, "2026-09-14")

    def test_mensal_para_anual_em_duas_acoes(self):
        pagos = self.pagamentos_registrados()
        db.encerrar_recorrencia(self.ids[2])                   # corte = hoje (15/09)
        restantes = [i for (i,) in self.consultar("SELECT id FROM contas WHERE serie_id = ? ORDER BY posicao",
                                                  (self.serie,))]
        # Julho, agosto, setembro (até o corte) e novembro (com pagamento) ficam; o resto sai.
        self.assertEqual(restantes, [self.ids[0], self.ids[1], self.ids[2], self.ids[4]])
        self.assertEqual(self.pagamentos_registrados(), pagos)
        with self.assertRaises(ValueError):                      # já encerrada: não encerra de novo
            db.encerrar_recorrencia(self.ids[2])
        nova, criadas = db.transformar_em_recorrente(self.ids[2], "anual", data_termino="2029-12")
        self.assertEqual(self.consultar("SELECT frequencia FROM series_recorrencia WHERE id = ?", (nova,)),
                         [("anual",)])
        self.assertEqual(len(criadas), 3)
        self.assertEqual(self.consultar("SELECT frequencia, ativa FROM series_recorrencia WHERE id = ?",
                                        (self.serie,)), [("mensal", 0)])   # a antiga fica como histórico
        self.assertEqual(self.pagamentos_registrados(), pagos)
        self.assert_banco_valido()

    def test_avulsa_com_pagamentos_transforma_mas_nao_parcela(self):
        db.encerrar_recorrencia(self.ids[2])
        antes = self.estado()
        with self.assertRaises(db.ParcelamentoRecusadoError):     # R1: estorno conta como registro
            db.transformar_unica_em_parcelada(self.ids[1], 3)
        self.assertEqual(self.estado(), antes)
        db.transformar_em_recorrente(self.ids[1], "mensal", data_termino="2026-12", variavel=True)
        self.assertEqual(len(pagamentos.obter_situacao(self.ids[1])["pagamentos"]), 1)
        self.assert_banco_valido()

    def test_variavel_encerrada_preserva_pendentes_e_exige_valor(self):
        _, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-07-10", "mensal",
                                           data_termino="2027-03", variavel=True)
        db.encerrar_recorrencia(ids[2])
        self.assertEqual(self.pendentes(), {ids[1], ids[2]})
        with self.assertRaises(db.ValorVariavelRecusadoError):
            db.transformar_em_recorrente(ids[2], "anual")
        db.editar_conta_ocorrencia(ids[2], valor=160.0)
        db.transformar_em_recorrente(ids[2], "anual", variavel=True)
        self.assertIn(ids[1], self.pendentes())                  # a outra avulsa continua pendente
        self.assert_banco_valido()

    def test_parcelada_nao_encerra(self):
        _, parcelas = db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-10-05")
        antes = self.estado()
        with self.assertRaises(db.ParcelamentoRecusadoError):
            db.encerrar_recorrencia(parcelas[1])
        self.assertEqual(self.estado(), antes)

    def test_r4_a_continua(self):
        _, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-08-10", "mensal",
                                           data_termino="2026-12", variavel=True)
        with self.assertRaises(db.ValorVariavelRecusadoError) as recusa:
            db.tornar_fixa(ids[3], 140.0)
        self.assertEqual(str(recusa.exception), db.MENSAGEM_PENDENTES_ANTERIORES)


class TestTelasEstrutura(BaseVariavelTelas):
    def itens(self):
        return [i.content for i in self.campo("Recorrência").suffix_icon.items]

    def editar(self, nome):
        self.entrar()
        self.clicar(self.linha(nome))
        self.clicar(self.botao("Editar"))

    def test_menus(self):
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "anual")
        db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-20", "mensal", variavel=True)
        db.criar_conta_unica(self.usuario_id, "Água", 80.0, "2026-09-18")
        db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-09-22")
        for nome, esperado in (("Aluguel", ["Alterar tipo de valor", "Encerrar recorrência"]), ("Luz", ["Alterar tipo de valor", "Encerrar recorrência"]),  # ajuste D
                               ("Água", ["Transformar em recorrente"])):
            with self.subTest(nome=nome):
                self.editar(nome)
                self.assertEqual(self.itens(), esperado)
        self.editar("Sofá")
        self.assertEqual(self.itens(), ["Alterar parcelamento"])                # parcela: ajuste A

    def test_encerrar_e_transformar_em_duas_acoes_pela_tela(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Academia", 100.0, "2026-09-10", "mensal",
                                               data_termino="2027-03")
        pagamentos.registrar_pagamento_parcial(ids[0], 40_00, "2026-09-05")
        pagos = self.consultar("SELECT * FROM pp_pagamentos")
        self.editar("Academia")
        self.clicar(next(i for i in self.campo("Recorrência").suffix_icon.items
                         if i.content == "Encerrar recorrência"))
        self.clicar(self.acao("Encerrar recorrência"))
        self.assertEqual(self.itens(), ["Desfazer esta alteração"])           # nada de Transformar agora
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.consultar("SELECT ativa FROM series_recorrencia"), [(0,)])
        self.editar("Academia")                                                # agora é avulsa
        self.assertEqual(self.itens(), ["Transformar em recorrente"])
        self.clicar(next(i for i in self.campo("Recorrência").suffix_icon.items
                         if i.content == "Transformar em recorrente"))
        from test_tela_principal import percorrer
        self.clicar(next(c for c in percorrer(self.dlg().content) if isinstance(c, ft.Container) and c.on_click
                         and self.textos_da(c) == ["Anual"]))
        self.clicar(self.acao("Transformar"))
        self.clicar(self.botao("Salvar alterações"))
        novas = self.consultar("SELECT frequencia, ativa FROM series_recorrencia ORDER BY id")
        self.assertEqual(novas, [("mensal", 0), ("anual", 1)])
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos"), pagos)
        self.assertTrue(db.validar_schema_atual()["ok"])


if __name__ == "__main__":
    unittest.main()
