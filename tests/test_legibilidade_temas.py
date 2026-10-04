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

O Claro NÃO é declarado conforme: suas limitações conhecidas (texto
secundário, verdes da marca, ícones sobre fundos tingidos) continuam
registradas em test_cores.py e ficam para a Etapa 10.
"""

import ast
import io
import os
import re
import unittest
from contextlib import redirect_stderr

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


def percorrer_com_fundo(controle, fundo):
    """(controle, fundo efetivo) em pré-ordem, combinando os fundos translúcidos."""
    if isinstance(controle, (ft.Container, ft.AlertDialog)) and controle.bgcolor:
        fundo = cor_solida(controle.bgcolor, fundo)
    yield controle, fundo
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
    def cores_exclusivas_do_outro_tema(self, paleta):
        outra = ESCURO if paleta is CLARO else CLARO
        return {v.upper() for v in outra.values()} - {v.upper() for v in paleta.values()} - CORES_DE_CATEGORIA - {"WHITE"}

    def verificar_vistas(self, verificar_contraste):
        self.assertGreater(len(self.vistas), 40)
        problemas = []
        for local, paleta, raiz, fundo_inicial in self.vistas:
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
                    if cor is None:
                        problemas.append(f"{local}: botão sem cor de texto: {controle.content!r}")
                    elif verificar_contraste and not controle.disabled:
                        base = cor_solida(controle.bgcolor, fundo) if getattr(controle, "bgcolor", None) else fundo
                        razao = contraste(cor_solida(cor, base), base)
                        if razao < MINIMO_TEXTO:
                            problemas.append(f"{local}: botão {razao:.2f}:1: {controle.content!r}")
                elif isinstance(controle, (ft.TextField, ft.Dropdown)):
                    for atributo in ("color", "border_color", "label_style"):
                        if getattr(controle, atributo) is None:
                            problemas.append(f"{local}: {tipo} {controle.label!r} sem {atributo}")
                    if isinstance(controle, ft.Dropdown) and controle.bgcolor is None:
                        problemas.append(f"{local}: lista {controle.label!r} sem fundo do menu")
                elif isinstance(controle, ft.Markdown):
                    folha = controle.md_style_sheet
                    if folha is None or folha.p_text_style.color != paleta["texto_principal"]:
                        problemas.append(f"{local}: Markdown sem as cores da paleta")
                    elif verificar_contraste and contraste(folha.p_text_style.color, fundo) < MINIMO_TEXTO:
                        problemas.append(f"{local}: Markdown abaixo de 4,5:1")
                elif isinstance(controle, ft.AlertDialog) and controle.bgcolor != paleta["fundo_dialogo"]:
                    problemas.append(f"{local}: diálogo sem o fundo da paleta")
        self.assertEqual(sorted(set(problemas)), [])


class TestTelasNoEscuro(TesteDeLegibilidade):
    def test_todas_as_telas_e_dialogos_legiveis_no_escuro(self):
        self.popular(self.ana)                                   # Ana: tema escuro gravado
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "ana@sino.com", "senha1234")
        self.assertEqual(sessao.cores.tema, "escuro")
        self.percorrer_app(pagina, ESCURO)
        self.verificar_vistas(verificar_contraste=True)

    def test_claro_sem_cores_do_escuro_e_com_cores_explicitas(self):
        # Contraste do Claro não é verificado aqui: limitações conhecidas (test_cores.py).
        self.popular(self.bia)
        pagina, _ = self.abrir_app()
        self.entrar(pagina, "bia@sino.com", "senha5678")
        self.percorrer_app(pagina, CLARO)
        self.verificar_vistas(verificar_contraste=False)


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
                self.assertEqual(calendario.today_foreground_color, paleta["acao_primaria"])
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
