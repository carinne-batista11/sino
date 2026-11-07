"""
Sino 6.12 (experimental), Etapa 3 -- valor CONHECIDO × valor PENDENTE.

Funções centrais preparatórias: nenhuma conta existente fica pendente, e
totais, gráficos e telas continuam iguais aos da Sino 6.11 enquanto a tabela
`ocorrencias_valor_pendente` não existir (ou estiver vazia). Valor pendente
nunca é R$ 0,00: um valor conhecido de 0,00 continua conhecido.
"""

import os
import sys
import unittest

import apoio_banco
from apoio_banco import TesteComBancoTemporario, db

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import main  # noqa: E402


class TestFuncoesDeValor(unittest.TestCase):
    def test_valor_conhecido(self):
        self.assertEqual(db.valor_conhecido({"valor": 120.5}), 120.5)
        self.assertEqual(db.valor_conhecido({"valor": 120.5, "valor_pendente": False}), 120.5)
        self.assertIsNone(db.valor_conhecido({"valor": 0.0, "valor_pendente": True}))

    def test_zero_conhecido_nao_e_pendente(self):
        self.assertEqual(db.valor_conhecido({"valor": 0.0}), 0.0)
        self.assertIsNotNone(db.valor_conhecido({"valor": 0.0}))
        self.assertEqual(db.quantidade_com_valor_pendente([{"valor": 0.0}]), 0)

    def test_soma_e_quantidade(self):
        contas = [{"valor": 100.0}, {"valor": 0.0, "valor_pendente": True}, {"valor": 50.25},
                  {"valor": 999.0, "valor_pendente": True}]
        self.assertEqual(db.soma_dos_valores_conhecidos(contas), 150.25)
        self.assertEqual(db.quantidade_com_valor_pendente(contas), 2)
        self.assertEqual(db.soma_dos_valores_conhecidos([]), 0)

    def test_soma_identica_a_6_11_sem_pendentes(self):
        contas = [{"valor": v} for v in (0.1, 0.2, 1200.0, 39.9, 180.35)]
        self.assertEqual(db.soma_dos_valores_conhecidos(contas), sum(c["valor"] for c in contas))

    def test_texto_do_valor(self):
        self.assertEqual(main.texto_do_valor({"valor": 1234.5}), "R$ 1.234,50")
        self.assertEqual(main.texto_do_valor({"valor": 0.0}), "R$ 0,00")
        self.assertEqual(main.texto_do_valor({"valor": 0.0, "valor_pendente": True}), "Valor pendente")
        self.assertNotEqual(main.texto_do_valor({"valor": 0.0, "valor_pendente": True}),
                            main.texto_do_valor({"valor": 0.0}))

    def test_resumo_do_mes_igual_sem_pendentes(self):
        contas = [{"valor": 100.0, "status": "pago"}, {"valor": 50.0, "status": "pendente", "total_pago": 20.0},
                  {"valor": 30.0, "status": "atrasado", "total_pago": 0}]
        self.assertEqual(main.resumo_do_mes(contas), (180.0, 120.0, 60.0))

    def test_resumo_do_mes_sem_pendentes_no_total(self):
        contas = [{"valor": 100.0, "status": "pendente", "total_pago": 0},
                  {"valor": 0.0, "status": "pendente", "total_pago": 0, "valor_pendente": True}]
        self.assertEqual(main.resumo_do_mes(contas), (100.0, 0, 100.0))


class TestSomasNoBanco(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()
        self.casa = self.criar_categoria(self.usuario_id, "Casa")
        self.luz = db.criar_conta_unica(self.usuario_id, "Luz", 180.35, "2026-09-10", categoria_id=self.casa)
        db.criar_conta_unica(self.usuario_id, "Gás", 95.0, "2026-09-20")
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 1200.0, "2026-09-05", "mensal", data_termino="2026-11",
                                  categoria_id=self.casa)

    def totais(self):
        return (db.resumo_do_periodo(self.usuario_id, "2026-09-01", "2026-12-31"),
                db.totais_por_mes(self.usuario_id, "2026-09", "2026-12"),
                db.totais_por_ano(self.usuario_id),
                sorted((g["categoria_id"] or 0, g["total"]) for g in
                       db.gastos_por_categoria(self.usuario_id, "2026-09-01", "2026-12-31")))

    def test_sem_a_tabela_condicao_neutra(self):
        conexao = db.conectar()
        try:
            self.assertEqual(db._sql_valor_conhecido(conexao.cursor()), "1")
        finally:
            conexao.close()

    def test_totais_iguais_a_soma_direta(self):
        total, pago = db.resumo_do_periodo(self.usuario_id, "2026-09-01", "2026-12-31")
        self.assertEqual(total, round(self.consultar("SELECT SUM(valor) FROM contas")[0][0], 2))
        self.assertEqual(pago, 0)
        self.assertEqual(db.totais_por_mes(self.usuario_id, "2026-09", "2026-12"),
                         {"2026-09": 1475.35, "2026-10": 1200.0, "2026-11": 1200.0})
        self.assertEqual(db.totais_por_ano(self.usuario_id), [(2026, 3875.35)])
        self.assertEqual(self.totais()[3], [(0, 95.0), (self.casa, 3780.35)])

    def test_tabela_vazia_nao_muda_nada(self):
        antes = self.totais()
        self.executar("CREATE TABLE ocorrencias_valor_pendente (conta_id INTEGER PRIMARY KEY)")
        self.assertEqual(self.totais(), antes)

    def test_pendente_fica_fora_de_todos_os_totais(self):
        # Simulação da Etapa 3: a tabela ainda não é criada pela migração (Etapa 4). Um valor
        # diferente de zero na linha pendente prova que ele não entra em nenhuma soma.
        self.executar("CREATE TABLE ocorrencias_valor_pendente (conta_id INTEGER PRIMARY KEY)")
        self.executar("UPDATE contas SET valor = 999 WHERE id = ?", (self.luz,))
        self.executar("INSERT INTO ocorrencias_valor_pendente (conta_id) VALUES (?)", (self.luz,))
        (total, _), meses, anos, categorias = self.totais()
        self.assertEqual(total, 3695.0)
        self.assertEqual(meses["2026-09"], 1295.0)
        self.assertEqual(anos, [(2026, 3695.0)])
        self.assertEqual(categorias, [(0, 95.0), (self.casa, 3600.0)])


if __name__ == "__main__":
    unittest.main()
