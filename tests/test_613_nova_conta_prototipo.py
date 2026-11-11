"""
PROTÓTIPO 6.13 (10/11/2026) -- Nova conta com Conta comum | Superconta, os quatro tipos visíveis no
formulário, Valor fixo | Valor variável no formulário, término num diálogo central e resumo estimado
das parcelas. Confere: padrões ao abrir (Conta comum e Única), campos de cada modalidade, cálculo
igual ao do banco (D3), gravação pelas mesmas funções e regras da 6.12, Superconta sem nenhuma
gravação e sem nada da F1, limites de 30 e 250 caracteres e controles focáveis com nome.
Páginas falsas e bancos temporários; "hoje" = 15/09/2026.
"""
import os
import sys
import unittest
from datetime import datetime
from unittest import mock

import apoio_banco
from apoio_banco import DataFixa, TesteComBancoTemporario, db
from test_sessao_tema import PaginaFalsa
from test_tela_principal import Evento

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))
import cores  # noqa: E402
import flet as ft  # noqa: E402
import main  # noqa: E402

CLARO = cores.PALETAS["claro"]


def percorrer(controle):
    """Como o de test_tela_principal, visitando também suffix_icon (lápis, calendário, seta)."""
    yield controle
    for atributo in ("controls", "content", "actions", "suffix_icon"):
        filho = getattr(controle, atributo, None)
        if isinstance(filho, list):
            for item in filho:
                yield from percorrer(item)
        elif isinstance(filho, ft.Control):
            yield from percorrer(filho)


class Base(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.usuario_id = self.criar_usuario(email="nova613@sino.com", senha="senha1234")
        self.pagina = PaginaFalsa().configurar()
        main.main(self.pagina)
        campos = {c.label: c for c in self.controles(ft.TextField)}
        campos["E-mail"].value, campos["Senha"].value = "nova613@sino.com", "senha1234"
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Entrar"))
        self.clicar(self.com_data("nova_conta"))

    # ------------------------------------------------------------ auxiliares
    def controles(self, tipo=None, raizes=None):
        raizes = self.pagina.controls if raizes is None else raizes
        todos = [c for raiz in raizes for c in percorrer(raiz)]
        return [c for c in todos if tipo is None or isinstance(c, tipo)]

    def clicar(self, c):
        c.on_click(Evento(self.pagina, c))

    def com_data(self, data, raizes=None):
        return next(c for c in self.controles(None, raizes) if getattr(c, "data", None) == data)

    def existe(self, data):
        return any(getattr(c, "data", None) == data for c in self.controles())

    def campo(self, rotulo):
        return next(c for c in self.controles((ft.TextField, ft.Dropdown)) if c.label == rotulo)

    def rotulos(self):
        return [c.label for c in self.controles((ft.TextField, ft.Dropdown))]

    def escrever(self, rotulo, valor):
        c = self.campo(rotulo)
        c.value = valor
        if c.on_change:
            c.on_change(Evento(self.pagina, c))

    def escolher(self, rotulo, valor):
        c = self.campo(rotulo)
        c.value = valor
        c.on_select(Evento(self.pagina, c))

    def data(self, ano, mes, dia):
        seletor = next(o for o in self.pagina.overlay if isinstance(o, ft.DatePicker))
        seletor.value = datetime(ano, mes, dia)
        seletor.on_change(Evento(self.pagina, seletor))

    def tipo(self, valor):
        self.clicar(self.com_data(f"tipo_conta_{valor}"))

    def abertos(self):
        return [d for d in self.pagina.dialogos if d.open]

    def erro(self):
        rodape = self.com_data("rodape_nova_conta")
        return rodape.content.controls[0].value

    def contagem(self, tabela):
        con = db.conectar()
        try:
            return con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        finally:
            con.close()

    def preencher(self, nome="Academia", valor="149,90"):
        self.escrever("Nome da conta", nome)
        self.escrever(self.rotulo_do_valor(), valor)
        self.data(2026, 9, 20)

    def rotulo_do_valor(self):
        return next(r for r in self.rotulos() if r and r.startswith("Valor"))

    def selecionado(self, botao):
        return any(isinstance(c, ft.Icon) and c.semantics_label == "Selecionado" for c in percorrer(botao))

    # 6.13 (término): o diálogo tem a chave "Sem data de término" e os seletores Mês e Ano.
    def abrir_termino(self):
        self.clicar(self.com_data("escolher_termino"))
        dlg = self.abertos()[-1]
        self.assertEqual(dlg.data, "dialogo_termino")
        chave = next(c for c in percorrer(dlg.content) if isinstance(c, ft.Switch))
        mes, ano = [c for c in percorrer(dlg.content) if isinstance(c, ft.Dropdown)]
        return dlg, chave, mes, ano

    def mudar_chave(self, chave, valor):
        chave.value = valor
        chave.on_change(Evento(self.pagina, chave))

    def acao_do_dialogo(self, dlg, texto):
        self.clicar(next(b for b in dlg.actions if b.content == texto))

    def definir_termino(self, mes, ano):
        dlg, chave, campo_mes, campo_ano = self.abrir_termino()
        self.mudar_chave(chave, False)
        campo_mes.value, campo_ano.value = str(mes), str(ano)
        campo_mes.on_select(Evento(self.pagina, campo_mes))
        campo_ano.on_select(Evento(self.pagina, campo_ano))
        self.acao_do_dialogo(dlg, "Confirmar")

    def consultar(self, sql, args=()):
        con = db.conectar()
        try:
            return con.execute(sql, args).fetchall()
        finally:
            con.close()


class TestAbertura(Base):
    def test_conta_comum_e_unica_selecionadas_por_padrao(self):
        self.assertTrue(self.selecionado(self.com_data("modo_comum")))
        self.assertFalse(self.selecionado(self.com_data("modo_superconta")))
        self.assertTrue(self.selecionado(self.com_data("tipo_conta_unica")))
        for outro in ("parcelada", "mensal", "anual"):
            self.assertFalse(self.selecionado(self.com_data(f"tipo_conta_{outro}")))

    def test_unica_mostra_so_os_campos_dela(self):
        # Ordem aprovada em 10/11: Nome | Categoria, Valor | Data de vencimento, Descrição.
        self.assertEqual(self.rotulos(), ["Nome da conta", "Categoria", "Valor da conta", "Data de vencimento",
                                          "Descrição (opcional)"])
        self.assertFalse(self.existe("linha_comportamento_valor"))
        self.assertFalse(self.existe("resumo_parcelas_nova_conta"))
        self.assertFalse(self.existe("termino_nova_conta"))
        textos = [c.value for c in self.controles(ft.Text)]
        self.assertIn("Conta única", textos)
        self.assertIn("A despesa é registrada uma única vez, pelo valor informado.", textos)
        faixa = [c.value for c in percorrer(self.com_data("faixa_tipo_nova_conta")) if isinstance(c, ft.Text)]
        self.assertFalse(any("fatura" in t for t in faixa))

    def test_cartoes_e_tipos_sao_botoes_focaveis(self):
        for data in ("modo_comum", "modo_superconta", "tipo_conta_unica", "tipo_conta_parcelada",
                     "tipo_conta_mensal", "tipo_conta_anual"):
            self.assertIsInstance(self.com_data(data), ft.Button)

    def test_limites_de_nome_e_descricao(self):
        # 2ª rodada: o contador fica dentro do campo, à direita (suffix_icon), e não embaixo.
        for rotulo, chave, limite in (("Nome da conta", "nome_conta", 30), ("Descrição (opcional)", "descricao", 250)):
            campo = self.campo(rotulo)
            contador = self.com_data(f"contador_{chave}_nova_conta")
            self.assertIn(contador, list(percorrer(campo.suffix_icon)))
            self.assertIsNone(campo.counter)
            self.assertEqual(contador.value, f"0/{limite}")
            self.escrever(rotulo, "a" * limite)
            self.assertEqual((contador.value, campo.helper), (f"{limite}/{limite}", None))
            self.escrever(rotulo, "a" * (limite + 1))  # recusado inteiro, como na 6.12
            self.assertEqual((campo.value, contador.value), ("a" * limite, f"{limite}/{limite}"))
            self.assertEqual(campo.helper, main.MENSAGEM_LIMITE_ATINGIDO)
            self.escrever(rotulo, "")
            self.assertEqual(contador.value, f"0/{limite}")


class TestModalidades(Base):
    def test_parcelada(self):
        # 2ª rodada: Nome | Categoria, Valor total | Quantidade, Primeiro vencimento | Valor por parcela.
        self.tipo("parcelada")
        self.assertEqual(self.rotulos(), ["Nome da conta", "Categoria", "Valor total da conta",
                                          "Quantidade de parcelas", "Primeiro vencimento",
                                          "Valor por parcela (estimado)", "Descrição (opcional)"])
        self.assertIsInstance(self.campo("Quantidade de parcelas"), ft.TextField)
        self.assertFalse(self.existe("resumo_parcelas_nova_conta"))
        estimado = self.com_data("valor_por_parcela_estimado")
        self.assertTrue(estimado.read_only)
        grade = self.com_data("grade_nova_conta")
        ordem = [getattr(cel.content, "data", None) for cel in grade.controls]
        self.assertEqual(ordem.index("valor_por_parcela_estimado"), ordem.index("data_nova_conta") + 1)
        self.assertEqual(grade.controls[ordem.index("data_nova_conta")].col, {"xs": 12, "sm": 6})
        self.assertEqual(grade.controls[ordem.index("valor_por_parcela_estimado")].col, {"xs": 12, "sm": 6})

    def informacao(self, data):
        antes = len(self.pagina.dialogos)
        self.clicar(self.com_data(data))
        novos = self.pagina.dialogos[antes:]
        self.assertEqual(len(novos), 1)
        self.assertIsInstance(novos[0], ft.SnackBar)
        return novos[0].content.value

    def test_resumo_usa_o_mesmo_calculo_do_banco(self):
        self.tipo("parcelada")
        self.escrever("Valor total da conta", "100,00")
        self.escrever("Quantidade de parcelas", "3")
        valores = db.dividir_em_parcelas(10000, 3)
        self.assertEqual(valores, [3334, 3333, 3333])
        # Nunca "3 parcelas de R$ 33,33": o campo e o "i" mostram a 1ª diferente (D3).
        self.assertEqual(self.com_data("valor_por_parcela_estimado").value, "R$ 33,33 (1ª: R$ 33,34)")
        self.assertEqual(self.informacao("info_parcelas_nova_conta"),
                         "Serão registradas 3 parcelas, com vencimento mensal: a 1ª de R$ 33,34 e as demais "
                         "de R$ 33,33.")
        self.escrever("Valor total da conta", "1.798,80")
        self.escrever("Quantidade de parcelas", "12")
        self.assertEqual(self.com_data("valor_por_parcela_estimado").value, "R$ 149,90")
        self.assertEqual(self.informacao("info_parcelas_nova_conta"),
                         "Serão registradas 12 parcelas de R$ 149,90, com vencimento mensal.")

    def test_quantidade_digitada_e_pelas_setas(self):
        self.tipo("parcelada")
        self.escrever("Valor total da conta", "120,00")
        campo = self.campo("Quantidade de parcelas")
        mais, menos = self.com_data("aumentar_parcelas"), self.com_data("diminuir_parcelas")
        self.assertEqual(campo.value, "2")
        self.assertTrue(menos.disabled)
        self.assertFalse(mais.disabled)
        self.clicar(mais)
        self.assertEqual(campo.value, "3")
        self.assertEqual(self.com_data("valor_por_parcela_estimado").value, "R$ 40,00")
        self.assertFalse(menos.disabled)
        self.escrever("Quantidade de parcelas", "35")
        self.clicar(mais)
        self.assertEqual(campo.value, "36")
        self.assertTrue(mais.disabled)
        self.clicar(mais)  # já no limite: continua 36
        self.assertEqual(campo.value, "36")
        self.clicar(menos)
        self.assertEqual(campo.value, "35")
        # Fora dos limites as setas voltam para dentro deles.
        self.escrever("Quantidade de parcelas", "50")
        self.assertTrue(mais.disabled)
        self.clicar(menos)
        self.assertEqual(campo.value, "36")
        self.escrever("Quantidade de parcelas", "1")
        self.clicar(mais)
        self.assertEqual(campo.value, "2")

    def test_quantidade_vazia_nao_numerica_e_fora_dos_limites(self):
        self.tipo("parcelada")
        self.escrever("Valor total da conta", "120,00")
        campo = self.campo("Quantidade de parcelas")
        self.escrever("Quantidade de parcelas", "12")
        for digitado in ("", "abc", "1", "0", "37", "99", " 12a"):
            self.escrever("Quantidade de parcelas", digitado)
            self.assertEqual(self.com_data("valor_por_parcela_estimado").value, "—")
            self.assertEqual(self.informacao("info_parcelas_nova_conta"), db.MENSAGEM_QUANTIDADE_DE_PARCELAS)
        # Vazio ao sair volta ao último número válido (12); fora dos limites, o campo avisa.
        self.escrever("Quantidade de parcelas", "")
        campo.on_blur(Evento(self.pagina, campo))
        self.assertEqual((campo.value, campo.error), ("12", None))
        self.assertEqual(self.com_data("valor_por_parcela_estimado").value, "R$ 10,00")
        self.escrever("Quantidade de parcelas", "40")
        campo.on_blur(Evento(self.pagina, campo))
        self.assertEqual(campo.error, db.MENSAGEM_QUANTIDADE_DE_PARCELAS)
        self.escrever("Quantidade de parcelas", "6")
        self.assertIsNone(campo.error)
        self.assertEqual(self.com_data("valor_por_parcela_estimado").value, "R$ 20,00")
        # Só aceita até dois algarismos (o filtro também barra letras ao digitar ou colar).
        self.assertEqual(campo.input_filter.regex_string, r"^[0-9]{0,2}$")

    def test_funcoes_da_quantidade(self):
        self.assertEqual([main.quantidade_de_parcelas(t) for t in ("2", "36", " 12 ", "1", "37", "", None, "x", "²")],
                         [2, 36, 12, None, None, None, None, None, None])
        self.assertEqual(main.passo_de_parcelas("36", 10, 1), 36)
        self.assertEqual(main.passo_de_parcelas("2", 10, -1), 2)
        self.assertEqual(main.passo_de_parcelas("", 10, 1), 11)
        self.assertEqual(main.passo_de_parcelas("abc", 10, -1), 9)

    def test_resumo_sem_valor_e_valor_pequeno(self):
        self.assertEqual(main.resumo_estimado_das_parcelas(None, 3)["valor"], None)
        self.assertEqual(main.resumo_estimado_das_parcelas(0.02, 3)["frase"],
                         db.MENSAGEM_VALOR_PEQUENO_PARA_PARCELAS)
        self.assertIsNone(main.resumo_estimado_das_parcelas(100, 37)["valor"])

    def test_mensal_fixo_por_padrao_e_variavel(self):
        # 2ª rodada: Tipo de valor | Valor do primeiro mês, Primeiro vencimento | Término.
        self.tipo("mensal")
        self.assertTrue(self.selecionado(self.com_data("comportamento_fixo")))
        self.assertFalse(self.selecionado(self.com_data("comportamento_variavel")))
        self.assertEqual(self.rotulos(), ["Nome da conta", "Categoria", "Valor do primeiro mês",
                                          "Primeiro vencimento", "Término da recorrência", "Descrição (opcional)"])
        grade = self.com_data("grade_nova_conta")
        ordem = [getattr(cel.content, "data", None) or getattr(cel.content, "label", None) for cel in grade.controls]
        i = ordem.index("linha_comportamento_valor")
        self.assertEqual(ordem[i:i + 4], ["linha_comportamento_valor", "valor_nova_conta", "data_nova_conta",
                                          "termino_nova_conta"])
        self.assertTrue(all(grade.controls[i + k].col == {"xs": 12, "sm": 6} for k in range(4)))
        self.assertFalse(self.existe("ajuda_valor_variavel"))
        self.clicar(self.com_data("comportamento_variavel"))
        self.assertTrue(self.selecionado(self.com_data("comportamento_variavel")))
        self.assertFalse(self.selecionado(self.com_data("comportamento_fixo")))
        self.assertIn("Valor do primeiro mês", self.rotulos())

    def test_informacao_do_tipo_de_valor_nao_muda_a_escolha(self):
        for tipo, fixo, variavel in (("mensal", "O mesmo valor todos os meses.", "O valor pode mudar a cada mês."),
                                     ("anual", "O mesmo valor todos os anos.", "O valor pode mudar a cada ano.")):
            self.tipo(tipo)
            self.clicar(self.com_data("comportamento_fixo"))
            self.assertEqual(self.informacao("info_comportamento_variavel"), variavel)
            self.assertTrue(self.selecionado(self.com_data("comportamento_fixo")))
            self.clicar(self.com_data("comportamento_variavel"))
            self.assertEqual(self.informacao("info_comportamento_fixo"), fixo)
            self.assertTrue(self.selecionado(self.com_data("comportamento_variavel")))
            self.assertNotIn("ocorrência", fixo + variavel)

    def test_anual_segue_a_mensal(self):
        self.tipo("anual")
        self.assertIn("Valor do primeiro ano", self.rotulos())
        self.assertIn("Conta recorrente anual", [c.value for c in self.controles(ft.Text)])
        self.assertTrue(self.selecionado(self.com_data("comportamento_fixo")))
        self.assertTrue(self.existe("linha_comportamento_valor"))

    def test_disposicao_do_tipo_de_valor_por_largura(self):
        esperado = {320: (False, "empilhada"), 380: (False, "empilhada"), 560: (False, "com_icone"),
                    720: (True, "com_icone"), 760: (False, "compacta"), 1000: (False, "com_icone"),
                    1300: (False, "com_icone"), None: (False, "com_icone"), mock.MagicMock(): (False, "com_icone")}
        for largura, disposicao in esperado.items():
            self.assertEqual(main.disposicao_tipo_de_valor(largura), disposicao, largura)
        # Meia coluna estreita (720 px): Tipo de valor e Término na linha toda; nenhuma meia coluna vazia.
        self.pagina.width = 720
        self.tipo("mensal")
        grade = self.com_data("grade_nova_conta")
        cols = {getattr(cel.content, "data", None): cel.col for cel in grade.controls}
        self.assertEqual(cols["linha_comportamento_valor"], 12)
        self.assertEqual(cols["termino_nova_conta"], 12)
        self.assertEqual(cols["valor_nova_conta"], {"xs": 12, "sm": 6})

    def test_valores_digitados_continuam_ao_trocar_de_tipo(self):
        self.preencher()
        for tipo in ("parcelada", "mensal", "anual", "unica"):
            self.tipo(tipo)
            self.assertEqual(self.campo("Nome da conta").value, "Academia")
            self.assertEqual(self.campo(self.rotulo_do_valor()).value, "149,90")

    def test_termino_no_dialogo_cancelar_e_confirmar(self):
        # 6.13: o padrão é "Sem data de término"; Cancelar nunca muda o formulário.
        self.tipo("mensal")
        self.assertEqual(self.campo("Término da recorrência").value, "Sem data de término")
        dlg, chave, mes, ano = self.abrir_termino()
        self.mudar_chave(chave, False)
        mes.value = "12"
        mes.on_select(Evento(self.pagina, mes))
        self.acao_do_dialogo(dlg, "Cancelar")
        self.assertEqual(self.campo("Término da recorrência").value, "Sem data de término")
        dlg, chave, mes, ano = self.abrir_termino()
        self.assertTrue(chave.value)                     # o rascunho cancelado não ficou guardado
        self.assertEqual((mes.value, ano.value), ("9", "2026"))
        self.acao_do_dialogo(dlg, "Cancelar")
        self.definir_termino(12, 2026)
        self.assertEqual(self.campo("Término da recorrência").value, "Até dezembro de 2026")
        dlg, chave, mes, ano = self.abrir_termino()
        self.assertFalse(chave.value)
        self.assertEqual((mes.value, ano.value, mes.disabled, ano.disabled), ("12", "2026", False, False))
        self.mudar_chave(chave, True)
        self.acao_do_dialogo(dlg, "Cancelar")
        self.assertEqual(self.campo("Término da recorrência").value, "Até dezembro de 2026")
        dlg, chave, mes, ano = self.abrir_termino()
        self.mudar_chave(chave, True)
        self.acao_do_dialogo(dlg, "Confirmar")
        self.assertEqual(self.campo("Término da recorrência").value, "Sem data de término")

    def test_nova_recorrencia_comeca_sem_termino(self):
        for tipo in ("mensal", "anual"):
            for comportamento in ("fixo", "variavel"):
                with self.subTest(tipo=tipo, comportamento=comportamento):
                    self.tipo(tipo)
                    self.clicar(self.com_data(f"comportamento_{comportamento}"))
                    self.assertEqual(self.campo("Término da recorrência").value, "Sem data de término")
                    self.assertNotIn("Até", self.campo("Término da recorrência").value)

    def test_dialogo_mes_e_ano_visiveis_e_desabilitados_com_sem_termino(self):
        for tipo in ("mensal", "anual"):
            with self.subTest(tipo=tipo):
                self.tipo(tipo)
                dlg, chave, mes, ano = self.abrir_termino()
                linha = next(c for c in dlg.content.controls if mes in getattr(c, "controls", []))
                self.assertTrue(chave.value)
                self.assertTrue(linha.visible)
                self.assertEqual((mes.disabled, ano.disabled, linha.opacity), (True, True, 0.45))
                self.mudar_chave(chave, False)
                self.assertEqual((mes.disabled, ano.disabled, linha.opacity), (False, False, 1.0))
                self.mudar_chave(chave, True)
                self.assertEqual((mes.disabled, ano.disabled, linha.opacity), (True, True, 0.45))
                self.assertTrue(linha.visible)
                self.acao_do_dialogo(dlg, "Cancelar")

    def test_dialogo_estreito_tambem_desabilita(self):
        self.pagina.width = 380
        self.tipo("anual")
        dlg, chave, mes, ano = self.abrir_termino()
        linha = next(c for c in dlg.content.controls if mes in getattr(c, "controls", []))
        self.assertIsInstance(linha, ft.Column)
        self.assertEqual((linha.visible, mes.disabled, ano.disabled), (True, True, True))


class TestGravacaoIgualA612(Base):
    def salvar(self):
        self.clicar(self.com_data("salvar_nova_conta"))

    def test_unica(self):
        self.preencher()
        self.salvar()
        contas = db.listar_contas(self.usuario_id)
        self.assertEqual([(c["nome"], c["valor"], c["data_vencimento"]) for c in contas],
                         [("Academia", 149.9, "2026-09-20")])

    def test_valor_obrigatorio_tambem_no_variavel(self):
        self.tipo("mensal")
        self.clicar(self.com_data("comportamento_variavel"))
        self.preencher(valor="")
        antes = self.contagem("contas")
        self.salvar()
        self.assertEqual(self.erro(), "Informe um valor válido.")
        self.assertEqual(self.contagem("contas"), antes)

    def test_mensal_variavel_primeira_com_valor_e_demais_pendentes(self):
        self.tipo("mensal")
        self.clicar(self.com_data("comportamento_variavel"))
        self.preencher()
        self.definir_termino(12, 2026)
        self.salvar()
        con = db.conectar()
        try:
            linhas = con.execute("SELECT c.data_vencimento, c.valor, p.conta_id IS NOT NULL FROM contas c "
                                 f"LEFT JOIN {db.TABELA_VALOR_PENDENTE} p ON p.conta_id = c.id "
                                 "ORDER BY c.data_vencimento").fetchall()
        finally:
            con.close()
        self.assertEqual(linhas, [("2026-09-20", 149.9, 0), ("2026-10-20", 0, 1), ("2026-11-20", 0, 1),
                                  ("2026-12-20", 0, 1)])

    # ---------------------------------------------- 6.13: término padrão
    def series(self):
        return self.consultar("SELECT id, frequencia, data_termino, horizonte_gerado_ate FROM series_recorrencia "
                              "ORDER BY id")

    def ocorrencias(self, serie_id):
        return [d for (d,) in self.consultar("SELECT data_vencimento FROM contas WHERE serie_id = ? "
                                             "ORDER BY data_vencimento", (serie_id,))]

    def test_sem_termino_salvo_e_geracao_limitada_ao_horizonte_inicial(self):
        # Sem término: só o horizonte inicial de 12 meses da 6.12 (5.3/CT07), nunca uma geração aberta.
        esperado = {"mensal": 13, "anual": 2}
        for tipo in ("mensal", "anual"):
            for comportamento in ("fixo", "variavel"):
                with self.subTest(tipo=tipo, comportamento=comportamento):
                    if self.existe("salvar_nova_conta") is False:
                        self.clicar(self.com_data("nova_conta"))
                    self.tipo(tipo)
                    self.clicar(self.com_data(f"comportamento_{comportamento}"))
                    self.preencher(nome=f"{tipo} {comportamento}")
                    self.salvar()
                    serie_id, frequencia, termino, horizonte = self.series()[-1]
                    self.assertEqual((frequencia, termino), (tipo, None))
                    datas = self.ocorrencias(serie_id)
                    self.assertEqual(len(datas), esperado[tipo])
                    self.assertEqual((datas[0], datas[-1], horizonte), ("2026-09-20", "2027-09-20", "2027-09-20"))
                    self.assertEqual(db.serie_variavel(serie_id), comportamento == "variavel")
                    pendentes = {c for (c,) in self.consultar(f"SELECT conta_id FROM {db.TABELA_VALOR_PENDENTE}")}
                    ids = [i for (i,) in self.consultar("SELECT id FROM contas WHERE serie_id = ? "
                                                        "ORDER BY data_vencimento", (serie_id,))]
                    self.assertEqual(pendentes & set(ids), set(ids[1:]) if comportamento == "variavel" else set())
        # Pedir um período distante gera só o que falta, uma vez (sob demanda, idempotente).
        serie_id = self.series()[0][0]
        db.gerar_ocorrencias_sob_demanda(serie_id, "2027-12")
        db.gerar_ocorrencias_sob_demanda(serie_id, "2027-12")
        self.assertEqual(len(self.ocorrencias(serie_id)), 16)

    def test_termino_definido_salvo(self):
        for tipo, ate, quantidade in (("mensal", (3, 2027), 7), ("anual", (9, 2029), 4)):
            with self.subTest(tipo=tipo):
                if not self.existe("salvar_nova_conta"):
                    self.clicar(self.com_data("nova_conta"))
                self.tipo(tipo)
                self.preencher(nome=f"Com término {tipo}")
                self.definir_termino(*ate)
                self.salvar()
                serie_id, frequencia, termino, _ = self.series()[-1]
                self.assertEqual((frequencia, termino), (tipo, f"{ate[1]:04d}-{ate[0]:02d}"))
                self.assertEqual(len(self.ocorrencias(serie_id)), quantidade)
                db.gerar_ocorrencias_sob_demanda(serie_id, "2035-12")   # com término não gera mais nada
                self.assertEqual(len(self.ocorrencias(serie_id)), quantidade)

    def test_contas_existentes_preservadas_e_edicao_mostra_o_salvo(self):
        com = db.criar_serie_recorrente(self.usuario_id, "Seguro", 80.0, "2026-09-10", "mensal",
                                        data_termino="2026-12")
        sem = db.criar_serie_recorrente(self.usuario_id, "Internet", 99.9, "2026-09-12", "anual")
        antes = (self.series(), self.consultar("SELECT * FROM contas ORDER BY id"))
        # Uma nova recorrência com o padrão novo não toca nas existentes.
        self.tipo("mensal")
        self.preencher(nome="Streaming")
        self.salvar()
        self.assertEqual(self.series()[:2], antes[0])
        self.assertEqual(self.consultar("SELECT * FROM contas WHERE id <= ? ORDER BY id",
                                        (max(r[0] for r in antes[1]),)), antes[1])
        self.assertEqual([r[2] for r in self.series()], ["2026-12", None, None])
        # A edição mostra o término efetivamente salvo, sem trocar pelo padrão novo.
        for nome, frase in (("Seguro", main.frase_recorrencia("mensal", "2026-12")),
                            ("Internet", main.frase_recorrencia("anual", None))):
            with self.subTest(nome=nome):
                linha = next(c for c in self.controles(ft.Container)
                             if c.data in ("linha_conta", "linha_conta_empilhada")
                             and nome in [t.value for t in percorrer(c) if isinstance(t, ft.Text)])
                self.clicar(linha)
                self.clicar(next(c for c in self.controles((ft.Button, ft.OutlinedButton, ft.TextButton))
                                 if c.content == "Editar"))
                self.assertEqual(self.campo("Recorrência").value, frase)
                self.mostrar_principal()
        self.assertEqual(self.series()[:2], antes[0])
        self.assertTrue(com and sem)

    def mostrar_principal(self):
        for _ in range(4):                       # Editar ("Cancelar" não salva) -> tela principal
            if self.existe("nova_conta"):
                return
            self.clicar(next(c for c in self.controles((ft.Button, ft.TextButton, ft.OutlinedButton))
                             if c.content in ("Cancelar", "Voltar")))
        self.fail("não voltou à tela principal")

    def test_demais_modalidades_nao_mudam(self):
        self.preencher(nome="Única")
        self.salvar()
        self.clicar(self.com_data("nova_conta"))
        self.tipo("parcelada")
        self.preencher(nome="Parcelada", valor="100,00")
        self.escrever("Quantidade de parcelas", "3")
        self.salvar()
        self.acao_do_dialogo(self.abertos()[-1], "Salvar conta")
        # A parcelada usa uma série mensal com término na última parcela (regra da 6.12, inalterada).
        self.assertEqual([r[1:3] for r in self.series()], [("mensal", "2026-11")])
        self.assertEqual(self.contagem("contas"), 4)
        self.assertFalse(self.existe("termino_nova_conta"))

    def test_termino_anterior_recusado_como_na_612(self):
        self.tipo("anual")
        self.preencher()
        self.definir_termino(9, 2026)
        self.data(2027, 3, 1)
        self.salvar()
        self.assertEqual(self.erro(), "O término não pode ser anterior à data de vencimento inicial.")
        self.assertEqual(self.contagem("contas"), 0)

    def test_quantidade_fora_dos_limites_nao_grava(self):
        self.tipo("parcelada")
        self.preencher(valor="100,00")
        for digitado in ("", "1", "37", "x"):
            self.escrever("Quantidade de parcelas", digitado)
            self.salvar()
            self.assertEqual(self.erro(), db.MENSAGEM_QUANTIDADE_DE_PARCELAS)
            self.assertEqual(self.abertos(), [])
            self.assertEqual(self.contagem("contas"), 0)

    def test_parcelada_previa_e_so_o_confirmar_grava(self):
        self.tipo("parcelada")
        self.preencher(valor="100,00")
        self.escrever("Quantidade de parcelas", "3")
        self.salvar()
        dlg = self.abertos()[-1]
        self.assertEqual(dlg.data, "dialogo_previa_parcelamento")
        self.assertEqual(self.contagem("contas"), 0)
        self.clicar(next(b for b in dlg.actions if b.content == "Salvar conta"))
        valores = [c["valor"] for c in sorted(db.listar_contas(self.usuario_id), key=lambda c: c["data_vencimento"])]
        self.assertEqual(valores, [33.34, 33.33, 33.33])

    def test_erro_de_nome_vazio(self):
        self.salvar()
        self.assertEqual(self.erro(), "Digite um nome para a conta.")


class TestSuperconta(Base):
    def setUp(self):
        super().setUp()
        self.clicar(self.com_data("modo_superconta"))

    def test_formulario_visual_e_mensagem(self):
        self.assertTrue(self.selecionado(self.com_data("modo_superconta")))
        self.assertEqual(self.rotulos(), ["Nome da superconta", "Valor total da fatura", "Vencimento da fatura",
                                          "Categoria", "Detalhamento da fatura", "Descrição (opcional)"])
        textos = [c.value for c in self.controles(ft.Text)]
        self.assertIn(main.TITULO_SUPERCONTA_EM_DESENVOLVIMENTO, textos)
        self.assertIn(main.TEXTO_SUPERCONTA_EM_DESENVOLVIMENTO, textos)
        self.assertEqual(self.campo("Nome da superconta").counter, main.texto_contador("", 30))
        self.assertEqual(self.campo("Descrição (opcional)").counter, main.texto_contador("", 250))
        self.assertTrue(self.campo("Detalhamento da fatura").read_only)

    def test_botoes_de_gravacao_cinza_e_desabilitados(self):
        for data in ("salvar_e_adicionar_indisponivel", "salvar_superconta_indisponivel"):
            botao = self.com_data(data)
            self.assertTrue(botao.disabled)
            self.assertIsNone(botao.on_click)
            self.assertEqual(botao.style.bgcolor, CLARO["botao_desabilitado_fundo"])
        self.assertFalse(self.existe("salvar_nova_conta"))

    def test_nada_e_gravado_e_nao_ha_nova_categoria(self):
        self.escrever("Nome da superconta", "Cartão")
        self.escrever("Valor total da fatura", "800,00")
        self.assertNotIn(main.SENTINELA_NOVA_CATEGORIA, [o.key for o in self.campo("Categoria").options])
        con = db.conectar()
        try:
            antes = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for (t,) in con.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
        finally:
            con.close()
        self.assertFalse(any(t.startswith("f1_") for t in antes))
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Cancelar"))
        con = db.conectar()
        try:
            depois = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in antes}
        finally:
            con.close()
        self.assertEqual(antes, depois)

    def test_sem_codigo_da_f1(self):
        fonte = open(main.__file__, encoding="utf-8").read()
        for termo in ("import supercontas", "supercontas.", "f1_", "garantir_tabelas"):
            self.assertNotIn(termo, fonte)

    def test_voltar_a_conta_comum_preserva_o_formulario(self):
        self.clicar(self.com_data("modo_comum"))
        self.assertTrue(self.selecionado(self.com_data("tipo_conta_unica")))
        self.assertTrue(self.existe("salvar_nova_conta"))


if __name__ == "__main__":
    unittest.main()
