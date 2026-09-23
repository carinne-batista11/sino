"""
Centralização das cores do tema (ERS v6.0, T3 — Etapa 0): todo papel de
cor usado em backend/main.py existe na paleta do tema e main.py não tem
mais cores fixas. (A paleta oficial das categorias continua em
database/db.py, fora do tema.)
"""

import os
import re
import sys
import unittest

import apoio_banco

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import cores  # noqa: E402

CAMINHO_MAIN = os.path.join(apoio_banco.RAIZ_PROJETO, "backend", "main.py")
COR_VALIDA = re.compile(r"^(#[0-9A-F]{6}|white)$")


class TestCores(unittest.TestCase):
    def setUp(self):
        with open(CAMINHO_MAIN, encoding="utf-8") as arquivo:
            self.codigo_main = arquivo.read()

    def test_papeis_usados_existem_no_tema_claro(self):
        usados = set(re.findall(r"(?<![\w.])cores\.([a-z_]+)", self.codigo_main))
        self.assertTrue(usados)
        self.assertEqual(usados - set(cores.PALETAS["claro"]), set())

    def test_valores_validos(self):
        for papel, valor in cores.PALETAS["claro"].items():
            self.assertRegex(valor, COR_VALIDA, papel)

    def test_sem_cor_fixa_em_main(self):
        self.assertEqual(re.findall(r'"#[0-9A-Fa-f]{3,8}"|"white"', self.codigo_main), [])

    def test_tema_padrao_e_claro(self):
        self.assertEqual(cores.TEMA_PADRAO, "claro")
        self.assertEqual(cores.texto_principal, cores.PALETAS["claro"]["texto_principal"])

    def test_papel_inexistente(self):
        with self.assertRaises(AttributeError):
            cores.papel_que_nao_existe


if __name__ == "__main__":
    unittest.main()
