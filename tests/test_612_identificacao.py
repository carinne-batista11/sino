"""
Sino 6.12 (experimental), Etapa 5 -- identificação (D1).

"Parcela X de Y" só para contas parceladas (série com linha em `parcelamentos`);
"Ocorrência X de Y" (ou "Ocorrência X", sem término) para recorrências mensais e
anuais -- inclusive as já existentes, mesmo com término, que nunca passam a ser
tratadas como parcelamento. Conta Única: sem identificação ("Não há parcelas").
Na Etapa 5 o parcelamento é registrado direto no banco (a criação vem na Etapa 6).
"""

import os
import sys
import unittest
from unittest import mock

import apoio_banco
from apoio_banco import DataFixa, TesteComBancoTemporario, db
from test_tela_principal import Evento, percorrer

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import flet as ft  # noqa: E402
import main  # noqa: E402


class TestTextos(unittest.TestCase):
    def test_textos(self):
        self.assertEqual(main.texto_identificacao({"tipo": "parcela", "posicao": 2, "total": 12}), "Parcela 2 de 12")
        self.assertEqual(main.texto_identificacao({"tipo": "ocorrencia", "posicao": 2, "total": 12}),
                         "Ocorrência 2 de 12")
        self.assertEqual(main.texto_identificacao({"tipo": "ocorrencia", "posicao": 5, "total": None}),
                         "Ocorrência 5")
        self.assertEqual(main.texto_ocorrencia(1, 4), "Ocorrência 1 de 4")
        self.assertEqual(main.texto_parcela((3, 6)), "Parcela 3 de 6")

    def test_rotulo(self):
        self.assertEqual(main.rotulo_identificacao({"tipo": "parcela", "posicao": 1, "total": 2}), "Parcela")
        self.assertEqual(main.rotulo_identificacao({"tipo": "ocorrencia", "posicao": 1, "total": 2}), "Ocorrência")
        self.assertEqual(main.rotulo_identificacao(None), "Parcela")


class BaseIdentificacao(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario(email="id@sino.com", senha="senha1234")

    def parcelar_direto(self, serie_id, quantidade, total_centavos):
        self.executar("INSERT INTO parcelamentos VALUES (?, ?, ?, '2026-09-01')", (serie_id, quantidade, total_centavos))


class TestIdentificacaoNoBanco(BaseIdentificacao):
    def test_recorrencias_sao_ocorrencias(self):
        _, mensal_com = db.criar_serie_recorrente(self.usuario_id, "Curso", 200.0, "2026-09-20", "mensal",
                                                  data_termino="2026-12")
        _, mensal_sem = db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-22", "mensal")
        _, anual = db.criar_serie_recorrente(self.usuario_id, "IPVA", 900.0, "2026-03-10", "anual")
        s_com = self.consultar("SELECT serie_id FROM contas WHERE id = ?", (mensal_com[1],))[0][0]
        self.assertEqual(db.obter_identificacao(s_com, mensal_com[1]), {"tipo": "ocorrencia", "posicao": 2, "total": 4})
        s_sem = self.consultar("SELECT serie_id FROM contas WHERE id = ?", (mensal_sem[0],))[0][0]
        self.assertEqual(db.obter_identificacao(s_sem, mensal_sem[0]), {"tipo": "ocorrencia", "posicao": 1, "total": None})
        s_anual = self.consultar("SELECT serie_id FROM contas WHERE id = ?", (anual[1],))[0][0]
        self.assertEqual(db.obter_identificacao(s_anual, anual[1])["tipo"], "ocorrencia")
        self.assertFalse(db.serie_parcelada(s_com))

    def test_parcelamento_e_parcela(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Notebook", 250.0, "2026-09-20", "mensal",
                                                  data_termino="2026-11")
        self.parcelar_direto(serie_id, 3, 75000)
        self.assertTrue(db.serie_parcelada(serie_id))
        self.assertEqual([db.obter_identificacao(serie_id, i) for i in ids],
                         [{"tipo": "parcela", "posicao": p, "total": 3} for p in (1, 2, 3)])

    def test_unica_e_casos_sem_serie(self):
        conta = db.criar_conta_unica(self.usuario_id, "Luz", 100.0, "2026-09-10")
        self.assertIsNone(db.obter_identificacao(None, conta))
        self.assertFalse(db.serie_parcelada(None))
        self.assertFalse(db.serie_parcelada(999))

    def test_banco_sem_a_tabela_da_v11(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Curso", 200.0, "2026-09-20", "mensal",
                                                  data_termino="2026-12")
        self.executar("DROP TABLE parcelamentos")
        self.assertFalse(db.serie_parcelada(serie_id))
        self.assertEqual(db.obter_identificacao(serie_id, ids[0])["tipo"], "ocorrencia")

    def test_contas_existentes_nao_viram_parcelamento(self):
        # Uma série mensal com término criada antes (sem linha em parcelamentos) continua recorrência.
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Academia", 120.0, "2026-09-05", "mensal",
                                                  data_termino="2027-02")
        self.assertEqual({db.obter_identificacao(serie_id, i)["tipo"] for i in ids}, {"ocorrencia"})
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM parcelamentos"), [(0,)])


class TestIdentificacaoNasTelas(BaseIdentificacao):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.pagina = mock.MagicMock()
        self.pagina.controls = []
        self.pagina.add.side_effect = lambda *controles: self.pagina.controls.extend(controles)
        db.criar_serie_recorrente(self.usuario_id, "Curso", 200.0, "2026-09-20", "mensal", data_termino="2026-12")
        db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-22", "mensal")
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Notebook", 250.0, "2026-09-25", "mensal",
                                                data_termino="2026-11")
        self.parcelar_direto(serie_id, 3, 75000)
        db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-09-28")

    def controles(self, tipo=None):
        todos = [c for raiz in self.pagina.controls for c in percorrer(raiz)]
        return [c for c in todos if tipo is None or isinstance(c, tipo)]

    def textos(self):
        return [c.value for c in self.controles(ft.Text)]

    def clicar(self, controle):
        controle.on_click(Evento(self.pagina, controle))

    def entrar(self):
        main.main(self.pagina)
        campos = {c.label: c for c in self.controles(ft.TextField)}
        campos["E-mail"].value = "id@sino.com"
        campos["Senha"].value = "senha1234"
        self.clicar(next(c for c in self.controles() if isinstance(c, ft.Button) and c.content == "Entrar"))

    def campos_dos_detalhes(self, nome):
        linha = next(c for c in self.controles(ft.Container)
                     if c.on_click is not None and isinstance(c.content, ft.Row) and c.border is not None
                     and any(isinstance(t, ft.Text) and t.value == nome for t in percorrer(c)))
        self.clicar(linha)
        grade = next(c for c in self.controles(ft.ResponsiveRow))
        campos = {}
        for celula in grade.controls:
            textos = [t for t in percorrer(celula) if isinstance(t, ft.Text)]
            campos[textos[0].value] = textos[1].value
        self.clicar(next(c for c in self.controles()
                         if isinstance(c, (ft.Button, ft.TextButton, ft.OutlinedButton)) and c.content == "Voltar"))
        return campos

    def test_inicio_mostra_parcela_e_ocorrencia(self):
        self.entrar()
        subtitulos = [t for t in self.textos() if isinstance(t, str) and " · " in t or (isinstance(t, str) and (
            t.startswith("Parcela") or t.startswith("Ocorrência")))]
        juntos = " | ".join(subtitulos)
        self.assertIn("Parcela 1 de 3", juntos)              # Notebook (parcelado)
        self.assertIn("Ocorrência 1 de 4", juntos)           # Curso (mensal com término)
        self.assertIn("Ocorrência 1", juntos)                # Internet (sem término)
        self.assertNotIn("Parcela 1 de 4", juntos)
        self.assertNotRegex(juntos, r"Parcela 1(?! de 3)")

    def test_detalhes(self):
        self.entrar()
        self.assertEqual(self.campos_dos_detalhes("Notebook")["Parcela"], "Parcela 1 de 3")
        curso = self.campos_dos_detalhes("Curso")
        self.assertEqual(curso["Ocorrência"], "Ocorrência 1 de 4")
        self.assertNotIn("Parcela", curso)
        self.assertEqual(self.campos_dos_detalhes("Internet")["Ocorrência"], "Ocorrência 1")
        self.assertEqual(self.campos_dos_detalhes("Seguro")["Parcela"], "Não há parcelas")


if __name__ == "__main__":
    unittest.main()
