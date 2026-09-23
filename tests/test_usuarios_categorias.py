"""
Regressão v5.0 — cadastro e login (RF01/RF02/RF15, RNF05 com PBKDF2 e
atualização de hash legado) e categorias (RF14/RF18, 5.11/5.13).
"""

import hashlib
import unittest

from apoio_banco import TesteComBancoTemporario, db


class TestUsuarios(TesteComBancoTemporario):
    def hash_armazenado(self, email):
        return self.consultar("SELECT senha_hash FROM usuarios WHERE email = ?", (email,))[0][0]

    def test_cadastro_exige_aceite_dos_termos(self):
        sucesso, _ = db.criar_usuario("Ana", "ana@sino.com", "senha123", aceite_termos=False)
        self.assertFalse(sucesso)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM usuarios")[0][0], 0)

    def test_cadastro_registra_data_do_aceite(self):
        self.criar_usuario(email="ana@sino.com")
        aceite = self.consultar("SELECT termos_aceitos_em FROM usuarios WHERE email = 'ana@sino.com'")[0][0]
        self.assertEqual(aceite, self.HOJE.isoformat())

    def test_email_duplicado_e_recusado(self):
        self.criar_usuario(email="ana@sino.com")
        sucesso, _ = db.criar_usuario("Outra", "ana@sino.com", "x", aceite_termos=True)
        self.assertFalse(sucesso)

    def test_senha_armazenada_com_pbkdf2_e_salt_individual(self):
        self.criar_usuario(email="a@sino.com", senha="mesma")
        self.criar_usuario(email="b@sino.com", senha="mesma")
        hash_a, hash_b = self.hash_armazenado("a@sino.com"), self.hash_armazenado("b@sino.com")
        self.assertTrue(hash_a.startswith(f"{db.PBKDF2_ALGORITMO}${db.PBKDF2_ITERACOES}$"))
        self.assertNotIn("mesma", hash_a)
        self.assertNotEqual(hash_a, hash_b)

    def test_login(self):
        usuario_id = self.criar_usuario(email="ana@sino.com", senha="senha123", nome="Ana")
        self.assertEqual(db.verificar_login("ana@sino.com", "senha123"),
                         {"id": usuario_id, "nome": "Ana", "email": "ana@sino.com"})
        self.assertIsNone(db.verificar_login("ana@sino.com", "errada"))
        self.assertIsNone(db.verificar_login("nao@existe.com", "senha123"))

    def test_hash_legado_autentica_e_e_atualizado_no_login(self):
        usuario_id = self.criar_usuario(email="antigo@sino.com", senha="qualquer")
        hash_legado = hashlib.sha256("abc".encode("utf-8")).hexdigest()
        self.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (hash_legado, usuario_id))

        self.assertIsNone(db.verificar_login("antigo@sino.com", "errada"))
        self.assertEqual(self.hash_armazenado("antigo@sino.com"), hash_legado)

        self.assertIsNotNone(db.verificar_login("antigo@sino.com", "abc"))
        novo_hash = self.hash_armazenado("antigo@sino.com")
        self.assertTrue(novo_hash.startswith(f"{db.PBKDF2_ALGORITMO}$"))
        self.assertIsNotNone(db.verificar_login("antigo@sino.com", "abc"))

    def test_hash_corrompido_falha_sem_excecao(self):
        usuario_id = self.criar_usuario(email="x@sino.com")
        self.executar("UPDATE usuarios SET senha_hash = 'pbkdf2_sha256$abc$zz' WHERE id = ?", (usuario_id,))
        self.assertIsNone(db.verificar_login("x@sino.com", "senha123"))


class TestCategorias(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def test_catalogo_inicial_de_11_categorias_com_cores_distintas(self):
        ids = db.inicializar_categorias_padrao(self.usuario_id)
        self.assertEqual(len(ids), 11)
        categorias = db.listar_categorias(self.usuario_id)
        self.assertEqual({c["nome"] for c in categorias}, {nome for nome, _ in db.CATEGORIAS_PRE_CRIADAS})
        cores = [c["cor"] for c in categorias]
        self.assertEqual(len(set(cores)), 11)
        self.assertTrue(set(cores) <= set(db.PALETA_CORES_CATEGORIAS))
        self.assertEqual(db.inicializar_categorias_padrao(self.usuario_id), [])

    def test_paleta_oficial_tem_30_cores_distintas(self):
        self.assertEqual(len(db.PALETA_CORES_CATEGORIAS), 30)
        self.assertEqual(len(set(db.PALETA_CORES_CATEGORIAS)), 30)

    def test_limite_de_30_categorias(self):
        for indice in range(db.LIMITE_CATEGORIAS_POR_USUARIO):
            db.criar_categoria(self.usuario_id, f"Categoria {indice}")
        with self.assertRaises(ValueError):
            db.criar_categoria(self.usuario_id, "Uma a mais")
        self.assertEqual(len(db.listar_categorias(self.usuario_id)), 30)

    def test_cor_automatica_e_unica(self):
        primeira = db.criar_categoria(self.usuario_id, "A")
        segunda = db.criar_categoria(self.usuario_id, "B")
        cores = {c["id"]: c["cor"] for c in db.listar_categorias(self.usuario_id)}
        self.assertEqual(cores[primeira], db.PALETA_CORES_CATEGORIAS[0])
        self.assertEqual(cores[segunda], db.PALETA_CORES_CATEGORIAS[1])

    def test_cor_em_uso_e_recusada(self):
        cor = db.PALETA_CORES_CATEGORIAS[5]
        db.criar_categoria(self.usuario_id, "A", cor=cor)
        with self.assertRaises(ValueError):
            db.criar_categoria(self.usuario_id, "B", cor=cor)
        segunda = db.criar_categoria(self.usuario_id, "B")
        with self.assertRaises(ValueError):
            db.editar_categoria(self.usuario_id, segunda, cor=cor)

    def test_mesma_cor_permitida_entre_usuarios(self):
        outro = self.criar_usuario(email="outro@sino.com")
        cor = db.PALETA_CORES_CATEGORIAS[3]
        db.criar_categoria(self.usuario_id, "A", cor=cor)
        db.criar_categoria(outro, "A", cor=cor)

    def test_cor_liberada_ao_trocar_ou_excluir(self):
        cor = db.PALETA_CORES_CATEGORIAS[0]
        primeira = db.criar_categoria(self.usuario_id, "A", cor=cor)
        db.editar_categoria(self.usuario_id, primeira, cor=db.PALETA_CORES_CATEGORIAS[7])
        segunda = db.criar_categoria(self.usuario_id, "B", cor=cor)
        db.excluir_categoria(self.usuario_id, segunda)
        db.criar_categoria(self.usuario_id, "C", cor=cor)

    def test_editar_categoria_isolada_por_usuario(self):
        categoria_id = db.criar_categoria(self.usuario_id, "Casa", "🏡")
        outro = self.criar_usuario(email="outro@sino.com")
        self.assertFalse(db.editar_categoria(outro, categoria_id, nome="Invadida"))
        self.assertTrue(db.editar_categoria(self.usuario_id, categoria_id, nome="Lar", icone="🏠"))
        categoria = db.listar_categorias(self.usuario_id)[0]
        self.assertEqual((categoria["nome"], categoria["icone"]), ("Lar", "🏠"))

    def test_excluir_categoria_deixa_contas_e_series_sem_categoria(self):
        categoria_id = db.criar_categoria(self.usuario_id, "Casa")
        avulsa = db.criar_conta_unica(self.usuario_id, "Luz", 120.0, "2026-09-20", categoria_id=categoria_id)
        serie_id, _ = db.criar_serie_recorrente(
            self.usuario_id, "Aluguel", 1000.0, "2026-09-10", "mensal", categoria_id=categoria_id,
        )
        outro = self.criar_usuario(email="outro@sino.com")
        self.assertFalse(db.excluir_categoria(outro, categoria_id))

        self.assertTrue(db.excluir_categoria(self.usuario_id, categoria_id))

        self.assertIsNotNone(self.conta(avulsa))
        self.assertIsNone(self.conta(avulsa)["categoria_id"])
        self.assertEqual({o[4] for o in self.ocorrencias(serie_id)}, {None})
        self.assertIsNone(self.serie(serie_id)["categoria_id"])
        novo = db.gerar_ocorrencias_sob_demanda(serie_id, "2027-10")[0]
        self.assertIsNone(self.conta(novo)["categoria_id"])


if __name__ == "__main__":
    unittest.main()
