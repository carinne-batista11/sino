"""
main.py — App do Sino em Flet, conectado ao banco SQLite.
Tela de login/cadastro + tela de Categorias (CRUD).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database"))

import flet as ft
import db as database


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
                        mostrar_tela_categorias()
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

                page.close(dialogo)
                atualizar_lista()

            dialogo = ft.AlertDialog(
                modal=True,
                title=ft.Text("Editar categoria" if cat else "Nova categoria"),
                content=ft.Column(controls=[campo_nome, campo_icone, erro], tight=True),
                actions=[
                    ft.TextButton(content="Cancelar", on_click=lambda e: page.close(dialogo)),
                    ft.Button(content="Salvar", bgcolor="#1D9E75", color="white", on_click=salvar),
                ],
            )
            page.open(dialogo)

        def confirmar_exclusao(cat):
            def excluir(e):
                database.excluir_categoria(cat["id"])
                page.close(dialogo)
                atualizar_lista()

            dialogo = ft.AlertDialog(
                modal=True,
                title=ft.Text("Excluir categoria"),
                content=ft.Text(
                    f"Excluir '{cat['nome']}'? As contas associadas não serão excluídas, "
                    "apenas ficarão sem categoria."
                ),
                actions=[
                    ft.TextButton(content="Cancelar", on_click=lambda e: page.close(dialogo)),
                    ft.Button(content="Excluir", bgcolor="#A32D2D", color="white", on_click=excluir),
                ],
            )
            page.open(dialogo)

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
                controls=[cabecalho, lista],
            )
        )
        atualizar_lista()

    mostrar_tela_login()


ft.run(main)
