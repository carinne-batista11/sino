"""
main.py — App do Sino em Flet, agora conectado ao banco SQLite

Novidade em relação à primeira versão: os campos de e-mail e senha
agora conversam de verdade com o database.py — dá pra criar uma
conta e fazer login checando os dados salvos no sino.db.

Como rodar:
    1. pip install flet
    2. python main.py
"""

import flet as ft
import database   # nosso arquivo database.py, na mesma pasta


def main(page: ft.Page):

    # Garante que a tabela de usuários existe antes de qualquer coisa.
    # Se já existir, essa linha não faz nada (lembra do "IF NOT EXISTS").
    database.criar_tabelas()

    # ---- Configurações gerais da janela ----
    page.title = "Sino"
    page.bgcolor = "#F4F4F1"
    page.window.width = 380
    page.window.height = 760
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 24

    # ---- Estado da tela: estamos em modo "login" ou "cadastro"? ----
    # Uma lista com um item só é um truque comum no Flet para guardar
    # uma variável que muda e precisa ser lida de dentro de funções.
    modo_cadastro = [False]

    # ---- Logo ----
    logo = ft.Container(
        content=ft.Text("$ino", size=28, weight=ft.FontWeight.BOLD, color="#39D67C"),
        bgcolor="#0B1410",
        width=80,
        height=80,
        border_radius=40,
        alignment=ft.Alignment.CENTER,
    )

    titulo = ft.Text("Bem-vindo de volta", size=20, weight=ft.FontWeight.BOLD)
    subtitulo = ft.Text("Suas contas, sob controle.", size=13, color="#888780")

    # ---- Campos ----
    # Esse campo só aparece no modo "Criar conta" (visible=False por padrão)
    campo_nome = ft.TextField(
        label="Nome completo",
        hint_text="Seu nome",
        width=330,
        visible=False,
    )

    campo_email = ft.TextField(
        label="E-mail",
        hint_text="voce@email.com",
        width=330,
    )

    campo_senha = ft.TextField(
        label="Senha",
        hint_text="********",
        password=True,
        can_reveal_password=True,
        width=330,
    )

    mensagem = ft.Text(value="", color="#1D9E75")

    # ---- Botão principal: muda de comportamento dependendo do modo ----
    def ao_clicar_botao_principal(e):
        email = campo_email.value.strip() if campo_email.value else ""
        senha = campo_senha.value if campo_senha.value else ""

        if modo_cadastro[0]:
            # ---- Modo CRIAR CONTA ----
            nome = campo_nome.value.strip() if campo_nome.value else ""

            if not nome or not email or not senha:
                mensagem.value = "Preencha nome, e-mail e senha."
                mensagem.color = "#A32D2D"
            else:
                sucesso, texto = database.criar_usuario(nome, email, senha)
                mensagem.value = texto
                mensagem.color = "#1D9E75" if sucesso else "#A32D2D"

                if sucesso:
                    # limpa os campos antes de voltar pro modo login
                    campo_nome.value = ""
                    campo_email.value = ""
                    campo_senha.value = ""
                    # depois de criar a conta, volta pro modo login automaticamente
                    alternar_modo(None)
                    # a linha acima já limpou a mensagem — escrevemos uma nova
                    mensagem.value = "Conta criada! Faça login abaixo."
                    mensagem.color = "#1D9E75"
                    page.update()

        else:
            # ---- Modo LOGIN ----
            if not email or not senha:
                mensagem.value = "Preencha e-mail e senha."
                mensagem.color = "#A32D2D"
            else:
                usuario = database.verificar_login(email, senha)
                if usuario:
                    mensagem.value = f"Bem-vindo(a), {usuario['nome']}! Login OK."
                    mensagem.color = "#1D9E75"
                else:
                    mensagem.value = "E-mail ou senha incorretos."
                    mensagem.color = "#A32D2D"

        page.update()

    botao_principal = ft.ElevatedButton(
        content="Entrar",
        width=330,
        bgcolor="#1D9E75",
        color="white",
        on_click=ao_clicar_botao_principal,
    )

    # ---- Link para alternar entre "Entrar" e "Criar conta" ----
    def alternar_modo(e):
        modo_cadastro[0] = not modo_cadastro[0]

        if modo_cadastro[0]:
            titulo.value = "Crie sua conta"
            subtitulo.value = "Leva menos de um minuto"
            campo_nome.visible = True
            botao_principal.content = "Criar conta"
            texto_alternar.value = "Já tem conta? Entrar"
        else:
            titulo.value = "Bem-vindo de volta"
            subtitulo.value = "Suas contas, sob controle."
            campo_nome.visible = False
            botao_principal.content = "Entrar"
            texto_alternar.value = "Não tem conta? Criar conta"

        mensagem.value = ""
        page.update()

    texto_alternar = ft.TextButton(
        content="Não tem conta? Criar conta",
        on_click=alternar_modo,
    )

    # ---- Monta a tela ----
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


ft.run(main)
