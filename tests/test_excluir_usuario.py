"""
ERS v6.0, Etapa 9 — Excluir conta (5.39, RF43; CT100-CT102; decisão T2).

Camada de dados: resumo informativo, conferência da senha atual (pendência
com a impressão do hash), exclusão explícita em uma única transação
(contas -> séries -> categorias -> usuário), revalidação da senha na
transação, reversão completa em qualquer falha, preservação dos registros e
das relações dos outros usuários e de `autorizacoes_usadas`.

Interface: item em Ajustes > Conta e sessão, aviso com as quantidades,
senha atual e confirmação final com botão destrutivo; cancelar em qualquer
passo não altera nada; sucesso encerra a sessão e volta ao login.

Tudo em bancos temporários (apoio_banco) e páginas falsas; nenhuma janela é
aberta e o banco real nunca é tocado.
"""

import asyncio
import io
import sqlite3
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from apoio_banco import TesteComBancoTemporario, _conectar_original, db
from test_alterar_email_interface import NOVO, BaseAlteracao
from test_autorizacoes_locais import INICIO, Relogio, autorizacao
from test_cores import MINIMO_TEXTO, contraste
from test_sessao_tema import CLARO, ESCURO, TesteDeSessao, ft, main, percorrer
from test_tela_principal import Evento

SENHA_ANA = "senha1234"   # definidas em TesteDeSessao
SENHA_BIA = "senha5678"


def popular(teste, usuario_id, prefixo):
    """Categorias padrão, uma conta única, uma série mensal e uma conta paga."""
    db.inicializar_categorias_padrao(usuario_id)
    categoria = teste.criar_categoria(usuario_id, f"{prefixo} Casa")
    db.criar_conta_unica(usuario_id, f"{prefixo} Avulsa", 50.0, "2026-09-20", categoria_id=categoria,
                         descricao="descrição")
    db.criar_serie_recorrente(usuario_id, f"{prefixo} Internet", 99.9, "2026-09-10", "mensal",
                              categoria_id=categoria)
    paga = db.criar_conta_unica(usuario_id, f"{prefixo} Paga", 10.0, "2026-09-01")
    db.marcar_conta_como_paga(paga, "2026-09-02")


def registros_do_usuario(teste, usuario_id):
    """Todas as linhas do usuário, com as relações (série e categoria de cada conta)."""
    return {
        "usuario": teste.consultar("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)),
        "categorias": teste.consultar("SELECT * FROM categorias WHERE usuario_id = ? ORDER BY id", (usuario_id,)),
        "series": teste.consultar("SELECT * FROM series_recorrencia WHERE usuario_id = ? ORDER BY id", (usuario_id,)),
        "contas": teste.consultar("SELECT * FROM contas WHERE usuario_id = ? ORDER BY id", (usuario_id,)),
        "relacoes": teste.consultar(
            """
            SELECT c.id, s.id, s.usuario_id, k.id, k.usuario_id, ks.id, ks.usuario_id
            FROM contas c
            LEFT JOIN series_recorrencia s ON s.id = c.serie_id
            LEFT JOIN categorias k ON k.id = c.categoria_id
            LEFT JOIN categorias ks ON ks.id = s.categoria_id
            WHERE c.usuario_id = ? ORDER BY c.id
            """,
            (usuario_id,),
        ),
    }


def banco_inteiro(teste):
    return {tabela: teste.consultar(f"SELECT * FROM {tabela} ORDER BY rowid")
            for tabela in ("usuarios", "categorias", "series_recorrencia", "contas", "autorizacoes_usadas")}


# ======================================================================
#  Camada de dados
# ======================================================================
class BaseExclusao(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.ana = self.criar_usuario(email="ana@sino.com", senha=SENHA_ANA, nome="Ana")
        self.bia = self.criar_usuario(email="bia@sino.com", senha=SENHA_BIA, nome="Bia")
        self.caio = self.criar_usuario(email="caio@sino.com", senha="senha0000", nome="Caio")
        for usuario_id, prefixo in ((self.ana, "Ana"), (self.bia, "Bia"), (self.caio, "Caio")):
            popular(self, usuario_id, prefixo)
        self.executar("INSERT INTO autorizacoes_usadas VALUES (?, ?, ?)",
                      ("A" * 21 + "w", "cadastro", 4_000_000_000))

    def outros(self):
        return {u: registros_do_usuario(self, u) for u in (self.bia, self.caio)}

    def restantes_de(self, usuario_id):
        return {tabela: self.consultar(f"SELECT COUNT(*) FROM {tabela} WHERE usuario_id = ?", (usuario_id,))[0][0]
                for tabela in ("categorias", "series_recorrencia", "contas")}


class TestResumo(BaseExclusao):
    def test_quantidades_do_usuario(self):
        esperado = {"contas": self.restantes_de(self.ana)["contas"],
                    "series": self.restantes_de(self.ana)["series_recorrencia"],
                    "categorias": self.restantes_de(self.ana)["categorias"]}
        self.assertEqual(db.resumo_dados_do_usuario(self.ana), esperado)
        self.assertEqual(esperado["series"], 1)
        self.assertGreater(esperado["contas"], 2)          # inclui as ocorrências da série
        self.assertGreater(esperado["categorias"], 1)

    def test_usuario_inexistente(self):
        self.assertIsNone(db.resumo_dados_do_usuario(9999))

    def test_usuario_sem_dados(self):
        novo = self.criar_usuario(email="novo@sino.com")
        self.assertEqual(db.resumo_dados_do_usuario(novo), {"contas": 0, "series": 0, "categorias": 0})


class TestConferirSenha(BaseExclusao):
    def test_senha_correta_devolve_pendencia_sem_a_senha(self):
        pendencia = db.conferir_senha_para_exclusao(self.ana, SENHA_ANA)
        self.assertIs(type(pendencia), db.PendenciaExclusaoUsuario)
        self.assertEqual(pendencia.usuario_id, self.ana)
        self.assertNotIn(SENHA_ANA, repr(pendencia))
        self.assertNotIn(pendencia.impressao_senha, repr(pendencia))
        self.assertFalse(hasattr(pendencia, "__dict__"))   # só usuario_id e impressao_senha

    def test_senha_incorreta_ou_que_nao_e_texto(self):  # CT101
        antes = banco_inteiro(self)
        for senha in ("errada99", "", None, 1234, SENHA_ANA + " "):
            with self.subTest(senha=senha):
                with self.assertRaises(db.SenhaAtualIncorretaError):
                    db.conferir_senha_para_exclusao(self.ana, senha)
        self.assertEqual(banco_inteiro(self), antes)

    def test_senha_de_outro_usuario_nao_serve(self):
        with self.assertRaises(db.SenhaAtualIncorretaError):
            db.conferir_senha_para_exclusao(self.ana, SENHA_BIA)

    def test_usuario_inexistente(self):
        with self.assertRaises(db.ContaNaoEncontradaError):
            db.conferir_senha_para_exclusao(9999, SENHA_ANA)

    def test_senha_no_formato_antigo(self):
        self.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                      (db._gerar_hash_senha_legado("antiga"), self.ana))
        pendencia = db.conferir_senha_para_exclusao(self.ana, "antiga")
        db.excluir_usuario(pendencia)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM usuarios WHERE id = ?", (self.ana,))[0][0], 0)


class TestExcluirUsuario(BaseExclusao):
    def test_remove_o_usuario_e_os_dados_vinculados(self):  # CT102
        resumo = db.resumo_dados_do_usuario(self.ana)
        removidos = db.excluir_usuario(db.conferir_senha_para_exclusao(self.ana, SENHA_ANA))
        self.assertEqual(removidos, resumo)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM usuarios WHERE id = ?", (self.ana,)), [(0,)])
        self.assertEqual(self.restantes_de(self.ana), {"categorias": 0, "series_recorrencia": 0, "contas": 0})
        self.assertEqual(self.consultar("PRAGMA foreign_key_check"), [])
        self.assertEqual(self.consultar("PRAGMA integrity_check"), [("ok",)])

    def test_outros_usuarios_preservados_com_as_relacoes(self):
        antes = self.outros()
        db.excluir_usuario(db.conferir_senha_para_exclusao(self.ana, SENHA_ANA))
        self.assertEqual(self.outros(), antes)

    def test_autorizacoes_usadas_preservadas(self):
        antes = self.consultar("SELECT * FROM autorizacoes_usadas")
        db.excluir_usuario(db.conferir_senha_para_exclusao(self.ana, SENHA_ANA))
        self.assertEqual(self.consultar("SELECT * FROM autorizacoes_usadas"), antes)

    def test_login_antigo_falha_e_o_email_pode_ser_cadastrado_de_novo(self):  # CT102
        db.excluir_usuario(db.conferir_senha_para_exclusao(self.ana, SENHA_ANA))
        self.assertIsNone(db.verificar_login("ana@sino.com", SENHA_ANA))
        self.assertFalse(db.email_em_uso("ana@sino.com"))
        novo = db.concluir_cadastro(autorizacao("cadastro", "ana@sino.com"), "Ana Nova", "ana@sino.com",
                                    db.hash_de_nova_senha("outra-senha"), relogio=Relogio(INICIO))
        self.assertNotEqual(novo, self.ana)
        self.assertEqual(db.resumo_dados_do_usuario(novo)["contas"], 0)   # nada da conta antiga volta

    def test_exige_a_pendencia_da_conferencia(self):
        pendencia_email = db.conferir_senha_atual(self.ana, SENHA_ANA)
        antes = banco_inteiro(self)
        for invalida in (pendencia_email, self.ana, None):
            with self.subTest(invalida=invalida):
                with self.assertRaises(TypeError):
                    db.excluir_usuario(invalida)
        self.assertEqual(banco_inteiro(self), antes)

    def test_senha_trocada_entre_a_conferencia_e_a_exclusao(self):
        pendencia = db.conferir_senha_para_exclusao(self.ana, SENHA_ANA)
        self.assertTrue(db.alterar_senha(self.ana, SENHA_ANA, "nova-senha-1"))
        antes = banco_inteiro(self)
        with self.assertRaises(db.SenhaAlteradaDuranteOperacaoError):
            db.excluir_usuario(pendencia)
        self.assertEqual(banco_inteiro(self), antes)

    def test_usuario_ja_excluido(self):
        pendencia = db.conferir_senha_para_exclusao(self.ana, SENHA_ANA)
        db.excluir_usuario(pendencia)
        antes = banco_inteiro(self)
        with self.assertRaises(db.ContaNaoEncontradaError):
            db.excluir_usuario(pendencia)
        self.assertEqual(banco_inteiro(self), antes)

    def test_falha_no_meio_desfaz_tudo(self):
        # Gatilho só neste banco temporário: as contas, séries e categorias já
        # foram apagadas dentro da transação quando o DELETE do usuário falha.
        self.executar("CREATE TRIGGER falhar BEFORE DELETE ON usuarios BEGIN SELECT RAISE(ABORT, 'falha'); END")
        pendencia = db.conferir_senha_para_exclusao(self.ana, SENHA_ANA)
        antes = banco_inteiro(self)
        with self.assertRaises(sqlite3.IntegrityError):
            db.excluir_usuario(pendencia)
        self.assertEqual(banco_inteiro(self), antes)

    def test_referencia_de_outro_usuario_impede_a_exclusao(self):
        # Rede de segurança das chaves estrangeiras: um dado de Bia apontando
        # para uma categoria de Ana faz a exclusão falhar sem apagar nada.
        categoria_ana = self.consultar("SELECT id FROM categorias WHERE usuario_id = ? LIMIT 1", (self.ana,))[0][0]
        self.executar("INSERT INTO contas (usuario_id, categoria_id, nome, valor, data_vencimento) "
                      "VALUES (?, ?, 'Cruzada', 1.0, '2026-09-30')", (self.bia, categoria_ana))
        pendencia = db.conferir_senha_para_exclusao(self.ana, SENHA_ANA)
        antes = banco_inteiro(self)
        with self.assertRaises(sqlite3.IntegrityError):
            db.excluir_usuario(pendencia)
        self.assertEqual(banco_inteiro(self), antes)

    def test_banco_ocupado_nao_apaga_nada(self):
        pendencia = db.conferir_senha_para_exclusao(self.ana, SENHA_ANA)
        antes = banco_inteiro(self)
        bloqueio = _conectar_original(self.caminho_banco, isolation_level=None)
        self.addCleanup(bloqueio.close)
        bloqueio.execute("BEGIN IMMEDIATE;")
        with mock.patch.object(db, "conectar", lambda: _conectar_original(self.caminho_banco, timeout=0.05)):
            with self.assertRaises(sqlite3.OperationalError):
                db.excluir_usuario(pendencia)
        bloqueio.execute("ROLLBACK;")
        self.assertEqual(banco_inteiro(self), antes)

    def test_secure_delete_ligado_antes_da_transacao(self):
        comandos = []

        class Conexao(sqlite3.Connection):
            def execute(self, sql, *args):
                comandos.append(sql)
                return super().execute(sql, *args)

        def conectar():
            conexao = _conectar_original(self.caminho_banco, factory=Conexao)
            conexao.execute("PRAGMA foreign_keys = ON;")
            return conexao

        pendencia = db.conferir_senha_para_exclusao(self.ana, SENHA_ANA)
        with mock.patch.object(db, "conectar", conectar):
            db.excluir_usuario(pendencia)
        self.assertIn("PRAGMA secure_delete = ON;", comandos)

    def test_textos_apagados_nao_ficam_no_arquivo_principal(self):
        # Medida adicional (secure_delete), verificada só no arquivo principal
        # deste banco temporário. NÃO prova eliminação completa: backups,
        # journal, cópias do sistema e recuperação no dispositivo ficam fora.
        marca = "MarcaUnicaDaAna-7f3a"
        self.executar("UPDATE usuarios SET nome = ? WHERE id = ?", (marca, self.ana))
        self.executar("UPDATE contas SET descricao = ? WHERE usuario_id = ?", (marca, self.ana))
        with open(self.caminho_banco, "rb") as arquivo:
            self.assertIn(marca.encode(), arquivo.read())
        db.excluir_usuario(db.conferir_senha_para_exclusao(self.ana, SENHA_ANA))
        with open(self.caminho_banco, "rb") as arquivo:
            conteudo = arquivo.read()
        self.assertNotIn(marca.encode(), conteudo)
        self.assertNotIn(b"ana@sino.com", conteudo)
        self.assertIn(b"bia@sino.com", conteudo)


# ======================================================================
#  Interface
# ======================================================================
class TesteDeExclusaoNaInterface(TesteDeSessao):
    def setUp(self):
        super().setUp()
        popular(self, self.ana, "Ana")
        popular(self, self.bia, "Bia")

    @staticmethod
    def clicar(pagina, controle):
        controle.on_click(Evento(pagina, controle))

    def abrir_ajustes(self, email="ana@sino.com", senha=SENHA_ANA):
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, email, senha)
        self.abrir_aba(pagina, "Ajustes")
        return pagina, sessao

    def item(self, pagina):
        return next(c for c in self.controles(pagina, ft.Container) if c.data == "abrir_excluir_conta")

    @staticmethod
    def dialogo(pagina):
        abertos = [d for d in pagina.dialogos if d.open]
        return abertos[-1] if abertos else None

    def textos(self, dialogo):
        return [t.value for t in percorrer(dialogo) if isinstance(t, ft.Text) and t.value]

    def botao(self, dialogo, rotulo):
        return next(b for b in percorrer(dialogo)
                    if isinstance(b, (ft.Button, ft.TextButton)) and b.content == rotulo)

    def campo_senha(self, dialogo):
        return next(c for c in percorrer(dialogo) if isinstance(c, ft.TextField))

    def erro_visivel(self, dialogo):
        erros = [t for t in percorrer(dialogo) if isinstance(t, ft.Text) and t.visible and t.value
                 and t.color in (CLARO["texto_erro"], ESCURO["texto_erro"])]
        return erros[0].value if erros else None

    def ir_para_aviso(self, pagina):
        self.clicar(pagina, self.item(pagina))
        dialogo = self.dialogo(pagina)
        self.assertEqual(dialogo.data, "exclusao_aviso")
        return dialogo

    def ir_para_senha(self, pagina):
        self.clicar(pagina, self.botao(self.ir_para_aviso(pagina), "Continuar"))
        dialogo = self.dialogo(pagina)
        self.assertEqual(dialogo.data, "exclusao_senha")
        return dialogo

    def informar_senha(self, pagina, dialogo, senha):
        campo = self.campo_senha(dialogo)
        campo.value = senha
        campo.on_change(Evento(pagina, campo))
        terminal = io.StringIO()
        with redirect_stderr(terminal), redirect_stdout(terminal):
            self.clicar(pagina, self.botao(dialogo, "Continuar"))
        return terminal.getvalue()

    def ir_para_confirmacao(self, pagina, senha=SENHA_ANA):
        self.informar_senha(pagina, self.ir_para_senha(pagina), senha)
        dialogo = self.dialogo(pagina)
        self.assertEqual(dialogo.data, "exclusao_confirmacao")
        return dialogo

    def confirmar(self, pagina, dialogo):
        terminal = io.StringIO()
        with redirect_stderr(terminal), redirect_stdout(terminal):
            self.clicar(pagina, self.botao(dialogo, "Excluir conta"))
        return terminal.getvalue()

    def na_tela_ajustes(self, pagina):
        return any(getattr(c, "data", None) == "tela_ajustes" for c in self.controles(pagina))


class TestItemEmAjustes(TesteDeExclusaoNaInterface):
    def test_ultimo_item_de_conta_e_sessao_com_aparencia_destrutiva(self):
        pagina, _ = self.abrir_ajustes()
        secao = next(c for c in self.controles(pagina, ft.Container)
                     if "Conta e sessão" in [t.value for t in percorrer(c) if isinstance(t, ft.Text)]
                     and c.border is not None)
        clicaveis = [c for c in percorrer(secao) if isinstance(c, ft.Container) and c.on_click is not None]
        rotulos = [[t.value for t in percorrer(c) if isinstance(t, ft.Text)][0] for c in clicaveis]
        self.assertEqual(rotulos, ["Sair da conta", "Excluir conta"])
        item = self.item(pagina)
        rotulo = next(t for t in percorrer(item) if isinstance(t, ft.Text) and t.value == "Excluir conta")
        icone = next(i for i in percorrer(item) if isinstance(i, ft.Icon) and i.icon == ft.Icons.DELETE_FOREVER)
        self.assertEqual(rotulo.color, ESCURO["acao_destrutiva"])   # Ana usa o tema escuro
        self.assertEqual(icone.color, ESCURO["acao_destrutiva"])
        self.assertIn("Apague sua conta de usuário e todos os seus dados.",
                      [t.value for t in percorrer(item) if isinstance(t, ft.Text)])

    def test_nunca_exclui_com_um_unico_clique(self):
        pagina, _ = self.abrir_ajustes()
        antes = banco_inteiro(self)
        with mock.patch.object(main.database, "excluir_usuario") as excluir:
            self.clicar(pagina, self.item(pagina))
        excluir.assert_not_called()
        self.assertEqual(banco_inteiro(self), antes)


class TestPassos(TesteDeExclusaoNaInterface):
    def test_aviso_com_quantidades_permanencia_e_backups(self):
        pagina, _ = self.abrir_ajustes()
        resumo = db.resumo_dados_do_usuario(self.ana)
        dialogo = self.ir_para_aviso(pagina)
        textos = self.textos(dialogo)
        self.assertEqual(dialogo.title.value, "Excluir sua conta do Sino?")
        self.assertIn(f"• {resumo['contas']} contas registradas", textos)
        self.assertIn("• 1 série recorrente", textos)
        self.assertIn("As contas incluem os meses futuros já gerados das recorrências.", textos)  # Etapa 10
        self.assertIn(f"• {resumo['categorias']} categorias", textos)
        juntos = " ".join(textos)
        self.assertIn("permanentemente do banco de dados atual do Sino", juntos)
        self.assertIn("Não é possível desfazer a exclusão.", juntos)
        self.assertIn("Cópias de segurança (backups) já existentes não são apagadas.", juntos)
        self.assertEqual([b.content for b in percorrer(dialogo) if isinstance(b, (ft.Button, ft.TextButton))],
                         ["Cancelar", "Continuar"])

    def test_singular_e_plural(self):
        self.assertEqual(main.linhas_dados_da_exclusao({"contas": 1, "series": 0, "categorias": 1}),
                         ["1 conta registrada", "0 séries recorrentes", "1 categoria"])
        self.assertEqual(main.linhas_dados_da_exclusao({"contas": 2, "series": 2, "categorias": 0}),
                         ["2 contas registradas", "2 séries recorrentes", "0 categorias"])

    def test_senha_oculta_e_continuar_so_com_senha(self):
        pagina, _ = self.abrir_ajustes()
        dialogo = self.ir_para_senha(pagina)
        campo, continuar = self.campo_senha(dialogo), self.botao(dialogo, "Continuar")
        self.assertEqual(campo.label, "Senha atual")
        self.assertTrue(campo.password)
        self.assertTrue(campo.can_reveal_password)
        self.assertTrue(continuar.disabled)
        campo.value = "x"
        campo.on_change(Evento(pagina, campo))
        self.assertFalse(continuar.disabled)

    def test_confirmacao_final_com_botao_destrutivo(self):
        pagina, _ = self.abrir_ajustes()
        dialogo = self.ir_para_confirmacao(pagina)
        self.assertEqual(dialogo.title.value, "Excluir conta definitivamente?")
        excluir = self.botao(dialogo, "Excluir conta")
        self.assertEqual(excluir.bgcolor, ESCURO["acao_destrutiva"])   # Ana usa o tema escuro
        self.assertEqual([b.content for b in percorrer(dialogo) if isinstance(b, (ft.Button, ft.TextButton))],
                         ["Cancelar", "Excluir conta"])
        self.assertIn("Não é possível desfazer.", self.textos(dialogo))

    def test_cancelar_em_qualquer_passo_nao_altera_nada(self):  # CT100
        for passo in ("aviso", "senha", "confirmacao"):
            with self.subTest(passo=passo):
                pagina, sessao = self.abrir_ajustes()
                antes = banco_inteiro(self)
                dialogo = {"aviso": self.ir_para_aviso, "senha": self.ir_para_senha,
                           "confirmacao": self.ir_para_confirmacao}[passo](pagina)
                self.clicar(pagina, self.botao(dialogo, "Cancelar"))
                self.assertIsNone(self.dialogo(pagina))
                self.assertEqual(banco_inteiro(self), antes)
                self.assertEqual(sessao.usuario, {"id": self.ana, "nome": "Ana"})
                self.assertTrue(self.na_tela_ajustes(pagina))

    def test_senha_incorreta_mantem_o_passo_e_nao_expoe_a_senha(self):  # CT101
        pagina, sessao = self.abrir_ajustes()
        antes = banco_inteiro(self)
        dialogo = self.ir_para_senha(pagina)
        terminal = self.informar_senha(pagina, dialogo, "senha-errada-42")
        self.assertIs(self.dialogo(pagina), dialogo)
        self.assertEqual(self.erro_visivel(dialogo), "A senha atual está incorreta.")
        self.assertEqual(banco_inteiro(self), antes)
        self.assertEqual(sessao.usuario["id"], self.ana)
        self.assertNotIn("senha-errada-42", terminal)
        self.assertFalse(any("senha-errada-42" in t for t in self.textos(dialogo)))

    def test_campo_de_senha_esvaziado_ao_avancar(self):
        pagina, _ = self.abrir_ajustes()
        dialogo_senha = self.ir_para_senha(pagina)
        self.informar_senha(pagina, dialogo_senha, SENHA_ANA)
        self.assertEqual(self.campo_senha(dialogo_senha).value, "")
        self.assertEqual(self.dialogo(pagina).data, "exclusao_confirmacao")


class TestConclusao(TesteDeExclusaoNaInterface):
    def test_exclui_encerra_a_sessao_e_volta_ao_login(self):  # CT102
        pagina, sessao = self.abrir_ajustes()       # Ana usa o tema escuro
        bia_antes = registros_do_usuario(self, self.bia)
        dialogo = self.ir_para_confirmacao(pagina)
        with mock.patch.object(sessao, "encerrar", wraps=sessao.encerrar) as encerrar:
            terminal = self.confirmar(pagina, dialogo)
        encerrar.assert_called_once_with(("Sua conta foi excluída.", False))
        self.assertEqual(terminal, "")
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM usuarios WHERE id = ?", (self.ana,)), [(0,)])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas WHERE usuario_id = ?", (self.ana,)), [(0,)])
        self.assertEqual(registros_do_usuario(self, self.bia), bia_antes)
        self.assertEqual(sessao.usuario, {"id": None, "nome": None})
        self.assertIsNone(self.dialogo(pagina))
        self.assert_na_tela_de_login_em_claro(pagina, sessao)
        mensagem = self.texto(pagina, "Sua conta foi excluída.")
        self.assertTrue(mensagem.visible)
        self.assertEqual(mensagem.color, CLARO["texto_sucesso"])

        self.entrar(pagina, "ana@sino.com", SENHA_ANA)  # o login antigo não funciona mais
        self.assertEqual(sessao.usuario["id"], None)
        self.entrar(pagina, "bia@sino.com", SENHA_BIA)  # os outros usuários seguem entrando
        self.assertEqual(sessao.usuario["id"], self.bia)

    def test_senha_trocada_durante_a_operacao(self):
        pagina, sessao = self.abrir_ajustes()
        dialogo = self.ir_para_confirmacao(pagina)
        self.assertTrue(db.alterar_senha(self.ana, SENHA_ANA, "trocada-123"))
        antes = banco_inteiro(self)
        self.confirmar(pagina, dialogo)
        self.assertEqual(self.erro_visivel(dialogo), "A senha da conta mudou durante a operação. Comece de novo.")
        self.assertIs(self.dialogo(pagina), dialogo)
        self.assertEqual(banco_inteiro(self), antes)
        self.assertEqual(sessao.usuario["id"], self.ana)

    def test_falha_inesperada_nao_apaga_nada_e_so_o_tipo_vai_ao_terminal(self):
        pagina, sessao = self.abrir_ajustes()
        dialogo = self.ir_para_confirmacao(pagina)
        antes = banco_inteiro(self)
        with mock.patch.object(main.database, "excluir_usuario",
                               side_effect=sqlite3.OperationalError("database is locked ana@sino.com")):
            terminal = self.confirmar(pagina, dialogo)
        self.assertEqual(self.erro_visivel(dialogo),
                         "Não foi possível excluir a conta. Nada foi apagado. Tente novamente.")
        self.assertEqual(terminal.strip(), "Sino: falha ao excluir a conta (OperationalError).")
        self.assertEqual(banco_inteiro(self), antes)
        self.assertEqual(sessao.usuario["id"], self.ana)


class TestLegibilidade(TesteDeExclusaoNaInterface):
    """Item e diálogos da exclusão nos dois temas (RNF09, parcial)."""

    def verificar(self, textos, fundo):
        for texto in textos:
            with self.subTest(texto=texto.value):
                self.assertGreaterEqual(contraste(texto.color, fundo), MINIMO_TEXTO)

    def test_item_e_dialogos_nos_dois_temas(self):
        for email, senha, paleta in (("bia@sino.com", SENHA_BIA, CLARO), ("ana@sino.com", SENHA_ANA, ESCURO)):
            with self.subTest(tema="claro" if paleta is CLARO else "escuro"):
                pagina, _ = self.abrir_ajustes(email, senha)
                rotulo = next(t for t in percorrer(self.item(pagina))
                              if isinstance(t, ft.Text) and t.value == "Excluir conta")
                self.verificar([rotulo], paleta["fundo_card"])
                aviso = self.ir_para_aviso(pagina)
                self.clicar(pagina, self.botao(aviso, "Cancelar"))
                confirmacao = self.ir_para_confirmacao(pagina, senha)
                for dialogo in (aviso, confirmacao):
                    self.assertEqual(dialogo.bgcolor, paleta["fundo_dialogo"])
                    self.verificar([t for t in percorrer(dialogo) if isinstance(t, ft.Text) and t.value],
                                   paleta["fundo_dialogo"])
                    self.assertEqual(self.botao(dialogo, "Cancelar").style.color, paleta["texto_principal"])
                excluir = self.botao(confirmacao, "Excluir conta")
                self.assertEqual(excluir.bgcolor, paleta["acao_destrutiva"])


class TestSessaoAntigaDepoisDaExclusao(BaseAlteracao, unittest.IsolatedAsyncioTestCase):
    """
    Uma gravação assíncrona da sessão antiga (alteração de e-mail) que termina
    depois da exclusão falha porque a conta não existe mais, e não mexe na
    tela de login nem na sessão. Pela interface os dois fluxos não se
    sobrepõem (o diálogo de e-mail é modal e não cancela durante a gravação);
    aqui a exclusão é feita pelas mesmas rotinas que o botão chama.
    """

    async def test_gravacao_pendente_nao_atualiza_a_interface_depois_da_exclusao(self):
        pagina, sessao = self.abrir_ajustes()
        dialogo_email = self.editar(pagina)
        self.campo(pagina, "Senha atual").value = SENHA_BIA
        self.campo(pagina, "Novo e-mail").value = NOVO
        self.acionar(pagina, self.botao(pagina, "Enviar código"))
        await pagina.concluir_tarefas()

        comecou, liberar = threading.Event(), threading.Event()
        original = db.alterar_email_verificado
        resultados = []

        def alterar_devagar(*args):
            comecou.set()
            liberar.wait(5)
            try:
                return original(*args)
            except Exception as ex:
                resultados.append(type(ex))
                raise

        with mock.patch.object(main.database, "alterar_email_verificado", alterar_devagar):
            self.campo(pagina, "Código").value = self.servidor.ultimo_codigo(NOVO)
            self.acionar(pagina, self.botao(pagina, "Confirmar"))
            await asyncio.to_thread(comecou.wait, 5)
            db.excluir_usuario(db.conferir_senha_para_exclusao(self.bia, SENHA_BIA))
            sessao.encerrar(("Sua conta foi excluída.", False))
            liberar.set()
            await pagina.concluir_tarefas()

        self.assertEqual(resultados, [db.ContaNaoEncontradaError])     # a gravação antiga falhou
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM usuarios WHERE id = ?", (self.bia,)), [(0,)])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM autorizacoes_usadas"), [(0,)])
        self.assertEqual(sessao.usuario, {"id": None, "nome": None})
        self.assertFalse([d for d in pagina.dialogos if d.open])
        visiveis = self.textos_visiveis(pagina)
        self.assertIn("Sua conta foi excluída.", visiveis)              # o login segue intacto
        self.assertIn("Bem-vindo de volta", visiveis)
        self.assertNotIn(str(db.ContaNaoEncontradaError()), visiveis)
        self.assertNotIn("E-mail alterado com sucesso.", visiveis)
        # Nem o diálogo antigo (já fechado) recebe a mensagem da falha.
        self.assertNotIn(str(db.ContaNaoEncontradaError()),
                         [t.value for t in percorrer(dialogo_email) if isinstance(t, ft.Text)])


if __name__ == "__main__":
    unittest.main()
