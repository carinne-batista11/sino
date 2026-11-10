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


class TestAbertura(Base):
    def test_conta_comum_e_unica_selecionadas_por_padrao(self):
        self.assertTrue(self.selecionado(self.com_data("modo_comum")))
        self.assertFalse(self.selecionado(self.com_data("modo_superconta")))
        self.assertTrue(self.selecionado(self.com_data("tipo_conta_unica")))
        for outro in ("parcelada", "mensal", "anual"):
            self.assertFalse(self.selecionado(self.com_data(f"tipo_conta_{outro}")))

    def test_unica_mostra_so_os_campos_dela(self):
        self.assertEqual(self.rotulos(), ["Nome da conta", "Valor da conta", "Data de vencimento", "Categoria",
                                          "Descrição (opcional)"])
        self.assertFalse(self.existe("linha_comportamento_valor"))
        self.assertFalse(self.existe("resumo_parcelas_nova_conta"))
        self.assertFalse(self.existe("termino_nova_conta"))
        self.assertIn("Conta única", [c.value for c in self.controles(ft.Text)])

    def test_cartoes_e_tipos_sao_botoes_focaveis(self):
        for data in ("modo_comum", "modo_superconta", "tipo_conta_unica", "tipo_conta_parcelada",
                     "tipo_conta_mensal", "tipo_conta_anual"):
            self.assertIsInstance(self.com_data(data), ft.Button)

    def test_limites_de_nome_e_descricao(self):
        self.assertEqual(self.campo("Nome da conta").counter, main.texto_contador("", 30))
        self.assertEqual(self.campo("Descrição (opcional)").counter, main.texto_contador("", 250))


class TestModalidades(Base):
    def test_parcelada(self):
        self.tipo("parcelada")
        self.assertEqual(self.rotulos(), ["Nome da conta", "Valor total da conta", "Quantidade de parcelas",
                                          "Primeiro vencimento", "Categoria", "Descrição (opcional)"])
        self.assertEqual([o.key for o in self.campo("Quantidade de parcelas").options],
                         [str(n) for n in range(2, 37)])
        # Resumo logo depois de Primeiro vencimento e Categoria, antes da Descrição.
        grade = self.com_data("grade_nova_conta")
        ordem = [getattr(cel.content, "data", None) or getattr(cel.content, "label", None)
                 for cel in grade.controls]
        self.assertEqual(ordem.index("resumo_parcelas_nova_conta"), ordem.index("data_nova_conta") + 2)

    def test_resumo_usa_o_mesmo_calculo_do_banco(self):
        self.tipo("parcelada")
        self.escrever("Valor total da conta", "100,00")
        self.escolher("Quantidade de parcelas", "3")
        valores = db.dividir_em_parcelas(10000, 3)
        self.assertEqual(valores, [3334, 3333, 3333])
        self.assertEqual(self.com_data("valor_por_parcela_estimado").value, "R$ 33,33")
        self.assertIn("a 1ª de R$ 33,34 e as demais de R$ 33,33", self.com_data("frase_das_parcelas").value)
        self.escrever("Valor total da conta", "1.798,80")
        self.escolher("Quantidade de parcelas", "12")
        self.assertEqual(self.com_data("frase_das_parcelas").value,
                         "Serão registradas 12 parcelas de R$ 149,90, com vencimento mensal.")

    def test_resumo_sem_valor_e_valor_pequeno(self):
        self.assertEqual(main.resumo_estimado_das_parcelas(None, 3)["valor"], None)
        self.assertEqual(main.resumo_estimado_das_parcelas(0.02, 3)["frase"],
                         db.MENSAGEM_VALOR_PEQUENO_PARA_PARCELAS)
        self.assertIsNone(main.resumo_estimado_das_parcelas(100, 37)["valor"])

    def test_mensal_fixo_por_padrao_e_variavel(self):
        self.tipo("mensal")
        self.assertTrue(self.selecionado(self.com_data("comportamento_fixo")))
        self.assertFalse(self.selecionado(self.com_data("comportamento_variavel")))
        self.assertEqual(self.rotulos(), ["Nome da conta", "Valor por ocorrência (mensal)", "Término da recorrência",
                                          "Primeiro vencimento", "Categoria", "Descrição (opcional)"])
        self.assertFalse(self.com_data("ajuda_valor_variavel").visible)
        self.clicar(self.com_data("comportamento_variavel"))
        self.assertTrue(self.selecionado(self.com_data("comportamento_variavel")))
        self.assertIn("Valor da primeira ocorrência", self.rotulos())
        self.assertTrue(self.com_data("ajuda_valor_variavel").visible)

    def test_anual_segue_a_mensal(self):
        self.tipo("anual")
        self.assertIn("Valor por ocorrência (anual)", self.rotulos())
        self.assertIn("Conta recorrente anual", [c.value for c in self.controles(ft.Text)])
        self.assertTrue(self.selecionado(self.com_data("comportamento_fixo")))

    def test_valores_digitados_continuam_ao_trocar_de_tipo(self):
        self.preencher()
        for tipo in ("parcelada", "mensal", "anual", "unica"):
            self.tipo(tipo)
            self.assertEqual(self.campo("Nome da conta").value, "Academia")
            self.assertEqual(self.campo(self.rotulo_do_valor()).value, "149,90")

    def test_termino_no_dialogo_cancelar_e_confirmar(self):
        self.tipo("mensal")
        self.assertEqual(self.campo("Término da recorrência").value, "Até setembro de 2026")
        self.clicar(self.com_data("escolher_termino"))
        dlg = self.abertos()[-1]
        chave = next(c for c in percorrer(dlg.content) if isinstance(c, ft.Switch))
        chave.value = True
        chave.on_change(Evento(self.pagina, chave))
        self.clicar(next(b for b in dlg.actions if b.content == "Cancelar"))
        self.assertEqual(self.campo("Término da recorrência").value, "Até setembro de 2026")
        self.clicar(self.com_data("escolher_termino"))
        dlg = self.abertos()[-1]
        chave = next(c for c in percorrer(dlg.content) if isinstance(c, ft.Switch))
        chave.value = True
        chave.on_change(Evento(self.pagina, chave))
        self.clicar(next(b for b in dlg.actions if b.content == "Confirmar"))
        self.assertEqual(self.campo("Término da recorrência").value, "Sem data de término")


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
        self.clicar(self.com_data("escolher_termino"))
        dlg = self.abertos()[-1]
        mes, ano = [c for c in percorrer(dlg.content) if isinstance(c, ft.Dropdown)]
        mes.value = "12"
        mes.on_select(Evento(self.pagina, mes))
        self.clicar(next(b for b in dlg.actions if b.content == "Confirmar"))
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

    def test_termino_anterior_recusado_como_na_612(self):
        self.tipo("anual")
        self.preencher()
        self.data(2027, 3, 1)
        self.salvar()
        self.assertEqual(self.erro(), "O término não pode ser anterior à data de vencimento inicial.")
        self.assertEqual(self.contagem("contas"), 0)

    def test_parcelada_previa_e_so_o_confirmar_grava(self):
        self.tipo("parcelada")
        self.preencher(valor="100,00")
        self.escolher("Quantidade de parcelas", "3")
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
