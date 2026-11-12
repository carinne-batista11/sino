"""
Sino 6.13.1: atualizado para a estrutura da 6.13 (cartões de tipo e diálogo "Término da
recorrência"); os comportamentos verificados continuam os mesmos. Texto original:

Sino 6.11 — Nova conta: diálogo "Configurar recorrência", no padrão de
"Transformar em recorrente" de Editar conta (aprovado no protótipo v3 de
02/11/2026). Abertura e fechamento, Única/Mensal/Anual, "Sem data de término",
Mês e Ano, Cancelar sem aplicar, Confirmar com resumo, reabertura com a
configuração confirmada, término guardado ao passar por Única, nada gravado
antes do Salvar, gravação pelo Salvar (mesmas regras da 6.10), nomes acessíveis
e foco, e comparação da estrutura com o diálogo real de Editar. Páginas falsas
e bancos temporários; "hoje" = 15/09/2026.
"""
import os
import sys
import unittest
from datetime import datetime
from unittest import mock

import apoio_banco
from apoio_banco import DataFixa, TesteComBancoTemporario, db
from test_sessao_tema import PaginaFalsa
from test_tela_principal import Evento, percorrer

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))
import cores  # noqa: E402
import flet as ft  # noqa: E402
import main  # noqa: E402

CLARO = cores.PALETAS["claro"]


class Base(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.usuario_id = self.criar_usuario(email="nova611@sino.com", senha="senha1234")
        self.pagina = PaginaFalsa().configurar()

    def entrar(self):
        self.pagina.controls.clear()
        main.main(self.pagina)
        campos = {c.label: c for c in self.controles(ft.TextField)}
        campos["E-mail"].value, campos["Senha"].value = "nova611@sino.com", "senha1234"
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Entrar"))

    def controles(self, tipo=None, raizes=None):
        raizes = self.pagina.controls if raizes is None else raizes
        todos = [c for raiz in raizes for c in percorrer(raiz)]
        return [c for c in todos if tipo is None or isinstance(c, tipo)]

    def clicar(self, c):
        c.on_click(Evento(self.pagina, c))


class TestDialogoRecorrencia(Base):
    """
    Sino 6.13.1: os comportamentos do antigo diálogo "Configurar recorrência" (6.11) na estrutura
    da 6.13 -- o tipo é escolhido nos cartões do formulário (Única | Parcelada | Recorrente mensal |
    Recorrente anual) e o término, no campo "Término da recorrência" e no diálogo central de mesmo
    nome. Os nomes dos testes foram mantidos para a rastreabilidade com a 6.11/6.12.
    """

    def setUp(self):
        super().setUp()
        self.entrar()
        self.clicar(next(c for c in self.controles() if getattr(c, "data", None) == "nova_conta"))

    # auxiliares
    def campo(self, rotulo, raizes=None):
        return next(c for c in self.controles((ft.TextField, ft.Dropdown), raizes) if c.label == rotulo)

    def com_data(self, data, raizes=None):
        return next(c for c in self.controles(None, raizes) if getattr(c, "data", None) == data)

    def existe(self, data):
        return any(getattr(c, "data", None) == data for c in self.controles())

    def termino(self):
        return self.com_data("termino_nova_conta")

    def abertos(self):
        return [d for d in self.pagina.dialogos if d.open]

    def abrir(self, pelo_campo=False):
        c = self.termino()
        self.clicar(c if pelo_campo else c.suffix_icon)
        self.assertEqual(len(self.abertos()), 1)
        self.assertEqual(self.abertos()[0].data, "dialogo_termino")
        return self.abertos()[0]

    def dlg(self):
        return self.abertos()[0]

    def no_dialogo(self, data):
        return next(c for c in percorrer(self.dlg().content) if getattr(c, "data", None) == data)

    def tipo(self, valor):
        self.clicar(self.com_data(f"tipo_conta_{valor}"))

    def ligar_sem_termino(self, valor):
        chave = self.no_dialogo("sem_termino_recorrencia")
        chave.value = valor
        chave.on_change(Evento(self.pagina, chave))

    def escolher(self, rotulo, valor):
        lista = self.campo(rotulo, [self.dlg().content])
        lista.value = valor
        lista.on_select(Evento(self.pagina, lista))

    def definir_termino(self, mes, ano):
        self.abrir()
        self.ligar_sem_termino(False)
        self.escolher("Mês", mes)
        self.escolher("Ano", ano)
        self.confirmar()

    def acao(self, texto):
        return next(b for b in self.dlg().actions if b.content == texto)

    def confirmar(self):
        d = self.dlg()
        self.clicar(self.acao("Confirmar"))
        self.assertFalse(d.open)

    def cancelar(self):
        d = self.dlg()
        self.clicar(self.acao("Cancelar"))
        self.assertFalse(d.open)

    def selecionado(self):
        """Tipos marcados: o "Selecionado" (nome acessível) e o fundo ativo têm de concordar."""
        marcados = []
        for v in ("unica", "parcelada", "mensal", "anual"):
            cartao = self.com_data(f"tipo_conta_{v}")
            marca = any(isinstance(c, ft.Icon) and c.semantics_label == "Selecionado" for c in percorrer(cartao))
            self.assertEqual(marca, cartao.style.bgcolor == CLARO["chip_ativo_fundo"], v)
            if marca:
                marcados.append(v)
        return marcados

    def mes_ano(self):
        return (self.campo("Mês", [self.dlg().content]).value, self.campo("Ano", [self.dlg().content]).value)

    def mes_ano_habilitados(self):
        mes, ano = self.campo("Mês", [self.dlg().content]), self.campo("Ano", [self.dlg().content])
        self.assertEqual(mes.disabled, ano.disabled)
        return not mes.disabled

    def textos(self):
        return [t.value for t in self.controles(ft.Text)]

    def preencher(self, nome="Curso", valor="200", data=(2026, 10, 5)):
        for c in (self.campo("Nome da conta"), self.com_data("valor_nova_conta")):
            c.value = nome if c.label == "Nome da conta" else valor
            if c.on_change:
                c.on_change(Evento(self.pagina, c))
        seletor = next(o for o in self.pagina.overlay if isinstance(o, ft.DatePicker))   # o da conta comum
        seletor.value = datetime(*data)
        seletor.on_change(Evento(self.pagina, seletor))

    def salvar(self):
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Salvar conta"))

    # 1. estado inicial e abertura/fechamento do diálogo do término
    def test_estado_inicial_com_orientacao_e_sem_dialogo(self):
        self.assertEqual(self.selecionado(), ["unica"])                       # Única por padrão
        self.assertIn(main.FAIXAS_NOVA_CONTA["unica"][0], self.textos())       # orientação do tipo
        self.assertIn(main.FAIXAS_NOVA_CONTA["unica"][1], self.textos())
        self.assertFalse(self.existe("termino_nova_conta"))
        self.assertEqual(self.pagina.dialogos, [])

    def test_abre_pelo_campo_e_pela_seta_e_fecha(self):
        self.tipo("mensal")
        for pelo_campo in (True, False):
            d = self.abrir(pelo_campo)
            self.assertIsInstance(d, ft.AlertDialog)
            self.assertTrue(d.modal)
            self.assertEqual(d.title.value, "Término da recorrência")
            textos = [c.value for c in percorrer(d.content) if isinstance(c, ft.Text)]
            self.assertIn("Sem data de término", textos)
            self.assertEqual([b.content for b in d.actions], ["Cancelar", "Confirmar"])
            self.cancelar()
            self.assertEqual(self.abertos(), [])

    def test_formulario_nao_muda_ao_abrir(self):
        self.tipo("mensal")
        antes = [id(c) for c in self.controles()]
        self.abrir()
        self.assertEqual([id(c) for c in self.controles()], antes)      # nada entra no formulário
        self.cancelar()
        self.assertEqual([id(c) for c in self.controles()], antes)

    # 2-4. tipos, sem término, Mês e Ano
    def test_unica_por_padrao_sem_termino_oculto(self):
        self.assertEqual(self.selecionado(), ["unica"])
        self.assertFalse(self.existe("termino_nova_conta"))
        self.assertFalse(self.existe("linha_comportamento_valor"))
        self.assertEqual(self.com_data("valor_nova_conta").label, "Valor da conta")

    def test_alternancia_e_sem_data_de_termino(self):
        for valor in ("mensal", "anual", "unica", "parcelada", "mensal"):
            self.tipo(valor)
            self.assertEqual(self.selecionado(), [valor])
            self.assertEqual(self.existe("termino_nova_conta"), valor in ("mensal", "anual"))
        self.assertEqual(self.termino().value, "Sem data de término")          # 6.13: começa sem término
        self.abrir()
        self.assertTrue(self.no_dialogo("sem_termino_recorrencia").value)
        self.assertEqual(self.mes_ano(), ("9", "2026"))                        # mês e ano atuais
        self.assertFalse(self.mes_ano_habilitados())                           # visíveis, mas desabilitados
        self.ligar_sem_termino(False)
        self.assertTrue(self.mes_ano_habilitados())
        self.ligar_sem_termino(True)
        self.assertFalse(self.mes_ano_habilitados())
        self.ligar_sem_termino(False)
        self.escolher("Mês", "5")
        self.escolher("Ano", "2027")
        self.confirmar()
        self.assertEqual(self.termino().value, "Até maio de 2027")
        self.tipo("unica")
        self.assertFalse(self.existe("termino_nova_conta"))
        self.tipo("anual")
        self.assertEqual(self.termino().value, "Até maio de 2027")             # o confirmado continua

    # 5. Cancelar
    def test_cancelar_nao_aplica(self):
        self.tipo("mensal")
        self.abrir()
        self.ligar_sem_termino(False)
        self.escolher("Mês", "5")
        self.escolher("Ano", "2027")
        self.cancelar()
        self.assertEqual(self.termino().value, "Sem data de término")          # nada confirmado
        self.abrir()
        self.assertTrue(self.no_dialogo("sem_termino_recorrencia").value)
        self.assertEqual(self.mes_ano(), ("9", "2026"))

    def test_cancelar_depois_de_confirmado_volta_ao_confirmado(self):
        self.tipo("mensal")
        self.definir_termino("5", "2027")
        self.abrir()
        self.ligar_sem_termino(True)
        self.cancelar()
        self.assertEqual(self.termino().value, "Até maio de 2027")
        self.abrir()
        self.assertFalse(self.no_dialogo("sem_termino_recorrencia").value)
        self.assertTrue(self.mes_ano_habilitados())
        self.assertEqual(self.mes_ano(), ("5", "2027"))

    # 6-7. Confirmar e reabrir
    def test_confirmar_atualiza_o_resumo_e_reabre_com_o_confirmado(self):
        self.tipo("anual")
        self.definir_termino("12", "2028")
        campo = self.termino()
        self.assertEqual(campo.value, "Até dezembro de 2028")
        self.assertEqual(campo.color, CLARO["texto_principal"])
        self.abrir()
        self.assertFalse(self.no_dialogo("sem_termino_recorrencia").value)
        self.assertEqual(self.mes_ano(), ("12", "2028"))
        self.ligar_sem_termino(True)
        self.confirmar()
        self.assertEqual(campo.value, "Sem data de término")
        self.abrir()
        self.assertTrue(self.no_dialogo("sem_termino_recorrencia").value)
        self.assertFalse(self.mes_ano_habilitados())

    def test_confirmar_unica_mostra_unica(self):
        self.tipo("mensal")
        self.tipo("unica")
        self.assertEqual(self.selecionado(), ["unica"])
        self.assertIn(main.FAIXAS_NOVA_CONTA["unica"][0], self.textos())
        self.assertNotIn(main.FAIXAS_NOVA_CONTA["mensal"][0], self.textos())
        self.assertFalse(self.existe("termino_nova_conta"))
        self.assertEqual((self.com_data("valor_nova_conta").label, self.com_data("data_nova_conta").label),
                         ("Valor da conta", "Data de vencimento"))

    def test_resumos_curtos(self):
        # Rótulo do caso = resumo da 6.11/6.12; o esperado é o texto da 6.13 (faixa do tipo e término).
        casos = [("Única", "unica", None, None, None),
                 ("Mensal, sem término", "mensal", True, None, "Sem data de término"),
                 ("Mensal até março de 2027", "mensal", False, ("3", "2027"), "Até março de 2027"),
                 ("Anual, sem término", "anual", True, None, "Sem data de término"),
                 ("Anual até dezembro de 2028", "anual", False, ("12", "2028"), "Até dezembro de 2028")]
        for rotulo, tipo, sem, termino, texto in casos:
            with self.subTest(rotulo):
                self.tipo(tipo)
                self.assertIn(main.FAIXAS_NOVA_CONTA[tipo][0], self.textos())
                if tipo == "unica":
                    self.assertFalse(self.existe("termino_nova_conta"))
                    continue
                self.abrir()
                self.ligar_sem_termino(sem)
                if termino:
                    self.escolher("Mês", termino[0])
                    self.escolher("Ano", termino[1])
                self.confirmar()
                self.assertEqual(self.termino().value, texto)

    # 8. término guardado ao passar por Única
    def test_termino_guardado_ao_passar_por_unica(self):
        self.preencher()
        self.tipo("mensal")
        self.definir_termino("5", "2027")
        self.tipo("unica")
        self.tipo("anual")
        self.assertEqual(self.termino().value, "Até maio de 2027")
        self.abrir()                                                         # em outra abertura
        self.assertEqual(self.mes_ano(), ("5", "2027"))
        self.assertFalse(self.no_dialogo("sem_termino_recorrencia").value)
        self.cancelar()
        self.salvar()
        self.assertEqual(self.consultar("SELECT frequencia, data_termino FROM series_recorrencia"),
                         [("anual", "2027-05")])

    # 9. nada gravado antes do Salvar; Salvar grava o confirmado
    def test_confirmar_nao_grava_no_banco(self):
        self.preencher()
        self.tipo("mensal")
        self.definir_termino("12", "2026")
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas")[0][0], 0)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM series_recorrencia")[0][0], 0)

    def test_salvar_mensal_com_termino(self):
        self.preencher()
        self.tipo("mensal")
        self.definir_termino("12", "2026")
        self.salvar()
        self.assertEqual(self.consultar("SELECT frequencia, data_termino FROM series_recorrencia"),
                         [("mensal", "2026-12")])

    def test_salvar_unica_depois_de_mensal_nao_aplica_termino(self):
        self.preencher()
        self.tipo("mensal")
        self.definir_termino("12", "2026")
        self.tipo("unica")
        self.salvar()
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM series_recorrencia")[0][0], 0)
        self.assertEqual(self.consultar("SELECT nome, serie_id FROM contas"), [("Curso", None)])

    def test_salvar_sem_abrir_grava_unica(self):
        self.preencher()
        self.salvar()
        self.assertEqual(self.consultar("SELECT nome, serie_id FROM contas"), [("Curso", None)])

    def test_salvar_ignora_o_que_foi_cancelado(self):
        self.preencher()
        self.tipo("anual")
        self.abrir()
        self.ligar_sem_termino(False)
        self.escolher("Mês", "12")
        self.escolher("Ano", "2027")
        self.cancelar()
        self.salvar()
        self.assertEqual(self.consultar("SELECT frequencia, data_termino FROM series_recorrencia"),
                         [("anual", None)])                                  # o término cancelado não vale

    def test_termino_anterior_continua_conferido_so_no_salvar(self):
        self.preencher(data=(2026, 10, 5))
        self.tipo("mensal")
        self.definir_termino("9", "2026")                                    # o diálogo não valida
        self.assertEqual(self.abertos(), [])
        self.salvar()
        erros = [t.value for t in self.controles(ft.Text) if t.color == CLARO["texto_erro"] and t.value]
        self.assertEqual(erros, ["O término não pode ser anterior à data de vencimento inicial."])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas")[0][0], 0)

    # 10. teclado e nomes acessíveis
    def test_nomes_acessiveis_e_foco(self):
        rotulos = {"unica": "Única", "parcelada": "Parcelada", "mensal": "Recorrente mensal",
                   "anual": "Recorrente anual"}
        for v, rotulo in rotulos.items():
            cartao = self.com_data(f"tipo_conta_{v}")
            self.assertIsInstance(cartao, ft.Button)                         # focável (Tab; Enter/Espaço)
            self.assertIn(rotulo, [t.value for t in percorrer(cartao) if isinstance(t, ft.Text)])
        self.tipo("mensal")
        campo = self.termino()
        seta = campo.suffix_icon
        self.assertIsInstance(seta, ft.IconButton)
        self.assertEqual(seta.icon.semantics_label, "Escolher término da recorrência")
        self.assertFalse(campo.can_request_focus)                            # o foco vai para a seta
        self.pagina.run_task.reset_mock()
        self.abrir()
        funcao, foco_ao_abrir = self.pagina.run_task.call_args[0][:2]
        self.assertEqual(funcao.__name__, "focar_depois")
        self.assertIs(foco_ao_abrir, self.no_dialogo("sem_termino_recorrencia"))   # 1º controle do diálogo
        self.assertIsInstance(foco_ao_abrir, ft.Switch)
        for acao in ("Cancelar", "Confirmar"):
            with self.subTest(acao):
                self.clicar(self.acao(acao))
                self.assertEqual(self.abertos(), [])
                self.assertIs(self.pagina.run_task.call_args[0][1], seta)    # o foco volta para a seta
                self.abrir()

    # janelas estreitas: o término quebra por palavra, como a Recorrência de Editar
    def test_resumo_quebra_linha_em_vez_de_ser_cortado(self):
        self.tipo("mensal")
        campo = self.termino()
        self.assertEqual((campo.multiline, campo.min_lines, campo.max_lines), (True, 1, 3))
        self.assertTrue(campo.read_only)
        self.assertFalse(campo.can_request_focus)                            # o foco continua na seta


class TestMesmoPadraoDeEditar(Base):
    """
    O diálogo do término da Nova conta segue o padrão da parte de término de "Transformar em
    recorrente" (Editar). Sino 6.13.1: a escolha do tipo e o "Valor fixo | Valor variável" saíram
    do diálogo da Nova conta para o formulário (cartões aprovados na 6.13), então a comparação
    passa a ser só da parte comum: título, coluna, chave "Sem data de término", Mês e Ano
    (inclusive desabilitados com a chave ligada), mensagem de erro reservada e botões.
    """

    @staticmethod
    def assinatura(d, i_chave, i_termino, i_erro):
        col = d.content
        linha_chave, linha_termino, erro = col.controls[i_chave], col.controls[i_termino], col.controls[i_erro]
        acao_cancelar, acao_confirmar = d.actions
        return {
            "modal": d.modal, "fundo": d.bgcolor, "titulo": (type(d.title), d.title.color, d.title.size),
            "coluna": (type(col), col.tight, col.spacing),
            "linha_chave": (linha_chave.alignment, [type(c) for c in linha_chave.controls],
                            linha_chave.controls[0].value, linha_chave.controls[0].size,
                            linha_chave.controls[0].color, linha_chave.controls[1].active_color,
                            linha_chave.controls[1].value),
            "linha_termino": (type(linha_termino), linha_termino.spacing, linha_termino.opacity,
                              [(type(c), c.label, c.expand, c.color, c.value, c.disabled,
                                [o.key for o in c.options]) for c in linha_termino.controls]),
            "erro": (type(erro), erro.size, erro.value, erro.color),
            "cancelar": (type(acao_cancelar), acao_cancelar.content, acao_cancelar.style.color),
            "confirmar": (type(acao_confirmar), acao_confirmar.bgcolor, acao_confirmar.color),
        }

    def test_mesma_estrutura_e_estilo(self):
        db.criar_conta_unica(self.usuario_id, "Internet", 400.0, "2026-09-20")
        self.entrar()
        linha = next(c for c in self.controles(ft.Container)
                     if c.data in ("linha_conta", "linha_conta_empilhada")
                     and "Internet" in [t.value for t in percorrer(c) if isinstance(t, ft.Text)])
        self.clicar(linha)
        self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Editar"))
        menu = next(c for c in self.controles(ft.TextField) if c.label == "Recorrência").suffix_icon
        item = next(i for i in menu.items if i.content == "Transformar em recorrente")
        item.on_click(Evento(self.pagina, item))
        editar = self.pagina.dialogos[-1]
        self.assertEqual(editar.title.value, "Transformar em recorrente")

        self.entrar()
        self.clicar(next(c for c in self.controles() if getattr(c, "data", None) == "nova_conta"))
        self.clicar(next(c for c in self.controles() if getattr(c, "data", None) == "tipo_conta_mensal"))
        campo = next(c for c in self.controles(ft.TextField) if getattr(c, "data", None) == "termino_nova_conta")
        self.clicar(campo.suffix_icon)
        novo = self.pagina.dialogos[-1]
        self.assertEqual(novo.data, "dialogo_termino")

        # Editar: texto, frequência, chave, Mês/Ano, valor, ajuda, erro; Nova conta: chave, Mês/Ano, erro.
        self.assertEqual(len(editar.content.controls), 7)
        self.assertEqual(editar.content.controls[4].data, "comportamento_transformar")
        self.assertEqual(len(novo.content.controls), 3)
        a, b = self.assinatura(editar, 2, 3, 6), self.assinatura(novo, 0, 1, 2)
        for chave in ("modal", "fundo", "titulo", "coluna", "linha_chave", "linha_termino", "erro", "cancelar"):
            with self.subTest(chave):
                self.assertEqual(a[chave], b[chave])
        # Diferença intencional: o rótulo da ação ("Transformar" em Editar, "Confirmar" na Nova conta).
        self.assertEqual(a["confirmar"], b["confirmar"])
        self.assertEqual(b["confirmar"], (ft.Button, CLARO["acao_primaria"], CLARO["texto_sobre_acao"]))
        self.assertEqual([x.content for x in novo.actions], ["Cancelar", "Confirmar"])
        self.assertEqual(novo.content.width, 420)



class TestCorDosCartoesDeTipo(Base):
    """
    Sino 6.13.1 (alternativa A, RNF09): os quatro cartões de tipo da Nova conta têm cor de texto
    explícita no próprio botão, como os cartões Conta comum | Superconta -- a mesma do nome e da
    marca do cartão --, nos dois temas e em cada tipo escolhido. Fundo, borda e conteúdo continuam
    os da 6.13.
    """

    def cartoes(self):
        return {v: next(c for c in self.controles() if getattr(c, "data", None) == f"tipo_conta_{v}")
                for v in ("unica", "parcelada", "mensal", "anual")}

    def test_cor_explicita_nos_quatro_cartoes_nos_dois_temas(self):
        for tema in ("claro", "escuro"):
            paleta = cores.PALETAS[tema]
            db.definir_tema(self.usuario_id, tema)
            self.entrar()
            self.clicar(next(c for c in self.controles() if getattr(c, "data", None) == "nova_conta"))
            modo = next(c for c in self.controles() if getattr(c, "data", None) == "modo_comum")
            self.assertEqual(modo.color, paleta["texto_principal"])               # o padrão seguido
            for escolhido in ("unica", "parcelada", "mensal", "anual"):
                self.clicar(self.cartoes()[escolhido])
                for valor, cartao in self.cartoes().items():
                    with self.subTest(tema=tema, escolhido=escolhido, cartao=valor):
                        ativo = valor == escolhido
                        esperado = paleta["chip_ativo_texto"] if ativo else paleta["texto_principal"]
                        self.assertEqual(cartao.color, esperado)
                        nome = [t for t in percorrer(cartao) if isinstance(t, ft.Text)][0]
                        self.assertEqual(nome.color, cartao.color)                   # igual ao nome visível
                        self.assertEqual(cartao.style.bgcolor,
                                         paleta["chip_ativo_fundo"] if ativo else paleta["fundo_card"])
                        self.assertIsNone(cartao.style.color)                       # só o `color` do botão



class TestCorDoValorPorParcela(Base):
    """
    Sino 6.13.1 (B1, RNF09): o campo "Valor por parcela (estimado)" da Parcelada tem cor explícita
    no próprio campo, a mesma do estilo do texto (texto_sucesso) -- sem mudança visual --, nos dois
    temas, e continua legível sobre o próprio fundo (4,5:1).
    """

    def test_cor_explicita_igual_a_do_estilo_nos_dois_temas(self):
        from test_cores import MINIMO_TEXTO, contraste
        for tema in ("claro", "escuro"):
            with self.subTest(tema=tema):
                paleta = cores.PALETAS[tema]
                db.definir_tema(self.usuario_id, tema)
                self.entrar()
                self.clicar(next(c for c in self.controles() if getattr(c, "data", None) == "nova_conta"))
                self.clicar(next(c for c in self.controles() if getattr(c, "data", None) == "tipo_conta_parcelada"))
                campo = next(c for c in self.controles() if getattr(c, "data", None) == "valor_por_parcela_estimado")
                self.assertEqual(campo.color, paleta["texto_sucesso"])
                self.assertEqual(campo.text_style.color, campo.color)
                self.assertEqual((campo.filled, campo.fill_color), (True, paleta["grafico_total_fundo"]))
                self.assertGreaterEqual(contraste(campo.color, campo.fill_color), MINIMO_TEXTO)


if __name__ == "__main__":
    unittest.main(verbosity=2)
