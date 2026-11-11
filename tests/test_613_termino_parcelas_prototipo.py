"""
Protótipo 6.13 -- melhorias finais de Editar conta e Parcelamento (ambiente isolado; dados fictícios).

A. Quantidade de parcelas: o mesmo controle digitável com setas (2 a 36) em Nova conta,
   Parcelar esta conta e Alterar parcelamento; cálculos e regras continuam no banco.
B. "Alterar término da recorrência" (decisões da autora B1-B7, 11/11/2026): antecipar,
   prorrogar e remover o término de uma série ativa mensal ou anual, fixa ou variável, como
   rascunho gravado no Salvar; proteção do histórico igual à de "Encerrar recorrência".
Hoje fixo: 15/09/2026 (no app e no banco), salvo quando o teste muda a data.
"""

import unittest
from datetime import date, datetime
from unittest import mock

from apoio_banco import DataFixa, TesteComBancoTemporario, db
from test_613_editar_detalhes_prototipo import MENU_SERIE, Base as BaseEditar
from test_613_nova_conta_prototipo import Base as BaseNovaConta
from test_tela_principal import Evento, percorrer

import flet as ft  # noqa: E402
import main  # noqa: E402
import pagamentos  # noqa: E402

ITEM = "Alterar término da recorrência"
MENSAL = ["2026-09-20", "2026-10-20", "2026-11-20", "2026-12-20", "2027-01-20", "2027-02-20", "2027-03-20",
          "2027-04-20", "2027-05-20", "2027-06-20", "2027-07-20", "2027-08-20", "2027-09-20"]


def com_banco_na_data_fixa(teste):
    """O banco também usa `date.today()` (B1); o mesmo DataFixa do app."""
    patcher = mock.patch.object(db, "date", DataFixa)
    patcher.start()
    teste.addCleanup(patcher.stop)


def mudar_hoje(teste, dia):
    patcher = mock.patch.object(DataFixa, "hoje", dia)
    patcher.start()
    teste.addCleanup(patcher.stop)


class AuxiliaresDeBanco:
    def vencimentos(self, serie_id):
        return [d for (d,) in self.consultar(
            "SELECT data_vencimento FROM contas WHERE serie_id = ? ORDER BY data_vencimento", (serie_id,))]

    def serie(self, serie_id):
        return self.consultar("SELECT data_termino, horizonte_gerado_ate, ativa FROM series_recorrencia "
                              "WHERE id = ?", (serie_id,))[0]

    def pendentes(self):
        return {i for (i,) in self.consultar(f"SELECT conta_id FROM {db.TABELA_VALOR_PENDENTE}")}

    def tudo(self):
        return (self.consultar("SELECT * FROM contas ORDER BY id"),
                self.consultar("SELECT * FROM series_recorrencia ORDER BY id"),
                self.consultar(f"SELECT * FROM {db.TABELA_PAGAMENTOS} ORDER BY id"),
                self.consultar(f"SELECT * FROM {db.TABELA_VALOR_PENDENTE} ORDER BY conta_id"))


# ====================================================================== B -- banco
class TestTerminoNoBanco(AuxiliaresDeBanco, TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        com_banco_na_data_fixa(self)
        self.usuario_id = self.criar_usuario()

    def mensal(self, nome="Aluguel", **opcoes):
        return db.criar_serie_recorrente(self.usuario_id, nome, 900.0, "2026-09-20", "mensal", **opcoes)

    # ------------------------------------------------------------ antecipar / prorrogar / remover
    def test_antecipar_mensal_fixa_exclui_as_seguintes_sem_historico(self):
        serie, ids = self.mensal()
        self.assertEqual(self.vencimentos(serie), MENSAL)
        resultado = db.alterar_termino_recorrencia(ids[0], "2027-01")
        self.assertEqual(self.vencimentos(serie), MENSAL[:5])
        self.assertEqual(self.serie(serie), ("2027-01", "2027-01-20", 1))
        self.assertEqual((resultado["removidas"], resultado["preservadas"], resultado["novas"]), (ids[5:], [], []))
        self.assertEqual(db.gerar_ocorrencias_sob_demanda(serie, "2028-12"), [])   # com término: nada volta

    def test_prorrogar_gera_ate_o_novo_termino_inclusive(self):
        serie, ids = self.mensal(data_termino="2026-12")
        self.assertEqual(self.vencimentos(serie), MENSAL[:4])
        resultado = db.alterar_termino_recorrencia(ids[0], "2027-03")
        self.assertEqual(self.vencimentos(serie), MENSAL[:7])
        self.assertEqual(self.serie(serie), ("2027-03", "2027-03-20", 1))
        self.assertEqual(len(resultado["novas"]), 3)
        posicoes = [p for (p,) in self.consultar("SELECT posicao FROM contas WHERE serie_id = ? "
                                                 "ORDER BY data_vencimento", (serie,))]
        self.assertEqual(posicoes, list(range(1, 8)))
        novas = self.consultar("SELECT nome, valor, status FROM contas WHERE id IN (?, ?, ?)", resultado["novas"])
        self.assertEqual(set(novas), {("Aluguel", 900.0, "pendente")})          # copiam o modelo da série

    def test_remover_termino_volta_a_ser_aberta(self):
        serie, ids = self.mensal(data_termino="2026-12")
        db.alterar_termino_recorrencia(ids[0], None)
        self.assertEqual(self.serie(serie)[0], None)
        self.assertEqual(self.vencimentos(serie), MENSAL)                      # 12 meses, como na criação
        self.assertEqual(len(db.gerar_ocorrencias_sob_demanda(serie, "2027-12")), 3)   # e a geração continua

    def test_anual_fixa_limite_inclusivo_b7(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "IPVA", 1800.0, "2026-09-26", "anual",
                                               data_termino="2030-09")
        self.assertEqual(len(ids), 5)
        db.alterar_termino_recorrencia(ids[0], "2028-08")                       # agosto: antes da cobrança
        self.assertEqual(self.vencimentos(serie), ["2026-09-26", "2027-09-26"])
        db.alterar_termino_recorrencia(ids[0], "2028-09")                       # setembro: inclui 2028
        self.assertEqual(self.vencimentos(serie), ["2026-09-26", "2027-09-26", "2028-09-26"])
        self.assertEqual(self.serie(serie)[0], "2028-09")

    def test_anual_variavel_novas_nascem_com_valor_pendente(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Seguro", 700.0, "2026-09-26", "anual",
                                               data_termino="2027-09", variavel=True)
        resultado = db.alterar_termino_recorrencia(ids[0], "2029-09")
        self.assertEqual(self.vencimentos(serie), ["2026-09-26", "2027-09-26", "2028-09-26", "2029-09-26"])
        self.assertTrue(set(resultado["novas"]) <= self.pendentes())
        self.assertEqual(len(resultado["novas"]), 2)

    def test_mensal_variavel_antecipar_apaga_as_marcas_de_valor_pendente(self):
        serie, ids = self.mensal(variavel=True)
        db.alterar_termino_recorrencia(ids[0], "2026-11")
        self.assertEqual(self.vencimentos(serie), MENSAL[:3])
        self.assertTrue(self.pendentes() <= set(ids[:3]))
        self.assertEqual(self.consultar(f"SELECT COUNT(*) FROM {db.TABELA_VALOR_PENDENTE} "
                                        "WHERE conta_id NOT IN (SELECT id FROM contas)"), [(0,)])

    # ------------------------------------------------------------ B2/B3: histórico protegido
    def test_protegidas_ficam_alem_do_termino_e_a_prorrogacao_nao_as_duplica(self):
        serie, ids = self.mensal()
        pagamentos.registrar_pagamento_parcial(ids[6], 100_00, "2026-09-10")       # pagamento ativo
        pagamentos.registrar_pagamento_parcial(ids[7], 100_00, "2026-09-10")
        self.executar(f"UPDATE {db.TABELA_PAGAMENTOS} SET estornado_em = '2026-09-11T10:00:00' "
                      "WHERE conta_id = ?", (ids[7],))                              # estornado
        self.executar("UPDATE contas SET status = 'pago', data_pagamento = '2026-09-01' WHERE id = ?",
                      (ids[8],))                                                   # paga antes da 6.10
        db.editar_conta_ocorrencia(ids[9], nome="Aluguel ajustado")                # editada individualmente
        pagos = self.consultar(f"SELECT * FROM {db.TABELA_PAGAMENTOS} ORDER BY id")

        previa = db.previa_alteracao_termino(ids[0], "2027-01")
        self.assertEqual(previa["preservadas"], MENSAL[6:10])
        self.assertEqual(previa["removidas"], 4)
        db.alterar_termino_recorrencia(ids[0], "2027-01")
        restantes = [i for (i,) in self.consultar("SELECT id FROM contas WHERE serie_id = ? ORDER BY id", (serie,))]
        self.assertEqual(restantes, ids[:5] + ids[6:10])
        self.assertEqual(self.consultar(f"SELECT * FROM {db.TABELA_PAGAMENTOS} ORDER BY id"), pagos)
        self.assertEqual(self.consultar("SELECT status, data_pagamento FROM contas WHERE id = ?", (ids[8],)),
                         [("pago", "2026-09-01")])
        self.assertEqual(self.consultar("SELECT nome FROM contas WHERE id = ?", (ids[9],)), [("Aluguel ajustado",)])
        self.assertEqual(self.serie(serie), ("2027-01", "2027-01-20", 1))

        resultado = db.alterar_termino_recorrencia(ids[0], "2027-09")             # prorrogar: só as vagas livres
        self.assertEqual(len(resultado["novas"]), 4)
        competencias = [d[:7] for d in self.vencimentos(serie)]
        self.assertEqual(competencias, [d[:7] for d in MENSAL])                   # uma por mês, sem duplicar

    # ------------------------------------------------------------ B1: término mínimo
    def test_atrasadas_nunca_sao_excluidas_b1(self):
        serie, ids = self.mensal()
        mudar_hoje(self, date(2026, 11, 15))                                     # setembro e outubro venceram
        with self.assertRaises(db.TerminoRecusadoError) as recusa:
            db.alterar_termino_recorrencia(ids[0], "2026-10")
        self.assertEqual(str(recusa.exception), "O término não pode ser anterior a novembro de 2026.")
        self.assertEqual(self.vencimentos(serie), MENSAL)
        db.alterar_termino_recorrencia(ids[0], "2026-11")
        self.assertEqual(self.vencimentos(serie), MENSAL[:3])
        self.assertEqual(self.consultar("SELECT status FROM contas WHERE id IN (?, ?)", ids[:2]),
                         [("pendente",), ("pendente",)])                         # atrasadas sem pagamento ficam

    def test_minimo_pela_ocorrencia_em_edicao_e_pelo_vencimento_ainda_nao_salvo(self):
        serie, ids = self.mensal()
        self.assertEqual(db.previa_alteracao_termino(ids[0], None)["minimo"], "2026-09")
        with self.assertRaisesRegex(db.TerminoRecusadoError, "dezembro de 2026"):
            db.previa_alteracao_termino(ids[3], "2026-11")                      # editando dezembro
        with self.assertRaisesRegex(db.TerminoRecusadoError, "dezembro de 2026"):
            db.previa_alteracao_termino(ids[0], "2026-10", referencia="2026-12-05")

    def test_anteriores_a_ocorrencia_em_edicao_nao_sao_tocadas(self):
        serie, ids = self.mensal()
        db.alterar_termino_recorrencia(ids[3], "2026-12")
        self.assertEqual([i for (i,) in self.consultar("SELECT id FROM contas WHERE serie_id = ? ORDER BY id",
                                                       (serie,))], ids[:4])

    # ------------------------------------------------------------ B6: elegibilidade
    def test_nao_elegiveis_sao_recusados_sem_gravar(self):
        unica = db.criar_conta_unica(self.usuario_id, "Água", 80.0, "2026-09-18")
        db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-09-22")
        parcela = self.consultar("SELECT id FROM contas WHERE nome = 'Sofá' ORDER BY data_vencimento")[0][0]
        _, gas = self.mensal("Gás", data_termino="2026-12")
        db.encerrar_recorrencia(gas[0])
        antes = self.tudo()
        for conta in (unica, parcela, gas[0], 999_999):
            with self.subTest(conta=conta):
                with self.assertRaises(db.TerminoRecusadoError) as recusa:
                    db.alterar_termino_recorrencia(conta, "2027-06")
                self.assertEqual(str(recusa.exception), db.MENSAGEM_TERMINO_SO_RECORRENCIA_ATIVA)
        _, ids = self.mensal()
        antes = self.tudo()
        for invalido in ("2026-13", "2026-00", "27-01", "2027/01", 202701):
            with self.subTest(termino=invalido):
                with self.assertRaises(db.TerminoRecusadoError) as recusa:
                    db.alterar_termino_recorrencia(ids[0], invalido)
                self.assertEqual(str(recusa.exception), db.MENSAGEM_TERMINO_INVALIDO)
        self.assertEqual(self.tudo(), antes)

    def test_mesmo_termino_nao_muda_nada(self):
        _, ids = self.mensal(data_termino="2027-03")
        antes = self.tudo()
        self.assertTrue(db.previa_alteracao_termino(ids[0], "2027-03")["sem_mudanca"])
        db.alterar_termino_recorrencia(ids[0], "2027-03")
        self.assertEqual(self.tudo(), antes)

    # ------------------------------------------------------------ B5: transação única
    def test_falha_depois_de_excluir_desfaz_tudo(self):
        _, ids = self.mensal()
        antes = self.tudo()
        with mock.patch.object(db, "_inserir_vagas_no_cursor", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                db.alterar_termino_recorrencia(ids[0], "2027-01")
        self.assertEqual(self.tudo(), antes)

    def test_falha_depois_de_inserir_desfaz_tudo(self):
        _, ids = self.mensal(data_termino="2026-12", variavel=True)
        antes = self.tudo()
        with mock.patch.object(db, "_renumerar_segmento", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                db.alterar_termino_recorrencia(ids[0], "2027-06")
        self.assertEqual(self.tudo(), antes)

    # ------------------------------------------------------------ B3/B4: avisos da prévia
    def test_avisos_da_previa(self):
        _, aberta = self.mensal()
        self.assertFalse(db.previa_alteracao_termino(aberta[0], "2027-01")["recriacao"])
        self.assertTrue(db.previa_alteracao_termino(aberta[0], None)["sem_mudanca"])
        _, com_termino = self.mensal("Luz", data_termino="2027-01")
        self.assertTrue(db.previa_alteracao_termino(com_termino[0], "2027-06")["recriacao"])    # prorrogar
        self.assertTrue(db.previa_alteracao_termino(com_termino[0], None)["recriacao"])         # remover
        self.assertFalse(db.previa_alteracao_termino(com_termino[0], "2026-12")["recriacao"])   # antecipar

    def test_remover_termino_criado_pela_exclusao_recria_os_meses_b4(self):
        serie, ids = self.mensal()
        db.excluir_conta_serie(ids[6])                                          # "Este mês em diante" (Fase 3.10)
        self.assertEqual(self.serie(serie)[0], "2027-02")
        self.assertTrue(db.previa_alteracao_termino(ids[0], None)["recriacao"])
        db.alterar_termino_recorrencia(ids[0], None)                            # aprovado pela autora (B4)
        self.assertEqual(self.vencimentos(serie), MENSAL)

    def test_geracao_sob_demanda_continua_igual(self):
        serie, ids = self.mensal(variavel=True)
        novas = db.gerar_ocorrencias_sob_demanda(serie, "2028-03")
        self.assertEqual(len(novas), 6)
        self.assertTrue(set(novas) <= self.pendentes())
        self.assertEqual(db.gerar_ocorrencias_sob_demanda(serie, "2028-03"), [])


# ====================================================================== B -- tela
class BaseTermino(AuxiliaresDeBanco, BaseEditar):
    def setUp(self):
        super().setUp()
        com_banco_na_data_fixa(self)

    def abrir_termino(self):
        self.escolher_item(ITEM)
        self.assertEqual(self.dlg().data, "dialogo_alterar_termino")

    def d(self, data):
        return self.no_dialogo(data)

    def escolher_termino(self, mes, ano):
        chave = self.d("sem_termino_alterar")
        if chave.value:
            self.mudar_chave(chave, False)
        self.escolher(self.d("mes_termino_alterar"), str(mes))
        self.escolher(self.d("ano_termino_alterar"), str(ano))

    def confirmar(self):
        self.clicar(self.acao("Confirmar"))

    def salvar(self):
        self.clicar(self.botao_salvar())

    def escolher_data(self, nova_data):
        self.clicar(self.campo("Data de vencimento").suffix_icon)
        seletor = self.dlg()
        self.assertIsInstance(seletor, ft.DatePicker)
        seletor.value = datetime.fromisoformat(nova_data)
        seletor.on_change(Evento(self.pagina, seletor))
        seletor.open = False


class TestAlterarTerminoTela(BaseTermino):
    def aluguel(self, **opcoes):
        return db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-20", "mensal", **opcoes)

    def test_menu_so_em_series_ativas_b6(self):
        self.aluguel()
        db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-21", "mensal", variavel=True)
        db.criar_serie_recorrente(self.usuario_id, "IPVA", 1800.0, "2026-09-26", "anual")
        db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-09-22")
        db.criar_conta_unica(self.usuario_id, "Água", 80.0, "2026-09-18")
        _, gas = db.criar_serie_recorrente(self.usuario_id, "Gás", 60.0, "2026-09-28", "mensal",
                                           data_termino="2026-12")
        db.encerrar_recorrencia(gas[0])
        for nome in ("Aluguel", "Luz", "IPVA"):
            with self.subTest(nome=nome):
                self.abrir_editar(nome)
                self.assertEqual(self.itens(), MENU_SERIE)
        for nome in ("Sofá", "Água", "Gás"):
            with self.subTest(nome=nome):
                self.abrir_editar(nome)
                self.assertNotIn(ITEM, self.itens())

    def test_sem_termino_salvo_abre_ativado_com_mes_ano_desabilitados(self):
        self.aluguel()
        self.abrir_editar("Aluguel")
        self.abrir_termino()
        chave, linha = self.d("sem_termino_alterar"), self.d("termino_alterar")
        mes, ano = self.d("mes_termino_alterar"), self.d("ano_termino_alterar")
        self.assertTrue(chave.value)
        self.assertEqual((mes.disabled, ano.disabled, linha.opacity), (True, True, 0.45))
        self.assertEqual((mes.value, ano.value), ("9", "2026"))                  # o mínimo (B1)
        self.assertIn("a partir de setembro de 2026", self.d("minimo_termino_alterar").value)
        self.mudar_chave(chave, False)
        self.assertEqual((mes.disabled, ano.disabled, linha.opacity), (False, False, 1.0))
        self.mudar_chave(chave, True)
        self.assertEqual((mes.disabled, ano.disabled, linha.opacity), (True, True, 0.45))
        self.assertEqual(self.dlg().title.value, "Alterar término da recorrência")
        self.assertTrue(self.dlg().modal)
        self.assertEqual([b.content for b in self.dlg().actions], ["Cancelar", "Confirmar"])

    def test_termino_salvo_aparece_no_dialogo(self):
        self.aluguel(data_termino="2027-09")
        self.abrir_editar("Aluguel")
        self.assertEqual(self.recorrencia().value, "Mensal · Fixo · Até set/2027")
        self.abrir_termino()
        self.assertFalse(self.d("sem_termino_alterar").value)
        self.assertEqual((self.d("mes_termino_alterar").value, self.d("ano_termino_alterar").value), ("9", "2027"))
        self.assertFalse(self.d("mes_termino_alterar").disabled)
        for aviso in ("aviso_exclusao_termino", "aviso_preservadas_termino", "aviso_recriacao_termino"):
            self.assertFalse(self.d(aviso).visible)

    def test_antecipar_como_rascunho_e_gravar_no_salvar(self):
        serie, _ = self.aluguel()
        self.abrir_editar("Aluguel")
        self.abrir_termino()
        self.escolher_termino(1, 2027)
        self.assertEqual(self.d("aviso_exclusao_termino").value,
                         "8 ocorrências sem pagamentos depois do novo término serão excluídas ao salvar.")
        self.confirmar()
        self.assertEqual(self.recorrencia().value, "Mensal · Fixo · Até jan/2027")
        self.assertEqual(self.recorrencia().helper, "Alteração pendente: será aplicada ao salvar.")
        self.assertEqual(self.itens(), ["Desfazer esta alteração"])               # B5: nada de tipo/Encerrar
        self.assertEqual(len(self.vencimentos(serie)), 13)                         # nada gravado ainda
        self.assertFalse(self.botao_salvar().disabled)
        self.salvar()
        self.assertEqual(self.vencimentos(serie), MENSAL[:5])
        self.assertEqual(self.serie(serie)[0], "2027-01")
        self.assertIn("Você alterou o término da recorrência para janeiro de 2027.", self.textos_do_dialogo())

    def test_cancelar_desfazer_e_abandonar_nao_gravam(self):
        self.aluguel()
        antes = self.tudo()
        self.abrir_editar("Aluguel")
        self.abrir_termino()
        self.escolher_termino(1, 2027)
        self.clicar(self.acao("Cancelar"))
        self.assertEqual(self.itens(), MENU_SERIE)
        self.assertEqual(self.recorrencia().value, "Mensal · Fixo · Sem término")
        self.abrir_termino()
        self.escolher_termino(1, 2027)
        self.confirmar()
        self.escolher_item("Desfazer esta alteração")
        self.assertEqual(self.itens(), MENU_SERIE)
        self.assertTrue(self.botao_salvar().disabled)
        self.abrir_termino()
        self.escolher_termino(1, 2027)
        self.confirmar()
        self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Cancelar"))   # sai de Editar
        self.assertTrue(self.existe("tela_detalhes"))
        self.assertEqual(self.tudo(), antes)

    def test_aviso_b3_lista_os_vencimentos_preservados(self):
        serie, ids = self.aluguel()
        pagamentos.registrar_pagamento_parcial(ids[6], 100_00, "2026-09-10")
        db.editar_conta_ocorrencia(ids[8], nome="Aluguel de maio")
        self.abrir_editar("Aluguel")
        self.abrir_termino()
        self.escolher_termino(1, 2027)
        aviso = self.d("aviso_preservadas_termino")
        self.assertTrue(aviso.visible)
        self.assertEqual(aviso.content.value, "Estas ocorrências têm pagamentos ou edição individual e continuarão "
                                              "registradas depois do novo término: 20/03/2027, 20/05/2027.")
        self.assertEqual(self.d("aviso_exclusao_termino").value,
                         "6 ocorrências sem pagamentos depois do novo término serão excluídas ao salvar.")
        self.confirmar()
        self.salvar()
        self.assertEqual(self.vencimentos(serie), MENSAL[:5] + ["2027-03-20", "2027-05-20"])

    def test_remover_termino_mostra_o_aviso_b4_e_grava(self):
        serie, _ = self.aluguel(data_termino="2026-12")
        self.abrir_editar("Aluguel")
        self.abrir_termino()
        self.assertFalse(self.d("aviso_recriacao_termino").visible)
        self.mudar_chave(self.d("sem_termino_alterar"), True)
        aviso = self.d("aviso_recriacao_termino")
        self.assertTrue(aviso.visible)
        self.assertEqual(aviso.content.value, main.TEXTO_AVISO_RECRIACAO_TERMINO)
        self.confirmar()
        self.assertEqual(self.recorrencia().value, "Mensal · Fixo · Sem término")
        self.salvar()
        self.assertEqual(self.serie(serie)[0], None)
        self.assertEqual(self.vencimentos(serie), MENSAL)
        self.assertIn("Você deixou a recorrência sem data de término.", self.textos_do_dialogo())

    def test_prorrogar_mostra_o_aviso_b4_e_grava(self):
        serie, _ = self.aluguel(data_termino="2026-12")
        self.abrir_editar("Aluguel")
        self.abrir_termino()
        self.escolher_termino(3, 2027)
        self.assertTrue(self.d("aviso_recriacao_termino").visible)
        self.assertFalse(self.d("aviso_exclusao_termino").visible)
        self.confirmar()
        self.salvar()
        self.assertEqual(self.vencimentos(serie), MENSAL[:7])

    def test_abaixo_do_minimo_recusa_e_desabilita_confirmar(self):
        self.aluguel()
        self.abrir_editar("Aluguel")
        self.abrir_termino()
        self.escolher_termino(8, 2026)
        self.assertEqual(self.d("erro_termino").value, "O término não pode ser anterior a setembro de 2026.")
        botao = self.acao("Confirmar")
        self.assertTrue(botao.disabled)
        cinza = botao.bgcolor
        self.confirmar()                                                           # bloqueio funcional
        self.assertEqual(self.dlg().data, "dialogo_alterar_termino")
        self.assertEqual(self.itens(), MENU_SERIE)                                 # nenhum rascunho
        self.escolher_termino(9, 2026)
        self.assertEqual(self.d("erro_termino").value, "")
        self.assertFalse(botao.disabled)
        self.assertNotEqual(botao.bgcolor, cinza)                                  # cinza só enquanto recusado

    def test_anual_variavel_pela_tela(self):
        serie, _ = db.criar_serie_recorrente(self.usuario_id, "IPVA", 1800.0, "2026-09-26", "anual",
                                             data_termino="2030-09", variavel=True)
        self.abrir_editar("IPVA")
        self.abrir_termino()
        self.escolher_termino(12, 2027)
        self.assertEqual(self.d("aviso_exclusao_termino").value,
                         "3 ocorrências sem pagamentos depois do novo término serão excluídas ao salvar.")
        self.confirmar()
        self.assertEqual(self.recorrencia().value, "Anual · Variável · Até dez/2027")
        self.salvar()
        self.assertEqual(self.vencimentos(serie), ["2026-09-26", "2027-09-26"])

    def test_conflito_b5_com_vencimento_em_este_mes_em_diante(self):
        serie, ids = self.aluguel()
        antes = self.tudo()
        self.abrir_editar("Aluguel")
        self.abrir_termino()
        self.escolher_termino(1, 2027)
        self.confirmar()
        self.escolher_data("2026-09-25")
        self.salvar()
        self.clicar(self.acao("Este mês em diante"))
        self.assertIn(main.TEXTO_TERMINO_COM_VENCIMENTO_EM_DIANTE, self.textos())
        self.assertEqual(self.tudo(), antes)                                       # nada gravado
        self.salvar()
        self.clicar(self.acao("Somente este mês"))                                 # um caminho válido
        self.assertEqual(self.vencimentos(serie), ["2026-09-25"] + MENSAL[1:5])
        self.assertEqual(self.serie(serie)[0], "2027-01")

    def test_vencimento_ainda_nao_salvo_entra_no_minimo_b1_b5(self):
        serie, _ = self.aluguel()
        antes = self.tudo()
        self.abrir_editar("Aluguel")
        self.abrir_termino()
        self.escolher_termino(10, 2026)
        self.confirmar()
        self.escolher_data("2026-11-05")
        self.salvar()
        self.assertIn("O término não pode ser anterior a novembro de 2026.", self.textos())
        self.assertFalse(any(d.open for d in self.pagina.dialogos))                # nem o diálogo de escopo
        self.assertEqual(self.tudo(), antes)

    def test_falha_ao_aplicar_nao_grava(self):
        self.aluguel()
        antes = self.tudo()
        self.abrir_editar("Aluguel")
        self.abrir_termino()
        self.escolher_termino(1, 2027)
        self.confirmar()
        with mock.patch.object(main.database, "_inserir_vagas_no_cursor", side_effect=RuntimeError("falha")):
            with self.assertRaises(RuntimeError):
                self.salvar()
        self.assertEqual(self.tudo(), antes)                                       # rollback integral

    def test_janela_estreita_empilha_e_larga_lado_a_lado(self):
        self.aluguel()
        for largura, tipo in ((380, ft.Column), (1000, ft.Row)):
            with self.subTest(largura=largura):
                self.pagina.width = 1200
                self.abrir_editar("Aluguel")
                self.pagina.width = largura
                self.abrir_termino()
                self.assertIsInstance(self.d("termino_alterar"), tipo)
                self.clicar(self.acao("Cancelar"))


# ====================================================================== A -- quantidade de parcelas
ASSINATURA = ("Quantidade de parcelas", ft.KeyboardType.NUMBER, r"^[0-9]{0,2}$",
              [("aumentar_parcelas", "Aumentar a quantidade de parcelas"),
               ("diminuir_parcelas", "Diminuir a quantidade de parcelas")])


def assinatura(campo):
    setas = [c for c in percorrer(campo.suffix_icon) if isinstance(c, ft.IconButton)]
    return (campo.label, campo.keyboard_type, campo.input_filter.regex_string,
            [(s.data, s.icon.semantics_label) for s in setas])


class BaseParcelas(AuxiliaresDeBanco, BaseEditar):
    def setas(self, campo):
        """As setas ficam dentro do campo (suffix_icon), fora do alcance de `percorrer`."""
        setas = {c.data: c for c in percorrer(campo.suffix_icon) if isinstance(c, ft.IconButton)}
        return setas["aumentar_parcelas"], setas["diminuir_parcelas"]

    def linhas(self):
        return [t for t in self.textos_do_dialogo() if t and t.startswith("Parcela ")]

    def sair(self, campo):
        campo.on_blur(Evento(self.pagina, campo))


class TestQuantidadeEmParcelar(BaseParcelas):
    def setUp(self):
        super().setUp()
        self.conta = db.criar_conta_unica(self.usuario_id, "Notebook", 1000.0, "2026-09-30")
        self.abrir_editar("Notebook")
        self.escolher_item("Parcelar esta conta")
        self.campo_q = self.no_dialogo("quantidade_parcelas_parcelar")

    def test_mesmo_controle_digitavel_com_setas(self):
        self.assertIsInstance(self.campo_q, ft.TextField)
        self.assertEqual(assinatura(self.campo_q), ASSINATURA)
        self.assertEqual(self.campo_q.value, "2")
        mais, menos = self.setas(self.campo_q)
        self.assertEqual((mais.disabled, menos.disabled), (False, True))          # 2: no mínimo
        self.clicar(mais)
        self.assertEqual(self.campo_q.value, "3")
        self.assertEqual(len(self.linhas()), 3)
        self.clicar(menos)
        self.assertEqual(self.campo_q.value, "2")
        self.digitar(self.campo_q, "36")
        self.assertEqual((mais.disabled, menos.disabled), (True, False))          # 36: no máximo
        self.assertEqual(len(self.linhas()), 36)
        self.clicar(mais)
        self.assertEqual(self.campo_q.value, "36")

    def test_digitacao_e_distribuicao_dos_centavos(self):
        self.digitar(self.campo_q, "7")
        valores = [linha.rsplit("R$ ", 1)[1] for linha in self.linhas()]
        esperado = [main.formatar_moeda(c / 100)[3:] for c in db.dividir_em_parcelas(1000_00, 7)]
        self.assertEqual(valores, esperado)                                         # 142,90 + 6 x 142,85
        self.assertEqual(self.linhas()[0], "Parcela 1 de 7 · 30/09/2026 · R$ 142,90")

    def test_valores_invalidos_nao_gravam(self):
        antes = self.tudo()
        for texto in ("1", "37", "", "0"):
            with self.subTest(texto=texto):
                self.digitar(self.campo_q, texto)
                self.assertEqual(self.linhas(), [])
                self.assertIn(db.MENSAGEM_QUANTIDADE_DE_PARCELAS, self.textos_do_dialogo())
                self.clicar(self.acao("Parcelar"))
                self.assertEqual(self.dlg().data, "dialogo_parcelar")                # continua aberto
        self.assertEqual(self.tudo(), antes)
        self.digitar(self.campo_q, "")
        self.sair(self.campo_q)                                                      # vazio volta ao último válido
        self.assertEqual(self.campo_q.value, "2")
        self.digitar(self.campo_q, "40")
        self.sair(self.campo_q)
        self.assertEqual(self.campo_q.error, db.MENSAGEM_QUANTIDADE_DE_PARCELAS)
        self.clicar(self.setas(self.campo_q)[1])                                      # seta parte do digitado
        self.assertEqual((self.campo_q.value, self.campo_q.error), ("36", None))

    def test_cancelar_nao_grava_e_confirmar_grava(self):
        antes = self.tudo()
        self.digitar(self.campo_q, "4")
        self.clicar(self.acao("Cancelar"))
        self.assertEqual(self.tudo(), antes)
        self.escolher_item("Parcelar esta conta")
        campo = self.no_dialogo("quantidade_parcelas_parcelar")
        self.assertEqual(campo.value, "2")                                           # diálogo novo
        self.digitar(campo, "4")
        self.clicar(self.acao("Parcelar"))
        serie_id = self.consultar("SELECT serie_id FROM contas WHERE id = ?", (self.conta,))[0][0]
        self.assertEqual(db.obter_identificacao(serie_id, self.conta), {"tipo": "parcela", "posicao": 1, "total": 4})
        self.assertTrue(self.existe("tela_detalhes"))


class TestQuantidadeComPagamento(BaseParcelas):
    def test_conta_com_pagamento_continua_recusada(self):
        conta = db.criar_conta_unica(self.usuario_id, "TV", 900.0, "2026-09-30")
        pagamentos.registrar_pagamento_parcial(conta, 100_00, "2026-09-10")
        antes = self.tudo()
        self.abrir_editar("TV")
        self.escolher_item("Parcelar esta conta")
        self.assertEqual(self.dlg().data, "dialogo_parcelar_recusado")
        self.assertEqual(self.dlg().content.value, db.MENSAGEM_UNICA_COM_PAGAMENTOS)
        self.clicar(self.acao("Entendi"))
        self.assertEqual(self.tudo(), antes)


class TestQuantidadeEmAlterarParcelamento(BaseParcelas):
    def setUp(self):
        super().setUp()
        db.criar_conta_parcelada(self.usuario_id, "Sofá", 1200.0, 6, "2026-09-22")
        self.ids = [i for (i,) in self.consultar("SELECT id FROM contas WHERE nome = 'Sofá' ORDER BY data_vencimento")]

    def abrir(self):
        self.abrir_editar("Sofá")
        self.escolher_item("Alterar parcelamento")
        self.assertEqual(self.dlg().data, "dialogo_alterar_parcelamento")
        return self.no_dialogo("quantidade_alterar_parcelamento")

    def test_mesmo_controle_com_a_quantidade_atual(self):
        campo = self.abrir()
        self.assertIsInstance(campo, ft.TextField)
        self.assertEqual(assinatura(campo), ASSINATURA)
        self.assertEqual(campo.value, "6")
        self.clicar(self.setas(campo)[0])
        self.assertEqual(campo.value, "7")
        self.assertEqual(len(self.linhas()), 7)

    def test_invalida_desabilita_aplicar_e_valida_grava(self):
        campo = self.abrir()
        antes = self.tudo()
        self.digitar(campo, "1")
        self.assertIn(db.MENSAGEM_QUANTIDADE_DE_PARCELAS, self.textos_do_dialogo())
        aplicar = self.no_dialogo_acao("Aplicar")
        self.assertTrue(aplicar.disabled)
        self.clicar(aplicar)
        self.assertEqual(self.tudo(), antes)
        self.digitar(campo, "4")
        self.assertFalse(aplicar.disabled)
        self.assertEqual(len(self.linhas()), 4)
        self.assertIn("2 parcela(s) sem pagamentos do fim serão excluídas.", self.textos_do_dialogo())
        self.clicar(aplicar)
        valores = [v for (v,) in self.consultar("SELECT valor FROM contas WHERE nome = 'Sofá' ORDER BY data_vencimento")]
        self.assertEqual(valores, [300.0] * 4)

    def test_com_pagamento_a_parcela_e_mantida(self):
        pagamentos.registrar_pagamento_parcial(self.ids[0], 50_00, "2026-09-10")
        campo = self.abrir()
        self.digitar(campo, "3")
        self.assertTrue(self.linhas()[0].endswith("· com pagamentos (mantida)"))
        previa = db.previa_alteracao_parcelamento(self.ids[0], novo_total=1200.0, nova_quantidade=3)
        self.assertEqual(len(self.linhas()), len(previa["parcelas"]))

    def test_cancelar_nao_grava(self):
        campo = self.abrir()
        antes = self.tudo()
        self.digitar(campo, "12")
        self.clicar(self.acao("Cancelar"))
        self.assertEqual(self.tudo(), antes)

    def no_dialogo_acao(self, texto):
        return next(b for b in self.dlg().actions if b.content == texto)


class TestQuantidadeNaNovaConta(BaseNovaConta):
    def test_nova_conta_usa_o_mesmo_controle(self):
        self.tipo("parcelada")
        campo = self.campo("Quantidade de parcelas")
        self.assertEqual(assinatura(campo), ASSINATURA)
        self.assertEqual(campo.data, "quantidade_parcelas_nova_conta")
        mais = self.com_data("aumentar_parcelas")
        self.clicar(mais)
        self.assertEqual(campo.value, "3")
        self.escrever("Valor total da conta", "100,00")
        self.assertEqual(self.com_data("valor_por_parcela_estimado").value, "R$ 33,33 (1ª: R$ 33,34)")


if __name__ == "__main__":
    unittest.main()
