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


def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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

        cabecalho_atrasadas = ft.Text("Contas atrasadas", size=15, weight=ft.FontWeight.BOLD, color="#0B1410")
        lista_atrasadas = ft.Column(controls=[], spacing=8)

        cabecalho_contas = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("Suas contas", size=15, weight=ft.FontWeight.BOLD, color="#0B1410"),
                ft.Text("Ver todas", size=13, color="#1D9E75"),
            ],
        )

        lista_contas = ft.Column(controls=[], spacing=8)

        def abrir_detalhe_conta(conta):
            page.controls.clear()
            page.overlay.clear()
            page.padding = 0

            categorias_atuais = {c["id"]: c["nome"] for c in database.listar_categorias(usuario_atual["id"])}
            nome_categoria = categorias_atuais.get(conta.get("categoria_id")) or "Sem categoria"

            area_corpo = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, controls=[])

            def mostrar_visualizacao():
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
                    else:
                        database.marcar_conta_como_paga(conta["id"])
                        conta["status"] = "pago"
                    mostrar_visualizacao()

                if conta["status"] == "pago":
                    texto_botao_status, cor_botao_status = "Marcar como pendente", "#E0A030"
                else:
                    texto_botao_status, cor_botao_status = "Marcar como paga", "#39D67C"

                recorrencia = "Sim" if conta.get("conta_fixa") == 1 else "Não"

                parcela_texto = None
                if conta.get("conta_fixa") == 1 and conta.get("serie_id") is not None:
                    parcela = database.obter_parcela(conta["serie_id"], conta["id"])
                    if parcela:
                        posicao, total_ocorrencias = parcela
                        parcela_texto = f"Parcela {posicao} de {total_ocorrencias}"

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

                area_corpo.controls = [
                    ft.Container(
                        padding=ft.Padding(20, 40, 20, 24),
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            controls=[
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
                total_ocorrencias = 1
                if conta.get("conta_fixa") == 1 and conta.get("serie_id") is not None:
                    parcela = database.obter_parcela(conta["serie_id"], conta["id"])
                    if parcela:
                        total_ocorrencias = parcela[1]

                if total_ocorrencias > 1:
                    mostrar_dialogo_exclusao_serie()
                else:
                    mostrar_dialogo_exclusao_simples()

            def mostrar_erro_exclusao_bloqueada():
                dialogo_erro = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Não foi possível excluir"),
                    content=ft.Text(
                        f"'{conta['nome']}' é a primeira ocorrência de uma série que ainda tem "
                        "outras ocorrências. Use 'Excluir definitivamente' para remover a série."
                    ),
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
                        # Defesa extra: a camada de dados também recusa excluir uma
                        # âncora de série com ocorrências ainda existentes, mesmo que
                        # algo além desta tela chame a função sem passar por aqui.
                        mostrar_erro_exclusao_bloqueada()

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
                # A âncora da série é a ocorrência cujo próprio id é o serie_id
                # compartilhado pelas demais. Excluí-la sozinha ("somente este mês")
                # deixaria as ocorrências futuras com uma referência quebrada, então
                # essa opção nem é oferecida quando a conta clicada é a âncora.
                eh_ancora = conta.get("serie_id") == conta.get("id")

                def excluir_apenas_esta(e):
                    sucesso = database.excluir_conta(conta["id"])
                    page.pop_dialog()
                    if sucesso:
                        mostrar_tela_principal()
                    else:
                        mostrar_erro_exclusao_bloqueada()

                def excluir_definitivamente(e):
                    database.excluir_conta_serie(conta["id"])
                    page.pop_dialog()
                    mostrar_tela_principal()

                acoes = [ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog())]
                if not eh_ancora:
                    acoes.append(
                        ft.TextButton(content="Excluir somente este mês", on_click=excluir_apenas_esta)
                    )
                acoes.append(
                    ft.Button(content="Excluir definitivamente", bgcolor="#A32D2D", color="white",
                              on_click=excluir_definitivamente)
                )

                dialogo = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Excluir conta recorrente"),
                    content=ft.Text(
                        f"'{conta['nome']}' faz parte de uma série de contas fixas. "
                        "O que você deseja excluir?"
                    ),
                    actions=acoes,
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

                    if conta.get("conta_fixa") == 1:
                        # RF20: uma ocorrência de conta fixa representa um mês/ano
                        # específico da série — a data só pode mudar de dia, nunca de
                        # mês/ano (nem "somente este mês", nem "este mês em diante").
                        # Bloqueamos aqui, antes de qualquer diálogo, para que o
                        # usuário corrija a data sem perder o que já preencheu.
                        data_original = date.fromisoformat(conta["data_vencimento"])
                        nova_data = data_selecionada["valor"]
                        if (nova_data.year, nova_data.month) != (data_original.year, data_original.month):
                            erro_edit.value = (
                                "Esta é uma conta fixa: a data só pode mudar de dia, "
                                "mantendo o mês e o ano da ocorrência atual."
                            )
                            page.update()
                            return
                        mostrar_dialogo_escopo_edicao(nome, valor, nova_data)
                    else:
                        database.editar_conta_ocorrencia(
                            conta["id"], nome=nome, valor=valor,
                            data_vencimento=data_selecionada["valor"].isoformat(),
                        )
                        mostrar_tela_principal()

                def mostrar_dialogo_escopo_edicao(nome, valor, nova_data):
                    # RF20: para contas fixas, é preciso perguntar se a alteração vale só
                    # para esta ocorrência ou também para as futuras da mesma série.
                    # Mês/ano da nova data já foi validado em salvar_edicao antes de
                    # chegar aqui, então as duas opções são sempre seguras de oferecer.

                    def aplicar_somente_esta(e):
                        sucesso = database.editar_conta_ocorrencia(
                            conta["id"], nome=nome, valor=valor,
                            data_vencimento=nova_data.isoformat(),
                        )
                        page.pop_dialog()
                        if sucesso:
                            mostrar_tela_principal()
                        else:
                            # Defesa extra: a camada de dados também recusa mudança de
                            # mês/ano para contas fixas, mesmo que algo além desta tela
                            # chame a função sem passar pela validação da UI.
                            erro_edit.value = "Não foi possível salvar: a data mudaria de mês/ano nesta conta fixa."
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
                            erro_edit.value = "Não foi possível salvar: a data mudaria de mês/ano nesta conta fixa."
                            page.update()

                    dialogo = ft.AlertDialog(
                        modal=True,
                        title=ft.Text("Aplicar alteração"),
                        content=ft.Text(
                            "Esta é uma conta fixa. A alteração deve valer apenas para este mês "
                            "ou também para os próximos meses da série?"
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
                            ],
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
                frase = f"venceu há {abs(dias_delta)} dia(s)"
            elif dias_delta == 0:
                cor, rotulo_status = "#C9820A", "A vencer"
                frase = "vence hoje"
            else:
                cor, rotulo_status = "#888780", "Pendente"
                frase = f"vence em {dias_delta} dia(s)"

            partes_subtitulo = [p for p in (nome_categoria, frase) if p]
            if conta.get("conta_fixa") == 1 and conta.get("serie_id") is not None:
                parcela = database.obter_parcela(conta["serie_id"], conta["id"])
                if parcela:
                    posicao, total_ocorrencias = parcela
                    partes_subtitulo.append(f"Parcela {posicao} de {total_ocorrencias}")
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

        def atualizar_dados():
            texto_mes.value = f"{MESES_PT[mes_atual[1] - 1]} {mes_atual[0]}"
            ano_mes = f"{mes_atual[0]:04d}-{mes_atual[1]:02d}"

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

            atrasadas = database.listar_contas_atrasadas(usuario_atual["id"])
            lista_atrasadas.controls.clear()
            if not atrasadas:
                lista_atrasadas.controls.append(
                    ft.Container(
                        content=ft.Text("Todas as suas contas estão em dia!", color="#1D9E75", size=13,
                                         weight=ft.FontWeight.BOLD),
                        padding=16,
                    )
                )
            else:
                for c in atrasadas:
                    lista_atrasadas.controls.append(linha_conta(c, categorias.get(c["categoria_id"], "")))

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
                            ft.Container(height=16),
                            cabecalho_atrasadas,
                            ft.Container(height=8),
                            lista_atrasadas,
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
        opcoes_categoria = [ft.dropdown.Option(key="", text="Sem categoria")] + [
            ft.dropdown.Option(key=str(c["id"]), text=f"{c['icone'] + ' ' if c['icone'] else ''}{c['nome']}")
            for c in categorias
        ]
        campo_categoria = ft.Dropdown(
            label="Categoria",
            value=str(categoria_pre_selecionada) if categoria_pre_selecionada else "",
            options=opcoes_categoria, color="#0B1410",
        )

        campo_repetir_ate = ft.TextField(
            label="Repetir até (mês/ano)", hint_text="mm/aaaa", color="#0B1410", visible=False,
        )

        def ao_mudar_conta_fixa(e):
            campo_repetir_ate.visible = campo_fixa.value
            page.update()

        campo_fixa = ft.Switch(value=False, active_color="#1D9E75", on_change=ao_mudar_conta_fixa)

        erro = ft.Text(value="", color="#A32D2D", size=12)

        def salvar(e):
            nome = campo_nome.value.strip() if campo_nome.value else ""
            valor = parse_valor(campo_valor.value)
            categoria_id = int(campo_categoria.value) if campo_categoria.value else None
            conta_fixa = 1 if campo_fixa.value else 0
            repetir_ate = None

            if not nome:
                erro.value = "Digite um nome para a conta."
            elif valor is None:
                erro.value = "Informe um valor válido."
            elif data_selecionada["valor"] is None:
                erro.value = "Escolha a data de vencimento."
            elif conta_fixa:
                texto_repetir = campo_repetir_ate.value.strip() if campo_repetir_ate.value else ""
                if not re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", texto_repetir):
                    erro.value = "Informe o mês final da recorrência no formato mm/aaaa."
                else:
                    mes_repetir, ano_repetir = (int(p) for p in texto_repetir.split("/"))
                    data_venc = data_selecionada["valor"]
                    if (ano_repetir, mes_repetir) < (data_venc.year, data_venc.month):
                        erro.value = "O mês final da recorrência não pode ser anterior ao mês de vencimento."
                    else:
                        repetir_ate = f"{ano_repetir:04d}-{mes_repetir:02d}"
                        erro.value = ""
            else:
                erro.value = ""

            if erro.value:
                page.update()
                return

            database.criar_conta(
                usuario_atual["id"], nome, valor, data_selecionada["valor"].isoformat(),
                categoria_id=categoria_id, conta_fixa=conta_fixa, repetir_ate=repetir_ate,
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

        cartao_fixa = ft.Container(
            bgcolor="white",
            border_radius=12,
            padding=14,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text("Conta fixa (recorrente)", size=14, weight=ft.FontWeight.BOLD, color="#0B1410"),
                            ft.Text("Repete todo mês até uma data limite", size=12, color="#888780"),
                        ],
                        spacing=2,
                    ),
                    campo_fixa,
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
                            cartao_fixa,
                            campo_repetir_ate,
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
