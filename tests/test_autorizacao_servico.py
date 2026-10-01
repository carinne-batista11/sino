"""
Testes de autorizacao_servico (Etapa 8): verificação Ed25519 estrita da
autorização, com os vetores gerados pelo servidor
(servidor/test/conformidade/autorizacao.json).
"""

import json
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from apoio_servico import CHAVE_PRIVADA, KID, assinar, b64url, carregar_conformidade

import autorizacao_servico as aut


class TestVetoresDoServidor(unittest.TestCase):
    def setUp(self):
        self.vetores = carregar_conformidade("autorizacao.json")
        self.chaves = {self.vetores["kid"]: aut.chave_publica_de_hex(self.vetores["chave_publica_hex"])}

    def test_chave_publica_coincide_com_a_de_teste(self):
        self.assertEqual(
            self.vetores["chave_publica_hex"],
            CHAVE_PRIVADA.public_key().public_bytes_raw().hex(),
        )

    def test_vetor_valido(self):
        conteudo = aut.verificar_assinatura(self.vetores["valido"]["token"], self.chaves)
        esperado = self.vetores["valido"]["conteudo"]
        self.assertEqual(
            conteudo,
            aut.ConteudoAutorizacao(
                kid=esperado["kid"], jti=esperado["jti"], finalidade=esperado["fin"],
                contexto=esperado["ctx"], iat=esperado["iat"], exp=esperado["exp"],
            ),
        )

    def test_todos_os_vetores_invalidos_sao_recusados(self):
        motivos = [v["motivo"] for v in self.vetores["invalidos"]]
        self.assertGreaterEqual(len(motivos), 14)
        for vetor in self.vetores["invalidos"]:
            with self.subTest(motivo=vetor["motivo"]):
                with self.assertRaises(aut.AutorizacaoInvalidaError):
                    aut.verificar_assinatura(vetor["token"], self.chaves)


class TestVerificacaoEstrita(unittest.TestCase):
    CHAVES = {KID: CHAVE_PRIVADA.public_key()}
    BASE = {
        "v": 1, "kid": KID, "jti": "anRpLWRlLXRlc3RlLTAwMQ", "fin": "cadastro", "ctx": "a" * 64,
        "iat": 1_790_000_000, "exp": 1_790_000_600,
    }

    def recusa(self, token):
        with self.assertRaises(aut.AutorizacaoInvalidaError):
            aut.verificar_assinatura(token, self.CHAVES)

    def test_aceita_o_formato_exato(self):
        self.assertEqual(aut.verificar_assinatura(assinar(self.BASE), self.CHAVES).jti, self.BASE["jti"])

    def test_tipos_ambiguos(self):
        for campo, valor in [("v", True), ("iat", 1.0), ("exp", "1790000600"), ("v", 2), ("jti", "curto"),
                             ("iat", 0), ("iat", 1_790_000_601)]:
            with self.subTest(campo=campo, valor=valor):
                self.recusa(assinar({**self.BASE, campo: valor}))

    def test_json_estrito(self):
        texto = json.dumps(self.BASE, separators=(",", ":"))
        self.recusa(assinar(texto.replace('"iat":1790000000', '"iat":NaN')))
        self.recusa(assinar(texto.replace('"exp":1790000600', '"exp":Infinity')))
        self.recusa(assinar(texto.replace('"v":1,', '"v":1,"v":1,')))
        self.recusa(assinar("[1,2]"))

    def test_tamanhos(self):
        self.recusa("a" * 1025)
        grande = {**self.BASE, "ctx": "a" * 64}
        texto = json.dumps(grande, separators=(",", ":"))[:-1] + ',"x":"' + "y" * 600 + '"}'
        self.recusa(assinar(texto))
        payload, assinatura = assinar(self.BASE).split(".")
        self.recusa(f"{payload}.{assinatura[:-4]}")

    def test_assinatura_de_outra_chave_e_kid_desconhecido(self):
        outra = Ed25519PrivateKey.from_private_bytes(bytes([0x33]) * 32)
        self.recusa(assinar(self.BASE, outra))
        self.recusa(assinar({**self.BASE, "kid": "desconhecido"}))

    def test_base64url_estrito(self):
        self.assertEqual(aut.decodificar_base64url(b64url(b"\x00\xff")), b"\x00\xff")
        for invalido in ["a=", "a+b", "a/b", "A", "AB", "AC"]:
            with self.subTest(texto=invalido):
                with self.assertRaises(ValueError):
                    aut.decodificar_base64url(invalido)

    def test_chave_publica_hex(self):
        with self.assertRaises(ValueError):
            aut.chave_publica_de_hex("abc")
        with self.assertRaises(ValueError):
            aut.chave_publica_de_hex(None)

    def test_json_estrito_utf8(self):
        with self.assertRaises(aut.JsonEstritoError):
            aut.carregar_json_estrito(b'{"a":"\xff"}')


if __name__ == "__main__":
    unittest.main()
