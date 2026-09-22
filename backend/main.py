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

# RF04/RF07 (5.11): chave de opção de Dropdown para "+ Nova categoria" nos
# seletores de categoria de Nova Conta/Editar Conta -- nunca colide com um
# categoria_id real (sempre str(int)) nem com "" ("Sem categoria").
SENTINELA_NOVA_CATEGORIA = "__nova__"

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


# Seletor geral de emojis (RF18/5.12, melhoria de UX pós-Bloco 1): catálogo
# próprio do Sino organizado em grupos, independente do nome digitado --
# garante acesso a um emoji pelo próprio app mesmo quando
# sugestoes_emoji_para não reconhece o nome. Configuração inicial de UX
# (mesmo espírito de PALETA_CORES_CATEGORIAS): dados puros, sem nenhuma
# lógica de renderização aqui -- a tela (abrir_seletor_emoji_geral, dentro
# de mostrar_tela_categorias) só lê esta lista. Editar/adicionar/remover/
# reordenar um grupo ou um emoji é só editar esta estrutura.
#
# "nome": rótulo do grupo, exibido pequeno e integrado ao contorno.
# "principais": exatamente 5 emojis, sempre visíveis com o grupo recolhido.
# "adicionais": só aparecem quando o grupo é expandido.
#
# Emojis podem se repetir entre grupos de propósito (ex.: ❤️ aparece em
# "Família", "Crianças" e "Outros") -- não há deduplicação global.
GRUPOS_EMOJI_CATEGORIA = [
    {
        "nome": "Finanças",
        "principais": ["💲", "💰", "🪙", "💳", "💸"],
        "adicionais": ["💵", "💴", "💶", "💷", "💱", "🤑", "💹", "📊", "🏦", "🪪", "⚖️", "🧾", "📈", "📉", "💼", "🏧", "🧮", "🏷️", "💎"],
    },
    {
        "nome": "Residencial",
        "principais": ["🏠", "🏡", "🏘️", "🏢", "🏨"],
        "adicionais": ["🏚️", "🏩", "🏬", "🏙️", "🏗️", "🛖", "🛋️", "🛏️", "🚪", "🪟", "🪑", "🛁", "🚿", "🚽", "🧹", "🧺", "🧽", "🪣", "🔑", "🔒", "💡", "🪴"],
    },
    {
        "nome": "Veículo",
        "principais": ["🚗", "🚕", "🚙", "🚌", "🏍️"],
        "adicionais": ["🚎", "🚓", "🚐", "🛻", "🚚", "🚛", "🚜", "🚲", "🛵", "✈️", "🚂", "🛳️", "🚆", "🚇", "🚄", "🚢", "⛵", "🚤", "🚁", "🛺", "🚘", "🛞", "⛽", "🅿️", "🚦", "🔧"],
    },
    {
        "nome": "Hospitalar",
        "principais": ["🏥", "🚑", "💊", "💉", "🩺"],
        "adicionais": ["🩻", "🤒", "😷", "🤧", "🤕", "🤢", "🩹", "🩼", "🦽", "🦷", "👓", "🧬", "🧪", "🌡️", "🩸", "❤️", "🫀", "🧠", "👩‍⚕️", "👨‍⚕️", "🧑‍⚕️"],
    },
    {
        "nome": "Pets",
        "principais": ["🐕", "🐈", "🐾", "🐇", "🦜"],
        "adicionais": ["🐩", "🐈‍⬛", "🐁", "🐿️", "🦮", "🐕‍🦺", "🐠", "🐴", "🐎", "🐶", "🐱", "🐹", "🐰", "🐭", "🐦", "🐟", "🐢", "🦎", "🐍", "🐸", "🐔", "🦆", "🦉", "🦔", "🦴"],
    },
    {
        "nome": "Estudos",
        "principais": ["📚", "📝", "💻", "🎓", "📖"],
        "adicionais": ["👩🏻‍💻", "🧑🏻‍💻", "📃", "📓", "📕", "📗", "📘", "📙", "📔", "📒", "📑", "📄", "📋", "✏️", "🖊️", "🖋️", "🖍️", "📏", "📐", "🏫", "🎒", "🧮", "🔬", "🔭", "🧪", "💡"],
    },
    {
        "nome": "Lazer",
        "principais": ["🎮", "🎬", "🎡", "🏖️", "🎨"],
        "adicionais": ["🎲", "🎳", "🏟️", "⛱️", "🎢", "🎠", "🎥", "🍿", "🎭", "🎤", "🎧", "🎵", "🎶", "🎸", "🎹", "🥁", "🎯", "🎰", "🧩", "♟️", "🃏", "🎴", "🎪", "🏕️", "📺", "📷", "📸", "🎉"],
    },
    {
        "nome": "Esportes",
        "principais": ["⚽", "🛼", "🏋️", "🏊", "🚴"],
        "adicionais": ["🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🥏", "🎱", "🏓", "🏸", "🏒", "🏑", "🥍", "🏏", "⛳", "🥊", "🥋", "🎽", "🛹", "⛸️", "🎿", "🏂", "🤸", "🏃", "🧘", "🤾", "🏄", "🤽", "🤺", "🏆", "🥇", "🥈", "🥉"],
    },
    {
        "nome": "Alimentação",
        "principais": ["🍽️", "🍔", "🍕", "🍎", "☕"],
        "adicionais": ["🍴", "🥄", "🥢", "🍳", "🥘", "🍲", "🥗", "🍛", "🍝", "🍜", "🍣", "🍤", "🍱", "🍚", "🍟", "🌭", "🥪", "🌮", "🌯", "🥙", "🥩", "🍗", "🥓", "🥚", "🧀", "🥖", "🥐", "🍞", "🥞", "🧇", "🍌", "🍓", "🍇", "🥑", "🥦", "🍰", "🎂", "🍫", "🍪", "🍩", "🍦", "🫖", "🧃", "🥤"],
    },
    {
        "nome": "Compras",
        "principais": ["🛍️", "🛒", "👗", "👟", "🎁"],
        "adicionais": ["🏷️", "👕", "👚", "👖", "🩳", "👔", "👙", "🩱", "👘", "👠", "👞", "🥾", "👜", "👛", "🎒", "💍", "💎", "⌚", "🕶️", "👓", "💄", "🧴", "🧼", "🧸", "📱", "💻", "🎧", "📦"],
    },
    {
        "nome": "Família",
        "principais": ["👨‍👩‍👧", "👨‍👩‍👧‍👦", "👵", "👴", "👶"],
        "adicionais": ["👨‍👩‍👦", "👩‍👧", "👩‍👦", "👨‍👧", "👨‍👦", "👩", "👨", "🧑", "🧒", "👧", "👦", "👩‍🦰", "👨‍🦰", "👩‍🦳", "👨‍🦳", "🫂", "❤️", "💕", "🏡", "🎂", "🎁"],
    },
    {
        "nome": "Trabalho",
        "principais": ["💼", "🧑‍💻", "🏢", "📊", "📌"],
        "adicionais": ["👩‍💼", "👨‍💼", "🧑‍💼", "👩‍💻", "👨‍💻", "💻", "🖥️", "⌨️", "🖱️", "🖨️", "📱", "☎️", "📞", "📧", "📅", "🗓️", "📋", "📎", "🗂️", "📁", "📈", "🤝", "✍️", "🪪"],
    },
    {
        "nome": "Crianças",
        "principais": ["👶", "🧸", "🍼", "🎈", "🛝"],
        "adicionais": ["🪀", "🪁", "🎠", "🎡", "🎨", "🖍️", "📚", "🎒", "🏫", "🍭", "🍬", "🍪", "🎂", "🎁", "👕", "👟", "🛏️", "🛁", "🧩", "🎮", "⚽", "🚲", "🛴", "❤️"],
    },
    {
        "nome": "Serviços",
        "principais": ["🔧", "🔨", "🧰", "🧹", "⚙️"],
        "adicionais": ["🪛", "🪚", "🔩", "🛠️", "🪜", "🧽", "🧺", "🪣", "🧼", "🚿", "🔌", "💡", "🔑", "🔒", "✂️", "📞", "📦", "🚚", "👷", "🧑‍🔧", "👨‍🔧", "👩‍🔧", "🧑‍🍳", "🧑‍🏫", "🧑‍⚕️", "💇", "💅"],
    },
    {
        "nome": "Beleza e cuidados",
        "principais": ["💄", "💅", "💋", "🧴", "👠"],
        "adicionais": ["💇", "💇‍♀️", "💇‍♂️", "🧖", "🧖‍♀️", "🧖‍♂️", "💆", "💆‍♀️", "💆‍♂️", "👄", "🪞", "🪮", "✂️", "🧼", "🫧", "🚿", "🛁", "👗", "💍", "🕶️", "🌸", "✨"],
    },
    {
        "nome": "Tecnologia",
        "principais": ["📱", "💻", "📸", "🎧", "⌚"],
        "adicionais": ["🖥️", "⌨️", "🖱️", "🖨️", "📷", "📹", "🎥", "📺", "📡", "🔌", "🔋", "💾", "💿", "📀", "🎮", "🕹️", "📞", "☎️", "🤖", "⚙️"],
    },
    {
        "nome": "Assinaturas",
        "principais": ["📺", "🎬", "🎵", "🎮", "▶️"],
        "adicionais": ["🎧", "💻", "🖥️", "📚", "📰", "🗞️", "☁️", "📦", "🎥", "🍿", "🎙️", "📻", "🔔", "🔁", "🗓️", "💳"],
    },
    {
        "nome": "Viagens",
        "principais": ["✈️", "🧳", "🏨", "🗺️", "🏖️"],
        "adicionais": ["🚆", "🚂", "🚄", "🚗", "🚕", "🚌", "🚢", "🛳️", "⛵", "🚤", "🚁", "🛫", "🛬", "🏝️", "⛱️", "🏕️", "🏙️", "🌆", "🌇", "🗽", "🗼", "🏰", "🏯", "🎡", "📷", "📸", "🎒", "🧭", "🌍", "🌎", "🌏"],
    },
    {
        "nome": "Eventos e comemorações",
        "principais": ["🎉", "🎂", "🎁", "🎈", "💐"],
        "adicionais": ["🎊", "🥳", "🍰", "🧁", "🥂", "💍", "👰", "🤵", "💒", "🎓", "🪩", "🎶", "🎵", "🎤", "🎪", "🎀", "🪅", "🕯️", "🌹", "❤️", "💌", "🎟️", "📸", "✨", "🎇", "🎆"],
    },
    {
        "nome": "Outros",
        "principais": ["⭐", "❤️", "✨", "📌", "🔔"],
        "adicionais": ["🌟", "💫", "💖", "💕", "🩷", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "🔥", "🌈", "☀️", "🌙", "☁️", "🌸", "🌻", "🍀", "🎯", "🏷️", "🔖", "📅", "🗓️", "⏰", "⏳", "🎉", "🎊", "🎁", "❗", "❓", "❕", "❔", "✅", "☑️", "➕", "➖", "🔵", "🟢", "🟡", "🟠", "🔴", "🟣", "⚪", "⚫", "🟤", "🔷", "🔶", "🔹", "🔸", "💠", "♻️"],
    },
]


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


def frase_recorrencia(frequencia, data_termino):
    """RF29 revisado (5.8, D7): frase contextual sobre a recorrência de uma
    série ativa, no lugar do texto genérico "Recorrente: Sim". Não trata o
    caso de série encerrada -- quem chama decide esse texto a partir de
    `ativa` (obter_info_serie), já que aqui a série é sempre ativa."""
    frequencia_texto = "mensalmente" if frequencia == "mensal" else "anualmente"
    if data_termino:
        ano_t, mes_t = map(int, data_termino.split("-"))
        return f"Esta conta se repete {frequencia_texto} até {MESES_PT[mes_t - 1].lower()} de {ano_t}."
    return f"Esta conta se repete {frequencia_texto} sem prazo definido para término."


def montar_mensagem_alteracao(nome_antigo, nome_novo, valor_antigo, valor_novo, data_antiga, data_nova,
                               categoria_nome_antiga=None, categoria_nome_nova=None,
                               status_antigo=None, status_novo=None,
                               data_pagamento_antiga=None, data_pagamento_nova=None,
                               recorrencia_acao=None, recorrencia_frequencia=None,
                               recorrencia_data_termino=None):
    """RF20/RF07 (5.6/5.11): frase em linguagem natural descrevendo somente os
    campos realmente alterados (nome, valor, data de vencimento, categoria,
    status/data de pagamento e/ou recorrência). `data_antiga`/`data_nova`
    são objetos `date`. `categoria_nome_antiga`/`categoria_nome_nova` são os
    NOMES já resolvidos da categoria (nunca IDs) -- `None` representa "sem
    categoria". `status_antigo`/`status_novo` são os valores de
    `contas.status` ("pago"/"pendente"/"atrasado"); `data_pagamento_antiga`/
    `data_pagamento_nova` são strings ISO ou `None`. `recorrencia_acao` é
    `None` (nada pendente) | "transformar" | "alterar_frequencia" |
    "encerrar" -- só chamada aqui DEPOIS que a operação estrutural
    correspondente já foi persistida com sucesso (nunca ao só configurar o
    rascunho). Retorna `None` quando nada mudou -- quem chama decide não
    exibir confirmação nenhuma nesse caso. Não inclui IDs nem o escopo da
    edição -- fora do escopo desta frase por decisão de produto.

    Troca de categoria (ambos os nomes preenchidos e diferentes) e mudança
    de data de pagamento SEM troca de status (conta continua paga, só a
    data muda) entram na mesma frase de "Você alterou ...", lado a lado com
    nome/valor/vencimento -- mesmo padrão, mesma pontuação (vírgulas + "e"
    antes do último item). Remoção/definição de categoria, qualquer
    TRANSIÇÃO de status (pendente/atrasado -> pago ou pago -> pendente) e
    qualquer ação de recorrência usam verbo próprio ("removeu"/"definiu"/
    "marcou"/"voltou"/"transformou"/"encerrou") que não combina com
    "alterou" -- por isso viram frases à parte, concatenadas com um espaço
    quando há também alterações que cabem na frase principal."""
    partes = []
    if nome_antigo != nome_novo:
        partes.append(f"o nome de '{nome_antigo}' para '{nome_novo}'")
    if valor_antigo != valor_novo:
        partes.append(f"o valor de {formatar_moeda(valor_antigo)} para {formatar_moeda(valor_novo)}")
    if data_antiga != data_nova:
        partes.append(f"o vencimento de {data_antiga.strftime('%d/%m')} para {data_nova.strftime('%d/%m')}")

    frase_categoria_especial = None
    if categoria_nome_antiga != categoria_nome_nova:
        if categoria_nome_antiga is not None and categoria_nome_nova is not None:
            partes.append(f"a categoria de '{categoria_nome_antiga}' para '{categoria_nome_nova}'")
        elif categoria_nome_antiga is not None:
            frase_categoria_especial = f"Você removeu a categoria '{categoria_nome_antiga}'."
        else:
            frase_categoria_especial = f"Você definiu a categoria como '{categoria_nome_nova}'."

    frase_status_especial = None
    estava_pago = status_antigo == "pago"
    esta_pago = status_novo == "pago"
    if status_antigo is not None and status_novo is not None and estava_pago != esta_pago:
        if esta_pago:
            if data_pagamento_nova:
                data_fmt = date.fromisoformat(data_pagamento_nova).strftime("%d/%m/%Y")
                frase_status_especial = f"Você marcou a conta como paga em {data_fmt}."
            else:
                frase_status_especial = "Você marcou a conta como paga."
        else:
            frase_status_especial = "Você voltou a conta para pendente."
    elif estava_pago and esta_pago and data_pagamento_antiga != data_pagamento_nova:
        if data_pagamento_antiga and data_pagamento_nova:
            antiga_fmt = date.fromisoformat(data_pagamento_antiga).strftime("%d/%m")
            nova_fmt = date.fromisoformat(data_pagamento_nova).strftime("%d/%m")
            partes.append(f"a data de pagamento de {antiga_fmt} para {nova_fmt}")

    def _frequencia_e_termino_em_texto(frequencia, termino):
        frequencia_texto = "mensalmente" if frequencia == "mensal" else "anualmente"
        if termino:
            ano_t, mes_t = map(int, termino.split("-"))
            termino_texto = f"até {MESES_PT[mes_t - 1].lower()} de {ano_t}"
        else:
            termino_texto = "sem data de término"
        return frequencia_texto, termino_texto

    frase_recorrencia_especial = None
    if recorrencia_acao == "transformar":
        frequencia_texto, termino_texto = _frequencia_e_termino_em_texto(
            recorrencia_frequencia, recorrencia_data_termino,
        )
        frase_recorrencia_especial = (
            f"Você transformou esta conta em recorrente ({frequencia_texto}, {termino_texto})."
        )
    elif recorrencia_acao == "alterar_frequencia":
        frequencia_texto, termino_texto = _frequencia_e_termino_em_texto(
            recorrencia_frequencia, recorrencia_data_termino,
        )
        frase_recorrencia_especial = (
            f"Você alterou a frequência da recorrência para {frequencia_texto}, {termino_texto}."
        )
    elif recorrencia_acao == "encerrar":
        frase_recorrencia_especial = "Você encerrou a recorrência desta conta."

    frase_alterou = None
    if partes:
        if len(partes) == 1:
            corpo = partes[0]
        else:
            corpo = f"{', '.join(partes[:-1])} e {partes[-1]}"
        frase_alterou = f"Você alterou {corpo}."

    frases = [
        f for f in (frase_alterou, frase_categoria_especial, frase_status_especial, frase_recorrencia_especial)
        if f
    ]
    if not frases:
        return None
    return " ".join(frases)


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

        titulo_contas = ft.Text("Suas contas", size=15, weight=ft.FontWeight.BOLD, color="#0B1410")

        cabecalho_contas = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                titulo_contas,
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

            # RF29 revisado (D7): frase contextual da seção "Recorrência" em
            # Editar (substitui "Recorrente: Sim") e mensagem de confirmação
            # de "Encerrar recorrência" -- calculado uma vez aqui pelo mesmo
            # motivo de serie_ativa acima. None para conta avulsa.
            info_serie = (
                database.obter_info_serie(conta["serie_id"])
                if conta.get("serie_id") is not None else None
            )

            def bloco_rotulado(rotulo, controles):
                # Padronização visual (pós-validação manual do RF07): Status e
                # Recorrência devem ter a MESMA linguagem visual dos campos
                # normais (contorno + label encaixado na borda superior), não a
                # aparência esmaecida de um TextField(disabled=True). Reaproveita
                # a mesma técnica já usada nos grupos do seletor de emojis
                # (abrir_seletor_emoji_geral/construir_grupo): Stack com
                # clip_behavior=NONE para o rótulo "recortar" a borda superior
                # sem ser cortado -- só troca as cores para o contorno escuro
                # (#0B1410, igual ao texto principal do app) e o fundo do rótulo
                # para a cor de fundo real desta tela (#F4F4F1), não branco.
                #
                # Causa real do encolhimento (achado após teste visual real):
                # `expand` é um sinalizador de FLEX (equivalente a `Expanded`),
                # só tem efeito quando o pai imediato é um Row/Column -- dentro
                # de um Stack ele não faz nada, porque Stack não usa layout de
                # flex. Por isso `expand=True` direto em `caixa` não tinha efeito
                # algum no runtime real, mesmo parecendo correto na teoria.
                #
                # A propriedade que realmente força um Container-com-filho a
                # ocupar toda a largura que o pai oferece é `alignment`: um
                # Container com filho e sem width explícita normalmente encolhe
                # para o tamanho do próprio filho (mesmo se o pai oferecer mais
                # espaço) -- mas, ao definir `alignment`, o Flutter/Flet passa a
                # expandir o Container até o limite (bound) que o pai oferece
                # SOMENTE nos eixos em que esse limite é finito, e usa o
                # alignment só para posicionar o filho dentro dessa caixa maior.
                # Aqui o eixo horizontal É finito (largura do Column em
                # horizontal_alignment=STRETCH, propagada pelo Stack), então a
                # borda passa a ocupar a largura total; o eixo vertical não é
                # limitado (a coluna do formulário rola, então a altura
                # disponível é efetivamente infinita), então a altura continua
                # determinada pelo próprio conteúdo -- exatamente o comportamento
                # desejado (borda larga, bloco compacto). TOP_LEFT preserva o
                # texto/ações alinhados à esquerda, sem esticar o conteúdo
                # interno (Row/Text) -- só a borda externa passa a ir até o fim.
                caixa = ft.Container(
                    border=ft.Border.all(1, "#0B1410"),
                    border_radius=8,
                    padding=ft.Padding(12, 14, 12, 10),
                    alignment=ft.Alignment.TOP_LEFT,
                    content=ft.Column(spacing=8, controls=controles),
                )
                rotulo_flutuante = ft.Container(
                    content=ft.Text(rotulo, size=12, color="#0B1410"),
                    bgcolor="#F4F4F1",
                    padding=ft.Padding(4, 0, 4, 0),
                    left=10,
                    top=-8,
                )
                return ft.Stack(controls=[caixa, rotulo_flutuante], clip_behavior=ft.ClipBehavior.NONE)

            def linha_info_acoes(texto_info, acoes):
                # Refinamento de layout: informação e ações contextuais na
                # MESMA linha, separadas por uma linha vertical discreta (um
                # Container fino, não o caractere "|" nem ft.VerticalDivider --
                # este último exige altura explícita dentro de uma Row, o que
                # não é um padrão já usado em nenhum outro lugar do Sino; um
                # Container de 1px já é um separador visual seguro e simples).
                # wrap=True é a rede de segurança pedida: se não houver espaço
                # (texto de recorrência longo, por exemplo), o conteúdo passa a
                # quebrar em nova linha em vez de cortar texto ou estourar a
                # largura -- nunca altera o texto em si.
                controles = [ft.Text(texto_info, size=14, color="#0B1410")]
                for acao in acoes:
                    controles.append(ft.Container(width=1, height=18, bgcolor="#E5E4DE"))
                    controles.append(acao)
                return ft.Row(wrap=True, spacing=10, run_spacing=6, controls=controles)

            # RF06/5.10 (etapa "Status como rascunho"): Status/data de pagamento
            # dentro de Editar deixam de persistir imediatamente -- viram uma
            # alteração pendente, igual a Nome/Valor/Vencimento/Categoria, só
            # aplicada de fato quando "Salvar alterações" é clicado.
            # `rascunho_status` guarda o estado local; o par ORIGINAL continua
            # intocado em `conta["status"]`/`conta["data_pagamento"]`, nunca
            # mutado por nenhuma ação de Status -- é contra ele que
            # ha_alteracao_pendente() e salvar_edicao() sempre comparam.
            rascunho_status = {"status": conta["status"], "data_pagamento": conta.get("data_pagamento")}

            # Pequena indireção: atualizar_estado_botao_salvar() (o que liga
            # cinza/verde) vive dentro de mostrar_formulario_edicao, porque
            # depende de widgets recriados a cada vez que essa função roda
            # (Nome/Valor/Vencimento/Categoria/botao_salvar) -- não pode ser
            # promovida para cá. construir_conteudo_status(), por outro lado,
            # foi promovida para o escopo de abrir_detalhe_conta (irmã de
            # mostrar_formulario_edicao, não vê seus locais diretamente).
            # gatilho_estado_salvar é o único ponto de contato entre os dois:
            # mostrar_formulario_edicao registra a função real toda vez que
            # roda; os handlers de Status (e, agora, de Recorrência) abaixo só
            # chamam esse gatilho, sem precisar saber onde ela mora.
            gatilho_estado_salvar = {"chamar": lambda: None}

            # RF27/RF28/RF29 (etapa "Recorrência como rascunho"): mesmo
            # princípio do Status -- Transformar em recorrente/Alterar
            # frequência/Encerrar recorrência deixam de escrever no banco ao
            # serem escolhidas; viram uma ÚNICA decisão estrutural pendente,
            # só aplicada de fato no Salvar. `acao` é o slot único (None =
            # nada pendente); escolher de novo qualquer uma das três ações
            # SUBSTITUI o rascunho inteiro -- nunca acumula operações (D5/D6/
            # D7 continuam vivendo inteiramente em database/db.py, só
            # chamadas mais tarde). O estado real (`serie_ativa`/`info_serie`,
            # já existentes) nunca é mutado por essas escolhas -- só por uma
            # aplicação de verdade no Salvar (que, de qualquer forma, sai
            # desta tela logo em seguida).
            rascunho_recorrencia = {"acao": None, "frequencia": None, "data_termino": None}

            # Vencimento (Nome/Valor/Categoria não entram aqui) já é pendente
            # até Salvar desde o RF07 -- mas os diálogos de Transformar/
            # Alterar frequência/Encerrar (definidos abaixo, no escopo de
            # abrir_detalhe_conta) não têm acesso direto a
            # data_selecionada["valor"] (local de mostrar_formulario_edicao).
            # vencimento_pendente é o ponto de contato: mostrar_formulario_
            # edicao mantém isso sincronizado (reset ao abrir, atualizado a
            # cada escolha de data); os três diálogos de recorrência usam
            # SEMPRE este valor -- nunca conta["data_vencimento"] direto --
            # para validar término/calcular a referência, garantindo que a
            # âncora considerada seja a mesma que será realmente salva.
            vencimento_pendente = {"valor": date.fromisoformat(conta["data_vencimento"])}

            # UX (padronização pós-validação manual do RF07) + correção de
            # navegação: bloco "Status", com a informação e as ações
            # contextuais dentro do mesmo contorno. Promovido para o escopo de
            # abrir_detalhe_conta (em vez de nascer dentro de
            # mostrar_formulario_edicao) para que as próprias ações de Status
            # (definidas logo abaixo) possam se re-executar e atualizar SÓ este
            # bloco via atualizar_bloco_status() -- sem depender de
            # mostrar_visualizacao() nem recriar o formulário inteiro, o que
            # preservaria Nome/Valor/Vencimento/Categoria intactos mesmo que
            # ainda não tenham sido salvos.
            def construir_conteudo_status():
                if rascunho_status["status"] == "pago":
                    texto_status_edit = (
                        f"Pago em {date.fromisoformat(rascunho_status['data_pagamento']).strftime('%d/%m/%Y')}"
                        if rascunho_status.get("data_pagamento") else "Pago"
                    )

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
                        page.pop_dialog()
                        # Checagem mínima na UI (RF06/5.10): a mudança fica
                        # pendente até Salvar, então database.editar_data_pagamento
                        # não é mais chamada aqui (é ela quem rejeitava data
                        # futura antes) -- o banco continua sendo a proteção
                        # final, aplicada de novo em aplicar_status_pendente()
                        # no momento do Salvar de verdade.
                        if nova_data.isoformat() > date.today().isoformat():
                            mostrar_erro_data_pagamento()
                            return
                        rascunho_status["data_pagamento"] = nova_data.isoformat()
                        atualizar_bloco_status()

                    seletor_data_pagamento = ft.DatePicker(
                        value=(
                            date.fromisoformat(rascunho_status["data_pagamento"])
                            if rascunho_status.get("data_pagamento") else date.today()
                        ),
                        first_date=date(2000, 1, 1),
                        last_date=date(2100, 12, 31),
                        on_change=ao_escolher_data_pagamento,
                    )
                    page.overlay.append(seletor_data_pagamento)

                    def abrir_seletor_data_pagamento(e):
                        page.show_dialog(seletor_data_pagamento)

                    def marcar_como_pendente_edicao(e):
                        # RF06/5.10 (rascunho): só muda rascunho_status -- nenhuma
                        # chamada a database.marcar_conta_como_pendente aqui. O
                        # status recalculado (Pendente vs Atrasado) usa a mesma
                        # lógica de sempre (data de vencimento vs. hoje, a partir
                        # de conta["data_vencimento"] -- o dado salvo).
                        dias_delta_atual = (date.fromisoformat(conta["data_vencimento"]) - date.today()).days
                        rascunho_status["status"] = "atrasado" if dias_delta_atual < 0 else "pendente"
                        rascunho_status["data_pagamento"] = None
                        atualizar_bloco_status()

                    acoes_status = [
                        ft.TextButton(
                            content="Alterar data de pagamento",
                            on_click=abrir_seletor_data_pagamento,
                        ),
                        ft.TextButton(
                            content="Marcar como pendente",
                            on_click=marcar_como_pendente_edicao,
                        ),
                    ]
                else:
                    texto_status_edit = "Atrasado" if rascunho_status["status"] == "atrasado" else "Pendente"

                    def marcar_como_paga_edicao(e):
                        # RF06/RF24 (rascunho): só muda rascunho_status -- nenhuma
                        # chamada a database.marcar_conta_como_paga aqui.
                        rascunho_status["status"] = "pago"
                        rascunho_status["data_pagamento"] = date.today().isoformat()
                        atualizar_bloco_status()

                    acoes_status = [
                        ft.TextButton(content="Marcar como paga", on_click=marcar_como_paga_edicao),
                    ]

                return linha_info_acoes(texto_status_edit, acoes_status)

            bloco_status = ft.Container(content=bloco_rotulado("Status", [construir_conteudo_status()]))

            def atualizar_bloco_status():
                # Ação de Status agora só altera o rascunho em memória -- aqui
                # recompomos o bloco a partir dele e acionamos o gatilho que
                # atualiza cor/estado de "Salvar alterações" (registrado por
                # mostrar_formulario_edicao; ver comentário acima de
                # rascunho_status).
                bloco_status.content = bloco_rotulado("Status", [construir_conteudo_status()])
                gatilho_estado_salvar["chamar"]()
                page.update()

            # UX (RF29 revisado -- D7) + Recorrência como rascunho: bloco
            # "Recorrência", mesmo princípio do bloco Status acima -- ver
            # rascunho_recorrencia (definido antes) para o porquê de ser um
            # slot único, e construir_conteudo_recorrencia() logo abaixo para
            # como a prévia é decidida.
            def limpar_rascunho_recorrencia():
                # "Desfazer esta alteração" (seção 4 do pedido): restaura a
                # configuração original sem executar nenhuma operação de
                # banco -- nada foi persistido, então não há o que reverter,
                # só o rascunho em memória a esquecer.
                rascunho_recorrencia["acao"] = None
                rascunho_recorrencia["frequencia"] = None
                rascunho_recorrencia["data_termino"] = None
                atualizar_bloco_recorrencia()
                gatilho_estado_salvar["chamar"]()

            def construir_conteudo_recorrencia():
                acao_pendente = rascunho_recorrencia["acao"]
                # Enquanto há uma decisão pendente, o bloco mostra a PRÉVIA
                # dessa decisão (nunca o estado real ainda salvo) -- inclusive
                # oferecendo as mesmas ações de uma recorrência já ativa
                # quando a decisão pendente é "transformar"/"alterar
                # frequência", para permitir editar a própria escolha pendente
                # (ex.: Transformar -> Mensal, depois mudar para Anual) sem
                # que o sistema aja como se já existisse uma série no banco.
                if acao_pendente == "encerrar":
                    ativa_exibida = False
                elif acao_pendente in ("transformar", "alterar_frequencia"):
                    ativa_exibida = True
                else:
                    ativa_exibida = serie_ativa

                if ativa_exibida:
                    if acao_pendente in ("transformar", "alterar_frequencia"):
                        frequencia_exibida = rascunho_recorrencia["frequencia"]
                        termino_exibido = rascunho_recorrencia["data_termino"]
                    else:
                        frequencia_exibida = info_serie["frequencia"]
                        termino_exibido = info_serie["data_termino"]
                    texto_recorrencia = frase_recorrencia(frequencia_exibida, termino_exibido)
                    acoes_recorrencia = [
                        ft.TextButton(
                            content="Alterar frequência",
                            on_click=lambda e: mostrar_dialogo_alterar_frequencia(),
                        ),
                        ft.TextButton(
                            content="Encerrar recorrência",
                            on_click=lambda e: mostrar_dialogo_encerrar_recorrencia(),
                        ),
                    ]
                else:
                    texto_recorrencia = "Esta conta não possui recorrência."
                    acoes_recorrencia = [
                        ft.TextButton(
                            content="Transformar em recorrente",
                            on_click=lambda e: mostrar_dialogo_transformar_recorrente(),
                        ),
                    ]

                if acao_pendente is not None:
                    acoes_recorrencia.append(
                        ft.TextButton(
                            content="Desfazer esta alteração",
                            on_click=lambda e: limpar_rascunho_recorrencia(),
                        )
                    )

                return linha_info_acoes(texto_recorrencia, acoes_recorrencia)

            bloco_recorrencia = ft.Container(
                content=bloco_rotulado("Recorrência", [construir_conteudo_recorrencia()]),
            )

            def atualizar_bloco_recorrencia():
                # Recorrência agora só altera rascunho_recorrencia em memória
                # -- aqui só recompomos o bloco a partir dele (serie_ativa/
                # info_serie reais não são mais tocados aqui; só voltam a ser
                # lidos do banco quando o Salvar de verdade aplicar a
                # operação, e nesse ponto a tela já está de saída).
                bloco_recorrencia.content = bloco_rotulado("Recorrência", [construir_conteudo_recorrencia()])
                page.update()

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

                # UX: Detalhes é predominantemente informativo -- a única ação de
                # status que continua aqui é "Marcar como paga" (pendente/atrasado ->
                # pago). Reverter de pago para pendente não tem mais ação nesta tela;
                # as alterações de status ficam concentradas em Editar
                # (mostrar_formulario_edicao: Pendente/Atrasado -> "Marcar como paga",
                # Pago -> "Alterar data de pagamento"). database.marcar_conta_como_pendente
                # continua existindo em database/db.py (RF06/5.10), só não tem mais
                # nenhum ponto de UI que a chame nesta tela.
                def marcar_como_paga_detalhes(e):
                    # RF06/RF24: altera somente esta ocorrência. O escopo de série
                    # (RF20, seção 5.2 do ERS) só se aplica a nome/valor/data — status
                    # não tem variante "este mês em diante".
                    database.marcar_conta_como_paga(conta["id"])
                    conta["status"] = "pago"
                    conta["data_pagamento"] = date.today().isoformat()
                    mostrar_visualizacao()

                # A tela de Detalhes é só consulta -- exibe "Pago em" quando houver,
                # mas a ação de alterar essa data mora em Editar (mostrar_formulario_edicao).
                pago_em_texto = None
                if conta["status"] == "pago" and conta.get("data_pagamento"):
                    pago_em_texto = date.fromisoformat(conta["data_pagamento"]).strftime("%d/%m/%Y")

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

                # Frase contextual de recorrência (mesma lógica de Editar --
                # mostrar_formulario_edicao -- reaproveitando frase_recorrencia() e
                # info_serie/serie_ativa já calculados uma vez no topo de
                # abrir_detalhe_conta). Avulsa e recorrência encerrada mostram o
                # mesmo texto -- depois de encerrada, a conta é tratada como avulsa
                # também aqui em Detalhes, igual já acontece em Editar. As ações
                # continuam só em Editar; aqui é somente consulta.
                if serie_ativa:
                    recorrencia_texto = frase_recorrencia(info_serie["frequencia"], info_serie["data_termino"])
                else:
                    recorrencia_texto = "Esta conta não possui recorrência."

                linhas_cartao = [
                    linha_detalhe("Nome", conta["nome"]),
                    linha_detalhe("Valor", formatar_moeda(conta["valor"])),
                    linha_detalhe("Vencimento", data_venc.strftime("%d/%m/%Y")),
                    linha_detalhe("Categoria", nome_categoria),
                    linha_detalhe("Status", rotulo_status, cor_valor=cor_status),
                    linha_detalhe("Recorrência", recorrencia_texto),
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
                ]
                if conta["status"] != "pago":
                    controles_acao.append(
                        ft.Button(
                            content="Marcar como paga",
                            bgcolor="#39D67C",
                            color="white",
                            on_click=marcar_como_paga_detalhes,
                        ),
                    )

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
                # RF28: conta avulsa de verdade (serie_id None) OU com recorrência já
                # encerrada (serie_id aponta pra série inativa) -- tratadas da mesma
                # forma, botão condicionado a "not serie_ativa" na seção Recorrência
                # de mostrar_formulario_edicao. database.transformar_em_recorrente já
                # aceita os dois casos, só rejeita série ativa.
                frequencia_transf = {"valor": "mensal"}
                linha_frequencia_transf = construir_seletor_frequencia(frequencia_transf)

                # "Sem data de término" começa DESATIVADO -- mesmo padrão já usado em
                # "Nova conta" e em "Alterar frequência" (D5): o término fica visível e
                # disponível por padrão; só quando o usuário ativa explicitamente é que
                # a recorrência passa a ser sem término.
                sem_termino_transf = ft.Switch(value=False, active_color="#1D9E75")
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
                    spacing=8, controls=[campo_mes_termino_transf, campo_ano_termino_transf], visible=True,
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
                        # Vencimento pendente (RF07, já existente): valida contra
                        # o que está sendo editado nesta sessão, não contra o
                        # valor ainda salvo -- garante que a âncora considerada
                        # aqui seja a mesma que vai para o banco no Salvar.
                        data_venc = vencimento_pendente["valor"]
                        if (ano_termino, mes_termino) < (data_venc.year, data_venc.month):
                            erro_transf.value = "O término não pode ser anterior à data de vencimento desta conta."
                            page.update()
                            return
                        data_termino = f"{ano_termino:04d}-{mes_termino:02d}"

                    # Recorrência como rascunho: nenhuma chamada a
                    # database.transformar_em_recorrente aqui -- só grava a
                    # decisão pendente. A operação de verdade só acontece
                    # dentro do fluxo de Salvar (aplicar_recorrencia_pendente).
                    rascunho_recorrencia["acao"] = "transformar"
                    rascunho_recorrencia["frequencia"] = frequencia_transf["valor"]
                    rascunho_recorrencia["data_termino"] = data_termino
                    page.pop_dialog()
                    atualizar_bloco_recorrencia()
                    gatilho_estado_salvar["chamar"]()

                dialogo = ft.AlertDialog(
                    modal=True,
                    bgcolor="white",
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
                        # Vencimento pendente (RF07, já existente): mesma razão
                        # de confirmar_transformacao acima.
                        data_venc_atual = vencimento_pendente["valor"]
                        if (ano_termino, mes_termino) < (data_venc_atual.year, data_venc_atual.month):
                            erro_freq.value = "O término não pode ser anterior à data desta ocorrência."
                            page.update()
                            return
                        data_termino = f"{ano_termino:04d}-{mes_termino:02d}"

                    # Recorrência como rascunho: nenhuma chamada a
                    # database.alterar_frequencia_serie aqui -- só grava a
                    # decisão pendente (D5 preservado: término sempre uma
                    # escolha nova, nunca reaproveitado, exatamente como já
                    # acontecia -- só o momento da chamada real muda).
                    #
                    # "Mudar de ideia": este botão também é o usado para
                    # EDITAR uma transformação ainda pendente (prévia como se
                    # já fosse ativa -- ver construir_conteudo_recorrencia).
                    # Se já havia "transformar" pendente, a decisão final
                    # continua sendo criar uma série nova -- só os parâmetros
                    # mudam; nunca vira "alterar_frequencia" (que pressupõe
                    # uma série já existente de verdade).
                    if rascunho_recorrencia["acao"] != "transformar":
                        rascunho_recorrencia["acao"] = "alterar_frequencia"
                    rascunho_recorrencia["frequencia"] = nova_frequencia["valor"]
                    rascunho_recorrencia["data_termino"] = data_termino

                    # Normalização -- só faz sentido quando a decisão pendente
                    # é ajustar uma série que JÁ existe de verdade
                    # (info_serie): se a escolha final bate exatamente com a
                    # configuração real e atual dela, não há alteração de
                    # verdade -- evita deixar "Salvar" verde à toa e evita uma
                    # operação estrutural desnecessária no Salvar. Nunca se
                    # aplica a "transformar" (série nova, mesmo que os
                    # parâmetros coincidam por acaso com uma série antiga que
                    # está sendo substituída -- ver aplicar_recorrencia_pendente).
                    if (
                        rascunho_recorrencia["acao"] == "alterar_frequencia"
                        and info_serie is not None
                        and rascunho_recorrencia["frequencia"] == info_serie["frequencia"]
                        and rascunho_recorrencia["data_termino"] == info_serie["data_termino"]
                    ):
                        rascunho_recorrencia["acao"] = None
                        rascunho_recorrencia["frequencia"] = None
                        rascunho_recorrencia["data_termino"] = None

                    page.pop_dialog()
                    atualizar_bloco_recorrencia()
                    gatilho_estado_salvar["chamar"]()

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

            def mostrar_dialogo_encerrar_recorrencia():
                # RF29 revisado (5.8, D7): contextual à ocorrência sendo editada
                # (conta["data_vencimento"]), nunca à data atual do sistema --
                # database.encerrar_recorrencia decide sozinha, a partir da
                # própria referência e de hoje, o que preservar (regra fechada
                # em D7: nunca apaga o que já aconteceu, nem a ocorrência
                # selecionada).
                erro_encerramento = ft.Text(value="", color="#A32D2D", size=12)
                # Vencimento pendente (RF07, já existente): mesma razão dos
                # outros dois diálogos -- referência calculada a partir do que
                # está sendo editado nesta sessão, não do valor ainda salvo.
                data_venc_referencia = vencimento_pendente["valor"]
                mes_referencia_texto = (
                    f"{MESES_PT[data_venc_referencia.month - 1].lower()} de {data_venc_referencia.year}"
                )
                frase_estado = (
                    frase_recorrencia(info_serie["frequencia"], info_serie["data_termino"])
                    if info_serie else ""
                )

                def confirmar_encerramento(e):
                    # Recorrência como rascunho: nenhuma chamada a
                    # database.encerrar_recorrencia aqui -- só grava a decisão
                    # pendente. D7 (corte max(referência, hoje), proteção de
                    # ocorrências pagas/editadas) só é recalculado dentro da
                    # própria função, no momento em que o Salvar a chamar de
                    # verdade.
                    #
                    # Este diálogo também pode ser aberto quando a "prévia
                    # ativa" é só uma transformação ainda pendente (conta sem
                    # série real -- ver construir_conteudo_recorrencia). Nesse
                    # caso não existe nada de verdade para encerrar no banco;
                    # "Encerrar" só pode significar desistir da transformação
                    # pendente, então o efeito correto é limpar o rascunho
                    # (equivalente a "Desfazer esta alteração"), nunca marcar
                    # "encerrar" -- isso evitaria uma falha no Salvar
                    # (encerrar_recorrencia rejeitaria uma conta avulsa).
                    # `serie_ativa` aqui é sempre o estado REAL original,
                    # nunca mutado por rascunhos -- é o jeito seguro de saber
                    # se existe mesmo uma série para encerrar.
                    if serie_ativa:
                        rascunho_recorrencia["acao"] = "encerrar"
                        rascunho_recorrencia["frequencia"] = None
                        rascunho_recorrencia["data_termino"] = None
                    else:
                        rascunho_recorrencia["acao"] = None
                        rascunho_recorrencia["frequencia"] = None
                        rascunho_recorrencia["data_termino"] = None
                    page.pop_dialog()
                    atualizar_bloco_recorrencia()
                    gatilho_estado_salvar["chamar"]()

                dialogo = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Encerrar recorrência"),
                    content=ft.Column(
                        tight=True,
                        spacing=12,
                        controls=[
                            ft.Text(
                                f"{frase_estado} Ao salvar as alterações, a recorrência será "
                                f"encerrada a partir de {mes_referencia_texto}: as contas que já "
                                "aconteceram serão mantidas, e as próximas ainda não realizadas "
                                "serão removidas."
                            ),
                            erro_encerramento,
                        ],
                    ),
                    actions=[
                        ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog()),
                        ft.Button(content="Encerrar recorrência", bgcolor="#A32D2D", color="white",
                                  on_click=confirmar_encerramento),
                    ],
                )
                page.show_dialog(dialogo)

            def mostrar_formulario_edicao():
                # Evita empilhar um DatePicker novo no overlay a cada vez que o
                # formulário é reaberto (visualização -> Editar -> voltar -> Editar...).
                page.overlay.clear()

                data_venc_atual = date.fromisoformat(conta["data_vencimento"])
                data_selecionada = {"valor": data_venc_atual}
                # Recorrência como rascunho: mantém vencimento_pendente (lido
                # pelos diálogos de Transformar/Alterar frequência/Encerrar,
                # que vivem fora desta função) sincronizado com o valor real
                # sendo editado aqui -- reset a cada abertura de Editar.
                vencimento_pendente["valor"] = data_venc_atual

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
                # RF07/5.11: categoria agora editável -- mesmo Dropdown/opções de
                # Nova Conta (montar_opcoes_categoria, promovida a main()),
                # incluindo "+ Nova categoria". Valor inicial reflete a
                # categoria atual da conta ("" quando não tem nenhuma).
                categoria_id_original = conta.get("categoria_id")
                campo_categoria_edit = ft.Dropdown(
                    label="Categoria",
                    value=str(categoria_id_original) if categoria_id_original is not None else "",
                    options=montar_opcoes_categoria(), color="#0B1410",
                    expand=True,
                )
                ultima_categoria_valida_edit = {"valor": campo_categoria_edit.value}

                def ao_mudar_categoria_edit(e):
                    if campo_categoria_edit.value != SENTINELA_NOVA_CATEGORIA:
                        ultima_categoria_valida_edit["valor"] = campo_categoria_edit.value
                        atualizar_estado_botao_salvar()
                        return

                    # "+ Nova categoria": restaura a seleção anterior antes de
                    # abrir o formulário compartilhado -- mesmo padrão de Nova
                    # Conta, para nunca deixar a sentinela "selecionada".
                    campo_categoria_edit.value = ultima_categoria_valida_edit["valor"]
                    page.update()

                    def ao_criar_categoria_edit(categoria_id):
                        # Criar uma categoria por si só NÃO conta como alteração
                        # da conta -- só o valor final do Dropdown importa
                        # (ha_alteracao_pendente compara por valor, nunca pelo
                        # evento "categoria foi criada"). categorias_atuais é
                        # atualizado em conjunto para que a nova categoria
                        # resolva corretamente pelo nome na mensagem do RF20.
                        categorias_atuais.clear()
                        categorias_atuais.update(
                            {c["id"]: c["nome"] for c in database.listar_categorias(usuario_atual["id"])}
                        )
                        campo_categoria_edit.options = montar_opcoes_categoria()
                        campo_categoria_edit.value = str(categoria_id)
                        ultima_categoria_valida_edit["valor"] = campo_categoria_edit.value
                        page.update()
                        atualizar_estado_botao_salvar()

                    abrir_criacao_categoria(ao_criar_categoria_edit)

                # Flet 0.86.5: ft.Dropdown NÃO tem evento `on_change` (confirmado
                # por introspecção -- só TextField/DatePicker têm). O evento real
                # de seleção é `on_select`; `on_change` seria só um atributo Python
                # solto, nunca ligado a nenhum evento, e o handler nunca dispararia.
                campo_categoria_edit.on_select = ao_mudar_categoria_edit

                def ao_escolher_data(e):
                    if e.control.value:
                        data_selecionada["valor"] = e.control.value.date()
                        vencimento_pendente["valor"] = data_selecionada["valor"]
                        campo_data_edit.value = data_selecionada["valor"].strftime("%d/%m/%Y")
                        page.update()
                        atualizar_estado_botao_salvar()

                seletor_data = ft.DatePicker(
                    first_date=date(2000, 1, 1),
                    last_date=date(2100, 12, 31),
                    on_change=ao_escolher_data,
                )
                page.overlay.append(seletor_data)

                def abrir_seletor_data(e):
                    page.show_dialog(seletor_data)

                def ha_alteracao_pendente():
                    # RF07 (5.11) + RF20 (5.6) + Status como rascunho: mesma
                    # comparação usada para montar a mensagem natural, mas só o
                    # booleano -- usada para habilitar/desabilitar "Salvar
                    # alterações" em tempo real. Valor sempre comparado já
                    # parseado (nunca a string bruta do campo) para não falsear
                    # positivo por formatação ("150,00" vs "150,0"); um valor
                    # temporariamente inválido (parse_valor -> None) ainda conta
                    # como alteração -- apenas a validação em salvar_edicao
                    # explica o erro. rascunho_status é sempre comparado contra
                    # `conta["status"]`/`conta.get("data_pagamento")` -- o
                    # ORIGINAL, nunca mutado -- para que voltar ao estado
                    # original desabilite Salvar de novo automaticamente.
                    nome_atual = campo_nome_edit.value.strip() if campo_nome_edit.value else ""
                    valor_atual = parse_valor(campo_valor_edit.value)
                    categoria_atual = (
                        int(campo_categoria_edit.value) if campo_categoria_edit.value else None
                    )
                    return (
                        nome_atual != conta["nome"]
                        or valor_atual != conta["valor"]
                        or data_selecionada["valor"] != data_venc_atual
                        or categoria_atual != categoria_id_original
                        or rascunho_status["status"] != conta["status"]
                        or rascunho_status["data_pagamento"] != conta.get("data_pagamento")
                        or rascunho_recorrencia["acao"] is not None
                    )

                def atualizar_estado_botao_salvar():
                    # Estado visual sempre derivado da mesma ha_alteracao_pendente()
                    # -- nunca uma segunda lógica de detecção só para a cor.
                    tem_alteracao = ha_alteracao_pendente()
                    botao_salvar.disabled = not tem_alteracao
                    botao_salvar.bgcolor = "#1D9E75" if tem_alteracao else "#E5E4DE"
                    botao_salvar.color = "white" if tem_alteracao else "#888780"
                    page.update()

                # Registra a função real no gatilho compartilhado com
                # construir_conteudo_status/atualizar_bloco_status (definidas em
                # abrir_detalhe_conta -- ver comentário junto a rascunho_status).
                # Também reseta rascunho_status para o valor ATUAL de `conta`
                # toda vez que este formulário é (re)aberto -- é isso que faz
                # Cancelar "descartar" uma mudança de Status pendente: como
                # nada foi persistido, reabrir Editar simplesmente recomeça do
                # zero a partir do estado real (nunca alterado). O bloco visual
                # é recomposto na hora (sem passar por atualizar_bloco_status,
                # que dependeria de botao_salvar -- ainda não existe neste
                # ponto da função) para não mostrar um Status "preso" numa
                # escolha pendente de uma sessão anterior de Editar já
                # cancelada.
                gatilho_estado_salvar["chamar"] = atualizar_estado_botao_salvar
                rascunho_status["status"] = conta["status"]
                rascunho_status["data_pagamento"] = conta.get("data_pagamento")
                bloco_status.content = bloco_rotulado("Status", [construir_conteudo_status()])
                # Mesmo raciocínio para Recorrência: reseta o rascunho e
                # recompõe o bloco na hora, para que Cancelar (reabrir Editar)
                # nunca mostre uma decisão pendente de uma sessão já cancelada.
                rascunho_recorrencia["acao"] = None
                rascunho_recorrencia["frequencia"] = None
                rascunho_recorrencia["data_termino"] = None
                bloco_recorrencia.content = bloco_rotulado("Recorrência", [construir_conteudo_recorrencia()])

                campo_nome_edit.on_change = lambda e: atualizar_estado_botao_salvar()
                campo_valor_edit.on_change = lambda e: atualizar_estado_botao_salvar()


                erro_edit = ft.Text(value="", color="#A32D2D", size=12)

                def aplicar_status_pendente():
                    # Status pertence exclusivamente à ocorrência (5.9/5.1) --
                    # aplicado SEMPRE em conta["id"], nunca propagado para a
                    # série, independente do escopo escolhido para
                    # Nome/Valor/Vencimento/Categoria (chamada tanto no ramo
                    # direto quanto nos dois ramos do diálogo de escopo, abaixo).
                    # Compara sempre contra o original (`conta["status"]`/
                    # `conta.get("data_pagamento")`, nunca mutados) -- se
                    # rascunho_status voltou a bater com o original, nenhuma
                    # chamada é feita. Reaproveita as mesmas 3 funções de
                    # sempre, sem nenhuma regra nova.
                    estava_pago = conta["status"] == "pago"
                    esta_pago = rascunho_status["status"] == "pago"
                    if esta_pago and not estava_pago:
                        database.marcar_conta_como_paga(
                            conta["id"], data_pagamento=rascunho_status["data_pagamento"],
                        )
                    elif estava_pago and not esta_pago:
                        database.marcar_conta_como_pendente(conta["id"])
                    elif (
                        estava_pago and esta_pago
                        and rascunho_status["data_pagamento"] != conta.get("data_pagamento")
                    ):
                        database.editar_data_pagamento(conta["id"], rascunho_status["data_pagamento"])

                def aplicar_recorrencia_pendente():
                    # Só chamada dentro do fluxo de Salvar, nunca ao configurar
                    # o rascunho (ver os três diálogos de Transformar/Alterar
                    # frequência/Encerrar). A ordem em que quem chama esta
                    # função a invoca (sempre depois de campos comuns/Status)
                    # garante que a linha de `contas` já reflita nome/valor/
                    # vencimento/categoria definitivos quando
                    # transformar_em_recorrente/alterar_frequencia_serie lerem
                    # a conta para usar como âncora. Retorna True quando
                    # aplicada com sucesso (ou quando não havia nada
                    # pendente); False só se a operação estrutural falhar de
                    # verdade (ValueError) -- caso raro, sem rollback do que já
                    # foi salvo antes (nome/valor/Status), só um aviso claro.
                    acao = rascunho_recorrencia["acao"]
                    if acao is None:
                        return True
                    try:
                        if acao == "transformar":
                            # "Mudar de ideia" (Encerrar -> depois Transformar,
                            # na mesma sessão): se a série REAL original ainda
                            # está ativa (nada foi persistido até aqui, então
                            # ela continua ativa de verdade no banco),
                            # transformar_em_recorrente rejeitaria de cara --
                            # ela só aceita conta avulsa ou com recorrência já
                            # encerrada. Encerramos a série real primeiro
                            # (preserva o histórico dela, D7) e só então
                            # criamos a nova -- as duas operações estruturais
                            # de sempre, só que em sequência, para entregar o
                            # resultado que o usuário via como UMA decisão só.
                            if serie_ativa:
                                database.encerrar_recorrencia(conta["id"])
                            novo_serie_id, _ = database.transformar_em_recorrente(
                                conta["id"], rascunho_recorrencia["frequencia"],
                                data_termino=rascunho_recorrencia["data_termino"],
                            )
                            conta["serie_id"] = novo_serie_id
                        elif acao == "alterar_frequencia":
                            database.alterar_frequencia_serie(
                                conta["id"], rascunho_recorrencia["frequencia"],
                                data_termino=rascunho_recorrencia["data_termino"],
                            )
                        elif acao == "encerrar":
                            database.encerrar_recorrencia(conta["id"])
                    except ValueError:
                        return False
                    return True

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

                    # RF07/5.11: "" no Dropdown = Sem categoria. remover_categoria
                    # avisa explicitamente o db.py quando é para limpar
                    # categoria_id (None sozinho significaria "não mexer" --
                    # mesma ambiguidade que motivou o parâmetro novo).
                    categoria_id_novo = (
                        int(campo_categoria_edit.value) if campo_categoria_edit.value else None
                    )
                    remover_categoria = campo_categoria_edit.value == ""

                    # RF20/5.6 (+ RF07 + Status): frase em linguagem natural
                    # descrevendo só os campos realmente alterados -- comparada
                    # aqui, antes de qualquer escopo ser escolhido, porque é o
                    # único ponto em que os valores antigos e os novos (recém
                    # validados) estão os dois disponíveis lado a lado. `None`
                    # quando nada mudou -- nesse caso nenhuma confirmação é
                    # exibida (e, defensivamente, nem o diálogo de escopo é
                    # aberto -- ver guarda abaixo).
                    mensagem_alteracao = montar_mensagem_alteracao(
                        conta["nome"], nome, conta["valor"], valor, data_venc_atual, nova_data,
                        categoria_nome_antiga=categorias_atuais.get(categoria_id_original),
                        categoria_nome_nova=categorias_atuais.get(categoria_id_novo),
                        status_antigo=conta["status"], status_novo=rascunho_status["status"],
                        data_pagamento_antiga=conta.get("data_pagamento"),
                        data_pagamento_nova=rascunho_status["data_pagamento"],
                        recorrencia_acao=rascunho_recorrencia["acao"],
                        recorrencia_frequencia=rascunho_recorrencia["frequencia"],
                        recorrencia_data_termino=rascunho_recorrencia["data_termino"],
                    )
                    if mensagem_alteracao is None:
                        # Nada mudou de fato -- não deveria ser alcançável com
                        # "Salvar alterações" desabilitado, mas serve de guarda
                        # defensiva contra o diálogo de escopo abrir à toa.
                        return

                    # "Há alguma alteração?" (mensagem_alteracao acima, também usada
                    # por ha_alteracao_pendente/Salvar) é uma pergunta DIFERENTE de
                    # "essa alteração precisa de escolha de escopo?" -- Status/data de
                    # pagamento pertencem exclusivamente à ocorrência (5.9/5.1) e nunca
                    # são propagáveis para a série, então NUNCA justificam sozinhos o
                    # diálogo "Somente este mês/Este mês em diante". Só Nome/Valor/
                    # Vencimento/Categoria entram nesta checagem -- de propósito, não
                    # volte a juntar as duas perguntas numa só (importante também para
                    # quando Recorrência virar rascunho: a mesma distinção vai valer).
                    ha_alteracao_propagavel = (
                        nome != conta["nome"]
                        or valor != conta["valor"]
                        or nova_data != data_venc_atual
                        or categoria_id_novo != categoria_id_original
                    )

                    if conta.get("serie_id") is not None and serie_ativa and ha_alteracao_propagavel:
                        # RF20 (5.6): só pergunta o escopo quando existe algo
                        # propagável de fato (Nome/Valor/Vencimento/Categoria) --
                        # uma alteração só de Status/data de pagamento nunca chega
                        # aqui, mesmo numa série ativa. Sem restrição de mês/ano
                        # (removida na Fase 2.6); a nova data pode cair em
                        # qualquer mês/ano. Série já removida (RF29) cai direto no
                        # ramo de baixo, como conta avulsa.
                        mostrar_dialogo_escopo_edicao(
                            nome, valor, nova_data, categoria_id_novo, remover_categoria, mensagem_alteracao,
                        )
                    else:
                        if ha_alteracao_propagavel:
                            # Só grava Nome/Valor/Vencimento/Categoria quando algo
                            # deles de fato mudou -- uma alteração só de Status não
                            # deve gerar uma reescrita sem propósito destes campos
                            # (e, numa série ativa, não deve marcar
                            # editado_individualmente=1 à toa só por causa de
                            # Status, que nunca é uma edição desses campos).
                            database.editar_conta_ocorrencia(
                                conta["id"], nome=nome, valor=valor,
                                data_vencimento=nova_data.isoformat(),
                                categoria_id=categoria_id_novo, remover_categoria=remover_categoria,
                            )
                        aplicar_status_pendente()
                        if not aplicar_recorrencia_pendente():
                            erro_edit.value = "Não foi possível aplicar a alteração de recorrência."
                            page.update()
                            return
                        # RF20/5.6 (conta avulsa ou recorrência já encerrada -- sem
                        # diálogo de escopo, decisão de produto): só exibe a
                        # confirmação quando algo realmente mudou; sem alteração real,
                        # mantém o comportamento de sempre (volta direto à Principal).
                        mostrar_confirmacao_edicao(mensagem_alteracao)

                def mostrar_confirmacao_edicao(mensagem_alteracao, dialogo_alvo=None):
                    # RF20/5.6: feedback em linguagem natural exibido DEPOIS que a
                    # alteração já foi salva com sucesso -- nunca uma confirmação
                    # prévia. Reaproveita o AlertDialog de
                    # escopo já aberto quando houver um (série ativa, `dialogo_alvo`);
                    # cria um novo, só com "Entendi", quando não há diálogo em aberto
                    # (conta avulsa ou série encerrada, `dialogo_alvo=None`).
                    def fechar_confirmacao(e):
                        page.pop_dialog()
                        mostrar_tela_principal()

                    acao_entendi = ft.Button(content="Entendi", bgcolor="#1D9E75", color="white",
                                              on_click=fechar_confirmacao)

                    if dialogo_alvo is not None:
                        dialogo_alvo.title = ft.Text("Alteração salva")
                        dialogo_alvo.content = ft.Text(mensagem_alteracao)
                        dialogo_alvo.actions = [acao_entendi]
                        page.update()
                    else:
                        page.show_dialog(
                            ft.AlertDialog(
                                modal=True,
                                title=ft.Text("Alteração salva"),
                                content=ft.Text(mensagem_alteracao),
                                actions=[acao_entendi],
                            )
                        )

                def mostrar_dialogo_escopo_edicao(nome, valor, nova_data, categoria_id_novo,
                                                   remover_categoria, mensagem_alteracao):
                    def aplicar_somente_esta(e):
                        sucesso = database.editar_conta_ocorrencia(
                            conta["id"], nome=nome, valor=valor,
                            data_vencimento=nova_data.isoformat(),
                            categoria_id=categoria_id_novo, remover_categoria=remover_categoria,
                        )
                        if not sucesso:
                            page.pop_dialog()
                            erro_edit.value = "Não foi possível salvar esta alteração."
                            page.update()
                            return
                        aplicar_status_pendente()
                        if not aplicar_recorrencia_pendente():
                            page.pop_dialog()
                            erro_edit.value = "Não foi possível aplicar a alteração de recorrência."
                            page.update()
                            return
                        mostrar_confirmacao_edicao(mensagem_alteracao, dialogo_alvo=dialogo)

                    def aplicar_este_mes_em_diante(e):
                        sucesso = database.editar_conta_serie(
                            conta["id"], nome=nome, valor=valor,
                            data_vencimento=nova_data.isoformat(),
                            categoria_id=categoria_id_novo, remover_categoria=remover_categoria,
                        )
                        if not sucesso:
                            page.pop_dialog()
                            erro_edit.value = (
                                "Não foi possível salvar: a nova data ultrapassaria o "
                                "término definido para esta recorrência."
                            )
                            page.update()
                            return
                        aplicar_status_pendente()
                        if not aplicar_recorrencia_pendente():
                            page.pop_dialog()
                            erro_edit.value = "Não foi possível aplicar a alteração de recorrência."
                            page.update()
                            return
                        mostrar_confirmacao_edicao(mensagem_alteracao, dialogo_alvo=dialogo)

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


                # RF07/RF20 (5.6/5.11) + padronização visual pós-validação manual:
                # "Salvar alterações" começa desabilitado (cinza -- #E5E4DE/#888780,
                # mesmas cores já usadas no app para estado inativo) e só habilita
                # (verde -- #1D9E75, mesma cor de toda ação principal do Sino)
                # quando nome/valor/vencimento/categoria realmente diferirem do
                # estado original (ha_alteracao_pendente, já conectada via
                # on_change em cada campo -- ver atualizar_estado_botao_salvar
                # acima). Larguras fixas para os dois pararem de ocupar a tela
                # inteira e formarem um grupo coerente alinhado à direita, com
                # Salvar (ação principal) um pouco maior que Cancelar (secundário).
                # "Cancelar" nunca salva, nunca abre o diálogo de escopo, nunca
                # mostra "Alteração salva" -- mesmo destino que a seta de voltar do
                # cabeçalho já usa, preservado sem nenhuma mudança.
                botao_cancelar_edicao = ft.Button(
                    content="Cancelar",
                    bgcolor="white",
                    color="#0B1410",
                    style=ft.ButtonStyle(side=ft.BorderSide(1, "#E5E4DE")),
                    width=110,
                    on_click=lambda e: mostrar_visualizacao(),
                )
                botao_salvar = ft.Button(
                    content="Salvar alterações",
                    bgcolor="#E5E4DE",
                    color="#888780",
                    disabled=True,
                    width=180,
                    on_click=salvar_edicao,
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
                                bloco_status,
                                bloco_recorrencia,
                                ft.Container(height=16),
                                erro_edit,
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.END,
                                    spacing=10,
                                    controls=[botao_cancelar_edicao, botao_salvar],
                                ),
                            ],
                        ),
                    ),
                ]
                page.update()

            page.add(area_corpo)
            mostrar_visualizacao()

        def linha_conta(conta, nome_categoria, acao_rapida_pagamento=False):
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

            controles_linha = [
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
            ]

            # Layout: colunas de largura fixa para valor/status e para a ação, para
            # que o texto do status não se desloque conforme o tamanho do valor --
            # a coluna da esquerda (nome/subtítulo) absorve o espaço restante.
            controles_linha[0].expand = True
            controles_linha[1].width = 92

            if acao_rapida_pagamento:
                # Ação rápida em "Suas contas": reutiliza database.marcar_conta_como_paga
                # (mesma função e mesma validação já usada no detalhe -- RF06/5.10), sem
                # pedir data -- a data efetiva é sempre hoje aqui, exatamente como o botão
                # "Marcar como paga" do detalhe já faz. Escolher outra data continua sendo
                # uma ação separada, disponível em Editar quando a conta já está paga.
                if conta["status"] == "pago":
                    # Toggle: reverter pelo quick-pay reaproveita
                    # database.marcar_conta_como_pendente (mesma função de Editar) --
                    # nenhuma regra nova. atualizar_dados() recarrega a lista pela
                    # mesma listagem de sempre, então Pendente/Atrasado é recalculado
                    # pela lógica já existente (data de vencimento vs. hoje), não por
                    # um cálculo paralelo aqui.
                    def marcar_como_pendente_rapido(e):
                        database.marcar_conta_como_pendente(conta["id"])
                        atualizar_dados()

                    icone_pagamento = ft.IconButton(
                        icon=ft.Icons.CHECK_CIRCLE,
                        icon_color="#39D67C",
                        icon_size=22,
                        tooltip="Marcar como pendente",
                        on_click=marcar_como_pendente_rapido,
                    )
                else:
                    def marcar_como_paga_rapido(e):
                        database.marcar_conta_como_paga(conta["id"])
                        atualizar_dados()

                    icone_pagamento = ft.IconButton(
                        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                        icon_color="#888780",
                        icon_size=22,
                        tooltip="Marcar como paga",
                        on_click=marcar_como_paga_rapido,
                    )
                controles_linha.append(
                    ft.Container(width=40, alignment=ft.Alignment.CENTER, content=icone_pagamento)
                )

            return ft.Container(
                bgcolor="white",
                border_radius=10,
                padding=12,
                border=ft.Border(left=ft.BorderSide(4, cor)),
                on_click=lambda e, c=conta: abrir_detalhe_conta(c),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=controles_linha,
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
            # RF05 (5.15): título da lista acompanha o mês selecionado no
            # seletor -- "Suas contas de setembro" -- sem alterar texto_mes
            # (seletor continua "Setembro 2026", tela separada).
            titulo_contas.value = f"Suas contas de {MESES_PT[mes_atual[1] - 1].lower()}"
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
                    lista_contas.controls.append(
                        linha_conta(c, categorias.get(c["categoria_id"], ""), acao_rapida_pagamento=True)
                    )

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
    #  FORMULÁRIO COMPARTILHADO DE CATEGORIA (RF14/RF18)
    #  Usado pela tela Categorias, por Nova Conta e por Editar
    #  Conta ("+ Nova categoria") -- uma única implementação,
    #  parametrizada pelo callback ao_salvar.
    # ======================================================
    def abrir_dialogo_categoria(cat=None, ao_salvar=None):
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

        # Melhoria de UX pós-Bloco 1: seletor geral de emojis, sempre visível
        # (com ou sem sugestões para o nome digitado) -- usa só ft.GridView,
        # recurso nativo do Flet, sem lib externa. Reaproveita o mesmo
        # mecanismo de seleção das sugestões (emoji_sugerido_selecionado +
        # montar_sugestoes_emoji) para manter a borda de destaque coerente
        # caso o emoji escolhido aqui coincida com uma sugestão.
        def escolher_emoji_geral(emoji):
            campo_icone.value = emoji
            emoji_sugerido_selecionado["valor"] = emoji
            montar_sugestoes_emoji()
            page.pop_dialog()
            page.update()

        def abrir_seletor_emoji_geral(e):
            # Catálogo próprio do Sino em 20 grupos (GRUPOS_EMOJI_CATEGORIA,
            # topo do arquivo) -- esta função só renderiza a partir dele, sem
            # nenhum emoji hardcoded aqui. Só um grupo expandido por vez
            # (grupo_expandido guarda um único índice ou None), mesmo padrão
            # de "estado num dict mutável + função de remontagem" já usado
            # em cor_selecionada/montar_paleta acima.
            grupo_expandido = {"indice": None}
            coluna_grupos = ft.Column(spacing=18, scroll=ft.ScrollMode.AUTO, height=420, width=300)

            def celula_emoji(emoji):
                return ft.Container(
                    content=ft.Text(emoji, size=17),
                    width=34,
                    height=34,
                    border_radius=8,
                    alignment=ft.Alignment.CENTER,
                    on_click=lambda ev, em=emoji: escolher_emoji_geral(em),
                )

            def alternar_grupo(indice):
                grupo_expandido["indice"] = None if grupo_expandido["indice"] == indice else indice
                montar_grupos()
                page.update()

            def construir_grupo(indice, dados):
                expandido = grupo_expandido["indice"] == indice

                linha_principais = ft.Row(
                    spacing=6, run_spacing=6, wrap=True,
                    controls=[celula_emoji(emoji) for emoji in dados["principais"]] + [
                        ft.Container(
                            content=ft.Icon(
                                ft.Icons.REMOVE if expandido else ft.Icons.ADD,
                                size=16, color="#888780",
                            ),
                            width=34, height=34, border_radius=8,
                            alignment=ft.Alignment.CENTER,
                            tooltip="Recolher" if expandido else "Mais emojis deste grupo",
                            on_click=lambda ev, i=indice: alternar_grupo(i),
                        )
                    ],
                )

                conteudo = [linha_principais]
                if expandido:
                    conteudo.append(
                        ft.Container(
                            padding=ft.Padding(0, 10, 0, 0),
                            content=ft.Row(
                                spacing=6, run_spacing=6, wrap=True,
                                controls=[celula_emoji(emoji) for emoji in dados["adicionais"]],
                            ),
                        )
                    )

                # Contorno fino com o nome do grupo integrado à borda, no
                # mesmo espírito visual do label flutuante dos campos do
                # Sino (ex.: "Categoria") -- Stack com clip NONE para o
                # rótulo poder "recortar" a linha superior sem ser cortado.
                caixa = ft.Container(
                    border=ft.Border.all(1, "#E5E4DE"),
                    border_radius=8,
                    padding=ft.Padding(12, 16, 12, 12),
                    content=ft.Column(spacing=0, controls=conteudo),
                )
                rotulo = ft.Container(
                    content=ft.Text(dados["nome"], size=11, color="#888780"),
                    bgcolor="white",
                    padding=ft.Padding(4, 0, 4, 0),
                    left=10,
                    top=-8,
                )
                return ft.Container(
                    margin=ft.Margin(0, 6, 0, 0),
                    content=ft.Stack(controls=[caixa, rotulo], clip_behavior=ft.ClipBehavior.NONE),
                )

            def montar_grupos():
                coluna_grupos.controls.clear()
                for indice, dados in enumerate(GRUPOS_EMOJI_CATEGORIA):
                    coluna_grupos.controls.append(construir_grupo(indice, dados))

            montar_grupos()

            dialogo_emoji = ft.AlertDialog(
                modal=True,
                title=ft.Text("Escolher emoji"),
                content=coluna_grupos,
                actions=[
                    ft.TextButton(content="Fechar", on_click=lambda ev: page.pop_dialog()),
                ],
            )
            page.show_dialog(dialogo_emoji)

        botao_mais_emojis = ft.TextButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=16, color="#1D9E75"),
                    ft.Text("Mais emojis", size=12, color="#1D9E75"),
                ],
                spacing=4,
                tight=True,
            ),
            on_click=abrir_seletor_emoji_geral,
        )

        # RF18/5.13 (Fase 3.11; revisado pós-Bloco 1): paleta já existente em
        # database.py -- nenhuma cor nova é inventada aqui. Cores já usadas
        # por OUTRA categoria deste usuário deixam de ser oferecidas como
        # opção (em vez de aparecerem esmaecidas/desabilitadas), para não dar
        # a impressão de disponibilidade -- a regra de unicidade em si
        # continua vivendo inteiramente no db.py, isto é só a apresentação.
        categorias_do_usuario = database.listar_categorias(usuario_atual["id"])
        cores_em_uso = {
            c["cor"] for c in categorias_do_usuario
            if c["cor"] and (cat is None or c["id"] != cat["id"])
        }
        cor_selecionada = {"valor": cat["cor"] if cat and cat.get("cor") else None}

        linha_cores = ft.Row(spacing=8, run_spacing=8, wrap=True, width=280)

        def montar_paleta():
            linha_cores.controls.clear()
            cores_disponiveis = [
                cor for cor in database.PALETA_CORES_CATEGORIAS
                if cor not in cores_em_uso
            ]
            # Caso de borda (diagnóstico prévio): a cor já pertencente à
            # categoria em edição deve continuar visível e selecionável mesmo
            # se, por uma futura revisão de PALETA_CORES_CATEGORIAS, ela não
            # fizer mais parte da paleta vigente.
            if cor_selecionada["valor"] and cor_selecionada["valor"] not in cores_disponiveis:
                cores_disponiveis.append(cor_selecionada["valor"])
            for cor in cores_disponiveis:
                selecionada = cor_selecionada["valor"] == cor
                linha_cores.controls.append(
                    ft.Container(
                        width=28,
                        height=28,
                        border_radius=14,
                        bgcolor=cor,
                        border=ft.Border.all(2, "#0B1410") if selecionada else None,
                        on_click=lambda e, c=cor: selecionar_cor(c),
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

            # Segunda barreira do limite de 30 categorias -- só para
            # CRIAÇÃO (cat is None); nunca bloqueia a edição de uma
            # categoria já existente, mesmo com o limite atingido. Cobre o
            # caso do limite ter sido alcançado por outra via entre a
            # abertura do diálogo e o clique em Salvar.
            if not cat:
                total_categorias = len(database.listar_categorias(usuario_atual["id"]))
                if total_categorias >= database.LIMITE_CATEGORIAS_POR_USUARIO:
                    erro.value = (
                        f"Você atingiu o limite máximo de "
                        f"{database.LIMITE_CATEGORIAS_POR_USUARIO} categorias."
                    )
                    page.update()
                    return

            icone = campo_icone.value.strip() if campo_icone.value else None
            cor = cor_selecionada["valor"]

            try:
                if cat:
                    database.editar_categoria(usuario_atual["id"], cat["id"], nome=nome, icone=icone, cor=cor)
                    categoria_id_resultante = cat["id"]
                else:
                    categoria_id_resultante = database.criar_categoria(usuario_atual["id"], nome, icone, cor)
            except ValueError as erro_valor:
                if "cor" in str(erro_valor):
                    erro.value = "Essa cor já está em uso por outra categoria sua. Escolha outra."
                else:
                    # Defesa técnica de database.py (limite ou paleta
                    # esgotada fora do fluxo normal da UI) -- mesma
                    # mensagem apresentada ao usuário, para consistência.
                    erro.value = (
                        f"Você atingiu o limite máximo de "
                        f"{database.LIMITE_CATEGORIAS_POR_USUARIO} categorias."
                    )
                page.update()
                return

            page.pop_dialog()
            # Callback explícito em vez de um "atualizar_lista()" fixo -- é o
            # que permite este mesmo formulário ser reutilizado pela tela
            # Categorias, por Nova Conta e por Editar Conta, cada um
            # decidindo o que fazer com o id resultante (recarregar a lista,
            # ou recarregar+selecionar a categoria no seletor da conta).
            if ao_salvar:
                ao_salvar(categoria_id_resultante)

        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar categoria" if cat else "Nova categoria"),
            content=ft.Column(
                controls=[
                    campo_nome,
                    campo_icone,
                    bloco_sugestoes_emoji,
                    botao_mais_emojis,
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

    def mostrar_limite_categorias():
        dialogo_limite = ft.AlertDialog(
            modal=True,
            title=ft.Text("Limite atingido"),
            content=ft.Text(
                f"Você atingiu o limite máximo de "
                f"{database.LIMITE_CATEGORIAS_POR_USUARIO} categorias."
            ),
            actions=[
                ft.Button(content="Entendi", bgcolor="#1D9E75", color="white",
                          on_click=lambda e: page.pop_dialog()),
            ],
        )
        page.show_dialog(dialogo_limite)

    def ponto_cor_categoria(cor):
        return ft.Container(width=10, height=10, border_radius=5, bgcolor=cor or "#E5E4DE")

    # RF04/RF07 (5.11) + "+ Nova categoria": função reutilizável para montar
    # as opções do seletor de categoria de uma conta -- usada tanto por Nova
    # Conta quanto por Editar Conta, e remontada sempre que a lista de
    # categorias mudar (ex.: depois de criar uma categoria sem sair da
    # tela). SENTINELA_NOVA_CATEGORIA nunca colide com um categoria_id real
    # (sempre str(int)) nem com "" (Sem categoria).
    def montar_opcoes_categoria():
        categorias_atuais = database.listar_categorias(usuario_atual["id"])
        return (
            [ft.dropdown.Option(key="", text="Sem categoria")]
            + [
                ft.dropdown.Option(
                    key=str(c["id"]),
                    text=f"{c['icone'] + ' ' if c['icone'] else ''}{c['nome']}",
                    leading_icon=ponto_cor_categoria(c["cor"]),
                )
                for c in categorias_atuais
            ]
            + [
                ft.dropdown.Option(
                    key=SENTINELA_NOVA_CATEGORIA, text="+ Nova categoria",
                    leading_icon=ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, color="#1D9E75", size=16),
                )
            ]
        )

    def abrir_criacao_categoria(ao_salvar):
        # Checagem de limite ANTES de abrir o formulário (5.11) -- reaproveitada
        # por qualquer ponto de entrada de "+ Nova categoria" (Categorias, Nova
        # Conta, Editar Conta), preservando a mesma "primeira barreira" que já
        # existia só para a tela Categorias: o usuário nem chega a ver a grade
        # de cores/emoji quando o limite já foi atingido, só a mensagem de
        # limite. A segunda barreira (dentro de abrir_dialogo_categoria/salvar)
        # continua intacta para o caso de o limite ser atingido por outra via
        # entre a abertura do formulário e o clique em Salvar.
        total_categorias = len(database.listar_categorias(usuario_atual["id"]))
        if total_categorias >= database.LIMITE_CATEGORIAS_POR_USUARIO:
            mostrar_limite_categorias()
            return
        abrir_dialogo_categoria(None, ao_salvar=ao_salvar)

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
                                              on_click=lambda e, c=cat: abrir_dialogo_categoria(
                                                  c, ao_salvar=lambda categoria_id: atualizar_lista())),
                                ft.IconButton(icon=ft.Icons.DELETE, icon_size=18, icon_color="#A32D2D",
                                              on_click=lambda e, c=cat: confirmar_exclusao(c)),
                            ]
                        ),
                    ],
                ),
            )

        def mostrar_erro_exclusao_categoria(cat):
            dialogo_erro = ft.AlertDialog(
                modal=True,
                title=ft.Text("Não foi possível excluir"),
                content=ft.Text(f"Não foi possível excluir '{cat['nome']}'."),
                actions=[
                    ft.Button(content="Entendi", bgcolor="#1D9E75", color="white",
                              on_click=lambda e: page.pop_dialog()),
                ],
            )
            page.show_dialog(dialogo_erro)

        def confirmar_exclusao(cat):
            def excluir(e):
                page.pop_dialog()
                try:
                    database.excluir_categoria(usuario_atual["id"], cat["id"])
                except Exception:
                    mostrar_erro_exclusao_categoria(cat)
                    return
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

        def ao_clicar_nova_categoria(e):
            # Checagem de limite + abertura do formulário agora vivem no
            # helper compartilhado abrir_criacao_categoria (promovido para
            # main(), reaproveitado também por Nova Conta/Editar Conta).
            abrir_criacao_categoria(ao_salvar=lambda categoria_id: atualizar_lista())

        cabecalho = ft.Container(
            bgcolor="#0B1410",
            padding=ft.Padding(20, 40, 20, 20),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Categorias", size=20, weight=ft.FontWeight.BOLD, color="white"),
                    ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color="#39D67C", icon_size=28,
                                  on_click=ao_clicar_nova_categoria),
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

        campo_categoria = ft.Dropdown(
            label="Categoria",
            value=str(categoria_pre_selecionada) if categoria_pre_selecionada else "",
            options=montar_opcoes_categoria(), color="#0B1410",
        )
        ultima_categoria_valida = {"valor": campo_categoria.value}

        def ao_mudar_categoria(e):
            if campo_categoria.value != SENTINELA_NOVA_CATEGORIA:
                ultima_categoria_valida["valor"] = campo_categoria.value
                return

            # "+ Nova categoria": nunca deixa a sentinela como valor
            # selecionado -- restaura a seleção anterior antes de abrir o
            # formulário compartilhado, para que cancelar a criação não
            # deixe o Dropdown "preso" numa opção que não é uma categoria.
            campo_categoria.value = ultima_categoria_valida["valor"]
            page.update()

            def ao_criar_categoria(categoria_id):
                campo_categoria.options = montar_opcoes_categoria()
                campo_categoria.value = str(categoria_id)
                ultima_categoria_valida["valor"] = campo_categoria.value
                page.update()

            abrir_criacao_categoria(ao_criar_categoria)

        # Mesma correção de Editar Conta: ft.Dropdown usa `on_select`, não
        # `on_change` (Flet 0.86.5 não declara esse campo em Dropdown).
        campo_categoria.on_select = ao_mudar_categoria

        # RF10: tipo de conta -- Única (avulsa), Mensal ou Anual (recorrentes).
        tipo_selecionado = {"valor": "unica"}

        # RF10/5.18: término opcional, escolhido pelo usuário -- "Sem data de
        # término" começa DESATIVADO (o término fica visível por padrão); quando
        # ativado, mostra o seletor visual de mês/ano (não mais campo de texto).
        sem_termino = ft.Switch(value=False, active_color="#1D9E75")

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
