"""
apoio_banco.py — Infraestrutura comum dos testes de regressão do Sino.

Cada teste roda contra um banco SQLite TEMPORÁRIO (e uma pasta de backups
temporária), criado do zero em setUp e apagado em tearDown. O banco real
(`database/sino.db`) e a pasta real de backups (`database/backups/`) nunca
são tocados:

  1. `db.NOME_DO_BANCO` e `db.PASTA_BACKUPS` são redirecionados para a
     pasta temporária antes de qualquer chamada ao `db.py`;
  2. uma verificação de isolamento falha o teste se algum desses caminhos
     ainda apontar para `database/`;
  3. `sqlite3.connect` é envolvido por uma guarda que recusa abrir o banco
     real — defesa extra caso alguma função passe a abrir o banco por
     outro caminho no futuro.

A data de "hoje" usada pelo `db.py` é fixada (`HOJE`), para que status
atrasado, próximos 7 dias, data futura de pagamento e o corte de
`encerrar_recorrencia` sejam determinísticos.
"""

import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from unittest import mock

RAIZ_PROJETO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PASTA_DATABASE = os.path.join(RAIZ_PROJETO, "database")
BANCO_REAL = os.path.realpath(os.path.join(PASTA_DATABASE, "sino.db"))
PASTA_BACKUPS_REAL = os.path.realpath(os.path.join(PASTA_DATABASE, "backups"))

if PASTA_DATABASE not in sys.path:
    sys.path.insert(0, PASTA_DATABASE)

import db  # noqa: E402

_conectar_original = sqlite3.connect


def _conectar_protegido(caminho, *args, **kwargs):
    if os.path.realpath(str(caminho)) == BANCO_REAL:
        raise AssertionError(f"teste tentou abrir o banco real: {caminho}")
    return _conectar_original(caminho, *args, **kwargs)


class DataFixa(date):
    """`date` com `today()` controlado pelo teste (atributo de classe `hoje`)."""

    hoje = date(2026, 9, 15)

    @classmethod
    def today(cls):
        return cls.hoje


class TesteComBancoTemporario(unittest.TestCase):
    HOJE = date(2026, 9, 15)

    def setUp(self):
        self._pasta_temporaria = tempfile.TemporaryDirectory(prefix="sino_teste_")
        pasta = self._pasta_temporaria.name
        self.caminho_banco = os.path.join(pasta, "sino_teste.db")
        self.pasta_backups = os.path.join(pasta, "backups")

        DataFixa.hoje = self.HOJE
        for alvo, atributo, valor in (
            (db, "NOME_DO_BANCO", self.caminho_banco),
            (db, "PASTA_BACKUPS", self.pasta_backups),
            (db, "date", DataFixa),
            (sqlite3, "connect", _conectar_protegido),
        ):
            patcher = mock.patch.object(alvo, atributo, valor)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self._pasta_temporaria.cleanup)

        self._verificar_isolamento()
        db.criar_tabelas()

    def _verificar_isolamento(self):
        banco = os.path.realpath(db.NOME_DO_BANCO)
        backups = os.path.realpath(db.PASTA_BACKUPS)
        pasta_database = os.path.realpath(PASTA_DATABASE)
        self.assertNotEqual(banco, BANCO_REAL)
        self.assertNotEqual(backups, PASTA_BACKUPS_REAL)
        self.assertFalse(banco.startswith(pasta_database + os.sep))
        self.assertFalse(backups.startswith(pasta_database + os.sep))

    # ------------------------------------------------------------------
    #  Auxiliares
    # ------------------------------------------------------------------
    def definir_hoje(self, nova_data):
        DataFixa.hoje = nova_data

    def consultar(self, sql, parametros=()):
        conexao = _conectar_original(self.caminho_banco)
        try:
            return conexao.execute(sql, parametros).fetchall()
        finally:
            conexao.close()

    def executar(self, sql, parametros=()):
        conexao = _conectar_original(self.caminho_banco)
        try:
            cursor = conexao.execute(sql, parametros)
            conexao.commit()
            return cursor.lastrowid
        finally:
            conexao.close()

    def criar_usuario(self, email="teste@sino.com", senha="senha123", nome="Teste"):
        sucesso, _ = db.criar_usuario(nome, email, senha, aceite_termos=True)
        self.assertTrue(sucesso)
        return self.consultar("SELECT id FROM usuarios WHERE email = ?", (email,))[0][0]

    def criar_categoria(self, usuario_id, nome="Casa"):
        return db.criar_categoria(usuario_id, nome, "🏡")

    def ocorrencias(self, serie_id):
        """Lista (id, data_vencimento, nome, valor, categoria_id, editado_individualmente) em ordem."""
        return self.consultar(
            """
            SELECT id, data_vencimento, nome, valor, categoria_id, editado_individualmente
            FROM contas WHERE serie_id = ? ORDER BY data_vencimento
            """,
            (serie_id,),
        )

    def datas(self, serie_id):
        return [linha[1] for linha in self.ocorrencias(serie_id)]

    def serie(self, serie_id):
        linhas = self.consultar(
            """
            SELECT nome, valor, categoria_id, frequencia, dia_ancora, mes_ancora,
                   data_inicio, data_termino, ativa, horizonte_gerado_ate
            FROM series_recorrencia WHERE id = ?
            """,
            (serie_id,),
        )
        if not linhas:
            return None
        chaves = ("nome", "valor", "categoria_id", "frequencia", "dia_ancora", "mes_ancora",
                  "data_inicio", "data_termino", "ativa", "horizonte_gerado_ate")
        return dict(zip(chaves, linhas[0]))

    def conta(self, conta_id):
        linhas = self.consultar(
            """
            SELECT nome, valor, data_vencimento, status, categoria_id, serie_id,
                   data_pagamento, editado_individualmente
            FROM contas WHERE id = ?
            """,
            (conta_id,),
        )
        if not linhas:
            return None
        chaves = ("nome", "valor", "data_vencimento", "status", "categoria_id", "serie_id",
                  "data_pagamento", "editado_individualmente")
        return dict(zip(chaves, linhas[0]))

    def id_por_data(self, serie_id, data_iso):
        linhas = self.consultar(
            "SELECT id FROM contas WHERE serie_id = ? AND data_vencimento = ?",
            (serie_id, data_iso),
        )
        self.assertEqual(len(linhas), 1, f"esperava 1 ocorrência em {data_iso}")
        return linhas[0][0]
