"""
Sino 6.12 (experimental), Etapa 2 -- gravação atômica (D14).

`db.transacao()` abre UMA transação explícita; os núcleos `_..._no_cursor`
(criar série, transformar em recorrente, editar ocorrência) gravam só no cursor
recebido. Estes testes conferem: COMMIT ao terminar; ROLLBACK integral em
qualquer falha (Exception e BaseException), inclusive quando várias operações
são compostas na mesma transação; e que as funções públicas continuam
devolvendo o mesmo resultado da Sino 6.11 (o restante da suíte cobre as regras).
"""

import unittest
from unittest import mock

from apoio_banco import TesteComBancoTemporario, db


class Interrupcao(BaseException):
    """Simula uma interrupção que não é Exception (como KeyboardInterrupt)."""


class BaseAtomicidade(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def estado(self):
        return (self.consultar("SELECT * FROM contas ORDER BY id"),
                self.consultar("SELECT * FROM series_recorrencia ORDER BY id"),
                self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"))


class TestTransacao(BaseAtomicidade):
    def test_commit_ao_terminar(self):
        with db.transacao() as cursor:
            cursor.execute("INSERT INTO contas (usuario_id, nome, valor, data_vencimento) VALUES (?, 'A', 10, "
                           "'2026-09-20')", (self.usuario_id,))
        self.assertEqual(self.consultar("SELECT nome FROM contas"), [("A",)])

    def test_rollback_em_excecao(self):
        antes = self.estado()
        with self.assertRaises(RuntimeError):
            with db.transacao() as cursor:
                cursor.execute("INSERT INTO contas (usuario_id, nome, valor, data_vencimento) VALUES (?, 'A', 10, "
                               "'2026-09-20')", (self.usuario_id,))
                raise RuntimeError("falha simulada")
        self.assertEqual(self.estado(), antes)

    def test_rollback_em_base_exception(self):
        antes = self.estado()
        with self.assertRaises(Interrupcao):
            with db.transacao() as cursor:
                cursor.execute("INSERT INTO contas (usuario_id, nome, valor, data_vencimento) VALUES (?, 'A', 10, "
                               "'2026-09-20')", (self.usuario_id,))
                raise Interrupcao()
        self.assertEqual(self.estado(), antes)

    def test_excecao_original_nao_e_mascarada(self):
        with self.assertRaisesRegex(ValueError, "original"):
            with db.transacao():
                raise ValueError("original")

    def test_chaves_estrangeiras_ligadas(self):
        with db.transacao() as cursor:
            self.assertEqual(cursor.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_conexao_fechada_depois(self):
        conexoes = []
        original = db.conectar

        def conectar_registrando():
            conexao = original()
            conexoes.append(conexao)
            return conexao

        with mock.patch.object(db, "conectar", conectar_registrando):
            with db.transacao() as cursor:
                cursor.execute("SELECT 1")
        with self.assertRaises(Exception):
            conexoes[0].execute("SELECT 1")  # fechada


class TestComposicao(BaseAtomicidade):
    def test_duas_operacoes_desfeitas_juntas(self):
        conta = db.criar_conta_unica(self.usuario_id, "Luz", 100.0, "2026-09-10")
        antes = self.estado()
        with self.assertRaises(RuntimeError):
            with db.transacao() as cursor:
                db._criar_serie_recorrente_no_cursor(cursor, self.usuario_id, "Aluguel", 900.0, "2026-09-05",
                                                     "mensal", data_termino="2026-12")
                db._editar_conta_ocorrencia_no_cursor(cursor, conta, valor=150.0)
                raise RuntimeError("falha depois das duas operações")
        self.assertEqual(self.estado(), antes)

    def test_duas_operacoes_confirmadas_juntas(self):
        conta = db.criar_conta_unica(self.usuario_id, "Luz", 100.0, "2026-09-10")
        with db.transacao() as cursor:
            serie_id, ids = db._transformar_em_recorrente_no_cursor(cursor, conta, "mensal", data_termino="2026-11")
            db._editar_conta_ocorrencia_no_cursor(cursor, ids[-1], valor=130.0)
        self.assertEqual(self.consultar("SELECT valor FROM contas WHERE serie_id = ? ORDER BY posicao", (serie_id,)),
                         [(100.0,), (100.0,), (130.0,)])

    def test_transformar_desfeito_por_falha_posterior(self):
        conta = db.criar_conta_unica(self.usuario_id, "Luz", 100.0, "2026-09-10")
        antes = self.estado()
        with self.assertRaises(Interrupcao):
            with db.transacao() as cursor:
                db._transformar_em_recorrente_no_cursor(cursor, conta, "anual")
                raise Interrupcao()
        self.assertEqual(self.estado(), antes)
        self.assertEqual(self.consultar("SELECT serie_id, posicao FROM contas WHERE id = ?", (conta,)), [(None, None)])

    def test_nucleos_nao_confirmam_sozinhos(self):
        with self.assertRaises(RuntimeError):
            with db.transacao() as cursor:
                db._criar_serie_recorrente_no_cursor(cursor, self.usuario_id, "Água", 80.0, "2026-09-12", "mensal")
                self.assertTrue(cursor.connection.in_transaction)  # o núcleo não confirmou nada
                raise RuntimeError("falha")
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM series_recorrencia"), [(0,)])


class TestFalhaNoMeioDasFuncoesPublicas(BaseAtomicidade):
    def test_criar_serie_falha_na_terceira_ocorrencia(self):
        antes = self.estado()
        original = db._inserir_ocorrencia
        chamadas = []

        def inserir_e_falhar(*args, **kwargs):
            chamadas.append(1)
            if len(chamadas) == 3:
                raise RuntimeError("falha simulada")
            return original(*args, **kwargs)

        with mock.patch.object(db, "_inserir_ocorrencia", inserir_e_falhar):
            with self.assertRaises(RuntimeError):
                db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-05", "mensal",
                                          data_termino="2027-02")
        self.assertEqual(self.estado(), antes)

    def test_transformar_falha_depois_de_vincular_a_ancora(self):
        conta = db.criar_conta_unica(self.usuario_id, "Luz", 100.0, "2026-09-10")
        antes = self.estado()
        with mock.patch.object(db, "_inserir_ocorrencia", side_effect=Interrupcao()):
            with self.assertRaises(Interrupcao):
                db.transformar_em_recorrente(conta, "mensal")
        self.assertEqual(self.estado(), antes)

    def test_editar_falha_depois_do_update(self):
        conta = db.criar_conta_unica(self.usuario_id, "Luz", 100.0, "2026-09-10")
        antes = self.estado()
        with mock.patch.object(db, "_sincronizar_quitacao", side_effect=Interrupcao()):
            with self.assertRaises(Interrupcao):
                db.editar_conta_ocorrencia(conta, valor=150.0, nome="Energia")
        self.assertEqual(self.estado(), antes)


class TestResultadosPublicosIguais(BaseAtomicidade):
    def test_criar_serie(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-01-31", "mensal",
                                                  data_termino="2026-04")
        self.assertEqual(len(ids), 4)
        self.assertEqual(self.consultar("SELECT data_vencimento, posicao, data_prevista FROM contas ORDER BY id"),
                         [("2026-01-31", 1, "2026-01-31"), ("2026-02-28", 2, "2026-02-28"),
                          ("2026-03-31", 3, "2026-03-31"), ("2026-04-30", 4, "2026-04-30")])

    def test_transformar(self):
        conta = db.criar_conta_unica(self.usuario_id, "Luz", 100.0, "2026-09-10")
        serie_id, ids = db.transformar_em_recorrente(conta, "mensal", data_termino="2026-11")
        self.assertEqual(len(ids), 2)
        with self.assertRaises(ValueError):
            db.transformar_em_recorrente(conta, "mensal")  # já pertence a série ativa
        with self.assertRaises(ValueError):
            db.transformar_em_recorrente(999, "mensal")

    def test_editar(self):
        self.assertFalse(db.editar_conta_ocorrencia(999, nome="X"))
        conta = db.criar_conta_unica(self.usuario_id, "Luz", 100.0, "2026-09-10")
        self.assertTrue(db.editar_conta_ocorrencia(conta))  # nada a alterar
        self.assertTrue(db.editar_conta_ocorrencia(conta, nome="Energia", valor=120.0))
        self.assertEqual(self.consultar("SELECT nome, valor, editado_individualmente FROM contas"),
                         [("Energia", 120.0, 0)])


if __name__ == "__main__":
    unittest.main()
