"""
main.py — App do Sino em Flet, conectado ao banco SQLite.
Tela de login/cadastro + tela de Categorias (CRUD).
"""

import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database"))

import flet as ft
import db as database

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

# RF18/5.12 (Fase D4): sugestões de emoji por nome de categoria pré-criada --
# dado só de apresentação (UI), por isso vive aqui e não em database/db.py.
# Baseado na tabela da seção 5.12 do ERS v5.0; a própria ERS declara esses
# valores como "proposta inicial de UX, não valores imutáveis". A linha
# "Casa" da ERS lista só 4 emojis (🏡 🏘️ 🏚️ 🏢) -- completada aqui com uma
# quinta opção coerente (🛋️) para manter 5 sugestões por categoria, como o
# restante da tabela já tem. Chaves normalizadas (minúsculas, sem espaços
# nas bordas) -- ver sugestoes_emoji_para.
SUGESTOES_EMOJI_CATEGORIA = {
    "casa": ["🏡", "🏘️", "🏚️", "🏢", "🛋️"],
    "automóvel": ["🚗", "🚕", "🏍️", "✈️", "🚃"],
    "lazer": ["🎡", "🏟️", "🏖️", "🎮", "🎳"],
    "faculdade": ["📚", "📋", "📝", "👩‍💻", "📖"],
    "academia": ["🏋🏻‍♀️", "⛹🏻‍♂️", "🛹", "🏊🏻‍♂️", "🚴🏻‍♂️"],
    "saúde": ["🏥", "💊", "🩺", "🩻", "💉"],
    "cartão de crédito": ["💳", "💵", "🪙", "💰", "🪪"],
    "beleza": ["💄", "💅🏻", "👗", "👟", "👜"],
    "streaming": ["📽️", "🎥", "📺", "🍿", "🎬"],
    "creche": ["👶", "👧", "🧒", "🧸", "🚼"],
    "outro": ["💕", "🔨", "🐾", "🧳", "🛒"],
}


def sugestoes_emoji_para(nome):
    """RF18 (5.12): 5 sugestões de emoji para um nome de categoria
    reconhecido, ou lista vazia se não houver sugestão específica (ERS:
    "sem sugestões pré-definidas específicas" para categorias do usuário).
    Comparação tolerante a diferenças simples de maiúsculas/minúsculas e
    espaços nas bordas -- nada além disso."""
    chave = (nome or "").strip().lower()
    return SUGESTOES_EMOJI_CATEGORIA.get(chave, [])


def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def frase_vencimento_futuro(dias_delta):
    """RF11 (5.17): linguagem natural para uma conta pendente/a vencer -- só
    apresentação, não recalcula nem reinterpreta dias_delta."""
    if dias_delta == 0:
        return "vence hoje"
    if dias_delta == 1:
        return "vence amanhã"
    return f"vence em {dias_delta} dias"


def frase_vencimento_passado(dias_atraso):
    """RF11 (5.17): linguagem natural para uma conta atrasada. `dias_atraso`
    é a quantidade de dias já passados (positiva) -- quem chama já calcula
    isso a partir de dias_delta; esta função só formata o texto."""
    if dias_atraso == 1:
        return "venceu ontem"
    return f"venceu há {dias_atraso} dias"


def frase_resumo_proximas(quantidade):
    """RF17 (5.17): singular/plural correto para o resumo de contas que
    vencem nos próximos 7 dias."""
    if quantidade == 1:
        return "1 conta vence nos próximos 7 dias"
    return f"{quantidade} contas vencem nos próximos 7 dias"


def parse_valor(texto):
    texto = (texto or "").strip().replace("R$", "").strip()
    if not texto:
        return None
    if "," in texto:
        # vírgula é o separador decimal; pontos restantes são de milhar
        texto = texto.replace(".", "").replace(",", ".")
    elif "." in texto and len(texto.rsplit(".", 1)[-1]) == 3:
        # sem vírgula: ponto seguido de 3 dígitos é separador de milhar
        # (ex.: "1.234" -> 1234); com 1 ou 2 dígitos, é decimal (ex.: "150.50")
        texto = texto.replace(".", "")
    try:
        valor = float(texto)
    except ValueError:
        return None
    return valor if valor > 0 else None


def main(page: ft.Page):
    database.criar_tabelas()

    page.title = "Sino"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F4F4F1"
    page.window.width = 380
    page.window.height = 760
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 24

    usuario_atual = {"id": None, "nome": None}

    # ======================================================
    #  BARRA DE NAVEGAÇÃO (reutilizável entre as telas)
    # ======================================================
    def barra_navegacao(aba_ativa):
        def item(nome_aba, icone, rotulo, on_click):
            ativa = aba_ativa == nome_aba
            cor = "#1D9E75" if ativa else "#888780"
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(icone, color=cor, size=22),
                        ft.Text(rotulo, size=11, color=cor),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                ),
                on_click=on_click,
                padding=ft.Padding(0, 8, 0, 8),
                expand=True,
                alignment=ft.Alignment.CENTER,
            )

        return ft.Container(
            bgcolor="white",
            border=ft.Border(top=ft.BorderSide(1, "#E5E4DE")),
            content=ft.Row(
                controls=[
                    item("inicio", ft.Icons.HOME, "Início", lambda e: mostrar_tela_principal()),
                    item("categorias", ft.Icons.FOLDER, "Categorias", lambda e: mostrar_tela_categorias()),
                    item("grafico", ft.Icons.BAR_CHART, "Gráfico", None),
                    item("ajustes", ft.Icons.SETTINGS, "Ajustes", None),
                ],
            ),
        )

    # ======================================================
    #  TELA DE LOGIN / CADASTRO
    # ======================================================
    def mostrar_tela_login():
        page.controls.clear()
        page.padding = 24
        modo_cadastro = [False]

        logo = ft.Container(
            content=ft.Text("$ino", size=28, weight=ft.FontWeight.BOLD, color="#39D67C"),
            bgcolor="#0B1410",
            width=80,
            height=80,
            border_radius=40,
            alignment=ft.Alignment.CENTER,
        )

        titulo = ft.Text("Bem-vindo de volta", size=20, weight=ft.FontWeight.BOLD, color="#0B1410")
        subtitulo = ft.Text("Suas contas, sob controle.", size=13, color="#888780")

        campo_nome = ft.TextField(label="Nome completo", hint_text="Seu nome", width=330, visible=False,
                                   color="#0B1410")
        campo_email = ft.TextField(label="E-mail", hint_text="voce@email.com", width=330, color="#0B1410")
        campo_senha = ft.TextField(label="Senha", hint_text="********", password=True,
                                    can_reveal_password=True, width=330, color="#0B1410")
        mensagem = ft.Text(value="", color="#1D9E75")

        def ao_clicar_botao_principal(e):
            email = campo_email.value.strip() if campo_email.value else ""
            senha = campo_senha.value if campo_senha.value else ""

            if modo_cadastro[0]:
                nome = campo_nome.value.strip() if campo_nome.value else ""
                if not nome or not email or not senha:
                    mensagem.value = "Preencha nome, e-mail e senha."
                    mensagem.color = "#A32D2D"
                else:
                    sucesso, texto = database.criar_usuario(nome, email, senha)
                    mensagem.value = texto
                    mensagem.color = "#1D9E75" if sucesso else "#A32D2D"
                    if sucesso:
                        # criar_usuario não retorna o id do novo usuário; buscamos via
                        # verificar_login (mesmas credenciais, já validadas) para poder
                        # inicializar o catálogo de categorias (RF14/5.11).
                        novo_usuario = database.verificar_login(email, senha)
                        if novo_usuario:
                            try:
                                database.inicializar_categorias_padrao(novo_usuario["id"])
                            except Exception:
                                # Não deixa uma falha aqui impedir a confirmação de que a
                                # conta foi criada -- o cadastro em si já foi concluído.
                                pass
                        alternar_modo(None)
                        mensagem.value = "Conta criada com sucesso! Faça login para continuar."
                        mensagem.color = "#1D9E75"
                        page.update()
            else:
                if not email or not senha:
                    mensagem.value = "Preencha e-mail e senha."
                    mensagem.color = "#A32D2D"
                else:
                    usuario = database.verificar_login(email, senha)
                    if usuario:
                        usuario_atual["id"] = usuario["id"]
                        usuario_atual["nome"] = usuario["nome"]
                        mostrar_tela_principal()
                        return
                    else:
                        mensagem.value = "E-mail ou senha incorretos."
                        mensagem.color = "#A32D2D"

            page.update()

        botao_principal = ft.Button(
            content="Entrar",
            width=330,
            bgcolor="#1D9E75",
            color="white",
            on_click=ao_clicar_botao_principal,
        )

        def alternar_modo(e):
            modo_cadastro[0] = not modo_cadastro[0]
            campo_nome.value = ""
            campo_email.value = ""
            campo_senha.value = ""
            if modo_cadastro[0]:
                titulo.value = "Crie sua conta"
                subtitulo.value = "Leva menos de um minuto"
                campo_nome.visible = True
                botao_principal.content = "Criar conta"
                texto_alternar.content = "Já tem conta? Entrar"
            else:
                titulo.value = "Bem-vindo de volta"
                subtitulo.value = "Suas contas, sob controle."
                campo_nome.visible = False
                botao_principal.content = "Entrar"
                texto_alternar.content = "Não tem conta? Criar conta"
            mensagem.value = ""
            page.update()

        texto_alternar = ft.TextButton(content="Não tem conta? Criar conta", on_click=alternar_modo)

        page.add(
            ft.Column(
                controls=[
                    ft.Container(height=20),
                    logo,
                    ft.Container(height=16),
                    titulo,
                    subtitulo,
                    ft.Container(height=24),
                    campo_nome,
                    campo_email,
                    campo_senha,
                    ft.Container(height=8),
                    botao_principal,
                    mensagem,
                    texto_alternar,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        page.update()

    # ======================================================
    #  TELA PRINCIPAL
    # ======================================================
    def mostrar_tela_principal():
        page.controls.clear()
        page.padding = 0

        hoje = date.today()
        mes_atual = [hoje.year, hoje.month]

        avatar = ft.Container(
            content=ft.Text("$", size=18, weight=ft.FontWeight.BOLD, color="#39D67C"),
            bgcolor="#0B1410",
            width=40,
            height=40,
            border_radius=20,
            alignment=ft.Alignment.CENTER,
        )

        nome_usuario = ft.Text(usuario_atual["nome"] or "", size=16, weight=ft.FontWeight.BOLD, color="#0B1410")

        sino = ft.Stack(
            controls=[
                ft.Icon(ft.Icons.NOTIFICATIONS_NONE, size=24, color="#0B1410"),
                ft.Container(width=8, height=8, bgcolor="#A32D2D", border_radius=4, right=0, top=0),
            ],
            width=28,
            height=28,
        )

        cabecalho_topo = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(
                    controls=[
                        avatar,
                        ft.Container(width=10),
                        ft.Column(
                            controls=[
                                ft.Text("Olá,", size=13, color="#888780"),
                                nome_usuario,
                            ],
                            spacing=0,
                        ),
                    ]
                ),
                sino,
            ],
        )

        texto_mes = ft.Text("", size=14, weight=ft.FontWeight.BOLD, color="#0B1410")

        def mudar_mes(delta):
            mes_atual[1] += delta
            if mes_atual[1] > 12:
                mes_atual[1] = 1
                mes_atual[0] += 1
            elif mes_atual[1] < 1:
                mes_atual[1] = 12
                mes_atual[0] -= 1
            atualizar_dados()

        seletor_mes = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, icon_size=18, on_click=lambda e: mudar_mes(-1)),
                texto_mes,
                ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, icon_size=18, on_click=lambda e: mudar_mes(1)),
            ],
        )

        valor_total = ft.Text("R$ 0,00", size=26, weight=ft.FontWeight.BOLD, color="white")
        valor_pago = ft.Text("pago R$ 0,00", size=12, color="#39D67C")
        valor_pendente = ft.Text("pendente R$ 0,00", size=12, color="#E0A030")

        filtro_total = {"valor": "todas"}
        OPCOES_FILTRO_TOTAL = (("todas", "Todas"), ("pendentes", "Pendentes"), ("pagas", "Pagas"))

        def selecionar_filtro_total(valor):
            filtro_total["valor"] = valor
            atualizar_dados()

        def chip_filtro_total(valor, rotulo):
            ativo = filtro_total["valor"] == valor
            return ft.Container(
                content=ft.Text(rotulo, size=10, weight=ft.FontWeight.BOLD,
                                 color="#0B1410" if ativo else "#888780"),
                bgcolor="#39D67C" if ativo else "transparent",
                border=None if ativo else ft.Border.all(1, "#3A413B"),
                border_radius=12,
                padding=ft.Padding(8, 4, 8, 4),
                on_click=lambda e: selecionar_filtro_total(valor),
            )

        linha_filtro_total = ft.Row(spacing=4, controls=[])

        card_total = ft.Container(
            bgcolor="#0B1410",
            border_radius=16,
            padding=16,
            content=ft.Column(
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Total do mês", size=12, color="#888780"),
                            linha_filtro_total,
                        ],
                    ),
                    valor_total,
                    ft.Container(height=8),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(controls=[ft.Icon(ft.Icons.CHECK_CIRCLE, size=14, color="#39D67C"), valor_pago]),
                            ft.Row(controls=[ft.Icon(ft.Icons.SCHEDULE, size=14, color="#E0A030"), valor_pendente]),
                        ],
                    ),
                ],
            ),
        )

        banner_semana = ft.Container(visible=False)

        bloco_atrasadas = ft.Container()

        def construir_bloco_atrasadas(atrasadas):
            # RF25/9: aviso compacto -- nunca a lista expandida de antes (Fase 3.9).
            # "Ver essas contas" abre a tela dedicada (mostrar_tela_atrasadas), que
            # busca TODAS as atrasadas do usuário via database.listar_contas_atrasadas,
            # sem depender do mês selecionado aqui.
            if atrasadas:
                bloco_atrasadas.bgcolor = "#FBE4E4"
                bloco_atrasadas.border_radius = 10
                bloco_atrasadas.padding = 12
                bloco_atrasadas.content = ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.ERROR_OUTLINE, size=18, color="#A32D2D"),
                                ft.Container(width=8),
                                ft.Text("Você possui contas em atraso!", size=13,
                                         weight=ft.FontWeight.BOLD, color="#A32D2D"),
                            ],
                        ),
                        ft.Container(
                            content=ft.Text("Ver essas contas", size=12, weight=ft.FontWeight.BOLD,
                                             color="#A32D2D"),
                            on_click=lambda e: mostrar_tela_atrasadas(),
                        ),
                    ],
                )
            else:
                bloco_atrasadas.bgcolor = "transparent"
                bloco_atrasadas.border_radius = 0
                bloco_atrasadas.padding = ft.Padding(0, 4, 0, 4)
                bloco_atrasadas.content = ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=16, color="#1D9E75"),
                        ft.Container(width=6),
                        ft.Text("Suas contas estão em dia!", size=13,
                                 weight=ft.FontWeight.BOLD, color="#1D9E75"),
                    ],
                )

        def ao_clicar_ver_todas(e):
            ano_mes_atual = f"{mes_atual[0]:04d}-{mes_atual[1]:02d}"
            mostrar_tela_todas_contas(ano_mes_atual)

        cabecalho_contas = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("Suas contas", size=15, weight=ft.FontWeight.BOLD, color="#0B1410"),
                ft.Container(
                    content=ft.Text("Ver todas", size=13, color="#1D9E75"),
                    on_click=ao_clicar_ver_todas,
                ),
            ],
        )

        lista_contas = ft.Column(controls=[], spacing=8)

        def abrir_detalhe_conta(conta):
            page.controls.clear()
            page.overlay.clear()
            page.padding = 0

            categorias_atuais = {c["id"]: c["nome"] for c in database.listar_categorias(usuario_atual["id"])}
            nome_categoria = categorias_atuais.get(conta.get("categoria_id")) or "Sem categoria"

            # Correção D1/D2 (auditoria pós-Fase 3): serie_id sozinho não basta --
            # uma série removida (RF29, ativa=0) continua com serie_id preenchido
            # em suas ocorrências (preserva histórico/RF26), mas elas devem se
            # comportar como conta individual daqui em diante (5.8). Computado uma
            # vez aqui porque nenhuma mutação de recorrência (RF27/28/29) deixa o
            # usuário na mesma tela sem recarregar via mostrar_tela_principal().
            serie_ativa = (
                conta.get("serie_id") is not None
                and database.serie_esta_ativa(conta["serie_id"])
            )

            area_corpo = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, controls=[])

            def construir_seletor_frequencia(estado):
                # RF27/RF28: chips Mensal/Anual reutilizáveis nos diálogos de
                # transformar em recorrente e alterar frequência -- mesmo estilo
                # visual dos chips de tipo da tela Nova conta.
                linha = ft.Row(spacing=8, controls=[])

                def montar():
                    linha.controls.clear()
                    for valor, rotulo in (("mensal", "Mensal"), ("anual", "Anual")):
                        ativo = estado["valor"] == valor
                        linha.controls.append(
                            ft.Container(
                                content=ft.Text(rotulo, size=13, weight=ft.FontWeight.BOLD,
                                                 color="white" if ativo else "#0B1410"),
                                bgcolor="#1D9E75" if ativo else "white",
                                border=None if ativo else ft.Border.all(1, "#E5E4DE"),
                                border_radius=10,
                                padding=ft.Padding(0, 12, 0, 12),
                                alignment=ft.Alignment.CENTER,
                                expand=True,
                                on_click=lambda e, v=valor: selecionar(v),
                            )
                        )

                def selecionar(valor):
                    estado["valor"] = valor
                    montar()
                    page.update()

                montar()
                return linha

            def mostrar_visualizacao():
                page.overlay.clear()

                data_venc = date.fromisoformat(conta["data_vencimento"])
                dias_delta = (data_venc - date.today()).days

                if conta["status"] == "pago":
                    cor_status, rotulo_status = "#1D9E75", "Pago"
                elif conta["status"] == "atrasado":
                    cor_status, rotulo_status = "#A32D2D", "Atrasado"
                elif dias_delta == 0:
                    cor_status, rotulo_status = "#C9820A", "A vencer"
                else:
                    cor_status, rotulo_status = "#888780", "Pendente"

                def alternar_status_pagamento(e):
                    # RF06/RF24: alterna somente esta ocorrência. O escopo de série
                    # (RF20, seção 5.2 do ERS) só se aplica a nome/valor/data — status
                    # não tem variante "este mês em diante".
                    if conta["status"] == "pago":
                        database.marcar_conta_como_pendente(conta["id"])
                        conta["status"] = "atrasado" if dias_delta < 0 else "pendente"
                        conta["data_pagamento"] = None
                    else:
                        database.marcar_conta_como_paga(conta["id"])
                        conta["status"] = "pago"
                        conta["data_pagamento"] = date.today().isoformat()
                    mostrar_visualizacao()

                if conta["status"] == "pago":
                    texto_botao_status, cor_botao_status = "Marcar como pendente", "#E0A030"
                else:
                    texto_botao_status, cor_botao_status = "Marcar como paga", "#39D67C"

                recorrencia = "Sim" if conta.get("serie_id") is not None else "Não"

                pago_em_texto = None
                seletor_data_pagamento = None
                if conta["status"] == "pago":
                    if conta.get("data_pagamento"):
                        pago_em_texto = date.fromisoformat(conta["data_pagamento"]).strftime("%d/%m/%Y")

                    def mostrar_erro_data_pagamento():
                        dialogo_erro = ft.AlertDialog(
                            modal=True,
                            title=ft.Text("Data inválida"),
                            content=ft.Text("A data de pagamento não pode ser no futuro."),
                            actions=[
                                ft.Button(content="Entendi", bgcolor="#1D9E75", color="white",
                                          on_click=lambda e: page.pop_dialog()),
                            ],
                        )
                        page.show_dialog(dialogo_erro)

                    def ao_escolher_data_pagamento(e):
                        if not e.control.value:
                            return
                        nova_data = e.control.value.date()
                        sucesso = database.editar_data_pagamento(conta["id"], nova_data.isoformat())
                        page.pop_dialog()
                        if sucesso:
                            conta["data_pagamento"] = nova_data.isoformat()
                            mostrar_visualizacao()
                        else:
                            mostrar_erro_data_pagamento()

                    seletor_data_pagamento = ft.DatePicker(
                        value=(
                            date.fromisoformat(conta["data_pagamento"])
                            if conta.get("data_pagamento") else date.today()
                        ),
                        first_date=date(2000, 1, 1),
                        last_date=date(2100, 12, 31),
                        on_change=ao_escolher_data_pagamento,
                    )
                    page.overlay.append(seletor_data_pagamento)

                def abrir_seletor_data_pagamento(e):
                    page.show_dialog(seletor_data_pagamento)

                parcela_texto = None
                if conta.get("serie_id") is not None:
                    parcela = database.obter_parcela(conta["serie_id"], conta["id"])
                    if parcela:
                        posicao, total_ocorrencias = parcela
                        parcela_texto = (
                            f"Parcela {posicao} de {total_ocorrencias}"
                            if total_ocorrencias is not None
                            else f"Parcela {posicao}"
                        )

                def linha_detalhe(rotulo, valor, cor_valor="#0B1410"):
                    return ft.Column(
                        controls=[
                            ft.Text(rotulo, size=12, color="#888780"),
                            ft.Text(valor, size=16, weight=ft.FontWeight.BOLD, color=cor_valor),
                        ],
                        spacing=2,
                    )

                linhas_cartao = [
                    linha_detalhe("Nome", conta["nome"]),
                    linha_detalhe("Valor", formatar_moeda(conta["valor"])),
                    linha_detalhe("Vencimento", data_venc.strftime("%d/%m/%Y")),
                    linha_detalhe("Categoria", nome_categoria),
                    linha_detalhe("Status", rotulo_status, cor_valor=cor_status),
                    linha_detalhe("Recorrência", recorrencia),
                ]
                if pago_em_texto:
                    linhas_cartao.append(linha_detalhe("Pago em", pago_em_texto))
                if parcela_texto:
                    linhas_cartao.append(linha_detalhe("Parcela", parcela_texto))

                cartao_detalhes = ft.Container(
                    bgcolor="white",
                    border_radius=12,
                    padding=16,
                    content=ft.Column(spacing=16, controls=linhas_cartao),
                )

                cabecalho = ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=20, icon_color="#0B1410",
                                      on_click=lambda e: mostrar_tela_principal()),
                        ft.Text("Detalhes da conta", size=18, weight=ft.FontWeight.BOLD, color="#0B1410"),
                        ft.Container(width=40),
                    ],
                )

                controles_acao = [
                    cabecalho,
                    ft.Container(height=20),
                    cartao_detalhes,
                    ft.Container(height=16),
                    ft.Button(
                        content=texto_botao_status,
                        bgcolor=cor_botao_status,
                        color="white",
                        on_click=alternar_status_pagamento,
                    ),
                ]
                if conta["status"] == "pago":
                    controles_acao += [
                        ft.Container(height=8),
                        ft.TextButton(
                            content="Alterar data de pagamento",
                            on_click=abrir_seletor_data_pagamento,
                        ),
                    ]

                area_corpo.controls = [
                    ft.Container(
                        padding=ft.Padding(20, 40, 20, 24),
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            controls=controles_acao + [
                                ft.Container(height=8),
                                ft.Button(
                                    content="Editar",
                                    bgcolor="#1D9E75",
                                    color="white",
                                    on_click=lambda e: mostrar_formulario_edicao(),
                                ),
                                ft.Container(height=8),
                                ft.Button(
                                    content="Excluir",
                                    bgcolor="#A32D2D",
                                    color="white",
                                    on_click=lambda e: confirmar_exclusao_conta(),
                                ),
                            ],
                        ),
                    ),
                ]
                page.update()

            def confirmar_exclusao_conta():
                if conta.get("serie_id") is not None and serie_ativa:
                    mostrar_dialogo_exclusao_serie()
                else:
                    mostrar_dialogo_exclusao_simples()

            def mostrar_erro_exclusao():
                dialogo_erro = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Não foi possível excluir"),
                    content=ft.Text(f"Não foi possível excluir '{conta['nome']}'."),
                    actions=[
                        ft.Button(content="Entendi", bgcolor="#1D9E75", color="white",
                                  on_click=lambda e: page.pop_dialog()),
                    ],
                )
                page.show_dialog(dialogo_erro)

            def mostrar_dialogo_exclusao_simples():
                def excluir(e):
                    sucesso = database.excluir_conta(conta["id"])
                    page.pop_dialog()
                    if sucesso:
                        mostrar_tela_principal()
                    else:
                        mostrar_erro_exclusao()

                dialogo = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Excluir conta"),
                    content=ft.Text(f"Deseja realmente excluir a conta '{conta['nome']}'?"),
                    actions=[
                        ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog()),
                        ft.Button(content="Excluir", bgcolor="#A32D2D", color="white", on_click=excluir),
                    ],
                )
                page.show_dialog(dialogo)

            def mostrar_dialogo_exclusao_serie():
                def excluir_somente_este_mes(e):
                    sucesso = database.excluir_conta(conta["id"])
                    page.pop_dialog()
                    if sucesso:
                        mostrar_tela_principal()
                    else:
                        mostrar_erro_exclusao()

                def excluir_este_mes_em_diante(e):
                    sucesso = database.excluir_conta_serie(conta["id"])
                    page.pop_dialog()
                    if sucesso:
                        mostrar_tela_principal()
                    else:
                        mostrar_erro_exclusao()

                acoes = [
                    ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.TextButton(content="Somente este mês", on_click=excluir_somente_este_mes),
                    ft.Button(content="Este mês em diante", bgcolor="#A32D2D", color="white",
                              on_click=excluir_este_mes_em_diante),
                ]

                dialogo = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Como deseja excluir esta conta?"),
                    content=ft.Text(
                        f"'{conta['nome']}' se repete todos os meses. Você pode excluir apenas "
                        "esta ocorrência, ou esta e todas as futuras."
                    ),
                    actions=acoes,
                )
                page.show_dialog(dialogo)

            def mostrar_dialogo_transformar_recorrente():
                # RF28: só para conta única (serie_id None) -- botão que abre este
                # diálogo já é condicionado a isso em mostrar_visualizacao().
                frequencia_transf = {"valor": "mensal"}
                linha_frequencia_transf = construir_seletor_frequencia(frequencia_transf)

                sem_termino_transf = ft.Switch(value=True, active_color="#1D9E75")
                ano_atual_transf = date.today().year
                campo_mes_termino_transf = ft.Dropdown(
                    label="Mês", color="#0B1410", expand=True,
                    value=str(date.today().month),
                    options=[ft.dropdown.Option(key=str(i), text=MESES_PT[i - 1]) for i in range(1, 13)],
                )
                campo_ano_termino_transf = ft.Dropdown(
                    label="Ano", color="#0B1410", expand=True,
                    value=str(ano_atual_transf),
                    options=[ft.dropdown.Option(key=str(a), text=str(a))
                             for a in range(ano_atual_transf, ano_atual_transf + 11)],
                )
                linha_termino_transf = ft.Row(
                    spacing=8, controls=[campo_mes_termino_transf, campo_ano_termino_transf], visible=False,
                )
                erro_transf = ft.Text(value="", color="#A32D2D", size=12)

                def ao_mudar_sem_termino_transf(e):
                    linha_termino_transf.visible = not sem_termino_transf.value
                    page.update()

                sem_termino_transf.on_change = ao_mudar_sem_termino_transf

                def confirmar_transformacao(e):
                    data_termino = None
                    if not sem_termino_transf.value:
                        mes_termino = int(campo_mes_termino_transf.value)
                        ano_termino = int(campo_ano_termino_transf.value)
                        data_venc = date.fromisoformat(conta["data_vencimento"])
                        if (ano_termino, mes_termino) < (data_venc.year, data_venc.month):
                            erro_transf.value = "O término não pode ser anterior à data de vencimento desta conta."
                            page.update()
                            return
                        data_termino = f"{ano_termino:04d}-{mes_termino:02d}"

                    try:
                        novo_serie_id, _ = database.transformar_em_recorrente(
                            conta["id"], frequencia_transf["valor"], data_termino=data_termino,
                        )
                    except ValueError:
                        erro_transf.value = "Não foi possível transformar esta conta em recorrente."
                        page.update()
                        return

                    conta["serie_id"] = novo_serie_id
                    page.pop_dialog()
                    mostrar_tela_principal()

                dialogo = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Transformar em recorrente"),
                    content=ft.Column(
                        tight=True,
                        spacing=12,
                        controls=[
                            ft.Text(
                                "A partir de agora, esta conta passa a se repetir automaticamente. "
                                "Escolha a frequência:"
                            ),
                            linha_frequencia_transf,
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text("Sem data de término", size=13, color="#0B1410"),
                                    sem_termino_transf,
                                ],
                            ),
                            linha_termino_transf,
                            erro_transf,
                        ],
                    ),
                    actions=[
                        ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog()),
                        ft.Button(content="Transformar", bgcolor="#1D9E75", color="white",
                                  on_click=confirmar_transformacao),
                    ],
                )
                page.show_dialog(dialogo)

            def mostrar_dialogo_alterar_frequencia():
                # RF27 (5.5) + D5: só para conta recorrente -- botão condicionado em
                # mostrar_visualizacao(). Não pré-seleciona a frequência atual
                # (database/db.py não expõe um getter para isso); o usuário escolhe
                # explicitamente a nova frequência.
                #
                # D5 (decisão de produto): o término anterior nunca é preservado
                # automaticamente -- o usuário escolhe de novo até quando a série
                # (já na nova frequência) continua, mesmo padrão de "Transformar em
                # recorrente". "Sem data de término" começa DESMARCADO aqui (só
                # nesta tela nova; "Transformar em recorrente" não foi alterado).
                nova_frequencia = {"valor": "mensal"}
                linha_frequencia_alt = construir_seletor_frequencia(nova_frequencia)

                sem_termino_alt = ft.Switch(value=False, active_color="#1D9E75")
                ano_atual_alt = date.today().year
                campo_mes_termino_alt = ft.Dropdown(
                    label="Mês", color="#0B1410", expand=True,
                    value=str(date.today().month),
                    options=[ft.dropdown.Option(key=str(i), text=MESES_PT[i - 1]) for i in range(1, 13)],
                )
                campo_ano_termino_alt = ft.Dropdown(
                    label="Ano", color="#0B1410", expand=True,
                    value=str(ano_atual_alt),
                    options=[ft.dropdown.Option(key=str(a), text=str(a))
                             for a in range(ano_atual_alt, ano_atual_alt + 11)],
                )
                linha_termino_alt = ft.Row(
                    spacing=8, controls=[campo_mes_termino_alt, campo_ano_termino_alt], visible=True,
                )
                erro_freq = ft.Text(value="", color="#A32D2D", size=12)

                def ao_mudar_sem_termino_alt(e):
                    linha_termino_alt.visible = not sem_termino_alt.value
                    page.update()

                sem_termino_alt.on_change = ao_mudar_sem_termino_alt

                def confirmar_alteracao(e):
                    data_termino = None
                    if not sem_termino_alt.value:
                        mes_termino = int(campo_mes_termino_alt.value)
                        ano_termino = int(campo_ano_termino_alt.value)
                        data_venc_atual = date.fromisoformat(conta["data_vencimento"])
                        if (ano_termino, mes_termino) < (data_venc_atual.year, data_venc_atual.month):
                            erro_freq.value = "O término não pode ser anterior à data desta ocorrência."
                            page.update()
                            return
                        data_termino = f"{ano_termino:04d}-{mes_termino:02d}"

                    try:
                        database.alterar_frequencia_serie(
                            conta["id"], nova_frequencia["valor"], data_termino=data_termino,
                        )
                    except ValueError:
                        erro_freq.value = "Não foi possível alterar a frequência desta conta."
                        page.update()
                        return

                    mostrar_confirmacao_alteracao(nova_frequencia["valor"], data_termino)

                def mostrar_confirmacao_alteracao(frequencia_escolhida, termino_escolhido):
                    frequencia_texto = "mensalmente" if frequencia_escolhida == "mensal" else "anualmente"
                    if termino_escolhido:
                        ano_t, mes_t = map(int, termino_escolhido.split("-"))
                        termino_texto = f"até {MESES_PT[mes_t - 1].lower()} de {ano_t}"
                    else:
                        termino_texto = "sem data de término"

                    def fechar_confirmacao(e):
                        page.pop_dialog()
                        mostrar_tela_principal()

                    dialogo.title = ft.Text("Frequência alterada")
                    dialogo.content = ft.Text(
                        f"A partir deste mês, a conta passa a se repetir {frequencia_texto}, "
                        f"{termino_texto}."
                    )
                    dialogo.actions = [
                        ft.Button(content="Entendi", bgcolor="#1D9E75", color="white",
                                  on_click=fechar_confirmacao),
                    ]
                    page.update()

                dialogo = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Alterar frequência"),
                    content=ft.Column(
                        tight=True,
                        spacing=12,
                        controls=[
                            ft.Text(
                                "A partir desta ocorrência, a conta passa a se repetir com a "
                                "nova frequência escolhida."
                            ),
                            linha_frequencia_alt,
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text("Sem data de término", size=13, color="#0B1410"),
                                    sem_termino_alt,
                                ],
                            ),
                            linha_termino_alt,
                            erro_freq,
                        ],
                    ),
                    actions=[
                        ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog()),
                        ft.Button(content="Confirmar", bgcolor="#1D9E75", color="white",
                                  on_click=confirmar_alteracao),
                    ],
                )
                page.show_dialog(dialogo)

            def mostrar_dialogo_remover_recorrencia():
                # RF29: não exclui nenhuma ocorrência -- só impede que a série gere
                # novas contas no futuro (database.remover_recorrencia).
                erro_remocao = ft.Text(value="", color="#A32D2D", size=12)

                def confirmar_remocao(e):
                    try:
                        database.remover_recorrencia(conta["serie_id"])
                    except ValueError:
                        erro_remocao.value = "Não foi possível remover a recorrência desta conta."
                        page.update()
                        return
                    page.pop_dialog()
                    mostrar_tela_principal()

                dialogo = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Remover recorrência"),
                    content=ft.Column(
                        tight=True,
                        spacing=12,
                        controls=[
                            ft.Text(
                                "Esta conta deixa de se repetir automaticamente a partir de agora. "
                                "As ocorrências já existentes, passadas e futuras, não são apagadas."
                            ),
                            erro_remocao,
                        ],
                    ),
                    actions=[
                        ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog()),
                        ft.Button(content="Remover recorrência", bgcolor="#A32D2D", color="white",
                                  on_click=confirmar_remocao),
                    ],
                )
                page.show_dialog(dialogo)

            def mostrar_formulario_edicao():
                # Evita empilhar um DatePicker novo no overlay a cada vez que o
                # formulário é reaberto (visualização -> Editar -> voltar -> Editar...).
                page.overlay.clear()

                data_venc_atual = date.fromisoformat(conta["data_vencimento"])
                data_selecionada = {"valor": data_venc_atual}

                campo_nome_edit = ft.TextField(
                    label="Nome da conta", value=conta["nome"], color="#0B1410",
                )
                campo_valor_edit = ft.TextField(
                    label="Valor",
                    value=f"{conta['valor']:.2f}".replace(".", ","),
                    keyboard_type=ft.KeyboardType.NUMBER,
                    color="#0B1410",
                )
                campo_data_edit = ft.TextField(
                    label="Data de vencimento",
                    value=data_venc_atual.strftime("%d/%m/%Y"),
                    read_only=True, expand=True, color="#0B1410",
                )
                campo_categoria_edit = ft.TextField(
                    label="Categoria", value=nome_categoria,
                    read_only=True, disabled=True, color="#0B1410",
                )

                def ao_escolher_data(e):
                    if e.control.value:
                        data_selecionada["valor"] = e.control.value.date()
                        campo_data_edit.value = data_selecionada["valor"].strftime("%d/%m/%Y")
                        page.update()

                seletor_data = ft.DatePicker(
                    first_date=date(2000, 1, 1),
                    last_date=date(2100, 12, 31),
                    on_change=ao_escolher_data,
                )
                page.overlay.append(seletor_data)

                def abrir_seletor_data(e):
                    page.show_dialog(seletor_data)

                erro_edit = ft.Text(value="", color="#A32D2D", size=12)

                def salvar_edicao(e):
                    nome = campo_nome_edit.value.strip() if campo_nome_edit.value else ""
                    valor = parse_valor(campo_valor_edit.value)

                    if not nome:
                        erro_edit.value = "Digite um nome para a conta."
                    elif valor is None:
                        erro_edit.value = "Informe um valor válido."
                    elif data_selecionada["valor"] is None:
                        erro_edit.value = "Escolha a data de vencimento."
                    else:
                        erro_edit.value = ""

                    if erro_edit.value:
                        page.update()
                        return

                    nova_data = data_selecionada["valor"]

                    if conta.get("serie_id") is not None and serie_ativa:
                        # RF20 (5.6): ocorrência de uma série ainda ativa -- pergunta o
                        # escopo antes de aplicar. Sem restrição de mês/ano (removida na
                        # Fase 2.6); a nova data pode cair em qualquer mês/ano. Série já
                        # removida (RF29) cai direto no ramo de baixo, como conta avulsa.
                        mostrar_dialogo_escopo_edicao(nome, valor, nova_data)
                    else:
                        database.editar_conta_ocorrencia(
                            conta["id"], nome=nome, valor=valor,
                            data_vencimento=nova_data.isoformat(),
                        )
                        mostrar_tela_principal()

                def mostrar_dialogo_escopo_edicao(nome, valor, nova_data):
                    def aplicar_somente_esta(e):
                        sucesso = database.editar_conta_ocorrencia(
                            conta["id"], nome=nome, valor=valor,
                            data_vencimento=nova_data.isoformat(),
                        )
                        page.pop_dialog()
                        if sucesso:
                            mostrar_tela_principal()
                        else:
                            erro_edit.value = "Não foi possível salvar esta alteração."
                            page.update()

                    def aplicar_este_mes_em_diante(e):
                        sucesso = database.editar_conta_serie(
                            conta["id"], nome=nome, valor=valor,
                            data_vencimento=nova_data.isoformat(),
                        )
                        page.pop_dialog()
                        if sucesso:
                            mostrar_tela_principal()
                        else:
                            erro_edit.value = (
                                "Não foi possível salvar: a nova data ultrapassaria o "
                                "término definido para esta recorrência."
                            )
                            page.update()

                    dialogo = ft.AlertDialog(
                        modal=True,
                        title=ft.Text("Como deseja aplicar esta alteração?"),
                        content=ft.Text(
                            "Esta conta faz parte de uma recorrência. Você pode alterar "
                            "apenas esta ocorrência ou também as próximas da mesma recorrência."
                        ),
                        actions=[
                            ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog()),
                            ft.Button(content="Somente este mês", bgcolor="#1D9E75", color="white",
                                      on_click=aplicar_somente_esta),
                            ft.TextButton(content="Este mês em diante", on_click=aplicar_este_mes_em_diante),
                        ],
                    )
                    page.show_dialog(dialogo)

                cabecalho_edicao = ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=20, icon_color="#0B1410",
                                      on_click=lambda e: mostrar_visualizacao()),
                        ft.Text("Editar conta", size=18, weight=ft.FontWeight.BOLD, color="#0B1410"),
                        ft.Container(width=40),
                    ],
                )

                # UX (movida da tela de detalhes para dentro de Editar): RF27/RF29
                # continuam chamando exatamente os mesmos diálogos já existentes
                # (mostrar_dialogo_alterar_frequencia/mostrar_dialogo_remover_recorrencia),
                # sem nenhuma lógica nova. Mesmas três condições de sempre --
                # conta.get("serie_id") e serie_ativa (D1/D2, calculado uma vez no
                # topo de abrir_detalhe_conta): avulsa -> RF28; recorrência ativa ->
                # RF27/RF29; recorrência inativa -> nenhuma ação de recorrência.
                if conta.get("serie_id") is None:
                    controles_recorrencia_edicao = [
                        ft.Container(height=8),
                        ft.TextButton(
                            content="Transformar em recorrente",
                            on_click=lambda e: mostrar_dialogo_transformar_recorrente(),
                        ),
                    ]
                elif serie_ativa:
                    controles_recorrencia_edicao = [
                        ft.Container(height=8),
                        ft.TextButton(
                            content="Alterar frequência",
                            on_click=lambda e: mostrar_dialogo_alterar_frequencia(),
                        ),
                        ft.Container(height=8),
                        ft.TextButton(
                            content="Remover recorrência",
                            on_click=lambda e: mostrar_dialogo_remover_recorrencia(),
                        ),
                    ]
                else:
                    controles_recorrencia_edicao = []

                area_corpo.controls = [
                    ft.Container(
                        padding=ft.Padding(20, 40, 20, 24),
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            controls=[
                                cabecalho_edicao,
                                ft.Container(height=20),
                                campo_nome_edit,
                                campo_valor_edit,
                                ft.Row(controls=[
                                    campo_data_edit,
                                    ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, icon_color="#1D9E75",
                                                  on_click=abrir_seletor_data),
                                ]),
                                campo_categoria_edit,
                                ft.Container(height=8),
                                erro_edit,
                                ft.Button(
                                    content="Salvar alterações",
                                    bgcolor="#1D9E75",
                                    color="white",
                                    on_click=salvar_edicao,
                                ),
                            ] + controles_recorrencia_edicao,
                        ),
                    ),
                ]
                page.update()

            page.add(area_corpo)
            mostrar_visualizacao()

        def linha_conta(conta, nome_categoria):
            data_venc = date.fromisoformat(conta["data_vencimento"])
            dias_delta = (data_venc - date.today()).days

            if conta["status"] == "pago":
                cor, rotulo_status = "#1D9E75", "Pago"
                frase = None
            elif conta["status"] == "atrasado":
                cor, rotulo_status = "#A32D2D", "Atrasado"
                frase = frase_vencimento_passado(abs(dias_delta))
            elif dias_delta == 0:
                cor, rotulo_status = "#C9820A", "A vencer"
                frase = frase_vencimento_futuro(dias_delta)
            else:
                cor, rotulo_status = "#888780", "Pendente"
                frase = frase_vencimento_futuro(dias_delta)

            partes_subtitulo = [p for p in (nome_categoria, frase) if p]
            if conta.get("serie_id") is not None:
                parcela = database.obter_parcela(conta["serie_id"], conta["id"])
                if parcela:
                    posicao, total_ocorrencias = parcela
                    texto_parcela = (
                        f"Parcela {posicao} de {total_ocorrencias}"
                        if total_ocorrencias is not None
                        else f"Parcela {posicao}"
                    )
                    partes_subtitulo.append(texto_parcela)
            subtitulo = " · ".join(partes_subtitulo)

            return ft.Container(
                bgcolor="white",
                border_radius=10,
                padding=12,
                border=ft.Border(left=ft.BorderSide(4, cor)),
                on_click=lambda e, c=conta: abrir_detalhe_conta(c),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(conta["nome"], size=14, weight=ft.FontWeight.BOLD, color="#0B1410"),
                                ft.Text(subtitulo, size=12, color="#888780"),
                            ],
                            spacing=2,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(formatar_moeda(conta["valor"]), size=14, weight=ft.FontWeight.BOLD,
                                         color="#0B1410"),
                                ft.Text(rotulo_status, size=12, color=cor),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            spacing=2,
                        ),
                    ],
                ),
            )

        def garantir_ocorrencias_geradas(ano_mes):
            # RF10/5.20 (Fase 3.10): geração sob demanda ao navegar para um mês
            # ainda não gerado. database.gerar_ocorrencias_sob_demanda já decide
            # sozinha se há algo a fazer (série inativa, com término, ou já
            # coberta -- não faz nada nesses casos) e é idempotente; aqui só
            # descobrimos quais séries o usuário tem (via qualquer ocorrência já
            # existente, de qualquer mês) e pedimos ao banco que cubra até o mês
            # navegado. Nenhuma regra de calendário/geração é duplicada aqui --
            # inclusive chamar com um mês passado é inofensivo (a função não gera
            # nada nesse caso).
            series_do_usuario = {
                c["serie_id"] for c in database.listar_contas(usuario_atual["id"])
                if c["serie_id"] is not None
            }
            for serie_id in series_do_usuario:
                database.gerar_ocorrencias_sob_demanda(serie_id, ano_mes)

        def atualizar_dados():
            texto_mes.value = f"{MESES_PT[mes_atual[1] - 1]} {mes_atual[0]}"
            ano_mes = f"{mes_atual[0]:04d}-{mes_atual[1]:02d}"

            garantir_ocorrencias_geradas(ano_mes)

            contas_mes = database.listar_contas(usuario_atual["id"], ano_mes)
            categorias = {c["id"]: c["nome"] for c in database.listar_categorias(usuario_atual["id"])}

            pago = sum(c["valor"] for c in contas_mes if c["status"] == "pago")
            pendente = sum(c["valor"] for c in contas_mes if c["status"] in ("pendente", "atrasado"))

            if filtro_total["valor"] == "pendentes":
                total_exibido = pendente
            elif filtro_total["valor"] == "pagas":
                total_exibido = pago
            else:
                total_exibido = pago + pendente

            valor_total.value = formatar_moeda(total_exibido)
            valor_pago.value = f"pago {formatar_moeda(pago)}"
            valor_pendente.value = f"pendente {formatar_moeda(pendente)}"

            linha_filtro_total.controls.clear()
            for valor, rotulo in OPCOES_FILTRO_TOTAL:
                linha_filtro_total.controls.append(chip_filtro_total(valor, rotulo))

            proximas = database.listar_contas_proximas(usuario_atual["id"], dias=7)
            if proximas:
                total_proximas = sum(c["valor"] for c in proximas)
                banner_semana.bgcolor = "#FDF1D6"
                banner_semana.border_radius = 10
                banner_semana.padding = 12
                banner_semana.content = ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.WARNING_AMBER, size=18, color="#B8860B"),
                        ft.Container(width=8),
                        ft.Column(
                            controls=[
                                ft.Text(frase_resumo_proximas(len(proximas)), size=13,
                                         weight=ft.FontWeight.BOLD, color="#7A5B00"),
                                ft.Text(f"Total de {formatar_moeda(total_proximas)}", size=12, color="#7A5B00"),
                            ],
                            spacing=0,
                        ),
                    ],
                )
                banner_semana.visible = True
            else:
                banner_semana.visible = False

            construir_bloco_atrasadas(database.listar_contas_atrasadas(usuario_atual["id"]))

            contas_ordenadas = sorted(
                contas_mes,
                key=lambda c: (0 if c["status"] == "atrasado" else 1, c["data_vencimento"]),
            )[:5]

            lista_contas.controls.clear()
            if not contas_ordenadas:
                lista_contas.controls.append(
                    ft.Container(
                        content=ft.Text("Nenhuma conta cadastrada ainda.", color="#888780", size=13),
                        padding=16,
                    )
                )
            else:
                for c in contas_ordenadas:
                    lista_contas.controls.append(linha_conta(c, categorias.get(c["categoria_id"], "")))

            page.update()

        def mostrar_tela_todas_contas(ano_mes):
            # RF05: mesma consulta e mesma ordenação de atualizar_dados(), só sem o
            # corte [:5]. Reaproveita linha_conta()/abrir_detalhe_conta() por estar
            # aninhada no mesmo escopo de mostrar_tela_principal().
            # RF09: filtro de status, com estado local a esta chamada (recriado a
            # cada abertura da tela, portanto nunca persistido) e independente do
            # filtro_total do RF12.
            page.controls.clear()
            page.padding = 0

            ano, mes = (int(p) for p in ano_mes.split("-"))
            categorias_atuais = {c["id"]: c["nome"] for c in database.listar_categorias(usuario_atual["id"])}

            contas_do_mes = database.listar_contas(usuario_atual["id"], ano_mes)
            contas_do_mes_ordenadas = sorted(
                contas_do_mes,
                key=lambda c: (0 if c["status"] == "atrasado" else 1, c["data_vencimento"]),
            )

            filtro_ver_todas = {"status": "todas"}
            OPCOES_FILTRO_STATUS_VER_TODAS = (
                ("todas", "Todas"), ("pendentes", "Pendentes"),
                ("pagas", "Pagas"), ("atrasadas", "Atrasadas"),
            )

            def contas_filtradas():
                status_sel = filtro_ver_todas["status"]
                resultado = contas_do_mes_ordenadas
                if status_sel == "pendentes":
                    resultado = [c for c in resultado if c["status"] == "pendente"]
                elif status_sel == "pagas":
                    resultado = [c for c in resultado if c["status"] == "pago"]
                elif status_sel == "atrasadas":
                    resultado = [c for c in resultado if c["status"] == "atrasado"]

                return resultado

            lista_completa = ft.ListView(expand=True, spacing=8, padding=ft.Padding(20, 0, 20, 24))

            def recompor_lista_completa():
                lista_completa.controls.clear()
                if not contas_do_mes_ordenadas:
                    lista_completa.controls.append(
                        ft.Container(
                            content=ft.Text("Nenhuma conta cadastrada neste mês.", color="#888780", size=13),
                            padding=16,
                        )
                    )
                    return

                filtradas = contas_filtradas()
                if not filtradas:
                    lista_completa.controls.append(
                        ft.Container(
                            content=ft.Text("Nenhuma conta encontrada com os filtros selecionados.",
                                             color="#888780", size=13),
                            padding=16,
                        )
                    )
                else:
                    for c in filtradas:
                        lista_completa.controls.append(
                            linha_conta(c, categorias_atuais.get(c["categoria_id"], ""))
                        )

            def atualizar_lista_ver_todas():
                recompor_lista_completa()
                page.update()

            linha_filtro_status_ver_todas = ft.Row(spacing=4, controls=[])

            def montar_chips_status_ver_todas():
                linha_filtro_status_ver_todas.controls.clear()
                for valor, rotulo in OPCOES_FILTRO_STATUS_VER_TODAS:
                    linha_filtro_status_ver_todas.controls.append(
                        chip_filtro_status_ver_todas(valor, rotulo)
                    )

            def selecionar_filtro_status_ver_todas(valor):
                filtro_ver_todas["status"] = valor
                montar_chips_status_ver_todas()
                atualizar_lista_ver_todas()

            def chip_filtro_status_ver_todas(valor, rotulo):
                ativo = filtro_ver_todas["status"] == valor
                return ft.Container(
                    content=ft.Text(rotulo, size=10, weight=ft.FontWeight.BOLD,
                                     color="#0B1410" if ativo else "#888780"),
                    bgcolor="#39D67C" if ativo else "transparent",
                    border=None if ativo else ft.Border.all(1, "#3A413B"),
                    border_radius=12,
                    padding=ft.Padding(8, 4, 8, 4),
                    on_click=lambda e, v=valor: selecionar_filtro_status_ver_todas(v),
                )

            montar_chips_status_ver_todas()
            recompor_lista_completa()

            cabecalho_todas_contas = ft.Container(
                padding=ft.Padding(20, 40, 20, 0),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=20, icon_color="#0B1410",
                                      on_click=lambda e: mostrar_tela_principal()),
                        ft.Text(f"{MESES_PT[mes - 1]} {ano}", size=18, weight=ft.FontWeight.BOLD,
                                color="#0B1410"),
                        ft.Container(width=40),
                    ],
                ),
            )

            filtros_ver_todas = ft.Container(
                padding=ft.Padding(20, 12, 20, 4),
                content=ft.Column(
                    spacing=8,
                    controls=[linha_filtro_status_ver_todas],
                ),
            )

            page.add(
                ft.Column(
                    expand=True,
                    controls=[cabecalho_todas_contas, filtros_ver_todas, lista_completa],
                )
            )
            page.update()

        def mostrar_tela_atrasadas():
            # RF25 (Fase 3.9): tela dedicada, sempre com TODAS as contas atrasadas
            # do usuário -- database.listar_contas_atrasadas já ignora o mês
            # selecionado na Tela Principal, então esta tela não filtra por
            # mes_atual. Reaproveita linha_conta()/abrir_detalhe_conta() por estar
            # aninhada no mesmo escopo de mostrar_tela_principal() (mesmo padrão de
            # mostrar_tela_todas_contas).
            page.controls.clear()
            page.padding = 0

            categorias_atuais = {c["id"]: c["nome"] for c in database.listar_categorias(usuario_atual["id"])}
            atrasadas_todas = database.listar_contas_atrasadas(usuario_atual["id"])

            lista_atrasadas_tela = ft.ListView(expand=True, spacing=8, padding=ft.Padding(20, 0, 20, 24))
            if not atrasadas_todas:
                lista_atrasadas_tela.controls.append(
                    ft.Container(
                        content=ft.Text("Nenhuma conta atrasada.", color="#888780", size=13),
                        padding=16,
                    )
                )
            else:
                for c in atrasadas_todas:
                    lista_atrasadas_tela.controls.append(
                        linha_conta(c, categorias_atuais.get(c["categoria_id"], ""))
                    )

            cabecalho_atrasadas_tela = ft.Container(
                padding=ft.Padding(20, 40, 20, 0),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=20, icon_color="#0B1410",
                                      on_click=lambda e: mostrar_tela_principal()),
                        ft.Text("Contas em atraso", size=18, weight=ft.FontWeight.BOLD, color="#0B1410"),
                        ft.Container(width=40),
                    ],
                ),
            )

            page.add(
                ft.Column(
                    expand=True,
                    controls=[cabecalho_atrasadas_tela, ft.Container(height=8), lista_atrasadas_tela],
                )
            )
            page.update()

        fab = ft.Container(
            content=ft.Icon(ft.Icons.ADD, color="white", size=26),
            bgcolor="#1D9E75",
            width=52,
            height=52,
            border_radius=26,
            alignment=ft.Alignment.CENTER,
            right=20,
            bottom=16,
            on_click=lambda e: mostrar_tela_nova_conta(),
        )

        conteudo = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            controls=[
                ft.Container(
                    padding=ft.Padding(20, 40, 20, 16),
                    content=ft.Column(
                        controls=[
                            cabecalho_topo,
                            ft.Container(height=16),
                            seletor_mes,
                            ft.Container(height=12),
                            card_total,
                            ft.Container(height=12),
                            banner_semana,
                            ft.Container(height=12),
                            bloco_atrasadas,
                            ft.Container(height=16),
                            cabecalho_contas,
                            ft.Container(height=8),
                            lista_contas,
                            ft.Container(height=80),
                        ],
                    ),
                ),
            ],
        )

        corpo = ft.Stack(
            expand=True,
            controls=[
                conteudo,
                fab,
            ],
        )

        page.add(
            ft.Column(
                expand=True,
                controls=[corpo, barra_navegacao("inicio")],
            )
        )

        atualizar_dados()

    # ======================================================
    #  TELA DE CATEGORIAS (CRUD)
    # ======================================================
    def mostrar_tela_categorias():
        page.controls.clear()
        page.padding = 0

        lista = ft.ListView(expand=True, spacing=8, padding=16)

        def atualizar_lista():
            lista.controls.clear()
            categorias = database.listar_categorias(usuario_atual["id"])

            if not categorias:
                lista.controls.append(
                    ft.Container(
                        content=ft.Text("Nenhuma categoria ainda. Toque em '+' para criar.",
                                         color="#888780", size=13),
                        padding=16,
                    )
                )
            else:
                for cat in categorias:
                    lista.controls.append(linha_categoria(cat))
            page.update()

        def linha_categoria(cat):
            return ft.Container(
                bgcolor="white",
                border_radius=12,
                padding=12,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Text(cat["icone"] or cat["nome"][0].upper(),
                                                     size=16, color="white"),
                                    bgcolor=cat["cor"] or "#1D9E75",
                                    width=36,
                                    height=36,
                                    border_radius=18,
                                    alignment=ft.Alignment.CENTER,
                                ),
                                ft.Container(width=10),
                                ft.Text(cat["nome"], size=15),
                            ]
                        ),
                        ft.Row(
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.ADD, icon_size=18, icon_color="#1D9E75",
                                    tooltip="Nova conta nesta categoria",
                                    on_click=lambda e, c=cat: mostrar_tela_nova_conta(
                                        categoria_pre_selecionada=c["id"]),
                                ),
                                ft.IconButton(icon=ft.Icons.EDIT, icon_size=18,
                                              on_click=lambda e, c=cat: abrir_dialogo_categoria(c)),
                                ft.IconButton(icon=ft.Icons.DELETE, icon_size=18, icon_color="#A32D2D",
                                              on_click=lambda e, c=cat: confirmar_exclusao(c)),
                            ]
                        ),
                    ],
                ),
            )

        def abrir_dialogo_categoria(cat=None):
            campo_nome = ft.TextField(label="Nome da categoria", value=cat["nome"] if cat else "", width=280)
            campo_icone = ft.TextField(label="Ícone (emoji, opcional)",
                                        value=cat["icone"] if cat else "", width=280)
            erro = ft.Text(value="", color="#A32D2D", size=12)

            # RF18/5.12 (Fase D4): sugestões de emoji contextuais ao nome digitado.
            # emoji_sugerido_selecionado rastreia qual sugestão foi clicada (mesmo
            # papel de cor_selecionada para a paleta de cores, abaixo) -- não é a
            # mesma coisa que "o texto atual de campo_icone", porque o campo livre
            # continua editável e não deve ser observado/sobrescrito por digitação.
            emoji_sugerido_selecionado = {"valor": cat["icone"] if cat and cat.get("icone") else None}
            linha_sugestoes_emoji = ft.Row(spacing=8, run_spacing=8, wrap=True, width=280)
            bloco_sugestoes_emoji = ft.Column(
                spacing=6,
                visible=False,
                controls=[
                    ft.Text("Sugestões", size=12, color="#888780"),
                    linha_sugestoes_emoji,
                ],
            )

            def montar_sugestoes_emoji():
                sugestoes = sugestoes_emoji_para(campo_nome.value)
                bloco_sugestoes_emoji.visible = bool(sugestoes)
                linha_sugestoes_emoji.controls.clear()
                for emoji in sugestoes:
                    selecionado = emoji_sugerido_selecionado["valor"] == emoji
                    linha_sugestoes_emoji.controls.append(
                        ft.Container(
                            content=ft.Text(emoji, size=16),
                            width=36,
                            height=36,
                            border_radius=18,
                            bgcolor="#F5F4F0",
                            alignment=ft.Alignment.CENTER,
                            border=ft.Border.all(2, "#1D9E75") if selecionado else None,
                            on_click=lambda e, em=emoji: selecionar_emoji_sugerido(em),
                        )
                    )

            def selecionar_emoji_sugerido(emoji):
                # Ação explícita do usuário -- só aqui o campo de ícone é
                # preenchido. Trocar o nome (ao_mudar_nome) nunca faz isso.
                campo_icone.value = emoji
                emoji_sugerido_selecionado["valor"] = emoji
                montar_sugestoes_emoji()
                page.update()

            def ao_mudar_nome(e):
                montar_sugestoes_emoji()
                page.update()

            campo_nome.on_change = ao_mudar_nome
            montar_sugestoes_emoji()

            # RF18/5.13 (Fase 3.11): paleta já existente em database.py -- nenhuma
            # cor nova é inventada aqui. Cores já usadas por OUTRA categoria deste
            # usuário ficam desabilitadas na própria paleta, só para não oferecer
            # uma opção que database.criar_categoria/editar_categoria já rejeitaria
            # (a regra de unicidade continua vivendo inteiramente no db.py).
            categorias_do_usuario = database.listar_categorias(usuario_atual["id"])
            cores_em_uso = {
                c["cor"] for c in categorias_do_usuario
                if c["cor"] and (cat is None or c["id"] != cat["id"])
            }
            cor_selecionada = {"valor": cat["cor"] if cat and cat.get("cor") else None}

            linha_cores = ft.Row(spacing=8, run_spacing=8, wrap=True, width=280)

            def montar_paleta():
                linha_cores.controls.clear()
                for cor in database.PALETA_CORES_CATEGORIAS:
                    em_uso = cor in cores_em_uso
                    selecionada = cor_selecionada["valor"] == cor
                    linha_cores.controls.append(
                        ft.Container(
                            width=28,
                            height=28,
                            border_radius=14,
                            bgcolor=cor,
                            opacity=0.25 if em_uso else 1.0,
                            border=ft.Border.all(2, "#0B1410") if selecionada else None,
                            tooltip="Já em uso por outra categoria sua" if em_uso else None,
                            on_click=None if em_uso else (lambda e, c=cor: selecionar_cor(c)),
                        )
                    )

            def selecionar_cor(cor):
                cor_selecionada["valor"] = cor
                montar_paleta()
                page.update()

            montar_paleta()

            def salvar(e):
                nome = campo_nome.value.strip() if campo_nome.value else ""
                if not nome:
                    erro.value = "Digite um nome para a categoria."
                    page.update()
                    return
                icone = campo_icone.value.strip() if campo_icone.value else None
                cor = cor_selecionada["valor"]

                try:
                    if cat:
                        database.editar_categoria(usuario_atual["id"], cat["id"], nome=nome, icone=icone, cor=cor)
                    else:
                        database.criar_categoria(usuario_atual["id"], nome, icone, cor)
                except ValueError as erro_valor:
                    if "cor" in str(erro_valor):
                        erro.value = "Essa cor já está em uso por outra categoria sua. Escolha outra."
                    else:
                        erro.value = "Limite de 30 categorias atingido. Exclua uma categoria existente para criar uma nova."
                    page.update()
                    return

                page.pop_dialog()
                atualizar_lista()

            dialogo = ft.AlertDialog(
                modal=True,
                title=ft.Text("Editar categoria" if cat else "Nova categoria"),
                content=ft.Column(
                    controls=[
                        campo_nome,
                        campo_icone,
                        bloco_sugestoes_emoji,
                        ft.Text("Cor", size=12, color="#888780"),
                        linha_cores,
                        erro,
                    ],
                    tight=True,
                    spacing=10,
                ),
                actions=[
                    ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.Button(content="Salvar", bgcolor="#1D9E75", color="white", on_click=salvar),
                ],
            )
            page.show_dialog(dialogo)

        def confirmar_exclusao(cat):
            def excluir(e):
                database.excluir_categoria(usuario_atual["id"], cat["id"])
                page.pop_dialog()
                atualizar_lista()

            dialogo = ft.AlertDialog(
                modal=True,
                title=ft.Text("Excluir categoria"),
                content=ft.Text(
                    f"Excluir '{cat['nome']}'? As contas associadas não serão excluídas, "
                    "apenas ficarão sem categoria."
                ),
                actions=[
                    ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.Button(content="Excluir", bgcolor="#A32D2D", color="white", on_click=excluir),
                ],
            )
            page.show_dialog(dialogo)

        cabecalho = ft.Container(
            bgcolor="#0B1410",
            padding=ft.Padding(20, 40, 20, 20),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Categorias", size=20, weight=ft.FontWeight.BOLD, color="white"),
                    ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color="#39D67C", icon_size=28,
                                  on_click=lambda e: abrir_dialogo_categoria(None)),
                ],
            ),
        )

        page.add(
            ft.Column(
                expand=True,
                controls=[cabecalho, lista, barra_navegacao("categorias")],
            )
        )
        atualizar_lista()

    # ======================================================
    #  TELA DE NOVA CONTA
    # ======================================================
    def mostrar_tela_nova_conta(categoria_pre_selecionada=None):
        page.controls.clear()
        page.overlay.clear()
        page.padding = 0

        data_selecionada = {"valor": None}

        campo_nome = ft.TextField(
            label="Nome da conta", hint_text="Ex: Aluguel, Internet...", color="#0B1410",
        )
        campo_valor = ft.TextField(
            label="Valor", hint_text="R$ 0,00", keyboard_type=ft.KeyboardType.NUMBER, color="#0B1410",
        )
        campo_data = ft.TextField(
            label="Data de vencimento", hint_text="dd/mm/aaaa", read_only=True, expand=True, color="#0B1410",
        )

        def ao_escolher_data(e):
            if e.control.value:
                data_selecionada["valor"] = e.control.value.date()
                campo_data.value = data_selecionada["valor"].strftime("%d/%m/%Y")
                page.update()

        seletor_data = ft.DatePicker(
            first_date=date(2000, 1, 1),
            last_date=date(2100, 12, 31),
            on_change=ao_escolher_data,
        )
        page.overlay.append(seletor_data)

        def abrir_seletor_data(e):
            page.show_dialog(seletor_data)

        categorias = database.listar_categorias(usuario_atual["id"])

        def ponto_cor_categoria(cor):
            return ft.Container(width=10, height=10, border_radius=5, bgcolor=cor or "#E5E4DE")

        opcoes_categoria = [ft.dropdown.Option(key="", text="Sem categoria")] + [
            ft.dropdown.Option(
                key=str(c["id"]),
                text=f"{c['icone'] + ' ' if c['icone'] else ''}{c['nome']}",
                leading_icon=ponto_cor_categoria(c["cor"]),
            )
            for c in categorias
        ]
        campo_categoria = ft.Dropdown(
            label="Categoria",
            value=str(categoria_pre_selecionada) if categoria_pre_selecionada else "",
            options=opcoes_categoria, color="#0B1410",
        )

        # RF10: tipo de conta -- Única (avulsa), Mensal ou Anual (recorrentes).
        tipo_selecionado = {"valor": "unica"}

        # RF10/5.18: término opcional -- "Sem data de término" por padrão; quando
        # desativado, mostra o seletor visual de mês/ano (não mais campo de texto).
        sem_termino = ft.Switch(value=True, active_color="#1D9E75")

        ano_atual = date.today().year
        campo_mes_termino = ft.Dropdown(
            label="Mês", color="#0B1410", expand=True,
            value=str(date.today().month),
            options=[ft.dropdown.Option(key=str(i), text=MESES_PT[i - 1]) for i in range(1, 13)],
        )
        campo_ano_termino = ft.Dropdown(
            label="Ano", color="#0B1410", expand=True,
            value=str(ano_atual),
            options=[ft.dropdown.Option(key=str(a), text=str(a)) for a in range(ano_atual, ano_atual + 11)],
        )
        linha_termino = ft.Row(spacing=8, controls=[campo_mes_termino, campo_ano_termino], visible=False)

        cartao_termino = ft.Container(
            bgcolor="white",
            border_radius=12,
            padding=14,
            visible=False,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Sem data de término", size=14, weight=ft.FontWeight.BOLD, color="#0B1410"),
                            sem_termino,
                        ],
                    ),
                    linha_termino,
                ],
            ),
        )

        def atualizar_secao_termino():
            eh_recorrente = tipo_selecionado["valor"] != "unica"
            cartao_termino.visible = eh_recorrente
            linha_termino.visible = eh_recorrente and not sem_termino.value
            page.update()

        sem_termino.on_change = lambda e: atualizar_secao_termino()

        linha_tipo = ft.Row(spacing=8, controls=[])

        def chip_tipo(valor, rotulo):
            ativo = tipo_selecionado["valor"] == valor
            return ft.Container(
                content=ft.Text(rotulo, size=13, weight=ft.FontWeight.BOLD,
                                 color="white" if ativo else "#0B1410"),
                bgcolor="#1D9E75" if ativo else "white",
                border=None if ativo else ft.Border.all(1, "#E5E4DE"),
                border_radius=10,
                padding=ft.Padding(0, 12, 0, 12),
                alignment=ft.Alignment.CENTER,
                expand=True,
                on_click=lambda e, v=valor: selecionar_tipo(v),
            )

        def montar_chips_tipo():
            linha_tipo.controls.clear()
            for valor, rotulo in (("unica", "Única"), ("mensal", "Mensal"), ("anual", "Anual")):
                linha_tipo.controls.append(chip_tipo(valor, rotulo))

        def selecionar_tipo(valor):
            tipo_selecionado["valor"] = valor
            montar_chips_tipo()
            atualizar_secao_termino()

        montar_chips_tipo()

        erro = ft.Text(value="", color="#A32D2D", size=12)

        def salvar(e):
            nome = campo_nome.value.strip() if campo_nome.value else ""
            valor = parse_valor(campo_valor.value)
            categoria_id = int(campo_categoria.value) if campo_categoria.value else None
            tipo = tipo_selecionado["valor"]
            data_termino = None

            if not nome:
                erro.value = "Digite um nome para a conta."
            elif valor is None:
                erro.value = "Informe um valor válido."
            elif data_selecionada["valor"] is None:
                erro.value = "Escolha a data de vencimento."
            elif tipo != "unica" and not sem_termino.value:
                mes_termino = int(campo_mes_termino.value)
                ano_termino = int(campo_ano_termino.value)
                data_venc = data_selecionada["valor"]
                if (ano_termino, mes_termino) < (data_venc.year, data_venc.month):
                    erro.value = "O término não pode ser anterior à data de vencimento inicial."
                else:
                    data_termino = f"{ano_termino:04d}-{mes_termino:02d}"
                    erro.value = ""
            else:
                erro.value = ""

            if erro.value:
                page.update()
                return

            if tipo == "unica":
                database.criar_conta_unica(
                    usuario_atual["id"], nome, valor, data_selecionada["valor"].isoformat(),
                    categoria_id=categoria_id,
                )
            else:
                database.criar_serie_recorrente(
                    usuario_atual["id"], nome, valor, data_selecionada["valor"].isoformat(),
                    "mensal" if tipo == "mensal" else "anual",
                    data_termino=data_termino, categoria_id=categoria_id,
                )
            mostrar_tela_principal()

        cabecalho = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=20, icon_color="#0B1410",
                              on_click=lambda e: mostrar_tela_principal()),
                ft.Text("Nova conta", size=18, weight=ft.FontWeight.BOLD, color="#0B1410"),
                ft.Container(width=40),
            ],
        )

        cartao_tipo = ft.Container(
            bgcolor="white",
            border_radius=12,
            padding=14,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("Tipo de conta", size=14, weight=ft.FontWeight.BOLD, color="#0B1410"),
                    linha_tipo,
                ],
            ),
        )

        conteudo = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            controls=[
                ft.Container(
                    padding=ft.Padding(20, 40, 20, 24),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        controls=[
                            cabecalho,
                            ft.Container(height=20),
                            campo_nome,
                            campo_valor,
                            ft.Row(controls=[
                                campo_data,
                                ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, icon_color="#1D9E75",
                                              on_click=abrir_seletor_data),
                            ]),
                            campo_categoria,
                            ft.Container(height=8),
                            cartao_tipo,
                            ft.Container(height=8),
                            cartao_termino,
                            ft.Container(height=8),
                            erro,
                            ft.Button(
                                content="Salvar conta",
                                bgcolor="#1D9E75",
                                color="white",
                                on_click=salvar,
                            ),
                        ],
                    ),
                ),
            ],
        )

        page.add(conteudo)

    mostrar_tela_login()


ft.run(main)
