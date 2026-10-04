"""
Detalhes da conta (ERS v6.0, Etapa 4; campos fixos na Etapa 10): RF31, 8.4, CT55–CT58, CT115, CT116.

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

    def celulas(self):
        """Células da grade de Detalhes, na ordem: (rótulo, Text do valor, célula)."""
        grade = next(c for c in self.controles(ft.ResponsiveRow))
        resultado = []
        for celula in grade.controls:
            textos = [t for t in percorrer(celula) if isinstance(t, ft.Text)]
            resultado.append((textos[0].value, textos[1], celula))
        return resultado

    def campos(self):
        return [(rotulo, valor.value) for rotulo, valor, _ in self.celulas()]

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
        self.assertEqual({c.color for c in rotulos}, {cores.texto_sem_categoria})  # rótulo (Etapa 10, RNF09)
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
    def test_ct115_conta_unica_mostra_todos_os_campos(self):
        # Etapa 10 (8.4): sempre os seis campos, nesta ordem, com os textos de ausência.
        db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-09-20")
        self.entrar()
        self.abrir_detalhes("Seguro")
        self.assertEqual(self.campos(), [
            ("Valor", "R$ 90,00"), ("Vencimento", "20/09/2026"), ("Categoria", "Sem categoria"),
            ("Parcela", "Não há parcelas"), ("Recorrência", "Esta conta não é recorrente."),
            ("Descrição", "Sem descrição"),
        ])
        cores_dos_valores = {rotulo: valor.color for rotulo, valor, _ in self.celulas()}
        self.assertEqual(cores_dos_valores["Parcela"], cores.texto_secundario)
        self.assertEqual(cores_dos_valores["Descrição"], cores.texto_secundario)
        self.assertEqual(cores_dos_valores["Categoria"], cores.texto_sem_categoria)
        # Largura: Valor|Vencimento e Categoria|Parcela lado a lado; Recorrência e Descrição em linha inteira.
        larguras = [celula.col for _, _, celula in self.celulas()]
        self.assertEqual(larguras, [{"xs": 12, "lg": 6}] * 4 + [{"xs": 12}] * 2)

    def test_serie_ativa_mostra_parcela(self):
        db.criar_serie_recorrente(self.usuario_id, "Curso", 200.0, "2026-09-20", "mensal", data_termino="2026-12")
        db.criar_serie_recorrente(self.usuario_id, "Internet", 100.0, "2026-09-22", "mensal")
        self.entrar()
        self.abrir_detalhes("Curso")
        campos = dict(self.campos())
        self.assertEqual(campos["Parcela"], "Parcela 1 de 4")
        self.assertEqual(campos["Recorrência"], "Esta conta se repete mensalmente até dezembro de 2026.")
        self.clicar(self.botao("Voltar"))
        # Sem término: posição sem total (5.19) e "sem prazo definido", nunca "Não há parcelas".
        self.abrir_detalhes("Internet")
        campos = dict(self.campos())
        self.assertEqual(campos["Parcela"], "Parcela 1")
        self.assertEqual(campos["Recorrência"], "Esta conta se repete mensalmente sem prazo definido para término.")

    # ---------------------------------------------------------------- rótulos (Etapa 10)
    def rotulos(self):
        """Text de cada rótulo da grade, na ordem."""
        grade = next(c for c in self.controles(ft.ResponsiveRow))
        return [next(t for t in percorrer(celula) if isinstance(t, ft.Text)) for celula in grade.controls]

    def rotulo_ao_lado(self, celula):
        """A linha interna da célula põe o rótulo (largura fixa) à esquerda do conteúdo?"""
        _, textos = celula.content.controls
        return isinstance(textos, ft.Row) and textos.controls[0].width == main.LARGURA_ROTULO_DETALHES

    def test_largura_minima_do_rotulo_ao_lado(self):
        self.assertTrue(main.rotulo_ao_lado_em_detalhes(main.LARGURA_MINIMA_ROTULO_AO_LADO))
        self.assertFalse(main.rotulo_ao_lado_em_detalhes(main.LARGURA_MINIMA_ROTULO_AO_LADO - 1))
        self.assertFalse(main.rotulo_ao_lado_em_detalhes(380))  # janela padrão do app
        self.assertTrue(main.rotulo_ao_lado_em_detalhes(None))  # desconhecida: larga

    def test_rotulos_maiores_a_esquerda_e_tudo_centralizado(self):
        self.pagina.width = 900
        db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-09-20", descricao="Linha 1\nLinha 2")
        self.entrar()
        self.abrir_detalhes("Seguro")
        self.assertEqual([t.value for t in self.rotulos()],
                         ["Valor", "Vencimento", "Categoria", "Parcela", "Recorrência", "Descrição"])
        self.assertEqual({(t.size, t.color) for t in self.rotulos()}, {(14, cores.texto_secundario)})
        for rotulo, valor, celula in self.celulas():
            with self.subTest(rotulo=rotulo):
                self.assertTrue(self.rotulo_ao_lado(celula))
                # Ícone e rótulo centralizados também em Recorrência e Descrição.
                self.assertEqual(celula.content.vertical_alignment, ft.CrossAxisAlignment.CENTER)
                self.assertEqual(celula.content.controls[1].vertical_alignment, ft.CrossAxisAlignment.CENTER)
                self.assertTrue(celula.content.controls[1].controls[1].expand)  # valor quebra linha, sem corte

    def test_janela_estreita_poe_o_rotulo_acima_e_redesenha_ao_redimensionar(self):
        self.pagina.width = 380
        db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-09-20")
        self.entrar()
        self.abrir_detalhes("Seguro")
        self.assertFalse(any(self.rotulo_ao_lado(celula) for _, _, celula in self.celulas()))
        self.assertEqual(self.campos()[0], ("Valor", "R$ 90,00"))  # rótulo acima, mesmo conteúdo

        self.pagina.width = 900
        self.pagina.on_resize(None)
        self.assertTrue(self.na_tela_de_detalhes())
        self.assertTrue(all(self.rotulo_ao_lado(celula) for _, _, celula in self.celulas()))

    def test_redimensionar_fora_dos_detalhes_nao_redesenha(self):
        self.pagina.width = 900
        db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-09-20")
        self.entrar()
        self.abrir_detalhes("Seguro")
        ao_redimensionar = self.pagina.on_resize
        self.clicar(self.botao("Voltar"))
        self.pagina.width = 380
        limpezas = self.pagina.overlay.clear.call_count
        ao_redimensionar(None)
        self.assertFalse(self.na_tela_de_detalhes())
        self.assertEqual(self.pagina.overlay.clear.call_count, limpezas)  # nada redesenhado nem limpo

    def test_icones_informativos_no_mesmo_verde_e_cabecalho_preservado(self):
        # Etapa 10: Valor, Vencimento, Categoria, Parcela, Recorrência e Descrição usam um
        # único papel (detalhes_icone) com o mesmo fundo suave; a cor da
        # categoria (cabeçalho) e a pílula de status não mudam.
        db.criar_serie_recorrente(self.usuario_id, "Curso", 200.0, "2026-09-20", "mensal",
                                  categoria_id=self.casa, data_termino="2026-12")
        self.entrar()
        self.abrir_detalhes("Curso")
        informativos = (ft.Icons.PAYMENTS_OUTLINED, ft.Icons.CALENDAR_MONTH, ft.Icons.FOLDER_OUTLINED,
                        ft.Icons.LAYERS_OUTLINED, ft.Icons.REPEAT, ft.Icons.NOTES)
        icones = {c.icon: c for c in self.controles(ft.Icon) if c.icon in informativos}
        self.assertEqual(set(icones), set(informativos))
        for icone in icones.values():
            fundo = next(c for c in self.controles(ft.Container) if c.content is icone)
            self.assertEqual(icone.color, cores.detalhes_icone)
            self.assertEqual(fundo.bgcolor, ft.Colors.with_opacity(0.12, cores.detalhes_icone))
        circulo = next(c for c in self.controles(ft.Container) if c.content is self.texto("🏡"))
        self.assertIn("#96E199", str(circulo.bgcolor))
        pilula = next(c for c in self.controles(ft.Container) if c.content is self.texto("Pendente"))
        self.assertEqual(pilula.bgcolor, ft.Colors.with_opacity(0.12, cores.status_pendente))
        self.assertEqual(pilula.content.color, cores.texto_pilula_pendente)

    def test_serie_encerrada_sem_parcela_e_nao_recorrente(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Academia", 99.0, "2026-09-20", "mensal")
        db.encerrar_recorrencia(ids[0])
        self.entrar()
        self.abrir_detalhes("Academia")
        # Série encerrada vira conta avulsa (5.8): mesmos textos da conta Única.
        campos = dict(self.campos())
        self.assertEqual(campos["Recorrência"], "Esta conta não é recorrente.")
        self.assertEqual(campos["Parcela"], "Não há parcelas")

    # ---------------------------------------------------------------- descrição
    def test_ct57_sem_descricao_mostra_sem_descricao(self):
        # Etapa 10 (8.4, 5.22): o campo fica na tela com "Sem descrição", em linha inteira.
        db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-09-20")
        self.entrar()
        self.abrir_detalhes("Seguro")
        rotulo, valor, celula = self.celulas()[-1]
        self.assertEqual((rotulo, valor.value, valor.color), ("Descrição", "Sem descrição", cores.texto_secundario))
        self.assertEqual(celula.col, {"xs": 12})

    def test_ct58_descricao_completa_com_quebras_de_linha(self):
        descricao = "Linha 1\nLinha 2\n\n" + "texto longo " * 38
        conta_id = db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-09-20", descricao=descricao)
        self.entrar()
        self.abrir_detalhes("Seguro")
        rotulo, valor, celula = self.celulas()[-1]
        self.assertEqual((rotulo, valor.value), ("Descrição", self.conta_descricao(conta_id)))
        recorrencia = next(v for r, v, _ in self.celulas() if r == "Recorrência")
        self.assertEqual((valor.color, valor.size, valor.weight), (cores.texto_principal, recorrencia.size, None))
        self.assertIsNone(valor.max_lines)  # altura automática, sem corte
        self.assertEqual(celula.col, {"xs": 12})
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
