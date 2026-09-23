"""
Correção v6.0 (Etapa 0) — lado da interface: salvar_edicao envia ao db.py
somente os campos realmente alterados (backend/main.py,
campos_alterados_edicao). Importa backend/main.py sem abrir o app, graças à
guarda `if __name__ == "__main__"` em torno de `ft.run(main)`.
"""

import os
import sys
import unittest
from datetime import date

import apoio_banco  # noqa: F401 -- garante database/ no sys.path antes de importar main

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import main  # noqa: E402


class TestCamposAlteradosEdicao(unittest.TestCase):
    ORIGINAL = ("Aluguel", 1000.0, date(2027, 2, 28), 3)

    def campos(self, nome="Aluguel", valor=1000.0, data=date(2027, 2, 28), categoria=3):
        nome_o, valor_o, data_o, categoria_o = self.ORIGINAL
        return main.campos_alterados_edicao(nome_o, nome, valor_o, valor, data_o, data, categoria_o, categoria)

    def test_nada_alterado(self):
        self.assertEqual(self.campos(), {})

    def test_so_valor_nao_envia_data(self):
        self.assertEqual(self.campos(valor=1100.0), {"valor": 1100.0})

    def test_so_nome(self):
        self.assertEqual(self.campos(nome="Aluguel novo"), {"nome": "Aluguel novo"})

    def test_so_data(self):
        self.assertEqual(self.campos(data=date(2027, 2, 15)), {"data_vencimento": "2027-02-15"})

    def test_trocar_categoria(self):
        self.assertEqual(self.campos(categoria=5), {"categoria_id": 5})

    def test_remover_categoria(self):
        self.assertEqual(self.campos(categoria=None), {"remover_categoria": True})

    def test_definir_categoria_em_conta_sem_categoria(self):
        campos = main.campos_alterados_edicao("A", "A", 1.0, 1.0, date(2027, 1, 1), date(2027, 1, 1), None, 7)
        self.assertEqual(campos, {"categoria_id": 7})

    def test_varios_campos(self):
        self.assertEqual(
            self.campos(nome="X", valor=2.0, categoria=None),
            {"nome": "X", "valor": 2.0, "remover_categoria": True},
        )


if __name__ == "__main__":
    unittest.main()
