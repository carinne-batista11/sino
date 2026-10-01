"""
ERS v6.0, Etapa 7 (passo 1) — senha mínima e alteração de senha no banco
(5.33, 5.34, RF37, RF38; CT81-CT86): validar_nova_senha, a validação em
criar_usuario e alterar_senha. O login de senhas anteriores à v6.0 continua
funcionando nos dois formatos de hash (CT82). Bancos temporários; o banco
real nunca é tocado.
"""

import hashlib
import sqlite3
import unittest
from unittest import mock

from apoio_banco import TesteComBancoTemporario, db

EMOJI_COMPOSTO = "👩‍💻"  # 3 pontos de código, 1 caractere percebido
SENHA_ANA = "senha-da-ana"
SENHA_BIA = "senha-da-bia"

# Novas senhas com espaço em branco em qualquer posição (5.33, Etapa 7).
SENHAS_COM_ESPACOS = (
    " senha-boa",            # borda inicial
    "senha-boa ",            # borda final
    "senha boa1",            # interno
    "senha\tboa1",           # tabulação
    "senha\nboa1",           # quebra de linha
    "senha\r\nboa1",         # quebra de linha (Windows)
    "senha\u00a0boa1",       # espaço não separável
    "senha\u2003boa1",       # espaço largo (em space)
    " " * 8,                 # só espaços
)


class TestValidarNovaSenha(unittest.TestCase):
    def test_minimo_por_caracteres_percebidos(self):
        self.assertEqual(db.SENHA_MINIMO, 8)
        self.assertEqual(db.validar_nova_senha("a" * 8), "a" * 8)
        with self.assertRaises(db.SenhaCurtaError):
            db.validar_nova_senha("a" * 7)

    def test_emoji_composto_conta_um(self):
        oito = "abcdefg" + EMOJI_COMPOSTO      # 8 percebidos, 10 pontos de código
        sete = "abcdef" + EMOJI_COMPOSTO       # 7 percebidos, 9 pontos de código
        self.assertGreater(len(sete), 8)
        self.assertEqual(db.validar_nova_senha(oito), oito)
        with self.assertRaises(db.SenhaCurtaError):
            db.validar_nova_senha(sete)

    def test_qualquer_espaco_recusado(self):
        for senha in SENHAS_COM_ESPACOS + (" " * 30, "\t" * 8, " ", "  a"):
            with self.subTest(senha=repr(senha)):
                with self.assertRaises(db.SenhaComEspacosError):
                    db.validar_nova_senha(senha)

    def test_senha_valida_volta_intacta(self):
        senha = "Senhá-Ç#1" + EMOJI_COMPOSTO   # nada é transformado nem normalizado
        self.assertIs(db.validar_nova_senha(senha), senha)

    def test_vazia_e_curta(self):
        with self.assertRaises(db.SenhaCurtaError):
            db.validar_nova_senha("")

    def test_entrada_nao_textual(self):
        for senha in (None, 12345678, b"senha-bytes", ["s", "e", "n", "h", "a", "1", "2", "3"]):
            with self.subTest(senha=repr(senha)):
                with self.assertRaises(db.SenhaInvalidaError):
                    db.validar_nova_senha(senha)

    def test_mensagens_amigaveis_e_hierarquia(self):
        self.assertEqual(str(db.SenhaCurtaError()), "A senha deve ter pelo menos 8 caracteres.")
        self.assertEqual(str(db.SenhaComEspacosError()), "A senha não pode conter espaços.")
        self.assertEqual(str(db.SenhaAtualIncorretaError()), "A senha atual está incorreta.")
        self.assertEqual(str(db.SenhaIgualAtualError()), "A nova senha deve ser diferente da atual.")
        for classe in (db.SenhaCurtaError, db.SenhaComEspacosError, db.SenhaIgualAtualError):
            self.assertTrue(issubclass(classe, db.SenhaInvalidaError))
        self.assertTrue(issubclass(db.SenhaInvalidaError, ValueError))
        self.assertTrue(issubclass(db.SenhaAtualIncorretaError, ValueError))


class TestCadastroComSenhaMinima(TesteComBancoTemporario):
    def total_usuarios(self):
        return self.consultar("SELECT COUNT(*) FROM usuarios")[0][0]

    def test_ct81_sete_recusada_oito_aceita(self):
        sucesso, mensagem = db.criar_usuario("Ana", "ana@sino.com", "a" * 7, aceite_termos=True)
        self.assertEqual((sucesso, mensagem), (False, "A senha deve ter pelo menos 8 caracteres."))
        self.assertEqual(self.total_usuarios(), 0)
        self.assertEqual(db.criar_usuario("Ana", "ana@sino.com", "a" * 8, aceite_termos=True)[0], True)
        self.assertIsNotNone(db.verificar_login("ana@sino.com", "a" * 8))

    def test_emoji_composto_no_cadastro(self):
        self.assertFalse(db.criar_usuario("Ana", "a@sino.com", "abcdef" + EMOJI_COMPOSTO, aceite_termos=True)[0])
        self.assertTrue(db.criar_usuario("Ana", "a@sino.com", "abcdefg" + EMOJI_COMPOSTO, aceite_termos=True)[0])
        self.assertIsNotNone(db.verificar_login("a@sino.com", "abcdefg" + EMOJI_COMPOSTO))

    def test_senha_com_espacos_recusada_sem_gravar(self):
        for senha in SENHAS_COM_ESPACOS:
            with self.subTest(senha=repr(senha)):
                sucesso, mensagem = db.criar_usuario("Ana", "ana@sino.com", senha, aceite_termos=True)
                self.assertEqual((sucesso, mensagem), (False, "A senha não pode conter espaços."))
        self.assertEqual(self.total_usuarios(), 0)

    def test_senha_gravada_exatamente_como_digitada(self):
        senha = "Senhá-Ç#1"
        self.assertTrue(db.criar_usuario("Ana", "ana@sino.com", senha, aceite_termos=True)[0])
        self.assertIsNotNone(db.verificar_login("ana@sino.com", senha))
        self.assertIsNone(db.verificar_login("ana@sino.com", senha.lower()))

    def test_somente_espacos_e_nao_textual_recusadas_sem_gravar(self):
        for senha in (" " * 10, None, 12345678):
            with self.subTest(senha=repr(senha)):
                sucesso, mensagem = db.criar_usuario("Ana", "ana@sino.com", senha, aceite_termos=True)
                self.assertFalse(sucesso)
                self.assertTrue(mensagem)
        self.assertEqual(self.total_usuarios(), 0)

    def test_aceite_continua_sendo_a_primeira_regra(self):
        sucesso, mensagem = db.criar_usuario("Ana", "ana@sino.com", "curta", aceite_termos=False)
        self.assertFalse(sucesso)
        self.assertEqual(mensagem, "É necessário aceitar os Termos de Uso e a Política de Privacidade.")

    def test_senha_hash_continua_pbkdf2(self):
        self.criar_usuario(email="ana@sino.com", senha=SENHA_ANA)
        senha_hash = self.consultar("SELECT senha_hash FROM usuarios")[0][0]
        self.assertTrue(senha_hash.startswith(f"{db.PBKDF2_ALGORITMO}${db.PBKDF2_ITERACOES}$"))
        self.assertNotIn(SENHA_ANA, senha_hash)


class TestLoginDeSenhasAntigas(TesteComBancoTemporario):
    """CT82: a regra de 5.33 não se aplica ao login de senhas já existentes."""

    def setUp(self):
        super().setUp()
        self.uid = self.criar_usuario(email="antiga@sino.com", senha=SENHA_ANA)

    def definir_hash(self, senha_hash):
        self.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (senha_hash, self.uid))

    def test_senha_curta_em_hash_legado(self):
        self.definir_hash(hashlib.sha256("abc".encode("utf-8")).hexdigest())
        self.assertIsNotNone(db.verificar_login("antiga@sino.com", "abc"))
        self.assertTrue(self.consultar("SELECT senha_hash FROM usuarios")[0][0].startswith("pbkdf2_sha256$"))
        self.assertIsNotNone(db.verificar_login("antiga@sino.com", "abc"))  # depois da conversão

    def test_senha_curta_em_hash_pbkdf2(self):
        self.definir_hash(db._gerar_hash_senha("curta"))
        self.assertIsNotNone(db.verificar_login("antiga@sino.com", "curta"))

    def test_senha_antiga_so_de_espacos(self):
        self.definir_hash(db._gerar_hash_senha("   "))
        self.assertIsNotNone(db.verificar_login("antiga@sino.com", "   "))

    def test_senhas_antigas_com_espacos_nos_dois_formatos(self):
        for senha in ("  bordas  ", "senha antiga", "com\ttab"):
            with self.subTest(senha=repr(senha)):
                self.definir_hash(db._gerar_hash_senha(senha))
                self.assertIsNotNone(db.verificar_login("antiga@sino.com", senha))
                self.assertIsNone(db.verificar_login("antiga@sino.com", "".join(senha.split())))
                self.definir_hash(hashlib.sha256(senha.encode("utf-8")).hexdigest())
                self.assertIsNotNone(db.verificar_login("antiga@sino.com", senha))


class TestAlterarSenha(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.ana = self.criar_usuario(email="ana@sino.com", senha=SENHA_ANA, nome="Ana")
        self.bia = self.criar_usuario(email="bia@sino.com", senha=SENHA_BIA, nome="Bia")

    def linhas(self):
        return self.consultar("SELECT * FROM usuarios ORDER BY id")

    def hash_de(self, usuario_id):
        return self.consultar("SELECT senha_hash FROM usuarios WHERE id = ?", (usuario_id,))[0][0]

    def assert_recusa_sem_alterar(self, erro, senha_atual, nova_senha, usuario_id=None):
        antes = self.linhas()
        with self.assertRaises(erro) as contexto:
            db.alterar_senha(self.ana if usuario_id is None else usuario_id, senha_atual, nova_senha)
        self.assertEqual(self.linhas(), antes)
        for senha in (senha_atual, nova_senha):   # a mensagem nunca expõe uma senha
            if isinstance(senha, str) and senha.strip():
                self.assertNotIn(senha, str(contexto.exception))
                self.assertNotIn(senha, repr(contexto.exception.args))
        return contexto.exception

    # CT86 --------------------------------------------------------------
    def test_alteracao_valida(self):
        self.assertIs(db.alterar_senha(self.ana, SENHA_ANA, "nova-senha-1"), True)
        self.assertIsNotNone(db.verificar_login("ana@sino.com", "nova-senha-1"))
        self.assertIsNone(db.verificar_login("ana@sino.com", SENHA_ANA))
        self.assertTrue(self.hash_de(self.ana).startswith(f"{db.PBKDF2_ALGORITMO}${db.PBKDF2_ITERACOES}$"))

    def test_so_o_hash_do_proprio_usuario_muda(self):
        antes = {linha[0]: linha for linha in self.linhas()}
        db.alterar_senha(self.ana, SENHA_ANA, "nova-senha-1")
        depois = {linha[0]: linha for linha in self.linhas()}
        self.assertEqual(depois[self.bia], antes[self.bia])
        colunas = [c[1] for c in self.consultar("PRAGMA table_info(usuarios)")]
        mudaram = {c for c, a, d in zip(colunas, antes[self.ana], depois[self.ana]) if a != d}
        self.assertEqual(mudaram, {"senha_hash"})
        self.assertIsNotNone(db.verificar_login("bia@sino.com", SENHA_BIA))

    def test_senha_da_outra_usuaria_nao_serve_como_atual(self):
        self.assert_recusa_sem_alterar(db.SenhaAtualIncorretaError, SENHA_BIA, "nova-senha-1")

    def test_nova_senha_com_espacos_recusada(self):
        for nova in SENHAS_COM_ESPACOS:
            with self.subTest(nova=repr(nova)):
                self.assert_recusa_sem_alterar(db.SenhaComEspacosError, SENHA_ANA, nova)
        self.assertIsNotNone(db.verificar_login("ana@sino.com", SENHA_ANA))

    def test_senha_antiga_com_espacos_pode_ser_substituida(self):
        for antiga, legado in (("senha antiga", False), ("  bordas  ", False), ("com espaço", True)):
            with self.subTest(antiga=repr(antiga), legado=legado):
                senha_hash = (hashlib.sha256(antiga.encode("utf-8")).hexdigest() if legado
                              else db._gerar_hash_senha(antiga))
                self.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (senha_hash, self.ana))
                self.assert_recusa_sem_alterar(db.SenhaAtualIncorretaError, "".join(antiga.split()), "nova-senha-1")
                self.assert_recusa_sem_alterar(db.SenhaComEspacosError, antiga, antiga)   # reutilizar: tem espaço
                self.assertTrue(db.alterar_senha(self.ana, antiga, "nova-senha-1"))
                self.assertTrue(self.hash_de(self.ana).startswith("pbkdf2_sha256$"))
                self.assertIsNotNone(db.verificar_login("ana@sino.com", "nova-senha-1"))
                self.assertIsNone(db.verificar_login("ana@sino.com", antiga))

    def test_emoji_composto(self):
        self.assert_recusa_sem_alterar(db.SenhaCurtaError, SENHA_ANA, "abcdef" + EMOJI_COMPOSTO)
        self.assertTrue(db.alterar_senha(self.ana, SENHA_ANA, "abcdefg" + EMOJI_COMPOSTO))
        self.assertIsNotNone(db.verificar_login("ana@sino.com", "abcdefg" + EMOJI_COMPOSTO))

    # CT83 --------------------------------------------------------------
    def test_senha_atual_incorreta(self):
        self.assert_recusa_sem_alterar(db.SenhaAtualIncorretaError, "senha-errada", "nova-senha-1")
        self.assertIsNotNone(db.verificar_login("ana@sino.com", SENHA_ANA))

    def test_senha_atual_nao_textual(self):
        for atual in (None, 12345678, b"senha-da-ana"):
            with self.subTest(atual=repr(atual)):
                self.assert_recusa_sem_alterar(db.SenhaAtualIncorretaError, atual, "nova-senha-1")

    def test_atual_incorreta_tem_precedencia_sobre_nova_invalida(self):
        self.assert_recusa_sem_alterar(db.SenhaAtualIncorretaError, "senha-errada", "curta")

    # CT81 --------------------------------------------------------------
    def test_nova_senha_curta(self):
        self.assert_recusa_sem_alterar(db.SenhaCurtaError, SENHA_ANA, "a" * 7)
        self.assertTrue(db.alterar_senha(self.ana, SENHA_ANA, "a" * 8))

    def test_nova_senha_so_de_espacos_ou_nao_textual(self):
        self.assert_recusa_sem_alterar(db.SenhaComEspacosError, SENHA_ANA, " " * 12)
        for nova in (None, 12345678):
            with self.subTest(nova=repr(nova)):
                self.assert_recusa_sem_alterar(db.SenhaInvalidaError, SENHA_ANA, nova)

    # CT85 --------------------------------------------------------------
    def test_nova_igual_a_atual(self):
        self.assert_recusa_sem_alterar(db.SenhaIgualAtualError, SENHA_ANA, SENHA_ANA)

    def test_reutilizar_depois_de_alterar_volta_a_ser_permitido_so_se_diferente_da_atual(self):
        db.alterar_senha(self.ana, SENHA_ANA, "nova-senha-1")
        self.assert_recusa_sem_alterar(db.SenhaIgualAtualError, "nova-senha-1", "nova-senha-1")

    def test_usuario_inexistente(self):
        antes = self.linhas()
        self.assertIs(db.alterar_senha(9999, SENHA_ANA, "nova-senha-1"), False)
        self.assertEqual(self.linhas(), antes)

    # Hashes legados ----------------------------------------------------
    def test_hash_legado_com_senha_antiga_curta(self):
        self.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                      (hashlib.sha256("abc".encode("utf-8")).hexdigest(), self.ana))
        self.assert_recusa_sem_alterar(db.SenhaAtualIncorretaError, "abd", "nova-senha-1")
        self.assert_recusa_sem_alterar(db.SenhaCurtaError, "abc", "abc")      # nova curta antes de "igual"
        self.assertTrue(db.alterar_senha(self.ana, "abc", "nova-senha-1"))
        self.assertTrue(self.hash_de(self.ana).startswith("pbkdf2_sha256$"))
        self.assertIsNotNone(db.verificar_login("ana@sino.com", "nova-senha-1"))
        self.assertIsNone(db.verificar_login("ana@sino.com", "abc"))

    def test_hash_legado_nova_igual_a_atual(self):
        legado = "senha-antiga-longa"
        self.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                      (hashlib.sha256(legado.encode("utf-8")).hexdigest(), self.ana))
        self.assert_recusa_sem_alterar(db.SenhaIgualAtualError, legado, legado)

    # Falhas ------------------------------------------------------------
    def test_falha_na_gravacao_nao_altera_nada(self):
        self.executar("CREATE TRIGGER falha_senha BEFORE UPDATE OF senha_hash ON usuarios "
                      "BEGIN SELECT RAISE(ABORT, 'falha simulada'); END")
        antes = self.linhas()
        with self.assertRaises(sqlite3.DatabaseError):
            db.alterar_senha(self.ana, SENHA_ANA, "nova-senha-1")
        self.assertEqual(self.linhas(), antes)
        self.executar("DROP TRIGGER falha_senha")
        self.assertTrue(db.alterar_senha(self.ana, SENHA_ANA, "nova-senha-1"))  # nada ficou travado

    def test_falha_ao_gerar_o_hash_nao_altera_nada(self):
        antes = self.linhas()
        with mock.patch.object(db, "_gerar_hash_senha", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                db.alterar_senha(self.ana, SENHA_ANA, "nova-senha-1")
        self.assertEqual(self.linhas(), antes)


if __name__ == "__main__":
    unittest.main()
