"""
Migração de schema v5.0 → v6.0 (ERS v6.0, 9.2; RNF07/RNF08) e unicidade
de e-mail sem diferenciar maiúsculas de minúsculas (5.31).

Os bancos v5 são criados a partir do DDL congelado em `fixture_schema_v5`,
sempre na pasta temporária do teste. O banco real nunca é tocado.
"""

import hashlib
import os
import sqlite3
import unittest
from unittest import mock

from apoio_banco import TesteComBancoTemporario, _conectar_original, db
from fixture_schema_v5 import COLUNAS_V5, criar_banco_v5

COLUNAS_NOVAS = {
    ("contas", "descricao"): ("TEXT", 0, None),
    ("series_recorrencia", "descricao"): ("TEXT", 0, None),
    ("usuarios", "email_verificado"): ("INTEGER", 1, "0"),
    ("usuarios", "tema"): ("TEXT", 1, "'claro'"),
}


class AuxiliaresBancoV6(TesteComBancoTemporario):
    """Auxiliares compartilhados com test_preparar_banco.py; não contém testes."""

    def setUp(self):
        super().setUp()
        self.caminho_v5 = os.path.join(os.path.dirname(self.caminho_banco), "sino_v5.db")

    def criar_v5(self, **kwargs):
        criar_banco_v5(self.caminho_v5, conectar=_conectar_original, **kwargs)

    def sql(self, caminho, comando, parametros=()):
        conexao = _conectar_original(caminho)
        try:
            resultado = conexao.execute(comando, parametros).fetchall()
            conexao.commit()
            return resultado
        finally:
            conexao.close()

    def dados_v5(self, caminho):
        """Todas as colunas v5 de todas as tabelas, linha a linha, e as sequências."""
        dados = {}
        for tabela, colunas in COLUNAS_V5.items():
            dados[tabela] = self.sql(caminho, f"SELECT {', '.join(colunas)} FROM {tabela} ORDER BY id")
        dados["sqlite_sequence"] = self.sql(caminho, "SELECT name, seq FROM sqlite_sequence ORDER BY name")
        return dados

    def schema(self, caminho):
        return (
            self.sql(caminho, "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"),
            self.sql(caminho, "PRAGMA user_version")[0][0],
        )

    def colunas(self, caminho, tabela):
        return {linha[1]: (linha[2], linha[3], linha[4])
                for linha in self.sql(caminho, f"PRAGMA table_info({tabela})")}

    def backups(self):
        if not os.path.isdir(self.pasta_backups):
            return []
        return sorted(os.listdir(self.pasta_backups))

    def sha256(self, caminho):
        with open(caminho, "rb") as arquivo:
            return hashlib.sha256(arquivo.read()).hexdigest()

    def assert_sem_transacao_nem_lock(self, caminho):
        """Uma nova conexão consegue o lock de escrita na hora (timeout 0)."""
        conexao = _conectar_original(caminho, timeout=0)
        try:
            conexao.isolation_level = None
            conexao.execute("BEGIN IMMEDIATE;")
            conexao.execute("ROLLBACK;")
        finally:
            conexao.close()

    def assert_nada_mudou(self, caminho, schema_antes, dados_antes):
        self.assertEqual(self.schema(caminho), schema_antes)  # inclui user_version
        self.assertEqual(self.dados_v5(caminho), dados_antes)
        self.assert_sem_transacao_nem_lock(caminho)

    def dump_completo(self, caminho):
        """Todas as linhas de todas as tabelas, com as colunas que existirem (qualquer schema)."""
        tabelas = [t for (t,) in self.sql(caminho, "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return {t: self.sql(caminho, f"SELECT * FROM {t} ORDER BY rowid") for t in tabelas}

    def recriar_contas_v41(self):
        """Troca `contas` pela estrutura da v4.1: conta_fixa/repetir_ate, sem os campos de pagamento."""
        self.sql(self.caminho_v5, "DROP TABLE contas")
        self.sql(self.caminho_v5, """
            CREATE TABLE contas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                categoria_id INTEGER,
                serie_id INTEGER,
                nome TEXT NOT NULL,
                valor REAL NOT NULL,
                data_vencimento TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente',
                conta_fixa INTEGER NOT NULL DEFAULT 0,
                repetir_ate TEXT
            )
        """)
        self.sql(self.caminho_v5,
                 "INSERT INTO contas (usuario_id, nome, valor, data_vencimento, conta_fixa, repetir_ate) "
                 "VALUES (3, 'Aluguel', 1500.0, '2026-08-05', 1, '2026-12-05')")

    def assert_recusado_sem_alteracao(self, funcao, excecao, regex):
        """Qualquer schema: nada muda (schema, linhas, bytes), sem backup e sem lock pendente."""
        schema_antes = self.schema(self.caminho_v5)
        dump_antes = self.dump_completo(self.caminho_v5)
        sha_antes = self.sha256(self.caminho_v5)

        with self.assertRaisesRegex(excecao, regex):
            funcao()

        self.assertEqual(self.schema(self.caminho_v5), schema_antes)
        self.assertEqual(self.dump_completo(self.caminho_v5), dump_antes)
        self.assertEqual(self.sha256(self.caminho_v5), sha_antes)
        self.assertEqual(self.backups(), [])
        self.assert_sem_transacao_nem_lock(self.caminho_v5)

    def assert_schema_v6(self, caminho):
        for (tabela, coluna), definicao in COLUNAS_NOVAS.items():
            self.assertEqual(self.colunas(caminho, tabela).get(coluna), definicao, f"{tabela}.{coluna}")
        indices = {linha[1]: linha[2] for linha in self.sql(caminho, "PRAGMA index_list(usuarios)")}
        self.assertEqual(indices.get(db.INDICE_EMAIL_CI), 1)
        self.assertEqual(self.sql(caminho, "PRAGMA user_version")[0][0], 6)


class TesteMigracaoV6(AuxiliaresBancoV6):
    # ------------------------------------------------------------------
    #  v5 → v6
    # ------------------------------------------------------------------
    def test_migra_v5_para_v6(self):
        self.criar_v5()
        resultado = db.migrar_schema_v6(self.caminho_v5)

        self.assertTrue(resultado["executado"])
        self.assertEqual(
            resultado["colunas_adicionadas"],
            ["contas.descricao", "series_recorrencia.descricao",
             "usuarios.email_verificado", "usuarios.tema"],
        )
        self.assertTrue(resultado["indice_criado"])
        self.assertTrue(resultado["versao_atualizada"])
        self.assert_schema_v6(self.caminho_v5)
        self.assertTrue(db.validar_migracao_v6(self.caminho_v5)["ok"])

    def test_preserva_dados_v5_linha_a_linha(self):
        self.criar_v5()
        antes = self.dados_v5(self.caminho_v5)
        indices_antes = self.sql(
            self.caminho_v5,
            "SELECT name, sql FROM sqlite_master WHERE type = 'index' ORDER BY name",
        )

        db.migrar_schema_v6(self.caminho_v5)

        self.assertEqual(self.dados_v5(self.caminho_v5), antes)
        indices_depois = self.sql(
            self.caminho_v5,
            "SELECT name, sql FROM sqlite_master WHERE type = 'index' ORDER BY name",
        )
        self.assertEqual([i for i in indices_depois if i[0] != db.INDICE_EMAIL_CI], indices_antes)

    def test_defaults_e_null_nas_linhas_existentes_e_novas(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)

        self.assertEqual(
            self.sql(self.caminho_v5, "SELECT DISTINCT email_verificado, tema FROM usuarios"),
            [(0, "claro")],
        )
        self.assertEqual(self.sql(self.caminho_v5, "SELECT COUNT(*) FROM contas WHERE descricao IS NOT NULL"), [(0,)])
        self.assertEqual(
            self.sql(self.caminho_v5, "SELECT COUNT(*) FROM series_recorrencia WHERE descricao IS NOT NULL"),
            [(0,)],
        )

        self.sql(self.caminho_v5,
                 "INSERT INTO usuarios (nome, email, senha_hash, termos_aceitos_em) "
                 "VALUES ('Nova', 'nova@sino.com', 'x', '2026-09-25')")
        self.assertEqual(
            self.sql(self.caminho_v5, "SELECT email_verificado, tema FROM usuarios WHERE email = 'nova@sino.com'"),
            [(0, "claro")],
        )
        self.sql(self.caminho_v5,
                 "INSERT INTO contas (usuario_id, nome, valor, data_vencimento) "
                 "VALUES (3, 'Nova conta', 10.0, '2026-10-01')")
        self.assertEqual(
            self.sql(self.caminho_v5, "SELECT descricao FROM contas WHERE nome = 'Nova conta'"),
            [(None,)],
        )

    def test_categoria_null_continua_sendo_sem_categoria(self):
        self.criar_v5()
        contas_sem_categoria = self.sql(self.caminho_v5, "SELECT id FROM contas WHERE categoria_id IS NULL ORDER BY id")
        series_sem_categoria = self.sql(
            self.caminho_v5, "SELECT id FROM series_recorrencia WHERE categoria_id IS NULL ORDER BY id"
        )
        self.assertTrue(contas_sem_categoria and series_sem_categoria)

        db.migrar_schema_v6(self.caminho_v5)

        self.assertEqual(
            self.sql(self.caminho_v5, "SELECT id FROM contas WHERE categoria_id IS NULL ORDER BY id"),
            contas_sem_categoria,
        )
        self.assertEqual(
            self.sql(self.caminho_v5, "SELECT id FROM series_recorrencia WHERE categoria_id IS NULL ORDER BY id"),
            series_sem_categoria,
        )
        self.assertEqual(
            self.sql(self.caminho_v5, "SELECT COUNT(*) FROM categorias WHERE lower(nome) = 'sem categoria'"),
            [(0,)],
        )

    # ------------------------------------------------------------------
    #  Banco novo e criar_tabelas()
    # ------------------------------------------------------------------
    def test_banco_novo_ja_nasce_v6_e_migracao_nao_faz_nada(self):
        self.assert_schema_v6(self.caminho_banco)
        self.assertTrue(db.validar_migracao_v6(self.caminho_banco)["ok"])

        resultado = db.migrar_schema_v6(self.caminho_banco)

        self.assertEqual(resultado, {"executado": False, "motivo": "já migrado", "backup": None})
        self.assertEqual(self.backups(), [])

    def test_banco_novo_e_banco_migrado_tem_as_mesmas_colunas(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)
        for tabela in COLUNAS_V5:
            self.assertEqual(self.colunas(self.caminho_v5, tabela), self.colunas(self.caminho_banco, tabela), tabela)

    def test_criar_tabelas_nao_altera_banco_v5_existente(self):
        self.criar_v5()
        schema_antes = self.schema(self.caminho_v5)
        dados_antes = self.dados_v5(self.caminho_v5)
        sha_antes = self.sha256(self.caminho_v5)

        with mock.patch.object(db, "NOME_DO_BANCO", self.caminho_v5):
            db.criar_tabelas()
            db.criar_tabelas()

        for (tabela, coluna) in COLUNAS_NOVAS:
            self.assertNotIn(coluna, self.colunas(self.caminho_v5, tabela), f"{tabela}.{coluna}")
        self.assertEqual(
            self.sql(self.caminho_v5, "SELECT COUNT(*) FROM sqlite_master WHERE name = ?", (db.INDICE_EMAIL_CI,)),
            [(0,)],
        )
        self.assertEqual(self.sql(self.caminho_v5, "PRAGMA user_version"), [(0,)])
        self.assert_nada_mudou(self.caminho_v5, schema_antes, dados_antes)
        self.assertEqual(self.sha256(self.caminho_v5), sha_antes)

    # ------------------------------------------------------------------
    #  Execução repetida e estados parciais
    # ------------------------------------------------------------------
    def test_execucao_repetida_nao_altera_nada(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)
        schema_depois = self.schema(self.caminho_v5)
        dados_depois = self.dados_v5(self.caminho_v5)
        backups_depois = self.backups()

        for _ in range(2):
            resultado = db.migrar_schema_v6(self.caminho_v5)
            self.assertEqual(resultado, {"executado": False, "motivo": "já migrado", "backup": None})

        self.assertEqual(self.schema(self.caminho_v5), schema_depois)
        self.assertEqual(self.dados_v5(self.caminho_v5), dados_depois)
        self.assertEqual(self.backups(), backups_depois)
        self.assertEqual(len(backups_depois), 1)

    def test_estado_parcial_completa_somente_o_que_falta(self):
        self.criar_v5()
        self.sql(self.caminho_v5, "ALTER TABLE contas ADD COLUMN descricao TEXT")
        self.sql(self.caminho_v5,
                 "ALTER TABLE usuarios ADD COLUMN tema TEXT NOT NULL DEFAULT 'claro' "
                 "CHECK (tema IN ('claro', 'escuro'))")
        self.sql(self.caminho_v5, "UPDATE contas SET descricao = 'nota já gravada' WHERE id = 104")
        self.sql(self.caminho_v5, "UPDATE usuarios SET tema = 'escuro' WHERE id = 7")

        resultado = db.migrar_schema_v6(self.caminho_v5)

        self.assertEqual(resultado["colunas_adicionadas"],
                         ["series_recorrencia.descricao", "usuarios.email_verificado"])
        self.assertTrue(resultado["indice_criado"])
        self.assert_schema_v6(self.caminho_v5)
        self.assertEqual(self.sql(self.caminho_v5, "SELECT descricao FROM contas WHERE id = 104"),
                         [("nota já gravada",)])
        self.assertEqual(self.sql(self.caminho_v5, "SELECT id, tema FROM usuarios ORDER BY id"),
                         [(3, "claro"), (7, "escuro")])

    def test_estado_parcial_com_indice_existente_e_versao_ausente(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)
        self.sql(self.caminho_v5, "PRAGMA user_version = 0")

        resultado = db.migrar_schema_v6(self.caminho_v5)

        self.assertTrue(resultado["executado"])
        self.assertEqual(resultado["colunas_adicionadas"], [])
        self.assertFalse(resultado["indice_criado"])
        self.assertTrue(resultado["versao_atualizada"])
        self.assert_schema_v6(self.caminho_v5)

    # ------------------------------------------------------------------
    #  E-mail: colisões e unicidade case-insensitive
    # ------------------------------------------------------------------
    def test_colisao_de_email_aborta_sem_alterar_nada(self):
        self.criar_v5(usuarios_extras=[
            (8, "Ana duplicada", "ANA@Sino.com", "x", "2026-09-03"),
            (9, "João duplicado", "joao@SINO.COM", "x", "2026-09-03"),
        ])
        schema_antes = self.schema(self.caminho_v5)
        dados_antes = self.dados_v5(self.caminho_v5)

        with self.assertRaises(db.ColisaoDeEmailError) as contexto:
            db.migrar_schema_v6(self.caminho_v5)

        self.assertEqual(contexto.exception.grupos_ids, [[3, 8], [7, 9]])
        mensagem = str(contexto.exception)
        self.assertIn("3, 8", mensagem)
        self.assertIn("7, 9", mensagem)
        self.assertNotIn("@", mensagem)
        self.assertEqual(self.schema(self.caminho_v5), schema_antes)
        self.assertEqual(self.dados_v5(self.caminho_v5), dados_antes)
        self.assertEqual(self.backups(), [])
        # nenhuma transação ou lock ficou pendente
        self.sql(self.caminho_v5, "UPDATE usuarios SET nome = nome WHERE id = 3")

    def test_indice_homonimo_incorreto_aborta_sem_alterar_nada(self):
        variantes = {
            "não único": "CREATE INDEX {n} ON usuarios(lower(email))",
            "coluna sem lower": "CREATE UNIQUE INDEX {n} ON usuarios(email)",
            "colação NOCASE na coluna": "CREATE UNIQUE INDEX {n} ON usuarios(email COLLATE NOCASE)",
            "upper": "CREATE UNIQUE INDEX {n} ON usuarios(upper(email))",
            "lower(trim)": "CREATE UNIQUE INDEX {n} ON usuarios(lower(trim(email)))",
            "outra coluna": "CREATE UNIQUE INDEX {n} ON usuarios(lower(nome))",
            "composto": "CREATE UNIQUE INDEX {n} ON usuarios(lower(email), id)",
            "parcial": "CREATE UNIQUE INDEX {n} ON usuarios(lower(email)) WHERE id > 0",
            "expressão NOCASE": "CREATE UNIQUE INDEX {n} ON usuarios(lower(email) COLLATE NOCASE)",
            "outra tabela": "CREATE UNIQUE INDEX {n} ON categorias(lower(nome))",
            "tabela homônima": "CREATE TABLE {n} (x)",
        }
        for descricao, ddl in variantes.items():
            with self.subTest(descricao):
                if os.path.exists(self.caminho_v5):
                    os.remove(self.caminho_v5)
                self.criar_v5()
                self.sql(self.caminho_v5, ddl.format(n=db.INDICE_EMAIL_CI))
                schema_antes = self.schema(self.caminho_v5)
                dados_antes = self.dados_v5(self.caminho_v5)

                with self.assertRaises(db.SchemaV6IncompativelError) as contexto:
                    db.migrar_schema_v6(self.caminho_v5)

                self.assertIn(db.INDICE_EMAIL_CI, str(contexto.exception))
                self.assert_nada_mudou(self.caminho_v5, schema_antes, dados_antes)
                self.assertEqual(self.backups(), [])
                self.assertEqual(db.validar_migracao_v6(self.caminho_v5)["indice_email_ci"], "incompativel")

    def test_indice_correto_com_outra_formatacao_e_aceito(self):
        self.criar_v5()
        self.sql(self.caminho_v5, f"create unique index {db.INDICE_EMAIL_CI} on usuarios (  LOWER( email )  )")

        resultado = db.migrar_schema_v6(self.caminho_v5)

        self.assertTrue(resultado["executado"])
        self.assertFalse(resultado["indice_criado"])
        self.assertEqual(len(resultado["colunas_adicionadas"]), 4)
        self.assertTrue(db.validar_migracao_v6(self.caminho_v5)["ok"])

    def test_banco_ja_migrado_com_indice_trocado_nao_e_considerado_migrado(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)
        self.sql(self.caminho_v5, f"DROP INDEX {db.INDICE_EMAIL_CI}")
        self.sql(self.caminho_v5, f"CREATE INDEX {db.INDICE_EMAIL_CI} ON usuarios(lower(email))")
        schema_antes = self.schema(self.caminho_v5)
        dados_antes = self.dados_v5(self.caminho_v5)

        with self.assertRaises(db.SchemaV6IncompativelError):
            db.migrar_schema_v6(self.caminho_v5)

        self.assert_nada_mudou(self.caminho_v5, schema_antes, dados_antes)
        self.assertEqual(len(self.backups()), 1)  # só o da primeira migração
        validacao = db.validar_migracao_v6(self.caminho_v5)
        self.assertFalse(validacao["ok"])
        self.assertEqual(validacao["indice_email_ci"], "incompativel")

    def test_coluna_homonima_com_definicao_diferente_aborta(self):
        self.criar_v5()
        self.sql(self.caminho_v5, "ALTER TABLE usuarios ADD COLUMN tema TEXT")
        schema_antes = self.schema(self.caminho_v5)
        dados_antes = self.dados_v5(self.caminho_v5)

        with self.assertRaises(db.SchemaV6IncompativelError) as contexto:
            db.migrar_schema_v6(self.caminho_v5)

        self.assertIn("usuarios.tema", str(contexto.exception))
        self.assert_nada_mudou(self.caminho_v5, schema_antes, dados_antes)
        self.assertEqual(self.backups(), [])

    def test_versao_nao_suportada_aborta_antes_de_qualquer_escrita(self):
        for versao in (7, 3):
            with self.subTest(user_version=versao):
                if os.path.exists(self.caminho_v5):
                    os.remove(self.caminho_v5)
                self.criar_v5()
                self.sql(self.caminho_v5, f"PRAGMA user_version = {versao}")
                schema_antes = self.schema(self.caminho_v5)
                dados_antes = self.dados_v5(self.caminho_v5)

                with self.assertRaises(db.VersaoDeBancoNaoSuportadaError) as contexto:
                    db.migrar_schema_v6(self.caminho_v5)

                self.assertEqual(contexto.exception.versao, versao)
                self.assert_nada_mudou(self.caminho_v5, schema_antes, dados_antes)
                self.assertEqual(self.backups(), [])

    def test_validacao_recusa_banco_v6_com_versao_futura(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)
        self.sql(self.caminho_v5, "PRAGMA user_version = 7")
        self.assertFalse(db.validar_migracao_v6(self.caminho_v5)["ok"])

    def test_tabelas_fora_do_schema_v5_nao_sao_tratadas_como_v5(self):
        variantes = {
            "contas v4.1": self.recriar_contas_v41,
            "coluna desconhecida": lambda: self.sql(self.caminho_v5, "ALTER TABLE usuarios ADD COLUMN telefone TEXT"),
            "coluna v5 ausente": lambda: self.sql(self.caminho_v5, "ALTER TABLE categorias DROP COLUMN cor"),
        }
        for descricao, alterar in variantes.items():
            with self.subTest(descricao):
                if os.path.exists(self.caminho_v5):
                    os.remove(self.caminho_v5)
                self.criar_v5()
                alterar()
                self.assert_recusado_sem_alteracao(
                    lambda: db.migrar_schema_v6(self.caminho_v5),
                    db.SchemaV6IncompativelError, "fora do schema v5",
                )

    def test_regra_de_email_e_a_mesma_no_cadastro_login_indice_e_colisao(self):
        variantes = ("Caixa@Sino.com", "caixa@sino.com", "CAIXA@SINO.COM", "cAiXa@sInO.cOm")
        self.criar_usuario(email=variantes[0], senha="senha123")
        for variante in variantes[1:]:
            with self.subTest(variante):
                self.assertFalse(db.criar_usuario("X", variante, "senha123", aceite_termos=True)[0])
                self.assertEqual(db.verificar_login(variante, "senha123")["email"], variantes[0])
                with self.assertRaises(sqlite3.IntegrityError):
                    self.executar(
                        "INSERT INTO usuarios (nome, email, senha_hash, termos_aceitos_em) "
                        "VALUES ('X', ?, 'x', '2026-09-25')",
                        (variante,),
                    )

        self.criar_v5(usuarios_extras=[(8 + i, "X", v, "x", "2026-09-03") for i, v in enumerate(variantes)])
        with self.assertRaises(db.ColisaoDeEmailError) as contexto:
            db.migrar_schema_v6(self.caminho_v5)
        self.assertEqual(contexto.exception.grupos_ids, [[8, 9, 10, 11]])
        self.assertEqual(self.sql(self.caminho_v5, "SELECT email FROM usuarios WHERE id >= 8 ORDER BY id"),
                         [(v,) for v in variantes])

    def test_indice_impede_email_que_so_difere_na_caixa(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)

        with self.assertRaises(sqlite3.IntegrityError):
            self.sql(self.caminho_v5,
                     "INSERT INTO usuarios (nome, email, senha_hash, termos_aceitos_em) "
                     "VALUES ('X', 'ANA@SINO.COM', 'x', '2026-09-25')")
        self.sql(self.caminho_v5,
                 "INSERT INTO usuarios (nome, email, senha_hash, termos_aceitos_em) "
                 "VALUES ('Y', 'outra@sino.com', 'x', '2026-09-25')")

    def test_cadastro_recusa_email_que_so_difere_na_caixa(self):
        self.criar_usuario(email="Teste@Sino.com")
        sucesso, mensagem = db.criar_usuario("Outro", "teste@sino.COM", "senha123", aceite_termos=True)
        self.assertFalse(sucesso)
        self.assertEqual(mensagem, "Já existe uma conta com esse e-mail.")
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM usuarios")[0][0], 1)

    def test_login_ignora_caixa_do_email_e_nao_exige_verificacao(self):
        self.criar_usuario(email="Teste@Sino.com", senha="senha123")
        self.assertEqual(self.consultar("SELECT email_verificado FROM usuarios")[0][0], 0)

        usuario = db.verificar_login("teste@SINO.com", "senha123")

        self.assertIsNotNone(usuario)
        self.assertEqual(usuario["email"], "Teste@Sino.com")
        self.assertIsNone(db.verificar_login("teste@sino.com", "senha errada"))

    def test_cadastro_e_login_coerentes_em_banco_v5_nao_migrado(self):
        self.criar_v5()
        with mock.patch.object(db, "NOME_DO_BANCO", self.caminho_v5):
            sucesso, _ = db.criar_usuario("Dup", "ANA@sino.com", "senha123", aceite_termos=True)
            self.assertFalse(sucesso)
            sucesso, _ = db.criar_usuario("Bia", "Bia@Sino.com", "senha123", aceite_termos=True)
            self.assertTrue(sucesso)
            self.assertEqual(db.verificar_login("bia@sino.com", "senha123")["email"], "Bia@Sino.com")

    def test_login_em_banco_v5_com_colisao_prioriza_email_exato(self):
        self.criar_v5(usuarios_extras=[
            (8, "Ana maiúscula", "ANA@sino.com", db._gerar_hash_senha("senha-oito"), "2026-09-03"),
        ])
        self.sql(self.caminho_v5, "UPDATE usuarios SET senha_hash = ? WHERE id = 3",
                 (db._gerar_hash_senha("senha-tres"),))
        with mock.patch.object(db, "NOME_DO_BANCO", self.caminho_v5):
            self.assertEqual(db.verificar_login("ANA@sino.com", "senha-oito")["id"], 8)
            self.assertEqual(db.verificar_login("ana@sino.com", "senha-tres")["id"], 3)

    # ------------------------------------------------------------------
    #  Backup
    # ------------------------------------------------------------------
    def test_backup_criado_antes_das_alteracoes(self):
        self.criar_v5()
        dados_antes = self.dados_v5(self.caminho_v5)
        schema_antes = self.schema(self.caminho_v5)

        resultado = db.migrar_schema_v6(self.caminho_v5)

        backup = resultado["backup"]
        self.assertEqual(os.path.dirname(backup), self.pasta_backups)
        self.assertTrue(os.path.basename(backup).startswith("sino_pre_migracao_v6_"))
        self.assertEqual(self.schema(backup), schema_antes)
        self.assertEqual(self.dados_v5(backup), dados_antes)
        self.assertEqual(self.sql(backup, "PRAGMA integrity_check"), [("ok",)])

    def test_criar_backup_mantem_nome_v5_e_nao_sobrescreve(self):
        self.criar_v5()
        primeiro = db.criar_backup(self.caminho_v5)
        segundo = db.criar_backup(self.caminho_v5)

        self.assertTrue(os.path.basename(primeiro).startswith("sino_pre_migracao_v5_"))
        self.assertNotEqual(primeiro, segundo)
        self.assertEqual(len(self.backups()), 2)
        self.assertEqual(self.dados_v5(primeiro), self.dados_v5(self.caminho_v5))
        self.assertIsNone(db.criar_backup(os.path.join(self.pasta_backups, "inexistente.db")))

    # ------------------------------------------------------------------
    #  Rollback
    # ------------------------------------------------------------------
    def assert_rollback_completo(self, schema_antes, dados_antes):
        self.assert_nada_mudou(self.caminho_v5, schema_antes, dados_antes)
        self.assertEqual(self.sql(self.caminho_v5, "PRAGMA user_version"), [(0,)])
        self.assertEqual(len(self.backups()), 1)

        resultado = db.migrar_schema_v6(self.caminho_v5)
        self.assertTrue(resultado["executado"])
        self.assert_schema_v6(self.caminho_v5)

    def test_rollback_quando_uma_alteracao_falha(self):
        self.criar_v5()
        schema_antes = self.schema(self.caminho_v5)
        dados_antes = self.dados_v5(self.caminho_v5)
        colunas_com_falha = db.COLUNAS_V6 + (("tabela_inexistente", "x", "TEXT", ("TEXT", 0, None)),)

        with mock.patch.object(db, "COLUNAS_V6", colunas_com_falha):
            with self.assertRaises(sqlite3.OperationalError):
                db.migrar_schema_v6(self.caminho_v5)

        self.assert_rollback_completo(schema_antes, dados_antes)

    def test_rollback_quando_a_validacao_falha(self):
        self.criar_v5()
        schema_antes = self.schema(self.caminho_v5)
        dados_antes = self.dados_v5(self.caminho_v5)

        with mock.patch.object(db, "_verificar_schema_v6", return_value={"ok": False}):
            with self.assertRaisesRegex(RuntimeError, "Validação pós-migração v6 falhou"):
                db.migrar_schema_v6(self.caminho_v5)

        self.assert_rollback_completo(schema_antes, dados_antes)

    def test_falha_ao_criar_backup_nao_altera_nada(self):
        self.criar_v5()
        schema_antes = self.schema(self.caminho_v5)
        dados_antes = self.dados_v5(self.caminho_v5)

        with mock.patch.object(db, "criar_backup", side_effect=OSError("disco cheio")):
            with self.assertRaisesRegex(OSError, "disco cheio"):
                db.migrar_schema_v6(self.caminho_v5)

        self.assert_nada_mudou(self.caminho_v5, schema_antes, dados_antes)
        self.assertEqual(self.backups(), [])

    def test_backup_corrompido_aborta_sem_alterar_nada(self):
        self.criar_v5()
        schema_antes = self.schema(self.caminho_v5)
        dados_antes = self.dados_v5(self.caminho_v5)
        caminho_corrompido = os.path.join(os.path.dirname(self.caminho_v5), "backup_corrompido.db")
        with open(caminho_corrompido, "wb") as arquivo:
            arquivo.write(b"isto nao e um banco sqlite" * 200)

        with mock.patch.object(db, "criar_backup", return_value=caminho_corrompido):
            with self.assertRaisesRegex(RuntimeError, "falhou no integrity_check"):
                db.migrar_schema_v6(self.caminho_v5)

        self.assert_nada_mudou(self.caminho_v5, schema_antes, dados_antes)

    def test_criar_backup_remove_arquivo_incompleto_em_falha(self):
        self.criar_v5()

        def conectar_destino_fechado(caminho, *args, **kwargs):
            conexao = _conectar_original(caminho, *args, **kwargs)
            if os.path.dirname(os.path.realpath(caminho)) == os.path.realpath(self.pasta_backups):
                conexao.close()  # faz Connection.backup() falhar depois de o arquivo existir
            return conexao

        with mock.patch.object(sqlite3, "connect", conectar_destino_fechado):
            with self.assertRaises(sqlite3.ProgrammingError):
                db.criar_backup(self.caminho_v5, rotulo="v6")

        self.assertEqual(self.backups(), [])
        self.assert_sem_transacao_nem_lock(self.caminho_v5)

    def test_banco_bloqueado_por_outra_conexao_aborta_sem_backup(self):
        self.criar_v5()
        schema_antes = self.schema(self.caminho_v5)
        dados_antes = self.dados_v5(self.caminho_v5)
        outra = _conectar_original(self.caminho_v5)
        outra.isolation_level = None
        outra.execute("BEGIN IMMEDIATE;")
        try:
            with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                db.migrar_schema_v6(self.caminho_v5)
        finally:
            outra.execute("ROLLBACK;")
            outra.close()

        self.assert_nada_mudou(self.caminho_v5, schema_antes, dados_antes)
        self.assertEqual(self.backups(), [])

    def test_banco_inexistente_nao_e_criado(self):
        with self.assertRaises(FileNotFoundError):
            db.migrar_schema_v6(self.caminho_v5)
        with self.assertRaises(FileNotFoundError):
            db.validar_migracao_v6(self.caminho_v5)
        self.assertFalse(os.path.exists(self.caminho_v5))
        self.assertEqual(self.backups(), [])

    def test_banco_sem_schema_v5_aborta(self):
        self.sql(self.caminho_v5, "CREATE TABLE outra (x)")
        with self.assertRaisesRegex(RuntimeError, "Schema v5 incompleto"):
            db.migrar_schema_v6(self.caminho_v5)
        self.assertEqual(self.backups(), [])

    # ------------------------------------------------------------------
    #  CHECKs e integridade
    # ------------------------------------------------------------------
    def test_checks_das_colunas_novas(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)
        for caminho in (self.caminho_v5, self.caminho_banco):
            if caminho == self.caminho_banco:
                self.criar_usuario()
            for atribuicao in ("tema = 'azul'", "tema = NULL",
                               "email_verificado = 2", "email_verificado = NULL"):
                with self.subTest(banco=os.path.basename(caminho), atribuicao=atribuicao):
                    with self.assertRaises(sqlite3.IntegrityError):
                        self.sql(caminho, f"UPDATE usuarios SET {atribuicao}")
            self.sql(caminho, "UPDATE usuarios SET tema = 'escuro', email_verificado = 1")

    def test_integridade_apos_migracao(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)

        self.assertEqual(self.sql(self.caminho_v5, "PRAGMA integrity_check"), [("ok",)])
        self.assertEqual(self.sql(self.caminho_v5, "PRAGMA foreign_key_check"), [])
        validacao = db.validar_migracao_v6(self.caminho_v5)
        self.assertTrue(validacao["ok"], validacao)
        self.assertTrue(db.validar_migracao_v5(self.caminho_v5)["ok"])


if __name__ == "__main__":
    unittest.main()
