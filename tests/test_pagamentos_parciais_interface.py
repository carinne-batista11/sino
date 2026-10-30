"""
Pagamentos parciais (Sino 6.10) pela interface, com uma página
falsa sobre um banco temporário (nenhuma janela é aberta). Cada passo confere
a tela E o banco: "Registrar pagamento parcial" ao lado de "Marcar como
paga", saldo e "Pagamentos registrados" (com o total pago) nos Detalhes,
quitação pelo saldo, recusas, reversão (último ou todos) com estorno
rastreável, Início e Editar conta (só dados gerais, desde a reorganização).

Hoje fixo: 15/09/2026.
"""

import asyncio
import os
import sys
from datetime import datetime
from unittest import mock

import apoio_banco
from apoio_banco import DataFixa, TesteComBancoTemporario, db

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import flet as ft  # noqa: E402
import main  # noqa: E402
import pagamentos  # noqa: E402
from test_tela_principal import Evento, percorrer  # noqa: E402


# Estrutura fixa dos Detalhes (rótulos na ordem), em qualquer situação de pagamento.
ESTRUTURA = ["Valor da conta", "Vencimento", "Total pago", "Saldo devedor", "Categoria", "Parcela",
             "Recorrência", "Descrição", "Pagamentos registrados"]


class TesteInterfacePagamentos(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.usuario_id = self.criar_usuario(email="pp@sino.com", senha="senha1234")
        db.criar_conta_unica(self.usuario_id, "Internet", 400.0, "2026-09-20")
        self.conta = self.consultar("SELECT MAX(id) FROM contas")[0][0]
        self.pagina = mock.MagicMock()
        self.pagina.controls = []
        self.pagina.width = 380
        self.pagina.add.side_effect = lambda *controles: self.pagina.controls.extend(controles)

    # ---------------------------------------------------------------- auxiliares
    def controles(self, tipo=None):
        todos = [c for raiz in self.pagina.controls for c in percorrer(raiz)]
        return [c for c in todos if tipo is None or isinstance(c, tipo)]

    def textos(self):
        return [c.value for c in self.controles(ft.Text)]

    def clicar(self, controle):
        controle.on_click(Evento(self.pagina, controle))

    def botao(self, texto):
        return next(c for c in self.controles()
                    if isinstance(c, (ft.Button, ft.TextButton, ft.OutlinedButton)) and c.content == texto)

    def tem_botao(self, texto):
        return any(isinstance(c, (ft.Button, ft.TextButton, ft.OutlinedButton)) and c.content == texto
                   for c in self.controles())

    def campo(self, rotulo, raiz=None):
        controles = percorrer(raiz) if raiz is not None else self.controles()
        return next(c for c in controles if isinstance(c, (ft.TextField, ft.Dropdown)) and c.label == rotulo)

    def entrar(self):
        self.pagina.controls.clear()
        main.main(self.pagina)
        self.campo("E-mail").value = "pp@sino.com"
        self.campo("Senha").value = "senha1234"
        self.clicar(self.botao("Entrar"))

    def linha_da_conta(self, nome):
        return next(c for c in self.controles(ft.Container)
                    if c.data in ("linha_conta", "linha_conta_empilhada")
                    and nome in [t.value for t in percorrer(c) if isinstance(t, ft.Text)])

    def abrir_detalhes(self, nome="Internet"):
        self.entrar()
        self.clicar(self.linha_da_conta(nome))

    def dialogo(self):
        return self.pagina.show_dialog.call_args[0][0]

    def textos_do_dialogo(self):
        return [c.value for c in percorrer(self.dialogo().content) if isinstance(c, ft.Text)]

    def acao_do_dialogo(self, texto):
        return next(b for b in self.dialogo().actions if b.content == texto)

    def valor_ao_lado(self, rotulo):
        textos = self.textos()
        return textos[textos.index(rotulo) + 1]

    def pagar_parcialmente(self, valor, data=None):
        self.clicar(self.botao("Registrar pagamento parcial"))
        dialogo = self.dialogo()
        self.campo("Valor a pagar", dialogo.content).value = valor
        if data is not None:
            self.campo("Data do pagamento", dialogo.content).value = data
        self.clicar(self.acao_do_dialogo("Registrar pagamento"))
        return dialogo

    def linhas(self):
        return self.consultar("SELECT valor_centavos, data_pagamento, tipo FROM pp_pagamentos ORDER BY id")

    def estrutura(self):
        return [t for t in self.textos() if t in ESTRUTURA]

    def acao_da_recorrencia(self, rotulo):
        """Item do menu do lápis da Recorrência em Editar (as ações de antes)."""
        menu = self.campo("Recorrência").suffix_icon
        return next(i for i in menu.items if i.content == rotulo)

    def acao_do_historico(self, dado):
        return next(b for b in self.controles(ft.IconButton) if b.data == dado)

    def opcao_diferenca(self, modo):
        return next(c for c in percorrer(self.dialogo().content)
                    if isinstance(c, ft.Container) and c.data == f"pp_diferenca_{modo}")

    def estornos(self):
        return self.consultar("SELECT id, estornado_em FROM pp_pagamentos ORDER BY id")

    def historico(self):
        textos = self.textos()
        return textos[textos.index("Pagamentos registrados"):]

    def opcao(self, modo):
        return next(c for c in percorrer(self.dialogo().content)
                    if isinstance(c, ft.Container) and c.data == f"pp_opcao_{modo}")

    def resumo_da_reversao(self):
        return next(c for c in percorrer(self.dialogo().content)
                    if isinstance(c, ft.Text) and c.data == "pp_resumo_reversao").value

    def quitar_exemplo(self):
        """Exemplo da autora: 150 + 100 parciais e 150 do saldo (Marcar como paga)."""
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-10")
        db.marcar_conta_como_paga(self.conta)


class TestDetalhes(TesteInterfacePagamentos):
    def test_conta_sem_pagamentos_mostra_as_duas_acoes_e_a_estrutura_completa(self):
        self.abrir_detalhes()
        self.assertTrue(self.tem_botao("Marcar como paga"))
        self.assertTrue(self.tem_botao("Registrar pagamento parcial"))
        self.assertEqual(self.estrutura(), ESTRUTURA)
        self.assertEqual(self.valor_ao_lado("Total pago"), "R$ 0,00")
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 400,00")
        self.assertIn("Nenhum pagamento registrado.", self.textos())

    def test_exemplo_da_autora_pela_tela(self):
        self.abrir_detalhes()
        self.pagar_parcialmente("150,00", "01/09/2026")
        self.assertEqual(self.dialogo().title.value, "Pagamento registrado")
        self.assertIn("Saldo devedor: R$ 250,00", self.dialogo().content.value)
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 250,00")
        self.assertIn("Total pago: R$ 150,00", self.textos())
        self.assertNotIn("Valor pago", self.textos())          # sem cartão isolado
        self.assertNotIn("Pago parcialmente", self.textos())   # sem selo no cabeçalho
        self.assertIn("Pendente", self.textos())

        self.pagar_parcialmente("100")
        self.assertIn("Total pago: R$ 250,00", self.textos())
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 150,00")

        self.clicar(self.botao("Marcar como paga"))
        self.assertIn("R$ 150,00", self.dialogo().content.value)
        self.clicar(self.acao_do_dialogo("Pagar R$ 150,00"))
        self.assertEqual(self.linhas(), [(150_00, "2026-09-01", "parcial"), (100_00, "2026-09-15", "parcial"),
                                         (150_00, "2026-09-15", "saldo")])
        self.assertIn("🟢 Pago em 15/09/2026", self.textos())
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 0,00")
        self.assertEqual(self.historico()[1:12], ["Total pago: R$ 400,00",
                                                  "01/09/2026", "Pagamento parcial", "R$ 150,00",
                                                  "15/09/2026", "Pagamento parcial", "R$ 100,00",
                                                  "15/09/2026", "Pagamento do saldo", "Conta quitada",
                                                  "R$ 150,00"])
        ids = [i for i, _ in self.estornos()]
        self.assertEqual([c.data for c in self.controles(ft.Container) if (c.data or "").startswith("pp_pagamento_")],
                         [f"pp_pagamento_{i}" for i in ids])  # cada registro identificável
        self.assertFalse(self.tem_botao("Registrar pagamento parcial"))

    def test_pagamento_do_saldo_inteiro_quita(self):
        self.abrir_detalhes()
        self.pagar_parcialmente("400,00")
        self.assertIn("foi paga por completo", self.dialogo().content.value)
        self.assertEqual(self.consultar("SELECT status FROM contas WHERE id = ?", (self.conta,)), [("pago",)])

    def test_recusas_no_dialogo(self):
        self.abrir_detalhes()
        casos = {("0", None): "Informe um valor maior que zero",
                 ("500,00", None): "O valor é maior que o saldo devedor (R$ 400,00).",
                 ("10,005", None): "Informe um valor maior que zero",
                 ("10", "16/09/2026"): "A data de pagamento não pode ser no futuro.",
                 ("10", "31/02/2026"): "Informe a data no formato dd/mm/aaaa."}
        for (valor, data), mensagem in casos.items():
            with self.subTest(valor=valor, data=data):
                dialogo = self.pagar_parcialmente(valor, data)
                textos = [c.value for c in percorrer(dialogo.content) if isinstance(c, ft.Text)]
                self.assertTrue(any(mensagem in (t or "") for t in textos), textos)
                self.pagina.pop_dialog()
        self.assertEqual(self.linhas(), [])

    def test_clique_repetido_nao_duplica(self):
        self.abrir_detalhes()
        dialogo = self.pagar_parcialmente("150")
        registrar = next(b for b in dialogo.actions if b.content == "Registrar pagamento")
        self.clicar(registrar)  # o mesmo diálogo, saldo já desatualizado
        self.assertEqual(len(self.linhas()), 1)
        textos = [c.value for c in percorrer(dialogo.content) if isinstance(c, ft.Text)]
        self.assertTrue(any("O saldo desta conta mudou" in (t or "") for t in textos))

    def test_um_pagamento_so_oferece_uma_opcao(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 400_00)
        self.abrir_detalhes()
        self.clicar(self.botao("Desmarcar como paga"))
        self.assertEqual(self.dialogo().title.value, "Desfazer pagamentos desta conta?")
        opcoes = [c.data for c in percorrer(self.dialogo().content) if isinstance(c, ft.Container)
                  and (c.data or "").startswith("pp_opcao_")]
        self.assertEqual(opcoes, ["pp_opcao_todos"])
        self.assertIn("Esta conta possui um pagamento registrado, totalizando R$ 400,00. Escolha como deseja "
                      "desfazer o pagamento.", self.textos_do_dialogo())

    def test_conta_paga_legada_continua_como_antes(self):
        self.executar("UPDATE contas SET status = 'pago', data_pagamento = '2026-09-02' WHERE id = ?", (self.conta,))
        self.abrir_detalhes()
        self.assertEqual(self.estrutura(), ESTRUTURA)
        self.assertEqual(self.valor_ao_lado("Total pago"), "R$ 400,00")
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 0,00")
        self.assertIn("Conta paga sem pagamentos individuais registrados.", self.textos())
        self.clicar(self.botao("Desmarcar como paga"))  # direto, sem diálogo
        self.assertEqual(self.consultar("SELECT status, data_pagamento FROM contas"), [("pendente", None)])
        self.assertEqual(self.linhas(), [])

    def test_excluir_conta_com_pagamentos(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 50_00)
        self.abrir_detalhes()
        self.clicar(self.botao("Excluir"))
        self.assertEqual(self.dialogo().title.value, "Excluir conta")  # confirmação de sempre
        self.clicar(self.acao_do_dialogo("Excluir"))
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas"), [(0,)])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM pp_pagamentos"), [(0,)])


class TestInicioEEditar(TesteInterfacePagamentos):
    def test_inicio_mostra_parcial_e_soma_no_pago(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00)
        db.criar_conta_unica(self.usuario_id, "Luz", 100.0, "2026-09-25")
        self.entrar()
        self.assertTrue(any("Pago parcialmente" in (t or "") for t in self.textos()))
        self.assertIn("R$ 500,00", self.textos())
        self.assertIn("pago R$ 150,00", self.textos())
        self.assertIn("pendente R$ 350,00", self.textos())

    def test_pagamento_rapido_com_parciais_pede_confirmacao(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00)
        self.entrar()
        botao = next(b for b in self.controles(ft.IconButton) if b.tooltip == "Marcar como paga")
        self.clicar(botao)
        self.assertIn("R$ 250,00", self.dialogo().content.value)
        self.clicar(self.acao_do_dialogo("Pagar R$ 250,00"))
        self.assertEqual(sum(v for v, _, _ in self.linhas()), 400_00)
        self.assertIn("pago R$ 400,00", self.textos())

        botao = next(b for b in self.controles(ft.IconButton) if b.tooltip == "Marcar como pendente")
        self.clicar(botao)
        self.assertEqual(self.dialogo().title.value, "Desfazer pagamentos desta conta?")
        self.assertEqual(self.consultar("SELECT status FROM contas"), [("pago",)])  # nada antes de confirmar
        self.clicar(self.opcao("ultimo"))
        self.clicar(self.acao_do_dialogo("Confirmar"))
        self.assertIn("pago R$ 150,00", self.textos())
        self.assertIn("pendente R$ 250,00", self.textos())

    def test_editar_mostra_pago_e_saldo_e_o_valor_continua_editavel(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00)
        self.abrir_detalhes()
        self.clicar(self.botao("Editar"))
        self.assertFalse(self.campo("Valor").read_only)
        situacao = pagamentos.obter_situacao(self.conta)                          # o banco segue igual
        self.assertEqual((situacao["pago_centavos"], situacao["saldo_centavos"]), (150_00, 250_00))
        textos = self.textos()
        self.assertEqual(textos[textos.index("Resumo dos pagamentos"):][:5],
                         ["Resumo dos pagamentos", "Total pago", "R$ 150,00", "Saldo devedor", "R$ 250,00"])
        self.assertFalse(self.tem_botao("Marcar como paga"))                     # pagar fica nos Detalhes

    def editar_valor(self, valor):
        self.clicar(self.botao("Editar"))
        self.campo("Valor").value = valor
        self.campo("Valor").on_change(None)
        self.clicar(self.botao("Salvar alterações"))

    def test_valor_menor_que_o_pago_e_recusado(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 250_00)
        self.abrir_detalhes()
        self.editar_valor("200,00")
        self.assertEqual(self.dialogo().title.value, "O valor informado é menor que o total já pago.")
        self.assertEqual(self.dialogo().content.value, "Esta conta possui R$ 250,00 em pagamentos registrados. "
                                                       "Informe um valor igual ou superior a R$ 250,00 para continuar.")
        self.assertEqual(self.consultar("SELECT valor FROM contas"), [(400.0,)])

    def test_valor_igual_ao_pago_quita_e_maior_reabre(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 250_00, "2026-09-10")
        self.abrir_detalhes()
        self.editar_valor("250,00")
        self.clicar(self.acao_do_dialogo("Entendi"))
        self.assertEqual(self.consultar("SELECT status, data_pagamento FROM contas"), [("pago", "2026-09-10")])
        self.clicar(self.linha_da_conta("Internet"))
        self.assertIn("🟢 Pago em 10/09/2026", self.textos())
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 0,00")
        self.editar_valor("500,00")
        self.assertEqual(self.dialogo().title.value, "Como deseja registrar a diferença?")
        self.clicar(self.opcao_diferenca("aberto"))
        self.clicar(self.acao_do_dialogo("Confirmar"))
        self.assertEqual(self.consultar("SELECT status, data_pagamento FROM contas"), [("pendente", None)])
        self.assertEqual(pagamentos.obter_situacao(self.conta)["saldo_centavos"], 250_00)

    def test_editar_conta_sem_pagamentos_nao_muda(self):
        self.abrir_detalhes()
        self.clicar(self.botao("Editar"))
        self.assertFalse(self.campo("Valor").read_only)
        self.assertIsNone(self.campo("Valor").helper)

    def test_este_mes_em_diante_preserva_ocorrencia_com_pagamentos(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Academia", 100.0, "2026-09-10", "mensal",
                                                  data_termino="2026-12")
        pagamentos.registrar_pagamento_parcial(ids[2], 90_00)
        self.abrir_detalhes("Academia")
        self.editar_valor("80,00")
        aviso = next(c for c in percorrer(self.dialogo().content)
                     if isinstance(c, ft.Container) and c.data == "pp_aviso_protegidas")
        self.assertEqual(aviso.content.value, "Em \"Este mês em diante\", algumas ocorrências possuem histórico "
                         "de pagamentos e manterão seus valores atuais (1 ocorrência). As demais serão atualizadas.")
        self.clicar(self.acao_do_dialogo("Este mês em diante"))
        self.assertEqual(self.dialogo().title.value, "Alteração salva")
        self.assertEqual(self.consultar("SELECT valor FROM contas WHERE serie_id = ? ORDER BY posicao", (serie_id,)),
                         [(80.0,), (80.0,), (100.0,), (80.0,)])

    def test_cancelar_o_escopo_nao_altera_valores(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Academia", 100.0, "2026-09-10", "mensal",
                                                  data_termino="2026-12")
        pagamentos.registrar_pagamento_parcial(ids[2], 90_00)
        self.abrir_detalhes("Academia")
        self.editar_valor("80,00")
        self.clicar(self.acao_do_dialogo("Cancelar"))
        self.assertEqual(self.consultar("SELECT DISTINCT valor FROM contas WHERE serie_id = ?", (serie_id,)),
                         [(100.0,)])

    def test_sem_protegidas_nao_ha_aviso(self):
        db.criar_serie_recorrente(self.usuario_id, "Academia", 100.0, "2026-09-10", "mensal", data_termino="2026-12")
        self.abrir_detalhes("Academia")
        self.editar_valor("80,00")
        self.assertFalse(any(isinstance(c, ft.Container) and c.data == "pp_aviso_protegidas"
                             for c in percorrer(self.dialogo().content)))

    def test_desfazer_o_ultimo_lancado_pela_tela(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-12")
        pagamentos.registrar_pagamento_parcial(self.conta, 250_00, "2026-09-02")
        self.abrir_detalhes()
        self.assertIn("🟢 Pago em 02/09/2026", self.textos())
        self.clicar(self.botao("Desmarcar como paga"))
        self.assertIn("Desfazer o último pagamento (R$ 250,00)", self.textos_do_dialogo())
        self.assertIn("Os pagamentos anteriores serão mantidos. A conta ficará com R$ 150,00 pagos e R$ 250,00 "
                      "em aberto.", self.textos_do_dialogo())
        self.clicar(self.opcao("ultimo"))
        self.clicar(self.acao_do_dialogo("Confirmar"))
        self.assertIn("Pendente", self.textos())
        self.assertEqual(self.valor_ao_lado("Total pago"), "R$ 150,00")
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 250,00")
        historico = self.historico()
        self.assertEqual(historico[historico.index("02/09/2026"):][:4],
                         ["02/09/2026", "Pagamento parcial",
                          "Estornado em 15/09/2026", "R$ 250,00"])
        self.entrar()
        self.assertIn("pago R$ 150,00", self.textos())

    def test_aviso_de_vencimento_soma_o_saldo(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 300_00)
        self.entrar()
        self.assertIn("Total de R$ 100,00", self.textos())


class TestReversao(TesteInterfacePagamentos):
    def test_desfazer_o_ultimo_pagamento(self):
        self.quitar_exemplo()
        self.abrir_detalhes()
        self.clicar(self.botao("Desmarcar como paga"))
        self.assertEqual(self.dialogo().title.value, "Desfazer pagamentos desta conta?")
        textos = self.textos_do_dialogo()
        self.assertIn("Esta conta possui três pagamentos registrados, totalizando R$ 400,00. Escolha como deseja "
                      "desfazer o pagamento.", textos)
        self.assertIn("Desfazer o último pagamento (R$ 150,00)", textos)
        self.assertIn("Os pagamentos anteriores serão mantidos. A conta ficará com R$ 250,00 pagos e R$ 150,00 "
                      "em aberto.", textos)
        self.assertIn("Desfazer todos os pagamentos (R$ 400,00)", textos)
        self.assertIn("Todos os pagamentos registrados serão revertidos. A conta ficará com R$ 400,00 em aberto.",
                      textos)
        confirmar = self.acao_do_dialogo("Confirmar")
        self.assertTrue(confirmar.disabled)
        self.assertEqual(self.resumo_da_reversao(), "Escolha uma opção.")

        self.clicar(self.opcao("ultimo"))
        self.assertEqual(self.resumo_da_reversao(), "Continuará pago: R$ 250,00  ·  Em aberto: R$ 150,00")
        self.assertFalse(confirmar.disabled)
        self.assertEqual([e for _, e in self.estornos()], [None, None, None])  # nada antes de confirmar

        self.clicar(confirmar)
        self.assertEqual(self.dialogo().title.value, "Pagamento desfeito")
        self.assertEqual([e for _, e in self.estornos()], [None, None, "2026-09-15"])
        self.assertEqual(self.consultar("SELECT status, data_pagamento FROM contas"), [("pendente", None)])
        self.assertIn("Pendente", self.textos())
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 150,00")
        self.assertEqual(self.historico()[1:13], ["Total pago: R$ 250,00",
                                                  "05/09/2026", "Pagamento parcial", "R$ 150,00",
                                                  "10/09/2026", "Pagamento parcial", "R$ 100,00",
                                                  "15/09/2026", "Pagamento do saldo", "Estornado em 15/09/2026",
                                                  "R$ 150,00"])
        self.assertTrue(self.tem_botao("Registrar pagamento parcial"))

    def test_desfazer_todos_os_pagamentos_conta_vencida(self):
        self.executar("UPDATE contas SET data_vencimento = '2026-09-01' WHERE id = ?", (self.conta,))
        self.quitar_exemplo()
        self.abrir_detalhes()
        self.clicar(self.botao("Desmarcar como paga"))
        self.clicar(self.opcao("todos"))
        self.assertEqual(self.resumo_da_reversao(), "Continuará pago: R$ 0,00  ·  Em aberto: R$ 400,00")
        self.clicar(self.acao_do_dialogo("Confirmar"))
        self.assertEqual(self.dialogo().title.value, "Pagamentos desfeitos")
        self.assertEqual([e for _, e in self.estornos()], ["2026-09-15"] * 3)
        self.assertIn("🔴 Atrasado", self.textos())
        self.assertEqual(self.estrutura(), ESTRUTURA)
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 400,00")
        self.assertIn("Total pago: R$ 0,00", self.textos())
        self.assertEqual(self.textos().count("Estornado em 15/09/2026"), 3)

    def test_cancelar_nao_altera_nada(self):
        self.quitar_exemplo()
        self.abrir_detalhes()
        self.clicar(self.botao("Desmarcar como paga"))
        self.clicar(self.opcao("todos"))
        self.clicar(self.acao_do_dialogo("Cancelar"))
        self.assertEqual([e for _, e in self.estornos()], [None, None, None])
        self.assertEqual(self.consultar("SELECT status FROM contas"), [("pago",)])

    def test_confirmar_duas_vezes_nao_reverte_de_novo(self):
        self.quitar_exemplo()
        self.abrir_detalhes()
        self.clicar(self.botao("Desmarcar como paga"))
        dialogo = self.dialogo()
        self.clicar(self.opcao("ultimo"))
        confirmar = next(b for b in dialogo.actions if b.content == "Confirmar")
        self.clicar(confirmar)
        confirmar.disabled = False
        self.clicar(confirmar)  # o mesmo diálogo outra vez
        self.assertEqual(self.dialogo().title.value, "Nada foi desfeito")
        self.assertEqual([e for _, e in self.estornos()], [None, None, "2026-09-15"])

    def test_detalhes_continua_exigindo_conta_quitada(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 200_00, "2026-09-10")
        pagamentos.registrar_pagamento_parcial(self.conta, 200_00, "2026-09-02")
        self.abrir_detalhes()
        self.clicar(self.botao("Desmarcar como paga"))
        self.clicar(self.opcao("todos"))
        db.editar_conta_ocorrencia(self.conta, valor=500.0)                        # reaberta por fora
        self.clicar(self.acao_do_dialogo("Confirmar"))
        self.assertEqual(self.dialogo().title.value, "Nada foi desfeito")
        self.assertEqual(self.estornos(), [(1, None), (2, None)])

    def test_quitar_de_novo_depois_de_desfazer(self):
        self.quitar_exemplo()
        pagamentos.desfazer_pagamentos(self.conta, "ultimo", [i for i, _ in self.estornos()])
        self.abrir_detalhes()
        self.clicar(self.botao("Marcar como paga"))
        self.assertIn("R$ 150,00", self.dialogo().content.value)
        self.clicar(self.acao_do_dialogo("Pagar R$ 150,00"))
        self.assertIn("Total pago: R$ 400,00", self.textos())
        self.assertEqual(len(self.estornos()), 4)


class TestPagamentosRegistrados(TesteInterfacePagamentos):
    """Histórico com lápis e lixeira nos ativos. Na etapa 4.2 ficavam em Editar
    conta; desde a reorganização (etapas 1 e 2) só nos Detalhes."""

    def ids(self):
        return [p["id"] for p in pagamentos.obter_situacao(self.conta)["pagamentos"]]

    def total_pago(self):
        return next(c.value for c in self.controles(ft.Text) if c.data == "pp_total_pago")

    def acoes_de_pagamento(self):
        return {b.data for b in self.controles(ft.IconButton) if (b.data or "").startswith("pp_")}

    def test_estrutura_estavel_em_todas_as_situacoes(self):
        self.abrir_detalhes()
        estruturas = [self.estrutura()]
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        self.abrir_detalhes()
        estruturas.append(self.estrutura())
        db.marcar_conta_como_paga(self.conta)
        self.abrir_detalhes()
        estruturas.append(self.estrutura())
        pagamentos.desfazer_pagamentos(self.conta, "todos", [p["id"] for p in
                                                              pagamentos.obter_situacao(self.conta)["ativos"]])
        self.abrir_detalhes()
        estruturas.append(self.estrutura())
        self.assertEqual(estruturas, [ESTRUTURA] * 4)
        grade = next(c for c in self.controles(ft.ResponsiveRow))
        self.assertEqual([c.col for c in grade.controls][:6], [{"xs": 12, "lg": 6}] * 6)  # três pares

    def test_detalhes_com_acoes_so_nos_ativos(self):
        # Reorganização, etapa 1: lápis e lixeira voltam aos Detalhes, só nos ativos.
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-10")
        p1, p2 = self.ids()
        pagamentos.estornar_pagamento(p2, (100_00, "2026-09-10"))
        self.abrir_detalhes()
        self.assertEqual(self.acoes_de_pagamento(), {f"pp_editar_{p1}", f"pp_desfazer_{p1}", f"pp_excluir_{p2}"})
        self.assertEqual(self.historico()[1:9], ["Total pago: R$ 150,00", "05/09/2026", "Pagamento parcial",
                                                 "R$ 150,00", "10/09/2026", "Pagamento parcial",
                                                 "Estornado em 15/09/2026", "R$ 100,00"])
        self.assertTrue(self.tem_botao("Registrar pagamento parcial"))  # registrar continua nos Detalhes
        self.assertTrue(self.tem_botao("Marcar como paga"))

    def test_acoes_so_nos_pagamentos_ativos(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-10")
        p1, p2 = self.ids()
        pagamentos.estornar_pagamento(p2, (100_00, "2026-09-10"))
        self.abrir_detalhes()
        self.assertEqual(self.acoes_de_pagamento(), {f"pp_editar_{p1}", f"pp_desfazer_{p1}", f"pp_excluir_{p2}"})
        editar = self.acao_do_historico(f"pp_editar_{p1}")
        self.assertEqual(editar.tooltip, "Editar pagamento")
        self.assertEqual(editar.icon.semantics_label, "Editar pagamento de R$ 150,00 em 05/09/2026")
        self.assertIn("Estornado em 15/09/2026", self.textos())

    def test_editar_pagamento(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-10")
        p1, _ = self.ids()
        self.abrir_detalhes()
        self.clicar(self.acao_do_historico(f"pp_editar_{p1}"))
        dialogo = self.dialogo()
        self.assertEqual(dialogo.title.value, "Editar pagamento")
        self.assertEqual(self.campo("Valor do pagamento", dialogo.content).value, "150,00")
        self.campo("Valor do pagamento", dialogo.content).value = "100,00"
        self.campo("Data do pagamento", dialogo.content).value = "04/09/2026"
        self.clicar(self.acao_do_dialogo("Salvar"))
        self.assertEqual(self.dialogo().title.value, "Pagamento atualizado")
        self.assertEqual(self.total_pago(), "Total pago: R$ 200,00")
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 200,00")
        self.assertIn("04/09/2026", self.textos())
        self.assertNotIn("R$ 150,00", [t for t in self.textos() if t])          # sem "antes"
        self.assertEqual(self.linhas()[0], (100_00, "2026-09-04", "parcial"))

    def test_editar_pagamento_recusas_e_quitacao(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-10")
        p1, _ = self.ids()
        self.abrir_detalhes()
        for valor, data, mensagem in (("300,01", "05/09/2026", "somariam mais que o valor da conta"),
                                      ("0", "05/09/2026", "Informe um valor maior que zero"),
                                      ("100", "16/09/2026", "não pode ser no futuro")):
            with self.subTest(valor=valor, data=data):
                self.clicar(self.acao_do_historico(f"pp_editar_{p1}"))
                dialogo = self.dialogo()
                self.campo("Valor do pagamento", dialogo.content).value = valor
                self.campo("Data do pagamento", dialogo.content).value = data
                self.clicar(self.acao_do_dialogo("Salvar"))
                self.assertTrue(any(mensagem in (t or "") for t in self.textos_do_dialogo()))
                self.pagina.pop_dialog()
        self.assertEqual(self.linhas()[0], (150_00, "2026-09-05", "parcial"))
        self.clicar(self.acao_do_historico(f"pp_editar_{p1}"))
        self.campo("Valor do pagamento", self.dialogo().content).value = "300,00"
        self.clicar(self.acao_do_dialogo("Salvar"))
        self.assertEqual(self.dialogo().content.value, "O valor do pagamento foi alterado de R$ 150,00 para "
                                                       "R$ 300,00.\n\nA conta ficou quitada, com R$ 400,00 pagos.")
        self.assertIn("🟢 Pago em 10/09/2026", self.textos())                   # status atualizado
        self.assertTrue(self.tem_botao("Desmarcar como paga"))

    def test_editar_pagamento_desatualizado(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        p1, = self.ids()
        self.abrir_detalhes()
        self.clicar(self.acao_do_historico(f"pp_editar_{p1}"))
        dialogo = self.dialogo()
        pagamentos.editar_pagamento(p1, 120_00, "2026-09-05", (150_00, "2026-09-05"))  # outra tela
        self.campo("Valor do pagamento", dialogo.content).value = "100,00"
        self.clicar(next(b for b in dialogo.actions if b.content == "Salvar"))
        self.assertTrue(any("Este pagamento mudou" in (t or "")
                            for t in [c.value for c in percorrer(dialogo.content) if isinstance(c, ft.Text)]))
        self.assertEqual(self.linhas(), [(120_00, "2026-09-05", "parcial")])

    def test_desfazer_um_pagamento(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-10")
        _, p2 = self.ids()
        self.abrir_detalhes()
        self.clicar(self.acao_do_historico(f"pp_desfazer_{p2}"))
        self.assertEqual(self.dialogo().title.value, "Desfazer este pagamento?")
        self.assertEqual(self.textos_do_dialogo(), [
            "Você está prestes a desfazer o pagamento de R$ 100,00 realizado em 10/09/2026.",
            "Após a confirmação, esta conta ficará com R$ 150,00 pagos e R$ 250,00 em aberto."])
        self.assertEqual(self.estornos(), [(1, None), (2, None)])  # nada antes de confirmar
        confirmar = self.acao_do_dialogo("Desfazer pagamento")
        self.clicar(confirmar)
        self.assertEqual(self.dialogo().title.value, "Pagamento desfeito")
        self.assertEqual(self.estornos(), [(1, None), (2, "2026-09-15")])
        self.assertEqual(self.total_pago(), "Total pago: R$ 150,00")
        self.assertIn("Estornado em 15/09/2026", self.textos())
        self.clicar(confirmar)  # o mesmo botão outra vez
        self.assertEqual(self.dialogo().title.value, "Nada foi desfeito")
        self.assertEqual(self.estornos(), [(1, None), (2, "2026-09-15")])

    def test_desfazer_pagamento_de_conta_quitada(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-10")
        db.marcar_conta_como_paga(self.conta)
        _, p2, _ = self.ids()
        self.abrir_detalhes()
        self.clicar(self.acao_do_historico(f"pp_desfazer_{p2}"))
        self.clicar(self.acao_do_dialogo("Desfazer pagamento"))
        self.assertIn("Pendente", self.textos())                                  # status recalculado
        self.assertEqual(self.total_pago(), "Total pago: R$ 300,00")
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 100,00")
        self.entrar()
        self.assertIn("pago R$ 300,00", self.textos())
        self.assertIn("pendente R$ 100,00", self.textos())

    def test_cancelar_edicao_de_pagamento_nao_muda_nada(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        p1, = self.ids()
        self.abrir_detalhes()
        self.clicar(self.acao_do_historico(f"pp_editar_{p1}"))
        self.campo("Valor do pagamento", self.dialogo().content).value = "10,00"
        self.clicar(self.acao_do_dialogo("Cancelar"))
        self.clicar(self.acao_do_historico(f"pp_desfazer_{p1}"))
        self.clicar(self.acao_do_dialogo("Cancelar"))
        self.assertEqual(self.linhas(), [(150_00, "2026-09-05", "parcial")])
        self.assertEqual(self.estornos(), [(1, None)])


class TestEtapa4Interface(TesteInterfacePagamentos):
    def editar_valor(self, valor):
        self.clicar(self.botao("Editar"))
        self.campo("Valor").value = valor
        self.campo("Valor").on_change(None)
        self.clicar(self.botao("Salvar alterações"))

    def test_marcar_como_paga_registra_pagamento_integral_e_desmarcar_estorna(self):
        self.abrir_detalhes()
        self.clicar(self.botao("Marcar como paga"))
        self.assertEqual(self.linhas(), [(400_00, "2026-09-15", "integral")])
        self.assertEqual(self.historico()[1:6], ["Total pago: R$ 400,00", "15/09/2026", "Pagamento integral",
                                                 "Conta quitada", "R$ 400,00"])
        self.clicar(self.botao("Desmarcar como paga"))
        self.assertEqual(self.dialogo().title.value, "Desfazer pagamentos desta conta?")
        self.assertIn("Esta conta possui um pagamento registrado, totalizando R$ 400,00. Escolha como deseja "
                      "desfazer o pagamento.", self.textos_do_dialogo())
        self.clicar(self.opcao("todos"))
        self.clicar(self.acao_do_dialogo("Confirmar"))
        self.assertEqual(self.estornos(), [(1, "2026-09-15")])
        self.assertIn("Pendente", self.textos())
        self.assertIn("Estornado em 15/09/2026", self.textos())
        self.assertEqual(self.valor_ao_lado("Total pago"), "R$ 0,00")

    def test_pagamento_rapido_do_inicio_tambem_registra(self):
        self.entrar()
        self.clicar(next(b for b in self.controles(ft.IconButton) if b.tooltip == "Marcar como paga"))
        self.assertEqual(self.linhas(), [(400_00, "2026-09-15", "integral")])
        self.assertIn("pago R$ 400,00", self.textos())

    def test_dialogo_da_diferenca(self):
        db.marcar_conta_como_paga(self.conta)
        self.abrir_detalhes()
        self.editar_valor("450,00")
        self.assertEqual(self.dialogo().title.value, "Como deseja registrar a diferença?")
        textos = self.textos_do_dialogo()
        self.assertIn("A conta Internet já possui R$ 400,00 pagos. Com a alteração, seu valor total será de "
                      "R$ 450,00.", textos)
        self.assertIn("O que deseja fazer com os R$ 50,00 adicionais?", textos)
        self.assertIn("Registrar R$ 50,00 como pagos", textos)
        self.assertIn("Manter R$ 50,00 em aberto", textos)
        confirmar = self.acao_do_dialogo("Confirmar")
        self.assertTrue(confirmar.disabled)
        self.clicar(self.opcao_diferenca("registrar"))
        self.assertEqual(next(c.value for c in percorrer(self.dialogo().content)
                              if isinstance(c, ft.Text) and c.data == "pp_resumo_diferenca"),
                         "Total pago: R$ 450,00  ·  Saldo devedor: R$ 0,00  ·  Paga")
        self.clicar(self.opcao_diferenca("aberto"))
        self.assertEqual(next(c.value for c in percorrer(self.dialogo().content)
                              if isinstance(c, ft.Text) and c.data == "pp_resumo_diferenca"),
                         "Total pago: R$ 400,00  ·  Saldo devedor: R$ 50,00  ·  Pendente")
        self.assertEqual(self.consultar("SELECT valor FROM contas"), [(400.0,)])  # nada antes de confirmar

    def test_cancelar_a_diferenca_preserva_tudo(self):
        db.marcar_conta_como_paga(self.conta)
        self.abrir_detalhes()
        self.editar_valor("450,00")
        self.clicar(self.opcao_diferenca("registrar"))
        self.clicar(self.acao_do_dialogo("Cancelar"))
        self.assertEqual(self.consultar("SELECT valor, status FROM contas"), [(400.0, "pago")])
        self.assertEqual(len(self.linhas()), 1)

    def test_registrar_a_diferenca_e_confirmacao_repetida(self):
        db.marcar_conta_como_paga(self.conta)
        self.abrir_detalhes()
        self.editar_valor("450,00")
        dialogo = self.dialogo()
        self.clicar(self.opcao_diferenca("registrar"))
        confirmar = next(b for b in dialogo.actions if b.content == "Confirmar")
        self.clicar(confirmar)
        self.assertEqual(self.dialogo().title.value, "Alteração salva")
        self.assertEqual(self.linhas(), [(400_00, "2026-09-15", "integral"), (50_00, "2026-09-15", "saldo")])
        self.assertEqual(self.consultar("SELECT valor, status FROM contas"), [(450.0, "pago")])
        confirmar.disabled = False
        self.clicar(confirmar)  # o mesmo botão outra vez: nada muda
        self.assertEqual(len(self.linhas()), 2)

    def test_conta_parcial_nao_mostra_o_dialogo(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00)
        self.abrir_detalhes()
        self.editar_valor("450,00")
        self.assertEqual(self.dialogo().title.value, "Alteração salva")
        self.assertEqual(pagamentos.obter_situacao(self.conta)["saldo_centavos"], 350_00)

    def test_aviso_na_mudanca_de_frequencia(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Academia", 100.0, "2026-09-10", "mensal",
                                                  data_termino="2027-02")
        pagamentos.registrar_pagamento_parcial(ids[2], 40_00)
        db.marcar_conta_como_paga(ids[3])
        self.abrir_detalhes("Academia")
        self.clicar(self.botao("Editar"))
        self.clicar(self.acao_da_recorrencia("Alterar frequência"))
        aviso = next(c for c in percorrer(self.dialogo().content)
                     if isinstance(c, ft.Container) and c.data == "pp_aviso_frequencia")
        self.assertEqual(aviso.content.value,
                         "Estas ocorrências têm pagamentos registrados e serão mantidas como estão: "
                         "novembro/2026 (R$ 40,00 pagos), dezembro/2026 (paga). A nova frequência não cria "
                         "outra cobrança nesses meses.")
        self.clicar(self.acao_do_dialogo("Cancelar"))
        self.assertEqual(len(self.ocorrencias(serie_id)), 6)


class TestRolagemDetalhesEditar(TesteInterfacePagamentos):
    """Correção da rolagem: Detalhes e Editar dividiam uma coluna rolável e a
    troca só do conteúdo mantinha a posição (Detalhes rolado até "Editar" abria
    Editar rolado). Cada troca entre as duas telas usa uma coluna nova; os testes
    conferem a estrutura (uma coluna rolável por troca), não pixels."""

    def setUp(self):
        super().setUp()
        self.executar("UPDATE contas SET descricao = ? WHERE id = ?", ("Linha longa. " * 70, self.conta))
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-02")
        pagamentos.registrar_pagamento_parcial(self.conta, 50_00, "2026-09-10")

    def coluna(self):
        self.assertEqual(len(self.pagina.controls), 1)
        coluna = self.pagina.controls[0]
        if coluna.data == "pp_editar_com_rodape":             # Editar: área rolável + barra fixa
            coluna = coluna.controls[0]
        self.assertIsInstance(coluna, ft.Column)
        self.assertEqual(coluna.scroll, ft.ScrollMode.AUTO)
        self.assertTrue(coluna.expand)
        return coluna

    def na_tela_de_detalhes(self):
        return any(getattr(c, "data", None) == "tela_detalhes" for c in self.controles())

    def em_editar(self):
        return "Editar conta" in self.textos() and not self.na_tela_de_detalhes()

    def seta_voltar(self):
        return next(b for b in self.controles(ft.IconButton) if getattr(b.icon, "icon", None) == ft.Icons.ARROW_BACK)

    def test_detalhes_para_editar_usa_coluna_nova(self):
        self.abrir_detalhes()
        dos_detalhes = self.coluna()
        self.clicar(self.botao("Editar"))
        da_edicao = self.coluna()
        self.assertIsNot(da_edicao, dos_detalhes)
        self.assertTrue(self.em_editar())
        self.assertEqual(self.campo("Nome da conta").value, "Internet")
        self.assertEqual(dos_detalhes.controls[0].content.data, "tela_detalhes")  # a antiga não recebe Editar

    def test_voltar_e_cancelar_de_editar_para_detalhes_usam_coluna_nova(self):
        self.abrir_detalhes()
        anteriores = [self.coluna()]
        for sair in (lambda: self.botao("Cancelar"), self.seta_voltar):
            self.clicar(self.botao("Editar"))
            anteriores.append(self.coluna())
            self.clicar(sair())
            self.assertTrue(self.na_tela_de_detalhes())
            atual = self.coluna()
            self.assertFalse(any(atual is c for c in anteriores))
            anteriores.append(atual)

    def test_lapis_continua_abrindo_editar_em_coluna_propria(self):
        self.entrar()
        do_inicio = self.pagina.controls[:]
        lapis = next(b for b in self.controles(ft.IconButton) if b.tooltip == "Editar conta")
        self.clicar(lapis)
        da_edicao = self.coluna()
        self.assertFalse(any(da_edicao is c for c in do_inicio))
        self.assertTrue(self.em_editar())
        self.assertEqual(self.campo("Nome da conta").value, "Internet")
        self.clicar(self.botao("Cancelar"))                    # pelo lápis, volta ao Início (oficial)
        self.assertFalse(self.na_tela_de_detalhes())
        self.assertIn("Total do mês", self.textos())

    def test_redesenhar_os_detalhes_mantem_a_coluna(self):
        self.abrir_detalhes()
        coluna = self.coluna()
        self.pagina.width = 900
        self.pagina.on_resize(None)                            # rótulo muda de lado: redesenha
        self.assertTrue(self.na_tela_de_detalhes())
        self.assertIs(self.coluna(), coluna)
        self.pagar_parcialmente("10,00")                       # ações dos Detalhes também redesenham
        self.assertTrue(self.na_tela_de_detalhes())
        self.assertIs(self.coluna(), coluna)

    def test_redimensionar_em_editar_nao_redesenha_e_detalhes_novos_redesenham(self):
        self.abrir_detalhes()
        dos_detalhes = self.pagina.on_resize
        self.clicar(self.botao("Editar"))
        da_edicao = self.coluna()
        self.campo("Nome da conta").value = "Internet nova"
        limpezas = self.pagina.overlay.clear.call_count
        self.pagina.width = 900
        dos_detalhes(None)
        self.assertTrue(self.em_editar())
        self.assertIs(self.coluna(), da_edicao)
        self.assertEqual(self.campo("Nome da conta").value, "Internet nova")
        self.assertEqual(self.pagina.overlay.clear.call_count, limpezas)

        self.clicar(self.botao("Cancelar"))
        voltou = self.coluna()
        limpezas = self.pagina.overlay.clear.call_count
        self.pagina.width = 380
        self.pagina.on_resize(None)
        self.assertTrue(self.na_tela_de_detalhes())
        self.assertIs(self.coluna(), voltou)
        self.assertEqual(self.pagina.overlay.clear.call_count, limpezas + 1)   # redesenhou

    def test_rascunho_de_editar_preservado(self):
        self.abrir_detalhes()
        self.clicar(self.botao("Editar"))
        coluna = self.coluna()
        valor = self.campo("Valor")
        valor.value = "500,00"
        valor.on_change(Evento(self.pagina, valor))            # só a nota da linha de pagamentos muda
        self.assertIs(self.coluna(), coluna)
        nome = self.campo("Nome da conta")
        nome.value = "Internet casa"
        nome.on_change(Evento(self.pagina, nome))
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.consultar("SELECT nome, valor, status FROM contas"),
                         [("Internet casa", 500.0, "pendente")])
        self.assertEqual(self.linhas(), [(100_00, "2026-09-02", "parcial"), (50_00, "2026-09-10", "parcial")])


class TestGerenciamentoNosDetalhes(TesteInterfacePagamentos):
    """Reorganização, etapa 1: editar e estornar pagamentos individuais pelos
    Detalhes (mesmos diálogos, gravação imediata com confirmação), com a tela
    redesenhada na mesma coluna e "Conta quitada" no pagamento que completou o
    valor (até a etapa 1 o texto era "Quitou a conta"). Hoje fixo: 15/09/2026."""

    def quitar(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-10")
        pagamentos.registrar_pagamento_parcial(self.conta, 250_00, "2026-09-02")   # lançado depois, data menor

    def acao(self, prefixo, pid):
        return next(b for b in self.controles(ft.IconButton) if b.data == f"{prefixo}{pid}")

    def editar_pagamento(self, pid, valor=None, data=None):
        self.clicar(self.acao("pp_editar_", pid))
        dialogo = self.dialogo()
        if valor is not None:
            self.campo("Valor do pagamento", dialogo.content).value = valor
        if data is not None:
            self.campo("Data do pagamento", dialogo.content).value = data
        self.clicar(self.acao_do_dialogo("Salvar"))
        return dialogo

    def na_tela_de_detalhes(self):
        return any(getattr(c, "data", None) == "tela_detalhes" for c in self.controles())

    def quitou(self):
        """Ids dos pagamentos marcados com "Conta quitada"."""
        return [int(c.data.split("_")[-1]) for c in self.controles(ft.Container)
                if (c.data or "").startswith("pp_pagamento_")
                and any(getattr(t, "data", None) == "pp_quitou" for t in percorrer(c))]

    def sem_quitadas_sem_registro(self):
        self.assertEqual(self.consultar(
            "SELECT COUNT(*) FROM contas c WHERE status = 'pago' AND NOT EXISTS (SELECT 1 FROM pp_pagamentos p "
            "WHERE p.conta_id = c.id AND p.estornado_em IS NULL)")[0][0], 0)

    # --------------------------------------------------------- "Conta quitada"
    def test_conta_quitada_no_ultimo_lancado_e_so_na_quitada(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-10")
        self.abrir_detalhes()
        self.assertEqual(self.quitou(), [])                                       # em aberto: nenhum
        self.clicar(self.botao("Voltar"))
        pagamentos.registrar_pagamento_parcial(self.conta, 250_00, "2026-09-02")
        self.clicar(self.linha_da_conta("Internet"))
        self.assertEqual(self.quitou(), [2])                                      # o 2º lançado, não a maior data
        self.assertIn("🟢 Pago em 02/09/2026", self.textos())                     # e é ele que dá a data
        self.assertEqual(sum(t == "Conta quitada" for t in self.textos()), 1)

    def test_paga_legada_sem_marca_nem_acoes(self):
        self.executar("UPDATE contas SET status = 'pago', data_pagamento = '2026-09-02' WHERE id = ?", (self.conta,))
        self.abrir_detalhes()
        self.assertEqual((self.quitou(), self.acoes_de_pagamento()), ([], set()))
        self.assertIn("Conta paga sem pagamentos individuais registrados.", self.textos())

    def acoes_de_pagamento(self):
        return {b.data for b in self.controles(ft.IconButton) if (b.data or "").startswith("pp_")}

    # --------------------------------------------------------------- editar
    def test_editar_valor_e_data_pelos_detalhes(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-10")
        self.abrir_detalhes()
        coluna = self.pagina.controls[0]
        self.editar_pagamento(1, valor="120,00", data="08/09/2026")
        self.assertEqual(self.linhas(), [(120_00, "2026-09-08", "parcial")])      # o mesmo registro
        self.assertEqual(self.dialogo().title.value, "Pagamento atualizado")
        self.assertEqual(self.dialogo().content.value, "O pagamento foi alterado para R$ 120,00, em 08/09/2026."
                                                       "\n\nA conta ficou com R$ 120,00 pagos e R$ 280,00 em aberto.")
        self.assertTrue(self.na_tela_de_detalhes())
        self.assertIs(self.pagina.controls[0], coluna)                            # redesenha na mesma coluna
        self.assertIn("Total pago: R$ 120,00", self.textos())
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 280,00")

    def test_corrigir_a_data_da_quitacao_pelo_lapis(self):
        self.quitar()
        self.abrir_detalhes()
        self.editar_pagamento(2, data="05/09/2026")
        self.assertEqual(self.consultar("SELECT status, data_pagamento FROM contas"), [("pago", "2026-09-05")])
        self.assertIn("🟢 Pago em 05/09/2026", self.textos())
        self.assertEqual(self.quitou(), [2])
        self.assertEqual(self.dialogo().title.value, "Data do pagamento alterada")
        self.assertEqual(self.dialogo().content.value, "A data do pagamento foi alterada para 05/09/2026."
                                                       "\n\nA conta ficou quitada, com R$ 400,00 pagos.")

    def test_editar_para_menos_reabre_a_conta(self):
        self.quitar()
        self.abrir_detalhes()
        self.editar_pagamento(1, valor="100,00")
        self.assertEqual(self.consultar("SELECT status, data_pagamento FROM contas"), [("pendente", None)])
        self.assertEqual(self.quitou(), [])
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 50,00")
        self.assertTrue(self.tem_botao("Registrar pagamento parcial"))
        self.sem_quitadas_sem_registro()

    def test_editar_recusas_nao_gravam(self):
        self.quitar()
        self.abrir_detalhes()
        for valor, data, erro in (("160,00", None, "máximo R$ 150,00"), ("0", None, "maior que zero"),
                                  (None, "20/09/2026", "não pode ser no futuro"), (None, "31/02/2026", "dd/mm/aaaa")):
            dialogo = self.editar_pagamento(1, valor=valor, data=data)
            mensagem = dialogo.content.controls[-1].value                          # o texto de erro
            self.assertIn(erro, mensagem)
            self.campo("Valor do pagamento", dialogo.content).value = "150,00"
            self.campo("Data do pagamento", dialogo.content).value = "10/09/2026"
        self.assertEqual(self.linhas(), [(150_00, "2026-09-10", "parcial"), (250_00, "2026-09-02", "parcial")])

    def test_editar_desatualizado_nao_grava(self):
        self.quitar()
        self.abrir_detalhes()
        pagamentos.editar_pagamento(1, 140_00, "2026-09-10", (150_00, "2026-09-10"))   # outra janela
        dialogo = self.editar_pagamento(1, valor="130,00")
        self.assertIn("mudou desde que a tela foi aberta", dialogo.content.controls[-1].value)
        self.assertEqual(self.linhas()[0], (140_00, "2026-09-10", "parcial"))

    def test_cancelar_a_edicao_nao_muda_nada(self):
        self.quitar()
        self.abrir_detalhes()
        self.clicar(self.acao("pp_editar_", 1))
        self.campo("Valor do pagamento", self.dialogo().content).value = "10,00"
        self.clicar(self.acao_do_dialogo("Cancelar"))
        self.assertEqual(self.linhas(), [(150_00, "2026-09-10", "parcial"), (250_00, "2026-09-02", "parcial")])

    # -------------------------------------------------------------- estornar
    def test_estornar_o_pagamento_que_quitou(self):
        self.quitar()
        self.abrir_detalhes()
        coluna = self.pagina.controls[0]
        self.clicar(self.acao("pp_desfazer_", 2))
        self.assertEqual(self.dialogo().title.value, "Desfazer este pagamento?")
        self.assertEqual(self.estornos(), [(1, None), (2, None)])                 # nada antes de confirmar
        self.clicar(self.acao_do_dialogo("Desfazer pagamento"))
        self.assertEqual(self.estornos(), [(1, None), (2, "2026-09-15")])
        self.assertEqual(self.consultar("SELECT status, data_pagamento FROM contas"), [("pendente", None)])
        self.assertEqual(self.dialogo().title.value, "Pagamento desfeito")
        self.assertIs(self.pagina.controls[0], coluna)
        self.assertEqual(self.acoes_de_pagamento(), {"pp_editar_1", "pp_desfazer_1", "pp_excluir_2"})   # estornado: só excluir
        self.assertIn("Estornado em 15/09/2026", self.textos())
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 250,00")
        self.assertEqual(self.quitou(), [])
        self.sem_quitadas_sem_registro()

    def test_estornar_todos_um_a_um_e_inicio_coerente(self):
        self.quitar()
        self.abrir_detalhes()
        for pid in (1, 2):
            self.clicar(self.acao("pp_desfazer_", pid))
            self.clicar(self.acao_do_dialogo("Desfazer pagamento"))
        self.assertEqual(pagamentos.obter_situacao(self.conta)["pago_centavos"], 0)
        self.assertEqual(self.acoes_de_pagamento(), {"pp_excluir_1", "pp_excluir_2"})
        self.assertIn("Total pago: R$ 0,00", self.textos())
        self.sem_quitadas_sem_registro()
        self.clicar(self.botao("Voltar"))
        self.assertIn("pago R$ 0,00", self.textos())
        self.assertIn("pendente R$ 400,00", self.textos())

    def test_estornar_desatualizado_e_cancelar(self):
        self.quitar()
        self.abrir_detalhes()
        self.clicar(self.acao("pp_desfazer_", 1))
        self.clicar(self.acao_do_dialogo("Cancelar"))
        self.assertEqual(self.estornos(), [(1, None), (2, None)])
        self.clicar(self.acao("pp_desfazer_", 1))
        pagamentos.estornar_pagamento(1, (150_00, "2026-09-10"))                 # outra janela
        self.clicar(self.acao_do_dialogo("Desfazer pagamento"))
        self.assertEqual(self.dialogo().title.value, "Nada foi desfeito")
        self.assertTrue(self.na_tela_de_detalhes())
        self.assertEqual(self.acoes_de_pagamento(), {"pp_editar_2", "pp_desfazer_2", "pp_excluir_1"})   # tela já atualizada

    # ------------------------------------------- coerência com as demais telas
    def test_pagamento_parcial_e_quitacao_continuam_e_ganham_acoes(self):
        self.abrir_detalhes()
        self.pagar_parcialmente("100,00")
        self.assertEqual(self.acoes_de_pagamento(), {"pp_editar_1", "pp_desfazer_1"})
        self.clicar(self.botao("Marcar como paga"))
        self.clicar(self.acao_do_dialogo("Pagar R$ 300,00"))
        self.assertEqual(self.linhas()[-1], (300_00, "2026-09-15", "saldo"))      # data de hoje
        self.assertEqual(self.quitou(), [2])
        self.sem_quitadas_sem_registro()

    def test_redimensionar_mantem_as_acoes(self):
        self.quitar()
        self.abrir_detalhes()
        self.pagina.width = 900
        self.pagina.on_resize(None)
        self.assertEqual(self.acoes_de_pagamento(), {"pp_editar_1", "pp_desfazer_1", "pp_editar_2", "pp_desfazer_2"})
        linha = next(c for c in self.controles(ft.Container) if c.data == "pp_pagamento_1")
        self.assertIsInstance(linha.content.controls[-1], ft.Row)                 # largo: valor e ícones lado a lado

    def test_editar_conta_sem_acoes_de_pagamento(self):
        self.quitar()
        self.abrir_detalhes()
        self.clicar(self.botao("Editar"))
        self.assertEqual(self.acoes_de_pagamento(), set())
        self.assertEqual(self.quitou(), [])
        self.clicar(self.botao("Cancelar"))
        self.assertTrue(self.na_tela_de_detalhes())
        self.assertEqual(self.quitou(), [2])


class TestEditarDadosGerais(TesteInterfacePagamentos):
    """Reorganização, etapa 2: Editar conta só com os dados gerais e uma linha só
    de leitura com o total pago e o saldo devedor GRAVADOS; pagar, desmarcar,
    corrigir e estornar ficam nos Detalhes e no Início. O diálogo da diferença
    continua. Hoje fixo: 15/09/2026."""

    ACOES_REMOVIDAS = ("Marcar como paga", "Marcar como pendente", "Alterar data de pagamento",
                       "Desfazer esta alteração")

    def editar(self, nome="Internet"):
        self.abrir_detalhes(nome)
        self.clicar(self.botao("Editar"))

    def caixa_do_resumo(self):
        return next(c for c in self.controles(ft.Container) if c.data == "pp_resumo_edicao")

    def resumo(self):
        """O resumo como a usuária o lê: "Total pago: X · <rótulo do saldo>: Y"."""
        t = {c.data: c.value for c in percorrer(self.caixa_do_resumo()) if isinstance(c, ft.Text) and c.data}
        return f"Total pago: {t['pp_valor_pago_edicao']} · {t['pp_rotulo_saldo_edicao']}: {t['pp_valor_saldo_edicao']}"

    def nota(self):
        return next(c for c in self.controles(ft.Text) if c.data == "pp_nota_resumo_edicao")

    def mudar(self, rotulo, valor):
        campo = self.campo(rotulo)
        campo.value = valor
        campo.on_change(Evento(self.pagina, campo))

    def sem_quitadas_sem_registro(self):
        self.assertEqual(self.consultar(
            "SELECT COUNT(*) FROM contas c WHERE status = 'pago' AND NOT EXISTS (SELECT 1 FROM pp_pagamentos p "
            "WHERE p.conta_id = c.id AND p.estornado_em IS NULL)")[0][0], 0)

    def conferir_editar_sem_financeiro(self):
        textos = self.textos()
        for texto in ("Status", "Pagamentos registrados"):
            self.assertNotIn(texto, textos)
        for acao in self.ACOES_REMOVIDAS:
            self.assertFalse(self.tem_botao(acao), acao)
        self.assertEqual([b.data for b in self.controles(ft.IconButton) if (b.data or "").startswith("pp_")], [])
        self.assertFalse(any(c.data == "pp_pagamentos_edicao" for c in self.controles(ft.Container)))
        for rotulo in ("Nome da conta", "Valor", "Data de vencimento", "Categoria", "Recorrência",
                       "Descrição (opcional)"):
            self.assertTrue(self.campo(rotulo))

    # ------------------------------------------------------------- estrutura
    def situacao(self):
        s = pagamentos.obter_situacao(self.conta)
        return s["pago_centavos"], s["saldo_centavos"], s["status"]

    def test_editar_sem_acoes_financeiras_em_qualquer_situacao(self):
        situacoes, resumos = [], []
        self.editar()
        situacoes.append(self.situacao())
        resumos.append(self.resumo())
        self.conferir_editar_sem_financeiro()
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        self.editar()
        situacoes.append(self.situacao())
        resumos.append(self.resumo())
        self.conferir_editar_sem_financeiro()
        db.marcar_conta_como_paga(self.conta)
        self.editar()
        situacoes.append(self.situacao())
        resumos.append(self.resumo())
        self.conferir_editar_sem_financeiro()
        self.assertEqual(situacoes, [(0, 400_00, "pendente"), (150_00, 250_00, "pendente"), (400_00, 0, "pago")])
        self.assertEqual(resumos, ["Total pago: R$ 0,00 · Saldo devedor: R$ 400,00",
                                   "Total pago: R$ 150,00 · Saldo devedor: R$ 250,00",
                                   "Total pago: R$ 400,00 · Saldo devedor: R$ 0,00"])

    def test_resumo_em_conteiner_depois_dos_dados_gerais_e_so_leitura(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        self.editar()
        grade = next(c for c in self.controles(ft.ResponsiveRow) if c.data == "pp_grade_edicao")
        self.assertIs(grade.controls[-1].content, self.caixa_do_resumo())          # duas colunas: por último
        caixa = self.caixa_do_resumo()
        self.assertEqual(caixa.border_radius, main.RAIO_EDICAO)                   # o raio dos campos de Editar
        self.assertIsNotNone(caixa.bgcolor)
        textos = [c.value for c in percorrer(caixa) if isinstance(c, ft.Text) and c.visible is not False]
        self.assertEqual(textos, ["Resumo dos pagamentos", "Total pago", "R$ 150,00", "Saldo devedor", "R$ 250,00"])
        self.assertFalse(any(isinstance(c, (ft.Button, ft.TextButton, ft.IconButton, ft.TextField, ft.Dropdown))
                             or getattr(c, "on_click", None) for c in percorrer(caixa)))

    def test_previa_do_saldo_devedor(self):
        self.executar("UPDATE contas SET valor = 200.0 WHERE id = ?", (self.conta,))
        db.marcar_conta_como_paga(self.conta, "2026-09-10")                      # exemplo: 200 pagos de 200
        antes = (self.consultar("SELECT * FROM contas"), self.consultar("SELECT * FROM pp_pagamentos"))
        self.editar()
        self.assertEqual(self.resumo(), "Total pago: R$ 200,00 · Saldo devedor: R$ 0,00")
        self.assertFalse(self.nota().visible)
        previa = "Prévia considerando o novo valor. Nenhuma alteração foi salva."
        invalido = "Informe um valor válido para ver o saldo devedor previsto."
        casos = [("250,00", "Total pago: R$ 200,00 · Saldo devedor previsto: R$ 50,00", previa),
                 ("250,1", "Total pago: R$ 200,00 · Saldo devedor previsto: R$ 50,10", previa),
                 ("1.200", "Total pago: R$ 200,00 · Saldo devedor previsto: R$ 1.000,00", previa),
                 ("", "Total pago: R$ 200,00 · Saldo devedor: R$ 0,00", invalido),
                 ("25x", "Total pago: R$ 200,00 · Saldo devedor: R$ 0,00", invalido),
                 ("0", "Total pago: R$ 200,00 · Saldo devedor: R$ 0,00", invalido),
                 ("150", "Total pago: R$ 200,00 · Saldo devedor previsto: —",
                  "O novo valor é menor que o total pago (R$ 200,00) e não poderá ser salvo.")]
        for digitado, resumo, nota in casos:
            with self.subTest(digitado=digitado):
                self.mudar("Valor", digitado)
                self.assertEqual(self.resumo(), resumo)
                self.assertTrue(self.nota().visible)
                self.assertEqual(self.nota().value, nota)
        self.mudar("Valor", "200")                                                # valor original de volta
        self.assertEqual(self.resumo(), "Total pago: R$ 200,00 · Saldo devedor: R$ 0,00")
        self.assertFalse(self.nota().visible)
        self.mudar("Nome da conta", "Internet casa")                              # outro campo: sem prévia
        self.assertFalse(self.nota().visible)
        self.assertEqual((self.consultar("SELECT * FROM contas"), self.consultar("SELECT * FROM pp_pagamentos")),
                         antes)                                                   # nada gravado

    def test_previa_nao_substitui_o_dialogo_da_diferenca(self):
        self.executar("UPDATE contas SET valor = 200.0 WHERE id = ?", (self.conta,))
        db.marcar_conta_como_paga(self.conta, "2026-09-10")
        self.editar()
        self.mudar("Valor", "250,00")
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.dialogo().title.value, "Como deseja registrar a diferença?")
        self.assertEqual(self.consultar("SELECT valor FROM contas"), [(200.0,)])

    def test_previa_em_conta_parcial_e_salvar_normal(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        self.editar()
        self.mudar("Valor", "500,00")
        self.assertEqual(self.resumo(), "Total pago: R$ 150,00 · Saldo devedor previsto: R$ 350,00")
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.dialogo().title.value, "Alteração salva")             # sem diálogo da diferença
        self.assertEqual(pagamentos.obter_situacao(self.conta)["saldo_centavos"], 350_00)
        self.assertEqual(self.linhas(), [(150_00, "2026-09-05", "parcial")])

    def test_conta_paga_legada(self):
        self.executar("UPDATE contas SET status = 'pago', data_pagamento = '2026-09-02' WHERE id = ?", (self.conta,))
        self.editar()
        self.conferir_editar_sem_financeiro()
        self.assertEqual(self.situacao(), (400_00, 0, "pago"))                       # legado: pago sem registros
        self.assertEqual(self.resumo(), "Total pago: R$ 400,00 · Saldo devedor: R$ 0,00")
        self.mudar("Nome da conta", "Internet casa")
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.consultar("SELECT nome, status, data_pagamento FROM contas"),
                         [("Internet casa", "pago", "2026-09-02")])               # nada convertido
        self.assertEqual(self.linhas(), [])

    def test_salvar_dados_gerais_nao_toca_nos_pagamentos(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        db.marcar_conta_como_paga(self.conta)
        antes = self.consultar("SELECT * FROM pp_pagamentos ORDER BY id")
        self.editar()
        self.mudar("Nome da conta", "Internet casa")
        self.mudar("Descrição (opcional)", "Fibra")
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.dialogo().title.value, "Alteração salva")
        self.assertEqual(self.consultar("SELECT nome, descricao, status, data_pagamento FROM contas"),
                         [("Internet casa", "Fibra", "pago", "2026-09-15")])
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"), antes)

    # ------------------------------------------------------- diferença de valor
    def preparar_exemplo(self, vencimento="2026-09-20"):
        """Exemplo da autora: conta de R$ 100 quitada com R$ 100 pagos."""
        self.executar("UPDATE contas SET valor = 100.0, data_vencimento = ? WHERE id = ?", (vencimento, self.conta))
        db.marcar_conta_como_paga(self.conta, "2026-09-10")
        self.editar()
        self.mudar("Valor", "150,00")
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.dialogo().title.value, "Como deseja registrar a diferença?")

    def test_diferenca_registrada_como_paga(self):
        self.preparar_exemplo()
        self.clicar(self.opcao_diferenca("registrar"))
        self.clicar(self.acao_do_dialogo("Confirmar"))
        self.assertEqual(self.dialogo().title.value, "Alteração salva")
        self.assertEqual(self.linhas(), [(100_00, "2026-09-10", "integral"), (50_00, "2026-09-15", "saldo")])
        situacao = pagamentos.obter_situacao(self.conta)
        self.assertEqual((situacao["valor_centavos"], situacao["pago_centavos"], situacao["status"]),
                         (150_00, 150_00, "pago"))
        self.sem_quitadas_sem_registro()

    def test_diferenca_mantida_em_aberto(self):
        for vencimento, status in (("2026-09-20", "pendente"), ("2026-09-01", "atrasado")):
            with self.subTest(vencimento=vencimento):
                self.executar("DELETE FROM pp_pagamentos")
                self.preparar_exemplo(vencimento)
                self.clicar(self.opcao_diferenca("aberto"))
                self.clicar(self.acao_do_dialogo("Confirmar"))
                self.assertEqual(self.linhas(), [(100_00, "2026-09-10", "integral")])
                situacao = pagamentos.obter_situacao(self.conta)
                self.assertEqual((situacao["valor_centavos"], situacao["pago_centavos"],
                                  situacao["saldo_centavos"], situacao["status"]), (150_00, 100_00, 50_00, status))
                self.sem_quitadas_sem_registro()

    def test_diferenca_cancelada_nao_grava(self):
        self.preparar_exemplo()
        self.clicar(self.opcao_diferenca("registrar"))
        self.clicar(self.acao_do_dialogo("Cancelar"))
        self.assertEqual(self.consultar("SELECT valor, status FROM contas"), [(100.0, "pago")])
        self.assertEqual(self.linhas(), [(100_00, "2026-09-10", "integral")])
        self.assertEqual(self.campo("Valor").value, "150,00")                    # o rascunho continua

    def test_diferenca_desatualizada_nao_grava(self):
        self.preparar_exemplo()
        self.clicar(self.opcao_diferenca("registrar"))
        pid = self.consultar("SELECT id FROM pp_pagamentos")[0][0]
        pagamentos.editar_pagamento(pid, 90_00, "2026-09-10", (100_00, "2026-09-10"))   # outra janela
        self.clicar(self.acao_do_dialogo("Confirmar"))
        self.assertEqual(self.dialogo().title.value, "Nada foi alterado")
        self.assertEqual(self.consultar("SELECT valor FROM contas"), [(100.0,)])
        self.assertEqual(self.linhas(), [(90_00, "2026-09-10", "integral")])

    def test_diferenca_na_serie_somente_este_mes_e_este_mes_em_diante(self):
        for escopo, valores in (("Somente este mês", [150.0, 100.0, 100.0, 100.0]),
                                ("Este mês em diante", [150.0, 150.0, 100.0, 150.0])):
            with self.subTest(escopo=escopo):
                serie_id, ids = db.criar_serie_recorrente(self.usuario_id, f"Academia {escopo}", 100.0,
                                                          "2026-09-20", "mensal", data_termino="2026-12")
                db.marcar_conta_como_paga(ids[0], "2026-09-10")
                pagamentos.registrar_pagamento_parcial(ids[2], 30_00, "2026-09-06")   # novembro: com histórico
                self.editar(f"Academia {escopo}")
                self.mudar("Valor", "150,00")
                self.clicar(self.botao("Salvar alterações"))
                self.clicar(self.opcao_diferenca("registrar"))
                self.clicar(self.acao_do_dialogo("Confirmar"))
                self.clicar(self.acao_do_dialogo(escopo))
                self.assertEqual(self.dialogo().title.value, "Alteração salva")
                self.assertEqual([v for (v,) in self.consultar(
                    "SELECT valor FROM contas WHERE serie_id = ? ORDER BY posicao", (serie_id,))], valores)
                selecionada = pagamentos.obter_situacao(ids[0])
                self.assertEqual((selecionada["pago_centavos"], selecionada["status"]), (150_00, "pago"))
                self.assertEqual(pagamentos.obter_situacao(ids[2])["pago_centavos"], 30_00)
                self.sem_quitadas_sem_registro()

    def test_valor_abaixo_do_pago_continua_recusado(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 250_00, "2026-09-05")
        self.editar()
        self.mudar("Valor", "200,00")
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.dialogo().title.value, db.ValorMenorQuePagoError(250_00).titulo)
        self.assertEqual(self.consultar("SELECT valor FROM contas"), [(400.0,)])

    def test_valor_igual_ao_pago_quita_com_os_registros(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 250_00, "2026-09-05")
        self.editar()
        self.mudar("Valor", "250,00")
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.consultar("SELECT status, data_pagamento FROM contas"), [("pago", "2026-09-05")])
        self.sem_quitadas_sem_registro()


class TestRefinamentosDeLinguagem(TesteInterfacePagamentos):
    """Reorganização, etapa 2: confirmação conforme o que mudou no pagamento,
    "Valor a pagar" com o limite sempre visível e "Saldo devedor". Hoje fixo:
    15/09/2026."""

    def setUp(self):
        super().setUp()
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-05")

    def editar_pagamento(self, valor=None, data=None):
        self.clicar(next(b for b in self.controles(ft.IconButton) if b.data == "pp_editar_1"))
        dialogo = self.dialogo()
        if valor is not None:
            self.campo("Valor do pagamento", dialogo.content).value = valor
        if data is not None:
            self.campo("Data do pagamento", dialogo.content).value = data
        self.clicar(self.acao_do_dialogo("Salvar"))
        return dialogo

    def test_confirmacao_conforme_o_que_mudou(self):
        self.abrir_detalhes()
        casos = [
            ((None, "07/09/2026"), "Data do pagamento alterada",
             "A data do pagamento foi alterada para 07/09/2026.\n\nA conta ficou com R$ 100,00 pagos e "
             "R$ 300,00 em aberto."),
            (("120,00", None), "Valor do pagamento alterado",
             "O valor do pagamento foi alterado de R$ 100,00 para R$ 120,00.\n\nA conta ficou com R$ 120,00 pagos "
             "e R$ 280,00 em aberto."),
            (("130", "08/09/2026"), "Pagamento atualizado",
             "O pagamento foi alterado para R$ 130,00, em 08/09/2026.\n\nA conta ficou com R$ 130,00 pagos e "
             "R$ 270,00 em aberto."),
        ]
        for (valor, data), titulo, mensagem in casos:
            with self.subTest(titulo=titulo):
                self.editar_pagamento(valor, data)
                self.assertEqual((self.dialogo().title.value, self.dialogo().content.value), (titulo, mensagem))
        self.assertEqual(self.linhas(), [(130_00, "2026-09-08", "parcial")])

    def test_sem_mudanca_efetiva_nao_confirma(self):
        self.abrir_detalhes()
        exibidos = self.pagina.show_dialog.call_count
        self.editar_pagamento("100", "05/09/2026")                                 # "100" == "100,00"
        self.assertEqual(self.pagina.show_dialog.call_count, exibidos + 1)          # só o próprio diálogo
        self.pagina.pop_dialog.assert_called()
        self.assertEqual(self.linhas(), [(100_00, "2026-09-05", "parcial")])

    def test_valor_a_pagar_com_limite_sempre_visivel(self):
        self.abrir_detalhes()
        self.clicar(self.botao("Registrar pagamento parcial"))
        campo = self.campo("Valor a pagar", self.dialogo().content)
        self.assertEqual(campo.helper, "Valor máximo: R$ 300,00")                  # helper: com ou sem foco
        self.assertIsNone(campo.hint_text)
        self.assertIn("Saldo devedor", self.textos_do_dialogo())
        self.assertNotIn("Valor pago", [getattr(c, "label", None) for c in percorrer(self.dialogo().content)])
        campo.value = "300,01"
        self.clicar(self.acao_do_dialogo("Registrar pagamento"))
        self.assertIn("O valor é maior que o saldo devedor (R$ 300,00).", self.textos_do_dialogo())
        self.assertEqual(len(self.linhas()), 1)
        campo.value = "50"
        self.clicar(self.acao_do_dialogo("Registrar pagamento"))
        self.assertIn("Saldo devedor: R$ 250,00.", self.dialogo().content.value)
        self.clicar(self.botao("Registrar pagamento parcial"))
        self.assertEqual(self.campo("Valor a pagar", self.dialogo().content).helper, "Valor máximo: R$ 250,00")

    def test_saldo_devedor_nos_detalhes_e_no_pagamento_do_saldo(self):
        self.abrir_detalhes()
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 300,00")
        self.assertNotIn("Saldo restante", self.textos())
        self.clicar(self.botao("Marcar como paga"))
        self.assertIn("Será registrado só o saldo devedor, R$ 300,00", self.dialogo().content.value)


class TestClassificacaoDinamica(TesteInterfacePagamentos):
    """Etapa 3, melhoria 4: o rótulo do histórico é calculado na leitura, pela
    ordem de registro (id), sem regravar o `tipo` (a origem). Ativos: único que
    cobre o valor = integral; o que completou a quitação depois de outros = do
    saldo; demais = parcial. Estornados: rótulo de origem. Hoje fixo: 15/09/2026."""

    def rotulos(self):
        """[(id, rótulo exibido, "Conta quitada"?)] na ordem do histórico."""
        self.abrir_detalhes()
        linhas = [c for c in self.controles(ft.Container) if (c.data or "").startswith("pp_pagamento_")]
        resultado = []
        for linha in linhas:
            textos = [t for t in percorrer(linha) if isinstance(t, ft.Text)]
            resultado.append((int(linha.data.split("_")[-1]), textos[1].value,
                              any(t.data == "pp_quitou" for t in textos)))
        return resultado

    def tipos(self):
        return [t for (t,) in self.consultar("SELECT tipo FROM pp_pagamentos ORDER BY id")]

    def test_um_pagamento_integral(self):
        db.marcar_conta_como_paga(self.conta, "2026-09-10")
        self.assertEqual(self.rotulos(), [(1, "Pagamento integral", True)])

    def test_varios_parciais_em_aberto(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-10")
        self.assertEqual(self.rotulos(), [(1, "Pagamento parcial", False), (2, "Pagamento parcial", False)])

    def test_parcial_que_completa_vira_pagamento_do_saldo(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        pagamentos.registrar_pagamento_parcial(self.conta, 250_00, "2026-09-10")   # gravado como 'parcial'
        self.assertEqual(self.rotulos(), [(1, "Pagamento parcial", False), (2, "Pagamento do saldo", True)])
        self.assertEqual(self.tipos(), ["parcial", "parcial"])                      # o banco não muda

    def test_parcial_unico_que_cobre_o_valor_e_integral(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 400_00, "2026-09-05")
        self.assertEqual(self.rotulos(), [(1, "Pagamento integral", True)])
        self.assertEqual(self.tipos(), ["integral"])                                # já gravado assim na origem

    def test_exemplo_da_autora_integral_editado_para_menos(self):
        self.executar("UPDATE contas SET valor = 200.0 WHERE id = ?", (self.conta,))
        db.marcar_conta_como_paga(self.conta, "2026-09-10")
        pagamentos.editar_pagamento(1, 150_00, "2026-09-10", (200_00, "2026-09-10"))
        self.assertEqual(self.rotulos(), [(1, "Pagamento parcial", False)])
        self.assertEqual(self.tipos(), ["integral"])

    def test_edicao_que_reabre_a_conta(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        db.marcar_conta_como_paga(self.conta)                                       # 'saldo' de 250
        pagamentos.editar_pagamento(2, 200_00, "2026-09-15", (250_00, "2026-09-15"))
        self.assertEqual(self.rotulos(), [(1, "Pagamento parcial", False), (2, "Pagamento parcial", False)])
        self.assertEqual(self.tipos(), ["parcial", "saldo"])

    def test_estorno_do_pagamento_que_quitou(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        db.marcar_conta_como_paga(self.conta)
        pagamentos.estornar_pagamento(2, (250_00, "2026-09-15"))
        self.assertEqual(self.rotulos(), [(1, "Pagamento parcial", False), (2, "Pagamento do saldo", False)])
        self.assertIn("Estornado em 15/09/2026", self.textos())                     # rótulo de origem

    def test_estornado_mantem_a_origem_mesmo_que_o_ativo_mude(self):
        db.marcar_conta_como_paga(self.conta, "2026-09-10")                        # 'integral'
        pagamentos.estornar_pagamento(1, (400_00, "2026-09-10"))
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-12")
        self.assertEqual(self.rotulos(), [(1, "Pagamento integral", False), (2, "Pagamento parcial", False)])

    def test_unico_ativo_restante_que_cobre_o_valor(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-10")
        pagamentos.estornar_pagamento(1, (150_00, "2026-09-05"))
        pagamentos.editar_pagamento(2, 400_00, "2026-09-10", (100_00, "2026-09-10"))
        self.assertEqual(self.rotulos(), [(1, "Pagamento parcial", False), (2, "Pagamento integral", True)])

    def test_ordem_de_registro_e_nao_a_data(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-12")
        pagamentos.registrar_pagamento_parcial(self.conta, 250_00, "2026-09-02")   # lançado depois, data menor
        self.assertEqual(self.rotulos(), [(2, "Pagamento do saldo", True), (1, "Pagamento parcial", False)])

    def test_diferenca_registrada_e_mantida_em_aberto(self):
        self.executar("UPDATE contas SET valor = 100.0 WHERE id = ?", (self.conta,))
        db.marcar_conta_como_paga(self.conta, "2026-09-10")
        db.editar_conta_ocorrencia(self.conta, valor=150.0,
                                   pp_diferenca={"registrar": True, "esperado": (100_00, 100_00)})
        self.assertEqual(self.rotulos(), [(1, "Pagamento parcial", False), (2, "Pagamento do saldo", True)])
        self.assertEqual(self.tipos(), ["integral", "saldo"])

    def test_diferenca_em_aberto(self):
        self.executar("UPDATE contas SET valor = 100.0 WHERE id = ?", (self.conta,))
        db.marcar_conta_como_paga(self.conta, "2026-09-10")
        db.editar_conta_ocorrencia(self.conta, valor=150.0,
                                   pp_diferenca={"registrar": False, "esperado": (100_00, 100_00)})
        self.assertEqual(self.rotulos(), [(1, "Pagamento parcial", False)])

    def test_banco_intacto_em_todos_os_passos(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-12")
        pagamentos.registrar_pagamento_parcial(self.conta, 250_00, "2026-09-02")
        antes = self.consultar("SELECT * FROM pp_pagamentos ORDER BY id")
        conta = self.consultar("SELECT * FROM contas")
        self.rotulos()
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"), antes)
        self.assertEqual(self.consultar("SELECT * FROM contas"), conta)


class TestExcluirEstornadoNosDetalhes(TesteInterfacePagamentos):
    """Etapa 3, alternativa C: lixeira só nos estornados, confirmação obrigatória
    e exclusão definitiva sem mudar o financeiro. Hoje fixo: 15/09/2026."""

    def setUp(self):
        super().setUp()
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00, "2026-09-05")
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-10")
        pagamentos.estornar_pagamento(2, (100_00, "2026-09-10"))

    def acoes(self):
        return {b.data for b in self.controles(ft.IconButton) if (b.data or "").startswith("pp_")}

    def lixeira(self, pid=2):
        return next(b for b in self.controles(ft.IconButton) if b.data == f"pp_excluir_{pid}")

    def financeiro(self):
        s = pagamentos.obter_situacao(self.conta)
        return s["pago_centavos"], s["saldo_centavos"], s["status"], [p["id"] for p in s["ativos"]]

    def test_lixeira_so_no_estornado_e_sem_lapis(self):
        self.abrir_detalhes()
        self.assertEqual(self.acoes(), {"pp_editar_1", "pp_desfazer_1", "pp_excluir_2"})
        lixeira = self.lixeira()
        self.assertEqual(lixeira.tooltip, "Excluir registro estornado")
        self.assertEqual(lixeira.icon.semantics_label, "Excluir registro estornado de R$ 100,00 em 10/09/2026")
        linha = next(c for c in self.controles(ft.Container) if c.data == "pp_pagamento_2")
        valor = next(t for t in percorrer(linha) if isinstance(t, ft.Text) and t.value == "R$ 100,00")
        self.assertEqual(valor.style.decoration, ft.TextDecoration.LINE_THROUGH)  # continua riscado

    def test_confirmacao_e_cancelar(self):
        self.abrir_detalhes()
        antes = self.consultar("SELECT * FROM pp_pagamentos ORDER BY id")
        self.clicar(self.lixeira())
        self.assertEqual(self.dialogo().title.value, "Excluir registro estornado?")
        self.assertEqual(self.dialogo().content.value, "Este registro será excluído permanentemente do histórico de "
                                                       "pagamentos. A exclusão não alterará o saldo da conta.")
        self.assertEqual([b.content for b in self.dialogo().actions], ["Cancelar", "Excluir definitivamente"])
        self.clicar(self.acao_do_dialogo("Cancelar"))
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"), antes)

    def test_excluir_definitivamente(self):
        self.abrir_detalhes()
        coluna = self.pagina.controls[0]
        antes = self.financeiro()
        exibidos = self.pagina.show_dialog.call_count
        self.clicar(self.lixeira())
        self.clicar(self.acao_do_dialogo("Excluir definitivamente"))
        self.assertEqual(self.estornos(), [(1, None)])                             # o registro sumiu do banco
        self.assertEqual(self.financeiro(), antes)
        self.assertEqual(self.consultar("SELECT name FROM sqlite_master WHERE name = 'pp_contas_com_historico'"),
                         [])                                                       # sem marca (simplificação)
        self.assertIs(self.pagina.controls[0], coluna)                             # redesenha no lugar
        self.assertNotIn("Estornado em 15/09/2026", self.textos())
        self.assertFalse(any(c.data == "pp_pagamento_2" for c in self.controles(ft.Container)))
        self.assertEqual(self.acoes(), {"pp_editar_1", "pp_desfazer_1"})
        self.assertIn("Total pago: R$ 150,00", self.textos())
        self.assertEqual(self.valor_ao_lado("Saldo devedor"), "R$ 250,00")
        self.assertEqual(self.pagina.show_dialog.call_count, exibidos + 1)         # sem aviso extra

    def test_ultimo_registro_deixa_o_historico_vazio(self):
        pagamentos.estornar_pagamento(1, (150_00, "2026-09-05"))
        self.abrir_detalhes()
        for pid in (1, 2):
            self.clicar(self.lixeira(pid))
            self.clicar(self.acao_do_dialogo("Excluir definitivamente"))
        self.assertIn("Nenhum pagamento registrado.", self.textos())
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM pp_pagamentos"), [(0,)])
        conexao = db.conectar()
        try:                                                                       # sem registros, sem proteção
            self.assertEqual(db._contas_com_pagamentos(conexao.cursor(), "id = ?", (self.conta,)), [])
        finally:
            conexao.close()
        self.assertEqual(self.financeiro(), (0, 400_00, "pendente", []))

    def test_excluido_por_outra_janela(self):
        self.abrir_detalhes()
        self.clicar(self.lixeira())
        pagamentos.excluir_estornado(2, self.conta)                                 # outra janela
        self.clicar(self.acao_do_dialogo("Excluir definitivamente"))
        self.assertEqual(self.dialogo().title.value, "Nada foi excluído")
        self.assertFalse(any(c.data == "pp_pagamento_2" for c in self.controles(ft.Container)))  # tela atualizada

    def test_largo_icone_ao_lado_e_estreito_abaixo(self):
        self.abrir_detalhes()
        linha = next(c for c in self.controles(ft.Container) if c.data == "pp_pagamento_2")
        self.assertIsInstance(linha.content.controls[-1], ft.Column)               # 380: abaixo do valor
        self.pagina.width = 900
        self.pagina.on_resize(None)
        linha = next(c for c in self.controles(ft.Container) if c.data == "pp_pagamento_2")
        self.assertIsInstance(linha.content.controls[-1], ft.Row)                  # largo: ao lado

    def test_classificacao_depois_de_excluir(self):
        db.marcar_conta_como_paga(self.conta)                                      # 150 + saldo 250
        self.abrir_detalhes()
        self.clicar(self.lixeira())
        self.clicar(self.acao_do_dialogo("Excluir definitivamente"))
        historico = self.historico()
        self.assertEqual(historico[historico.index("05/09/2026"):][:2], ["05/09/2026", "Pagamento parcial"])
        self.assertIn("Pagamento do saldo", historico)
        self.assertIn("Conta quitada", historico)


class TestVisualEditar(TesteInterfacePagamentos):
    """Refinamento visual de Editar conta (28/10): título do resumo com o mês e o
    ano da ocorrência (vencimento gravado, nunca o mês do sistema nem o do
    pagamento), Total pago e Saldo lado a lado só com largura, barra fixa com
    Cancelar e Salvar fora da área rolável e campos com o mesmo raio e bordas.
    Nada financeiro muda. Hoje fixo: 15/09/2026."""

    def editar(self, nome="Internet"):
        self.abrir_detalhes(nome)
        self.clicar(self.botao("Editar"))

    def titulo(self):
        texto = next(c for c in self.controles(ft.Text) if c.data == "pp_titulo_resumo_edicao")
        visivel = (texto.value + "".join(s.text for s in texto.spans)).replace(" ", " ")
        self.assertEqual(texto.semantics_label, visivel)                      # leitor de tela lê o mesmo
        return visivel

    def mudar(self, rotulo, valor):
        campo = self.campo(rotulo)
        campo.value = valor
        campo.on_change(Evento(self.pagina, campo))

    def raiz(self):
        self.assertEqual(len(self.pagina.controls), 1)
        return self.pagina.controls[0]

    def rodape(self):
        return next(c for c in self.controles(ft.Container) if c.data == "pp_rodape_edicao")

    # --------------------------------------------------------- mês e ano
    def test_competencia_pelo_vencimento(self):
        self.assertEqual(main.competencia_da_ocorrencia("2026-10-31"), "Outubro de 2026")
        self.assertEqual(main.competencia_da_ocorrencia("2026-11-01"), "Novembro de 2026")
        self.assertEqual(main.competencia_da_ocorrencia("2027-01-15"), "Janeiro de 2027")

    def test_titulo_da_conta_avulsa(self):
        self.editar()
        self.assertEqual(self.titulo(), "Resumo dos pagamentos — Setembro de 2026")

    def test_titulo_de_outro_mes_nao_usa_o_mes_atual(self):
        db.criar_conta_unica(self.usuario_id, "Seguro", 90.0, "2026-11-05")
        self.entrar()
        self.clicar(next(b for b in self.controles(ft.IconButton) if b.data == "proximo_mes"))
        self.clicar(next(b for b in self.controles(ft.IconButton) if b.data == "proximo_mes"))
        self.clicar(self.linha_da_conta("Seguro"))
        self.clicar(self.botao("Editar"))
        self.assertEqual(self.titulo(), "Resumo dos pagamentos — Novembro de 2026")   # hoje é setembro

    def test_titulo_nao_segue_o_mes_do_pagamento(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-08-30")   # pago antes, em agosto
        self.editar()
        self.assertEqual(self.titulo(), "Resumo dos pagamentos — Setembro de 2026")

    def test_titulo_de_cada_ocorrencia_recorrente(self):
        db.criar_serie_recorrente(self.usuario_id, "Academia", 120.0, "2026-09-10", "mensal")
        self.editar("Academia")
        self.assertEqual(self.titulo(), "Resumo dos pagamentos — Setembro de 2026")
        self.entrar()
        self.clicar(next(b for b in self.controles(ft.IconButton) if b.data == "proximo_mes"))
        self.clicar(self.linha_da_conta("Academia"))
        self.clicar(self.botao("Editar"))
        self.assertEqual(self.titulo(), "Resumo dos pagamentos — Outubro de 2026")
        self.assertEqual(self.campo("Data de vencimento").value, "10/10/2026")

    def test_titulo_e_resumo_ficam_no_gravado_durante_a_previa(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 150_00)
        self.editar()
        self.mudar("Valor", "500,00")
        self.assertEqual(self.titulo(), "Resumo dos pagamentos — Setembro de 2026")
        textos = {c.data: c.value for c in self.controles(ft.Text) if c.data}
        self.assertEqual((textos["pp_rotulo_saldo_edicao"], textos["pp_valor_saldo_edicao"]),
                         ("Saldo devedor previsto", "R$ 350,00"))
        self.assertEqual(textos["pp_nota_resumo_edicao"],
                         "Prévia considerando o novo valor. Nenhuma alteração foi salva.")
        self.assertEqual(self.consultar("SELECT valor FROM contas"), [(400.0,)])

    # --------------------------------------------------------- resumo
    def test_resumo_lado_a_lado_so_com_largura(self):
        self.editar()
        caixa = next(c for c in self.controles(ft.Container) if c.data == "pp_resumo_edicao")
        linha = next(c for c in percorrer(caixa) if isinstance(c, ft.ResponsiveRow))
        pago, traco, linha_horizontal, saldo = linha.controls
        self.assertEqual(linha.columns, 25)
        self.assertEqual(pago.col, {"xs": 25, "sm": 12})                     # estreito: um embaixo do outro
        self.assertEqual(saldo.col, {"xs": 25, "sm": 12})
        self.assertEqual(traco.col, {"xs": 0, "sm": 1})                      # traço vertical só lado a lado
        self.assertEqual(linha_horizontal.col, {"xs": 25, "sm": 0})          # e o horizontal só empilhado
        self.assertEqual(caixa.border_radius, main.RAIO_EDICAO)
        self.assertFalse(any(isinstance(c, (ft.Button, ft.TextButton, ft.IconButton, ft.TextField, ft.Dropdown))
                             or getattr(c, "on_click", None) for c in percorrer(caixa)))

    # --------------------------------------------------------- campos
    def test_campos_com_o_mesmo_raio_borda_e_fonte(self):
        self.editar()
        for rotulo in ("Nome da conta", "Valor", "Data de vencimento", "Categoria", "Descrição (opcional)"):
            with self.subTest(rotulo=rotulo):
                campo = self.campo(rotulo)
                self.assertEqual((campo.border_radius, campo.border_width, campo.focused_border_width,
                                  campo.text_size), (main.RAIO_EDICAO, 1, 2, 15))
        self.assertEqual(self.campo("Valor").value, "400,00")                 # "R$" é só o prefixo visual
        self.assertEqual(self.campo("Nome da conta").counter, "8/30")         # contadores mantidos
        self.assertEqual(self.campo("Descrição (opcional)").counter, "0/1000")

    # --------------------------------------------------------- barra inferior
    def test_botoes_na_barra_fixa_fora_da_area_rolavel(self):
        self.editar()
        raiz = self.raiz()
        self.assertEqual(raiz.data, "pp_editar_com_rodape")
        area, rodape = raiz.controls
        self.assertEqual(area.scroll, ft.ScrollMode.AUTO)
        self.assertTrue(area.expand)
        self.assertIs(rodape, self.rodape())
        botoes = [c.content for c in percorrer(rodape) if isinstance(c, ft.Button)]
        self.assertEqual(botoes, ["Cancelar", "Salvar alterações"])          # ordem do Tab: Cancelar, Salvar
        self.assertFalse(any(isinstance(c, ft.Button) for c in percorrer(area)))
        self.assertIn("Descrição (opcional)", [c.label for c in percorrer(area) if isinstance(c, ft.TextField)])

    def test_salvar_desabilitado_ate_haver_alteracao(self):
        self.editar()
        salvar = self.botao("Salvar alterações")
        self.assertTrue(salvar.disabled)
        self.mudar("Nome da conta", "Internet casa")
        self.assertFalse(salvar.disabled)
        self.mudar("Nome da conta", "Internet")
        self.assertTrue(salvar.disabled)

    def test_erro_de_valor_invalido_aparece_na_barra(self):
        self.editar()
        self.mudar("Valor", "abc")
        self.clicar(self.botao("Salvar alterações"))
        erros = [c.value for c in percorrer(self.rodape()) if isinstance(c, ft.Text) and c.value]
        self.assertEqual(erros, ["Informe um valor válido."])
        self.assertEqual(self.consultar("SELECT valor FROM contas"), [(400.0,)])

    def test_cancelar_nao_grava_e_volta_aos_detalhes(self):
        antes = self.consultar("SELECT * FROM contas")
        self.editar()
        self.mudar("Nome da conta", "Outro nome")
        self.mudar("Valor", "999,00")
        self.clicar(self.botao("Cancelar"))
        self.assertTrue(any(getattr(c, "data", None) == "tela_detalhes" for c in self.controles()))
        self.assertNotEqual(self.raiz().data, "pp_editar_com_rodape")        # Detalhes sem barra
        self.assertEqual(self.consultar("SELECT * FROM contas"), antes)

    def test_salvar_pela_barra_grava(self):
        self.editar()
        self.mudar("Nome da conta", "Internet casa")
        self.mudar("Valor", "450,00")
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.dialogo().title.value, "Alteração salva")
        self.assertEqual(self.consultar("SELECT nome, valor FROM contas"), [("Internet casa", 450.0)])


class TestEditarDuasColunas(TesteInterfacePagamentos):
    """Editar em duas colunas com lápis (28/10): Nome; Valor | Data; Categoria |
    Recorrência; Descrição; Resumo -- uma coluna abaixo de md, mesma ordem. Os
    campos continuam editáveis por si; o lápis é só um atalho para a MESMA ação
    (foco, calendário, lista, menu da Recorrência) e nunca salva. Hoje fixo:
    15/09/2026."""

    def editar(self, nome="Internet"):
        self.abrir_detalhes(nome)
        self.clicar(self.botao("Editar"))

    def grade(self):
        return next(c for c in self.controles(ft.ResponsiveRow) if c.data == "pp_grade_edicao")

    def celulas(self):
        """O controle de cada célula da grade (Categoria vem numa Row; Recorrência
        no contêiner que o rascunho recompõe; o resumo é o próprio contêiner)."""
        for item in self.grade().controls:
            c = item.content
            if isinstance(c, ft.Row):
                c = c.controls[0]
            elif isinstance(c, ft.Container) and c.data != "pp_resumo_edicao":
                c = c.content
            yield c, item.col

    def clicar_e_esperar(self, controle):
        resultado = controle.on_click(Evento(self.pagina, controle))
        if asyncio.iscoroutine(resultado):
            asyncio.run(resultado)

    def menu(self):
        return self.campo("Recorrência").suffix_icon

    def itens(self):
        return [i.content for i in self.menu().items]

    def conferir_lapis(self, lapis, nome):
        self.assertIsInstance(lapis, ft.IconButton)                         # focável: Tab e Enter/Espaço
        self.assertEqual((lapis.icon.icon, lapis.icon.semantics_label, lapis.tooltip),
                         (ft.Icons.EDIT_OUTLINED, nome, nome))

    # --------------------------------------------------------------- grade
    def test_duas_colunas_em_md_e_uma_abaixo(self):
        self.editar()
        conteudos = [(getattr(c, "label", None) or c.data, col) for c, col in self.celulas()]
        meia = {"xs": 12, "md": 6}
        self.assertEqual(conteudos, [("Nome da conta", 12), ("Valor", meia), ("Data de vencimento", meia),
                                     ("Categoria", meia), ("Recorrência", meia),
                                     ("Descrição (opcional)", 12), ("pp_resumo_edicao", 12)])

    def test_campos_continuam_editaveis_diretamente(self):
        self.editar()
        for rotulo in ("Nome da conta", "Valor", "Descrição (opcional)"):
            self.assertFalse(self.campo(rotulo).read_only, rotulo)
        self.assertIsNotNone(self.campo("Categoria").on_select)
        self.assertTrue(self.campo("Data de vencimento").read_only)            # como antes: só pelo calendário

    # --------------------------------------------------------------- lápis
    def test_lapis_de_nome_valor_e_descricao_so_poem_o_foco(self):
        antes = self.consultar("SELECT * FROM contas")
        self.editar()
        for rotulo, nome in (("Nome da conta", "Editar nome da conta"), ("Valor", "Editar valor"),
                             ("Descrição (opcional)", "Editar descrição")):
            with self.subTest(rotulo=rotulo):
                campo = self.campo(rotulo)
                self.conferir_lapis(campo.suffix_icon, nome)
                with mock.patch.object(type(campo), "focus", new_callable=mock.AsyncMock) as focar:
                    self.clicar_e_esperar(campo.suffix_icon)
                focar.assert_awaited_once()
        self.assertTrue(self.botao("Salvar alterações").disabled)              # nada mudou, nada salvo
        self.assertEqual(self.consultar("SELECT * FROM contas"), antes)

    def test_lapis_e_clique_da_data_abrem_o_calendario_de_sempre(self):
        self.editar()
        data = self.campo("Data de vencimento")
        self.conferir_lapis(data.suffix_icon, "Editar data de vencimento")
        self.clicar(data.suffix_icon)
        seletor = self.dialogo()
        self.assertIsInstance(seletor, ft.DatePicker)
        self.assertIn(seletor, self.pagina.overlay.append.call_args_list[-1][0])   # o mesmo seletor do overlay
        self.pagina.show_dialog.reset_mock()
        data.on_click(Evento(self.pagina, data))                                # clique no próprio campo
        self.assertIs(self.dialogo(), seletor)

    def test_lapis_da_categoria_no_botao_da_lista(self):
        self.editar()
        categoria = self.campo("Categoria")
        for icone, seta in ((categoria.trailing_icon, ft.Icons.ARROW_DROP_DOWN),
                            (categoria.selected_trailing_icon, ft.Icons.ARROW_DROP_UP)):
            self.assertIsInstance(icone, ft.Row)
            icones = [c for c in icone.controls if isinstance(c, ft.Icon)]
            self.assertEqual([i.icon for i in icones], [seta, ft.Icons.EDIT_OUTLINED])
            self.assertEqual(icones[1].semantics_label, "Editar categoria")

    # --------------------------------------------------------------- recorrência
    def test_recorrencia_avulsa_com_menu_transformar(self):
        self.editar()
        campo = self.campo("Recorrência")
        self.assertEqual(campo.value, main.TEXTO_NAO_RECORRENTE)
        self.assertTrue(campo.read_only)
        self.assertFalse(campo.can_request_focus)                              # o foco vai para o lápis
        self.assertIsInstance(self.menu(), ft.PopupMenuButton)
        self.assertEqual((self.menu().content.semantics_label, self.menu().tooltip),
                         ("Editar recorrência", "Editar recorrência"))
        self.assertEqual(self.itens(), ["Transformar em recorrente"])
        self.clicar(self.acao_da_recorrencia("Transformar em recorrente"))
        self.assertEqual(self.dialogo().title.value, "Transformar em recorrente")   # o diálogo de sempre

    def test_recorrencia_ativa_rascunho_e_desfazer(self):
        db.criar_serie_recorrente(self.usuario_id, "Academia", 100.0, "2026-09-10", "mensal", data_termino="2027-10")
        self.editar("Academia")
        self.assertEqual(self.campo("Recorrência").value, main.frase_recorrencia("mensal", "2027-10"))
        self.assertEqual(self.itens(), ["Alterar frequência", "Encerrar recorrência"])
        self.assertIsNone(self.campo("Recorrência").helper)
        self.clicar(self.acao_da_recorrencia("Encerrar recorrência"))
        self.assertEqual(self.dialogo().title.value, "Encerrar recorrência")
        self.clicar(self.acao_do_dialogo("Encerrar recorrência"))
        self.assertEqual(self.campo("Recorrência").value, main.TEXTO_NAO_RECORRENTE)   # prévia do rascunho
        self.assertEqual(self.campo("Recorrência").helper, "Alteração pendente: será aplicada ao salvar.")
        self.assertEqual(self.itens(), ["Transformar em recorrente", "Desfazer esta alteração"])
        self.assertFalse(self.botao("Salvar alterações").disabled)
        self.assertEqual(self.consultar("SELECT ativa FROM series_recorrencia"), [(1,)])  # nada gravado
        self.clicar(self.acao_da_recorrencia("Desfazer esta alteração"))
        self.assertEqual(self.itens(), ["Alterar frequência", "Encerrar recorrência"])
        self.assertTrue(self.botao("Salvar alterações").disabled)

    # --------------------------------------------------------------- teclado
    def test_ordem_do_tab_campo_e_seu_lapis(self):
        """A ordem de Tab segue a árvore: cada campo e, logo depois, o seu lápis
        (dentro do próprio campo); Recorrência só pelo lápis; a barra no fim."""
        self.editar()
        ordem = []
        for c, _ in self.celulas():
            if isinstance(c, ft.TextField):
                if c.can_request_focus is not False:
                    ordem.append(c.label)
                ordem.append(c.suffix_icon.tooltip)
            elif isinstance(c, ft.Dropdown):
                ordem.append(c.label)
        self.assertEqual(ordem, ["Nome da conta", "Editar nome da conta", "Valor", "Editar valor",
                                 "Data de vencimento", "Editar data de vencimento", "Categoria",
                                 "Editar recorrência", "Descrição (opcional)", "Editar descrição"])
        raiz = self.pagina.controls[0]
        self.assertIs(raiz.controls[-1].data, "pp_rodape_edicao")                # Cancelar e Salvar por último



class TestEtapa4AvisoDoVencimento(TesteInterfacePagamentos):
    """Sino 6.10, etapa 4 da integração (I3/I4 pela tela): no diálogo "Como
    deseja aplicar esta alteração?", com um novo vencimento, o aviso
    "Ocorrências com pagamentos registrados manterão seus meses originais
    (N ...)" aparece só quando a proteção realmente impede uma mudança de mês
    (só o dia não conta; a selecionada não conta; sem pagamentos, nada; uma
    alteração que seria recusada, nada). Convive com o aviso do valor. A
    recusa da I4 mostra a mensagem e não grava nada. Hoje fixo: 15/09/2026;
    série mensal desde 10/09/2026 (setembro é a selecionada)."""

    NOME = "Série I3"

    def setUp(self):
        super().setUp()
        _, self.ids = db.criar_serie_recorrente(self.usuario_id, self.NOME, 100.0, "2026-09-10", "mensal")
        self.set, self.out, self.nov, self.dez, self.jan = self.ids[:5]

    def pagar(self, conta):
        pagamentos.registrar_pagamento_parcial(conta, 40_00, "2026-09-05")

    def escopo(self, nova_data, valor=None):
        """Detalhes de setembro › Editar › calendário do vencimento › Salvar."""
        self.abrir_detalhes(self.NOME)
        self.clicar(self.botao("Editar"))
        seletor = [c.args[0] for c in self.pagina.overlay.append.call_args_list
                   if isinstance(c.args[0], ft.DatePicker)][-1]
        seletor.value = datetime.fromisoformat(nova_data)
        seletor.on_change(Evento(self.pagina, seletor))
        if valor is not None:
            campo = self.campo("Valor")
            campo.value = valor
            campo.on_change(Evento(self.pagina, campo))
        self.clicar(self.botao("Salvar alterações"))
        dialogo = self.dialogo()
        self.assertEqual(dialogo.title.value, "Como deseja aplicar esta alteração?")
        return dialogo

    def avisos(self, dialogo):
        return {c.data: c.content.value for c in percorrer(dialogo.content)
                if isinstance(c, ft.Container) and (c.data or "").startswith("pp_aviso_")}

    def venc(self, conta):
        return self.consultar("SELECT data_vencimento FROM contas WHERE id = ?", (conta,))[0][0]

    def tudo(self):
        return (self.consultar("SELECT * FROM contas ORDER BY id"),
                self.consultar("SELECT * FROM series_recorrencia ORDER BY id"),
                self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"))

    def test_aviso_com_uma_e_com_varias(self):
        self.pagar(self.nov)
        self.assertEqual(self.avisos(self.escopo("2026-10-10")), {
            "pp_aviso_vencimento": "Ocorrências com pagamentos registrados manterão seus meses originais "
                                   "(1 ocorrência)."})
        self.pagar(self.jan)
        self.assertEqual(self.avisos(self.escopo("2026-10-10"))["pp_aviso_vencimento"],
                         "Ocorrências com pagamentos registrados manterão seus meses originais (2 ocorrências).")

    def test_sem_aviso_so_com_o_dia(self):
        self.pagar(self.nov)
        self.assertEqual(self.avisos(self.escopo("2026-09-20")), {})

    def test_sem_aviso_sem_ocorrencias_com_pagamentos(self):
        db.editar_conta_ocorrencia(self.nov, nome="Editada")                     # só editada: não conta
        self.assertEqual(self.avisos(self.escopo("2026-10-10")), {})

    def test_a_selecionada_movida_nao_conta(self):
        self.pagar(self.set)                                                       # I1: a própria selecionada
        dialogo = self.escopo("2026-10-10")
        self.assertEqual(self.avisos(dialogo), {})
        self.clicar(self.acao_do_dialogo("Este mês em diante"))
        self.assertEqual(self.venc(self.set), "2026-10-10")                        # mudou de mês, com o pagamento
        self.assertEqual(pagamentos.obter_situacao(self.set)["pago_centavos"], 40_00)

    def test_avisos_de_valor_e_de_vencimento_juntos(self):
        self.pagar(self.nov)
        dialogo = self.escopo("2026-10-10", valor="120,00")
        avisos = self.avisos(dialogo)
        self.assertEqual(set(avisos), {"pp_aviso_protegidas", "pp_aviso_vencimento"})
        self.assertIn("manterão seus valores atuais (1 ocorrência)", avisos["pp_aviso_protegidas"])
        self.assertIn("manterão seus meses originais (1 ocorrência)", avisos["pp_aviso_vencimento"])
        ordem = [c.data for c in percorrer(dialogo.content) if isinstance(c, ft.Container) and c.data]
        self.assertEqual(ordem, ["pp_aviso_protegidas", "pp_aviso_vencimento"])     # valor, depois mês

    def test_dialogo_continua_utilizavel_e_aplica(self):
        self.pagar(self.nov)
        dialogo = self.escopo("2026-10-10")
        self.assertEqual([b.content for b in dialogo.actions], ["Cancelar", "Somente este mês", "Este mês em diante"])
        self.assertIsInstance(dialogo.content, ft.Column)
        self.clicar(self.acao_do_dialogo("Este mês em diante"))
        self.assertEqual(self.dialogo().title.value, "Alteração salva")
        self.assertEqual((self.venc(self.set), self.venc(self.out), self.venc(self.nov), self.venc(self.dez)),
                         ("2026-10-10", "2026-12-10", "2026-11-10", "2027-01-10"))  # nov fica; out pula nov

    def test_recusas_da_i4_mostram_a_mensagem_e_nao_gravam(self):
        self.pagar(self.nov)
        for data, motivo in (("2026-11-20", "mesmo_mes"), ("2026-12-10", "depois")):
            with self.subTest(motivo=motivo):
                antes = self.tudo()
                dialogo = self.escopo(data)
                self.assertEqual(self.avisos(dialogo), {})                         # sem aviso de sucesso
                self.clicar(self.acao_do_dialogo("Este mês em diante"))
                self.assertIn(db.MENSAGENS_COMPETENCIA_COM_PAGAMENTOS[motivo], self.textos())
                self.assertNotEqual(self.dialogo().title.value, "Alteração salva")
                self.assertEqual(self.tudo(), antes)

    def test_somente_este_mes_continua_disponivel(self):
        self.pagar(self.nov)
        self.escopo("2026-12-10")
        self.clicar(self.acao_do_dialogo("Somente este mês"))
        self.assertEqual((self.venc(self.set), self.venc(self.nov)), ("2026-12-10", "2026-11-10"))


class TestEtapa5EditarIntegrado(TesteInterfacePagamentos):
    """Sino 6.10, etapa 5 da integração: o Editar novo (resumo, prévia do saldo,
    lápis, barra fixa e menu da Recorrência) com as regras das etapas 3 e 4 --
    estornados fora do total pago, recusas visíveis na barra, aviso I3 pelo
    lápis da data e nenhuma mensagem de sucesso numa recusa. Hoje fixo:
    15/09/2026."""

    def editar(self, nome="Internet"):
        self.abrir_detalhes(nome)
        self.clicar(self.botao("Editar"))

    def resumo(self):
        caixa = next(c for c in self.controles(ft.Container) if c.data == "pp_resumo_edicao")
        t = {c.data: c.value for c in percorrer(caixa) if isinstance(c, ft.Text) and c.data}
        return f"Total pago: {t['pp_valor_pago_edicao']} · {t['pp_rotulo_saldo_edicao']}: {t['pp_valor_saldo_edicao']}"

    def mudar(self, rotulo, valor):
        campo = self.campo(rotulo)
        campo.value = valor
        campo.on_change(Evento(self.pagina, campo))

    def escolher_data(self, nova_data):
        self.clicar(self.campo("Data de vencimento").suffix_icon)                 # lápis da data
        seletor = self.dialogo()
        self.assertIsInstance(seletor, ft.DatePicker)
        seletor.value = datetime.fromisoformat(nova_data)
        seletor.on_change(Evento(self.pagina, seletor))

    def textos_da_barra(self):
        barra = next(c for c in self.controles(ft.Container) if c.data == "pp_rodape_edicao")
        return [c.value for c in percorrer(barra) if isinstance(c, ft.Text) and c.value]

    def tudo(self):
        return (self.consultar("SELECT * FROM contas ORDER BY id"),
                self.consultar("SELECT * FROM series_recorrencia ORDER BY id"),
                self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"))

    def test_resumo_ignora_estornados_e_segue_o_modulo_financeiro(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 100_00, "2026-09-05")
        pagamentos.registrar_pagamento_parcial(self.conta, 50_00, "2026-09-06")
        pid = self.consultar("SELECT MAX(id) FROM pp_pagamentos")[0][0]
        pagamentos.estornar_pagamento(pid, (50_00, "2026-09-06"))
        self.editar()
        s = pagamentos.obter_situacao(self.conta)
        self.assertEqual((s["pago_centavos"], s["saldo_centavos"]), (100_00, 300_00))
        self.assertEqual(self.resumo(), "Total pago: R$ 100,00 · Saldo devedor: R$ 300,00")
        self.mudar("Valor", "350,00")
        self.assertEqual(self.resumo(), "Total pago: R$ 100,00 · Saldo devedor previsto: R$ 250,00")

    def test_resumo_de_conta_quitada_por_pagamentos(self):
        db.marcar_conta_como_paga(self.conta, "2026-09-10")
        self.editar()
        self.assertEqual(self.resumo(), "Total pago: R$ 400,00 · Saldo devedor: R$ 0,00")

    def test_valor_menor_que_o_pago_e_recusado_sem_gravar(self):
        pagamentos.registrar_pagamento_parcial(self.conta, 250_00, "2026-09-05")
        antes = self.tudo()
        self.editar()
        self.mudar("Valor", "200,00")
        self.assertEqual(self.resumo(), "Total pago: R$ 250,00 · Saldo devedor previsto: —")
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.dialogo().title.value, "O valor informado é menor que o total já pago.")
        self.assertEqual(self.tudo(), antes)

    def test_recusas_da_etapa4_aparecem_na_barra_e_nada_e_gravado(self):
        _, ids = db.criar_serie_recorrente(self.usuario_id, "Academia", 100.0, "2026-09-10", "mensal")
        pagamentos.registrar_pagamento_parcial(ids[2], 40_00, "2026-09-05")          # novembro com pagamento
        for data, motivo in (("2026-11-20", "mesmo_mes"), ("2026-12-10", "depois")):
            with self.subTest(motivo=motivo):
                antes = self.tudo()
                self.editar("Academia")
                self.escolher_data(data)
                self.clicar(self.botao("Salvar alterações"))
                self.assertEqual(self.avisos_do_escopo(), {})                        # nada de aviso I3
                self.clicar(self.acao_do_dialogo("Este mês em diante"))
                self.assertEqual(self.textos_da_barra(), [db.MENSAGENS_COMPETENCIA_COM_PAGAMENTOS[motivo]])
                self.assertNotEqual(self.dialogo().title.value, "Alteração salva")
                self.assertEqual(self.tudo(), antes)

    def test_recusa_anual_aparece_na_barra(self):
        _, ids = db.criar_serie_recorrente(self.usuario_id, "Seguro", 900.0, "2026-09-10", "anual")
        pagamentos.registrar_pagamento_parcial(ids[1], 40_00, "2026-09-05")          # setembro/2027 pago
        antes = self.tudo()
        self.editar("Seguro")
        self.escolher_data("2027-03-10")
        self.clicar(self.botao("Salvar alterações"))
        self.clicar(self.acao_do_dialogo("Este mês em diante"))
        self.assertEqual(self.textos_da_barra(), [db.MENSAGENS_COMPETENCIA_COM_PAGAMENTOS["ano"]])
        self.assertEqual(self.tudo(), antes)

    def avisos_do_escopo(self):
        return {c.data: c.content.value for c in percorrer(self.dialogo().content)
                if isinstance(c, ft.Container) and (c.data or "").startswith("pp_aviso_")}

    def test_aviso_i3_pelo_lapis_da_data_e_aplicacao(self):
        _, ids = db.criar_serie_recorrente(self.usuario_id, "Academia", 100.0, "2026-09-10", "mensal")
        pagamentos.registrar_pagamento_parcial(ids[2], 40_00, "2026-09-05")
        self.editar("Academia")
        self.escolher_data("2026-10-10")
        self.assertEqual(self.campo("Data de vencimento").value, "10/10/2026")
        self.assertEqual(self.consultar("SELECT data_vencimento FROM contas WHERE id = ?", (ids[0],)),
                         [("2026-09-10",)])                                           # nada salvo ainda
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.avisos_do_escopo(), {
            "pp_aviso_vencimento": "Ocorrências com pagamentos registrados manterão seus meses originais "
                                   "(1 ocorrência)."})
        self.clicar(self.acao_do_dialogo("Este mês em diante"))
        self.assertEqual(self.dialogo().title.value, "Alteração salva")
        self.assertEqual(self.consultar("SELECT data_vencimento FROM contas WHERE id = ?", (ids[2],)),
                         [("2026-11-10",)])                                           # H2: novembro fica

    def test_menu_da_recorrencia_leva_ao_aviso_de_pagamentos_na_frequencia(self):
        _, ids = db.criar_serie_recorrente(self.usuario_id, "Academia", 100.0, "2026-09-10", "mensal")
        pagamentos.registrar_pagamento_parcial(ids[2], 40_00, "2026-09-05")
        self.editar("Academia")
        self.clicar(self.acao_da_recorrencia("Alterar frequência"))
        self.assertTrue(any(isinstance(c, ft.Container) and c.data == "pp_aviso_frequencia"
                            for c in percorrer(self.dialogo().content)))
