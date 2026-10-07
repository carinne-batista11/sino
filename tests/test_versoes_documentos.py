"""
ERS v7.0, 5.53 (M12, entrega E2): versões dos Termos de Uso e da Política de
Privacidade, registro do aceite por versão e fluxo de novo aceite no login.

Bancos e backups sempre temporários (apoio_banco); o banco real nunca é
aberto. O histórico de versões é trocado por versões fictícias (mock) para
simular mudanças futuras, relevantes ou menores, sem alterar os textos.
"""

import os
import sys
import unittest
from unittest import mock

import apoio_banco
from apoio_banco import TesteComBancoTemporario, _conectar_original, db
from test_cadastro_codigo_interface import BaseCadastro
from test_migracao_v6 import AuxiliaresBancoV6
from test_sessao_tema import PaginaFalsa, TesteDeSessao, ft, percorrer
from test_tela_principal import Evento

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import documentos  # noqa: E402
import main  # noqa: E402

INICIAL = "2026-10-04"
ATUAL = "2026-10-06"  # versão relevante aprovada pela autora (P38)


def historico(*extras_termos, extras_politica=(), base=None):
    """Histórico real (inteiro, ou só até `base` versões) + versões fictícias posteriores."""
    fatia = slice(None) if base is None else slice(base)
    return {
        "termos": documentos.HISTORICO_VERSOES["termos"][fatia] + tuple(extras_termos),
        "politica": documentos.HISTORICO_VERSOES["politica"][fatia] + tuple(extras_politica),
    }


def versao(data, classificacao, resumo="Resumo de teste."):
    return {"versao": data, "classificacao": classificacao, "resumo": resumo, "motivo": "teste"}


def sem_registros():
    return {chave: {"aceite": [], "ciencia": []} for chave in documentos.HISTORICO_VERSOES}


def aceitou_as_atuais():
    """Registros de quem aceitou as versões vigentes (ex.: cadastro atual)."""
    return {chave: {"aceite": [ATUAL], "ciencia": []} for chave in documentos.HISTORICO_VERSOES}


# ----------------------------------------------------------------------
#  Histórico e textos (docs/legal)
# ----------------------------------------------------------------------
class TestHistoricoDeVersoes(unittest.TestCase):
    def test_versoes_registradas(self):  # P37, P38
        for chave in ("termos", "politica"):
            with self.subTest(chave):
                versoes = documentos.HISTORICO_VERSOES[chave]
                self.assertEqual([(v["versao"], v["classificacao"]) for v in versoes],
                                 [(INICIAL, "inicial"), (ATUAL, "relevante")])
                self.assertIn("Última atualização: 06/10/2026", documentos.DOCUMENTOS[chave][1])

    def test_textos_de_04_10_preservados_no_historico(self):
        for chave, nome in (("termos", "termos-de-uso"), ("politica", "politica-de-privacidade")):
            with self.subTest(chave):
                antigo = documentos.caminho_historico(chave, INICIAL).read_text(encoding="utf-8")
                self.assertIn("Última atualização: 04/10/2026", antigo)
                self.assertNotEqual(antigo, documentos.DOCUMENTOS[chave][1])

    def test_afirmacoes_desatualizadas_corrigidas(self):
        termos, politica = documentos.TERMOS_DE_USO, documentos.POLITICA_DE_PRIVACIDADE
        self.assertNotIn("não registra qual versão do texto foi aceita", termos)
        self.assertNotIn("não há controle de versões do texto", politica)
        self.assertIn("O Sino registra qual versão destes termos foi aceita no cadastro.", termos)
        self.assertIn("*Registros de aceite e de ciência dos documentos:*", politica)
        self.assertIn("**não** equivale a um aceite", politica)
        self.assertIn("Nas contas criadas antes desta versão, o aceite original permanece registrado apenas pela "
                      "data, sem versão identificada.", politica)
        self.assertIn("são apagados na exclusão da conta. Eles podem continuar existindo nas cópias de segurança "
                      "já feitas antes da exclusão (item 6)", politica)

    def test_historico_coerente(self):
        for chave, versoes in documentos.HISTORICO_VERSOES.items():
            with self.subTest(chave):
                datas = [v["versao"] for v in versoes]
                self.assertEqual(datas, sorted(set(datas)), "datas crescentes e sem repetição")
                self.assertEqual(versoes[0]["classificacao"], "inicial")
                for v in versoes[1:]:
                    self.assertIn(v["classificacao"], ("relevante", "menor"))
                    self.assertTrue(v["resumo"], "resumo obrigatório em versões novas")
                for v in versoes:
                    self.assertTrue(v["motivo"])

    def test_texto_vigente_identico_ao_arquivo_historico(self):
        for chave, (_, texto) in documentos.DOCUMENTOS.items():
            with self.subTest(chave):
                caminho = documentos.caminho_historico(chave, documentos.versao_atual(chave)["versao"])
                self.assertEqual(caminho.read_text(encoding="utf-8"), texto)

    def test_cada_versao_tem_arquivo_e_nenhum_arquivo_sobra(self):
        esperados = {documentos.caminho_historico(chave, v["versao"]).name
                     for chave, versoes in documentos.HISTORICO_VERSOES.items() for v in versoes}
        existentes = {p.name for p in documentos.PASTA_HISTORICO.glob("*.md") if p.name != "README.md"}
        self.assertEqual(existentes, esperados)
        self.assertEqual(sorted(esperados), ["politica-de-privacidade_2026-10-04.md", "politica-de-privacidade_2026-10-06.md",
                                             "termos-de-uso_2026-10-04.md", "termos-de-uso_2026-10-06.md"])

    def test_rotulo_e_versoes_atuais(self):
        self.assertEqual(documentos.rotulo_versao(INICIAL), "Versão de 04/10/2026")
        self.assertEqual(documentos.versoes_atuais(), {"termos": ATUAL, "politica": ATUAL})


# ----------------------------------------------------------------------
#  Regra de pendências (5.53)
# ----------------------------------------------------------------------
class TestPendencias(unittest.TestCase):
    def pendencias(self, registros, hist):
        with mock.patch.dict(documentos.HISTORICO_VERSOES, hist):
            return documentos.pendencias(registros)

    def test_versao_inicial_nao_pede_nada_a_quem_aceitou_antes_do_versionamento(self):
        self.assertEqual(self.pendencias(sem_registros(), historico(base=1)), {"aceite": [], "aviso": []})

    def test_versao_de_06_10_pede_aceite_a_quem_aceitou_antes_do_versionamento(self):  # P38
        resultado = documentos.pendencias(sem_registros())
        self.assertEqual([(i["documento"], i["versao"]) for i in resultado["aceite"]],
                         [("termos", ATUAL), ("politica", ATUAL)])
        self.assertEqual(resultado["aviso"], [])
        self.assertTrue(all(len(i["mudancas"]) == 1 for i in resultado["aceite"]))

    def test_quem_aceitou_as_versoes_atuais_nao_tem_pendencia(self):
        self.assertEqual(documentos.pendencias(aceitou_as_atuais()), {"aceite": [], "aviso": []})

    def test_versao_relevante_pede_aceite_a_quem_aceitou_antes_do_versionamento(self):  # CT151
        hist = historico(versao("2026-12-01", "relevante", "Envio real de e-mails."), base=1)
        resultado = self.pendencias(sem_registros(), hist)
        self.assertEqual([i["documento"] for i in resultado["aceite"]], ["termos"])
        item = resultado["aceite"][0]
        self.assertEqual(item["versao"], "2026-12-01")
        self.assertEqual([m["resumo"] for m in item["mudancas"]], ["Envio real de e-mails."])
        self.assertEqual(resultado["aviso"], [])

    def test_versao_relevante_pede_aceite_a_quem_aceitou_uma_versao_anterior(self):
        hist = historico(versao("2026-12-01", "relevante"))
        resultado = self.pendencias(aceitou_as_atuais(), hist)
        self.assertEqual([i["documento"] for i in resultado["aceite"]], ["termos"])

    def test_quem_ja_aceitou_a_versao_relevante_nao_aceita_de_novo(self):
        hist = historico(versao("2026-12-01", "relevante"))
        registros = aceitou_as_atuais()
        registros["termos"]["aceite"] = [ATUAL, "2026-12-01"]
        self.assertEqual(self.pendencias(registros, hist), {"aceite": [], "aviso": []})

    def test_ciencia_nao_substitui_o_aceite_de_versao_relevante(self):
        hist = historico(versao("2026-12-01", "relevante"))
        registros = aceitou_as_atuais()
        registros["termos"]["ciencia"] = ["2026-12-01"]
        self.assertEqual(len(self.pendencias(registros, hist)["aceite"]), 1)

    def test_ajuste_menor_so_avisa(self):  # CT152
        hist = historico(extras_politica=(versao("2026-11-10", "menor", "Correção de redação."),))
        resultado = self.pendencias(aceitou_as_atuais(), hist)
        self.assertEqual(resultado["aceite"], [])
        self.assertEqual([i["documento"] for i in resultado["aviso"]], ["politica"])
        self.assertEqual(resultado["aviso"][0]["mudancas"][0]["resumo"], "Correção de redação.")

    def test_ciencia_ou_aceite_encerram_o_aviso(self):
        hist = historico(extras_politica=(versao("2026-11-10", "menor"),))
        for tipo in ("ciencia", "aceite"):
            with self.subTest(tipo):
                registros = aceitou_as_atuais()
                registros["politica"][tipo] = registros["politica"][tipo] + ["2026-11-10"]
                self.assertEqual(self.pendencias(registros, hist), {"aceite": [], "aviso": []})

    def test_relevante_seguida_de_menor(self):
        hist = historico(versao("2026-12-01", "relevante", "R"), versao("2027-01-05", "menor", "M"))
        # Sem aceite da relevante: aceite pendente, com as duas mudanças no resumo.
        resultado = self.pendencias(aceitou_as_atuais(), hist)
        self.assertEqual([m["resumo"] for m in resultado["aceite"][0]["mudancas"]], ["R", "M"])
        # Com a relevante aceita: só o aviso da menor.
        registros = aceitou_as_atuais()
        registros["termos"]["aceite"] = [ATUAL, "2026-12-01"]
        resultado = self.pendencias(registros, hist)
        self.assertEqual(resultado["aceite"], [])
        self.assertEqual([m["resumo"] for m in resultado["aviso"][0]["mudancas"]], ["M"])


# ----------------------------------------------------------------------
#  Banco: registro dos aceites
# ----------------------------------------------------------------------
class TestRegistroNoBanco(TesteComBancoTemporario):
    def test_usuario_antigo_nao_tem_versao_atribuida(self):
        ana = self.criar_usuario(email="ana@sino.com", senha="senha1234", aceitar_versoes_atuais=False)
        self.assertEqual(db.registros_de_documentos(ana), sem_registros())

    def test_registrar_aceite_e_ciencia(self):
        ana = self.criar_usuario(email="ana@sino.com", senha="senha1234", aceitar_versoes_atuais=False)
        db.registrar_documentos(ana, aceites={"termos": "2026-12-01"}, ciencias={"politica": "2026-11-10"})
        registros = db.registros_de_documentos(ana)
        self.assertEqual(registros["termos"], {"aceite": ["2026-12-01"], "ciencia": []})
        self.assertEqual(registros["politica"], {"aceite": [], "ciencia": ["2026-11-10"]})
        linha = self.sql("SELECT registrado_em FROM aceites_documentos WHERE documento = 'termos'")
        self.assertRegex(linha[0][0], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")

    def test_registro_repetido_mantem_o_primeiro(self):
        ana = self.criar_usuario(email="ana@sino.com", senha="senha1234", aceitar_versoes_atuais=False)
        db.registrar_documentos(ana, aceites={"termos": INICIAL})
        primeiro = self.sql("SELECT id, registrado_em FROM aceites_documentos")
        db.registrar_documentos(ana, aceites={"termos": INICIAL})
        self.assertEqual(self.sql("SELECT id, registrado_em FROM aceites_documentos"), primeiro)

    def test_recusas_nao_gravam_nada(self):
        ana = self.criar_usuario(email="ana@sino.com", senha="senha1234", aceitar_versoes_atuais=False)
        casos = [
            (ValueError, {"aceites": {"contrato": INICIAL}}),
            (ValueError, {"aceites": {"termos": "04/10/2026"}}),
            (ValueError, {"aceites": {"termos": "2026-02-30"}}),
            (TypeError, {"aceites": ["termos"]}),
        ]
        for excecao, argumentos in casos:
            with self.subTest(argumentos):
                with self.assertRaises(excecao):
                    db.registrar_documentos(ana, **argumentos)
        with self.assertRaises(db.ContaNaoEncontradaError):
            db.registrar_documentos(999, aceites={"termos": INICIAL})
        self.assertEqual(self.sql("SELECT COUNT(*) FROM aceites_documentos"), [(0,)])

    def test_cadastro_grava_as_versoes_aceitas(self):
        from test_autorizacoes_locais import Relogio, autorizacao
        usuario = db.concluir_cadastro(autorizacao("cadastro", "nova@sino.com"), "Nova", "nova@sino.com",
                                       db.hash_de_nova_senha("senhaforte1"), Relogio(),
                                       documentos.versoes_atuais())
        registros = db.registros_de_documentos(usuario)
        self.assertEqual(registros["termos"]["aceite"], [ATUAL])
        self.assertEqual(registros["politica"]["aceite"], [ATUAL])

    def test_cadastro_com_versao_invalida_nao_cria_usuario(self):
        from test_autorizacoes_locais import Relogio, autorizacao
        with self.assertRaises(ValueError):
            db.concluir_cadastro(autorizacao("cadastro", "x@sino.com"), "X", "x@sino.com",
                                 db.hash_de_nova_senha("senhaforte1"), Relogio(), {"termos": "ontem"})
        self.assertEqual(self.sql("SELECT COUNT(*) FROM usuarios"), [(0,)])

    def test_excluir_usuario_apaga_os_registros_de_aceite(self):
        ana = self.criar_usuario(email="ana@sino.com", senha="senha1234")
        bia = self.criar_usuario(email="bia@sino.com", senha="senha5678")
        db.excluir_usuario(db.conferir_senha_para_exclusao(ana, "senha1234"))
        self.assertEqual(self.sql("SELECT DISTINCT usuario_id FROM aceites_documentos"), [(bia,)])
        self.assertTrue(db.validar_schema_atual()["ok"])

    def test_validacao_recusa_registro_fora_do_formato(self):
        ana = self.criar_usuario(email="ana@sino.com", senha="senha1234", aceitar_versoes_atuais=False)
        # Uma data gravada como BLOB passa no CHECK (tamanho), mas não na validação estrita.
        self.sql("INSERT INTO aceites_documentos (usuario_id, documento, versao, tipo, registrado_em) "
                 "VALUES (?, 'termos', '2026-10-04', 'aceite', CAST('2026-10-06T10:00:00' AS BLOB))", (ana,))
        validacao = db.validar_schema_atual()
        self.assertFalse(validacao["ok"])
        self.assertEqual(validacao["aceites_invalidos"], 1)

    def sql(self, consulta, parametros=()):
        conexao = _conectar_original(self.caminho_banco)
        try:
            resultado = conexao.execute(consulta, parametros).fetchall()
            conexao.commit()
            return resultado
        finally:
            conexao.close()


# ----------------------------------------------------------------------
#  Migração v8 -> v9 (CT153, CT154)
# ----------------------------------------------------------------------
class TestMigracaoV9(AuxiliaresBancoV6):
    def criar_v8(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)
        db.migrar_schema_v7(self.caminho_v5)
        db.migrar_schema_v8(self.caminho_v5)

    def dados_v8(self, caminho):
        conexao = _conectar_original(caminho)
        try:
            return db._dados_v8(conexao.cursor())
        finally:
            conexao.close()

    def backups_v9(self):
        return [b for b in self.backups() if b.startswith("sino_pre_migracao_v9_")]

    def assert_recusado(self, excecao, regex):
        dump_antes, sha_antes, backups_antes = (self.dump_completo(self.caminho_v5),
                                                self.sha256(self.caminho_v5), self.backups())
        with self.assertRaisesRegex(excecao, regex):
            db.migrar_schema_v9(self.caminho_v5)
        self.assertEqual(self.dump_completo(self.caminho_v5), dump_antes)
        self.assertEqual(self.sha256(self.caminho_v5), sha_antes)
        self.assertEqual(self.backups(), backups_antes)
        self.assert_sem_transacao_nem_lock(self.caminho_v5)

    def test_v8_com_usuarios_passa_pela_v9(self):  # CT153
        self.criar_v8()
        dados_antes = self.dados_v8(self.caminho_v5)
        aceites_antes = self.sql(self.caminho_v5, "SELECT id, termos_aceitos_em FROM usuarios ORDER BY id")
        self.assertTrue(aceites_antes)

        resultado = db.migrar_schema_v9(self.caminho_v5)

        self.assertTrue(resultado["executado"])
        self.assertFalse(resultado["tabela_reaproveitada"])
        self.assertEqual(self.backups_v9(), [os.path.basename(resultado["backup"])])
        self.assert_schema_v9(self.caminho_v5)
        self.assertTrue(db.validar_schema_atual(self.caminho_v5)["ok"])
        self.assertEqual(self.dados_v8(self.caminho_v5), dados_antes)
        # Aceites antigos continuam só como data, sem versão atribuída.
        self.assertEqual(self.sql(self.caminho_v5, "SELECT id, termos_aceitos_em FROM usuarios ORDER BY id"),
                         aceites_antes)
        self.assertEqual(self.sql(self.caminho_v5, "SELECT COUNT(*) FROM aceites_documentos"), [(0,)])
        self.assert_sem_transacao_nem_lock(self.caminho_v5)

    def test_backup_e_do_estado_v8_e_integro(self):
        self.criar_v8()
        dump_v8 = self.dump_completo(self.caminho_v5)
        resultado = db.migrar_schema_v9(self.caminho_v5)
        backup = os.path.join(self.pasta_backups, os.path.basename(resultado["backup"]))
        self.assertEqual(self.sql(backup, "PRAGMA user_version")[0][0], 8)
        self.assertEqual(self.sql(backup, "PRAGMA integrity_check"), [("ok",)])
        self.assertEqual(self.dump_completo(backup), dump_v8)

    def test_falha_no_meio_da_v9_deixa_o_banco_em_v8(self):  # CT154
        self.criar_v8()
        dump_antes = self.dump_completo(self.caminho_v5)
        with mock.patch.object(db, "_criar_tabela_aceites", side_effect=RuntimeError("falha simulada")):
            with self.assertRaisesRegex(RuntimeError, "falha simulada"):
                db.migrar_schema_v9(self.caminho_v5)
        self.assertEqual(self.sql(self.caminho_v5, "PRAGMA user_version")[0][0], 8)
        self.assertEqual(self.dump_completo(self.caminho_v5), dump_antes)
        self.assertEqual(len(self.backups_v9()), 1)  # o backup permanece no disco
        self.assert_sem_transacao_nem_lock(self.caminho_v5)
        # A próxima tentativa completa a migração.
        self.assertTrue(db.migrar_schema_v9(self.caminho_v5)["executado"])
        self.assert_schema_v9(self.caminho_v5)

    def test_falha_na_v9_mostra_a_tela_de_erro_e_nao_abre_o_login(self):  # CT154
        self.criar_v8()
        pagina = PaginaFalsa().configurar()
        with mock.patch.object(db, "NOME_DO_BANCO", self.caminho_v5), \
                mock.patch.object(db, "_criar_tabela_aceites", side_effect=RuntimeError("falha simulada")), \
                mock.patch("sys.stderr"):
            main.main(pagina)
        textos = [c.value for raiz in pagina.controls for c in percorrer(raiz) if isinstance(c, ft.Text)]
        self.assertIn("Não foi possível abrir o Sino", textos)
        self.assertNotIn("Bem-vindo de volta", textos)
        self.assertEqual(self.sql(self.caminho_v5, "PRAGMA user_version")[0][0], 8)

    def test_execucao_repetida_nao_altera_nada(self):
        self.criar_v8()
        db.migrar_schema_v9(self.caminho_v5)
        sha, backups = self.sha256(self.caminho_v5), self.backups()
        self.assertEqual(db.migrar_schema_v9(self.caminho_v5),
                         {"executado": False, "motivo": "já migrado", "backup": None})
        self.assertEqual((self.sha256(self.caminho_v5), self.backups()), (sha, backups))
        # As migrações anteriores reconhecem o banco v9 como migrado.
        for migrar in (db.migrar_schema_v8, db.migrar_schema_v7, db.migrar_schema_v6):
            self.assertEqual(migrar(self.caminho_v5)["motivo"], "já migrado")

    def test_banco_novo_e_banco_migrado_tem_o_mesmo_schema(self):
        self.criar_v8()
        db.migrar_schema_v9(self.caminho_v5)
        consulta = "SELECT type, name, sql FROM sqlite_master WHERE tbl_name = 'aceites_documentos' ORDER BY name"
        self.assertEqual(self.sql(self.caminho_v5, consulta), self.sql(self.caminho_banco, consulta))
        self.assertEqual(self.sql(self.caminho_banco, "PRAGMA user_version")[0][0], 9)

    def test_v7_e_recusado_sem_alteracao(self):
        self.criar_v5()
        db.migrar_schema_v6(self.caminho_v5)
        db.migrar_schema_v7(self.caminho_v5)
        self.assert_recusado(db.SchemaV9IncompativelError, "migração v8 antes da v9")

    def test_v8_com_tabela_diferente_e_recusado(self):
        self.criar_v8()
        self.sql(self.caminho_v5, db.DDL_ACEITES.replace("UNIQUE (usuario_id, documento, versao, tipo)",
                                                         "UNIQUE (usuario_id, documento, versao)"))
        self.assert_recusado(db.SchemaV9IncompativelError, "definição diferente")

    def test_v8_com_tabela_identica_e_vazia_e_reaproveitada(self):
        self.criar_v8()
        self.sql(self.caminho_v5, db.DDL_ACEITES)
        resultado = db.migrar_schema_v9(self.caminho_v5)
        self.assertTrue(resultado["tabela_reaproveitada"])
        self.assert_schema_v9(self.caminho_v5)

    def test_v9_sem_a_tabela_e_recusado(self):
        self.criar_v8()
        self.sql(self.caminho_v5, "PRAGMA user_version = 9")
        self.assert_recusado(db.SchemaV9IncompativelError, "banco v9 com aceites_documentos ausente")

    def test_restricoes_da_tabela(self):
        self.criar_v8()
        db.migrar_schema_v9(self.caminho_v5)
        conexao = _conectar_original(self.caminho_v5)
        conexao.execute("PRAGMA foreign_keys = ON")
        try:
            for valores in ((1, "contrato", INICIAL, "aceite", "2026-10-06T10:00:00"),
                            (1, "termos", "2026-1-04", "aceite", "2026-10-06T10:00:00"),
                            (1, "termos", INICIAL, "leitura", "2026-10-06T10:00:00"),
                            (1, "termos", INICIAL, "aceite", ""),
                            (999, "termos", INICIAL, "aceite", "2026-10-06T10:00:00")):
                with self.subTest(valores), self.assertRaises(Exception):
                    conexao.execute("INSERT INTO aceites_documentos (usuario_id, documento, versao, tipo, "
                                    "registrado_em) VALUES (?, ?, ?, ?, ?)", valores)
        finally:
            conexao.close()


# ----------------------------------------------------------------------
#  Interface: versão exibida, cadastro, novo aceite e aviso (CT151, CT152)
# ----------------------------------------------------------------------
class TestInterfaceDeVersoes(TesteDeSessao):
    def textos(self, pagina):
        return [t.value for t in self.controles(pagina, ft.Text)]

    def botao(self, pagina, data):
        return next(c for c in self.controles(pagina) if getattr(c, "data", None) == data)

    def entrar_com_historico(self, hist, email="bia@sino.com", senha="senha5678"):
        pagina, sessao = self.abrir_app()
        with mock.patch.dict(documentos.HISTORICO_VERSOES, hist):
            self.entrar(pagina, email, senha)
        return pagina, sessao

    def test_sem_mudancas_o_login_entra_direto(self):
        pagina, sessao = self.entrar_com_historico(historico())
        self.assertEqual(sessao.usuario["id"], self.bia)
        self.assertNotIn("Os documentos do Sino mudaram", self.textos(pagina))
        self.assertEqual(pagina.dialogos, [])

    def test_versao_relevante_exige_novo_aceite_antes_de_entrar(self):  # CT151
        hist = historico(versao("2026-12-01", "relevante", "Envio real de códigos por e-mail."))
        pagina, sessao = self.entrar_com_historico(hist)
        self.assertIsNone(sessao.usuario["id"])  # sem aceite, não entra
        textos = self.textos(pagina)
        self.assertIn("Os documentos do Sino mudaram", textos)
        self.assertIn("Termos de Uso — Versão de 01/12/2026", textos)
        self.assertIn("• Versão de 01/12/2026: Envio real de códigos por e-mail.", textos)
        self.assertNotIn("Política de Privacidade — Versão de 06/10/2026", textos)
        # A tela é exibida no tema Claro, mesmo para quem usa o Escuro.
        self.assertEqual(sessao.cores.tema, "claro")

        with mock.patch.dict(documentos.HISTORICO_VERSOES, hist):
            aceitar = self.botao(pagina, "aceitar_documentos")
            aceitar.on_click(Evento(pagina, aceitar))
        self.assertEqual(sessao.usuario["id"], self.bia)
        self.assertEqual(db.registros_de_documentos(self.bia)["termos"]["aceite"], [ATUAL, "2026-12-01"])
        self.assertEqual(db.registros_de_documentos(self.bia)["politica"]["aceite"], [ATUAL])

    def test_sair_da_tela_de_novo_aceite_volta_ao_login_sem_registrar(self):  # CT151
        hist = historico(versao("2026-12-01", "relevante"))
        pagina, sessao = self.entrar_com_historico(hist)
        sair = self.botao(pagina, "sair_novo_aceite")
        sair.on_click(Evento(pagina, sair))
        self.assertIsNone(sessao.usuario["id"])
        self.assertIn("Bem-vindo de volta", self.textos(pagina))
        self.assertEqual(db.registros_de_documentos(self.bia)["termos"], {"aceite": [ATUAL], "ciencia": []})
        # No próximo login, a tela volta.
        with mock.patch.dict(documentos.HISTORICO_VERSOES, hist):
            self.entrar(pagina, "bia@sino.com", "senha5678")
        self.assertIn("Os documentos do Sino mudaram", self.textos(pagina))

    def test_ler_documento_na_tela_de_novo_aceite_e_voltar(self):
        hist = historico(versao("2026-12-01", "relevante"))
        pagina, _ = self.entrar_com_historico(hist)
        with mock.patch.dict(documentos.HISTORICO_VERSOES, hist):
            ler = self.botao(pagina, "ler_termos")
            ler.on_click(Evento(pagina, ler))
            self.assertTrue(any(getattr(c, "data", None) == "documento_termos" for c in self.controles(pagina)))
            voltar = next(b for b in self.controles(pagina, ft.TextButton) if b.content == "Voltar")
            voltar.on_click(Evento(pagina, voltar))
        self.assertIn("Os documentos do Sino mudaram", self.textos(pagina))

    def test_falha_ao_registrar_o_aceite_mantem_a_tela_sem_entrar(self):
        hist = historico(versao("2026-12-01", "relevante"))
        pagina, sessao = self.entrar_com_historico(hist)
        with mock.patch.dict(documentos.HISTORICO_VERSOES, hist), \
                mock.patch.object(main.database, "registrar_documentos", side_effect=OSError("disco")), \
                mock.patch.object(main.fluxos_codigo, "registrar_falha"):
            aceitar = self.botao(pagina, "aceitar_documentos")
            aceitar.on_click(Evento(pagina, aceitar))
        self.assertIsNone(sessao.usuario["id"])
        self.assertIn("Não foi possível registrar o aceite. Tente novamente.", self.textos(pagina))

    def test_ajuste_menor_avisa_sem_bloquear(self):  # CT152
        hist = historico(extras_politica=(versao("2026-11-10", "menor", "Correção de um link."),))
        pagina, sessao = self.entrar_com_historico(hist)
        self.assertEqual(sessao.usuario["id"], self.bia)  # entra sem aceite
        self.assertNotIn("Os documentos do Sino mudaram", self.textos(pagina))
        aviso = next(d for d in pagina.dialogos if d.data == "aviso_documentos")
        self.assertTrue(aviso.open)
        textos_aviso = [c.value for c in percorrer(aviso.content) if isinstance(c, ft.Text)]
        self.assertIn("• Versão de 10/11/2026: Correção de um link.", textos_aviso)

        entendi = aviso.actions[0]
        with mock.patch.dict(documentos.HISTORICO_VERSOES, hist):
            entendi.on_click(Evento(pagina, entendi))
        self.assertFalse(aviso.open)
        self.assertEqual(db.registros_de_documentos(self.bia)["politica"]["ciencia"], ["2026-11-10"])

    def test_conta_antiga_aceita_a_versao_de_06_10_sem_versao_no_aceite_original(self):  # P38
        carla = self.criar_usuario(email="carla@sino.com", senha="senha9012", aceitar_versoes_atuais=False)
        data_original = self.consultar("SELECT termos_aceitos_em FROM usuarios WHERE id = ?", (carla,))[0][0]
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "carla@sino.com", "senha9012")
        self.assertIsNone(sessao.usuario["id"])
        textos = self.textos(pagina)
        self.assertIn("Termos de Uso — Versão de 06/10/2026", textos)
        self.assertIn("Política de Privacidade — Versão de 06/10/2026", textos)
        aceitar = self.botao(pagina, "aceitar_documentos")
        aceitar.on_click(Evento(pagina, aceitar))
        self.assertEqual(sessao.usuario["id"], carla)
        self.assertEqual(db.registros_de_documentos(carla),
                         {"termos": {"aceite": [ATUAL], "ciencia": []},
                          "politica": {"aceite": [ATUAL], "ciencia": []}})
        # O aceite original continua só com a data: nenhuma versão de 04/10 foi atribuída.
        self.assertEqual(self.consultar("SELECT termos_aceitos_em FROM usuarios WHERE id = ?", (carla,))[0][0],
                         data_original)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM aceites_documentos WHERE usuario_id = ? AND versao = ?",
                                        (carla, INICIAL))[0][0], 0)

    def test_documento_mostra_a_versao_vigente(self):
        pagina, _ = self.abrir_app()
        alternar = next(b for b in self.controles(pagina, ft.TextButton) if b.content == "Não tem conta? Criar conta")
        alternar.on_click(Evento(pagina, alternar))
        for chave, rotulo in (("termos", "Termos de Uso"), ("politica", "Política de Privacidade")):
            with self.subTest(chave):
                ler = next(b for b in self.controles(pagina, ft.TextButton) if b.content == f"Ler {rotulo}")
                ler.on_click(Evento(pagina, ler))
                rotulo_versao = next(c for c in self.controles(pagina) if getattr(c, "data", None) == f"versao_{chave}")
                self.assertEqual(rotulo_versao.value, "Versão de 06/10/2026")
                voltar = next(b for b in self.controles(pagina, ft.TextButton) if b.content == "Voltar")
                voltar.on_click(Evento(pagina, voltar))


class TestCadastroRegistraVersoes(BaseCadastro):
    def test_cadastro_pela_interface_grava_o_aceite_das_versoes_vigentes(self):
        pagina, _ = self.abrir_cadastro()
        self.ate_o_codigo(pagina)
        self.confirmar(pagina, self.servidor.ultimo_codigo("carla@sino.com"))
        pagina.executar_pendentes()
        usuario_id = self.usuario()[0]
        registros = db.registros_de_documentos(usuario_id)
        self.assertEqual(registros["termos"]["aceite"], [ATUAL])
        self.assertEqual(registros["politica"]["aceite"], [ATUAL])
        # Quem acabou de aceitar as versões vigentes entra sem novo aceite nem aviso.
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "carla@sino.com", "senhaforte1")
        self.assertEqual(sessao.usuario["id"], usuario_id)
        self.assertEqual(pagina.dialogos, [])


if __name__ == "__main__":
    unittest.main()
