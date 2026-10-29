"""
RNF14 (Sino 6.9.1, auditoria AT-SPI de 24/10/2026) — nome acessível dos botões
só de ícone: lápis e pagamento das linhas de Início (grupo A), setas de voltar e
botões do calendário (grupo B), ações das categorias (grupo C), setas de período
do Gráfico (grupo D) e os dois "Editar" de Ajustes (grupo E).

O tooltip não dá nome acessível no Linux e o IconButton do Flet 0.86.5 não tem
semantics_label; o nome vai no ícone (main.icone_com_nome), com a mesma cor e o
mesmo tamanho do botão, sem Semantics externo e sem dica visível nova. Leitor de
tela e AT-SPI: só na validação manual.
"""

import sqlite3
import unittest

from test_seletor_mes import BaseSeletor
from test_sessao_tema import CLARO, ESCURO
from test_tela_principal import Evento, ft, main, percorrer
from apoio_banco import db


class BaseNomes(BaseSeletor):
    def setUp(self):
        super().setUp()
        self.casa = self.criar_categoria(self.usuario_id)
        db.criar_conta_unica(self.usuario_id, "Internet", 99.9, "2026-09-10", categoria_id=self.casa)  # atrasada
        db.criar_conta_unica(self.usuario_id, "Luz", 120.0, "2026-09-28", categoria_id=self.casa)

    def clicavel_com_texto(self, texto):
        return next(c for c in self.controles() if getattr(c, "on_click", None) is not None
                    and any(isinstance(t, ft.Text) and t.value == texto for t in percorrer(c)))

    def botao_de_icone(self, icone, controles=None):
        controles = self.controles() if controles is None else controles
        return next(b for b in controles if isinstance(b, ft.IconButton) and getattr(b.icon, "icon", None) == icone)

    def em_inicio(self):
        return any(getattr(c, "data", None) == "proximo_mes" for c in self.controles())

    def assert_nome_no_icone(self, botao, nome, tamanho, cor, dica=None):
        self.assertIsInstance(botao, ft.IconButton)                    # continua focável (Tab; Enter/Espaço)
        self.assertIsInstance(botao.icon, ft.Icon)
        self.assertEqual(botao.icon.semantics_label, nome)
        self.assertEqual(botao.tooltip, dica)                          # dica do mouse igual à de antes
        self.assertEqual((botao.icon_size, botao.icon.size), (tamanho, tamanho))
        self.assertEqual((botao.icon_color, botao.icon.color), (cor, cor))

    def assert_sem_semantics_externo(self):
        self.assertEqual([c for c in self.controles(ft.Semantics) if c.label], [])
        self.assertEqual(self.controles(ft.MergeSemantics), [])


class TestVoltarECalendario(BaseNomes):
    """Grupo B: "Voltar" em Ver status, Contas atrasadas, Edição e Nova conta; "Escolher data"."""

    def assert_voltar(self, paleta=CLARO):
        voltar = self.botao_de_icone(ft.Icons.ARROW_BACK)
        self.assert_nome_no_icone(voltar, "Voltar", 20, paleta["texto_principal"])
        return voltar

    def assert_calendario_abre_o_seletor(self, paleta=CLARO):
        calendario = self.botao_de_icone(ft.Icons.CALENDAR_MONTH)
        self.assert_nome_no_icone(calendario, "Escolher data", None, paleta["acao_primaria"])
        self.clicar(calendario)
        self.assertIsInstance(self.pagina.dialogos[-1], ft.DatePicker)
        self.assertTrue(self.pagina.dialogos[-1].open)

    def test_ver_status(self):
        self.entrar()
        self.clicar(self.clicavel_com_texto("Ver status"))
        self.assert_sem_semantics_externo()
        self.clicar(self.assert_voltar())
        self.assertTrue(self.em_inicio())

    def test_contas_atrasadas(self):
        self.entrar()
        self.clicar(self.clicavel_com_texto("Ver essas contas"))
        self.assertIn("Contas em atraso", self.textos())
        self.clicar(self.assert_voltar())
        self.assertTrue(self.em_inicio())

    def test_edicao(self):
        self.entrar()
        self.clicar(self.icones("Editar conta")[0])
        self.assertIn("Editar conta", self.textos())
        self.assert_calendario_abre_o_seletor()
        self.clicar(self.assert_voltar())
        self.assertTrue(self.em_inicio())                               # o lápis volta para Início

    def test_nova_conta(self):
        self.entrar()
        self.clicar(next(c for c in self.controles() if getattr(c, "data", None) == "nova_conta"))
        self.assertIn("Nova conta", self.textos())
        self.assert_sem_semantics_externo()
        self.assert_calendario_abre_o_seletor()
        self.clicar(self.assert_voltar())
        self.assertTrue(self.em_inicio())

    def test_nova_conta_no_escuro(self):  # RNF09: as cores seguem o tema
        db.definir_tema(self.usuario_id, "escuro")
        self.entrar()
        self.clicar(next(c for c in self.controles() if getattr(c, "data", None) == "nova_conta"))
        self.assert_voltar(ESCURO)
        self.assert_calendario_abre_o_seletor(ESCURO)


class TestAcoesDasCategorias(BaseNomes):
    """Grupo C: "Nova categoria" e as ações de cada linha com o nome da categoria."""

    def setUp(self):
        super().setUp()
        self.mercado = self.criar_categoria(self.usuario_id, "Mercado")

    def abrir_categorias(self):
        self.entrar()
        self.clicar(self.clicavel_com_texto("Categorias"))

    def linha(self, nome):
        """Os três botões da linha da categoria, na ordem (nova conta, editar, excluir)."""
        return [b for b in self.controles(ft.IconButton)
                if isinstance(b.icon, ft.Icon) and (b.icon.semantics_label or "").endswith(f" {nome}")]

    def dialogo_aberto(self):
        return [d for d in self.pagina.dialogos if d.open][-1]

    def assert_botoes(self, paleta):
        nova = self.botao_de_icone(ft.Icons.ADD_CIRCLE)
        self.assert_nome_no_icone(nova, "Nova categoria", 28, paleta["acento_sobre_destaque"])
        for nome in ("Casa", "Mercado"):
            adicionar, editar, excluir = self.linha(nome)
            self.assert_nome_no_icone(adicionar, f"Nova conta na categoria {nome}", 18, paleta["acao_primaria"],
                                      dica="Nova conta nesta categoria")
            self.assert_nome_no_icone(editar, f"Editar categoria {nome}", 18, paleta["texto_secundario"])
            self.assert_nome_no_icone(excluir, f"Excluir categoria {nome}", 18, paleta["acao_destrutiva"])
            self.assertEqual([b.icon.icon for b in (adicionar, editar, excluir)],
                             [ft.Icons.ADD, ft.Icons.EDIT, ft.Icons.DELETE])
        self.assert_sem_semantics_externo()

    def test_nomes_no_claro(self):
        self.abrir_categorias()
        self.assert_botoes(CLARO)

    def test_nomes_no_escuro(self):  # RNF09: as cores seguem o tema
        db.definir_tema(self.usuario_id, "escuro")
        self.abrir_categorias()
        self.assert_botoes(ESCURO)

    def test_acoes_continuam_as_mesmas(self):
        self.abrir_categorias()
        self.clicar(self.botao_de_icone(ft.Icons.ADD_CIRCLE))
        self.assertEqual(self.dialogo_aberto().title.value, "Nova categoria")
        self.pagina.pop_dialog()
        self.clicar(self.linha("Mercado")[1])
        dialogo = self.dialogo_aberto()
        self.assertEqual(dialogo.title.value, "Editar categoria")
        self.assertEqual(next(c for c in percorrer(dialogo) if isinstance(c, ft.TextField)).value, "Mercado")
        self.pagina.pop_dialog()
        self.clicar(self.linha("Mercado")[2])
        self.assertEqual(self.dialogo_aberto().title.value, "Excluir categoria")
        self.pagina.pop_dialog()
        self.clicar(self.linha("Mercado")[0])
        self.assertIn("Nova conta", self.textos())
        categoria = next(c for c in self.controles(ft.Dropdown) if c.label == "Categoria")
        self.assertEqual(categoria.value, str(self.mercado))            # categoria já escolhida

    def test_nomes_acompanham_a_renomeacao(self):
        self.abrir_categorias()
        self.clicar(self.linha("Mercado")[1])
        dialogo = self.dialogo_aberto()
        next(c for c in percorrer(dialogo) if isinstance(c, ft.TextField)).value = "Feira"
        self.clicar(next(b for b in dialogo.actions if b.content == "Salvar"))
        self.assertEqual(self.linha("Mercado"), [])
        self.assertEqual([b.icon.semantics_label for b in self.linha("Feira")],
                         ["Nova conta na categoria Feira", "Editar categoria Feira", "Excluir categoria Feira"])


class TestSetasDoGrafico(BaseNomes):
    """Grupo D: "Período anterior" e "Próximo período", também quando desabilitadas."""

    def abrir_grafico(self):
        self.entrar()
        self.clicar(self.clicavel_com_texto("Gráfico"))

    def setas(self):
        return self.botao_de_icone(ft.Icons.CHEVRON_LEFT), self.botao_de_icone(ft.Icons.CHEVRON_RIGHT)

    def assert_setas(self, paleta, anterior_desabilitada=False, proxima_desabilitada=False):
        anterior, proxima = self.setas()
        for seta, nome, desabilitada in ((anterior, "Período anterior", anterior_desabilitada),
                                         (proxima, "Próximo período", proxima_desabilitada)):
            # mesma dica e mesma cor de antes, inclusive desabilitada (sem disabled_color)
            self.assert_nome_no_icone(seta, nome, None, paleta["texto_principal"], dica=nome)
            self.assertIsNone(seta.disabled_color)
            self.assertEqual(bool(seta.disabled), desabilitada)
        self.assert_sem_semantics_externo()

    def test_mensal_no_claro_navega_como_antes(self):
        self.abrir_grafico()
        self.assertIn("Setembro de 2026", self.textos())
        self.assert_setas(CLARO)
        self.clicar(self.setas()[0])
        self.assertIn("Agosto de 2026", self.textos())
        self.assert_setas(CLARO)
        self.clicar(self.setas()[1])
        self.clicar(self.setas()[1])
        self.assertIn("Outubro de 2026", self.textos())
        self.assert_setas(CLARO)

    def test_mensal_no_escuro(self):  # RNF09: as cores seguem o tema
        db.definir_tema(self.usuario_id, "escuro")
        self.abrir_grafico()
        self.assert_setas(ESCURO)

    def test_anual_com_setas_desabilitadas_nos_limites(self):
        db.criar_conta_unica(self.usuario_id, "Antiga", 50.0, "2024-03-10")
        self.abrir_grafico()
        self.clicar(self.clicavel_com_texto("Anual"))
        self.assert_setas(CLARO, proxima_desabilitada=True)           # 2026 é o último ano com contas
        self.clicar(self.setas()[0])
        self.assertIn("2024", self.textos())                           # pula 2025, sem contas
        self.assert_setas(CLARO, anterior_desabilitada=True)


class TestEditarDeAjustes(BaseNomes):
    """Grupo E: os dois "Editar" de Ajustes com nomes próprios e o mesmo texto visível."""

    def abrir_ajustes(self):
        self.entrar()
        self.clicar(self.clicavel_com_texto("Ajustes"))

    def editar(self):
        return self.controles(ft.OutlinedButton)

    def assert_botoes(self, paleta):
        nome, email = self.editar()
        for botao, rotulo in ((nome, "Editar nome"), (email, "Editar e-mail")):
            self.assertIsInstance(botao.content, ft.Text)
            self.assertEqual((botao.content.value, botao.content.semantics_label), ("Editar", rotulo))
            self.assertEqual(botao.icon, ft.Icons.EDIT)
            self.assertIsNone(botao.tooltip)
            # mesma aparência: cor do estilo repetida no texto; tamanho e peso herdados do botão
            self.assertEqual((botao.style.color, botao.content.color), (paleta["texto_principal"],) * 2)
            self.assertEqual((botao.content.size, botao.content.weight), (None, None))
        self.assertEqual(email.data, "editar_email")
        self.assert_sem_semantics_externo()

    def test_nomes_no_claro(self):
        self.abrir_ajustes()
        self.assert_botoes(CLARO)

    def test_nomes_no_escuro(self):  # RNF09: as cores seguem o tema
        db.definir_tema(self.usuario_id, "escuro")
        self.abrir_ajustes()
        self.assert_botoes(ESCURO)

    def test_cada_um_abre_o_seu_dialogo(self):
        self.abrir_ajustes()
        nome, email = self.editar()
        for botao, rotulo_do_campo in ((nome, "Nome"), (email, "Senha atual")):
            self.clicar(botao)
            dialogo = [d for d in self.pagina.dialogos if d.open][-1]
            self.assertIn(rotulo_do_campo, [c.label for c in percorrer(dialogo) if isinstance(c, ft.TextField)])
            self.pagina.pop_dialog()


class TestAcoesDasLinhasDeInicio(BaseNomes):
    """
    Grupo A: lápis e pagamento de cada linha de Início, com o nome e o vencimento
    da ocorrência exibida e, só entre contas de mesmo nome e mesmo vencimento, a
    posição na lista ("1 de 2"). Hoje fixo em 15/09/2026; no setUp, Internet
    10/09 (atrasada) e Luz 28/09 (pendente).
    """

    def linhas(self):
        return [c for c in self.controles(ft.Container) if c.data in ("linha_conta", "linha_conta_empilhada")]

    def acoes(self, linha):
        return [b for b in percorrer(linha) if isinstance(b, ft.IconButton)]

    def nomes(self):
        """(nome visível, nome do lápis, nome do pagamento) de cada linha, na ordem exibida."""
        resultado = []
        for linha in self.linhas():
            visivel = next(t.value for t in percorrer(linha) if isinstance(t, ft.Text))
            resultado.append((visivel, *[b.icon.semantics_label for b in self.acoes(linha)]))
        return resultado

    def valores(self):
        return [[t.value for t in percorrer(linha) if isinstance(t, ft.Text)][2] for linha in self.linhas()]

    def acao(self, nome_acessivel):
        return next(b for b in self.controles(ft.IconButton)
                    if isinstance(b.icon, ft.Icon) and b.icon.semantics_label == nome_acessivel)

    # Depois de salvar, a edição abre no máximo dois diálogos em sequência
    # (escopo da série e confirmação); o terceiro é margem. Um diálogo que não
    # fecha pela primeira ação faz o teste falhar, em vez de prender o laço.
    LIMITE_DE_DIALOGOS = 3

    def fechar_dialogos(self):
        for _ in range(self.LIMITE_DE_DIALOGOS):
            abertos = [d for d in self.pagina.dialogos if d.open]
            if not abertos:
                return
            abertos[-1].actions[0].on_click(Evento(self.pagina, abertos[-1].actions[0]))
        abertos = [d for d in self.pagina.dialogos if d.open]
        if abertos:
            self.fail(f"diálogos ainda abertos depois de {self.LIMITE_DE_DIALOGOS} tentativas: "
                      f"{[getattr(d.title, 'value', d.title) for d in abertos]}")

    def renomear(self, nome_do_lapis, novo_nome):
        self.clicar(self.acao(nome_do_lapis))
        next(c for c in self.controles(ft.TextField) if c.label == "Nome da conta").value = novo_nome
        self.clicar(self.botao("Salvar alterações"))
        self.fechar_dialogos()
        self.assertTrue(self.em_inicio())

    def proximo_mes(self):
        self.clicar(next(b for b in self.controles(ft.IconButton) if b.data == "proximo_mes"))

    def mes_anterior(self):
        self.clicar(next(b for b in self.controles(ft.IconButton) if b.data == "mes_anterior"))

    def assert_linhas(self, paleta):
        for linha in self.linhas():
            lapis, pagamento = self.acoes(linha)
            nome_lapis = lapis.icon.semantics_label
            self.assert_nome_no_icone(lapis, nome_lapis, 22, paleta["texto_secundario"], dica="Editar conta")
            self.assertEqual(lapis.icon.icon, ft.Icons.EDIT_OUTLINED)
            if pagamento.tooltip == "Marcar como pendente":
                icone, cor = ft.Icons.CHECK_CIRCLE, paleta["controle_pago"]
            else:
                icone, cor = ft.Icons.CHECK_CIRCLE_OUTLINE, paleta["controle_pendente"]
                self.assertEqual(pagamento.tooltip, "Marcar como paga")
            self.assert_nome_no_icone(pagamento, pagamento.icon.semantics_label, 22, cor, dica=pagamento.tooltip)
            self.assertEqual(pagamento.icon.icon, icone)
        self.assert_sem_semantics_externo()

    # ------------------------------------------------------------ nomes
    def test_nomes_com_nome_e_vencimento_nos_tres_status(self):
        db.marcar_conta_como_paga(db.criar_conta_unica(self.usuario_id, "Água", 50.0, "2026-09-05"))
        db.criar_conta_unica(self.usuario_id, "Manutenção do condomínio bloco", 300.0, "2026-09-20")
        self.entrar()
        self.assertEqual(self.nomes(), [
            ("Internet", "Editar conta Internet, vencimento 10/09/2026",
             "Marcar Internet, vencimento 10/09/2026, como paga"),                       # atrasada
            ("Água", "Editar conta Água, vencimento 05/09/2026",
             "Marcar Água, vencimento 05/09/2026, como pendente"),                       # paga
            ("Manutenção do condomínio bloco",
             "Editar conta Manutenção do condomínio bloco, vencimento 20/09/2026",
             "Marcar Manutenção do condomínio bloco, vencimento 20/09/2026, como paga"),
            ("Luz", "Editar conta Luz, vencimento 28/09/2026", "Marcar Luz, vencimento 28/09/2026, como paga"),
        ])
        self.assert_linhas(CLARO)

    def test_cores_e_icones_no_escuro(self):  # RNF09: as cores seguem o tema
        db.marcar_conta_como_paga(db.criar_conta_unica(self.usuario_id, "Água", 50.0, "2026-09-05"))
        db.definir_tema(self.usuario_id, "escuro")
        self.entrar()
        self.assertEqual(len(self.linhas()), 3)
        self.assert_linhas(ESCURO)

    def test_recorrente_usa_o_vencimento_da_ocorrencia_e_acompanha_o_mes(self):
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-15", "mensal")
        self.entrar()
        self.assertIn(("Aluguel", "Editar conta Aluguel, vencimento 15/09/2026",
                       "Marcar Aluguel, vencimento 15/09/2026, como paga"), self.nomes())
        self.proximo_mes()
        self.assertEqual(self.nomes(), [("Aluguel", "Editar conta Aluguel, vencimento 15/10/2026",
                                         "Marcar Aluguel, vencimento 15/10/2026, como paga")])
        self.mes_anterior()
        self.assertEqual([n[0] for n in self.nomes()], ["Internet", "Aluguel", "Luz"])

    def test_nome_acompanha_o_pagamento(self):
        self.entrar()
        self.clicar(self.acao("Marcar Luz, vencimento 28/09/2026, como paga"))
        self.assertEqual(self.nomes()[-1][2], "Marcar Luz, vencimento 28/09/2026, como pendente")
        self.clicar(self.acao("Marcar Luz, vencimento 28/09/2026, como pendente"))
        # Pagamentos parciais: desfazer a quitação passa pela confirmação da reversão.
        dialogo = self.pagina.show_dialog.call_args[0][0]
        self.clicar(next(c for c in percorrer(dialogo.content)
                         if isinstance(c, ft.Container) and c.data == "pp_opcao_todos"))
        self.clicar(next(b for b in dialogo.actions if b.content == "Confirmar"))
        self.assertEqual(self.nomes()[-1][2], "Marcar Luz, vencimento 28/09/2026, como paga")

    def test_lapis_abre_a_edicao_e_nome_acompanha_a_renomeacao(self):
        self.entrar()
        self.renomear("Editar conta Luz, vencimento 28/09/2026", "Energia")
        self.assertEqual(self.nomes(), [
            ("Internet", "Editar conta Internet, vencimento 10/09/2026",
             "Marcar Internet, vencimento 10/09/2026, como paga"),
            ("Energia", "Editar conta Energia, vencimento 28/09/2026",
             "Marcar Energia, vencimento 28/09/2026, como paga"),
        ])

    # ------------------------------------------------------------ contas iguais
    def test_mesmo_nome_com_vencimentos_diferentes_sem_posicao(self):
        db.criar_conta_unica(self.usuario_id, "Luz", 80.0, "2026-09-12")      # atrasada
        self.entrar()
        self.assertEqual([n[1] for n in self.nomes()], [
            "Editar conta Internet, vencimento 10/09/2026",
            "Editar conta Luz, vencimento 12/09/2026",
            "Editar conta Luz, vencimento 28/09/2026",
        ])

    def test_mesmo_nome_e_vencimento_numerados_na_ordem_exibida(self):
        db.criar_conta_unica(self.usuario_id, "Gás", 60.0, "2026-09-20")
        db.criar_conta_unica(self.usuario_id, "Gás", 75.0, "2026-09-20")
        self.entrar()
        ordem = main.ordenar_contas_do_mes(db.listar_contas(self.usuario_id, "2026-09"))
        self.assertEqual([c["nome"] for c in ordem], ["Internet", "Gás", "Gás", "Luz"])
        self.assertEqual(self.valores(), [main.formatar_moeda(c["valor"]) for c in ordem])   # ordem inalterada
        self.assertEqual(self.nomes(), [
            ("Internet", "Editar conta Internet, vencimento 10/09/2026",
             "Marcar Internet, vencimento 10/09/2026, como paga"),
            ("Gás", "Editar conta Gás, vencimento 20/09/2026, 1 de 2",
             "Marcar Gás, vencimento 20/09/2026, 1 de 2, como paga"),
            ("Gás", "Editar conta Gás, vencimento 20/09/2026, 2 de 2",
             "Marcar Gás, vencimento 20/09/2026, 2 de 2, como paga"),
            ("Luz", "Editar conta Luz, vencimento 28/09/2026", "Marcar Luz, vencimento 28/09/2026, como paga"),
        ])
        # cada posição leva à sua conta: pagar o "2 de 2" paga a segunda linha
        self.clicar(self.acao("Marcar Gás, vencimento 20/09/2026, 2 de 2, como paga"))
        self.assertEqual(self.nomes()[2][2], "Marcar Gás, vencimento 20/09/2026, 2 de 2, como pendente")
        self.assertEqual(self.nomes()[1][2], "Marcar Gás, vencimento 20/09/2026, 1 de 2, como paga")

    def test_duplicatas_nao_consecutivas_e_renumeradas_quando_a_ordem_muda(self):
        db.criar_conta_unica(self.usuario_id, "Gás", 60.0, "2026-09-12")                          # atrasada
        db.marcar_conta_como_paga(db.criar_conta_unica(self.usuario_id, "Gás", 75.0, "2026-09-12"))  # paga
        db.marcar_conta_como_paga(db.criar_conta_unica(self.usuario_id, "Água", 50.0, "2026-09-01"))
        self.entrar()
        # atrasadas primeiro: Água (01/09, paga) fica entre as duas Gás
        self.assertEqual([(n[0], v) for n, v in zip(self.nomes(), self.valores())], [
            ("Internet", "R$ 99,90"), ("Gás", "R$ 60,00"), ("Água", "R$ 50,00"), ("Gás", "R$ 75,00"), ("Luz", "R$ 120,00"),
        ])
        self.assertEqual(self.nomes()[1][1:], ("Editar conta Gás, vencimento 12/09/2026, 1 de 2",
                                               "Marcar Gás, vencimento 12/09/2026, 1 de 2, como paga"))
        self.assertEqual(self.nomes()[3][1:], ("Editar conta Gás, vencimento 12/09/2026, 2 de 2",
                                               "Marcar Gás, vencimento 12/09/2026, 2 de 2, como pendente"))
        self.assertEqual(self.nomes()[2][1], "Editar conta Água, vencimento 01/09/2026")
        # pagar a atrasada muda a ordem exibida (deixa de vir primeiro); a posição acompanha a lista nova
        self.clicar(self.acao("Marcar Gás, vencimento 12/09/2026, 1 de 2, como paga"))
        ordem = main.ordenar_contas_do_mes(db.listar_contas(self.usuario_id, "2026-09"))
        self.assertEqual(self.valores(), [main.formatar_moeda(c["valor"]) for c in ordem])
        gas = [(v, n[1]) for n, v in zip(self.nomes(), self.valores()) if n[0] == "Gás"]
        self.assertEqual([n for _, n in gas], ["Editar conta Gás, vencimento 12/09/2026, 1 de 2",
                                               "Editar conta Gás, vencimento 12/09/2026, 2 de 2"])
        self.assertEqual([v for v, _ in gas], [main.formatar_moeda(c["valor"]) for c in ordem if c["nome"] == "Gás"])

    def test_posicao_some_quando_deixa_de_haver_duplicata(self):
        db.criar_conta_unica(self.usuario_id, "Gás", 60.0, "2026-09-20")
        db.criar_conta_unica(self.usuario_id, "Gás", 75.0, "2026-09-20")
        db.criar_conta_unica(self.usuario_id, "Gás", 90.0, "2026-09-20")
        self.entrar()
        self.assertEqual([n[1] for n in self.nomes() if n[0] == "Gás"],
                         [f"Editar conta Gás, vencimento 20/09/2026, {i} de 3" for i in (1, 2, 3)])
        self.renomear("Editar conta Gás, vencimento 20/09/2026, 2 de 3", "Gás da cozinha")
        self.assertEqual([n[1] for n in self.nomes() if n[0].startswith("Gás")], [
            "Editar conta Gás, vencimento 20/09/2026, 1 de 2",
            "Editar conta Gás da cozinha, vencimento 20/09/2026",
            "Editar conta Gás, vencimento 20/09/2026, 2 de 2",
        ])
        self.renomear("Editar conta Gás, vencimento 20/09/2026, 2 de 2", "Gás do aquecedor")
        self.assertEqual([n[1] for n in self.nomes() if n[0].startswith("Gás")], [
            "Editar conta Gás, vencimento 20/09/2026",
            "Editar conta Gás da cozinha, vencimento 20/09/2026",
            "Editar conta Gás do aquecedor, vencimento 20/09/2026",
        ])

    def test_posicao_conta_por_mes_exibido(self):
        db.criar_conta_unica(self.usuario_id, "Gás", 60.0, "2026-09-20")
        db.criar_conta_unica(self.usuario_id, "Gás", 75.0, "2026-10-20")
        db.criar_conta_unica(self.usuario_id, "Gás", 90.0, "2026-10-20")
        self.entrar()
        self.assertIn("Editar conta Gás, vencimento 20/09/2026", [n[1] for n in self.nomes()])
        self.proximo_mes()
        self.assertEqual([n[1] for n in self.nomes()], ["Editar conta Gás, vencimento 20/10/2026, 1 de 2",
                                                         "Editar conta Gás, vencimento 20/10/2026, 2 de 2"])

    def test_auxiliar_fechar_dialogos_tem_limite(self):
        # só o auxiliar do teste: diálogos de mentira, nenhum diálogo do app
        def dialogo(titulo, ao_clicar):
            return ft.AlertDialog(title=ft.Text(titulo), actions=[ft.TextButton("Ok", on_click=ao_clicar)])

        self.pagina.show_dialog(dialogo("Fecha", lambda e: self.pagina.pop_dialog()))
        self.pagina.show_dialog(dialogo("Fecha também", lambda e: self.pagina.pop_dialog()))
        self.fechar_dialogos()
        self.assertFalse(any(d.open for d in self.pagina.dialogos))

        self.pagina.show_dialog(dialogo("Preso", lambda e: None))
        with self.assertRaises(self.failureException) as falha:
            self.fechar_dialogos()
        self.assertIn("diálogos ainda abertos depois de 3 tentativas: ['Preso']", str(falha.exception))

    def test_nada_e_gravado_no_banco(self):
        db.criar_conta_unica(self.usuario_id, "Gás", 60.0, "2026-09-20")
        db.criar_conta_unica(self.usuario_id, "Gás", 75.0, "2026-09-20")
        self.entrar()
        antes = list(self.conexao_de_leitura().iterdump())
        self.proximo_mes()
        self.mes_anterior()
        self.assertIn("Editar conta Gás, vencimento 20/09/2026, 2 de 2", [n[1] for n in self.nomes()])
        depois = list(self.conexao_de_leitura().iterdump())
        self.assertEqual(antes, depois)
        self.assertFalse([linha for linha in depois if " de 2" in linha])

    def conexao_de_leitura(self):
        conexao = sqlite3.connect(db.NOME_DO_BANCO)
        self.addCleanup(conexao.close)
        return conexao


class TestPosicoesDeContasIguais(unittest.TestCase):
    """main.posicoes_de_contas_iguais: uma contagem e uma atribuição, na ordem recebida."""

    def contas(self, *pares):
        return [{"nome": nome, "data_vencimento": vencimento} for nome, vencimento in pares]

    def test_sem_duplicatas(self):
        contas = self.contas(("Luz", "2026-10-05"), ("Luz", "2026-10-28"), ("Água", "2026-10-05"))
        self.assertEqual(main.posicoes_de_contas_iguais(contas), [None, None, None])

    def test_duplicatas_na_ordem_recebida_sem_alterar_a_lista(self):
        contas = self.contas(("Gás", "2026-10-20"), ("Luz", "2026-10-20"), ("Gás", "2026-10-20"),
                             ("Gás", "2026-10-21"), ("Gás", "2026-10-20"))
        copia = [dict(c) for c in contas]
        self.assertEqual(main.posicoes_de_contas_iguais(contas), ["1 de 3", None, "2 de 3", None, "3 de 3"])
        self.assertEqual(contas, copia)

    def test_lista_vazia(self):
        self.assertEqual(main.posicoes_de_contas_iguais([]), [])
