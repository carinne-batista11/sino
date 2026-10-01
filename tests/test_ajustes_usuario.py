"""
ERS v6.0, Etapa 6 (passo 1) — funções de usuário da tela Ajustes em
database/db.py: obter_usuario, alterar_nome_usuario (RF35, 5.23; CT62) e
definir_tema (RF40, 5.36; CT96, CT97), além do tema no retorno de
verificar_login. Tudo em bancos temporários; o banco real nunca é tocado.
"""

import os
import unittest
from unittest import mock

from apoio_banco import TesteComBancoTemporario, _conectar_original, db
from fixture_schema_v5 import criar_banco_v5

import limites  # database/ já está no sys.path via apoio_banco

EMOJI_COMPOSTO = "👩‍💻"  # 3 pontos de código, 1 caractere percebido


class TesteComDoisUsuarios(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.ana = self.criar_usuario(email="ana@sino.com", senha="senha123", nome="Ana")
        self.bia = self.criar_usuario(email="bia@sino.com", senha="senha456", nome="Bia")

    def linhas_usuarios(self):
        return self.consultar("SELECT * FROM usuarios ORDER BY id")

    def linha(self, usuario_id):
        return self.consultar("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))[0]


class TestObterUsuario(TesteComDoisUsuarios):
    def test_dados_do_usuario(self):
        self.assertEqual(db.obter_usuario(self.ana), {
            "id": self.ana, "nome": "Ana", "email": "ana@sino.com",
            "email_verificado": False, "tema": "claro",
        })

    def test_email_verificado_e_booleano(self):
        self.executar("UPDATE usuarios SET email_verificado = 1 WHERE id = ?", (self.bia,))
        self.assertIs(db.obter_usuario(self.bia)["email_verificado"], True)
        self.assertIs(db.obter_usuario(self.ana)["email_verificado"], False)

    def test_nao_expoe_senha_nem_aceite(self):
        self.assertEqual(set(db.obter_usuario(self.ana)),
                         {"id", "nome", "email", "email_verificado", "tema"})

    def test_usuario_inexistente(self):
        self.assertIsNone(db.obter_usuario(9999))


class TestAlterarNomeUsuario(TesteComDoisUsuarios):
    def test_altera_so_o_proprio_usuario(self):
        antes_bia = self.linha(self.bia)
        self.assertEqual(db.alterar_nome_usuario(self.ana, "Ana Maria"), "Ana Maria")
        self.assertEqual(db.obter_usuario(self.ana)["nome"], "Ana Maria")
        self.assertEqual(self.linha(self.bia), antes_bia)

    def test_so_o_nome_muda(self):
        antes = self.linha(self.ana)
        db.alterar_nome_usuario(self.ana, "Ana Maria")
        depois = self.linha(self.ana)
        colunas = [c[1] for c in self.consultar("PRAGMA table_info(usuarios)")]
        diferentes = {c for c, a, d in zip(colunas, antes, depois) if a != d}
        self.assertEqual(diferentes, {"nome"})

    def test_remove_espacos_das_bordas_e_preserva_os_internos(self):
        self.assertEqual(db.alterar_nome_usuario(self.ana, "  Ana   Maria \n"), "Ana   Maria")
        self.assertEqual(db.obter_usuario(self.ana)["nome"], "Ana   Maria")

    # CT62 --------------------------------------------------------------
    def test_70_aceito_71_recusado_sem_gravar(self):
        self.assertEqual(db.alterar_nome_usuario(self.ana, "a" * 70), "a" * 70)
        antes = self.linhas_usuarios()
        with self.assertRaises(limites.LimiteDeCaracteresError) as contexto:
            db.alterar_nome_usuario(self.ana, "a" * 71)
        self.assertEqual((contexto.exception.campo, contexto.exception.limite, contexto.exception.contagem),
                         ("nome_usuario", 70, 71))
        self.assertIn("70", str(contexto.exception))
        self.assertEqual(self.linhas_usuarios(), antes)

    def test_limite_por_caractere_percebido(self):
        nome = "a" * 69 + EMOJI_COMPOSTO  # 72 pontos de código, 70 caracteres percebidos
        self.assertGreater(len(nome), 70)
        self.assertEqual(db.alterar_nome_usuario(self.ana, nome), nome)
        with self.assertRaises(limites.LimiteDeCaracteresError):
            db.alterar_nome_usuario(self.ana, nome + EMOJI_COMPOSTO)
        self.assertEqual(db.obter_usuario(self.ana)["nome"], nome)

    def test_limite_contado_depois_de_remover_espacos(self):
        self.assertEqual(db.alterar_nome_usuario(self.ana, "  " + "a" * 70 + "  "), "a" * 70)

    def test_nome_vazio_recusado_sem_gravar(self):
        antes = self.linhas_usuarios()
        for nome in ("", "   ", "\n\t", None):
            with self.subTest(nome=nome):
                with self.assertRaises(ValueError):
                    db.alterar_nome_usuario(self.ana, nome)
        self.assertEqual(self.linhas_usuarios(), antes)

    def test_usuario_inexistente_nao_grava(self):
        antes = self.linhas_usuarios()
        self.assertIsNone(db.alterar_nome_usuario(9999, "Fantasma"))
        self.assertEqual(self.linhas_usuarios(), antes)

    def test_login_devolve_o_novo_nome(self):
        db.alterar_nome_usuario(self.ana, "Ana Maria")
        self.assertEqual(db.verificar_login("ana@sino.com", "senha123")["nome"], "Ana Maria")
        self.assertEqual(db.verificar_login("bia@sino.com", "senha456")["nome"], "Bia")


class TestDefinirTema(TesteComDoisUsuarios):
    # CT97 --------------------------------------------------------------
    def test_padrao_e_claro(self):
        self.assertEqual(db.TEMA_PADRAO, "claro")
        self.assertEqual(db.obter_usuario(self.ana)["tema"], "claro")
        self.assertEqual(db.verificar_login("ana@sino.com", "senha123")["tema"], "claro")

    def test_altera_so_o_proprio_usuario(self):
        antes_bia = self.linha(self.bia)
        self.assertTrue(db.definir_tema(self.ana, "escuro"))
        self.assertEqual(db.obter_usuario(self.ana)["tema"], "escuro")
        self.assertEqual(self.linha(self.bia), antes_bia)

    # CT96 --------------------------------------------------------------
    def test_preferencia_persiste_entre_logins(self):
        db.definir_tema(self.ana, "escuro")
        self.assertEqual(db.verificar_login("ana@sino.com", "senha123")["tema"], "escuro")
        self.assertEqual(db.verificar_login("ana@sino.com", "senha123")["tema"], "escuro")
        self.assertEqual(db.verificar_login("bia@sino.com", "senha456")["tema"], "claro")

    def test_voltar_para_claro(self):
        db.definir_tema(self.ana, "escuro")
        self.assertTrue(db.definir_tema(self.ana, "claro"))
        self.assertEqual(db.obter_usuario(self.ana)["tema"], "claro")

    def test_tema_invalido_recusado_sem_gravar(self):
        db.definir_tema(self.ana, "escuro")
        antes = self.linhas_usuarios()
        for tema in ("azul", "Escuro", "", None, "sistema"):
            with self.subTest(tema=tema):
                with self.assertRaises(ValueError):
                    db.definir_tema(self.ana, tema)
        self.assertEqual(self.linhas_usuarios(), antes)

    def test_usuario_inexistente(self):
        antes = self.linhas_usuarios()
        self.assertFalse(db.definir_tema(9999, "escuro"))
        self.assertEqual(self.linhas_usuarios(), antes)

    def test_temas_aceitos_sao_os_do_schema(self):
        self.assertEqual(db.TEMAS, ("claro", "escuro"))
        for tema in db.TEMAS:
            self.assertTrue(db.definir_tema(self.ana, tema))


class TestVerificarLoginTema(TesteComBancoTemporario):
    def test_contrato_anterior_preservado(self):
        usuario_id = self.criar_usuario(email="ana@sino.com", senha="senha123", nome="Ana")
        usuario = db.verificar_login("ana@sino.com", "senha123")
        self.assertEqual({k: usuario[k] for k in ("id", "nome", "email")},
                         {"id": usuario_id, "nome": "Ana", "email": "ana@sino.com"})
        self.assertIsNone(db.verificar_login("ana@sino.com", "errada"))

    def test_banco_v5_nao_migrado_usa_tema_padrao(self):
        caminho_v5 = os.path.join(os.path.dirname(self.caminho_banco), "sino_v5.db")
        criar_banco_v5(caminho_v5, conectar=_conectar_original)
        with mock.patch.object(db, "NOME_DO_BANCO", caminho_v5):
            self.assertTrue(db.criar_usuario("Bia", "bia@sino.com", "senha123", aceite_termos=True)[0])
            usuario = db.verificar_login("bia@sino.com", "senha123")
        self.assertEqual((usuario["nome"], usuario["tema"]), ("Bia", "claro"))


if __name__ == "__main__":
    unittest.main()
