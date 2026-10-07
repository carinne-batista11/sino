"""
Migração v7 -> v8 (ERS v6.0, Etapa 8): tabela `autorizacoes_usadas`.

Bancos e backups sempre temporários (apoio_banco); o banco real nunca é
aberto. Cobre a criação, a preservação dos dados, o backup, a recusa de
estados inesperados (sem escrita e sem backup), o rollback em falha e as
restrições da tabela.
"""

import os
import unittest
from unittest import mock

from apoio_banco import _conectar_original, db
from test_migracao_v6 import VERSAO_FUTURA, AuxiliaresBancoV6

JTI = "QUFBQUFBQUFBQUFBQUFBQQ"  # 16 bytes em base64url canônico


class TesteMigracaoV8(AuxiliaresBancoV6):
    def criar_v7(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)
        db.migrar_schema_v7(self.caminho_v5)

    def backups_v8(self):
        return [b for b in self.backups() if b.startswith("sino_pre_migracao_v8_")]

    def dados_v7(self, caminho):
        conexao = _conectar_original(caminho)
        try:
            return db._dados_v7(conexao.cursor())
        finally:
            conexao.close()

    def assert_recusado_v8(self, excecao, regex):
        """Nada muda (schema, linhas, bytes), nenhum backup novo e nenhum lock pendente."""
        schema_antes = self.schema(self.caminho_v5)
        dump_antes = self.dump_completo(self.caminho_v5)
        sha_antes = self.sha256(self.caminho_v5)
        backups_antes = self.backups()
        with self.assertRaisesRegex(excecao, regex) as contexto:
            db.migrar_schema_v8(self.caminho_v5)
        self.assertEqual(self.schema(self.caminho_v5), schema_antes)
        self.assertEqual(self.dump_completo(self.caminho_v5), dump_antes)
        self.assertEqual(self.sha256(self.caminho_v5), sha_antes)
        self.assertEqual(self.backups(), backups_antes)
        self.assert_sem_transacao_nem_lock(self.caminho_v5)
        return contexto.exception

    def criar_tabela_manual(self, ddl=None, indice=True, linhas=()):
        self.sql(self.caminho_v5, ddl or db.DDL_AUTORIZACOES)
        if indice:
            self.sql(self.caminho_v5, db.DDL_INDICE_AUTORIZACOES)
        for linha in linhas:
            self.sql(self.caminho_v5, "INSERT INTO autorizacoes_usadas VALUES (?, ?, ?)", linha)

    # ------------------------------------------------------------------
    #  v7 -> v8
    # ------------------------------------------------------------------
    def test_migra_v7_para_v8_preservando_os_dados(self):
        self.criar_v7()
        dados_antes = self.dados_v7(self.caminho_v5)
        sequencias_antes = self.sql(self.caminho_v5, "SELECT name, seq FROM sqlite_sequence ORDER BY name")
        verificados_antes = self.sql(self.caminho_v5, "SELECT id, email_verificado FROM usuarios ORDER BY id")

        resultado = db.migrar_schema_v8(self.caminho_v5)

        self.assertTrue(resultado["executado"])
        self.assertFalse(resultado["tabela_reaproveitada"])
        self.assertEqual(self.backups_v8(), [os.path.basename(resultado["backup"])])
        self.assert_schema_v8(self.caminho_v5)
        self.assertTrue(self.validar_schema_v8(self.caminho_v5)["ok"])
        self.assertEqual(self.dados_v7(self.caminho_v5), dados_antes)
        self.assertEqual(self.sql(self.caminho_v5, "SELECT name, seq FROM sqlite_sequence ORDER BY name"),
                         sequencias_antes)
        # Contas antigas de teste continuam não verificadas (P2).
        self.assertEqual(self.sql(self.caminho_v5, "SELECT id, email_verificado FROM usuarios ORDER BY id"),
                         verificados_antes)
        self.assertEqual(self.sql(self.caminho_v5, "SELECT COUNT(*) FROM autorizacoes_usadas"), [(0,)])
        self.assert_sem_transacao_nem_lock(self.caminho_v5)

    def test_backup_e_do_estado_v7_e_integro(self):
        self.criar_v7()
        dump_v7 = self.dump_completo(self.caminho_v5)
        resultado = db.migrar_schema_v8(self.caminho_v5)
        backup = os.path.join(self.pasta_backups, os.path.basename(resultado["backup"]))
        self.assertEqual(self.sql(backup, "PRAGMA user_version")[0][0], 7)
        self.assertEqual(self.sql(backup, "PRAGMA integrity_check"), [("ok",)])
        self.assertEqual(self.dump_completo(backup), dump_v7)

    def test_execucao_repetida_nao_altera_nada(self):
        self.criar_v7()
        db.migrar_schema_v8(self.caminho_v5)
        sha, backups = self.sha256(self.caminho_v5), self.backups()
        self.assertEqual(db.migrar_schema_v8(self.caminho_v5),
                         {"executado": False, "motivo": "já migrado", "backup": None})
        self.assertEqual((self.sha256(self.caminho_v5), self.backups()), (sha, backups))

    def test_banco_novo_e_banco_migrado_tem_o_mesmo_schema(self):
        self.criar_v7()
        db.migrar_schema_v8(self.caminho_v5)
        consulta = ("SELECT type, name, sql FROM sqlite_master "
                    "WHERE tbl_name = 'autorizacoes_usadas' ORDER BY name")
        self.assertEqual(self.sql(self.caminho_v5, consulta), self.sql(self.caminho_banco, consulta))
        # O banco novo já nasce no schema atual (v9), que contém a tabela da v8.
        self.assertEqual(self.sql(self.caminho_banco, "PRAGMA user_version")[0][0], db.VERSAO_SCHEMA_V9)

    def test_migracao_v7_reconhece_banco_v8_como_migrado(self):
        self.criar_v7()
        db.migrar_schema_v8(self.caminho_v5)
        self.assertEqual(db.migrar_schema_v7(self.caminho_v5)["motivo"], "já migrado")
        self.assertEqual(db.migrar_schema_v6(self.caminho_v5)["motivo"], "já migrado")

    # ------------------------------------------------------------------
    #  Tabela já existente num banco v7: conferida, nunca presumida
    # ------------------------------------------------------------------
    def test_v7_com_tabela_identica_e_dados_validos_e_reaproveitada(self):
        self.criar_v7()
        self.criar_tabela_manual(linhas=[(JTI, "cadastro", 1_790_000_600)])
        resultado = db.migrar_schema_v8(self.caminho_v5)
        self.assertTrue(resultado["executado"])
        self.assertTrue(resultado["tabela_reaproveitada"])
        self.assertEqual(self.sql(self.caminho_v5, "SELECT * FROM autorizacoes_usadas"),
                         [(JTI, "cadastro", 1_790_000_600)])
        self.assert_schema_v8(self.caminho_v5)

    def test_v7_com_tabela_sem_not_null_e_recusado(self):
        self.criar_v7()
        self.criar_tabela_manual(db.DDL_AUTORIZACOES.replace("jti TEXT NOT NULL PRIMARY KEY", "jti TEXT PRIMARY KEY"))
        self.assert_recusado_v8(db.SchemaV8IncompativelError, "definição diferente")

    def test_v7_com_check_diferente_e_recusado(self):
        self.criar_v7()
        self.criar_tabela_manual(db.DDL_AUTORIZACOES.replace("AND expira_em > 0", "AND expira_em >= 0"))
        self.assert_recusado_v8(db.SchemaV8IncompativelError, "definição diferente")

    def test_v7_com_tabela_sem_indice_ou_com_indice_extra_ou_gatilho_e_recusado(self):
        casos = {
            "sem_indice": lambda: self.criar_tabela_manual(indice=False),
            "indice_extra": lambda: (self.criar_tabela_manual(),
                                     self.sql(self.caminho_v5, "CREATE INDEX extra ON autorizacoes_usadas(finalidade)")),
            "gatilho": lambda: (self.criar_tabela_manual(), self.sql(
                self.caminho_v5,
                "CREATE TRIGGER t AFTER INSERT ON autorizacoes_usadas BEGIN SELECT 1; END")),
            "so_indice": lambda: (self.sql(self.caminho_v5, "CREATE TABLE outra (expira_em INTEGER)"),
                                  self.sql(self.caminho_v5,
                                           f"CREATE INDEX {db.INDICE_AUTORIZACOES_EXPIRA} ON outra(expira_em)")),
        }
        for nome, preparar in casos.items():
            with self.subTest(caso=nome):
                if os.path.exists(self.caminho_v5):
                    os.remove(self.caminho_v5)
                for backup in self.backups():
                    os.remove(os.path.join(self.pasta_backups, backup))
                self.criar_v7()
                preparar()
                self.assert_recusado_v8(db.SchemaV8IncompativelError, "definição diferente")

    def test_v7_com_dados_fora_do_formato_e_recusado(self):
        self.criar_v7()
        self.criar_tabela_manual()
        # Linha gravada por fora das restrições (simula dados inconsistentes).
        conexao = _conectar_original(self.caminho_v5)
        try:
            conexao.execute("PRAGMA ignore_check_constraints = ON")
            conexao.execute("INSERT INTO autorizacoes_usadas VALUES ('curto', 'cadastro', 10)")
            conexao.commit()
        finally:
            conexao.close()
        self.assert_recusado_v8(db.SchemaV8IncompativelError, "fora do formato")

    # ------------------------------------------------------------------
    #  Outros estados recusados
    # ------------------------------------------------------------------
    def test_banco_v6_e_recusado(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)
        self.assert_recusado_v8(db.SchemaV8IncompativelError, "migração v7 antes da v8")

    def test_versao_futura_e_recusada(self):
        self.criar_v7()
        self.sql(self.caminho_v5, f"PRAGMA user_version = {VERSAO_FUTURA}")
        self.assert_recusado_v8(db.VersaoDeBancoNaoSuportadaError, str(VERSAO_FUTURA))

    def test_banco_v8_sem_tabela_ou_com_tabela_incompativel_e_recusado(self):
        self.criar_v7()
        self.sql(self.caminho_v5, "PRAGMA user_version = 8")
        self.assert_recusado_v8(db.SchemaV8IncompativelError, "banco v8 com autorizacoes_usadas ausente")
        self.criar_tabela_manual(indice=False)
        self.assert_recusado_v8(db.SchemaV8IncompativelError, "banco v8 com autorizacoes_usadas incompativel")
        self.assertFalse(db.validar_schema_atual(self.caminho_v5)["ok"])

    # ------------------------------------------------------------------
    #  Falhas durante a migração
    # ------------------------------------------------------------------
    def test_falha_depois_de_criar_a_tabela_reverte_e_mantem_o_backup(self):
        self.criar_v7()
        dump_antes = self.dump_completo(self.caminho_v5)
        verificar_real = db._verificar_schema_v8

        def falhar(cursor):
            # A tabela já foi criada nesta transação quando a validação roda.
            self.assertTrue(db._tabela_existe(cursor, "autorizacoes_usadas"))
            raise RuntimeError("falha simulada")

        with mock.patch.object(db, "_verificar_schema_v8", side_effect=falhar):
            with self.assertRaisesRegex(RuntimeError, "falha simulada"):
                db.migrar_schema_v8(self.caminho_v5)

        self.assertEqual(self.sql(self.caminho_v5, "PRAGMA user_version")[0][0], 7)
        self.assertEqual(self.dump_completo(self.caminho_v5), dump_antes)
        self.assertEqual(len(self.backups_v8()), 1)
        self.assert_sem_transacao_nem_lock(self.caminho_v5)
        self.assertIs(db._verificar_schema_v8, verificar_real)
        # A próxima tentativa conclui normalmente.
        self.assertTrue(db.migrar_schema_v8(self.caminho_v5)["executado"])
        self.assert_schema_v8(self.caminho_v5)

    def test_validacao_final_reprovada_reverte(self):
        self.criar_v7()
        with mock.patch.object(db, "_dados_v7", side_effect=[{"antes": 1}, {"depois": 2}]):
            with self.assertRaisesRegex(RuntimeError, "Validação pós-migração v8"):
                db.migrar_schema_v8(self.caminho_v5)
        self.assertEqual(self.sql(self.caminho_v5, "PRAGMA user_version")[0][0], 7)
        self.assertFalse(self.sql(self.caminho_v5,
                                  "SELECT 1 FROM sqlite_master WHERE name = 'autorizacoes_usadas'"))

    def test_backup_corrompido_aborta_sem_alterar(self):
        self.criar_v7()
        dump_antes = self.dump_completo(self.caminho_v5)
        with mock.patch.object(db, "_verificar_integridade_backup", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "integrity_check"):
                db.migrar_schema_v8(self.caminho_v5)
        self.assertEqual(self.dump_completo(self.caminho_v5), dump_antes)
        self.assertEqual(self.sql(self.caminho_v5, "PRAGMA user_version")[0][0], 7)


class TesteRestricoesDaTabela(AuxiliaresBancoV6):
    """Restrições do banco (o banco do teste nasce em v8 via criar_tabelas)."""

    def inserir(self, jti, finalidade="cadastro", expira=1_790_000_600):
        self.sql(self.caminho_banco, "INSERT INTO autorizacoes_usadas VALUES (?, ?, ?)", (jti, finalidade, expira))

    def test_registro_valido(self):
        self.inserir(JTI)
        self.assertEqual(self.sql(self.caminho_banco, "SELECT typeof(jti), typeof(expira_em) FROM autorizacoes_usadas"),
                         [("text", "integer")])

    def test_jti_invalido_e_recusado(self):
        for jti in (None, "QUFBQUFBQUFBQUFBQUFBQB", "QUFBQUFBQUFBQUFBQUFBQ", "QUFBQUFBQUFBQUFBQUFBQ=",
                    "QUFBQUFBQUFBQUFBQUF+QQ", 12345):
            with self.subTest(jti=jti):
                with self.assertRaises(db.sqlite3.IntegrityError):
                    self.inserir(jti)

    def test_finalidade_invalida_e_recusada(self):
        for finalidade in (None, "login", "Cadastro"):
            with self.subTest(finalidade=finalidade):
                with self.assertRaises(db.sqlite3.IntegrityError):
                    self.inserir(JTI, finalidade=finalidade)

    def test_expira_em_que_continua_invalido_depois_da_conversao(self):
        # Afinidade INTEGER: '123' viraria inteiro antes do CHECK; estes não viram.
        for valor in ("abc", "1.5", 1.5, 0, "0", -5, None):
            with self.subTest(valor=valor):
                with self.assertRaises(db.sqlite3.IntegrityError):
                    self.inserir(JTI, expira=valor)

    def test_jti_repetido_e_recusado(self):
        self.inserir(JTI)
        with self.assertRaises(db.sqlite3.IntegrityError):
            self.inserir(JTI, finalidade="recuperacao_senha")


if __name__ == "__main__":
    unittest.main()
