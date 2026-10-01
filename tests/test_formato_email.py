"""
Formato de e-mail dos fluxos com código (ERS v6.0, Etapa 8): a mesma regra no
serviço (servidor/src/email.ts), no cliente (backend/servico_codigos.py) e na
camada de dados (database/db.py), conferida com os casos gerados pelo
servidor (servidor/test/conformidade/emails.json). Bancos temporários; sem rede.
"""

import unittest
from unittest import mock

from apoio_banco import TesteComBancoTemporario, db
from apoio_servico import Relogio, TransporteFalso, carregar_conformidade, configuracao

import servico_codigos as sc
from test_autorizacoes_locais import autorizacao

NAO_ASCII = "josé@exemplo.com"


class TestCasosCompartilhados(unittest.TestCase):
    def setUp(self):
        self.casos = carregar_conformidade("emails.json")["casos"]

    def test_cliente_e_banco_seguem_o_servidor(self):
        self.assertGreaterEqual(len(self.casos), 27)
        for caso in self.casos:
            entrada = caso["entrada"]
            with self.subTest(entrada=repr(entrada)):
                if caso["valido"]:
                    self.assertEqual(sc.normalizar_email(entrada), caso["normalizado"])
                    self.assertEqual(db.validar_email_novo(entrada).lower(), caso["normalizado"])
                    self.assertEqual(sc.validar_email(entrada), db.validar_email_novo(entrada))
                else:
                    with self.assertRaises(sc.EmailInvalidoError):
                        sc.validar_email(entrada)
                    with self.assertRaises(db.EmailInvalidoError):
                        db.validar_email_novo(entrada)

    def test_bordas_so_removem_espacos_comuns(self):
        self.assertEqual(sc.validar_email("  a@b.com  "), "a@b.com")
        for borda in (" ", "\t", "\n", "\x1f", "　", " "):
            with self.subTest(borda=repr(borda)):
                with self.assertRaises(sc.EmailInvalidoError):
                    sc.validar_email(f"{borda}a@b.com")
                with self.assertRaises(db.EmailInvalidoError):
                    db.validar_email_novo(f"a@b.com{borda}")

    def test_tipos_invalidos(self):
        for valor in (None, 42, b"a@b.com"):
            with self.subTest(valor=valor):
                with self.assertRaises(sc.EmailInvalidoError):
                    sc.validar_email(valor)
                with self.assertRaises(db.EmailInvalidoError):
                    db.validar_email_novo(valor)


class TestClienteRecusaAntesDeEnviar(unittest.IsolatedAsyncioTestCase):
    async def test_mesma_recusa_nas_tres_finalidades_sem_requisicao(self):
        transporte = TransporteFalso([])
        cliente = sc.ClienteServicoCodigos(configuracao(), transporte, relogio=Relogio())
        for finalidade in sc.FINALIDADES:
            with self.subTest(finalidade=finalidade):
                with self.assertRaises(sc.EmailInvalidoError) as erro:
                    cliente.nova_operacao(finalidade, NAO_ASCII)
                self.assertEqual(str(erro.exception), "Informe um e-mail válido.")
        self.assertEqual(transporte.requisicoes, [])


class TestFuncoesLocais(TesteComBancoTemporario):
    def assert_sem_consulta(self, funcao):
        """O formato é recusado antes de abrir o banco."""
        with mock.patch.object(db, "conectar", side_effect=AssertionError("consultou o banco")):
            with self.assertRaises(db.EmailInvalidoError):
                funcao()

    def test_cadastro_e_alteracao_recusam_novos_enderecos_fora_do_formato(self):
        senha = db.hash_de_nova_senha("senhaforte1")
        self.assert_sem_consulta(lambda: db.concluir_cadastro(
            autorizacao("cadastro", NAO_ASCII), "J", NAO_ASCII, senha, relogio=Relogio()))
        usuario_id = self.criar_usuario(email="atual@sino.com", senha="senha123")
        pendencia = db.conferir_senha_atual(usuario_id, "senha123")
        self.assert_sem_consulta(lambda: db.alterar_email_verificado(
            autorizacao("alteracao_email", NAO_ASCII), pendencia, NAO_ASCII, relogio=Relogio()))
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM autorizacoes_usadas"), [(0,)])

    def test_recuperacao_recusa_o_formato_antes_de_consultar_a_conta(self):
        for email in (NAO_ASCII, "pessoa@exemplo.com ", "sem-arroba"):
            with self.subTest(email=repr(email)):
                self.assert_sem_consulta(lambda: db.existe_conta_verificada(email))
                self.assert_sem_consulta(lambda: db.redefinir_senha_por_autorizacao(
                    autorizacao("recuperacao_senha", "x@sino.com"), email, "novasenha2", relogio=Relogio()))

    def test_conta_antiga_com_acento_continua_entrando_e_pode_trocar_para_ascii(self):
        usuario_id = self.criar_usuario(email=NAO_ASCII, senha="senha123")
        self.assertIsNotNone(db.verificar_login(NAO_ASCII, "senha123"))
        self.assertTrue(db.email_em_uso(f"  {NAO_ASCII}  "))
        pendencia = db.conferir_senha_atual(usuario_id, "senha123")
        novo = db.alterar_email_verificado(autorizacao("alteracao_email", "jose@exemplo.com"), pendencia,
                                           "jose@exemplo.com", relogio=Relogio())
        self.assertEqual(novo, "jose@exemplo.com")
        self.assertIsNotNone(db.verificar_login("jose@exemplo.com", "senha123"))
        self.assertEqual(self.consultar("SELECT email_verificado FROM usuarios WHERE id = ?", (usuario_id,)),
                         [(1,)])


if __name__ == "__main__":
    unittest.main()
