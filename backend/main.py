"""
main.py — App do Sino em Flet, conectado ao banco SQLite.
Tela de login/cadastro + tela de Categorias (CRUD).
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database"))

import flet as ft
import db as database

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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

        card_total = ft.Container(
            bgcolor="#0B1410",
            border_radius=16,
            padding=16,
            content=ft.Column(
                controls=[
                    ft.Text("Total do mês", size=12, color="#888780"),
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

        cabecalho_contas = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("Suas contas", size=15, weight=ft.FontWeight.BOLD, color="#0B1410"),
                ft.Text("Ver todas", size=13, color="#1D9E75"),
            ],
        )

        lista_contas = ft.Column(controls=[], spacing=8)

        def linha_conta(conta, nome_categoria):
            data_venc = date.fromisoformat(conta["data_vencimento"])
            dias_delta = (data_venc - date.today()).days

            if conta["status"] == "atrasado":
                cor, rotulo_status = "#A32D2D", "Atrasado"
                frase = f"venceu há {abs(dias_delta)} dia(s)"
            elif dias_delta == 0:
                cor, rotulo_status = "#C9820A", "A vencer"
                frase = "vence hoje"
            else:
                cor, rotulo_status = "#888780", "Pendente"
                frase = f"vence em {dias_delta} dia(s)"

            subtitulo = f"{nome_categoria} · {frase}" if nome_categoria else frase

            return ft.Container(
                bgcolor="white",
                border_radius=10,
                padding=12,
                border=ft.Border(left=ft.BorderSide(4, cor)),
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

        def atualizar_dados():
            texto_mes.value = f"{MESES_PT[mes_atual[1] - 1]} {mes_atual[0]}"
            ano_mes = f"{mes_atual[0]:04d}-{mes_atual[1]:02d}"

            contas_mes = database.listar_contas(usuario_atual["id"], ano_mes)
            categorias = {c["id"]: c["nome"] for c in database.listar_categorias(usuario_atual["id"])}

            total = sum(c["valor"] for c in contas_mes)
            pago = sum(c["valor"] for c in contas_mes if c["status"] == "pago")
            pendente = total - pago

            valor_total.value = formatar_moeda(total)
            valor_pago.value = f"pago {formatar_moeda(pago)}"
            valor_pendente.value = f"pendente {formatar_moeda(pendente)}"

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
                                ft.Text(f"{len(proximas)} conta(s) vencem esta semana", size=13,
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

        fab = ft.Container(
            content=ft.Icon(ft.Icons.ADD, color="white", size=26),
            bgcolor="#1D9E75",
            width=52,
            height=52,
            border_radius=26,
            alignment=ft.Alignment.CENTER,
            right=20,
            bottom=16,
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
                                    bgcolor="#1D9E75",
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

            def salvar(e):
                nome = campo_nome.value.strip() if campo_nome.value else ""
                if not nome:
                    erro.value = "Digite um nome para a categoria."
                    page.update()
                    return
                icone = campo_icone.value.strip() if campo_icone.value else None

                if cat:
                    database.editar_categoria(cat["id"], nome=nome, icone=icone)
                else:
                    database.criar_categoria(usuario_atual["id"], nome, icone)

                page.pop_dialog()
                atualizar_lista()

            dialogo = ft.AlertDialog(
                modal=True,
                title=ft.Text("Editar categoria" if cat else "Nova categoria"),
                content=ft.Column(controls=[campo_nome, campo_icone, erro], tight=True),
                actions=[
                    ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.Button(content="Salvar", bgcolor="#1D9E75", color="white", on_click=salvar),
                ],
            )
            page.show_dialog(dialogo)

        def confirmar_exclusao(cat):
            def excluir(e):
                database.excluir_categoria(cat["id"])
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

    mostrar_tela_login()


ft.run(main)
