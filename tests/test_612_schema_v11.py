"""
Sino 6.12 (experimental), Etapa 4 -- schema v11 e migração v10 -> v11.

Três tabelas novas (parcelamentos, séries de valor variável, ocorrências com
valor pendente) e um gatilho na tabela de pendentes; nenhuma tabela, coluna ou
linha existente muda. Testes: banco novo; migração com backup verificado e dados
preservados; idempotência; recusas sem gravação e sem backup; rollback; gatilho;
validação de órfãos e de regras; exclusões que limpam os complementos; e a
recusa de abrir um banco v11 por um app que só conhece até a v10 (Sino 6.11).
"""

import hashlib
import os
import sqlite3
import unittest
from unittest import mock

from apoio_banco import TesteComBancoTemporario, _conectar_original, db

import pagamentos

V11 = ("parcelamentos", "series_valor_variavel", "ocorrencias_valor_pendente")


class BaseV11(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()
        self.luz = db.criar_conta_unica(self.usuario_id, "Luz", 180.35, "2026-09-10")
        pagamentos.registrar_pagamento_parcial(self.luz, 50_00, "2026-09-05")
        self.serie_mensal, self.mensais = db.criar_serie_recorrente(
            self.usuario_id, "Aluguel", 1200.0, "2026-08-31", "mensal", data_termino="2027-01")
        self.serie_anual, self.anuais = db.criar_serie_recorrente(self.usuario_id, "IPVA", 1500.0, "2026-03-15",
                                                                  "anual")

    # ---------------------------------------------------------------- auxiliares
    def versao(self):
        return self.consultar("PRAGMA user_version")[0][0]

    def estados(self):
        conexao = _conectar_original(self.caminho_banco)
        try:
            return db._estados_v11(conexao.cursor())
        finally:
            conexao.close()

    def backups(self):
        return sorted(os.listdir(self.pasta_backups)) if os.path.isdir(self.pasta_backups) else []

    def sha256(self):
        with open(self.caminho_banco, "rb") as arquivo:
            return hashlib.sha256(arquivo.read()).hexdigest()

    def dados(self, caminho=None):
        conexao = _conectar_original(caminho or self.caminho_banco)
        try:
            return {tabela: conexao.execute(f"SELECT * FROM {tabela} ORDER BY 1").fetchall()
                    for tabela in ("usuarios", "categorias", "contas", "series_recorrencia", "pp_pagamentos",
                                   "aceites_documentos", "autorizacoes_usadas")}
        finally:
            conexao.close()

    def rebaixar_para_v10(self):
        """O banco do teste nasce v11; sem os objetos da v11 e com user_version 10, é um banco da Sino 6.11."""
        self.executar(f"DROP TRIGGER {db.GATILHO_PENDENTE_SEM_PAGAMENTOS}")
        for tabela in V11:
            self.executar(f"DROP TABLE {tabela}")
        self.executar("PRAGMA user_version = 10")
        conexao = _conectar_original(self.caminho_banco)
        try:
            self.assertTrue(db._verificar_schema_v10(conexao.cursor())["ok"])
        finally:
            conexao.close()

    def validar(self):
        return db.validar_schema_atual(self.caminho_banco)

    def sem_violacoes(self):
        self.assertEqual(self.consultar("PRAGMA foreign_key_check"), [])
        resultado = self.validar()
        self.assertTrue(resultado["ok"], resultado)


class TestBancoNovo(BaseV11):
    def test_nasce_v11_com_as_tabelas_vazias(self):
        self.assertEqual(self.versao(), 11)
        self.assertEqual(db.VERSAO_SCHEMA_ATUAL, 11)
        self.assertIn(11, db.VERSOES_SUPORTADAS)
        self.assertEqual(self.estados(), {tabela: "valida" for tabela in V11})
        for tabela in V11:
            self.assertEqual(self.consultar(f"SELECT COUNT(*) FROM {tabela}"), [(0,)])
        self.sem_violacoes()

    def test_colunas_e_chaves(self):
        self.assertEqual([c[1] for c in self.consultar("PRAGMA table_info(parcelamentos)")],
                         ["serie_id", "quantidade_original", "valor_total_original_centavos", "criado_em"])
        self.assertEqual([c[1] for c in self.consultar("PRAGMA table_info(series_valor_variavel)")],
                         ["serie_id", "definido_em"])
        self.assertEqual([c[1] for c in self.consultar("PRAGMA table_info(ocorrencias_valor_pendente)")],
                         ["conta_id", "definido_em"])
        self.assertEqual([tuple(f[2:5]) for f in self.consultar("PRAGMA foreign_key_list(parcelamentos)")],
                         [("series_recorrencia", "serie_id", "id")])
        self.assertEqual([tuple(f[2:5]) for f in self.consultar("PRAGMA foreign_key_list(ocorrencias_valor_pendente)")],
                         [("contas", "conta_id", "id")])

    def test_pp_pagamentos_continua_exata_sem_gatilho(self):
        self.assertEqual(self.consultar("SELECT name FROM sqlite_master WHERE type = 'trigger' "
                                        "AND tbl_name = 'pp_pagamentos'"), [])
        conexao = _conectar_original(self.caminho_banco)
        try:
            self.assertEqual(db._estado_tabela_pagamentos(conexao.cursor()), "valida")
        finally:
            conexao.close()

    def test_restricoes_das_colunas(self):
        for sql in ("INSERT INTO parcelamentos VALUES (?, 1, 100, '2026-09-01')",
                    "INSERT INTO parcelamentos VALUES (?, 37, 100, '2026-09-01')",
                    "INSERT INTO parcelamentos VALUES (?, 12, 0, '2026-09-01')",
                    "INSERT INTO parcelamentos VALUES (?, 12, 100, NULL)"):
            with self.subTest(sql=sql):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.executar(sql, (self.serie_mensal,))


class TestMigracao(BaseV11):
    def test_v10_para_v11_preserva_tudo_com_backup_verificado(self):
        self.rebaixar_para_v10()
        antes = self.dados()

        resultado = db.migrar_schema_v11(self.caminho_banco)

        self.assertTrue(resultado["executado"])
        self.assertEqual(self.backups(), [os.path.basename(resultado["backup"])])
        self.assertIn("sino_pre_migracao_v11_", resultado["backup"])
        self.assertTrue(db._verificar_integridade_backup(resultado["backup"]))
        backup = _conectar_original(resultado["backup"])
        try:
            self.assertEqual(backup.execute("PRAGMA user_version").fetchone()[0], 10)
        finally:
            backup.close()
        self.assertEqual(self.dados(resultado["backup"]), antes)
        self.assertEqual(self.versao(), 11)
        self.assertEqual(self.dados(), antes)                      # nenhuma linha existente muda
        for tabela in V11:
            self.assertEqual(self.consultar(f"SELECT COUNT(*) FROM {tabela}"), [(0,)])  # todas continuam fixas
        self.sem_violacoes()

    def test_preparar_banco_migra_o_v10_uma_vez(self):
        self.rebaixar_para_v10()
        antes = self.dados()
        resultado = db.preparar_banco()
        self.assertEqual(resultado["situacao"], "migrado")
        self.assertTrue(resultado["migracao_v11"]["executado"])
        self.assertFalse(resultado["migracao_v10"]["executado"])
        self.assertEqual(self.dados(), antes)
        sha, backups = self.sha256(), self.backups()
        self.assertEqual(db.preparar_banco()["situacao"], "atual")
        self.assertEqual((self.sha256(), self.backups()), (sha, backups))

    def test_execucao_repetida_nao_altera_nada(self):
        self.rebaixar_para_v10()
        db.migrar_schema_v11(self.caminho_banco)
        sha, backups = self.sha256(), self.backups()
        self.assertEqual(db.migrar_schema_v11(self.caminho_banco),
                         {"executado": False, "motivo": "já migrado", "backup": None})
        for migrar in (db.migrar_schema_v6, db.migrar_schema_v7, db.migrar_schema_v8, db.migrar_schema_v9,
                       db.migrar_schema_v10):
            with self.subTest(migracao=migrar.__name__):
                self.assertFalse(migrar(self.caminho_banco)["executado"])
        self.assertEqual((self.sha256(), self.backups()), (sha, backups))

    # ------------------------------------------------------------- recusas
    def assert_recusado(self, excecao, regex):
        sha, backups = self.sha256(), self.backups()
        with self.assertRaisesRegex(excecao, regex):
            db.migrar_schema_v11(self.caminho_banco)
        self.assertEqual((self.sha256(), self.backups()), (sha, backups))

    def test_anterior_a_v10_e_recusado(self):
        self.rebaixar_para_v10()
        self.executar("PRAGMA user_version = 9")
        self.assert_recusado(db.SchemaV11IncompativelError, "precisa passar pela migração v10")

    def test_versao_futura_e_recusada(self):
        self.executar("PRAGMA user_version = 12")
        self.assert_recusado(db.VersaoDeBancoNaoSuportadaError, "12")

    def test_v10_com_tabela_da_v11_ja_existente_e_recusado(self):
        self.rebaixar_para_v10()
        self.executar("CREATE TABLE parcelamentos (serie_id INTEGER PRIMARY KEY)")
        self.assert_recusado(db.SchemaV11IncompativelError, "já tem parcelamentos")

    def test_v11_sem_uma_tabela_e_recusado(self):
        self.executar("DROP TABLE series_valor_variavel")
        self.assert_recusado(db.SchemaV11IncompativelError, "series_valor_variavel ausente")
        self.assertFalse(self.validar()["ok"])

    def test_v11_com_gatilho_ausente_e_recusado(self):
        self.executar(f"DROP TRIGGER {db.GATILHO_PENDENTE_SEM_PAGAMENTOS}")
        self.assert_recusado(db.SchemaV11IncompativelError, "ocorrencias_valor_pendente incompativel")

    def test_v11_com_dados_fora_das_regras_e_recusado(self):
        self.executar("INSERT INTO parcelamentos VALUES (?, 12, 100, '2026-09-01')", (self.serie_anual,))
        self.assert_recusado(db.SchemaV11IncompativelError, "fora das regras")

    # ------------------------------------------------------------- rollback
    def test_falha_no_meio_reverte_tudo_e_mantem_o_backup(self):
        self.rebaixar_para_v10()
        antes = self.dados()
        original = db._criar_tabelas_v11

        def criar_e_falhar(cursor):
            cursor.execute(db.DDL_V11["parcelamentos"])
            raise RuntimeError("falha simulada")

        with mock.patch.object(db, "_criar_tabelas_v11", criar_e_falhar):
            with self.assertRaisesRegex(RuntimeError, "falha simulada"):
                db.migrar_schema_v11(self.caminho_banco)
        self.assertEqual(self.versao(), 10)
        self.assertEqual(self.estados(), {tabela: "ausente" for tabela in V11})
        self.assertEqual(self.dados(), antes)
        self.assertEqual(len(self.backups()), 1)                   # o backup fica, como na v10
        self.assertIs(db._criar_tabelas_v11, original)
        self.assertTrue(db.migrar_schema_v11(self.caminho_banco)["executado"])  # a próxima retoma

    def test_validacao_pos_migracao_falha_e_reverte(self):
        self.rebaixar_para_v10()
        with mock.patch.object(db, "_verificar_schema_v11", return_value={"ok": False}):
            with self.assertRaisesRegex(RuntimeError, "Validação pós-migração v11"):
                db.migrar_schema_v11(self.caminho_banco)
        self.assertEqual(self.versao(), 10)
        self.assertEqual(self.estados(), {tabela: "ausente" for tabela in V11})

    def test_app_que_so_conhece_a_v10_recusa_o_banco_v11(self):
        # Sino 6.11: VERSOES_SUPORTADAS ia até a 10 -- o banco v11 é recusado antes de qualquer escrita.
        sha = self.sha256()
        with mock.patch.object(db, "VERSOES_SUPORTADAS", (0, 6, 7, 8, 9, 10)):
            with mock.patch.object(db, "validar_schema_atual", return_value={"ok": False}):
                with self.assertRaises(db.VersaoDeBancoNaoSuportadaError):
                    db.preparar_banco()
        self.assertEqual(self.sha256(), sha)


class TestGatilhoEValidacao(BaseV11):
    def tornar_variavel(self, serie_id):
        self.executar("INSERT INTO series_valor_variavel VALUES (?, '2026-09-01')", (serie_id,))

    def marcar_pendente(self, conta_id):
        self.executar("UPDATE contas SET valor = 0 WHERE id = ?", (conta_id,))
        self.executar("INSERT INTO ocorrencias_valor_pendente VALUES (?, '2026-09-01')", (conta_id,))

    def test_gatilho_recusa_pendente_com_pagamento(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "não pode ficar com valor pendente"):
            self.executar("INSERT INTO ocorrencias_valor_pendente VALUES (?, '2026-09-01')", (self.luz,))
        estornado = self.mensais[1]
        pagamentos.registrar_pagamento_parcial(estornado, 100_00, "2026-09-10")
        pagamento = self.consultar("SELECT id FROM pp_pagamentos WHERE conta_id = ?", (estornado,))[0][0]
        pagamentos.estornar_pagamento(pagamento, (100_00, "2026-09-10"))
        with self.assertRaises(sqlite3.IntegrityError):  # estornado também protege
            self.executar("INSERT INTO ocorrencias_valor_pendente VALUES (?, '2026-09-01')", (estornado,))

    def test_dados_validos(self):
        self.tornar_variavel(self.serie_mensal)
        for conta in self.mensais[1:]:
            self.marcar_pendente(conta)
        self.executar("UPDATE series_recorrencia SET data_termino = '2026-12' WHERE id = ?", (self.serie_anual,))
        self.sem_violacoes()

    def test_validacao_acusa_cada_regra(self):
        casos = {
            "parcelamento de série anual":
                lambda: self.executar("INSERT INTO parcelamentos VALUES (?, 12, 100, '2026-09-01')",
                                      (self.serie_anual,)),
            "parcelamento de série sem término": lambda: (
                self.executar("UPDATE series_recorrencia SET data_termino = NULL WHERE id = ?", (self.serie_mensal,)),
                self.executar("INSERT INTO parcelamentos VALUES (?, 12, 100, '2026-09-01')", (self.serie_mensal,))),
            "série parcelada e variável": lambda: (
                self.executar("INSERT INTO parcelamentos VALUES (?, 6, 100, '2026-09-01')", (self.serie_mensal,)),
                self.tornar_variavel(self.serie_mensal)),
            "pendente em série fixa": lambda: self.marcar_pendente(self.mensais[2]),
            "pendente em conta única": lambda: (
                self.executar("INSERT INTO ocorrencias_valor_pendente VALUES (?, '2026-09-01')",
                              (db.criar_conta_unica(self.usuario_id, "X", 1.0, "2026-09-20"),))),
            "pendente com valor diferente de zero": lambda: (
                self.tornar_variavel(self.serie_mensal),
                self.executar("INSERT INTO ocorrencias_valor_pendente VALUES (?, '2026-09-01')", (self.mensais[2],))),
            "pendente que recebeu pagamento depois": lambda: (
                self.tornar_variavel(self.serie_mensal), self.marcar_pendente(self.mensais[2]),
                self.executar("INSERT INTO pp_pagamentos (conta_id, valor_centavos, data_pagamento, tipo, "
                              "registrado_em) VALUES (?, 100, '2026-09-10', 'parcial', '2026-09-10T10:00:00')",
                              (self.mensais[2],))),
        }
        for nome, preparar in casos.items():
            with self.subTest(caso=nome):
                self.setUp_novo()
                preparar()
                resultado = self.validar()
                self.assertFalse(resultado["ok"])
                self.assertGreater(resultado["dados_v11_invalidos"], 0)

    def setUp_novo(self):
        for tabela in V11:
            self.executar(f"DELETE FROM {tabela}")
        self.executar("DELETE FROM pp_pagamentos WHERE conta_id != ?", (self.luz,))
        self.executar("UPDATE contas SET valor = 1200.0 WHERE serie_id = ?", (self.serie_mensal,))
        self.executar("UPDATE series_recorrencia SET data_termino = '2027-01' WHERE id = ?", (self.serie_mensal,))
        self.assertTrue(self.validar()["ok"])

    def test_orfaos_aparecem_na_validacao(self):
        conexao = _conectar_original(self.caminho_banco)
        try:
            conexao.execute("PRAGMA foreign_keys = OFF")
            conexao.execute("INSERT INTO series_valor_variavel VALUES (999, '2026-09-01')")
            conexao.commit()
        finally:
            conexao.close()
        resultado = self.validar()
        self.assertFalse(resultado["ok"])
        self.assertTrue(resultado["violacoes_fk"])


class TestExclusoesLimpamOsComplementos(BaseV11):
    """Com as chaves estrangeiras ligadas e sem cascata, excluir uma conta ou série com
    complementos falharia; as exclusões apagam antes os complementos, na mesma transação."""

    def setUp(self):
        super().setUp()
        # Série mensal variável (pendentes a partir da 2ª) e uma série "parcelada" (registro direto).
        self.executar("INSERT INTO series_valor_variavel VALUES (?, '2026-09-01')", (self.serie_mensal,))
        for conta in self.mensais[1:]:
            self.executar("UPDATE contas SET valor = 0 WHERE id = ?", (conta,))
            self.executar("INSERT INTO ocorrencias_valor_pendente VALUES (?, '2026-09-01')", (conta,))
        self.serie_parcelada, self.parcelas = db.criar_serie_recorrente(
            self.usuario_id, "Notebook", 250.0, "2026-09-20", "mensal", data_termino="2026-12")
        self.executar("INSERT INTO parcelamentos VALUES (?, 4, 100000, '2026-09-01')", (self.serie_parcelada,))
        self.sem_violacoes()

    def contar(self, tabela):
        return self.consultar(f"SELECT COUNT(*) FROM {tabela}")[0][0]

    def test_excluir_uma_ocorrencia_pendente(self):
        self.assertTrue(db.excluir_conta(self.mensais[3]))
        self.assertEqual(self.contar("ocorrencias_valor_pendente"), len(self.mensais) - 2)
        self.sem_violacoes()

    def test_excluir_serie_inteira_apaga_marca_variavel_e_pendentes(self):
        self.assertTrue(db.excluir_conta_serie(self.mensais[0]))
        self.assertEqual((self.contar("series_valor_variavel"), self.contar("ocorrencias_valor_pendente")), (0, 0))
        self.sem_violacoes()

    def test_excluir_este_mes_em_diante(self):
        self.assertTrue(db.excluir_conta_serie(self.mensais[2]))
        self.assertEqual(self.contar("ocorrencias_valor_pendente"), 1)   # só a 2ª (anterior) continua
        self.assertEqual(self.contar("series_valor_variavel"), 1)
        self.sem_violacoes()

    def test_excluir_a_ultima_parcela_restante_apaga_o_parcelamento(self):
        for conta in self.parcelas[1:]:
            db.excluir_conta(conta)
        self.assertEqual(self.contar("parcelamentos"), 1)
        db.excluir_conta(self.parcelas[0])
        self.assertEqual(self.contar("parcelamentos"), 0)
        self.sem_violacoes()

    def test_excluir_parcelada_inteira(self):
        db.excluir_conta_serie(self.parcelas[0])
        self.assertEqual(self.contar("parcelamentos"), 0)
        self.sem_violacoes()

    def test_encerrar_recorrencia_apaga_pendentes_removidas(self):
        db.encerrar_recorrencia(self.mensais[0])  # hoje fixo: 15/09/2026; ficam set (corte) e anteriores
        restantes = self.consultar("SELECT id FROM contas WHERE serie_id = ?", (self.serie_mensal,))
        self.assertEqual(self.consultar("SELECT conta_id FROM ocorrencias_valor_pendente ORDER BY 1"),
                         [r for r in restantes if r[0] != self.mensais[0]])
        self.sem_violacoes()

    def test_alterar_frequencia_de_serie_variavel_recusada(self):
        # Ajuste deliberado na Etapa 8: desde a Etapa 8 uma série variável não muda de frequência
        # (R6; proposta técnica 9) -- a recusa acontece antes de gravar, sem órfãos.
        antes = {t: self.consultar(f"SELECT * FROM {t} ORDER BY 1") for t in V11 + ("contas", "series_recorrencia")}
        with self.assertRaises(db.ValorVariavelRecusadoError):
            db.alterar_frequencia_serie(self.mensais[0], "anual", data_termino="2028-08")
        self.assertEqual({t: self.consultar(f"SELECT * FROM {t} ORDER BY 1") for t in antes}, antes)
        self.assertEqual(self.consultar("PRAGMA foreign_key_check"), [])

    def test_excluir_usuario_apaga_tudo(self):
        pendencia = db.conferir_senha_para_exclusao(self.usuario_id, "senha123")
        db.excluir_usuario(pendencia)
        for tabela in V11 + ("contas", "series_recorrencia", "pp_pagamentos"):
            self.assertEqual(self.contar(tabela), 0, tabela)
        self.assertEqual(self.consultar("PRAGMA foreign_key_check"), [])


if __name__ == "__main__":
    unittest.main()
