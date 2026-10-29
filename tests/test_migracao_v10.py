"""
Migração v9 -> v10 (Sino 6.10, pagamentos parciais): tabela `pp_pagamentos`
e o índice por conta. Só o schema: nenhuma regra financeira e nenhuma conta
convertida.

Bancos e backups sempre temporários (apoio_banco); o banco real nunca é
aberto. Cobre o banco novo, a migração e a cadeia desde a v5, a preservação
dos dados (inclusive contas já pagas, sem registros), o backup, a execução
repetida, a recusa de estados inesperados (sem escrita e sem backup), a
tabela preexistente compatível ou não, o rollback em falha, a versão futura e
as restrições da tabela.
"""

import os
import sqlite3
import unittest
from unittest import mock

from apoio_banco import _conectar_original, db
from test_migracao_v6 import VERSAO_FUTURA, AuxiliaresBancoV6

# Mesma tabela, formatação diferente (como no protótipo de pagamentos parciais):
# "IF NOT EXISTS" e outra indentação -- o SQLite guarda o texto sem o
# "IF NOT EXISTS" e a comparação ignora o espaçamento.
DDL_COMO_NO_PROTOTIPO = """
    CREATE TABLE IF NOT EXISTS pp_pagamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conta_id INTEGER NOT NULL REFERENCES contas(id),
        valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
        data_pagamento TEXT NOT NULL,
        tipo TEXT NOT NULL CHECK (tipo IN ('parcial', 'saldo', 'integral')),
        registrado_em TEXT NOT NULL,
        estornado_em TEXT
    )
"""
INDICE_COMO_NO_PROTOTIPO = "CREATE INDEX IF NOT EXISTS idx_pp_pagamentos_conta ON pp_pagamentos(conta_id);"


class AuxiliaresV10(AuxiliaresBancoV6):
    def criar_v9(self):
        self.criar_v5()
        for migrar in (db.migrar_schema_v6, db.migrar_schema_v7, db.migrar_schema_v8, db.migrar_schema_v9):
            migrar(self.caminho_v5)
        self.assertEqual(self.versao(self.caminho_v5), 9)

    def versao(self, caminho):
        return self.sql(caminho, "PRAGMA user_version")[0][0]

    def backups_v10(self):
        return [b for b in self.backups() if b.startswith("sino_pre_migracao_v10_")]

    def dados_v9(self, caminho):
        conexao = _conectar_original(caminho)
        try:
            return db._dados_v9(conexao.cursor())
        finally:
            conexao.close()

    def verificar(self, caminho, funcao="_verificar_schema_v10", **kwargs):
        conexao = sqlite3.connect(caminho)
        try:
            return getattr(db, funcao)(conexao.cursor(), **kwargs)
        finally:
            conexao.close()

    def estado_tabela(self, caminho):
        conexao = sqlite3.connect(caminho)
        try:
            return db._estado_tabela_pagamentos(conexao.cursor())
        finally:
            conexao.close()

    def contas_pagas(self, caminho):
        return self.sql(caminho, "SELECT id, valor, status, data_pagamento FROM contas WHERE status = 'pago' "
                                 "ORDER BY id")

    def uma_conta(self, caminho):
        return self.sql(caminho, "SELECT MIN(id) FROM contas")[0][0]

    def criar_tabela_manual(self, ddl=DDL_COMO_NO_PROTOTIPO, indice=INDICE_COMO_NO_PROTOTIPO, linhas=()):
        self.sql(self.caminho_v5, ddl)
        if indice:
            self.sql(self.caminho_v5, indice)
        for linha in linhas:
            self.sql(self.caminho_v5, "INSERT INTO pp_pagamentos (conta_id, valor_centavos, data_pagamento, tipo, "
                                      "registrado_em, estornado_em) VALUES (?, ?, ?, ?, ?, ?)", linha)

    def assert_recusado_v10(self, excecao, regex):
        """Nada muda (schema, linhas, bytes), nenhum backup novo e nenhum lock pendente."""
        schema_antes = self.schema(self.caminho_v5)
        dump_antes = self.dump_completo(self.caminho_v5)
        sha_antes = self.sha256(self.caminho_v5)
        backups_antes = self.backups()
        with self.assertRaisesRegex(excecao, regex) as contexto:
            db.migrar_schema_v10(self.caminho_v5)
        self.assertEqual(self.schema(self.caminho_v5), schema_antes)
        self.assertEqual(self.dump_completo(self.caminho_v5), dump_antes)
        self.assertEqual(self.sha256(self.caminho_v5), sha_antes)
        self.assertEqual(self.backups(), backups_antes)
        self.assert_sem_transacao_nem_lock(self.caminho_v5)
        return contexto.exception

    def assert_schema_v10(self, caminho):
        self.assertEqual(self.versao(caminho), 10)
        self.assertEqual(self.estado_tabela(caminho), "valida")
        resultado = self.verificar(caminho)
        self.assertTrue(resultado["ok"], resultado)


class TestBancoNovoV10(AuxiliaresV10):
    def test_banco_novo_nasce_v10_com_a_tabela_e_o_indice(self):
        caminho = self.caminho_banco                      # criado por criar_tabelas() no setUp
        self.assertEqual(self.versao(caminho), 10)
        self.assertEqual(self.sql(caminho, "PRAGMA table_info(pp_pagamentos)"),
                         [tuple(c) for c in db.COLUNAS_PAGAMENTOS])
        self.assertEqual([tuple(f[2:5]) for f in self.sql(caminho, "PRAGMA foreign_key_list(pp_pagamentos)")],
                         [("contas", "conta_id", "id")])
        self.assertEqual(self.sql(caminho, "SELECT name FROM sqlite_master WHERE type = 'index' "
                                           "AND tbl_name = 'pp_pagamentos'"), [("idx_pp_pagamentos_conta",)])
        self.assertEqual(self.sql(caminho, "SELECT COUNT(*) FROM pp_pagamentos"), [(0,)])
        self.assertTrue(db.validar_schema_atual(caminho)["ok"])

    def test_preparar_banco_inexistente_cria_v10_sem_backup(self):
        caminho = os.path.join(os.path.dirname(self.caminho_banco), "novo.db")
        with mock.patch.object(db, "NOME_DO_BANCO", caminho):
            resultado = db.preparar_banco()
            self.assertEqual(resultado["situacao"], "criado")
            self.assertIsNone(resultado["migracao_v10"])
            self.assertEqual(db.preparar_banco()["situacao"], "atual")   # de novo: nada a fazer
        self.assert_schema_v10(caminho)
        self.assertEqual(self.backups(), [])

    def test_validacao_positiva_e_negativa(self):
        caminho = self.caminho_banco
        self.assertTrue(self.verificar(caminho)["ok"])
        self.sql(caminho, "DROP INDEX idx_pp_pagamentos_conta")
        resultado = self.verificar(caminho)
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["tabela_pagamentos"], "incompativel")
        with self.assertRaisesRegex(db.BancoNaoPreparadoError, "tabela_pagamentos"):
            raise db.BancoNaoPreparadoError(resultado)
        self.sql(caminho, "DROP TABLE pp_pagamentos")
        self.assertEqual(self.verificar(caminho)["tabela_pagamentos"], "ausente")
        self.assertFalse(db.validar_schema_atual(caminho)["ok"])

    def test_banco_novo_e_banco_migrado_tem_o_mesmo_schema(self):
        self.criar_v9()
        db.migrar_schema_v10(self.caminho_v5)

        def objetos(caminho):
            return [(t, n, db._normalizar_ddl(s)) for t, n, s in self.sql(
                caminho, "SELECT type, name, sql FROM sqlite_master WHERE tbl_name = 'pp_pagamentos' "
                         "ORDER BY type, name")]

        self.assertEqual(objetos(self.caminho_banco), objetos(self.caminho_v5))
        self.assertEqual(self.sql(self.caminho_banco, "PRAGMA table_info(pp_pagamentos)"),
                         self.sql(self.caminho_v5, "PRAGMA table_info(pp_pagamentos)"))


class TestMigracaoV10(AuxiliaresV10):
    def test_migra_v9_para_v10_preservando_os_dados(self):
        self.criar_v9()
        dados_antes = self.dados_v9(self.caminho_v5)
        pagas_antes = self.contas_pagas(self.caminho_v5)
        sequencias_antes = self.sql(self.caminho_v5, "SELECT name, seq FROM sqlite_sequence ORDER BY name")
        self.assertTrue(pagas_antes)                                    # o fixture tem contas já pagas

        resultado = db.migrar_schema_v10(self.caminho_v5)

        self.assertTrue(resultado["executado"])
        self.assertFalse(resultado["tabela_reaproveitada"])
        self.assertEqual(self.backups_v10(), [os.path.basename(resultado["backup"])])
        self.assert_schema_v10(self.caminho_v5)
        self.assertEqual(self.dados_v9(self.caminho_v5), dados_antes)
        self.assertEqual(self.contas_pagas(self.caminho_v5), pagas_antes)   # legado: pagas, sem registros
        self.assertEqual(self.sql(self.caminho_v5, "SELECT COUNT(*) FROM pp_pagamentos"), [(0,)])
        self.assertEqual(self.sql(self.caminho_v5, "SELECT name, seq FROM sqlite_sequence ORDER BY name"),
                         sequencias_antes)
        self.assertEqual(self.sql(self.caminho_v5, "PRAGMA integrity_check"), [("ok",)])
        self.assertEqual(self.sql(self.caminho_v5, "PRAGMA foreign_key_check"), [])
        self.assert_sem_transacao_nem_lock(self.caminho_v5)

    def test_backup_e_do_estado_v9_e_integro(self):
        self.criar_v9()
        dump_antes = self.dump_completo(self.caminho_v5)
        resultado = db.migrar_schema_v10(self.caminho_v5)
        backup = resultado["backup"]
        self.assertTrue(db._verificar_integridade_backup(backup))
        self.assertEqual(self.versao(backup), 9)
        self.assertEqual(self.estado_tabela(backup), "ausente")
        self.assertEqual(self.dump_completo(backup), dump_antes)
        self.assertTrue(self.verificar(backup, "_verificar_schema_v9")["ok"])

    def test_cadeia_desde_v5_v6_v7_e_v8_pelo_preparar_banco(self):
        etapas = (db.migrar_schema_v6, db.migrar_schema_v7, db.migrar_schema_v8, db.migrar_schema_v9)
        for inicio in range(0, 5):                                       # v5, v6, v7, v8 e v9
            with self.subTest(versao_inicial=(5, 6, 7, 8, 9)[inicio]):
                for nome in os.listdir(os.path.dirname(self.caminho_v5)):
                    if nome.startswith("sino_v5.db"):
                        os.remove(os.path.join(os.path.dirname(self.caminho_v5), nome))
                self.criar_v5()
                for migrar in etapas[:inicio]:
                    migrar(self.caminho_v5)
                dados_v5 = self.dados_v5(self.caminho_v5)
                with mock.patch.object(db, "NOME_DO_BANCO", self.caminho_v5):
                    resultado = db.preparar_banco()
                self.assertEqual(resultado["situacao"], "migrado")
                self.assertTrue(resultado["migracao_v10"]["executado"])
                self.assert_schema_v10(self.caminho_v5)
                self.assertEqual(self.dados_v5(self.caminho_v5), dados_v5)

    def test_execucao_repetida_nao_altera_nada(self):
        self.criar_v9()
        db.migrar_schema_v10(self.caminho_v5)
        sha, backups = self.sha256(self.caminho_v5), self.backups()
        self.assertEqual(db.migrar_schema_v10(self.caminho_v5),
                         {"executado": False, "motivo": "já migrado", "backup": None})
        with mock.patch.object(db, "NOME_DO_BANCO", self.caminho_v5):
            self.assertEqual(db.preparar_banco()["situacao"], "atual")
        self.assertEqual((self.sha256(self.caminho_v5), self.backups()), (sha, backups))

    def test_migracoes_anteriores_reconhecem_o_banco_v10(self):
        self.criar_v9()
        db.migrar_schema_v10(self.caminho_v5)
        sha = self.sha256(self.caminho_v5)
        for migrar in (db.migrar_schema_v6, db.migrar_schema_v7, db.migrar_schema_v8, db.migrar_schema_v9):
            with self.subTest(migracao=migrar.__name__):
                self.assertFalse(migrar(self.caminho_v5)["executado"])
        self.assertEqual(self.sha256(self.caminho_v5), sha)
        self.assertTrue(db.validar_migracao_v6(self.caminho_v5)["ok"])

    # ------------------------------------------------------------- recusas
    def test_banco_anterior_a_v9_e_recusado(self):
        self.criar_v5()
        for migrar in (db.migrar_schema_v6, db.migrar_schema_v7, db.migrar_schema_v8):
            migrar(self.caminho_v5)
        self.assert_recusado_v10(db.SchemaV10IncompativelError, "precisa passar pela migração v9")

    def test_versao_futura_e_recusada(self):
        self.criar_v9()
        self.sql(self.caminho_v5, f"PRAGMA user_version = {VERSAO_FUTURA}")
        self.assertEqual(VERSAO_FUTURA, 11)
        self.assert_recusado_v10(db.VersaoDeBancoNaoSuportadaError, str(VERSAO_FUTURA))
        with mock.patch.object(db, "NOME_DO_BANCO", self.caminho_v5):
            with self.assertRaises(db.VersaoDeBancoNaoSuportadaError):
                db.preparar_banco()

    def test_banco_v9_invalido_e_recusado(self):
        self.criar_v9()
        self.sql(self.caminho_v5, "DROP TABLE aceites_documentos")
        self.assert_recusado_v10(db.BancoNaoPreparadoError, "tabela_aceites")

    def test_banco_v10_sem_tabela_ou_com_tabela_incompativel_e_recusado(self):
        self.criar_v9()
        self.sql(self.caminho_v5, "PRAGMA user_version = 10")
        self.assert_recusado_v10(db.SchemaV10IncompativelError, "banco v10 com pp_pagamentos ausente")
        self.criar_tabela_manual(indice=None)
        self.assert_recusado_v10(db.SchemaV10IncompativelError, "banco v10 com pp_pagamentos incompativel")

    # ------------------------------------------------------------- tabela preexistente
    def test_tabela_preexistente_compativel_e_reaproveitada_com_os_registros(self):
        self.criar_v9()
        conta = self.uma_conta(self.caminho_v5)
        self.criar_tabela_manual(linhas=[
            (conta, 150_00, "2026-09-05", "parcial", "2026-09-05T10:00:00", None),
            (conta, 50_00, "2026-09-06", "saldo", "2026-09-06T10:00:00", "2026-09-07T09:00:00"),
        ])
        registros_antes = self.sql(self.caminho_v5, "SELECT * FROM pp_pagamentos ORDER BY id")
        dados_antes = self.dados_v9(self.caminho_v5)
        resultado = db.migrar_schema_v10(self.caminho_v5)
        self.assertTrue(resultado["executado"])
        self.assertTrue(resultado["tabela_reaproveitada"])
        self.assert_schema_v10(self.caminho_v5)
        self.assertEqual(self.sql(self.caminho_v5, "SELECT * FROM pp_pagamentos ORDER BY id"), registros_antes)
        self.assertEqual(self.dados_v9(self.caminho_v5), dados_antes)

    def test_tabela_preexistente_incompativel_e_recusada_sem_perder_dados(self):
        conta_valida = (150_00, "2026-09-05", "parcial", "2026-09-05T10:00:00", None)
        casos = {
            "CHECK antigo (sem 'integral')": DDL_COMO_NO_PROTOTIPO.replace("'saldo', 'integral'", "'saldo'"),
            "sem estornado_em": DDL_COMO_NO_PROTOTIPO.replace(",\n        estornado_em TEXT", ""),
            "valor sem CHECK": DDL_COMO_NO_PROTOTIPO.replace(" CHECK (valor_centavos > 0)", ""),
            "chave estrangeira para outra tabela": DDL_COMO_NO_PROTOTIPO.replace("REFERENCES contas(id)",
                                                                                  "REFERENCES usuarios(id)"),
            "coluna a mais": DDL_COMO_NO_PROTOTIPO.replace("estornado_em TEXT", "estornado_em TEXT,\n extra TEXT"),
        }
        for rotulo, ddl in casos.items():
            with self.subTest(caso=rotulo):
                for nome in os.listdir(os.path.dirname(self.caminho_v5)):
                    if nome.startswith("sino_v5.db"):
                        os.remove(os.path.join(os.path.dirname(self.caminho_v5), nome))
                self.criar_v9()
                conta = self.uma_conta(self.caminho_v5)
                self.sql(self.caminho_v5, ddl)
                self.sql(self.caminho_v5, INDICE_COMO_NO_PROTOTIPO)
                colunas = [c[1] for c in self.sql(self.caminho_v5, "PRAGMA table_info(pp_pagamentos)")][1:6]
                self.sql(self.caminho_v5, f"INSERT INTO pp_pagamentos ({', '.join(colunas)}) VALUES (?, ?, ?, ?, ?)",
                         (conta,) + conta_valida[:4])
                self.assert_recusado_v10(db.SchemaV10IncompativelError, "definição diferente")
                self.assertEqual(self.sql(self.caminho_v5, "SELECT COUNT(*) FROM pp_pagamentos"), [(1,)])

    def test_tabela_preexistente_sem_indice_com_indice_extra_ou_gatilho_e_recusada(self):
        self.criar_v9()
        self.criar_tabela_manual(indice=None)
        self.assert_recusado_v10(db.SchemaV10IncompativelError, "definição diferente")
        self.sql(self.caminho_v5, INDICE_COMO_NO_PROTOTIPO)
        self.sql(self.caminho_v5, "CREATE INDEX extra ON pp_pagamentos(data_pagamento)")
        self.assert_recusado_v10(db.SchemaV10IncompativelError, "definição diferente")
        self.sql(self.caminho_v5, "DROP INDEX extra")
        self.sql(self.caminho_v5, "CREATE TRIGGER gatilho AFTER INSERT ON pp_pagamentos BEGIN SELECT 1; END")
        self.assert_recusado_v10(db.SchemaV10IncompativelError, "definição diferente")

    def test_registros_fora_do_formato_sao_recusados(self):
        self.criar_v9()
        conta = self.uma_conta(self.caminho_v5)
        self.criar_tabela_manual()
        invalidos = [
            (conta, 100, "05/09/2026", "parcial", "2026-09-05T10:00:00", None),        # data fora do formato
            (conta, 100, "2026-09-05", "parcial", "ontem", None),                      # registro curto
            (conta, 100, "2026-09-05", "parcial", "2026-09-05T10:00:00", ""),          # estorno vazio
            (conta, 1.5, "2026-09-05", "parcial", "2026-09-05T10:00:00", None),        # centavos não inteiros
        ]
        for linha in invalidos:
            with self.subTest(linha=linha):
                self.sql(self.caminho_v5, "DELETE FROM pp_pagamentos")
                self.sql(self.caminho_v5, "INSERT INTO pp_pagamentos (conta_id, valor_centavos, data_pagamento, "
                                          "tipo, registrado_em, estornado_em) VALUES (?, ?, ?, ?, ?, ?)", linha)
                self.assert_recusado_v10(db.SchemaV10IncompativelError, "fora do formato")

    def test_registro_de_conta_inexistente_e_recusado(self):
        self.criar_v9()
        self.criar_tabela_manual(linhas=[(999_999, 100, "2026-09-05", "parcial", "2026-09-05T10:00:00", None)])
        self.assert_recusado_v10(db.BancoNaoPreparadoError, "violacoes_fk")

    # ------------------------------------------------------------- falhas
    def test_falha_depois_de_criar_a_tabela_reverte_e_mantem_o_backup(self):
        self.criar_v9()
        dump_antes = self.dump_completo(self.caminho_v5)
        verificar_real = db._verificar_schema_v10

        def falhar(cursor, versao_esperada=db.VERSAO_SCHEMA_V10):
            self.assertTrue(db._tabela_existe(cursor, "pp_pagamentos"))   # já criada nesta transação
            raise RuntimeError("falha simulada")

        with mock.patch.object(db, "_verificar_schema_v10", side_effect=falhar):
            with self.assertRaisesRegex(RuntimeError, "falha simulada"):
                db.migrar_schema_v10(self.caminho_v5)

        self.assertEqual(self.versao(self.caminho_v5), 9)
        self.assertEqual(self.dump_completo(self.caminho_v5), dump_antes)
        self.assertEqual(self.estado_tabela(self.caminho_v5), "ausente")
        self.assertEqual(len(self.backups_v10()), 1)
        self.assert_sem_transacao_nem_lock(self.caminho_v5)
        self.assertIs(db._verificar_schema_v10, verificar_real)
        self.assertTrue(db.migrar_schema_v10(self.caminho_v5)["executado"])     # a próxima conclui
        self.assert_schema_v10(self.caminho_v5)

    def test_validacao_final_reprovada_reverte(self):
        self.criar_v9()
        with mock.patch.object(db, "_dados_v9", side_effect=[{"antes": 1}, {"depois": 2}]):
            with self.assertRaisesRegex(RuntimeError, "Validação pós-migração v10"):
                db.migrar_schema_v10(self.caminho_v5)
        self.assertEqual(self.versao(self.caminho_v5), 9)
        self.assertEqual(self.estado_tabela(self.caminho_v5), "ausente")

    def test_backup_corrompido_aborta_sem_alterar(self):
        self.criar_v9()
        dump_antes = self.dump_completo(self.caminho_v5)
        with mock.patch.object(db, "_verificar_integridade_backup", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "integrity_check"):
                db.migrar_schema_v10(self.caminho_v5)
        self.assertEqual(self.dump_completo(self.caminho_v5), dump_antes)
        self.assertEqual(self.versao(self.caminho_v5), 9)

    def test_falha_na_v10_pelo_preparar_banco_deixa_o_banco_em_v9_e_a_proxima_retoma(self):
        self.criar_v9()
        with mock.patch.object(db, "NOME_DO_BANCO", self.caminho_v5):
            with mock.patch.object(db, "_criar_tabela_pagamentos", side_effect=RuntimeError("falha simulada")):
                with self.assertRaisesRegex(RuntimeError, "falha simulada"):
                    db.preparar_banco()
            self.assertEqual(self.versao(self.caminho_v5), 9)
            resultado = db.preparar_banco()
        self.assertEqual(resultado["situacao"], "migrado")
        self.assert_schema_v10(self.caminho_v5)


class TestRestricoesDaTabelaDePagamentos(AuxiliaresV10):
    """Restrições do banco (o banco do teste nasce em v10 via criar_tabelas)."""

    def inserir(self, conta_id, valor=100, tipo="parcial"):
        conexao = _conectar_original(self.caminho_banco)
        try:
            conexao.execute("PRAGMA foreign_keys = ON;")
            conexao.execute("INSERT INTO pp_pagamentos (conta_id, valor_centavos, data_pagamento, tipo, "
                            "registrado_em) VALUES (?, ?, '2026-09-05', ?, '2026-09-05T10:00:00')",
                            (conta_id, valor, tipo))
            conexao.commit()
        finally:
            conexao.close()

    def setUp(self):
        super().setUp()
        usuario = self.criar_usuario(email="restricoes@exemplo.invalid", senha="senha1234")
        db.criar_conta_unica(usuario, "Luz", 100.0, "2026-09-20")
        self.conta = self.sql(self.caminho_banco, "SELECT MAX(id) FROM contas")[0][0]

    def test_registro_valido(self):
        self.inserir(self.conta)
        self.assertEqual(self.sql(self.caminho_banco, "SELECT conta_id, valor_centavos, estornado_em "
                                                      "FROM pp_pagamentos"), [(self.conta, 100, None)])

    def test_valor_nao_positivo_e_recusado(self):
        for valor in (0, -1):
            with self.subTest(valor=valor), self.assertRaises(sqlite3.IntegrityError):
                self.inserir(self.conta, valor=valor)

    def test_tipo_invalido_e_recusado(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.inserir(self.conta, tipo="outro")

    def test_conta_inexistente_e_recusada_com_chaves_estrangeiras_ligadas(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.inserir(999_999)


if __name__ == "__main__":
    unittest.main()
