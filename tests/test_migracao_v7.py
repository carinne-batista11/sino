"""
Migração de schema v6 → v7 (ERS v6.0, Etapa 2b): posição lógica das
ocorrências de série (`contas.posicao`, `contas.data_prevista`,
`series_recorrencia.posicao_ancora`), com backup, transação, validação,
idempotência e recusa (D3) quando a vaga de uma ocorrência antiga não é
inferível.

Os bancos v6 nascem do DDL v5 congelado em `fixture_schema_v5` + a
migração v6 real, sempre na pasta temporária do teste.
"""

import os
import sqlite3
import unittest
from unittest import mock

from apoio_banco import _conectar_original, db
from test_migracao_v6 import VERSAO_FUTURA, AuxiliaresBancoV6


class TesteMigracaoV7(AuxiliaresBancoV6):
    def criar_v6(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)
        self.backups_v6 = self.backups()

    def backups_v7(self):
        return [b for b in self.backups() if b.startswith("sino_pre_migracao_v7_")]

    def posicoes(self, serie_id):
        return self.sql(self.caminho_v5,
                        "SELECT id, posicao, data_prevista, data_vencimento FROM contas "
                        "WHERE serie_id = ? ORDER BY posicao", (serie_id,))

    def assert_recusa_v7(self, excecao, regex=None):
        schema_antes = self.schema(self.caminho_v5)
        dump_antes = self.dump_completo(self.caminho_v5)
        sha_antes = self.sha256(self.caminho_v5)
        backups_antes = self.backups()

        with self.assertRaises(excecao) as contexto:
            db.migrar_schema_v7(self.caminho_v5)

        if regex:
            self.assertRegex(str(contexto.exception), regex)
        self.assertEqual(self.schema(self.caminho_v5), schema_antes)
        self.assertEqual(self.dump_completo(self.caminho_v5), dump_antes)
        self.assertEqual(self.sha256(self.caminho_v5), sha_antes)
        self.assertEqual(self.backups(), backups_antes)  # recusa antes do backup
        self.assert_sem_transacao_nem_lock(self.caminho_v5)
        return contexto.exception

    # ------------------------------------------------------------------
    #  Caminho feliz
    # ------------------------------------------------------------------
    def test_migra_v6_para_v7_preenchendo_posicao_e_vaga(self):
        self.criar_v6()
        dados_antes = self.dados_v5(self.caminho_v5)

        resultado = db.migrar_schema_v7(self.caminho_v5)

        self.assertTrue(resultado["executado"])
        self.assertEqual(self.backups_v7(), [os.path.basename(resultado["backup"])])
        self.assertEqual(resultado["ocorrencias_provaveis"], [101])  # editada, vaga pela competência
        self.assert_schema_v7(self.caminho_v5)
        self.assertEqual(self.dados_v5(self.caminho_v5), dados_antes)
        self.assertTrue(self.validar_schema_v7(self.caminho_v5)["ok"])

        # posição = ordem (vencimento, id); vaga = vencimento
        self.assertEqual(self.posicoes(20), [(100, 1, "2026-08-31", "2026-08-31"),
                                             (101, 2, "2026-09-30", "2026-09-30")])
        self.assertEqual(self.posicoes(21), [(102, 1, "2028-02-29", "2028-02-29"),
                                             (103, 2, "2029-02-28", "2029-02-28")])
        self.assertEqual(self.posicoes(22), [(105, 1, "2026-09-05", "2026-09-05")])
        avulsas = self.sql(self.caminho_v5,
                           "SELECT posicao, data_prevista FROM contas WHERE serie_id IS NULL")
        self.assertEqual(set(avulsas), {(None, None)})
        ancoras = self.sql(self.caminho_v5, "SELECT id, posicao_ancora FROM series_recorrencia ORDER BY id")
        self.assertEqual(ancoras, [(20, 1), (21, 1), (22, 1)])

    def test_backup_e_do_estado_v6_e_integro(self):
        self.criar_v6()
        dump_v6 = self.dump_completo(self.caminho_v5)
        resultado = db.migrar_schema_v7(self.caminho_v5)
        backup = os.path.join(self.pasta_backups, os.path.basename(resultado["backup"]))
        self.assertEqual(self.sql(backup, "PRAGMA user_version")[0][0], 6)
        self.assertEqual(self.dump_completo(backup), dump_v6)
        self.assertEqual(self.sql(backup, "PRAGMA integrity_check"), [("ok",)])

    def test_serie_sem_ocorrencias_recebe_ancora_zero(self):
        self.criar_v6()
        self.sql(self.caminho_v5, "DELETE FROM contas WHERE serie_id = 22")
        db.migrar_schema_v7(self.caminho_v5)
        self.assertEqual(self.sql(self.caminho_v5,
                                  "SELECT posicao_ancora FROM series_recorrencia WHERE id = 22"), [(0,)])

    def test_execucao_repetida_nao_altera_nada(self):
        self.criar_v6()
        db.migrar_schema_v7(self.caminho_v5)
        sha, backups = self.sha256(self.caminho_v5), self.backups()

        resultado = db.migrar_schema_v7(self.caminho_v5)

        self.assertEqual(resultado, {"executado": False, "motivo": "já migrado", "backup": None})
        self.assertEqual((self.sha256(self.caminho_v5), self.backups()), (sha, backups))
        self.assert_sem_transacao_nem_lock(self.caminho_v5)

    def test_banco_migrado_e_banco_novo_tem_o_mesmo_schema(self):
        self.criar_v6()
        db.migrar_schema_v7(self.caminho_v5)
        for tabela in ("usuarios", "categorias", "series_recorrencia", "contas"):
            self.assertEqual(self.colunas(self.caminho_v5, tabela), self.colunas(self.caminho_banco, tabela))
        self.assert_schema_v9(self.caminho_banco)

    def test_operacoes_funcionam_sobre_o_banco_migrado(self):
        self.criar_v6()
        db.migrar_schema_v7(self.caminho_v5)
        with mock.patch.object(db, "NOME_DO_BANCO", self.caminho_v5):
            self.assertEqual(db.obter_parcela(20, 101), (2, 2))
            self.assertTrue(db.editar_conta_serie(100, valor=1700.0))
        valores = self.sql(self.caminho_v5, "SELECT id, valor FROM contas WHERE serie_id = 20 ORDER BY id")
        self.assertEqual(valores, [(100, 1700.0), (101, 1700.0)])

    # ------------------------------------------------------------------
    #  D3: vaga não inferível -> recusa com diagnóstico
    # ------------------------------------------------------------------
    def test_editada_fora_da_grade_recusa_com_diagnostico(self):
        self.criar_v6()
        # 101 (editada) movida para 2027-02-10: fora da grade da série 20,
        # cujo horizonte é 2026-12-31
        self.sql(self.caminho_v5, "UPDATE contas SET data_vencimento = '2027-02-10' WHERE id = 101")
        erro = self.assert_recusa_v7(db.VagasNaoInferiveisError, "conta 101")
        self.assertEqual(erro.diagnostico, [(101, 20, "fora das competências da grade atual")])

    def test_editada_anterior_a_ancora_recusa(self):
        self.criar_v6()
        self.sql(self.caminho_v5, "UPDATE contas SET editado_individualmente = 1 WHERE id = 102")
        self.sql(self.caminho_v5, "UPDATE series_recorrencia SET data_inicio = '2029-02-28' WHERE id = 21")
        erro = self.assert_recusa_v7(db.VagasNaoInferiveisError)
        self.assertEqual([(c, s) for c, s, _ in erro.diagnostico], [(102, 21)])

    def test_editada_em_competencia_compartilhada_recusa(self):
        self.criar_v6()
        self.sql(self.caminho_v5, "UPDATE contas SET data_vencimento = '2026-08-15' WHERE id = 101")
        erro = self.assert_recusa_v7(db.VagasNaoInferiveisError)
        self.assertEqual(erro.diagnostico[0][2], "competência compartilhada com outra ocorrência")

    # ------------------------------------------------------------------
    #  Estados recusados antes de qualquer escrita
    # ------------------------------------------------------------------
    def test_banco_v5_precisa_da_v6_antes(self):
        self.criar_v5()
        self.assert_recusa_v7(db.SchemaV7IncompativelError, "migração v6 antes")

    def test_itens_v7_presentes_num_banco_v6_sao_recusados(self):
        self.criar_v6()
        self.sql(self.caminho_v5, "ALTER TABLE contas ADD COLUMN posicao INTEGER")
        self.assert_recusa_v7(db.SchemaV7IncompativelError, "já presentes num banco v6")

    def test_coluna_v7_com_definicao_diferente_e_recusada(self):
        self.criar_v6()
        self.sql(self.caminho_v5, "ALTER TABLE contas ADD COLUMN data_prevista INTEGER")
        self.assert_recusa_v7(db.SchemaV7IncompativelError, "contas.data_prevista")

    def test_versao_futura_e_recusada(self):
        self.criar_v6()
        self.sql(self.caminho_v5, f"PRAGMA user_version = {VERSAO_FUTURA}")
        self.assert_recusa_v7(db.VersaoDeBancoNaoSuportadaError)

    def test_banco_v6_com_violacao_de_fk_e_recusado(self):
        self.criar_v6()
        self.sql(self.caminho_v5, "INSERT INTO contas (usuario_id, nome, valor, data_vencimento) "
                                  "VALUES (999, 'Órfã', 1.0, '2026-10-01')")
        self.assert_recusa_v7(db.BancoNaoPreparadoError, "violacoes_fk")

    def test_coluna_desconhecida_num_v7_nao_e_aceita(self):
        # M1: antes, um v7 com uma coluna fora do schema passava como "atual".
        self.criar_v6()
        db.migrar_schema_v7(self.caminho_v5)
        self.sql(self.caminho_v5, "ALTER TABLE contas ADD COLUMN extra TEXT")

        validacao = db.validar_schema_atual(self.caminho_v5)
        self.assertFalse(validacao["ok"])
        self.assertTrue(validacao["colunas_fora_do_schema"])
        self.assert_recusa_v7(db.SchemaV7IncompativelError, "desconhecidas: extra")
        with mock.patch.object(db, "NOME_DO_BANCO", self.caminho_v5):
            self.assert_recusa_v7(db.SchemaV7IncompativelError)  # via migrar direto
            sha = self.sha256(self.caminho_v5)
            with self.assertRaises(db.SchemaV7IncompativelError):
                db.preparar_banco()
            self.assertEqual(self.sha256(self.caminho_v5), sha)

    def test_versao_7_incompleta_e_recusada(self):
        self.criar_v6()
        self.sql(self.caminho_v5, "PRAGMA user_version = 7")
        self.assert_recusa_v7(db.SchemaV7IncompativelError, "sem todos os itens da v7")

    # ------------------------------------------------------------------
    #  Falhas depois do backup: rollback completo
    # ------------------------------------------------------------------
    def test_falha_depois_das_alteracoes_faz_rollback(self):
        self.criar_v6()
        schema_antes = self.schema(self.caminho_v5)
        dump_antes = self.dump_completo(self.caminho_v5)
        dados_reais = db._dados_v6
        chamadas = []

        def dados_divergentes(cursor):
            chamadas.append(1)
            dados = dados_reais(cursor)
            return dados if len(chamadas) == 1 else {}

        with mock.patch.object(db, "_dados_v6", side_effect=dados_divergentes):
            with self.assertRaisesRegex(RuntimeError, "Validação pós-migração v7 falhou"):
                db.migrar_schema_v7(self.caminho_v5)

        self.assertEqual(self.schema(self.caminho_v5), schema_antes)
        self.assertEqual(self.dump_completo(self.caminho_v5), dump_antes)
        self.assertEqual(len(self.backups_v7()), 1)  # o backup permanece
        self.assert_sem_transacao_nem_lock(self.caminho_v5)

    def test_falha_ao_criar_backup_nao_altera_nada(self):
        self.criar_v6()
        with mock.patch.object(db, "criar_backup", side_effect=OSError("disco cheio")):
            self.assert_recusa_v7(OSError, "disco cheio")

    def test_backup_corrompido_aborta_sem_alterar_nada(self):
        self.criar_v6()
        schema_antes = self.schema(self.caminho_v5)
        with mock.patch.object(db, "_verificar_integridade_backup", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "integrity_check"):
                db.migrar_schema_v7(self.caminho_v5)
        self.assertEqual(self.schema(self.caminho_v5), schema_antes)

    def test_banco_bloqueado_por_outra_conexao_aborta_sem_backup(self):
        self.criar_v6()
        schema_antes = self.schema(self.caminho_v5)
        dados_antes = self.dados_v5(self.caminho_v5)
        outra = _conectar_original(self.caminho_v5)
        outra.isolation_level = None
        outra.execute("BEGIN IMMEDIATE;")
        try:
            with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                db.migrar_schema_v7(self.caminho_v5)
        finally:
            outra.execute("ROLLBACK;")
            outra.close()

        self.assert_nada_mudou(self.caminho_v5, schema_antes, dados_antes)
        self.assertEqual(self.backups_v7(), [])

    def test_indice_unico_impede_posicao_repetida(self):
        self.criar_v6()
        db.migrar_schema_v7(self.caminho_v5)
        with self.assertRaises(sqlite3.IntegrityError):
            self.sql(self.caminho_v5, "UPDATE contas SET posicao = 1 WHERE id = 101")


if __name__ == "__main__":
    unittest.main()
