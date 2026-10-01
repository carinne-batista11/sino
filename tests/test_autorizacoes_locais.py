"""
Operações locais confirmadas por código (ERS v6.0, Etapa 8): cadastro,
alteração de e-mail e redefinição de senha consumindo a autorização
verificada pelo cliente do serviço de códigos.

Bancos temporários (apoio_banco). A autorização é simulada por um objeto com
os mesmos atributos da `AutorizacaoVerificada` do cliente; o relógio
monotônico é injetado. Cobre uso único do jti, vínculo com a operação,
validade antes e depois do bloqueio e antes da gravação, concorrência,
falhas depois de gravar o jti e a limpeza pelo iat assinado.
"""

import base64
import hashlib
import threading
import unittest
from dataclasses import dataclass, replace
from unittest import mock

from apoio_banco import TesteComBancoTemporario, _conectar_original, db

INICIO = 1_000.0          # relógio monotônico dos testes
IAT = 1_790_000_000       # iat UTC assinado (s)
EXP = IAT + 600


@dataclass(frozen=True)
class Autorizacao:
    """Mesmos atributos da AutorizacaoVerificada do cliente."""
    jti: str
    finalidade: str
    exp_utc_s: int
    iat_utc_s: int
    email_normalizado: str
    prazo_monotonico: float

    def vigente(self, agora_monotonico):
        return agora_monotonico < self.prazo_monotonico


_contador = [0]


def novo_jti():
    _contador[0] += 1
    return base64.urlsafe_b64encode(hashlib.sha256(str(_contador[0]).encode()).digest()[:16]).rstrip(b"=").decode()


def autorizacao(finalidade, email, jti=None, iat=IAT, exp=EXP, prazo=INICIO + 500):
    return Autorizacao(jti or novo_jti(), finalidade, exp, iat, email.strip().lower(), prazo)


class Relogio:
    """Valores em sequência (o último se repete) ou um valor alterável."""

    def __init__(self, *valores):
        self.valores = list(valores) or [INICIO]
        self.chamadas = 0

    def __call__(self):
        self.chamadas += 1
        return self.valores.pop(0) if len(self.valores) > 1 else self.valores[0]


class BaseAutorizacoes(TesteComBancoTemporario):
    def autorizacoes(self):
        return self.consultar("SELECT jti, finalidade, expira_em FROM autorizacoes_usadas ORDER BY jti")

    def usuario(self, email):
        linhas = self.consultar(
            "SELECT id, nome, email, email_verificado, termos_aceitos_em FROM usuarios WHERE lower(email) = lower(?)",
            (email,),
        )
        return linhas[0] if linhas else None

    def cadastrar(self, email="pessoa@sino.com", senha="senhaforte1", nome="Pessoa"):
        aut = autorizacao("cadastro", email)
        return db.concluir_cadastro(aut, nome, email, db.hash_de_nova_senha(senha), relogio=Relogio())

    def assert_nada_gravado(self, usuarios_antes, autorizacoes_antes):
        self.assertEqual(self.consultar("SELECT * FROM usuarios ORDER BY id"), usuarios_antes)
        self.assertEqual(self.autorizacoes(), autorizacoes_antes)

    def estado(self):
        return self.consultar("SELECT * FROM usuarios ORDER BY id"), self.autorizacoes()


class TesteCadastro(BaseAutorizacoes):
    def test_cadastro_confirmado_cria_usuario_verificado_com_categorias(self):
        aut = autorizacao("cadastro", "Pessoa@Sino.com")
        usuario_id = db.concluir_cadastro(aut, " Pessoa ", " Pessoa@Sino.com ", db.hash_de_nova_senha("senhaforte1"),
                                          relogio=Relogio())
        self.assertEqual(self.usuario("pessoa@sino.com"),
                         (usuario_id, "Pessoa", "Pessoa@Sino.com", 1, self.HOJE.isoformat()))
        self.assertEqual(len(db.listar_categorias(usuario_id)), len(db.CATEGORIAS_PRE_CRIADAS))
        self.assertEqual(self.autorizacoes(), [(aut.jti, "cadastro", EXP)])
        self.assertEqual(db.verificar_login("pessoa@sino.com", "senhaforte1")["id"], usuario_id)

    def test_senha_validada_e_contrato_interno(self):
        with self.assertRaises(db.SenhaInvalidaError):
            db.hash_de_nova_senha("curta")
        with self.assertRaises(db.SenhaInvalidaError):
            db.hash_de_nova_senha("tem espaço")
        validada = db.hash_de_nova_senha("senhaforte1")
        self.assertEqual(repr(validada), "SenhaValidada(<oculta>)")
        self.assertNotIn("pbkdf2", repr(validada))
        antes = self.estado()
        aut = autorizacao("cadastro", "x@sino.com")
        for senha in (validada._senha_hash, "senhaforte1", None):
            with self.subTest(senha=type(senha).__name__):
                with self.assertRaises(TypeError):
                    db.concluir_cadastro(aut, "X", "x@sino.com", senha, relogio=Relogio())
        self.assert_nada_gravado(*antes)

    def test_email_em_uso_nao_consome_a_autorizacao(self):
        self.criar_usuario(email="Pessoa@Sino.com")
        antes = self.estado()
        aut = autorizacao("cadastro", "pessoa@sino.COM")
        with self.assertRaises(db.EmailEmUsoError):
            db.concluir_cadastro(aut, "Outra", "pessoa@sino.COM", db.hash_de_nova_senha("senhaforte1"),
                                 relogio=Relogio())
        self.assert_nada_gravado(*antes)

    def test_nome_invalido(self):
        aut = autorizacao("cadastro", "x@sino.com")
        with self.assertRaises(ValueError):
            db.concluir_cadastro(aut, "  ", "x@sino.com", db.hash_de_nova_senha("senhaforte1"), relogio=Relogio())
        with self.assertRaises(db.LimiteDeCaracteresError):
            db.concluir_cadastro(aut, "n" * 71, "x@sino.com", db.hash_de_nova_senha("senhaforte1"), relogio=Relogio())
        self.assertEqual(self.autorizacoes(), [])

    def test_falha_depois_de_gravar_o_jti_desfaz_tudo(self):
        aut = autorizacao("cadastro", "falha@sino.com")
        senha = db.hash_de_nova_senha("senhaforte1")
        antes = self.estado()
        with mock.patch.object(db, "_inserir_categorias_padrao", side_effect=RuntimeError("falha simulada")):
            with self.assertRaisesRegex(RuntimeError, "falha simulada"):
                db.concluir_cadastro(aut, "Falha", "falha@sino.com", senha, relogio=Relogio())
        self.assert_nada_gravado(*antes)
        # A mesma autorização continua sem uso e conclui depois.
        usuario_id = db.concluir_cadastro(aut, "Falha", "falha@sino.com", senha, relogio=Relogio())
        self.assertEqual(self.usuario("falha@sino.com")[0], usuario_id)


class TesteVinculoEUsoUnico(BaseAutorizacoes):
    def test_autorizacao_de_outra_operacao_e_recusada(self):
        senha = db.hash_de_nova_senha("senhaforte1")
        base = autorizacao("cadastro", "a@sino.com")
        casos = {
            "finalidade": replace(base, finalidade="recuperacao_senha"),
            "outro_email": replace(base, email_normalizado="b@sino.com"),
            "jti_nao_canonico": replace(base, jti=base.jti[:21] + "B"),
            "jti_curto": replace(base, jti="abc"),
            "exp_booleano": replace(base, exp_utc_s=True),
            "iat_depois_do_exp": replace(base, iat_utc_s=EXP + 1),
        }
        antes = self.estado()
        for nome, aut in casos.items():
            with self.subTest(caso=nome):
                with self.assertRaises(db.AutorizacaoRecusadaError):
                    db.concluir_cadastro(aut, "A", "a@sino.com", senha, relogio=Relogio())
        with self.assertRaises(db.AutorizacaoRecusadaError):
            db.concluir_cadastro(object(), "A", "a@sino.com", senha, relogio=Relogio())
        self.assert_nada_gravado(*antes)

    def test_jti_so_pode_ser_usado_uma_vez_inclusive_entre_operacoes(self):
        self.cadastrar("um@sino.com")
        aut = autorizacao("recuperacao_senha", "um@sino.com")
        db.redefinir_senha_por_autorizacao(aut, "um@sino.com", "novasenha2", relogio=Relogio())
        with self.assertRaises(db.AutorizacaoJaUsadaError):
            db.redefinir_senha_por_autorizacao(aut, "um@sino.com", "outrasenha3", relogio=Relogio())
        self.assertIsNotNone(db.verificar_login("um@sino.com", "novasenha2"))
        # O mesmo jti numa autorização de outra finalidade também é recusado.
        mesma = autorizacao("cadastro", "dois@sino.com", jti=aut.jti)
        with self.assertRaises(db.AutorizacaoJaUsadaError):
            db.concluir_cadastro(mesma, "Dois", "dois@sino.com", db.hash_de_nova_senha("senhaforte1"),
                                 relogio=Relogio())
        self.assertIsNone(self.usuario("dois@sino.com"))


class TesteValidade(BaseAutorizacoes):
    def setUp(self):
        super().setUp()
        self.aut = autorizacao("cadastro", "v@sino.com", prazo=INICIO + 10)
        self.senha = db.hash_de_nova_senha("senhaforte1")

    def concluir(self, relogio):
        return db.concluir_cadastro(self.aut, "V", "v@sino.com", self.senha, relogio=relogio)

    def test_expirada_antes_do_bloqueio(self):
        antes = self.estado()
        with self.assertRaises(db.AutorizacaoExpiradaError):
            self.concluir(Relogio(INICIO + 10))
        self.assert_nada_gravado(*antes)

    def test_expirada_depois_de_obter_o_bloqueio(self):
        antes = self.estado()
        # Vencida só na 2ª consulta (logo após o BEGIN IMMEDIATE); a 3ª voltaria
        # a parecer válida: só a conferência após o bloqueio pode recusar.
        relogio = Relogio(INICIO, INICIO + 11, INICIO)
        with self.assertRaises(db.AutorizacaoExpiradaError):
            self.concluir(relogio)
        self.assertEqual(relogio.chamadas, 2)
        self.assert_nada_gravado(*antes)

    def test_expirada_durante_o_preparo_antes_da_gravacao(self):
        antes = self.estado()
        relogio = Relogio(INICIO, INICIO + 1, INICIO + 11)
        with self.assertRaises(db.AutorizacaoExpiradaError):
            self.concluir(relogio)
        self.assertEqual(relogio.chamadas, 3)
        self.assert_nada_gravado(*antes)

    def test_expirada_enquanto_espera_o_bloqueio_de_outra_conexao(self):
        antes = self.estado()
        agora = [INICIO]
        consultas = []
        consultou = threading.Event()

        def relogio():
            consultas.append(agora[0])
            consultou.set()
            return agora[0]

        bloqueio = _conectar_original(self.caminho_banco, check_same_thread=False)
        bloqueio.isolation_level = None
        bloqueio.execute("BEGIN IMMEDIATE;")

        def segurar_e_liberar():
            consultou.wait(5)          # a checagem prévia já passou
            agora[0] = INICIO + 11     # o prazo vence enquanto o bloqueio está ocupado
            bloqueio.execute("ROLLBACK;")

        auxiliar = threading.Thread(target=segurar_e_liberar)
        auxiliar.start()
        try:
            with self.assertRaises(db.AutorizacaoExpiradaError):
                self.concluir(relogio)
        finally:
            auxiliar.join(5)
            bloqueio.close()
        self.assertEqual(consultas, [INICIO, INICIO + 11])  # recusada logo após obter o bloqueio
        self.assert_nada_gravado(*antes)

    def test_banco_ocupado_nao_grava_nem_consome(self):
        antes = self.estado()
        bloqueio = _conectar_original(self.caminho_banco)
        bloqueio.isolation_level = None
        bloqueio.execute("BEGIN IMMEDIATE;")
        try:
            def conectar_sem_espera():
                conexao = _conectar_original(self.caminho_banco, timeout=0)
                conexao.execute("PRAGMA foreign_keys = ON;")
                return conexao

            with mock.patch.object(db, "conectar", conectar_sem_espera):
                with self.assertRaises(db.sqlite3.OperationalError):
                    self.concluir(Relogio())
        finally:
            bloqueio.execute("ROLLBACK;")
            bloqueio.close()
        self.assert_nada_gravado(*antes)
        self.assertIsInstance(self.concluir(Relogio()), int)


class TesteConcorrencia(BaseAutorizacoes):
    def correr(self, funcoes):
        barreira = threading.Barrier(len(funcoes))
        resultados = [None] * len(funcoes)

        def executar(i, funcao):
            barreira.wait(5)
            try:
                resultados[i] = funcao()
            except Exception as erro:  # noqa: BLE001 -- registrado para a asserção
                resultados[i] = erro

        threads = [threading.Thread(target=executar, args=(i, f)) for i, f in enumerate(funcoes)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(30)
        return resultados

    def test_mesmo_jti_em_paralelo_e_consumido_uma_unica_vez(self):
        self.cadastrar("c@sino.com")
        aut = autorizacao("recuperacao_senha", "c@sino.com")
        resultados = self.correr([
            lambda: db.redefinir_senha_por_autorizacao(aut, "c@sino.com", "paralela11", relogio=Relogio()),
            lambda: db.redefinir_senha_por_autorizacao(aut, "c@sino.com", "paralela22", relogio=Relogio()),
        ])
        sucessos = [r for r in resultados if isinstance(r, int)]
        erros = [r for r in resultados if isinstance(r, Exception)]
        self.assertEqual(len(sucessos), 1)
        self.assertEqual([type(e) for e in erros], [db.AutorizacaoJaUsadaError])
        self.assertEqual(len(self.autorizacoes()), 2)  # o do cadastro e o da recuperação

    def test_mesmo_email_em_dois_cadastros_paralelos(self):
        resultados = self.correr([
            lambda: db.concluir_cadastro(autorizacao("cadastro", "p@sino.com"), "P1", "p@sino.com",
                                         db.hash_de_nova_senha("senhaforte1"), relogio=Relogio()),
            lambda: db.concluir_cadastro(autorizacao("cadastro", "P@sino.com"), "P2", "P@sino.com",
                                         db.hash_de_nova_senha("senhaforte2"), relogio=Relogio()),
        ])
        self.assertEqual(sum(isinstance(r, int) for r in resultados), 1)
        self.assertEqual([type(r) for r in resultados if isinstance(r, Exception)], [db.EmailEmUsoError])
        self.assertEqual(len(self.autorizacoes()), 1)


class TesteAlteracaoEmail(BaseAutorizacoes):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario(email="Atual@Sino.com", senha="senha123")  # conta de teste antiga

    def pendencia(self, senha="senha123"):
        return db.conferir_senha_atual(self.usuario_id, senha)

    def alterar(self, pendencia, novo, relogio=None, **kwargs):
        aut = kwargs.pop("aut", None) or autorizacao("alteracao_email", novo)
        return db.alterar_email_verificado(aut, pendencia, novo, relogio=relogio or Relogio())

    def test_alteracao_confirmada(self):
        pendencia = self.pendencia()
        self.assertEqual(repr(pendencia), f"PendenciaAlteracaoEmail(usuario_id={self.usuario_id})")
        # Até concluir, o e-mail atual continua entrando (CT112).
        self.assertIsNotNone(db.verificar_login("atual@sino.com", "senha123"))
        self.assertEqual(self.alterar(pendencia, " Novo@Sino.com "), "Novo@Sino.com")
        self.assertEqual(self.usuario("novo@sino.com")[2:4], ("Novo@Sino.com", 1))
        self.assertIsNone(db.verificar_login("atual@sino.com", "senha123"))
        self.assertIsNotNone(db.verificar_login("novo@sino.com", "senha123"))

    def test_senha_atual_antiga_continua_aceita(self):
        legado = hashlib.sha256("a b".encode()).hexdigest()  # formato antigo, curta e com espaço
        self.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (legado, self.usuario_id))
        self.assertEqual(self.alterar(self.pendencia("a b"), "novo@sino.com"), "novo@sino.com")
        with self.assertRaises(db.SenhaAtualIncorretaError):
            db.conferir_senha_atual(self.usuario_id, "errada")
        with self.assertRaises(db.ContaNaoEncontradaError):
            db.conferir_senha_atual(9999, "senha123")

    def test_recusas_nao_consomem_a_autorizacao(self):
        self.criar_usuario(email="outra@sino.com")
        casos = {
            "mesmo_email": ("ATUAL@sino.com", db.MesmoEmailError, None),
            "email_de_outra_conta": ("Outra@SINO.com", db.EmailEmUsoError, None),
            "email_mudou_so_na_caixa": ("novo@sino.com", db.EmailAlteradoDuranteOperacaoError,
                                        "UPDATE usuarios SET email = 'ATUAL@sino.com' WHERE id = ?"),
            "senha_mudou": ("novo@sino.com", db.SenhaAlteradaDuranteOperacaoError, "senha"),
            "usuario_removido": ("novo@sino.com", db.ContaNaoEncontradaError,
                                 "DELETE FROM usuarios WHERE id = ?"),
        }
        for nome, (novo, erro, acao) in casos.items():
            with self.subTest(caso=nome):
                self.executar("UPDATE usuarios SET email = 'Atual@Sino.com', senha_hash = ? WHERE id = ?",
                              (db._gerar_hash_senha("senha123"), self.usuario_id))
                pendencia = self.pendencia()
                if acao == "senha":
                    db.alterar_senha(self.usuario_id, "senha123", "outrasenha9")
                elif acao and acao.startswith("DELETE"):
                    pendencia = db.PendenciaAlteracaoEmail(9999, "x@sino.com", "0" * 64)
                elif acao:
                    self.executar(acao, (self.usuario_id,))
                antes = self.estado()
                with self.assertRaises(erro):
                    self.alterar(pendencia, novo)
                self.assert_nada_gravado(*antes)

    def test_pendencia_e_autorizacao_vinculadas(self):
        with self.assertRaises(TypeError):
            db.alterar_email_verificado(autorizacao("alteracao_email", "n@sino.com"),
                                        (self.usuario_id, "Atual@Sino.com", "x"), "n@sino.com", relogio=Relogio())
        with self.assertRaises(db.AutorizacaoRecusadaError):
            self.alterar(self.pendencia(), "n@sino.com", aut=autorizacao("alteracao_email", "outro@sino.com"))
        self.assertEqual(self.autorizacoes(), [])


class TesteRecuperacao(BaseAutorizacoes):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.cadastrar("rec@sino.com", senha="senhaforte1")

    def redefinir(self, nova, aut=None, email="REC@sino.com"):
        return db.redefinir_senha_por_autorizacao(
            aut or autorizacao("recuperacao_senha", email), email, nova, relogio=Relogio())

    def test_recuperacao_confirmada(self):
        self.assertEqual(self.redefinir("novasenha2"), self.usuario_id)
        self.assertIsNone(db.verificar_login("rec@sino.com", "senhaforte1"))
        self.assertIsNotNone(db.verificar_login("rec@sino.com", "novasenha2"))

    def test_recusas_nao_consomem_e_a_mesma_autorizacao_conclui_depois(self):
        aut = autorizacao("recuperacao_senha", "rec@sino.com")
        antes = self.estado()
        for nova, erro in (("curta", db.SenhaCurtaError), ("com espaco s", db.SenhaComEspacosError),
                           ("senhaforte1", db.SenhaIgualAtualError)):
            with self.subTest(nova=nova):
                with self.assertRaises(erro):
                    self.redefinir(nova, aut=aut)
                self.assert_nada_gravado(*antes)
        self.assertEqual(self.redefinir("novasenha2", aut=aut), self.usuario_id)

    def test_igual_a_senha_atual_em_formato_antigo(self):
        legado = hashlib.sha256("senhaantiga1".encode()).hexdigest()
        self.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (legado, self.usuario_id))
        with self.assertRaises(db.SenhaIgualAtualError):
            self.redefinir("senhaantiga1")
        self.assertEqual(self.autorizacoes()[0][1], "cadastro")

    def test_conta_nao_verificada_ou_inexistente_e_recusada(self):
        self.criar_usuario(email="teste@sino.com")  # conta antiga de teste: não verificada
        antes = self.estado()
        for email in ("teste@sino.com", "ninguem@sino.com"):
            with self.subTest(email=email):
                with self.assertRaises(db.ContaNaoEncontradaError):
                    self.redefinir("novasenha2", email=email)
        self.assert_nada_gravado(*antes)


class TesteLimpeza(BaseAutorizacoes):
    def inserir(self, jti, expira):
        self.executar("INSERT INTO autorizacoes_usadas VALUES (?, 'cadastro', ?)", (jti, expira))

    def test_apaga_so_o_que_expirou_antes_do_iat_assinado(self):
        vencido, no_limite, vivo = novo_jti(), novo_jti(), novo_jti()
        self.inserir(vencido, IAT - 1)
        self.inserir(no_limite, IAT)
        self.inserir(vivo, IAT + 300)
        aut = autorizacao("cadastro", "l@sino.com")
        db.concluir_cadastro(aut, "L", "l@sino.com", db.hash_de_nova_senha("senhaforte1"), relogio=Relogio())
        restantes = {linha[0] for linha in self.autorizacoes()}
        self.assertEqual(restantes, {no_limite, vivo, aut.jti})

    def test_sem_autorizacao_consumida_nada_e_apagado(self):
        vencido = novo_jti()
        self.inserir(vencido, 1)
        self.criar_usuario(email="existe@sino.com")
        aut = autorizacao("cadastro", "existe@sino.com")
        with self.assertRaises(db.EmailEmUsoError):
            db.concluir_cadastro(aut, "E", "existe@sino.com", db.hash_de_nova_senha("senhaforte1"),
                                 relogio=Relogio())
        self.assertEqual([linha[0] for linha in self.autorizacoes()], [vencido])

    def test_relogio_local_nao_influi(self):
        vivo = novo_jti()
        self.inserir(vivo, IAT + 1)
        with mock.patch("time.time", return_value=10 ** 12):  # relógio local muito adiantado
            db.concluir_cadastro(autorizacao("cadastro", "r@sino.com"), "R", "r@sino.com",
                                 db.hash_de_nova_senha("senhaforte1"), relogio=Relogio())
        self.assertIn(vivo, {linha[0] for linha in self.autorizacoes()})


class TesteConsultas(BaseAutorizacoes):
    def test_email_em_uso_e_conta_verificada(self):
        antigo = self.criar_usuario(email="Antigo@Sino.com")
        self.cadastrar("verificado@sino.com")
        self.assertTrue(db.email_em_uso("antigo@SINO.com"))
        self.assertFalse(db.email_em_uso("antigo@sino.com", exceto_usuario_id=antigo))
        self.assertFalse(db.email_em_uso("livre@sino.com"))
        self.assertFalse(db.existe_conta_verificada("antigo@sino.com"))  # contas de teste: P2
        self.assertTrue(db.existe_conta_verificada(" VERIFICADO@sino.com "))
        self.assertFalse(db.existe_conta_verificada("livre@sino.com"))

    def test_contas_antigas_continuam_entrando(self):
        self.criar_usuario(email="velha@sino.com", senha="senha123")
        self.assertIsNotNone(db.verificar_login("velha@sino.com", "senha123"))
        self.assertEqual(self.usuario("velha@sino.com")[3], 0)


if __name__ == "__main__":
    unittest.main()
