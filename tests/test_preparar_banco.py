"""
Inicialização do banco (ERS v6.0, Etapa 1): database.preparar_banco() e a
integração em backend/main.py (preparar_banco_ou_exibir_erro).

`db.NOME_DO_BANCO` aponta para um arquivo na pasta temporária do teste; a
guarda de apoio_banco continua impedindo qualquer acesso ao banco real.
"""

import io
import os
import sqlite3
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import apoio_banco
from apoio_banco import db
from fixture_schema_v5 import criar_banco_v5
from test_migracao_v6 import AuxiliaresBancoV6

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import flet as ft  # noqa: E402
import main  # noqa: E402


class TestePrepararBanco(AuxiliaresBancoV6):
    def setUp(self):
        super().setUp()
        # o "banco do app" deste teste é self.caminho_v5 (ainda inexistente)
        patcher = mock.patch.object(db, "NOME_DO_BANCO", self.caminho_v5)
        patcher.start()
        self.addCleanup(patcher.stop)

    def estado(self):
        return (self.sha256(self.caminho_v5), os.path.getmtime(self.caminho_v5), self.backups())

    def criar_v6_populado(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)

    # ------------------------------------------------------------------
    #  Os três cenários normais
    # ------------------------------------------------------------------
    def test_banco_inexistente_cria_v6_sem_backup(self):
        self.assertFalse(os.path.exists(self.caminho_v5))

        resultado = db.preparar_banco()

        self.assertEqual(resultado, {"situacao": "criado", "migracao": None})
        self.assert_schema_v6(self.caminho_v5)
        self.assertTrue(db.validar_migracao_v6(self.caminho_v5)["ok"])
        self.assertEqual(self.backups(), [])

    def test_arquivo_vazio_e_tratado_como_banco_novo(self):
        open(self.caminho_v5, "wb").close()

        resultado = db.preparar_banco()

        self.assertEqual(resultado["situacao"], "criado")
        self.assert_schema_v6(self.caminho_v5)
        self.assertEqual(self.backups(), [])

    def test_banco_v5_e_migrado_com_backup_e_dados_preservados(self):
        self.criar_v5()
        dados_antes = self.dados_v5(self.caminho_v5)

        with mock.patch.object(db, "criar_tabelas", wraps=db.criar_tabelas) as criar_tabelas:
            resultado = db.preparar_banco()

        criar_tabelas.assert_not_called()  # nunca sobre um banco existente
        self.assertEqual(resultado["situacao"], "migrado")
        self.assertTrue(resultado["migracao"]["executado"])
        self.assertEqual(self.backups(), [os.path.basename(resultado["migracao"]["backup"])])
        self.assert_schema_v6(self.caminho_v5)
        self.assertEqual(self.dados_v5(self.caminho_v5), dados_antes)
        self.assertTrue(db.validar_migracao_v6(self.caminho_v5)["ok"])

    def test_banco_v6_nao_e_alterado_nem_recebe_backup(self):
        self.criar_v6_populado()
        estado_antes = self.estado()

        with mock.patch.object(db, "migrar_schema_v6", wraps=db.migrar_schema_v6) as migrar, \
                mock.patch.object(db, "criar_tabelas", wraps=db.criar_tabelas) as criar_tabelas:
            resultado = db.preparar_banco()

        self.assertEqual(resultado, {"situacao": "atual", "migracao": None})
        migrar.assert_not_called()  # nem o lock de escrita da migração é pedido
        criar_tabelas.assert_not_called()
        self.assertEqual(self.estado(), estado_antes)

    def test_inicializacoes_repetidas_sao_idempotentes(self):
        self.criar_v5()
        self.assertEqual(db.preparar_banco()["situacao"], "migrado")
        estado_depois_da_migracao = self.estado()

        for _ in range(3):
            self.assertEqual(db.preparar_banco(), {"situacao": "atual", "migracao": None})

        self.assertEqual(self.estado(), estado_depois_da_migracao)
        self.assertEqual(len(self.backups()), 1)

    # ------------------------------------------------------------------
    #  Falhas: nada é alterado e a exceção chega a quem chamou
    # ------------------------------------------------------------------
    def assert_falha_sem_alteracao(self, excecao, backups_esperados=0, regex=None):
        schema_antes = self.schema(self.caminho_v5)
        dados_antes = self.dados_v5(self.caminho_v5)

        with self.assertRaises(excecao) as contexto:
            db.preparar_banco()

        if regex:
            self.assertRegex(str(contexto.exception), regex)
        self.assert_nada_mudou(self.caminho_v5, schema_antes, dados_antes)
        self.assertEqual(len(self.backups()), backups_esperados)
        return contexto.exception

    def test_banco_de_versao_futura_e_recusado_sem_tentar_migrar(self):
        self.criar_v6_populado()
        self.sql(self.caminho_v5, "PRAGMA user_version = 7")
        estado_antes = self.estado()
        schema_antes = self.schema(self.caminho_v5)
        backups_antes = self.backups()

        with mock.patch.object(db, "migrar_schema_v6", wraps=db.migrar_schema_v6) as migrar, \
                mock.patch.object(db, "criar_tabelas", wraps=db.criar_tabelas) as criar_tabelas, \
                mock.patch.object(db, "criar_backup", wraps=db.criar_backup) as criar_backup:
            with self.assertRaises(db.VersaoDeBancoNaoSuportadaError) as contexto:
                db.preparar_banco()

        self.assertEqual(contexto.exception.versao, 7)
        self.assertIn("versão mais nova", str(contexto.exception))
        migrar.assert_not_called()
        criar_tabelas.assert_not_called()
        criar_backup.assert_not_called()
        self.assertEqual(self.estado(), estado_antes)
        self.assertEqual(self.schema(self.caminho_v5), schema_antes)
        self.assertEqual(self.backups(), backups_antes)
        self.assert_sem_transacao_nem_lock(self.caminho_v5)

    def test_arquivo_sem_tabelas_mas_de_versao_futura_nao_e_tratado_como_novo(self):
        self.sql(self.caminho_v5, "PRAGMA user_version = 7")
        sha_antes = self.sha256(self.caminho_v5)

        with mock.patch.object(db, "criar_tabelas", wraps=db.criar_tabelas) as criar_tabelas:
            with self.assertRaises(db.VersaoDeBancoNaoSuportadaError):
                db.preparar_banco()

        criar_tabelas.assert_not_called()
        self.assertEqual(self.sha256(self.caminho_v5), sha_antes)

    def test_banco_de_versao_desconhecida_e_recusado(self):
        self.criar_v5()
        self.sql(self.caminho_v5, "PRAGMA user_version = 3")
        self.assert_falha_sem_alteracao(db.VersaoDeBancoNaoSuportadaError, regex="desconhecida")

    def test_schema_anterior_a_v5_nao_e_migrado(self):
        self.criar_v5()
        self.recriar_contas_v41()
        with mock.patch.object(db, "criar_tabelas", wraps=db.criar_tabelas) as criar_tabelas:
            self.assert_recusado_sem_alteracao(
                db.preparar_banco, db.SchemaV6IncompativelError, "tabela contas fora do schema v5",
            )
        criar_tabelas.assert_not_called()

    def test_colisao_de_email_impede_a_inicializacao(self):
        self.criar_v5(usuarios_extras=[(8, "Ana duplicada", "ANA@Sino.com", "x", "2026-09-03")])
        erro = self.assert_falha_sem_alteracao(db.ColisaoDeEmailError)
        self.assertEqual(erro.grupos_ids, [[3, 8]])

    def test_schema_incompativel_impede_a_inicializacao(self):
        self.criar_v5()
        self.sql(self.caminho_v5, f"CREATE INDEX {db.INDICE_EMAIL_CI} ON usuarios(lower(email))")
        self.assert_falha_sem_alteracao(db.SchemaV6IncompativelError)

    def test_coluna_homonima_incompativel_impede_a_inicializacao(self):
        self.criar_v5()
        self.sql(self.caminho_v5, "ALTER TABLE usuarios ADD COLUMN tema TEXT")
        self.assert_falha_sem_alteracao(db.SchemaV6IncompativelError, regex="usuarios.tema")

    def test_schema_v5_incompleto_impede_a_inicializacao(self):
        self.sql(self.caminho_v5, "CREATE TABLE usuarios (id INTEGER PRIMARY KEY, email TEXT)")
        schema_antes = self.schema(self.caminho_v5)

        with self.assertRaisesRegex(RuntimeError, "Schema v5 incompleto"):
            db.preparar_banco()

        self.assertEqual(self.schema(self.caminho_v5), schema_antes)
        self.assertEqual(self.backups(), [])

    def test_falha_de_backup_preserva_o_banco(self):
        self.criar_v5()
        with mock.patch.object(db, "criar_backup", side_effect=OSError("disco cheio")):
            self.assert_falha_sem_alteracao(OSError, regex="disco cheio")

    def test_falha_durante_a_migracao_faz_rollback(self):
        self.criar_v5()
        colunas_com_falha = db.COLUNAS_V6 + (("tabela_inexistente", "x", "TEXT", ("TEXT", 0, None)),)
        with mock.patch.object(db, "COLUNAS_V6", colunas_com_falha):
            self.assert_falha_sem_alteracao(sqlite3.OperationalError, backups_esperados=1)

    def test_arquivo_invalido_impede_a_inicializacao_sem_alterar_o_arquivo(self):
        with open(self.caminho_v5, "wb") as arquivo:
            arquivo.write(b"isto nao e um banco sqlite" * 200)
        sha_antes = self.sha256(self.caminho_v5)

        with self.assertRaises(sqlite3.DatabaseError):
            db.preparar_banco()

        self.assertEqual(self.sha256(self.caminho_v5), sha_antes)
        self.assertEqual(self.backups(), [])

    def test_banco_v6_que_falha_na_validacao_impede_a_inicializacao(self):
        self.criar_v6_populado()
        # FK órfã gravada com foreign_keys desligado: o schema está correto,
        # mas o banco não passa em validar_migracao_v6()
        self.sql(self.caminho_v5,
                 "INSERT INTO contas (usuario_id, nome, valor, data_vencimento) "
                 "VALUES (999, 'Órfã', 1.0, '2026-10-01')")
        estado_antes = self.estado()

        with self.assertRaises(db.BancoNaoPreparadoError) as contexto:
            db.preparar_banco()

        self.assertIn("violacoes_fk", str(contexto.exception))
        self.assertEqual(self.estado(), estado_antes)


class TesteInicializacaoInterface(AuxiliaresBancoV6):
    """backend/main.py: uma falha de preparação nunca chega ao login."""

    def pagina_falsa(self):
        pagina = mock.MagicMock()
        pagina.controls = []
        pagina.add.side_effect = lambda *controles: pagina.controls.extend(controles)
        return pagina

    @staticmethod
    def textos(controle):
        encontrados = []
        if isinstance(controle, ft.Text):
            encontrados.append(controle.value)
        for filho in getattr(controle, "controls", None) or []:
            encontrados.extend(TesteInicializacaoInterface.textos(filho))
        conteudo = getattr(controle, "content", None)
        if conteudo is not None and not isinstance(conteudo, str):
            encontrados.extend(TesteInicializacaoInterface.textos(conteudo))
        return encontrados

    def test_falha_de_preparacao_mostra_erro_e_nao_abre_o_login(self):
        pagina = self.pagina_falsa()
        erro = db.ColisaoDeEmailError([[3, 8]])
        stderr = io.StringIO()

        with mock.patch.object(main.database, "preparar_banco", side_effect=erro), \
                redirect_stderr(stderr):
            main.main(pagina)

        self.assertEqual(len(pagina.controls), 1)  # só a tela de erro
        textos = [t for c in pagina.controls for t in self.textos(c)]
        self.assertIn("Não foi possível abrir o Sino", textos)
        self.assertFalse(any("Bem-vindo" in t or "E-mail" in t for t in textos))
        self.assertFalse(any("ColisaoDeEmailError" in t or "3, 8" in t for t in textos))
        # o diagnóstico técnico completo fica no terminal
        self.assertIn("Traceback", stderr.getvalue())
        self.assertIn("ColisaoDeEmailError", stderr.getvalue())

    def test_banco_de_versao_futura_mostra_so_a_tela_de_erro(self):
        """De ponta a ponta, sem mock em preparar_banco."""
        criar_banco_v5(self.caminho_v5, conectar=apoio_banco._conectar_original)
        db.migrar_schema_v6(self.caminho_v5)
        self.sql(self.caminho_v5, "PRAGMA user_version = 7")
        sha_antes = self.sha256(self.caminho_v5)
        backups_antes = self.backups()
        pagina = self.pagina_falsa()
        stderr = io.StringIO()

        with mock.patch.object(db, "NOME_DO_BANCO", self.caminho_v5), redirect_stderr(stderr):
            main.main(pagina)

        textos = [t for c in pagina.controls for t in self.textos(c)]
        self.assertEqual(len(pagina.controls), 1)
        self.assertIn("Não foi possível abrir o Sino", textos)
        self.assertFalse(any("user_version" in t or "7" in t for t in textos))
        self.assertIn("VersaoDeBancoNaoSuportadaError", stderr.getvalue())
        self.assertEqual(self.sha256(self.caminho_v5), sha_antes)
        self.assertEqual(self.backups(), backups_antes)

    def test_preparacao_bem_sucedida_segue_para_o_login(self):
        pagina = self.pagina_falsa()
        with mock.patch.object(main.database, "preparar_banco",
                               return_value={"situacao": "atual", "migracao": None}):
            main.main(pagina)

        textos = [t for c in pagina.controls for t in self.textos(c)]
        self.assertIn("Bem-vindo de volta", textos)
        self.assertNotIn("Não foi possível abrir o Sino", textos)

    def test_migracao_na_inicializacao_informa_o_backup_no_terminal(self):
        pagina = self.pagina_falsa()
        resultado = {"situacao": "migrado", "migracao": {"executado": True, "backup": "/tmp/x/backup.db"}}
        stdout = io.StringIO()
        with mock.patch.object(main.database, "preparar_banco", return_value=resultado), \
                redirect_stdout(stdout):
            self.assertTrue(main.preparar_banco_ou_exibir_erro(pagina))
        self.assertIn("/tmp/x/backup.db", stdout.getvalue())

    def test_main_usa_o_banco_temporario_de_ponta_a_ponta(self):
        """Sem mocks em preparar_banco: o banco do teste é criado em v6 e o login abre."""
        pagina = self.pagina_falsa()
        with mock.patch.object(db, "NOME_DO_BANCO", self.caminho_v5):
            main.main(pagina)
        self.assert_schema_v6(self.caminho_v5)
        self.assertIn("Bem-vindo de volta", [t for c in pagina.controls for t in self.textos(c)])


if __name__ == "__main__":
    unittest.main()
