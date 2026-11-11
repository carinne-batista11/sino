"""
Protótipo 6.13 -- correções finais de Editar conta (ambiente isolado; dados fictícios).

1. Atomicidade: com um término pendente, o Salvar grava os campos do formulário ("Somente este
   mês" ou "Este mês em diante") e o término numa ÚNICA transação
   (`db.salvar_edicao_com_termino`). Falhas reais são provocadas por gatilhos SQLite que abortam
   (RAISE(ABORT)) em cada etapa -- exclusão, geração e atualização do término -- e por falhas
   simuladas antes da primeira gravação; em todas, nada fica gravado.
2. Rodapé de Editar: "Cancelar" com recuo lateral menor (cabe numa linha em 320 px).
Hoje fixo: 15/09/2026 (no app e no banco).
"""

import sqlite3
import unittest
from unittest import mock

from apoio_banco import TesteComBancoTemporario, db
from test_613_termino_parcelas_prototipo import (MENSAL, AuxiliaresDeBanco, BaseTermino,
                                                 com_banco_na_data_fixa)
from test_tela_principal import Evento, percorrer

import flet as ft  # noqa: E402
import main  # noqa: E402
import pagamentos  # noqa: E402

GATILHOS = {
    "exclusao": "BEFORE DELETE ON contas",
    "geracao": "BEFORE INSERT ON contas",
    "termino": "BEFORE UPDATE OF data_termino ON series_recorrencia",
}


class GatilhosDeFalha:
    def falhar_em(self, etapa):
        """Uma falha REAL do banco na etapa: o gatilho aborta a instrução (sqlite3.IntegrityError)."""
        self.executar(f"CREATE TRIGGER falha_{etapa} {GATILHOS[etapa]} "
                      f"BEGIN SELECT RAISE(ABORT, 'falha simulada: {etapa}'); END")
        self.addCleanup(self.executar, f"DROP TRIGGER IF EXISTS falha_{etapa}")

    def sem_gatilhos(self):
        for etapa in GATILHOS:
            self.executar(f"DROP TRIGGER IF EXISTS falha_{etapa}")


# ====================================================================== banco
class TestSalvamentoAtomicoNoBanco(GatilhosDeFalha, AuxiliaresDeBanco, TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        com_banco_na_data_fixa(self)
        self.usuario_id = self.criar_usuario()
        self.serie_id, self.ids = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-20", "mensal")

    def nomes_e_valores(self):
        return self.consultar("SELECT nome, valor FROM contas WHERE serie_id = ? ORDER BY data_vencimento",
                              (self.serie_id,))

    # ------------------------------------------------------------ sucesso (alterações combinadas)
    def test_somente_este_mes_com_termino(self):
        resultado = db.salvar_edicao_com_termino(self.ids[0], "somente_este_mes", "2027-01", nome="Aluguel set",
                                                 valor=950.0, data_vencimento="2026-09-25")
        self.assertEqual(len(resultado["removidas"]), 8)
        self.assertEqual(self.consultar("SELECT nome, valor, data_vencimento, editado_individualmente FROM contas "
                                        "WHERE id = ?", (self.ids[0],)), [("Aluguel set", 950.0, "2026-09-25", 1)])
        self.assertEqual(self.vencimentos(self.serie_id), ["2026-09-25"] + MENSAL[1:5])
        self.assertEqual(self.serie_(), "2027-01")

    def test_este_mes_em_diante_com_termino(self):
        db.salvar_edicao_com_termino(self.ids[0], "este_mes_em_diante", "2027-01", nome="Aluguel novo",
                                     valor=1000.0, descricao="Contrato de 2026")
        self.assertEqual(self.nomes_e_valores(), [("Aluguel novo", 1000.0)] * 5)
        self.assertEqual(self.consultar("SELECT nome, valor, descricao FROM series_recorrencia WHERE id = ?",
                                        (self.serie_id,)), [("Aluguel novo", 1000.0, "Contrato de 2026")])
        self.assertEqual(self.serie_(), "2027-01")

    def test_prorrogar_com_campos_gera_ja_com_o_modelo_novo(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-21", "mensal",
                                               data_termino="2026-12")
        db.salvar_edicao_com_termino(ids[0], "este_mes_em_diante", "2027-03", nome="Energia")
        nomes = [n for (n,) in self.consultar("SELECT nome FROM contas WHERE serie_id = ?", (serie,))]
        self.assertEqual(nomes, ["Energia"] * 7)                        # as 3 novas nascem com o nome novo

    def serie_(self):
        return self.serie(self.serie_id)[0]

    # ------------------------------------------------------------ falhas: nada fica gravado
    def test_falha_antes_de_qualquer_gravacao(self):
        antes = self.tudo()
        for escopo, nucleo in (("somente_este_mes", "_editar_conta_ocorrencia_no_cursor"),
                               ("este_mes_em_diante", "_editar_conta_serie_no_cursor")):
            with self.subTest(escopo=escopo):
                with mock.patch.object(db, nucleo, side_effect=RuntimeError("falha simulada")):
                    with self.assertRaises(RuntimeError):
                        db.salvar_edicao_com_termino(self.ids[0], escopo, "2027-01", nome="Outro")
                self.assertEqual(self.tudo(), antes)

    def test_falha_depois_dos_campos_na_exclusao(self):
        antes = self.tudo()
        self.falhar_em("exclusao")
        for escopo in ("somente_este_mes", "este_mes_em_diante"):
            with self.subTest(escopo=escopo):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "falha simulada: exclusao"):
                    db.salvar_edicao_com_termino(self.ids[0], escopo, "2027-01", nome="Outro", valor=990.0)
                self.assertEqual(self.tudo(), antes)                     # nome e valor desfeitos também

    def test_falha_na_geracao(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-21", "mensal",
                                               data_termino="2026-12")
        antes = self.tudo()
        self.falhar_em("geracao")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "falha simulada: geracao"):
            db.salvar_edicao_com_termino(ids[0], "este_mes_em_diante", "2027-06", nome="Energia")
        self.assertEqual(self.tudo(), antes)

    def test_falha_na_atualizacao_do_termino_depois_de_excluir_e_gerar(self):
        antes = self.tudo()
        self.falhar_em("termino")
        for escopo in ("somente_este_mes", "este_mes_em_diante"):
            with self.subTest(escopo=escopo):
                with self.assertRaisesRegex(sqlite3.IntegrityError, "falha simulada: termino"):
                    db.salvar_edicao_com_termino(self.ids[0], escopo, "2027-01", nome="Outro")
                self.assertEqual(self.tudo(), antes)

    def test_falha_ao_remover_o_termino(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-21", "mensal",
                                               data_termino="2026-12")
        antes = self.tudo()
        self.falhar_em("termino")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "falha simulada: termino"):
            db.salvar_edicao_com_termino(ids[0], "este_mes_em_diante", None, nome="Energia")
        self.assertEqual(self.tudo(), antes)

    def test_recusa_do_termino_desfaz_os_campos(self):
        antes = self.tudo()
        with self.assertRaisesRegex(db.TerminoRecusadoError, "setembro de 2026"):
            db.salvar_edicao_com_termino(self.ids[0], "este_mes_em_diante", "2026-08", nome="Outro")
        # "Somente este mês" movendo a ocorrência para novembro: o mínimo (B1) passa a ser novembro.
        with self.assertRaisesRegex(db.TerminoRecusadoError, "novembro de 2026"):
            db.salvar_edicao_com_termino(self.ids[0], "somente_este_mes", "2026-10", data_vencimento="2026-11-05")
        self.assertEqual(self.tudo(), antes)

    def test_recusa_dos_campos_nao_grava_o_termino(self):
        pagamentos.registrar_pagamento_parcial(self.ids[0], 500_00, "2026-09-10")
        antes = self.tudo()
        with self.assertRaises(db.ValorMenorQuePagoError):
            db.salvar_edicao_com_termino(self.ids[0], "este_mes_em_diante", "2027-01", valor=100.0)
        self.assertFalse(db.salvar_edicao_com_termino(999_999, "somente_este_mes", "2027-01", nome="X"))
        self.assertEqual(self.tudo(), antes)

    def test_conflito_b5_no_banco(self):
        antes = self.tudo()
        with self.assertRaises(db.TerminoRecusadoError) as recusa:
            db.salvar_edicao_com_termino(self.ids[0], "este_mes_em_diante", "2027-01", data_vencimento="2026-09-25")
        self.assertEqual(str(recusa.exception), db.MENSAGEM_TERMINO_COM_VENCIMENTO_EM_DIANTE)
        with self.assertRaises(ValueError):
            db.salvar_edicao_com_termino(self.ids[0], "outro", "2027-01", nome="X")
        self.assertEqual(self.tudo(), antes)

    # ------------------------------------------------------------ pagamentos e histórico
    def test_pagamentos_e_historico_integros_na_falha_e_no_sucesso(self):
        pagamentos.registrar_pagamento_parcial(self.ids[0], 900_00, "2026-09-10")      # quitada
        pagamentos.registrar_pagamento_parcial(self.ids[6], 100_00, "2026-09-10")      # parcial (mar/2027)
        pagamentos.registrar_pagamento_parcial(self.ids[7], 100_00, "2026-09-10")
        self.executar(f"UPDATE {db.TABELA_PAGAMENTOS} SET estornado_em = '2026-09-11T10:00:00' "
                      "WHERE conta_id = ?", (self.ids[7],))                             # estornado
        diferenca = {"registrar": True, "esperado": (900_00, 900_00)}                 # registrar R$ 100,00
        (tipo_da_quitacao,) = self.consultar(f"SELECT tipo FROM {db.TABELA_PAGAMENTOS} WHERE conta_id = ?",
                                             (self.ids[0],))[0]
        antes = self.tudo()
        self.falhar_em("termino")
        with self.assertRaises(sqlite3.IntegrityError):
            db.salvar_edicao_com_termino(self.ids[0], "somente_este_mes", "2027-01", valor=1000.0,
                                         pp_diferenca=diferenca)
        self.assertEqual(self.tudo(), antes)                     # nem o pagamento da diferença ficou
        self.sem_gatilhos()
        db.salvar_edicao_com_termino(self.ids[0], "somente_este_mes", "2027-01", valor=1000.0,
                                     pp_diferenca=diferenca)
        self.assertEqual(self.consultar(f"SELECT valor_centavos, tipo FROM {db.TABELA_PAGAMENTOS} "
                                        "WHERE conta_id = ? ORDER BY id", (self.ids[0],)),
                         [(900_00, tipo_da_quitacao), (100_00, "saldo")])
        self.assertEqual(self.consultar("SELECT status FROM contas WHERE id = ?", (self.ids[0],)), [("pago",)])
        consulta = f"SELECT * FROM {db.TABELA_PAGAMENTOS} WHERE conta_id IN (?, ?) ORDER BY id"
        self.assertEqual(self.consultar(consulta, (self.ids[6], self.ids[7])),
                         [p for p in antes[2] if p in self.consultar(consulta, (self.ids[6], self.ids[7]))])
        self.assertEqual(len(self.consultar(consulta, (self.ids[6], self.ids[7]))), 2)
        self.assertEqual(self.vencimentos(self.serie_id), MENSAL[:5] + MENSAL[6:8])   # B2/B3: ficam

    # ------------------------------------------------------------ as funções de sempre continuam iguais
    def test_editar_conta_serie_sozinha_continua_transacional(self):
        db.editar_conta_serie(self.ids[3], nome="Aluguel dezembro")
        self.assertEqual([n for (n,) in self.consultar("SELECT nome FROM contas WHERE serie_id = ? "
                                                       "ORDER BY data_vencimento", (self.serie_id,))],
                         ["Aluguel"] * 3 + ["Aluguel dezembro"] * 10)
        antes = self.tudo()
        self.executar("CREATE TRIGGER falha_modelo BEFORE UPDATE ON series_recorrencia "
                      "BEGIN SELECT RAISE(ABORT, 'falha simulada: modelo'); END")
        self.addCleanup(self.executar, "DROP TRIGGER IF EXISTS falha_modelo")
        with self.assertRaises(sqlite3.IntegrityError):
            db.editar_conta_serie(self.ids[0], nome="Outro", valor=990.0)           # contas antes, modelo depois
        self.assertEqual(self.tudo(), antes)

    def test_parcela_em_diante_e_avulsa_pelo_mesmo_caminho(self):
        db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-09-22")
        parcelas = [i for (i,) in self.consultar("SELECT id FROM contas WHERE nome = 'Sofá' ORDER BY data_vencimento")]
        self.assertTrue(db.editar_conta_serie(parcelas[1], nome="Sofá novo"))
        self.assertEqual([n for (n,) in self.consultar("SELECT nome FROM contas WHERE id IN (?, ?, ?) ORDER BY id",
                                                       parcelas)], ["Sofá", "Sofá novo", "Sofá novo"])
        with self.assertRaises(db.ParcelamentoRecusadoError):
            db.editar_conta_serie(parcelas[1], valor=250.0)                          # regra da 6.12 mantida
        avulsa = db.criar_conta_unica(self.usuario_id, "Água", 80.0, "2026-09-18")
        self.assertTrue(db.editar_conta_serie(avulsa, nome="Água e esgoto"))
        self.assertEqual(self.consultar("SELECT nome FROM contas WHERE id = ?", (avulsa,)), [("Água e esgoto",)])


# ====================================================================== tela
class TestSalvamentoAtomicoNaTela(GatilhosDeFalha, BaseTermino):
    def aluguel(self, **opcoes):
        return db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-20", "mensal", **opcoes)

    def mudar_campo(self, rotulo, texto):
        campo = self.campo(rotulo)
        campo.value = texto
        campo.on_change(Evento(self.pagina, campo))

    def preparar(self):
        serie, ids = self.aluguel()
        self.abrir_editar("Aluguel")
        self.mudar_campo("Nome da conta", "Aluguel novo")
        self.abrir_termino()
        self.escolher_termino(1, 2027)
        self.confirmar()
        return serie, ids

    def test_nome_e_termino_em_este_mes_em_diante_gravados_juntos(self):
        serie, _ = self.preparar()
        self.salvar()
        self.clicar(self.acao("Este mês em diante"))
        self.assertEqual(self.consultar("SELECT DISTINCT nome FROM contas WHERE serie_id = ?", (serie,)),
                         [("Aluguel novo",)])
        self.assertEqual(self.vencimentos(serie), MENSAL[:5])
        textos = self.textos_do_dialogo()
        self.assertTrue(any("Você alterou o nome de 'Aluguel' para 'Aluguel novo'." in t for t in textos), textos)
        self.assertTrue(any("Você alterou o término da recorrência para janeiro de 2027." in t for t in textos))

    def test_falha_inesperada_no_salvar_nao_grava_nada(self):
        for escopo in ("Somente este mês", "Este mês em diante"):
            with self.subTest(escopo=escopo):
                self.sem_gatilhos()
                self.executar("DELETE FROM contas")
                self.executar("DELETE FROM series_recorrencia")
                self.preparar()
                antes = self.tudo()
                self.falhar_em("termino")
                self.salvar()
                with self.assertRaisesRegex(sqlite3.IntegrityError, "falha simulada: termino"):
                    self.clicar(self.acao(escopo))
                self.assertEqual(self.tudo(), antes)                       # nem o nome ficou gravado

    def test_variavel_so_valor_e_termino_juntos(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-21", "mensal", variavel=True)
        self.abrir_editar("Luz")
        self.mudar_campo("Valor", "170,00")                       # variável, só o valor: sem diálogo de escopo
        self.abrir_termino()
        self.escolher_termino(12, 2026)
        self.confirmar()
        antes = self.tudo()
        self.falhar_em("exclusao")
        with self.assertRaises(sqlite3.IntegrityError):
            self.salvar()
        self.assertEqual(self.tudo(), antes)
        self.sem_gatilhos()
        self.salvar()
        self.assertEqual(self.consultar("SELECT valor FROM contas WHERE id = ?", (ids[0],)), [(170.0,)])
        self.assertEqual(self.vencimentos(serie), ["2026-09-21", "2026-10-21", "2026-11-21", "2026-12-21"])

    def test_sem_termino_pendente_os_campos_seguem_o_caminho_de_sempre(self):
        serie, _ = self.aluguel()
        self.abrir_editar("Aluguel")
        self.mudar_campo("Nome da conta", "Aluguel novo")
        with mock.patch.object(main.database, "salvar_edicao_com_termino") as combinado:
            self.salvar()
            self.clicar(self.acao("Este mês em diante"))
        combinado.assert_not_called()
        self.assertEqual(self.consultar("SELECT DISTINCT nome FROM contas WHERE serie_id = ?", (serie,)),
                         [("Aluguel novo",)])
        self.assertEqual(len(self.vencimentos(serie)), 13)


# ====================================================================== rodapé
class TestRodapeDeEditar(BaseTermino):
    def test_cancelar_com_recuo_menor_e_mesmas_colunas(self):
        db.criar_conta_unica(self.usuario_id, "Notebook", 1000.0, "2026-09-30")
        self.abrir_editar("Notebook")
        rodape = next(c for c in self.controles(ft.Container) if c.data == "pp_rodape_edicao")
        botoes = [c for c in percorrer(rodape) if isinstance(c, ft.Button)]
        self.assertEqual([b.content for b in botoes], ["Cancelar", "Salvar alterações"])   # ordem do Tab
        cancelar, salvar = botoes
        self.assertEqual(cancelar.style.padding, ft.Padding(4, 0, 4, 0))
        self.assertEqual(salvar.style.padding, ft.Padding(8, 0, 8, 0))                     # Salvar como antes
        self.assertEqual((cancelar.col, salvar.col), ({"xs": 4, "sm": 3, "md": 2}, {"xs": 8, "sm": 5, "md": 3}))
        self.assertEqual((cancelar.height, salvar.height), (44, 44))
        self.assertTrue(salvar.disabled)
        self.clicar(cancelar)
        self.assertTrue(self.existe("tela_detalhes"))                                      # continua funcionando


if __name__ == "__main__":
    unittest.main()
