"""
Detalhes da conta (ERS v6.0, Etapa 4): RF31, 8.4, CT55–CT58, CT115, CT116.

Funções puras (identificação pela categoria, status ao lado da ação,
recorrência e parcela) e o fluxo real da tela com uma página falsa sobre um
banco temporário v7. Hoje fixo em 15/09/2026. Nenhuma janela é aberta.
"""

import os
import sys
import unittest
from datetime import date
from unittest import mock

import apoio_banco
from apoio_banco import DataFixa, TesteComBancoTemporario, db
from test_tela_principal import Evento, percorrer

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import cores  # noqa: E402
import flet as ft  # noqa: E402
import main  # noqa: E402

HOJE = date(2026, 9, 15)


class TestFuncoesDosDetalhes(unittest.TestCase):
    def test_identificacao_com_emoji_e_cor(self):
        self.assertEqual(main.identificacao_categoria({"nome": "Casa", "icone": "🏡", "cor": "#96E199"}),
                         {"nome": "Casa", "emoji": "🏡", "cor": "#96E199", "sem_categoria": False})

    def test_sem_categoria_e_cinza_sem_emoji(self):
        self.assertEqual(main.identificacao_categoria(None),
                         {"nome": "Sem categoria", "emoji": None, "cor": None, "sem_categoria": True})

    def test_categoria_sem_emoji_ou_cor_mantem_o_nome(self):
        self.assertEqual(main.identificacao_categoria({"nome": "Sem cor", "icone": None, "cor": None}),
                         {"nome": "Sem cor", "emoji": None, "cor": None, "sem_categoria": False})
        self.assertEqual(main.identificacao_categoria({"nome": "X", "icone": "", "cor": ""})["emoji"], None)

    def status(self, status, vencimento, pagamento=None):
        return main.status_para_detalhes(
            {"status": status, "data_vencimento": vencimento, "data_pagamento": pagamento}, HOJE)

    def test_tres_status_e_acoes(self):
        self.assertEqual(self.status("atrasado", "2026-09-10"),
                         {"status": "atrasado", "rotulo": "🔴 Atrasado", "acao": "Marcar como paga", "vence_hoje": False})
        self.assertEqual(self.status("pendente", "2026-09-20")["rotulo"], "Pendente")
        self.assertEqual(self.status("pago", "2026-09-20", "2026-09-05"),
                         {"status": "pago", "rotulo": "🟢 Pago em 05/09/2026", "acao": "Desmarcar como paga",
                          "vence_hoje": False})

    def test_vence_hoje_continua_pendente(self):
        s = self.status("pendente", "2026-09-15")
        self.assertEqual((s["status"], s["rotulo"], s["vence_hoje"]), ("pendente", "Pendente", True))

    def test_status_ao_desmarcar_pelo_vencimento_real(self):
        self.assertEqual(main.status_ao_desmarcar({"data_vencimento": "2026-09-14"}, HOJE), "atrasado")
        self.assertEqual(main.status_ao_desmarcar({"data_vencimento": "2026-09-15"}, HOJE), "pendente")

    def test_recorrencia_e_parcela(self):
        self.assertEqual(main.texto_recorrencia_detalhes(False, None), "Esta conta não é recorrente.")
        self.assertEqual(main.texto_recorrencia_detalhes(True, {"frequencia": "mensal", "data_termino": None}),
                         main.frase_recorrencia("mensal", None))
        self.assertEqual(main.texto_parcela((2, 4)), "Parcela 2 de 4")
        self.assertEqual(main.texto_parcela((3, None)), "Parcela 3")


class TestTelaDeDetalhes(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.usuario_id = self.criar_usuario(email="detalhes@sino.com", senha="senha1234")
        self.casa = db.criar_categoria(self.usuario_id, "Casa", "🏡", "#96E199")
        self.pagina = mock.MagicMock()
        self.pagina.controls = []
        self.pagina.add.side_effect = lambda *controles: self.pagina.controls.extend(controles)

    # ---------------------------------------------------------------- auxiliares
    def controles(self, tipo=None):
        todos = [c for raiz in self.pagina.controls for c in percorrer(raiz)]
        return [c for c in todos if tipo is None or isinstance(c, tipo)]

    def textos(self):
        return [c.value for c in self.controles(ft.Text)]

    def texto(self, valor):
        return next(c for c in self.controles(ft.Text) if c.value == valor)

    def clicar(self, controle):
        controle.on_click(Evento(self.pagina, controle))

    def botao(self, texto):
        return next(c for c in self.controles()
                    if isinstance(c, (ft.Button, ft.TextButton, ft.OutlinedButton)) and c.content == texto)

    def na_tela_de_detalhes(self):
        return any(getattr(c, "data", None) == "tela_detalhes" for c in self.controles())

    def entrar(self):
        main.main(self.pagina)
        campos = {c.label: c for c in self.controles(ft.TextField)}
        campos["E-mail"].value = "detalhes@sino.com"
        campos["Senha"].value = "senha1234"
        self.clicar(self.botao("Entrar"))

    def ir_para_outubro(self):
        self.clicar(next(b for b in self.controles(ft.IconButton) if b.icon == ft.Icons.CHEVRON_RIGHT))
        self.assertIn("Outubro 2026", self.textos())

    def abrir_detalhes(self, nome):
        linha = next(c for c in self.controles(ft.Container)
                     if c.on_click is not None and isinstance(c.content, ft.Row) and c.border is not None
                     and any(isinstance(t, ft.Text) and t.value == nome for t in percorrer(c)))
        self.clicar(linha)
        self.assertTrue(self.na_tela_de_detalhes())

    # ---------------------------------------------------------------- identificação
    def test_ct55_emoji_e_cor_da_categoria(self):
        db.criar_conta_unica(self.usuario_id, "Aluguel", 1500.0, "2026-09-20", categoria_id=self.casa)
        self.entrar()
        self.abrir_detalhes("Aluguel")

        emoji = self.texto("🏡")
        circulo = next(c for c in self.controles(ft.Container) if c.content is emoji)
        self.assertIn("#96E199", str(circulo.bgcolor))
        self.assertIn("Casa", self.textos())
        self.assertEqual(self.texto("Aluguel").size, 22)

    def test_ct116_sem_categoria_em_cinza_sem_emoji(self):
        db.criar_conta_unica(self.usuario_id, "Presente", 50.0, "2026-09-20")
        self.entrar()
        self.abrir_detalhes("Presente")

        rotulos = [c for c in self.controles(ft.Text) if c.value == "Sem categoria"]
        self.assertEqual({c.color for c in rotulos}, {cores.sem_categoria})
        circulo = next(c for c in self.controles(ft.Container) if c.width == 64)
        self.assertIsNone(circulo.content)

    def test_categoria_existente_sem_emoji_nem_cor(self):
        categoria = self.executar("INSERT INTO categorias (usuario_id, nome, icone, cor) VALUES (?, 'Diversos', NULL, NULL)",
                                  (self.usuario_id,))
        db.criar_conta_unica(self.usuario_id, "Feira", 80.0, "2026-09-20", categoria_id=categoria)
        self.entrar()
        self.abrir_detalhes("Feira")
        self.assertIn("Diversos", self.textos())
        self.assertNotIn("Sem categoria", self.textos())
        circulo = next(c for c in self.controles(ft.Container) if c.width == 64)
        self.assertIsNone(circulo.content)
        self.assertEqual(circulo.bgcolor, cores.categoria_sem_cor)

    # ---------------------------------------------------------------- status e pagamento
    def test_ct56_pendente_atrasada_e_vence_hoje(self):
        db.criar_conta_unica(self.usuario_id, "Pendente A", 10.0, "2026-09-20")
        db.criar_conta_unica(self.usuario_id, "Atrasada B", 10.0, "2026-09-10")
        db.criar_conta_unica(self.usuario_id, "Hoje C", 10.0, "2026-09-15")
        self.entrar()
        for nome, rotulo, vence_hoje in (("Pendente A", "Pendente", False), ("Atrasada B", "🔴 Atrasado", False),
                                         ("Hoje C", "Pendente", True)):
            with self.subTest(nome=nome):
                self.abrir_detalhes(nome)
                self.assertIn(rotulo, self.textos())
                self.assertEqual("Vence hoje" in self.textos(), vence_hoje)
                self.assertIsInstance(self.botao("Marcar como paga"), ft.Button)
                self.clicar(self.botao("Voltar"))

    def test_marcar_como_paga_so_esta_ocorrencia_e_continua_nos_detalhes(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Escola", 700.0, "2026-09-20", "mensal")
        self.entrar()
        self.abrir_detalhes("Escola")

        self.clicar(self.botao("Marcar como paga"))

        self.assertTrue(self.na_tela_de_detalhes())
        self.assertIn("🟢 Pago em 15/09/2026", self.textos())
        self.assertIsInstance(self.botao("Desmarcar como paga"), ft.OutlinedButton)
        self.assertEqual((self.conta(ids[0])["status"], self.conta(ids[0])["data_pagamento"]), ("pago", "2026-09-15"))
        self.assertEqual(self.conta(ids[1])["status"], "pendente")

    def test_desmarcar_como_paga_remove_a_data_e_recalcula_pelo_vencimento(self):
        atrasada = db.criar_conta_unica(self.usuario_id, "Luz", 90.0, "2026-09-10")
        futura = db.criar_conta_unica(self.usuario_id, "Água", 60.0, "2026-09-25")
        db.marcar_conta_como_paga(atrasada, "2026-09-12")
        db.marcar_conta_como_paga(futura, "2026-09-12")
        self.entrar()

        self.abrir_detalhes("Luz")
        self.assertIn("🟢 Pago em 12/09/2026", self.textos())
        self.clicar(self.botao("Desmarcar como paga"))
        self.assertIn("🔴 Atrasado", self.textos())
        self.assertEqual((self.conta(atrasada)["status"], self.conta(atrasada)["data_pagamento"]), ("pendente", None))
        self.assertEqual(self.conta(futura)["status"], "pago")  # outra conta intacta

        self.clicar(self.botao("Voltar"))
        self.abrir_detalhes("Água")
        self.clicar(self.botao("Desmarcar como paga"))
        self.assertIn("Pendente", self.textos())
        self.assertIsInstance(self.botao("Marcar como paga"), ft.Button)

    # ---------------------------------------------------------------- grade, recorrência, parcela
    def test_ct115_conta_unica_sem_parcela(self):
        db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-09-20")
        self.entrar()
        self.abrir_detalhes("Seguro")
        textos = self.textos()
        self.assertIn("Esta conta não é recorrente.", textos)
        self.assertNotIn("Parcela", textos)
        for rotulo in ("Valor", "Vencimento", "Categoria", "Recorrência"):
            self.assertIn(rotulo, textos)
        self.assertIn("R$ 90,00", textos)
        self.assertIn("20/09/2026", textos)

    def test_serie_ativa_mostra_parcela(self):
        db.criar_serie_recorrente(self.usuario_id, "Curso", 200.0, "2026-09-20", "mensal", data_termino="2026-12")
        db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-22", "mensal")
        self.entrar()
        self.abrir_detalhes("Curso")
        self.assertIn("Parcela 1 de 4", self.textos())
        self.assertIn(main.frase_recorrencia("mensal", "2026-12"), self.textos())
        self.clicar(self.botao("Voltar"))
        self.abrir_detalhes("Internet")
        self.assertIn("Parcela 1", self.textos())

    def test_serie_encerrada_sem_parcela_e_nao_recorrente(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Academia", 99.0, "2026-09-20", "mensal")
        db.encerrar_recorrencia(ids[0])
        self.entrar()
        self.abrir_detalhes("Academia")
        self.assertIn("Esta conta não é recorrente.", self.textos())
        self.assertNotIn("Parcela", self.textos())

    # ---------------------------------------------------------------- descrição
    def test_ct57_sem_descricao_nao_ocupa_espaco(self):
        db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-09-20")
        self.entrar()
        self.abrir_detalhes("Seguro")
        self.assertNotIn("Descrição", self.textos())

    def test_ct58_descricao_completa_com_quebras_de_linha(self):
        descricao = "Linha 1\nLinha 2\n\n" + "texto longo " * 38
        conta_id = db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-09-20", descricao=descricao)
        self.entrar()
        self.abrir_detalhes("Seguro")
        self.assertIn("Descrição", self.textos())
        self.assertIn(self.conta_descricao(conta_id), self.textos())
        self.assertIn("\n\n", self.conta_descricao(conta_id))

    def conta_descricao(self, conta_id):
        return self.consultar("SELECT descricao FROM contas WHERE id = ?", (conta_id,))[0][0]

    # ---------------------------------------------------------------- rodapé e navegação
    def test_editar_e_excluir_iguais_e_editar_volta_aos_detalhes(self):
        db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-09-20")
        self.entrar()
        self.abrir_detalhes("Seguro")
        editar, excluir = self.botao("Editar"), self.botao("Excluir")
        self.assertEqual((editar.width, excluir.width), (140, 140))
        self.assertEqual(excluir.bgcolor, cores.acao_destrutiva)

        self.clicar(editar)
        self.assertFalse(self.na_tela_de_detalhes())
        self.assertIn("Esta conta não é recorrente.", self.textos())  # Editar usa o mesmo texto
        self.clicar(self.botao("Cancelar"))
        self.assertTrue(self.na_tela_de_detalhes())

    def test_voltar_dos_detalhes_mantem_o_mes(self):
        db.criar_conta_unica(self.usuario_id, "Luz Outubro", 120.0, "2026-10-15")
        self.entrar()
        self.ir_para_outubro()
        self.abrir_detalhes("Luz Outubro")
        self.clicar(self.botao("Voltar"))
        self.assertIn("Outubro 2026", self.textos())

    def test_exclusao_concluida_volta_ao_mes(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz Outubro", 120.0, "2026-10-15")
        self.entrar()
        self.ir_para_outubro()
        self.abrir_detalhes("Luz Outubro")
        self.clicar(self.botao("Excluir"))
        dialogo = self.pagina.show_dialog.call_args[0][0]
        next(a for a in dialogo.actions if a.content == "Excluir").on_click(Evento(self.pagina))
        self.assertIn("Outubro 2026", self.textos())
        self.assertIsNone(self.conta(conta_id))

    def test_entendi_apos_salvar_pelos_detalhes_volta_ao_mes(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz Outubro", 120.0, "2026-10-15")
        self.entrar()
        self.ir_para_outubro()
        self.abrir_detalhes("Luz Outubro")
        self.clicar(self.botao("Editar"))
        next(c for c in self.controles(ft.TextField) if c.label == "Valor").value = "130,00"
        self.clicar(self.botao("Salvar alterações"))
        dialogo = self.pagina.show_dialog.call_args[0][0]
        dialogo.actions[0].on_click(Evento(self.pagina))
        self.assertIn("Outubro 2026", self.textos())
        self.assertEqual(self.conta(conta_id)["valor"], 130.0)


if __name__ == "__main__":
    unittest.main()
