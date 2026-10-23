"""
ERS v6.0, Etapa 6 — legibilidade mínima do tema Escuro nas telas autenticadas
(5.36, RNF09 parcial): Início, Ver status, Contas em atraso, Detalhes,
Nova/Editar conta, Categorias, Gráfico, Ajustes, Termos/Política e seus
diálogos.

Verifica os CONTROLES REAIS criados pela interface (páginas falsas sobre
bancos temporários), não só a paleta:
  * nenhum controle de tela autenticada fica sem cor explícita (exceto
    glifos de emoji) nem usa uma cor exclusiva do outro tema;
  * no Escuro, textos e botões atingem 4,5:1 e ícones 3:1 sobre o fundo em
    que realmente aparecem (camadas translúcidas combinadas);
  * trocar o tema em Ajustes e navegar recria os controles com a paleta nova;
  * o tema do Flet (diálogos, calendário) vem da paleta de cada tema.

Desde a Etapa 10 (opção A da paleta), o Claro também tem o contraste medido
nessas telas e diálogos. A cobertura é a das telas percorridas aqui e dos
pares de test_cores.py; não é uma auditoria completa de RNF09 (gráficos em
detalhe, estados raros e telas de autenticação ficam fora desta varredura).
"""

import ast
import io
import os
import re
import unittest
from contextlib import redirect_stderr

import flet_charts as fch

import apoio_banco
from apoio_banco import db
from test_cores import MINIMO_NAO_TEXTO, MINIMO_TEXTO, contraste
from test_sessao_tema import CLARO, ESCURO, TesteDeSessao, cores, ft, main
from test_tela_principal import Evento

CAMINHO_MAIN = os.path.join(apoio_banco.RAIZ_PROJETO, "backend", "main.py")
CORES_DE_CATEGORIA = set(db.PALETA_CORES_CATEGORIAS)
ATRIBUTOS_DE_COR = ("color", "bgcolor", "icon_color", "border_color", "focused_border_color", "cursor_color")


def cor_solida(cor, fundo):
    """Cor efetiva de `cor` (hex, "white", "transparent" ou "hex,alfa") sobre `fundo` sólido."""
    cor = str(getattr(cor, "value", cor))
    if cor == "transparent":
        return fundo
    hexa = lambda c: "FFFFFF" if c.lower() == "white" else c.lstrip("#")
    if "," in cor:
        base, alfa = cor.split(",")
        alfa = float(alfa)
        mistura = [round(int(hexa(base)[i:i + 2], 16) * alfa + int(hexa(fundo)[i:i + 2], 16) * (1 - alfa))
                   for i in (0, 2, 4)]
        return "#" + "".join(f"{c:02X}" for c in mistura)
    return "#" + hexa(cor).upper()


def filhos(controle):
    for atributo in ("content", "controls", "actions", "title", "leading", "trailing", "subtitle"):
        valor = getattr(controle, atributo, None)
        if isinstance(valor, list):
            yield from (c for c in valor if isinstance(c, ft.Control))
        elif isinstance(valor, ft.Control):
            yield valor
    if isinstance(controle, fch.BarChart):
        # RNF09 (encerramento da v6.0): rótulos dos eixos também são texto da tela.
        for eixo in (controle.bottom_axis, controle.left_axis, controle.right_axis, controle.top_axis):
            for rotulo in (getattr(eixo, "labels", None) or []):
                if isinstance(rotulo.label, ft.Control):
                    yield rotulo.label


def fundo_do_botao(botao):
    """
    Sino 6.9 (F2.1): fundo exibido por um `ft.Button`/`ft.TextButton` -- o
    `bgcolor` do Button ou o `style.bgcolor` (por estado: o DEFAULT). None
    quando o botão não tem fundo próprio (o conteúdo fica sobre o fundo herdado).
    """
    cor = getattr(botao, "bgcolor", None) or (botao.style.bgcolor if botao.style else None)
    if isinstance(cor, dict):
        cor = cor.get(ft.ControlState.DEFAULT)
    return cor or None


def e_medicao_invisivel(controle):
    """
    Sino 6.9 (F6, DF3): faixa técnica de medição do comparativo -- ignorada na
    varredura SÓ se tiver a marca E opacity 0 E estiver fora da árvore de
    acessibilidade (Semantics com exclude_semantics). Qualquer outro controle,
    inclusive uma faixa marcada mas visível, continua sendo verificado.
    """
    return (isinstance(controle, ft.Container) and controle.data == main.MARCA_MEDICAO_INVISIVEL
            and controle.opacity == 0 and isinstance(controle.content, ft.Semantics)
            and controle.content.exclude_semantics is True)


def percorrer_com_fundo(controle, fundo):
    """
    (controle, fundo efetivo) em pré-ordem, combinando os fundos translúcidos.
    O conteúdo de um Button/TextButton com fundo próprio é medido sobre esse
    fundo; o próprio botão continua recebendo o fundo de fora (a verificação
    do botão combina o `bgcolor` dele sobre esse fundo). A faixa de medição
    invisível (e_medicao_invisivel) é a única subárvore ignorada.
    """
    if e_medicao_invisivel(controle):
        return
    if isinstance(controle, (ft.Container, ft.AlertDialog, ft.SnackBar)) and controle.bgcolor:
        fundo = cor_solida(controle.bgcolor, fundo)
    yield controle, fundo
    if isinstance(controle, (ft.Button, ft.TextButton)) and fundo_do_botao(controle):
        fundo = cor_solida(fundo_do_botao(controle), fundo)
    for filho in filhos(controle):
        yield from percorrer_com_fundo(filho, fundo)


def tem_texto_legivel(valor):
    return bool(valor) and any(ch.isalnum() for ch in valor)


class TesteDeLegibilidade(TesteDeSessao):
    """Percorre as telas e os diálogos reais registrando cada "vista"."""

    def setUp(self):
        super().setUp()
        self.vistas = []  # (local, paleta esperada, controle raiz, fundo inicial)

    # ---------------------------------------------------------------- dados
    def popular(self, usuario_id):
        db.inicializar_categorias_padrao(usuario_id)
        categorias = db.listar_categorias(usuario_id)
        casa, outra = categorias[0]["id"], categorias[1]["id"]
        db.criar_conta_unica(usuario_id, "Atrasada", 50.0, "2026-09-01", categoria_id=casa)
        paga = db.criar_conta_unica(usuario_id, "Paga", 70.0, "2026-09-05", categoria_id=casa)
        db.marcar_conta_como_paga(paga, "2026-09-05")
        db.criar_conta_unica(usuario_id, "Avulsa", 30.0, "2026-09-18", descricao="Descrição\nde teste")
        db.criar_serie_recorrente(usuario_id, "Internet", 100.0, "2026-09-17", "mensal", categoria_id=outra)

    # ---------------------------------------------------------------- navegação
    def todos(self, pagina):
        return [c for raiz in pagina.controls for c, _ in percorrer_com_fundo(raiz, "#000000")]

    def registrar(self, pagina, local, paleta):
        for raiz in pagina.controls:
            self.vistas.append((local, paleta, raiz, paleta["fundo_pagina"]))
        for dialogo in pagina.dialogos:
            if dialogo.open:
                self.vistas.append((f"{local} [diálogo]", paleta, dialogo, paleta["fundo_pagina"]))

    @staticmethod
    def clicar(pagina, controle):
        controle.on_click(Evento(pagina, controle))

    def fechar_dialogos(self, pagina):
        while pagina.pop_dialog() is not None:
            pass

    def botao(self, pagina, rotulo, raiz=None):
        controles = self.todos(pagina) if raiz is None else [c for c, _ in percorrer_com_fundo(raiz, "#000000")]
        return next((c for c in controles if isinstance(c, (ft.Button, ft.TextButton, ft.OutlinedButton))
                     and c.content == rotulo), None)

    def clicavel_com_texto(self, pagina, texto):
        return next((c for c in self.todos(pagina) if isinstance(c, ft.Container) and c.on_click is not None
                     and any(isinstance(t, ft.Text) and t.value == texto for t, _ in percorrer_com_fundo(c, "#000000"))),
                    None)

    def ir_para_inicio(self, pagina):
        self.fechar_dialogos(pagina)
        for _ in range(4):
            aba = self.clicavel_com_texto(pagina, "Início")
            if aba is not None:
                self.clicar(pagina, aba)
                return
            voltar = self.botao(pagina, "Voltar") or self.botao(pagina, "Cancelar") or next(
                (c for c in self.todos(pagina) if isinstance(c, ft.IconButton) and c.icon == ft.Icons.ARROW_BACK), None)
            self.assertIsNotNone(voltar, "sem caminho de volta ao Início")
            self.clicar(pagina, voltar)
        self.fail("não voltou ao Início")

    def abrir_linha(self, pagina, nome):
        linha = next(c for c in self.todos(pagina) if isinstance(c, ft.Container) and c.on_click is not None
                     and isinstance(c.content, ft.Row) and c.border is not None
                     and any(isinstance(t, ft.Text) and t.value == nome for t, _ in percorrer_com_fundo(c, "#000000")))
        self.clicar(pagina, linha)

    def abrir_e_registrar_dialogo(self, pagina, rotulo, local, paleta):
        botao = self.botao(pagina, rotulo)
        self.assertIsNotNone(botao, f"botão {rotulo!r} não encontrado em {local}")
        self.clicar(pagina, botao)
        self.registrar(pagina, local, paleta)
        self.fechar_dialogos(pagina)

    def percorrer_app(self, pagina, paleta):
        """Todas as telas autenticadas e os seus diálogos principais, a partir do Início."""
        self.ir_para_inicio(pagina)
        self.registrar(pagina, "Início", paleta)

        # v7.0 5.44 (M3): seletor de mês e ano -- mês de hoje exibido (fundo e
        # contorno juntos, "Mês atual" desativado) e outro mês exibido (hoje só
        # com contorno).
        abrir_seletor = next(c for c in self.todos(pagina) if isinstance(c, ft.TextButton)
                             and c.data == "escolher_mes_e_ano")
        self.clicar(pagina, abrir_seletor)
        self.registrar(pagina, "Início/Escolher mês e ano", paleta)
        self.fechar_dialogos(pagina)
        seta = lambda icone: next(c for c in self.todos(pagina) if isinstance(c, ft.IconButton) and c.icon == icone)
        self.clicar(pagina, seta(ft.Icons.CHEVRON_RIGHT))
        self.clicar(pagina, next(c for c in self.todos(pagina) if isinstance(c, ft.TextButton)
                                 and c.data == "escolher_mes_e_ano"))
        self.registrar(pagina, "Início/Escolher mês e ano (outro mês)", paleta)
        self.fechar_dialogos(pagina)
        self.clicar(pagina, seta(ft.Icons.CHEVRON_LEFT))

        self.clicar(pagina, self.botao(pagina, "Ver status") or self.clicavel_com_texto(pagina, "Ver status"))
        self.registrar(pagina, "Ver status", paleta)
        for filtro in ("Pendentes", "Pagas", "Atrasadas"):
            alvo = self.clicavel_com_texto(pagina, filtro)
            self.clicar(pagina, alvo)
            self.registrar(pagina, f"Ver status/{filtro}", paleta)
        self.ir_para_inicio(pagina)

        self.clicar(pagina, self.clicavel_com_texto(pagina, "Ver essas contas"))   # banner de atraso
        self.registrar(pagina, "Contas em atraso", paleta)
        self.ir_para_inicio(pagina)

        for nome in ("Atrasada", "Paga", "Avulsa", "Internet"):
            self.abrir_linha(pagina, nome)
            self.registrar(pagina, f"Detalhes/{nome}", paleta)
            self.abrir_e_registrar_dialogo(pagina, "Excluir", f"Detalhes/{nome}/Excluir", paleta)
            self.clicar(pagina, self.botao(pagina, "Editar"))
            self.registrar(pagina, f"Editar/{nome}", paleta)
            if nome == "Avulsa":
                self.abrir_e_registrar_dialogo(pagina, "Transformar em recorrente", "Editar/Transformar", paleta)
            if nome == "Internet":
                self.abrir_e_registrar_dialogo(pagina, "Alterar frequência", "Editar/Alterar frequência", paleta)
                self.abrir_e_registrar_dialogo(pagina, "Encerrar recorrência", "Editar/Encerrar", paleta)
            valor = next(c for c in self.todos(pagina) if isinstance(c, ft.TextField) and c.label == "Valor")
            valor.value = "123,00"
            if valor.on_change:
                valor.on_change(Evento(pagina, valor))
            with redirect_stderr(io.StringIO()):
                self.clicar(pagina, self.botao(pagina, "Salvar alterações"))
            self.registrar(pagina, f"Editar/{nome}/após salvar", paleta)   # escopo ou "Alteração salva"
            self.ir_para_inicio(pagina)

        fab = next(c for c in self.todos(pagina) if isinstance(c, ft.Container) and c.on_click is not None
                   and isinstance(c.content, ft.Icon) and c.content.icon == ft.Icons.ADD)
        self.clicar(pagina, fab)
        self.registrar(pagina, "Nova conta", paleta)
        self.clicar(pagina, self.botao(pagina, "Salvar conta"))           # mensagem de erro de validação
        self.registrar(pagina, "Nova conta/erro", paleta)
        self.ir_para_inicio(pagina)

        self.clicar(pagina, self.clicavel_com_texto(pagina, "Categorias"))
        self.registrar(pagina, "Categorias", paleta)
        for icone, local in ((ft.Icons.ADD_CIRCLE, "nova"), (ft.Icons.EDIT, "editar"), (ft.Icons.DELETE, "excluir")):
            botao = next(c for c in self.todos(pagina) if isinstance(c, ft.IconButton) and c.icon == icone)
            self.clicar(pagina, botao)
            self.registrar(pagina, f"Categorias/{local}", paleta)
            self.fechar_dialogos(pagina)

        self.clicar(pagina, self.clicavel_com_texto(pagina, "Gráfico"))
        self.registrar(pagina, "Gráfico mensal", paleta)
        # Sino 6.9 (F8): aviso do comparativo (SnackBar) ao ativar um rótulo.
        rotulo = next(c for c in self.todos(pagina) if isinstance(c, ft.TextButton)
                      and isinstance(c.data, tuple) and c.data[0] == "rotulo_do_comparativo")
        self.clicar(pagina, rotulo)
        self.assertTrue(any(isinstance(d, ft.SnackBar) and d.open for d in pagina.dialogos))
        self.registrar(pagina, "Gráfico/aviso do comparativo", paleta)
        self.fechar_dialogos(pagina)
        self.clicar(pagina, self.clicavel_com_texto(pagina, "Anual"))
        self.registrar(pagina, "Gráfico anual", paleta)

        self.executar("UPDATE usuarios SET email_verificado = 1")   # Etapa 8: selo "Verificado" visível
        self.clicar(pagina, self.clicavel_com_texto(pagina, "Ajustes"))
        self.registrar(pagina, "Ajustes", paleta)
        alterar_senha = next(c for c in self.todos(pagina) if isinstance(c, ft.Container)
                             and c.data == "abrir_alterar_senha")
        self.clicar(pagina, alterar_senha)
        self.registrar(pagina, "Ajustes/Alterar senha", paleta)
        self.fechar_dialogos(pagina)
        editar_email = next(c for c in self.todos(pagina) if isinstance(c, ft.OutlinedButton)
                            and c.data == "editar_email")
        self.clicar(pagina, editar_email)
        self.registrar(pagina, "Ajustes/Alterar e-mail", paleta)
        self.fechar_dialogos(pagina)
        excluir_conta = next(c for c in self.todos(pagina) if isinstance(c, ft.Container)
                             and c.data == "abrir_excluir_conta")
        self.clicar(pagina, excluir_conta)
        self.registrar(pagina, "Ajustes/Excluir conta (aviso)", paleta)
        self.clicar(pagina, self.botao(pagina, "Continuar", raiz=next(d for d in pagina.dialogos if d.open)))
        self.registrar(pagina, "Ajustes/Excluir conta (senha)", paleta)
        self.fechar_dialogos(pagina)
        for chave in ("termos", "politica"):
            item = next(c for c in self.todos(pagina) if isinstance(c, ft.Container) and c.data == f"abrir_{chave}")
            self.clicar(pagina, item)
            self.registrar(pagina, f"Documento/{chave}", paleta)
            self.clicar(pagina, self.botao(pagina, "Voltar"))

    # ---------------------------------------------------------------- verificações
    @staticmethod
    def contraste_do_campo(campo, fundo, paleta):
        """Texto digitado, rótulo, dica e erro (4,5:1) e borda (3:1) de um campo."""
        def cor(estilo, padrao):
            return estilo.color if estilo is not None and estilo.color else padrao
        textos = {"texto": campo.color or paleta["texto_principal"],
                  "rótulo": cor(campo.label_style, paleta["texto_secundario"]),
                  "erro": cor(campo.error_style, paleta["texto_erro"])}
        if isinstance(campo, ft.TextField):
            textos["dica"] = cor(campo.hint_style, paleta["texto_secundario"])
        for nome, valor in textos.items():
            if contraste(cor_solida(valor, fundo), fundo) < MINIMO_TEXTO:
                yield f"{nome} abaixo de 4,5:1"
        borda = campo.border_color or paleta["borda_campo"]
        if contraste(cor_solida(borda, fundo), fundo) < MINIMO_NAO_TEXTO:
            yield "borda abaixo de 3:1"

    def cores_exclusivas_do_outro_tema(self, paleta):
        outra = ESCURO if paleta is CLARO else CLARO
        return {v.upper() for v in outra.values()} - {v.upper() for v in paleta.values()} - CORES_DE_CATEGORIA - {"WHITE"}

    def verificar_vistas(self, verificar_contraste, conhecidos=None, minimo_de_vistas=40, estilo_do_tema=False):
        """
        `estilo_do_tema`: campos sem estilo próprio usam as cores do `ft.Theme`
        da paleta (tema_flet: rótulo/dica = on_surface_variant, borda = outline),
        como nas telas de autenticação; nas demais telas o estilo é exigido.
        """
        self.assertGreater(len(self.vistas), minimo_de_vistas)
        problemas = self.problemas_das_vistas(self.vistas, verificar_contraste, estilo_do_tema)
        if conhecidos is None:
            self.assertEqual(sorted(set(problemas)), [])
        else:
            # Lista exata (sem o nome da tela): nada novo e nada já resolvido nela.
            self.assertEqual({p.split(": ", 1)[1] for p in problemas}, conhecidos)

    def problemas_das_vistas(self, vistas, verificar_contraste, estilo_do_tema=False):
        problemas = []
        for local, paleta, raiz, fundo_inicial in vistas:
            proibidas = self.cores_exclusivas_do_outro_tema(paleta)
            for controle, fundo in percorrer_com_fundo(raiz, fundo_inicial):
                tipo = type(controle).__name__
                for atributo in ATRIBUTOS_DE_COR:
                    valor = getattr(controle, atributo, None)
                    if isinstance(valor, str) and valor.split(",")[0].upper() in proibidas:
                        problemas.append(f"{local}: {tipo}.{atributo} = {valor} (cor do outro tema)")
                if isinstance(controle, ft.Text) and tem_texto_legivel(controle.value):
                    if controle.color is None:
                        problemas.append(f"{local}: texto sem cor explícita: {controle.value[:40]!r}")
                    elif verificar_contraste:
                        razao = contraste(cor_solida(controle.color, fundo), fundo)
                        if razao < MINIMO_TEXTO:
                            problemas.append(f"{local}: texto {razao:.2f}:1: {controle.value[:40]!r}")
                elif isinstance(controle, ft.Icon):
                    if controle.color is None:
                        problemas.append(f"{local}: ícone sem cor: {controle.icon}")
                    elif verificar_contraste and contraste(cor_solida(controle.color, fundo), fundo) < MINIMO_NAO_TEXTO:
                        problemas.append(f"{local}: ícone abaixo de 3:1: {controle.icon}")
                elif isinstance(controle, ft.IconButton):
                    if controle.icon_color is None:
                        problemas.append(f"{local}: botão de ícone sem cor: {controle.icon}")
                    elif verificar_contraste and not controle.disabled and \
                            contraste(cor_solida(controle.icon_color, fundo), fundo) < MINIMO_NAO_TEXTO:
                        problemas.append(f"{local}: botão de ícone abaixo de 3:1: {controle.icon}")
                elif isinstance(controle, (ft.Button, ft.TextButton, ft.OutlinedButton)):
                    cor = getattr(controle, "color", None) or (controle.style.color if controle.style else None)
                    if cor is None and estilo_do_tema and isinstance(controle, ft.TextButton):
                        cor = paleta["acao_primaria"]   # tema_flet: primary
                    if cor is None:
                        problemas.append(f"{local}: botão sem cor de texto: {controle.content!r}")
                    elif verificar_contraste and not controle.disabled:
                        base = cor_solida(controle.bgcolor, fundo) if getattr(controle, "bgcolor", None) else fundo
                        razao = contraste(cor_solida(cor, base), base)
                        if razao < MINIMO_TEXTO:
                            problemas.append(f"{local}: botão {razao:.2f}:1: {controle.content!r}")
                    # Sino 6.9 (F8): contorno de foco visível (3:1 sobre o fundo de fora).
                    lados = controle.style.side if controle.style else None
                    foco = lados.get(ft.ControlState.FOCUSED) if isinstance(lados, dict) else None
                    if verificar_contraste and foco is not None and foco.color and \
                            contraste(cor_solida(foco.color, fundo), fundo) < MINIMO_NAO_TEXTO:
                        problemas.append(f"{local}: foco do botão abaixo de 3:1: {controle.content!r}")
                elif isinstance(controle, (ft.TextField, ft.Dropdown)):
                    exigidos = ("color",) if estilo_do_tema else ("color", "border_color", "label_style")
                    for atributo in exigidos:
                        if getattr(controle, atributo) is None:
                            problemas.append(f"{local}: {tipo} {controle.label!r} sem {atributo}")
                    if isinstance(controle, ft.Dropdown) and controle.bgcolor is None:
                        problemas.append(f"{local}: lista {controle.label!r} sem fundo do menu")
                    if verificar_contraste:
                        problemas.extend(f"{local}: {tipo} {controle.label!r} {p}"
                                         for p in self.contraste_do_campo(controle, fundo, paleta))
                elif isinstance(controle, fch.BarChart) and verificar_contraste:
                    for grupo in controle.groups:
                        for barra in grupo.rods:
                            # 5.48 (Sino 6.9, F8): com contorno visível, é o CONTORNO que
                            # delimita a coluna contra o fundo (3:1) e o preenchimento (cor
                            # da categoria) é decorativo; sem contorno (ou com espessura 0),
                            # o preenchimento continua obrigado a 3:1.
                            contorno = barra.border_side
                            if contorno is not None and contorno.color and (contorno.width or 0) > 0:
                                if contraste(cor_solida(contorno.color, fundo), fundo) < MINIMO_NAO_TEXTO:
                                    problemas.append(f"{local}: contorno da barra abaixo de 3:1: {contorno.color}")
                            elif contraste(cor_solida(barra.color, fundo), fundo) < MINIMO_NAO_TEXTO:
                                problemas.append(f"{local}: barra abaixo de 3:1: {barra.color}")
                            estilo = barra.tooltip.text_style if barra.tooltip else None
                            if estilo is not None and contraste(cor_solida(estilo.color, fundo), fundo) < MINIMO_TEXTO:
                                problemas.append(f"{local}: valor da barra abaixo de 4,5:1: {barra.tooltip.text!r}")
                elif isinstance(controle, ft.Markdown):
                    folha = controle.md_style_sheet
                    if folha is None or folha.p_text_style.color != paleta["texto_principal"]:
                        problemas.append(f"{local}: Markdown sem as cores da paleta")
                    elif verificar_contraste and contraste(folha.p_text_style.color, fundo) < MINIMO_TEXTO:
                        problemas.append(f"{local}: Markdown abaixo de 4,5:1")
                elif isinstance(controle, ft.AlertDialog) and controle.bgcolor != paleta["fundo_dialogo"]:
                    problemas.append(f"{local}: diálogo sem o fundo da paleta")
        return problemas


# Etapa 10: os cinco casos residuais do Claro (camadas translúcidas) foram
# corrigidos -- texto das pílulas de status escurecido (#5E5D58 e #126A4F,
# fundo mantido) e ícones de Parcela, total e pagas em tons mais escuros.
# Lista exata e vazia: qualquer caso novo nas telas percorridas falha aqui.
LIMITACOES_TELAS_CLARO = set()


class TestTelasNoEscuro(TesteDeLegibilidade):
    def test_todas_as_telas_e_dialogos_legiveis_no_escuro(self):
        self.popular(self.ana)                                   # Ana: tema escuro gravado
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "ana@sino.com", "senha1234")
        self.assertEqual(sessao.cores.tema, "escuro")
        self.percorrer_app(pagina, ESCURO)
        self.verificar_vistas(verificar_contraste=True)

    def test_claro_sem_cores_do_escuro_e_legivel(self):
        # Etapa 10 (opção A da paleta): o Claro passa a ter o contraste medido
        # nas mesmas telas e diálogos percorridos no Escuro.
        self.popular(self.bia)
        pagina, _ = self.abrir_app()
        self.entrar(pagina, "bia@sino.com", "senha5678")
        self.percorrer_app(pagina, CLARO)
        self.verificar_vistas(verificar_contraste=True, conhecidos=LIMITACOES_TELAS_CLARO)


class TestNavegarDepoisDeTrocarOTema(TesteDeLegibilidade):
    def trocar_tema_em_ajustes(self, pagina, tema):
        self.clicar(pagina, self.clicavel_com_texto(pagina, "Ajustes"))
        opcao = next(c for c in self.todos(pagina) if isinstance(c, ft.Container) and c.data == f"tema_{tema}")
        self.clicar(pagina, opcao)

    def test_claro_para_escuro_recria_as_telas(self):
        self.popular(self.bia)
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "bia@sino.com", "senha5678")
        self.trocar_tema_em_ajustes(pagina, "escuro")
        self.assertEqual(sessao.cores.tema, "escuro")
        self.percorrer_app(pagina, ESCURO)
        self.verificar_vistas(verificar_contraste=True)

    def test_escuro_para_claro_recria_as_telas(self):
        self.popular(self.ana)
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "ana@sino.com", "senha1234")
        self.trocar_tema_em_ajustes(pagina, "claro")
        self.assertEqual(sessao.cores.tema, "claro")
        self.percorrer_app(pagina, CLARO)
        self.verificar_vistas(verificar_contraste=False)


class TestCodigoDasTelas(unittest.TestCase):
    """Garantias estáticas sobre backend/main.py (complementam as verificações dinâmicas)."""

    @classmethod
    def setUpClass(cls):
        with open(CAMINHO_MAIN, encoding="utf-8") as arquivo:
            cls.codigo = arquivo.read()
        cls.arvore = ast.parse(cls.codigo)

    def test_telas_autenticadas_nao_usam_as_cores_do_modulo(self):
        # O módulo só é usado para criar a Paleta e para o tema padrão/validação;
        # nenhum papel de cor é lido de `modulo_cores` (seria sempre o Claro).
        usados = set(re.findall(r"modulo_cores\.([A-Za-z_]+)", self.codigo))
        self.assertLessEqual(usados, {"Paleta", "TEMA_PADRAO", "PALETAS", "validar_tema"})
        self.assertEqual(usados & set(cores.PALETAS["claro"]), set())

    def test_controles_fora_do_login_tem_cor_explicita(self):
        login = next(n for n in ast.walk(self.arvore)
                     if isinstance(n, ast.FunctionDef) and n.name == "mostrar_tela_login")
        exigido = {"Text": "color", "Icon": "color", "IconButton": "icon_color", "TextButton": "style",
                   "OutlinedButton": "style", "TextField": "border_color", "Dropdown": "border_color",
                   "AlertDialog": "bgcolor"}
        faltando = []
        for n in ast.walk(self.arvore):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and getattr(n.func.value, "id", None) == "ft" and n.func.attr in exigido):
                continue
            if login.lineno <= n.lineno <= login.end_lineno:
                continue  # autenticação: sempre Claro (P8)
            argumentos = {k.arg for k in n.keywords}
            if exigido[n.func.attr] in argumentos or None in argumentos:  # None: **estilo_...()
                continue
            if n.func.attr == "Text" and n.args and re.search(r"emoji|icone", ast.unparse(n.args[0])):
                continue  # glifo de emoji: a cor não se aplica
            faltando.append((n.lineno, n.func.attr))
        self.assertEqual(faltando, [])


class TestFundoDosBotoes(TesteDeLegibilidade):
    """
    Sino 6.9 (F2.1): o texto dentro de um botão é medido sobre o fundo que o
    botão exibe (por exemplo, o mês selecionado do seletor: texto_sobre_acao
    sobre acao_primaria), e não sobre o fundo do diálogo; sem fundo próprio,
    vale o fundo herdado. Controles montados à mão, nos dois temas.
    """

    def dialogo_com(self, *controles, paleta):
        return ft.AlertDialog(bgcolor=paleta["fundo_dialogo"], content=ft.Row(controls=list(controles)))

    @staticmethod
    def fundo_do_dialogo(paleta):
        # Normalizado como na varredura ("white" -> "#FFFFFF").
        return cor_solida(paleta["fundo_dialogo"], paleta["fundo_pagina"])

    def fundos(self, raiz, fundo_inicial):
        return {id(c): f for c, f in percorrer_com_fundo(raiz, fundo_inicial)}

    def problemas(self, raiz, paleta):
        return self.problemas_das_vistas([("teste", paleta, raiz, paleta["fundo_pagina"])], True)

    def test_texto_branco_sobre_o_fundo_do_mes_selecionado(self):
        for nome, paleta in (("claro", CLARO), ("escuro", ESCURO)):
            with self.subTest(tema=nome):
                texto = ft.Text("Out", color=paleta["texto_sobre_acao"])
                botao = ft.Button(content=texto, bgcolor=paleta["acao_primaria"], color=paleta["texto_sobre_acao"])
                dialogo = self.dialogo_com(botao, paleta=paleta)
                fundos = self.fundos(dialogo, paleta["fundo_pagina"])
                self.assertEqual(fundos[id(texto)], cor_solida(paleta["acao_primaria"], paleta["fundo_dialogo"]))
                self.assertEqual(fundos[id(botao)], self.fundo_do_dialogo(paleta))   # o botão segue com o fundo de fora
                self.assertGreaterEqual(contraste(paleta["texto_sobre_acao"], paleta["acao_primaria"]), MINIMO_TEXTO)
                self.assertEqual(self.problemas(dialogo, paleta), [])

    def test_botao_sem_fundo_proprio_usa_o_fundo_herdado(self):
        for nome, paleta in (("claro", CLARO), ("escuro", ESCURO)):
            with self.subTest(tema=nome):
                texto_button = ft.Text("Nov", color=paleta["texto_principal"])
                texto_textbutton = ft.Text("Outubro 2026", color=paleta["texto_principal"])
                button = ft.Button(content=texto_button, color=paleta["texto_principal"])
                textbutton = ft.TextButton(content=texto_textbutton,
                                           style=ft.ButtonStyle(color=paleta["texto_principal"]))
                dialogo = self.dialogo_com(button, textbutton, paleta=paleta)
                fundos = self.fundos(dialogo, paleta["fundo_pagina"])
                self.assertEqual(fundos[id(texto_button)], self.fundo_do_dialogo(paleta))
                self.assertEqual(fundos[id(texto_textbutton)], self.fundo_do_dialogo(paleta))
                self.assertEqual(self.problemas(dialogo, paleta), [])

    def test_fundo_do_textbutton_pelo_estilo(self):
        for nome, paleta in (("claro", CLARO), ("escuro", ESCURO)):
            with self.subTest(tema=nome):
                texto = ft.Text("Mês", color=paleta["texto_sobre_acao"])
                botao = ft.TextButton(content=texto, style=ft.ButtonStyle(
                    color=paleta["texto_sobre_acao"], bgcolor={ft.ControlState.DEFAULT: paleta["acao_primaria"]}))
                fundos = self.fundos(self.dialogo_com(botao, paleta=paleta), paleta["fundo_pagina"])
                self.assertEqual(fundos[id(texto)], cor_solida(paleta["acao_primaria"], paleta["fundo_dialogo"]))

    def test_falha_real_dentro_do_botao_continua_detectada(self):
        # Texto na mesma cor do fundo do botão: precisa continuar falhando.
        for nome, paleta in (("claro", CLARO), ("escuro", ESCURO)):
            with self.subTest(tema=nome):
                texto = ft.Text("Out", color=paleta["acao_primaria"])
                botao = ft.Button(content=texto, bgcolor=paleta["acao_primaria"], color=paleta["texto_sobre_acao"])
                problemas = self.problemas(self.dialogo_com(botao, paleta=paleta), paleta)
                self.assertEqual(len(problemas), 1)
                self.assertIn("texto 1.00:1: 'Out'", problemas[0])

    def test_texto_do_botao_sem_fundo_proprio_continua_medido_no_fundo_herdado(self):
        # Sem fundo próprio, um texto claro sobre o diálogo claro continua falhando.
        texto = ft.Text("Nov", color=CLARO["fundo_dialogo"])
        botao = ft.Button(content=texto, color=CLARO["texto_principal"])
        problemas = self.problemas(self.dialogo_com(botao, paleta=CLARO), CLARO)
        self.assertEqual(len(problemas), 1)
        self.assertIn("'Nov'", problemas[0])


class TestMedicaoInvisivel(TesteDeLegibilidade):
    """
    Sino 6.9 (F6, DF3): só a faixa técnica de medição -- marcada, opacity 0 e
    fora da acessibilidade -- sai da varredura; texto visível continua medido.
    Controles montados à mão, no Claro (texto da cor do fundo: 1,00:1).
    """

    def faixa(self, texto, marca=main.MARCA_MEDICAO_INVISIVEL, opacidade=0, excluir=True):
        return ft.Container(data=marca, height=0, opacity=opacidade,
                            content=ft.Semantics(exclude_semantics=excluir, content=ft.Column(controls=[texto])))

    def problemas(self, *controles):
        raiz = ft.Container(bgcolor=CLARO["fundo_card"], content=ft.Column(controls=list(controles)))
        return self.problemas_das_vistas([("teste", CLARO, raiz, CLARO["fundo_pagina"])], True)

    def ilegivel(self, valor="Casa"):
        return ft.Text(valor, color=CLARO["fundo_card"])

    def test_faixa_invisivel_e_ignorada(self):
        self.assertEqual(self.problemas(self.faixa(self.ilegivel())), [])

    def test_texto_visivel_continua_verificado(self):
        problemas = self.problemas(self.faixa(ft.Text("Lazer", color=CLARO["texto_principal"])), self.ilegivel())
        self.assertEqual(len(problemas), 1)
        self.assertIn("'Casa'", problemas[0])

    def test_faixa_marcada_mas_visivel_nao_e_ignorada(self):
        for opacidade in (1, 0.5, None):
            with self.subTest(opacidade=opacidade):
                problemas = self.problemas(self.faixa(self.ilegivel(), opacidade=opacidade))
                self.assertEqual(len(problemas), 1)
                self.assertIn("texto 1.00:1: 'Casa'", problemas[0])

    def test_faixa_na_acessibilidade_ou_sem_marca_nao_e_ignorada(self):
        for faixa in (self.faixa(self.ilegivel(), excluir=False),
                      self.faixa(self.ilegivel(), marca=None),
                      self.faixa(self.ilegivel(), marca="outra")):
            with self.subTest(marca=faixa.data, excluir=faixa.content.exclude_semantics):
                self.assertEqual(len(self.problemas(faixa)), 1)
        # Opacity 0 sem a marca (um aviso escondido, por exemplo) também é verificado.
        escondido = ft.Container(opacity=0, content=self.ilegivel())
        self.assertEqual(len(self.problemas(escondido)), 1)

    def test_faixa_do_comparativo_no_app(self):
        # A faixa real do Gráfico atende às três condições e não tem nada focável;
        # é a única subárvore que a varredura deixa de percorrer.
        def arvore(controle):
            yield controle
            for filho in filhos(controle):
                yield from arvore(filho)

        self.popular(self.bia)
        pagina, _ = self.abrir_app()
        self.entrar(pagina, "bia@sino.com", "senha5678")
        self.clicar(pagina, self.clicavel_com_texto(pagina, "Gráfico"))
        tudo = [c for raiz in pagina.controls for c in arvore(raiz)]
        faixas = [c for c in tudo if isinstance(c, ft.Container) and c.data == main.MARCA_MEDICAO_INVISIVEL]
        self.assertEqual(len(faixas), 1)
        self.assertTrue(e_medicao_invisivel(faixas[0]))
        dentro = list(arvore(faixas[0]))
        self.assertTrue(any(isinstance(c, ft.Text) for c in dentro))
        self.assertFalse(any(isinstance(c, (ft.Button, ft.TextButton, ft.IconButton, ft.OutlinedButton,
                                            ft.TextField, ft.Dropdown)) for c in dentro))
        ignorados = {id(c) for c in tudo} - {id(c) for raiz in pagina.controls for c, _ in percorrer_com_fundo(raiz, "#000000")}
        self.assertEqual(ignorados, {id(c) for c in dentro})


class TestContrasteDoComparativo(TesteDeLegibilidade):
    """
    Sino 6.9 (F8; 5.48): contorno das colunas (3:1), preenchimento decorativo só
    com contorno, valores e rótulos (4,5:1), foco (3:1) e aviso (4,5:1), nos dois
    temas. Controles montados à mão: a regra precisa ACUSAR cada defeito.
    """
    PASTEL = "#FFD54F"   # cor de categoria abaixo de 3:1 sobre o cartão do Claro

    def coluna(self, paleta, cor=PASTEL, contorno=None, valor_cor=None):
        return fch.BarChartRod(
            to_y=10, color=cor, border_side=contorno, selected=True,
            tooltip=fch.BarChartRodTooltip(text="R$ 10,00", text_style=ft.TextStyle(
                color=valor_cor or paleta["texto_principal"])))

    def problemas(self, paleta, *controles):
        raiz = ft.Container(bgcolor=paleta["fundo_card"], content=ft.Column(controls=list(controles)))
        return self.problemas_das_vistas([("teste", paleta, raiz, paleta["fundo_pagina"])], True)

    def grafico(self, *colunas):
        return fch.BarChart(groups=[fch.BarChartGroup(x=i, rods=[c]) for i, c in enumerate(colunas)])

    def test_preenchimento_pastel_aceito_so_com_contorno_contrastante(self):
        for nome, paleta in (("claro", CLARO), ("escuro", ESCURO)):
            with self.subTest(tema=nome):
                contorno = ft.BorderSide(1, paleta["texto_principal"])
                self.assertEqual(self.problemas(paleta, self.grafico(self.coluna(paleta, contorno=contorno))), [])

    def test_contorno_abaixo_de_3_para_1_e_acusado(self):
        problemas = self.problemas(CLARO, self.grafico(self.coluna(CLARO, contorno=ft.BorderSide(1, "#DDDDDD"))))
        self.assertEqual(len(problemas), 1)
        self.assertIn("contorno da barra abaixo de 3:1: #DDDDDD", problemas[0])

    def test_sem_contorno_o_preenchimento_volta_a_ser_exigido(self):
        for contorno in (None, ft.BorderSide(0, CLARO["texto_principal"])):
            with self.subTest(contorno=contorno):
                problemas = self.problemas(CLARO, self.grafico(self.coluna(CLARO, contorno=contorno)))
                self.assertEqual(len(problemas), 1)
                self.assertIn(f"barra abaixo de 3:1: {self.PASTEL}", problemas[0])

    def test_contorno_do_tema_errado_e_acusado_no_escuro(self):
        contorno = ft.BorderSide(1, CLARO["texto_principal"])   # escuro sobre o cartão escuro
        self.assertEqual(self.problemas(CLARO, self.grafico(self.coluna(CLARO, contorno=contorno))), [])
        problemas = self.problemas(ESCURO, self.grafico(self.coluna(ESCURO, contorno=contorno)))
        self.assertTrue(any("contorno da barra abaixo de 3:1" in p for p in problemas))

    def test_valor_e_rotulo_abaixo_de_4_5_para_1_sao_acusados(self):
        contorno = ft.BorderSide(1, CLARO["texto_principal"])
        coluna = self.coluna(CLARO, contorno=contorno, valor_cor="#AAAAAA")
        rotulo = ft.TextButton(content=ft.Text("Casa", color="#AAAAAA"), style=ft.ButtonStyle(color="#AAAAAA"))
        problemas = self.problemas(CLARO, self.grafico(coluna), rotulo)
        self.assertTrue(any("valor da barra abaixo de 4,5:1" in p for p in problemas))
        self.assertTrue(any("texto" in p and "'Casa'" in p for p in problemas))
        self.assertTrue(any(p.split(": ", 1)[1].startswith("botão ") for p in problemas))

    def test_foco_abaixo_de_3_para_1_e_acusado(self):
        for nome, paleta, ruim in (("claro", CLARO, "#EEEEEE"), ("escuro", ESCURO, "#202825")):
            with self.subTest(tema=nome):
                botao = ft.TextButton(content=ft.Text("Casa", color=paleta["texto_principal"]),
                                      style=ft.ButtonStyle(color=paleta["texto_principal"],
                                                           side={ft.ControlState.FOCUSED: ft.BorderSide(2, ruim)}))
                problemas = self.problemas(paleta, botao)
                self.assertEqual(len(problemas), 1)
                self.assertIn("foco do botão abaixo de 3:1", problemas[0])
                botao.style.side[ft.ControlState.FOCUSED] = ft.BorderSide(2, paleta["acao_primaria"])
                self.assertEqual(self.problemas(paleta, botao), [])

    def test_aviso_medido_sobre_o_proprio_fundo(self):
        for nome, paleta in (("claro", CLARO), ("escuro", ESCURO)):
            with self.subTest(tema=nome):
                bom = ft.SnackBar(ft.Text("Casa: R$ 10,00", color=paleta["fundo_card"]), bgcolor=paleta["texto_principal"])
                ruim = ft.SnackBar(ft.Text("Casa: R$ 10,00", color=paleta["texto_principal"]),
                                   bgcolor=paleta["texto_principal"])
                vistas = lambda aviso: [("teste", paleta, aviso, paleta["fundo_pagina"])]
                self.assertEqual(self.problemas_das_vistas(vistas(bom), True), [])
                self.assertEqual(len(self.problemas_das_vistas(vistas(ruim), True)), 1)

    def test_botao_visivel_marcado_como_medicao_nao_escapa(self):
        botao = ft.TextButton(content=ft.Text("Casa", color="#FFFFFF"), style=ft.ButtonStyle(color="#FFFFFF"))
        faixa = ft.Container(data=main.MARCA_MEDICAO_INVISIVEL, opacity=1,
                             content=ft.Semantics(exclude_semantics=True, content=botao))
        problemas = self.problemas(CLARO, faixa)
        self.assertEqual(len(problemas), 2)   # o botão e o texto dentro dele

    def test_vistas_reais_cobrem_colunas_com_contorno_e_aviso(self):
        # A aprovação das telas não é vazia: o Gráfico real tem o comparativo,
        # com contorno em todas as colunas, e o aviso entra nas vistas.
        self.popular(self.bia)
        pagina, _ = self.abrir_app()
        self.entrar(pagina, "bia@sino.com", "senha5678")
        self.percorrer_app(pagina, CLARO)
        locais = {local for local, _, _, _ in self.vistas}
        self.assertIn("Gráfico/aviso do comparativo [diálogo]", locais)
        graficos = [c for local, _, raiz, fundo in self.vistas if local == "Gráfico mensal"
                    for c, _ in percorrer_com_fundo(raiz, fundo) if isinstance(c, fch.BarChart)]
        comparativo = [g for g in graficos if g.groups and g.groups[0].rods[0].border_side is not None]
        # Sino 6.9 (F7-A2): um gráfico por categoria, todos varridos, com a mesma escala.
        self.assertGreaterEqual(len(comparativo), 2)
        self.assertTrue(all(len(g.groups) == 1 and len(g.groups[0].rods) == 1 for g in comparativo))
        self.assertEqual(len({g.max_y for g in comparativo}), 1)
        self.assertTrue(all(r.border_side.width >= 1 and r.border_side.color == CLARO["texto_principal"]
                            for g in comparativo for grupo in g.groups for r in grupo.rods))
        rotulos = [l.label for g in comparativo for l in g.bottom_axis.labels]
        self.assertTrue(all(isinstance(c, ft.Container) and isinstance(c.content, ft.TextButton) for c in rotulos))
        abaixo = [r.color for g in comparativo for grupo in g.groups for r in grupo.rods
                  if contraste(cor_solida(r.color, "#FFFFFF"), "#FFFFFF") < MINIMO_NAO_TEXTO]
        self.assertTrue(abaixo)   # há preenchimento pastel: o contorno é que garante os 3:1


class TestTemaDoFlet(unittest.TestCase):
    def test_dialogos_e_calendario_seguem_a_paleta_de_cada_tema(self):
        for tema, paleta in (("claro", CLARO), ("escuro", ESCURO)):
            with self.subTest(tema=tema):
                tema_flet = main.tema_flet(tema)
                self.assertEqual(tema_flet.dialog_theme.bgcolor, paleta["fundo_dialogo"])
                self.assertEqual(tema_flet.dialog_theme.title_text_style.color, paleta["texto_principal"])
                self.assertEqual(tema_flet.dialog_theme.content_text_style.color, paleta["texto_principal"])
                calendario = tema_flet.date_picker_theme
                self.assertEqual(calendario.bgcolor, paleta["fundo_dialogo"])
                self.assertEqual(calendario.header_foreground_color, paleta["texto_principal"])
                # v7.0 5.47 (M6): cor do número de hoje por estado.
                self.assertEqual(calendario.today_foreground_color, {
                    ft.ControlState.SELECTED: paleta["texto_sobre_acao"],
                    ft.ControlState.DEFAULT: paleta["acao_primaria"],
                })
                self.assertEqual(calendario.today_border_side.color, paleta["acao_primaria"])
                self.assertEqual(tema_flet.color_scheme.on_primary, paleta["texto_sobre_acao"])

    def test_calendario_no_escuro_tem_contraste(self):
        self.assertGreaterEqual(contraste(ESCURO["texto_principal"], ESCURO["fundo_dialogo"]), MINIMO_TEXTO)
        self.assertGreaterEqual(contraste(ESCURO["acao_primaria"], ESCURO["fundo_dialogo"]), MINIMO_TEXTO)
        self.assertGreaterEqual(contraste(ESCURO["texto_sobre_acao"], ESCURO["acao_primaria"]), MINIMO_TEXTO)

    def test_tema_invalido(self):
        with self.assertRaises(cores.TemaInvalidoError):
            main.tema_flet("azul")


if __name__ == "__main__":
    unittest.main()
