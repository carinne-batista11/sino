"""
Sino 6.12 (experimental) -- validação automatizada final (07/11/2026).

Lacunas cobertas aqui (o resto já está na suíte):
* R4-A no cenário exato da validação manual (nov R$ 100 · dez pendente · jan R$ 150), de ponta a
  ponta pela interface: bloqueio no diálogo, botão cinza e desabilitado, nada gravado, informar
  dezembro por Editar e conversão liberada ao reabrir, com R4/X3.
* Limite de 250 na descrição: texto colado acima do limite, criação pela tela (Única, Mensal fixa,
  Mensal variável), parcelada e edições individuais e coletivas, recusa sem alterar valor nem
  pagamentos.
* Mensagem corrigida do valor coletivo numa parcelada (Editar conta > Recorrência).
Bancos temporários; hoje fixo: 15/09/2026; nenhuma janela é aberta.
"""

import unittest
from unittest import mock

from apoio_banco import db
import limites  # noqa: E402  (depois de apoio_banco, que põe database/ no caminho)
from test_612_ajustes_validacao import BaseAjustes
from test_612_variavel_telas import CLARO
from test_descricao_250 import contador_de
from test_tela_principal import Evento

import flet as ft  # noqa: E402
import main  # noqa: E402
import pagamentos  # noqa: E402

NO_LIMITE = "d" * 249 + "👩‍💻"           # 250 caracteres percebidos
ACIMA = "c" * 300                       # texto colado acima do limite


def som_simulado():
    return mock.patch.object(main.aviso_sonoro.aviso_limite, "tocar", return_value=True)


class TestR4ACenarioDaValidacaoManual(BaseAjustes):
    def setUp(self):
        super().setUp()
        self.serie, self.ids = db.criar_serie_recorrente(self.usuario_id, "Teste bloqueio R4-A", 100.0,
                                                         "2026-11-10", "mensal", data_termino="2027-03",
                                                         variavel=True)
        db.editar_conta_ocorrencia(self.ids[2], valor=150.0)                    # janeiro/2027

    def ir_para(self, avancos):
        self.entrar()
        for _ in range(avancos):
            self.clicar(next(c for c in self.controles(ft.IconButton) if c.data == "proximo_mes"))

    def editar(self, avancos):
        self.ir_para(avancos)
        self.clicar(self.linha("Teste bloqueio R4-A"))
        self.clicar(self.botao("Editar"))

    def abrir_conversao_em_janeiro(self):
        self.editar(4)                                                          # set -> jan/2027
        self.assertEqual(self.itens_do_menu(), ["Alterar tipo de valor", "Alterar término da recorrência", "Encerrar recorrência"])
        self.escolher_no_menu("Alterar tipo de valor")
        self.assertEqual(self.dlg().data, "dialogo_comportamento_valor")
        return self.acao("Mudar para fixo")

    def test_cenario_completo(self):
        self.assertEqual(self.valores(self.serie), [100.0, 0.0, 150.0, 0.0, 0.0])
        self.assertEqual(self.pendentes(), {self.ids[1], self.ids[3], self.ids[4]})
        antes = self.estado()

        # 1) bloqueado: motivo visível, botão cinza e desabilitado, nada gravado
        botao = self.abrir_conversao_em_janeiro()
        self.assertIn(db.MENSAGEM_PENDENTES_ANTERIORES, self.textos_do_dialogo())
        self.assertTrue(botao.disabled)
        self.assertEqual((botao.bgcolor, botao.color),
                         (CLARO["botao_desabilitado_fundo"], CLARO["botao_desabilitado_texto"]))
        self.no_dialogo("valor_fixo_comportamento").value = "150,00"
        botao.on_click(Evento(self.pagina, botao))                              # acionamento indevido
        self.assertEqual(self.estado(), antes)
        self.assertEqual(self.dlg().data, "dialogo_comportamento_valor")        # continua no diálogo
        with self.assertRaises(db.ValorVariavelRecusadoError):
            db.tornar_fixa(self.ids[2], 150.0)                                  # o banco mantém a proteção
        self.assertEqual(self.estado(), antes)
        self.clicar(self.acao("Cancelar"))
        self.assertTrue(self.em_editar())

        # 2) dezembro informado por Editar (só o valor: sem diálogo de abrangência)
        self.editar(3)
        self.digitar("Valor", "120,00")
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.dlg().title.value, "Alteração salva")
        self.clicar(self.acao("Entendi"))
        self.assertEqual(self.valores(self.serie), [100.0, 120.0, 150.0, 0.0, 0.0])
        self.assertTrue(db.serie_variavel(self.serie))

        # 3) reaberto em janeiro: habilitado; R4/X3 -- janeiro mantém, fev e mar recebem o valor
        botao = self.abrir_conversao_em_janeiro()
        self.assertFalse(botao.disabled)
        self.assertEqual((botao.bgcolor, botao.color), (CLARO["acao_primaria"], CLARO["texto_sobre_acao"]))
        self.assertNotIn(db.MENSAGEM_PENDENTES_ANTERIORES, self.textos_do_dialogo())
        self.assertEqual(self.no_dialogo("valor_fixo_comportamento").value, "150,00")  # sugestão: último informado
        self.no_dialogo("valor_fixo_comportamento").value = "160,00"
        self.clicar(botao)
        self.assertFalse(db.serie_variavel(self.serie))
        self.assertEqual(self.valores(self.serie), [100.0, 120.0, 150.0, 160.0, 160.0])
        self.assertEqual(self.pendentes(), set())
        self.assertEqual(db.obter_info_serie(self.serie)["frequencia"], "mensal")   # R6
        self.assertTrue(self.em_detalhes())

    def test_em_dezembro_a_conversao_e_permitida_e_preenche_a_selecionada(self):
        botao_de = None
        self.editar(3)                                                          # dezembro (pendente)
        self.escolher_no_menu("Alterar tipo de valor")
        botao_de = self.acao("Mudar para fixo")
        self.assertFalse(botao_de.disabled)
        self.no_dialogo("valor_fixo_comportamento").value = "130,00"
        self.clicar(botao_de)
        # X3: a selecionada (pendente) recebe o valor; janeiro (informado) mantém; fev/mar recebem
        self.assertEqual(self.valores(self.serie), [100.0, 130.0, 150.0, 130.0, 130.0])

    def test_pagamentos_preservados_na_conversao(self):
        pagamentos.registrar_pagamento_parcial(self.ids[0], 40_00, "2026-09-10")
        db.editar_conta_ocorrencia(self.ids[1], valor=120.0)
        pagos = self.consultar("SELECT * FROM pp_pagamentos ORDER BY id")
        self.assertEqual(db.tornar_fixa(self.ids[2], 170.0), [self.ids[3], self.ids[4]])
        self.assertEqual(self.valores(self.serie), [100.0, 120.0, 150.0, 170.0, 170.0])
        self.assertEqual(self.consultar("SELECT * FROM pp_pagamentos ORDER BY id"), pagos)


class TestLimite250NaTela(BaseAjustes):
    def abrir_nova_conta(self):
        self.entrar()
        self.clicar(next(c for c in self.controles() if getattr(c, "data", None) == "nova_conta"))

    def descricao(self):
        return self.campo("Descrição (opcional)")

    def test_colar_acima_do_limite_e_recusado_inteiro(self):
        self.abrir_nova_conta()
        campo = self.descricao()
        with som_simulado() as tocar:
            self.digitar("Descrição (opcional)", ACIMA)                         # colagem num campo vazio
        # Sino 6.13.1: contador interno da Nova conta (6.13), lido por `contador_de`.
        self.assertEqual((campo.value, contador_de(campo), campo.helper), ("", "0/250", "Limite atingido"))
        tocar.assert_called_once_with()
        self.digitar("Descrição (opcional)", "a" * 200)
        with som_simulado():
            self.digitar("Descrição (opcional)", "a" * 200 + "b" * 60)           # colagem que passaria de 250
        self.assertEqual((campo.value, contador_de(campo)), ("a" * 200, "200/250"))  # nada cortado nem perdido
        self.digitar("Descrição (opcional)", "a" * 200 + "b" * 50)
        self.assertEqual((contador_de(campo), campo.helper), ("250/250", None))

    def preencher(self, nome, valor):
        self.nc_preencher(nome, valor, (2026, 9, 20))                          # Sino 6.13.1: rótulo do valor por tipo
        self.digitar("Descrição (opcional)", NO_LIMITE)

    def salvar_conta(self):
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Salvar conta"))

    def test_criar_unica_mensal_fixa_e_variavel_com_250(self):
        for nome, tipo, variavel in (("Água", None, False), ("Aluguel", "mensal", False), ("Luz", "mensal", True)):
            with self.subTest(nome=nome):
                self.abrir_nova_conta()
                self.preencher(nome, "90,00")
                if tipo:                                                        # Sino 6.13.1: cartões de tipo
                    self.nc_tipo(tipo)
                    if variavel:
                        self.clicar(self.nc_controle("comportamento_variavel"))
                self.salvar_conta()
                descricoes = {d for (d,) in self.consultar("SELECT descricao FROM contas WHERE nome = ?", (nome,))}
                self.assertEqual(descricoes, {NO_LIMITE})
        modelos = dict(self.consultar("SELECT nome, descricao FROM series_recorrencia"))
        self.assertEqual(modelos, {"Aluguel": NO_LIMITE, "Luz": NO_LIMITE})

    def test_parcela_somente_esta_com_250_pela_tela(self):
        serie, p = db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-09-20", descricao="Loja")
        self.abrir_editar("Sofá")
        self.digitar("Descrição (opcional)", NO_LIMITE)
        self.clicar(self.botao("Salvar alterações"))
        self.clicar(self.acao("Somente este mês"))
        self.assertEqual([d for (d,) in self.consultar(
            "SELECT descricao FROM contas WHERE serie_id = ? ORDER BY posicao", (serie,))], [NO_LIMITE, "Loja", "Loja"])
        self.assertEqual(self.valores(serie), [200.0] * 3)

    def test_variavel_descricao_em_diante_com_250_pela_tela(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-20", "mensal",
                                               data_termino="2026-12", variavel=True)
        self.abrir_editar("Luz")
        self.digitar("Descrição (opcional)", NO_LIMITE)
        self.clicar(self.botao("Salvar alterações"))
        self.assertEqual(self.dlg().title.value, "Como deseja aplicar esta alteração?")  # descrição: com diálogo
        self.clicar(self.acao("Este mês em diante"))
        self.assertEqual({d for (d,) in self.consultar("SELECT descricao FROM contas WHERE serie_id = ?", (serie,))},
                         {NO_LIMITE})
        self.assertEqual(self.pendentes(), set(ids[1:]))                      # pendentes preservadas

    def test_legada_acima_com_valor_alterado_nao_grava_nada(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Antiga", 100.0, "2026-09-25")
        pagamentos.registrar_pagamento_parcial(conta_id, 30_00, "2026-09-10")
        self.executar("UPDATE contas SET descricao = ? WHERE id = ?", ("x" * 300, conta_id))  # dado artificial
        antes = self.estado()
        self.abrir_editar("Antiga")
        self.digitar("Valor", "150,00")
        self.clicar(self.botao("Salvar alterações"))
        self.assertIn("A descrição pode ter no máximo 250 caracteres (atual: 300).", self.textos())
        self.assertEqual(self.estado(), antes)                                  # valor e pagamentos intactos


class TestLimite250NoBanco(BaseAjustes):
    def test_coletivas_e_individuais_por_tipo(self):
        _, fixa = db.criar_serie_recorrente(self.usuario_id, "Aluguel", 900.0, "2026-09-25", "anual",
                                            data_termino="2029-12")
        _, var = db.criar_serie_recorrente(self.usuario_id, "Luz", 150.0, "2026-09-20", "mensal",
                                           data_termino="2026-12", variavel=True)
        _, parc = db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-09-22")
        for ids in (fixa, var, parc):
            self.assertTrue(db.editar_conta_serie(ids[1], descricao=NO_LIMITE))
            self.assertTrue(db.editar_conta_ocorrencia(ids[0], descricao="d" * 249))
        for ids in (fixa, var, parc):
            for funcao in (db.editar_conta_ocorrencia, db.editar_conta_serie):
                antes = self.estado()
                with self.subTest(funcao=funcao.__name__), self.assertRaises(limites.LimiteDeCaracteresError):
                    funcao(ids[0], nome="Outro", descricao=NO_LIMITE + "x")
                self.assertEqual(self.estado(), antes)

    def test_recusa_com_pagamentos_nao_mexe_em_nada(self):
        serie, ids = db.criar_serie_recorrente(self.usuario_id, "Escola", 700.0, "2026-09-10", "mensal",
                                               data_termino="2026-12")
        pagamentos.registrar_pagamento_parcial(ids[0], 100_00, "2026-09-05")
        pagamentos.registrar_pagamento_parcial(ids[1], 700_00, "2026-09-06")
        antes = self.estado()
        for funcao in (db.editar_conta_ocorrencia, db.editar_conta_serie):
            with self.assertRaises(limites.LimiteDeCaracteresError):
                funcao(ids[0], valor=800.0, descricao="d" * 251)
        self.assertEqual(self.estado(), antes)

    def test_transformar_e_parcelar_preservam_descricao_de_250(self):
        conta = db.criar_conta_unica(self.usuario_id, "Geladeira", 900.0, "2026-09-30", descricao=NO_LIMITE)
        serie, ids = db.transformar_unica_em_parcelada(conta, 3)
        self.assertEqual({d for (d,) in self.consultar("SELECT descricao FROM contas WHERE serie_id = ?", (serie,))},
                         {NO_LIMITE})
        outra = db.criar_conta_unica(self.usuario_id, "Internet", 100.0, "2026-09-28", descricao=NO_LIMITE)
        serie2, _ = db.transformar_em_recorrente(outra, "mensal", data_termino="2026-12", variavel=True)
        self.assertEqual(self.consultar("SELECT descricao FROM series_recorrencia WHERE id = ?", (serie2,)),
                         [(NO_LIMITE,)])


class TestMensagemCorrigida(BaseAjustes):
    def test_valor_coletivo_em_parcelada_orienta_editar_conta(self):
        self.assertEqual(db.MENSAGEM_VALOR_COLETIVO_PARCELADA,
                         "Para mudar o valor de várias parcelas, use “Alterar parcelamento” "
                         "em Editar conta, no campo Recorrência.")
        self.assertNotIn("detalhes", db.MENSAGEM_VALOR_COLETIVO_PARCELADA.lower())
        serie, p = db.criar_conta_parcelada(self.usuario_id, "Sofá", 600.0, 3, "2026-09-20")
        antes = self.estado()
        self.abrir_editar("Sofá")
        self.digitar("Valor", "250,00")
        self.clicar(self.botao("Salvar alterações"))
        self.clicar(self.acao("Este mês em diante"))
        self.assertIn(db.MENSAGEM_VALOR_COLETIVO_PARCELADA, self.textos())
        self.assertEqual(self.estado(), antes)
        self.assertEqual(self.itens_do_menu(), ["Alterar parcelamento"])        # a orientação é verdadeira


if __name__ == "__main__":
    unittest.main()
