"""
Sino 6.12 (experimental) -- ajustes pós-validação manual (07/11/2026).

A: "Alterar parcelamento" sai dos Detalhes e fica no campo Recorrência de Editar (só
   parceladas); aplica pelo mesmo diálogo/mecanismo e volta aos Detalhes da conta.
B: no diálogo, "Aplicar" fica cinza e desabilitado enquanto a prévia é recusada.
C: recorrência de valor variável -- mudar SÓ o valor (inclusive informar o de uma
   pendente) grava só a ocorrência, sem o diálogo de abrangência; outros campos
   mantêm o diálogo; séries de valor fixo não mudam.
D: "Alterar tipo de valor" no campo Recorrência de Editar (R3/R4, R4-A, X3), separado
   de "Encerrar recorrência"; R6 continua (sem "Alterar frequência").
Bancos temporários (apoio_banco); hoje fixo: 15/09/2026; nenhuma janela é aberta.
"""

import unittest

from apoio_banco import db
from test_612_variavel_telas import CLARO, BaseVariavelTelas
from test_tela_principal import Evento

import flet as ft  # noqa: E402
import main  # noqa: E402
import pagamentos  # noqa: E402


class BaseAjustes(BaseVariavelTelas):
    def estado(self):
        return {t: self.consultar(f"SELECT * FROM {t} ORDER BY 1")
                for t in ("contas", "pp_pagamentos", "series_recorrencia", "parcelamentos",
                          "series_valor_variavel", "ocorrencias_valor_pendente")}

    def abrir_editar(self, nome, mes=None):
        self.entrar()
        if mes is not None:
            self.clicar(next(c for c in self.controles(ft.IconButton) if c.data == mes))
        self.clicar(self.linha(nome))
        self.clicar(self.botao("Editar"))

    def itens_do_menu(self):
        menu = self.campo("Recorrência").suffix_icon
        return None if menu is None else [i.content for i in menu.items]

    def escolher_no_menu(self, texto):
        self.clicar(next(i for i in self.campo("Recorrência").suffix_icon.items if i.content == texto))

    def digitar(self, rotulo, texto):
        campo = self.campo(rotulo)
        campo.value = texto
        campo.on_change(Evento(self.pagina, campo))

    def em_detalhes(self):
        return any(getattr(c, "data", None) == "tela_detalhes" for c in self.controles())

    def em_editar(self):
        return "Editar conta" in self.textos()

    def valores(self, serie_id):
        return [v for (v,) in self.consultar("SELECT valor FROM contas WHERE serie_id = ? ORDER BY posicao",
                                             (serie_id,))]


# ---------------------------------------------------------------- A e B: parcelamento
class TestAjusteAParcelamentoEmEditar(BaseAjustes):
    def setUp(self):
        super().setUp()
        self.serie, self.p = db.criar_conta_parcelada(self.usuario_id, "Sofá", 1200.0, 6, "2026-09-20")

    def abrir_dialogo(self):
        self.abrir_editar("Sofá")
        self.assertEqual(self.itens_do_menu(), ["Alterar parcelamento"])
        self.escolher_no_menu("Alterar parcelamento")
        self.assertEqual(self.dlg().data, "dialogo_alterar_parcelamento")

    def total(self, texto):
        campo = self.no_dialogo("total_alterar_parcelamento")
        campo.value = texto
        campo.on_change(Evento(self.pagina, campo))

    def aplicar(self):
        return self.no_dialogo_acao("aplicar_alterar_parcelamento")

    def no_dialogo_acao(self, data):
        return next(b for b in self.dlg().actions if getattr(b, "data", None) == data)

    def test_detalhes_sem_a_acao(self):
        self.entrar()
        self.clicar(self.linha("Sofá"))
        self.assertTrue(self.em_detalhes())
        self.assertEqual([c for c in self.controles() if getattr(c, "data", None) == "alterar_parcelamento"], [])
        self.assertNotIn("Alterar parcelamento", [getattr(c, "content", None) for c in self.controles()])

    def test_aplicar_volta_aos_detalhes_da_mesma_conta(self):
        self.abrir_dialogo()
        self.total("1.500,00")
        self.clicar(self.aplicar())
        self.assertEqual(self.abertos(), [])
        self.assertTrue(self.em_detalhes())
        self.assertIn("R$ 250,00", self.textos())                         # dados relidos do banco
        self.assertEqual(self.valores(self.serie), [250.0] * 6)

    def test_protecoes_de_paga_estornada_e_editada(self):
        pagamentos.registrar_pagamento_parcial(self.p[0], 50_00, "2026-09-12")      # com pagamento
        pagamentos.registrar_pagamento_parcial(self.p[1], 30_00, "2026-09-13")      # estornado
        p = pagamentos.obter_situacao(self.p[1])["ativos"][0]
        pagamentos.estornar_pagamento(p["id"], (p["valor_centavos"], p["data_pagamento"]))
        db.editar_conta_ocorrencia(self.p[2], valor=260.0)                          # editada
        pagos = self.consultar("SELECT * FROM pp_pagamentos ORDER BY id")
        self.abrir_dialogo()
        previa = [t for t in self.textos_do_dialogo() if t.startswith("Parcela ")]
        self.assertIn("Parcela 1 de 6 · 20/09/2026 · R$ 200,00 · com pagamentos (mantida)", previa)
        self.assertIn("Parcela 2 de 6 · 20/10/2026 · R$ 200,00 · com pagamentos (mantida)", previa)
        self.assertIn("Parcela 3 de 6 · 20/11/2026 · R$ 260,00 · editada (mantida)", previa)
        self.total("1.560,00")
        self.clicar(self.aplicar())
        valores = self.valores(self.serie)
        self.assertEqual(valores[:3], [200.0, 200.0, 260.0])
        self.assertEqual(round(sum(valores), 2), 1560.0)
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"), pagos)
        self.assertTrue(self.em_detalhes())

    def test_alteracao_nao_salva_impede_abrir(self):
        self.abrir_editar("Sofá")
        self.digitar("Nome da conta", "Sofá novo")
        antes = self.estado()
        self.escolher_no_menu("Alterar parcelamento")
        self.assertEqual(self.dlg().title.value, "Há alterações não salvas")
        self.assertEqual(self.dlg().content.value, main.TEXTO_SALVE_ANTES_DA_ACAO)
        self.clicar(self.acao("Entendi"))
        self.assertEqual(self.abertos(), [])
        self.assertTrue(self.em_editar())
        self.assertEqual(self.campo("Nome da conta").value, "Sofá novo")             # nada perdido
        self.assertEqual(self.estado(), antes)

    def test_cancelar_nao_grava_e_fica_em_editar(self):
        antes = self.estado()
        self.abrir_dialogo()
        self.total("2.000,00")
        self.clicar(self.acao("Cancelar"))
        self.assertEqual(self.estado(), antes)
        self.assertTrue(self.em_editar())

    # ------------------------------------------------------------ B
    def test_aplicar_desabilitado_com_total_invalido_e_reabilitado(self):
        self.abrir_dialogo()
        botao = self.aplicar()
        self.assertFalse(botao.disabled)
        self.assertEqual(botao.bgcolor, CLARO["acao_primaria"])
        self.total("abc")
        self.assertTrue(botao.disabled)
        self.assertEqual((botao.bgcolor, botao.color),
                         (CLARO["botao_desabilitado_fundo"], CLARO["botao_desabilitado_texto"]))
        self.assertIn(db.MENSAGEM_VALOR_TOTAL_INVALIDO, self.textos_do_dialogo())
        self.total("1.300,00")
        self.assertFalse(botao.disabled)
        self.assertEqual((botao.bgcolor, botao.color), (CLARO["acao_primaria"], CLARO["texto_sobre_acao"]))
        self.assertNotIn(db.MENSAGEM_VALOR_TOTAL_INVALIDO, self.textos_do_dialogo())

    def test_bloqueio_funcional_com_recalculo_recusado(self):
        pagamentos.registrar_pagamento_parcial(self.p[0], 50_00, "2026-09-12")
        db.editar_conta_ocorrencia(self.p[1], valor=200.0)
        antes = self.estado()
        self.abrir_dialogo()
        self.total("150,00")                                                     # menor que o mantido
        botao = self.aplicar()
        self.assertTrue(botao.disabled)
        mensagens = [t for t in self.textos_do_dialogo() if t and not t.startswith(("Só ", "Parcela "))]
        self.assertTrue(mensagens, "a mensagem de validação continua visível")
        botao.on_click(Evento(self.pagina, botao))                               # mesmo clicado à força
        self.assertEqual(self.estado(), antes)
        self.assertEqual(self.dlg().data, "dialogo_alterar_parcelamento")
        self.escolher(self.no_dialogo("quantidade_alterar_parcelamento"), "6")
        self.total("1.400,00")
        self.assertFalse(botao.disabled)
        self.clicar(botao)
        self.assertEqual(round(sum(self.valores(self.serie)), 2), 1400.0)

    def test_reducao_com_fixas_desabilita_pela_quantidade(self):
        db.editar_conta_ocorrencia(self.p[5], valor=210.0)
        self.abrir_dialogo()
        self.escolher(self.no_dialogo("quantidade_alterar_parcelamento"), "4")
        self.assertIn(db.MENSAGEM_REDUCAO_COM_FIXAS, self.textos_do_dialogo())
        self.assertTrue(self.aplicar().disabled)
        self.escolher(self.no_dialogo("quantidade_alterar_parcelamento"), "6")
        self.assertFalse(self.aplicar().disabled)


# ---------------------------------------------------------------- C: valor de série variável
class TestAjusteCValorVariavelSemDialogo(BaseAjustes):
    def setUp(self):
        super().setUp()
        # Luz: ago (150, conhecida), set..dez pendentes; outubro informado (130).
        self.serie, self.ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-08-10", "mensal",
                                                         data_termino="2026-12", variavel=True)
        db.editar_conta_ocorrencia(self.ids[2], valor=130.0)

    def modelo(self):
        return self.consultar("SELECT valor FROM series_recorrencia WHERE id = ?", (self.serie,))[0][0]

    def salvar(self):
        self.clicar(self.botao("Salvar alterações"))

    def test_informar_pendente_sem_dialogo(self):
        self.abrir_editar("Luz")                                                  # setembro (pendente)
        self.digitar("Valor", "175,00")
        self.salvar()
        self.assertEqual(self.dlg().title.value, "Alteração salva")
        self.assertEqual(self.valores(self.serie), [150.0, 175.0, 130.0, 0.0, 0.0])
        self.assertEqual(self.pendentes(), {self.ids[3], self.ids[4]})           # futuras continuam pendentes
        self.assertEqual(self.modelo(), 150.0)

    def test_valor_conhecido_so_desta_ocorrencia(self):
        pagamentos.registrar_pagamento_parcial(self.ids[0], 20_00, "2026-08-15")
        pagos = self.consultar("SELECT * FROM pp_pagamentos ORDER BY id")
        self.abrir_editar("Luz", mes="proximo_mes")                              # outubro (130)
        self.digitar("Valor", "220,00")
        self.salvar()
        self.assertEqual(self.dlg().title.value, "Alteração salva")
        self.assertEqual(self.valores(self.serie), [150.0, 0.0, 220.0, 0.0, 0.0])
        self.assertEqual(self.pendentes(), {self.ids[1], self.ids[3], self.ids[4]})
        self.assertEqual(self.modelo(), 150.0)
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"), pagos)

    def test_valor_abaixo_do_pago_recusado_sem_dialogo(self):
        pagamentos.registrar_pagamento_parcial(self.ids[2], 100_00, "2026-09-10")
        antes = self.estado()
        self.abrir_editar("Luz", mes="proximo_mes")
        self.digitar("Valor", "80,00")
        self.salvar()
        self.assertNotEqual(self.dlg().title.value, "Como deseja aplicar esta alteração?")
        self.assertEqual(self.estado(), antes)

    def test_outro_campo_mantem_o_dialogo(self):
        for campos in ({"Nome da conta": "Energia"}, {"Nome da conta": "Energia", "Valor": "160,00"}):
            with self.subTest(campos=list(campos)):
                self.abrir_editar("Luz", mes="proximo_mes")
                for rotulo, texto in campos.items():
                    self.digitar(rotulo, texto)
                self.salvar()
                self.assertEqual(self.dlg().title.value, "Como deseja aplicar esta alteração?")
                textos = self.textos_do_dialogo()
                self.assertEqual(main.TEXTO_AVISO_R5 in textos, "Valor" in campos)
                self.clicar(self.acao("Cancelar"))
                self.assertEqual(self.valores(self.serie), [150.0, 0.0, 130.0, 0.0, 0.0])

    def test_outro_campo_com_valor_em_diante_segue_r5(self):
        self.abrir_editar("Luz", mes="proximo_mes")
        self.digitar("Nome da conta", "Energia")
        self.digitar("Valor", "160,00")
        self.salvar()
        self.clicar(self.acao("Este mês em diante"))
        self.assertEqual(self.valores(self.serie), [150.0, 0.0, 160.0, 0.0, 0.0])
        self.assertEqual(self.modelo(), 160.0)                                   # R5: o modelo muda
        self.assertEqual(self.pendentes(), {self.ids[1], self.ids[3], self.ids[4]})

    def test_serie_fixa_continua_com_dialogo(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "mensal",
                                               data_termino="2026-12")
        self.abrir_editar("Aluguel")
        self.digitar("Valor", "950,00")
        self.salvar()
        self.assertEqual(self.dlg().title.value, "Como deseja aplicar esta alteração?")
        self.assertNotIn(main.TEXTO_AVISO_R5, self.textos_do_dialogo())
        self.clicar(self.acao("Este mês em diante"))
        self.assertEqual(self.valores(serie), [950.0] * 4)

    def test_anual_variavel_tambem(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Seguro", 640.0, "2025-09-27", "anual",
                                               data_termino="2028-12", variavel=True)
        self.abrir_editar("Seguro")
        self.digitar("Valor", "700,00")
        self.salvar()
        self.assertEqual(self.dlg().title.value, "Alteração salva")
        self.assertEqual(self.valores(serie)[:2], [640.0, 700.0])
        self.assertTrue(set(ids[2:]) <= self.pendentes())


# ---------------------------------------------------------------- D: Alterar tipo de valor
class TestAjusteDAlterarTipoDeValor(BaseAjustes):
    MENU = ["Alterar tipo de valor", "Alterar término da recorrência", "Encerrar recorrência"]  # 6.13 (E4)

    def test_menu_por_tipo(self):
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "mensal")
        db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-20", "mensal", variavel=True)
        db.criar_serie_recorrente(self.usuario_id, "IPVA", 1800.0, "2026-09-26", "anual")
        db.criar_conta_unica(self.usuario_id, "Água", 80.0, "2026-09-18")
        db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-09-22")
        _, gas = db.criar_serie_recorrente(self.usuario_id, "Gás", 60.0, "2026-09-28", "mensal",
                                           data_termino="2026-12")
        db.encerrar_recorrencia(gas[0])
        for nome, esperado in (("Aluguel", self.MENU), ("Luz", self.MENU), ("IPVA", self.MENU),
                               ("Água", ["Transformar em recorrente", "Parcelar esta conta"]), ("Sofá", ["Alterar parcelamento"]),
                               ("Gás", ["Transformar em recorrente", "Parcelar esta conta"])):
            with self.subTest(nome=nome):
                self.abrir_editar(nome)
                self.assertEqual(self.itens_do_menu(), esperado)
                self.assertNotIn("Alterar frequência", self.itens_do_menu())     # R6

    def test_fixo_para_variavel_r3_x3_e_volta_aos_detalhes(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "mensal",
                                               data_termino="2027-01")
        pagamentos.registrar_pagamento_parcial(ids[2], 100_00, "2026-09-10")    # novembro, com pagamento
        db.editar_conta_ocorrencia(ids[3], valor=950.0)                          # dezembro, editada
        pagos = self.consultar("SELECT * FROM pp_pagamentos ORDER BY id")
        self.abrir_editar("Aluguel")
        self.escolher_no_menu("Alterar tipo de valor")
        self.assertEqual(self.dlg().data, "dialogo_comportamento_valor")
        self.clicar(self.acao("Mudar para variável"))
        self.assertTrue(db.serie_variavel(serie))
        self.assertEqual(self.valores(serie)[0], 900.0)                         # a selecionada mantém
        self.assertEqual(self.pendentes() & set(ids), {ids[1], ids[4]})          # só as livres seguintes
        self.assertEqual(self.valores(serie)[2:4], [900.0, 950.0])
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"), pagos)
        self.assertTrue(self.em_detalhes())
        self.assertEqual(db.obter_info_serie(serie)["frequencia"], "mensal")    # R6

    def test_variavel_para_fixo_r4_exige_valor(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-20", "mensal",
                                               data_termino="2026-12", variavel=True)
        db.editar_conta_ocorrencia(ids[1], valor=130.0)
        self.abrir_editar("Luz")
        self.escolher_no_menu("Alterar tipo de valor")
        campo = self.no_dialogo("valor_fixo_comportamento")
        self.assertEqual(campo.value, "130,00")                                   # sugestão: último informado
        campo.value = ""
        self.clicar(self.acao("Mudar para fixo"))
        self.assertIn(db.MENSAGEM_VALOR_INVALIDO, self.textos_do_dialogo())
        self.assertTrue(db.serie_variavel(serie))
        campo.value = "140,00"
        self.clicar(self.acao("Mudar para fixo"))
        self.assertFalse(db.serie_variavel(serie))
        self.assertEqual(self.valores(serie), [150.0, 130.0, 140.0, 140.0])      # informado preservado
        self.assertEqual(self.pendentes() & set(ids), set())
        self.assertTrue(self.em_detalhes())

    def test_r4a_recusa_com_pendente_anterior(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-08-10", "mensal",
                                               data_termino="2026-12", variavel=True)
        antes = self.estado()
        self.abrir_editar("Luz", mes="proximo_mes")                              # outubro; setembro pendente
        self.escolher_no_menu("Alterar tipo de valor")
        self.assertIn(db.MENSAGEM_PENDENTES_ANTERIORES, self.textos_do_dialogo())
        self.no_dialogo("valor_fixo_comportamento").value = "150,00"
        self.clicar(self.acao("Mudar para fixo"))
        self.assertIn(db.MENSAGEM_PENDENTES_ANTERIORES, self.textos_do_dialogo())
        self.assertEqual(self.estado(), antes)
        self.clicar(self.acao("Cancelar"))
        self.assertTrue(self.em_editar())

    def test_r4a_botao_cinza_desabilitado_e_reabilitado(self):
        # Validação final (07/11): com a recusa R4-A já conhecida ao abrir, "Mudar para fixo" fica
        # cinza e desabilitado, com o motivo visível; corrigida a condição, volta a habilitar.
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-08-10", "mensal",
                                               data_termino="2026-12", variavel=True)
        db.editar_conta_ocorrencia(ids[2], valor=150.0)                         # outubro conhecido
        antes = self.estado()
        self.abrir_editar("Luz", mes="proximo_mes")                              # outubro; setembro pendente
        self.escolher_no_menu("Alterar tipo de valor")
        botao = self.acao("Mudar para fixo")
        self.assertTrue(botao.disabled)
        self.assertEqual((botao.bgcolor, botao.color),
                         (CLARO["botao_desabilitado_fundo"], CLARO["botao_desabilitado_texto"]))
        self.assertIn(db.MENSAGEM_PENDENTES_ANTERIORES, self.textos_do_dialogo())  # o motivo
        botao.on_click(Evento(self.pagina, botao))                               # mesmo clicado à força
        self.assertEqual(self.estado(), antes)
        self.assertTrue(db.serie_variavel(serie))
        with self.assertRaises(db.ValorVariavelRecusadoError):                   # o banco continua recusando
            db.tornar_fixa(ids[2], 150.0)
        self.clicar(self.acao("Cancelar"))
        db.editar_conta_ocorrencia(ids[1], valor=140.0)                         # setembro informado
        self.abrir_editar("Luz", mes="proximo_mes")
        self.escolher_no_menu("Alterar tipo de valor")
        botao = self.acao("Mudar para fixo")
        self.assertFalse(botao.disabled)
        self.assertEqual((botao.bgcolor, botao.color), (CLARO["acao_primaria"], CLARO["texto_sobre_acao"]))
        self.assertNotIn(db.MENSAGEM_PENDENTES_ANTERIORES, self.textos_do_dialogo())
        self.no_dialogo("valor_fixo_comportamento").value = "160,00"
        self.clicar(botao)
        self.assertFalse(db.serie_variavel(serie))
        self.assertEqual(self.valores(serie), [150.0, 140.0, 150.0, 160.0, 160.0])

    def test_r4a_cenario_da_validacao_manual(self):
        # Nov/2026 R$ 100 · Dez/2026 pendente · Jan/2027 R$ 150 -- converter em janeiro é impedido.
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Teste bloqueio R4-A", 100.0, "2026-11-10",
                                               "mensal", data_termino="2027-03", variavel=True)
        db.editar_conta_ocorrencia(ids[2], valor=150.0)
        self.assertEqual(db.previa_tornar_fixa(ids[2])["recusa"], db.MENSAGEM_PENDENTES_ANTERIORES)
        self.assertIsNone(db.previa_tornar_fixa(ids[1])["recusa"])              # em dezembro, permitido

    def test_fixo_para_variavel_nao_fica_desabilitado(self):
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "mensal")
        self.abrir_editar("Aluguel")
        self.escolher_no_menu("Alterar tipo de valor")
        botao = self.acao("Mudar para variável")
        self.assertFalse(botao.disabled)
        self.assertEqual(botao.bgcolor, CLARO["acao_primaria"])

    def test_encerramento_pendente_tira_a_conversao(self):
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "mensal",
                                  data_termino="2026-12")
        self.abrir_editar("Aluguel")
        self.escolher_no_menu("Encerrar recorrência")
        self.clicar(self.acao("Encerrar recorrência"))
        self.assertEqual(self.itens_do_menu(), ["Desfazer esta alteração"])     # nunca as duas juntas
        self.escolher_no_menu("Desfazer esta alteração")
        self.assertEqual(self.itens_do_menu(), self.MENU)

    def test_alteracao_nao_salva_impede_converter(self):
        serie, _ = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "mensal")
        self.abrir_editar("Aluguel")
        self.digitar("Valor", "990,00")
        antes = self.estado()
        self.escolher_no_menu("Alterar tipo de valor")
        self.assertEqual(self.dlg().title.value, "Há alterações não salvas")
        self.clicar(self.acao("Entendi"))
        self.assertEqual(self.estado(), antes)
        self.assertFalse(db.serie_variavel(serie))
        self.assertEqual(self.campo("Valor").value, "990,00")

    def test_anual(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "IPVA", 1800.0, "2026-09-26", "anual",
                                               data_termino="2029-12")
        self.abrir_editar("IPVA")
        self.escolher_no_menu("Alterar tipo de valor")
        self.clicar(self.acao("Mudar para variável"))
        self.assertTrue(db.serie_variavel(serie))
        self.assertEqual(db.obter_info_serie(serie)["frequencia"], "anual")
        self.assertEqual(self.pendentes() & set(ids), set(ids[1:]))

    def test_d1_conversao_so_em_editar(self):
        # Decisão D1 (07/11): o botão "Mudar para valor fixo/variável" saiu dos Detalhes.
        db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "mensal")
        db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-20", "mensal", variavel=True)
        db.criar_serie_recorrente(self.usuario_id, "IPVA", 1800.0, "2026-09-26", "anual")
        for nome in ("Aluguel", "Luz", "IPVA"):
            with self.subTest(nome=nome):
                self.entrar()
                self.clicar(self.linha(nome))
                self.assertEqual([c for c in self.controles() if getattr(c, "data", None) == "mudar_comportamento_valor"],
                                 [])
                textos = [getattr(c, "content", None) for c in self.controles()] + self.textos()
                self.assertFalse([t for t in textos if isinstance(t, str) and t.startswith("Mudar para valor")])
                self.clicar(self.botao("Editar"))
                self.assertEqual(self.itens_do_menu(), self.MENU)
                self.escolher_no_menu("Alterar tipo de valor")
                self.assertEqual(self.dlg().data, "dialogo_comportamento_valor")
                self.clicar(self.acao("Cancelar"))


if __name__ == "__main__":
    unittest.main()
