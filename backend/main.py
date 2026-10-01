"""
main.py — App do Sino em Flet, conectado ao banco SQLite.
Tela de login/cadastro + tela de Categorias (CRUD).
"""

import os
import re
import sys
import traceback
from calendar import monthrange
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database"))

import flet as ft
import flet_charts as fch
import db as database
import aviso_sonoro
import cores as modulo_cores
import documentos
import limites

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
                               recorrencia_data_termino=None,
                               descricao_antiga=None, descricao_nova=None):
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
    quando há também alterações que cabem na frase principal.

    Descrição (5.22), comparada já normalizada: alterar entra na frase
    principal ("a descrição", sem repetir o texto); adicionar e remover
    viram frases à parte, como a categoria."""
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

    frase_descricao_especial = None
    descricao_antiga = limites.normalizar_descricao(descricao_antiga)
    descricao_nova = limites.normalizar_descricao(descricao_nova)
    if descricao_antiga != descricao_nova:
        if descricao_antiga is not None and descricao_nova is not None:
            partes.append("a descrição")
        elif descricao_antiga is None:
            frase_descricao_especial = "Você adicionou uma descrição."
        else:
            frase_descricao_especial = "Você removeu a descrição."

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
        f for f in (frase_alterou, frase_categoria_especial, frase_descricao_especial,
                    frase_status_especial, frase_recorrencia_especial)
        if f
    ]
    if not frases:
        return None
    return " ".join(frases)


def campos_alterados_edicao(nome_original, nome_novo, valor_original, valor_novo,
                            data_original, data_nova, categoria_original, categoria_nova,
                            descricao_original=None, descricao_nova=None):
    """RF20/5.6 (correção v6.0, Etapa 0): argumentos para
    `database.editar_conta_ocorrencia`/`editar_conta_serie` contendo SOMENTE
    os campos que o usuário realmente alterou -- um campo não alterado nunca
    é enviado, para não redefinir a âncora da série nem sobrescrever
    ocorrências futuras com valores próprios. `data_original`/`data_nova`
    são objetos `date`; categoria `None` = sem categoria (vira
    `remover_categoria=True` quando ela foi removida). Dicionário vazio
    quando nada propagável mudou.

    Descrição (5.22): comparada já normalizada (`limites.normalizar_descricao`)
    -- só espaços nas bordas não contam como alteração. Removida vira
    `remover_descricao=True` (mesmo motivo da categoria: `None` sozinho
    significa "não mexer")."""
    campos = {}
    if nome_novo != nome_original:
        campos["nome"] = nome_novo
    if valor_novo != valor_original:
        campos["valor"] = valor_novo
    if data_nova != data_original:
        campos["data_vencimento"] = data_nova.isoformat()
    if categoria_nova != categoria_original:
        if categoria_nova is None:
            campos["remover_categoria"] = True
        else:
            campos["categoria_id"] = categoria_nova
    descricao_original = limites.normalizar_descricao(descricao_original)
    descricao_nova = limites.normalizar_descricao(descricao_nova)
    if descricao_nova != descricao_original:
        if descricao_nova is None:
            campos["remover_descricao"] = True
        else:
            campos["descricao"] = descricao_nova
    return campos


def erro_de_limite(campo, texto, limite):
    """5.23: mensagem amigável se `texto` passar de `limite` caracteres
    percebidos (`limites.contar_caracteres`); `None` quando está dentro."""
    contagem = limites.contar_caracteres(texto)
    if contagem > limite:
        return limites.mensagem_limite(campo, limite, contagem)
    return None


def erro_de_nova_senha(senha):
    """5.33: mensagem amigável se `senha` não puder ser definida (mesma regra
    de `database.validar_nova_senha`); `None` quando pode. Nunca contém a senha."""
    try:
        database.validar_nova_senha(senha)
    except database.SenhaInvalidaError as erro:
        return str(erro)
    return None


def texto_contador(texto, limite):
    """Contador exibido junto ao campo, por grafemas (ex.: "12/30")."""
    return f"{limites.contar_caracteres(texto)}/{limite}"


def texto_para_limite(campo, texto):
    """Texto como será contado e gravado: descrição normalizada, nomes com strip."""
    if campo == "descricao":
        return limites.normalizar_descricao(texto)
    return (texto or "").strip()


def atualizar_contador_de_limite(controle, campo, limite):
    """5.23: contador pelos grafemas do valor VISÍVEL (bruto, com espaços e
    quebras de linha) -- o mesmo que o bloqueio da digitação usa -- e, se o
    texto que seria gravado (normalizado) passar do limite, a mensagem
    amigável no campo. Nunca altera `controle.value` (P4: nada é cortado)."""
    controle.counter = texto_contador(controle.value, limite)
    controle.error = erro_de_limite(campo, texto_para_limite(campo, controle.value), limite)


MENSAGEM_LIMITE_ATINGIDO = "Limite atingido"


def edicao_dentro_do_limite(anterior, novo, limite):
    """
    5.23: uma edição (digitação, colagem, substituição da seleção) é aceita
    se o valor visível resultante couber no limite ou, num dado antigo que
    já estava acima dele, se REDUZIR a contagem -- apagar ou substituir por
    menos continua possível até o texto se adequar (P4).

    Conta os grafemas do valor bruto do campo, inclusive espaços nas bordas
    e quebras de linha: com o contador em 30/30, qualquer 31º grafema é
    recusado. A normalização (strip) continua valendo ao salvar e na
    persistência, que validam o texto normalizado.
    """
    contagem_nova = limites.contar_caracteres(novo)
    return contagem_nova <= limite or contagem_nova < limites.contar_caracteres(anterior)


def cursor_apos_recusa(anterior, novo):
    """
    Posição do cursor (em unidades UTF-16, como o Flutter conta) ao
    restaurar `anterior` depois de recusar `novo`: onde a edição recusada
    começou (fim do prefixo comum), recuada até a fronteira de grafema mais
    próxima -- o cursor nunca fica no meio de um emoji composto.
    """
    anterior = anterior or ""
    novo = novo or ""
    prefixo = 0
    while prefixo < min(len(anterior), len(novo)) and anterior[prefixo] == novo[prefixo]:
        prefixo += 1
    posicao = 0
    for grafema in limites.grafemas(anterior):
        if posicao + len(grafema) > prefixo:
            break
        posicao += len(grafema)
    return len(anterior[:posicao].encode("utf-16-le")) // 2


class LimiteDoCampo:
    """
    Liga a um TextField o contador por grafemas e o bloqueio do limite
    (5.23). Uma edição que ultrapassaria o limite é recusada inteira: o
    campo volta ao último valor válido (nada é cortado, então um emoji
    composto nunca fica pela metade), o cursor volta para onde a edição
    começou e o campo mostra "Limite atingido". Usado em vez de
    `max_length`, que truncaria o texto colado e um dado antigo acima do
    limite ao editar.

    Cada recusa também pede um som curto a `aviso` (por padrão
    `aviso_sonoro.aviso_limite`, melhor esforço, sem bloquear a interface).
    """

    def __init__(self, controle, campo, limite, ao_mudar=None, aviso=None):
        self.controle = controle
        self.campo = campo
        self.limite = limite
        self.ao_mudar = ao_mudar
        self.aviso = aviso if aviso is not None else aviso_sonoro.aviso_limite
        controle.on_change = self.tratar_mudanca
        self.sincronizar()

    def sincronizar(self):
        """Adota o valor atual do campo como o último válido (abertura do
        formulário ou valor definido pelo código)."""
        self.ultimo_valor = self.controle.value or ""
        self.controle.helper = None
        atualizar_contador_de_limite(self.controle, self.campo, self.limite)

    def tratar_mudanca(self, e):
        novo = self.controle.value or ""
        if edicao_dentro_do_limite(self.ultimo_valor, novo, self.limite):
            self.ultimo_valor = novo
            self.controle.helper = None
            atualizar_contador_de_limite(self.controle, self.campo, self.limite)
            if self.ao_mudar is not None:
                self.ao_mudar(e)
        else:
            cursor = cursor_apos_recusa(self.ultimo_valor, novo)
            self.controle.value = self.ultimo_valor
            self.controle.selection = ft.TextSelection(base_offset=cursor, extent_offset=cursor)
            self.controle.helper = MENSAGEM_LIMITE_ATINGIDO
            atualizar_contador_de_limite(self.controle, self.campo, self.limite)
            self.aviso.tocar()
        e.page.update()


def ligar_contador_de_limite(controle, campo, limite, ao_mudar=None, aviso=None):
    """Contador por grafemas e bloqueio do limite em `controle` (ver
    `LimiteDoCampo`); `ao_mudar` só é chamado para edições aceitas."""
    return LimiteDoCampo(controle, campo, limite, ao_mudar, aviso)


def resumo_do_mes(contas):
    """
    RF12/5.16 (Etapa 3): (total, pago, pendente) das contas do mês. O total
    soma TODAS as contas, independentemente do status -- marcar ou
    desmarcar uma conta como paga só move o valor entre pago e pendente.
    Atrasadas contam como pendentes (e no mês do vencimento).
    """
    pago = sum(c["valor"] for c in contas if c["status"] == "pago")
    pendente = sum(c["valor"] for c in contas if c["status"] != "pago")
    return pago + pendente, pago, pendente


def ordenar_contas_do_mes(contas):
    """Ordem da lista do mês: atrasadas primeiro, depois por vencimento."""
    return sorted(contas, key=lambda c: (0 if c["status"] == "atrasado" else 1, c["data_vencimento"]))


FILTROS_DE_STATUS = (
    ("todas", "Todas"), ("pendentes", "Pendentes"), ("pagas", "Pagas"), ("atrasadas", "Atrasadas"),
)


def filtrar_por_status(contas, filtro):
    """RF09/5.21: filtro da tela Ver status (as contas já são as do mês)."""
    status = {"pendentes": "pendente", "pagas": "pago", "atrasadas": "atrasado"}.get(filtro)
    return list(contas) if status is None else [c for c in contas if c["status"] == status]


TEXTO_NAO_RECORRENTE = "Esta conta não é recorrente."


def identificacao_categoria(categoria):
    """
    Etapa 4 (8.4): como a categoria identifica a conta em Detalhes. `None`
    = "Sem categoria" (cinza, sem emoji nem substituto). Uma categoria sem
    emoji ou sem cor mantém o próprio nome, com apresentação neutra.
    """
    if categoria is None:
        return {"nome": "Sem categoria", "emoji": None, "cor": None, "sem_categoria": True}
    return {"nome": categoria["nome"], "emoji": categoria.get("icone") or None,
            "cor": categoria.get("cor") or None, "sem_categoria": False}


def status_para_detalhes(conta, hoje):
    """
    Etapa 4 (8.4): status e ação de pagamento lado a lado em Detalhes.
    Três status (Atrasado, Pendente, Pago); vencer hoje continua Pendente
    ("Vence hoje" é informação de vencimento, `vence_hoje`).
    """
    vencimento = date.fromisoformat(conta["data_vencimento"])
    if conta["status"] == "pago":
        rotulo = "🟢 Pago"
        if conta.get("data_pagamento"):
            rotulo += f" em {date.fromisoformat(conta['data_pagamento']).strftime('%d/%m/%Y')}"
        return {"status": "pago", "rotulo": rotulo, "acao": "Desmarcar como paga", "vence_hoje": False}
    if conta["status"] == "atrasado":
        return {"status": "atrasado", "rotulo": "🔴 Atrasado", "acao": "Marcar como paga", "vence_hoje": False}
    return {"status": "pendente", "rotulo": "Pendente", "acao": "Marcar como paga",
            "vence_hoje": vencimento == hoje}


def status_ao_desmarcar(conta, hoje):
    """Status de uma conta que volta a ficar em aberto: atrasada se o
    vencimento real já passou, pendente caso contrário (5.10)."""
    return "atrasado" if date.fromisoformat(conta["data_vencimento"]) < hoje else "pendente"


def texto_recorrencia_detalhes(serie_ativa, info_serie):
    """Frase de recorrência: série ativa -> frase contextual; conta única ou
    série encerrada (tratada como avulsa, 5.8) -> TEXTO_NAO_RECORRENTE."""
    if serie_ativa:
        return frase_recorrencia(info_serie["frequencia"], info_serie["data_termino"])
    return TEXTO_NAO_RECORRENTE


def texto_parcela(parcela):
    """(posição, total) -> "Parcela X de Y"; total None -> "Parcela X"."""
    posicao, total = parcela
    return f"Parcela {posicao} de {total}" if total is not None else f"Parcela {posicao}"


MESES_ABREVIADOS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def formatar_percentual(valor):
    """5.28: casa decimal só quando necessária -- 42%, 24,5%, 8,3%."""
    arredondado = round(valor + 0.0, 1)
    if arredondado == int(arredondado):
        return f"{int(arredondado)}%"
    return f"{arredondado:.1f}%".replace(".", ",")


def percentual_de(parte, total):
    return 0.0 if not total else parte / total * 100


def mes_anterior(ano, mes):
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def intervalo_do_periodo(modo, ano, mes=None):
    """(início, fim) ISO do mês ou do ano."""
    if modo == "anual":
        return f"{ano:04d}-01-01", f"{ano:04d}-12-31"
    return f"{ano:04d}-{mes:02d}-01", f"{ano:04d}-{mes:02d}-{monthrange(ano, mes)[1]:02d}"


def rotulo_periodo(modo, ano, mes=None):
    return str(ano) if modo == "anual" else f"{MESES_PT[mes - 1]} de {ano}"


def janela_seis_meses(ano, mes):
    """RF21: o mês (ano, mes) e os cinco anteriores, em ordem."""
    meses = [(ano, mes)]
    while len(meses) < 6:
        meses.insert(0, mes_anterior(*meses[0]))
    return meses


def texto_total_pago(pago, total):
    """5.24: "R$ 2.000,00 de R$ 2.340,00 pagos — 85,5%"."""
    return (f"{formatar_moeda(pago)} de {formatar_moeda(total)} pagos — "
            f"{formatar_percentual(percentual_de(pago, total))}")


def ordenar_distribuicao(itens):
    """RF22: maior valor primeiro; "Sem categoria" sempre por último (5.25)."""
    com_categoria = sorted((i for i in itens if i["categoria_id"] is not None),
                           key=lambda i: (-i["total"], i["nome"].lower()))
    return com_categoria + [i for i in itens if i["categoria_id"] is None]


def comparacao_com_anterior(atual, anterior):
    """
    RF23 (5.29): variação do período em relação ao anterior, pelos totais.
    Retorna {"tipo", "destaque", "complemento"}; `tipo` em aumento, reducao,
    igual, sem_base, sem_gastos.
    """
    diferenca = round(atual - anterior, 2)
    if atual == 0 and anterior == 0:
        return {"tipo": "sem_gastos", "destaque": "Sem gastos nos dois períodos.", "complemento": None}
    if anterior == 0:
        return {"tipo": "sem_base", "destaque": "Não há base de comparação",
                "complemento": f"{formatar_moeda(diferenca)} a mais"}
    if diferenca == 0:
        return {"tipo": "igual", "destaque": "0% — Sem alteração", "complemento": None}
    variacao = formatar_percentual(abs(diferenca) / anterior * 100)
    if diferenca > 0:
        return {"tipo": "aumento", "destaque": f"▲ {variacao}", "complemento": f"{formatar_moeda(diferenca)} a mais"}
    return {"tipo": "reducao", "destaque": f"▼ {variacao}", "complemento": f"{formatar_moeda(-diferenca)} a menos"}


LARGURA_MINIMA_LEGENDA_EM_COLUNAS = 700


def layout_gastos_por_categoria(largura_pagina):
    """
    Etapa 5 (protótipo 10): medidas de "Gastos por categoria". Em janela
    larga, colunas fixas e próximas -- nome (cabe um nome de 30 caracteres
    numa linha), valor e percentual -- e uma rosca grande. Em janela
    estreita, o nome ocupa o espaço livre e quebra linha, e a rosca encolhe
    para caber. Largura desconhecida é tratada como larga.
    """
    if not isinstance(largura_pagina, (int, float)) or largura_pagina >= LARGURA_MINIMA_LEGENDA_EM_COLUNAS:
        return {"largura_nome": 240, "largura_valor": 130, "largura_percentual": 60, "tamanho_rosca": 320,
                "estreita": False}
    return {"largura_nome": None, "largura_valor": 112, "largura_percentual": 56,
            "tamanho_rosca": int(max(200, min(300, largura_pagina - 90))), "estreita": True}


def ano_inicial_anual(anos_com_historico, ano_atual):
    """5.26: o ano atual se tiver contas; senão o mais recente com contas."""
    if not anos_com_historico or ano_atual in anos_com_historico:
        return ano_atual
    return max(anos_com_historico)


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


def preparar_banco_ou_exibir_erro(page, cores=modulo_cores):
    """
    ERS v6.0, Etapas 1, 2b e 8: garante o banco no schema atual (v8) antes de
    qualquer tela que dependa dele (database.preparar_banco: cria, migra
    v5 -> v6 -> v7 -> v8 com backup ou reconhece que já está atualizado). Em caso de falha, o traceback
    completo vai para o terminal, a usuária vê só uma mensagem genérica e o
    retorno False impede que o app siga para o login.

    `cores`: a Paleta da sessão (antes do login é sempre o tema Claro, P8).
    """
    try:
        resultado = database.preparar_banco()
    except Exception:
        print("Sino: falha ao preparar o banco de dados; o app não foi iniciado.", file=sys.stderr)
        traceback.print_exc()
        page.controls.clear()
        page.add(
            ft.Column(
                controls=[
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=cores.texto_erro, size=48),
                    ft.Text(
                        "Não foi possível abrir o Sino",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=cores.texto_principal,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "O Sino encontrou um problema ao preparar seus dados e foi interrompido "
                        "para protegê-los. Nenhuma informação foi apagada. Os detalhes técnicos "
                        "foram registrados no terminal.",
                        size=14,
                        color=cores.texto_secundario,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            )
        )
        return False

    if resultado["situacao"] == "migrado":
        for versao, chave in (("v6", "migracao"), ("v7", "migracao_v7"), ("v8", "migracao_v8")):
            migracao = resultado.get(chave)
            if migracao and migracao.get("executado"):
                print(f"Sino: banco migrado para a {versao}. Backup pré-migração: {migracao['backup']}")
    return True


def tema_flet(tema):
    """
    `ft.Theme` de um tema do Sino (5.36): semente e cores principais da
    identidade verde, para que os controles que usam as cores padrão do
    Flet (diálogos, campos, botões de texto) sigam a paleta daquele tema.
    """
    paleta = modulo_cores.PALETAS[modulo_cores.validar_tema(tema)]
    return ft.Theme(
        color_scheme_seed=paleta["acao_primaria"],
        color_scheme=ft.ColorScheme(
            primary=paleta["acao_primaria"],
            on_primary=paleta["texto_sobre_acao"],
            surface=paleta["fundo_card"],
            on_surface=paleta["texto_principal"],
            on_surface_variant=paleta["texto_secundario"],
            outline=paleta["borda_campo"],
            error=paleta["texto_erro"],
        ),
        # Rede de segurança para diálogos e para o calendário (ft.DatePicker
        # não tem atributos de cor próprios).
        dialog_theme=ft.DialogTheme(
            bgcolor=paleta["fundo_dialogo"],
            title_text_style=ft.TextStyle(color=paleta["texto_principal"], size=20),
            content_text_style=ft.TextStyle(color=paleta["texto_principal"], size=14),
        ),
        date_picker_theme=ft.DatePickerTheme(
            bgcolor=paleta["fundo_dialogo"],
            header_bgcolor=paleta["fundo_dialogo"],
            header_foreground_color=paleta["texto_principal"],
            divider_color=paleta["divisor"],
            today_foreground_color=paleta["acao_primaria"],
            today_border_side=ft.BorderSide(1, paleta["acao_primaria"]),
            cancel_button_style=ft.ButtonStyle(color=paleta["acao_primaria"]),
            confirm_button_style=ft.ButtonStyle(color=paleta["acao_primaria"]),
        ),
    )


class SessaoSino:
    """
    Estado de UMA página do Sino (ERS v6.0, 5.36/5.38): o usuário
    autenticado e a Paleta de cores própria da página. Nada disso é global:
    duas páginas no mesmo processo têm sessões e temas independentes.

    `ao_encerrar` é a função que abre o login (definida por main()).
    """

    MODOS_FLET = {"claro": ft.ThemeMode.LIGHT, "escuro": ft.ThemeMode.DARK}

    def __init__(self, page):
        self.page = page
        self.cores = modulo_cores.Paleta()
        self.usuario = {"id": None, "nome": None}
        self.ao_encerrar = None

    def aplicar_tema(self, tema):
        """Paleta da página, `theme_mode` e fundo; tema inválido não altera nada."""
        self.cores.definir_tema(tema)
        self.page.theme_mode = self.MODOS_FLET[tema]
        self.page.bgcolor = self.cores.fundo_pagina

    def autenticar(self, usuario):
        """
        Após `verificar_login` bem-sucedido: aplica o tema gravado do usuário e
        só então preenche a sessão (um tema inválido não deixa sessão parcial).
        """
        self.aplicar_tema(usuario["tema"])
        self.usuario["id"] = usuario["id"]
        self.usuario["nome"] = usuario["nome"]

    def encerrar(self):
        """
        Sair da conta (5.38): limpa o usuário, fecha os diálogos abertos,
        esvazia o overlay, desliga o `on_resize` da tela anterior, volta ao
        tema Claro (P8) e abre o login. Nenhum dado é removido do banco.
        """
        self.usuario["id"] = None
        self.usuario["nome"] = None
        while self.page.pop_dialog() is not None:
            pass
        self.page.overlay.clear()
        self.page.on_resize = None
        self.aplicar_tema(modulo_cores.TEMA_PADRAO)
        if self.ao_encerrar is not None:
            self.ao_encerrar()


def main(page: ft.Page):
    # Uma sessão (e uma Paleta) por página, antes de qualquer uso de cores.
    sessao = SessaoSino(page)
    cores = sessao.cores
    usuario_atual = sessao.usuario
    aplicar_tema = sessao.aplicar_tema

    # Campos e listas de seleção com as cores da Paleta da sessão (legíveis
    # nos dois temas; no Claro, as mesmas cores que o tema verde já dava).
    def estilo_campo_texto():
        return dict(
            border_color=cores.borda_campo, focused_border_color=cores.acao_primaria,
            cursor_color=cores.acao_primaria,
            label_style=ft.TextStyle(color=cores.texto_secundario),
            hint_style=ft.TextStyle(color=cores.texto_secundario),
            counter_style=ft.TextStyle(color=cores.texto_secundario),
            helper_style=ft.TextStyle(color=cores.texto_secundario),
            error_style=ft.TextStyle(color=cores.texto_erro),
        )

    def estilo_lista():
        return dict(
            border_color=cores.borda_campo, focused_border_color=cores.acao_primaria,
            label_style=ft.TextStyle(color=cores.texto_secundario),
            error_style=ft.TextStyle(color=cores.texto_erro),
            bgcolor=cores.fundo_dialogo,  # fundo do menu aberto
        )

    page.theme = tema_flet("claro")
    page.dark_theme = tema_flet("escuro")
    aplicar_tema(modulo_cores.TEMA_PADRAO)

    page.title = "Sino"
    page.window.width = 380
    page.window.height = 760
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 24

    if not preparar_banco_ou_exibir_erro(page, cores):
        return

    # ======================================================
    #  BARRA DE NAVEGAÇÃO (reutilizável entre as telas)
    # ======================================================
    def barra_navegacao(aba_ativa):
        def item(nome_aba, icone, rotulo, on_click):
            ativa = aba_ativa == nome_aba
            cor = cores.nav_ativo if ativa else cores.nav_inativo
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
            bgcolor=cores.fundo_card,
            border=ft.Border(top=ft.BorderSide(1, cores.borda_suave)),
            content=ft.Row(
                controls=[
                    item("inicio", ft.Icons.HOME, "Início", lambda e: mostrar_tela_principal()),
                    item("categorias", ft.Icons.FOLDER, "Categorias", lambda e: mostrar_tela_categorias()),
                    item("grafico", ft.Icons.BAR_CHART, "Gráfico", lambda e: mostrar_tela_grafico()),
                    item("ajustes", ft.Icons.SETTINGS, "Ajustes", lambda e: mostrar_tela_ajustes()),
                ],
            ),
        )

    # ======================================================
    #  DOCUMENTOS: TERMOS DE USO E POLÍTICA DE PRIVACIDADE
    # ======================================================
    def mostrar_documento(chave, ao_voltar):
        """
        RF15/RF41, 5.37: exibe um documento de `documentos.DOCUMENTOS` dentro
        do Sino, com rolagem e botão Voltar (que chama `ao_voltar`). É a mesma
        tela, com o mesmo texto, no cadastro e em Ajustes; as cores vêm da
        Paleta da sessão (no cadastro, sempre o Claro).
        """
        _, texto = documentos.DOCUMENTOS[chave]
        page.controls.clear()
        page.padding = 0

        estilo_texto = ft.TextStyle(color=cores.texto_principal, size=14)
        folha_de_estilo = ft.MarkdownStyleSheet(
            p_text_style=estilo_texto,
            h1_text_style=ft.TextStyle(color=cores.texto_principal, size=24, weight=ft.FontWeight.BOLD),
            h2_text_style=ft.TextStyle(color=cores.texto_principal, size=17, weight=ft.FontWeight.BOLD),
            strong_text_style=ft.TextStyle(color=cores.texto_principal, weight=ft.FontWeight.BOLD),
            em_text_style=ft.TextStyle(color=cores.texto_principal, italic=True),
            a_text_style=estilo_texto,
            list_bullet_text_style=estilo_texto,
            code_text_style=ft.TextStyle(color=cores.texto_principal, bgcolor=cores.fundo_pagina, size=13,
                                         font_family="monospace"),
        )
        documento = ft.Markdown(value=texto, selectable=True, md_style_sheet=folha_de_estilo)

        barra_topo = ft.Container(
            padding=ft.Padding(8, 12, 8, 4),
            content=ft.Row(controls=[
                ft.TextButton(
                    content="Voltar", icon=ft.Icons.ARROW_BACK, on_click=lambda e: ao_voltar(),
                    style=ft.ButtonStyle(color=cores.texto_principal, icon_color=cores.acao_primaria),
                ),
            ]),
        )
        conteudo = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, controls=[
            ft.Container(padding=ft.Padding(16, 4, 16, 24), content=ft.ResponsiveRow(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[ft.Container(
                    data=f"documento_{chave}", col={"xs": 12, "md": 10, "xl": 8},
                    bgcolor=cores.fundo_card, border_radius=16, padding=20,
                    border=ft.Border.all(1, cores.borda_suave), content=documento,
                )],
            )),
        ])
        page.add(ft.Column(expand=True, controls=[barra_topo, conteudo]))
        page.update()

    # ======================================================
    #  TELA DE LOGIN / CADASTRO
    # ======================================================
    def mostrar_tela_login():
        aplicar_tema(modulo_cores.TEMA_PADRAO)  # autenticação sempre em Claro (5.36, P8)
        page.controls.clear()
        page.padding = 24
        modo_cadastro = [False]

        logo = ft.Container(
            content=ft.Text("$ino", size=28, weight=ft.FontWeight.BOLD, color=cores.texto_marca),
            bgcolor=cores.fundo_marca,
            width=80,
            height=80,
            border_radius=40,
            alignment=ft.Alignment.CENTER,
        )

        titulo = ft.Text("Bem-vindo de volta", size=20, weight=ft.FontWeight.BOLD, color=cores.texto_principal)
        subtitulo = ft.Text("Suas contas, sob controle.", size=13, color=cores.texto_secundario)

        campo_nome = ft.TextField(label="Nome completo", hint_text="Seu nome", width=330, visible=False,
                                   color=cores.texto_principal)
        limite_nome_cadastro = ligar_contador_de_limite(campo_nome, "nome_usuario", limites.LIMITE_NOME_USUARIO)
        campo_email = ft.TextField(label="E-mail", hint_text="voce@email.com", width=330, color=cores.texto_principal)
        campo_senha = ft.TextField(label="Senha", hint_text="********", password=True,
                                    can_reveal_password=True, width=330, color=cores.texto_principal)
        # RF15: aceite dos Termos de Uso/Política de Privacidade, exigido só no
        # Cadastro (mesmo padrão de visibilidade de campo_nome -- alternado em
        # alternar_modo, resetado a cada troca de modo).
        campo_aceite_termos = ft.Checkbox(
            label="Li e aceito os Termos de Uso e a Política de Privacidade.",
            value=False, visible=False, width=330,
        )
        mensagem = ft.Text(value="", color=cores.texto_sucesso)

        # RF15/5.37: os documentos podem ser lidos antes do aceite. A tela do
        # formulário é guardada e reexibida ao voltar, com os campos (e o
        # aceite) exatamente como estavam; ler não marca o aceite.
        def voltar_ao_formulario():
            page.controls.clear()
            page.padding = 24
            page.add(tela_autenticacao)
            page.update()

        def link_documento(chave):
            rotulo, _ = documentos.DOCUMENTOS[chave]
            return ft.TextButton(
                content=f"Ler {rotulo}", on_click=lambda e: mostrar_documento(chave, voltar_ao_formulario),
                style=ft.ButtonStyle(color=cores.acao_primaria),
            )

        links_documentos = ft.Row(
            visible=False, width=330, wrap=True, spacing=0, alignment=ft.MainAxisAlignment.CENTER,
            controls=[link_documento("termos"), link_documento("politica")],
        )

        def ao_clicar_botao_principal(e):
            # A senha nunca é transformada (5.33): sem strip nem limite máximo;
            # uma nova senha com espaços é recusada como veio. No login, as
            # regras de nova senha não se aplicam (senhas anteriores, mesmo
            # curtas ou com espaços, continuam entrando, CT82).
            email = campo_email.value.strip() if campo_email.value else ""
            senha = campo_senha.value if campo_senha.value else ""

            if modo_cadastro[0]:
                nome = campo_nome.value.strip() if campo_nome.value else ""
                erro_nome = erro_de_limite("nome_usuario", nome, limites.LIMITE_NOME_USUARIO)
                erro_senha = erro_de_nova_senha(senha)
                if not nome or not email or not senha:
                    mensagem.value = "Preencha nome, e-mail e senha."
                    mensagem.color = cores.texto_erro
                elif erro_nome:
                    mensagem.value = erro_nome
                    mensagem.color = cores.texto_erro
                elif erro_senha:
                    # 5.33/RF37: mesma regra do banco (database.validar_nova_senha);
                    # campos e aceite ficam como estão para a correção.
                    mensagem.value = erro_senha
                    mensagem.color = cores.texto_erro
                elif not campo_aceite_termos.value:
                    # RF15: aceite é obrigatório para prosseguir -- criar_usuario
                    # nem chega a ser chamada sem ele.
                    mensagem.value = (
                        "Você precisa aceitar os Termos de Uso e a Política de "
                        "Privacidade para criar sua conta."
                    )
                    mensagem.color = cores.texto_erro
                else:
                    sucesso, texto = database.criar_usuario(nome, email, senha, aceite_termos=True)
                    mensagem.value = texto
                    mensagem.color = cores.texto_sucesso if sucesso else cores.texto_erro
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
                        mensagem.color = cores.texto_sucesso
                        page.update()
            else:
                if not email or not senha:
                    mensagem.value = "Preencha e-mail e senha."
                    mensagem.color = cores.texto_erro
                else:
                    usuario = database.verificar_login(email, senha)
                    if usuario:
                        sessao.autenticar(usuario)  # tema do usuário (5.36) + sessão
                        mostrar_tela_principal()
                        return
                    else:
                        mensagem.value = "E-mail ou senha incorretos."
                        mensagem.color = cores.texto_erro

            page.update()

        botao_principal = ft.Button(
            content="Entrar",
            width=330,
            bgcolor=cores.acao_primaria,
            color=cores.texto_sobre_acao,
            on_click=ao_clicar_botao_principal,
        )

        def alternar_modo(e):
            modo_cadastro[0] = not modo_cadastro[0]
            campo_nome.value = ""
            limite_nome_cadastro.sincronizar()
            campo_email.value = ""
            campo_senha.value = ""
            campo_aceite_termos.value = False
            if modo_cadastro[0]:
                titulo.value = "Crie sua conta"
                subtitulo.value = "Leva menos de um minuto"
                campo_senha.helper = f"Mínimo de {database.SENHA_MINIMO} caracteres"
                campo_nome.visible = True
                links_documentos.visible = True
                campo_aceite_termos.visible = True
                botao_principal.content = "Criar conta"
                texto_alternar.content = "Já tem conta? Entrar"
            else:
                titulo.value = "Bem-vindo de volta"
                subtitulo.value = "Suas contas, sob controle."
                campo_senha.helper = None
                campo_nome.visible = False
                links_documentos.visible = False
                campo_aceite_termos.visible = False
                botao_principal.content = "Entrar"
                texto_alternar.content = "Não tem conta? Criar conta"
            mensagem.value = ""
            page.update()

        texto_alternar = ft.TextButton(content="Não tem conta? Criar conta", on_click=alternar_modo)

        tela_autenticacao = ft.Column(
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
                links_documentos,
                campo_aceite_termos,
                ft.Container(height=8),
                botao_principal,
                mensagem,
                texto_alternar,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        page.add(tela_autenticacao)
        page.update()

    # ======================================================
    #  TELA PRINCIPAL
    # ======================================================
    def mostrar_tela_principal(mes_inicial=None):
        """`mes_inicial` = (ano, mes) a manter selecionado (ex.: ao voltar da
        edição aberta pelo lápis); sem ele, o mês atual."""
        page.controls.clear()
        page.padding = 0

        hoje = date.today()
        mes_atual = list(mes_inicial) if mes_inicial else [hoje.year, hoje.month]

        avatar = ft.Container(
            content=ft.Text("$", size=18, weight=ft.FontWeight.BOLD, color=cores.texto_marca),
            bgcolor=cores.fundo_marca,
            width=40,
            height=40,
            border_radius=20,
            alignment=ft.Alignment.CENTER,
        )

        nome_usuario = ft.Text(usuario_atual["nome"] or "", size=16, weight=ft.FontWeight.BOLD, color=cores.texto_principal)

        sino = ft.Stack(
            controls=[
                ft.Icon(ft.Icons.NOTIFICATIONS_NONE, size=24, color=cores.texto_principal),
                ft.Container(width=8, height=8, bgcolor=cores.indicador_notificacao, border_radius=4, right=0, top=0),
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
                                ft.Text("Olá,", size=13, color=cores.texto_secundario),
                                nome_usuario,
                            ],
                            spacing=0,
                        ),
                    ]
                ),
                sino,
            ],
        )

        texto_mes = ft.Text("", size=14, weight=ft.FontWeight.BOLD, color=cores.texto_principal)

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
                ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, icon_size=18, on_click=lambda e: mudar_mes(-1),
                              icon_color=cores.texto_secundario),
                texto_mes,
                ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, icon_size=18, on_click=lambda e: mudar_mes(1),
                              icon_color=cores.texto_secundario),
            ],
        )

        valor_total = ft.Text("R$ 0,00", size=26, weight=ft.FontWeight.BOLD, color=cores.texto_card_total)
        valor_pago = ft.Text("pago R$ 0,00", size=12, color=cores.total_pago)
        valor_pendente = ft.Text("pendente R$ 0,00", size=12, color=cores.total_pendente)

        # RF12/5.16 (Etapa 3): sem filtros -- o total é sempre a soma de todas
        # as contas do mês; pago/pendente continuam como informação complementar.
        card_total = ft.Container(
            bgcolor=cores.fundo_card_total,
            border_radius=16,
            padding=16,
            content=ft.Column(
                controls=[
                    ft.Text("Total do mês", size=12, color=cores.texto_secundario_card_total),
                    valor_total,
                    ft.Container(height=8),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(controls=[ft.Icon(ft.Icons.CHECK_CIRCLE, size=14, color=cores.total_pago), valor_pago]),
                            ft.Row(controls=[ft.Icon(ft.Icons.SCHEDULE, size=14, color=cores.total_pendente), valor_pendente]),
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
                bloco_atrasadas.bgcolor = cores.alerta_atraso_fundo
                bloco_atrasadas.border_radius = 10
                bloco_atrasadas.padding = 12
                bloco_atrasadas.content = ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.ERROR_OUTLINE, size=18, color=cores.alerta_atraso_texto),
                                ft.Container(width=8),
                                ft.Text("Você possui contas em atraso!", size=13,
                                         weight=ft.FontWeight.BOLD, color=cores.alerta_atraso_texto),
                            ],
                        ),
                        ft.Container(
                            content=ft.Text("Ver essas contas", size=12, weight=ft.FontWeight.BOLD,
                                             color=cores.alerta_atraso_texto),
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
                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=16, color=cores.texto_sucesso),
                        ft.Container(width=6),
                        ft.Text("Suas contas estão em dia!", size=13,
                                 weight=ft.FontWeight.BOLD, color=cores.texto_sucesso),
                    ],
                )

        def ao_clicar_ver_status(e):
            ano_mes_atual = f"{mes_atual[0]:04d}-{mes_atual[1]:02d}"
            mostrar_tela_ver_status(ano_mes_atual)

        titulo_contas = ft.Text("Suas contas", size=15, weight=ft.FontWeight.BOLD, color=cores.texto_principal)

        # RF09/5.21 (Etapa 3): "Ver status" substitui "Ver todas", ao lado do título.
        cabecalho_contas = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                titulo_contas,
                ft.Container(
                    content=ft.Text("Ver status", size=13, color=cores.acao_primaria),
                    on_click=ao_clicar_ver_status,
                ),
            ],
        )

        lista_contas = ft.Column(controls=[], spacing=8)

        def abrir_detalhe_conta(conta, abrir_em_edicao=False):
            """
            Detalhes da conta; `abrir_em_edicao=True` (lápis da Tela
            Principal, RF30) abre direto o formulário Editar. Voltar dos
            Detalhes, exclusão concluída e o "Entendi" depois de salvar
            retornam à Tela Principal no mês de referência (`mes_atual`). No
            formulário, Voltar/Cancelar retornam à Tela Principal (mesmo mês)
            quando aberto pelo lápis, e aos Detalhes quando aberto por eles.
            """
            page.controls.clear()
            page.overlay.clear()
            page.padding = 0

            def voltar_do_formulario():
                if abrir_em_edicao:
                    mostrar_tela_principal(tuple(mes_atual))
                else:
                    mostrar_visualizacao()

            lista_categorias = database.listar_categorias(usuario_atual["id"])
            categorias_atuais = {c["id"]: c["nome"] for c in lista_categorias}
            categoria_da_conta = next((c for c in lista_categorias if c["id"] == conta.get("categoria_id")), None)

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
                    border=ft.Border.all(1, cores.borda_campo),
                    border_radius=8,
                    padding=ft.Padding(12, 14, 12, 10),
                    alignment=ft.Alignment.TOP_LEFT,
                    content=ft.Column(spacing=8, controls=controles),
                )
                rotulo_flutuante = ft.Container(
                    content=ft.Text(rotulo, size=12, color=cores.texto_principal),
                    bgcolor=cores.fundo_pagina,
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
                controles = [ft.Text(texto_info, size=14, color=cores.texto_principal)]
                for acao in acoes:
                    controles.append(ft.Container(width=1, height=18, bgcolor=cores.divisor))
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
                            title=ft.Text("Data inválida", color=cores.texto_principal),
                            content=ft.Text("A data de pagamento não pode ser no futuro.", color=cores.texto_principal),
                            actions=[
                                ft.Button(content="Entendi", bgcolor=cores.acao_primaria, color=cores.texto_sobre_acao,
                                          on_click=lambda e: page.pop_dialog()),
                            ],
                            bgcolor=cores.fundo_dialogo,
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
                            style=ft.ButtonStyle(color=cores.acao_primaria),
                        ),
                        ft.TextButton(
                            content="Marcar como pendente",
                            on_click=marcar_como_pendente_edicao,
                            style=ft.ButtonStyle(color=cores.acao_primaria),
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
                        ft.TextButton(content="Marcar como paga", on_click=marcar_como_paga_edicao,
                                      style=ft.ButtonStyle(color=cores.acao_primaria)),
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
                            style=ft.ButtonStyle(color=cores.acao_primaria),
                        ),
                        ft.TextButton(
                            content="Encerrar recorrência",
                            on_click=lambda e: mostrar_dialogo_encerrar_recorrencia(),
                            style=ft.ButtonStyle(color=cores.acao_primaria),
                        ),
                    ]
                else:
                    texto_recorrencia = TEXTO_NAO_RECORRENTE
                    acoes_recorrencia = [
                        ft.TextButton(
                            content="Transformar em recorrente",
                            on_click=lambda e: mostrar_dialogo_transformar_recorrente(),
                            style=ft.ButtonStyle(color=cores.acao_primaria),
                        ),
                    ]

                if acao_pendente is not None:
                    acoes_recorrencia.append(
                        ft.TextButton(
                            content="Desfazer esta alteração",
                            on_click=lambda e: limpar_rascunho_recorrencia(),
                            style=ft.ButtonStyle(color=cores.acao_primaria),
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
                                                 color=cores.chip_ativo_texto if ativo else cores.chip_inativo_texto),
                                bgcolor=cores.chip_ativo_fundo if ativo else cores.chip_inativo_fundo,
                                border=None if ativo else ft.Border.all(1, cores.borda_suave),
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
                # Etapa 4 (ERS 8.4, protótipo 13): identificação pela categoria
                # (emoji e cor), status ao lado da ação de pagamento perto do
                # topo, grade Valor/Vencimento/Categoria/Parcela, Recorrência,
                # Descrição (só quando preenchida) e Editar/Excluir no rodapé.
                page.overlay.clear()
                hoje = date.today()
                data_venc = date.fromisoformat(conta["data_vencimento"])
                status = status_para_detalhes(conta, hoje)
                categoria = identificacao_categoria(categoria_da_conta)

                def marcar_como_paga_detalhes(e):
                    # RF06/RF24: só esta ocorrência; status nunca tem escopo de série.
                    database.marcar_conta_como_paga(conta["id"])
                    conta["status"] = "pago"
                    conta["data_pagamento"] = hoje.isoformat()
                    mostrar_visualizacao()

                def desmarcar_como_paga_detalhes(e):
                    # 8.4/CT56: volta a ficar em aberto só esta ocorrência, sem
                    # data de pagamento; pendente ou atrasada pelo vencimento real.
                    database.marcar_conta_como_pendente(conta["id"])
                    conta["status"] = status_ao_desmarcar(conta, hoje)
                    conta["data_pagamento"] = None
                    mostrar_visualizacao()

                # --- Identificação (emoji e cor da categoria) ---------------
                if categoria["sem_categoria"]:
                    fundo_circulo = ft.Colors.with_opacity(0.18, cores.sem_categoria)
                    cor_subtitulo = cores.sem_categoria
                elif categoria["cor"]:
                    fundo_circulo = ft.Colors.with_opacity(0.18, categoria["cor"])
                    cor_subtitulo = cores.texto_secundario
                else:
                    fundo_circulo = cores.categoria_sem_cor
                    cor_subtitulo = cores.texto_secundario
                circulo = ft.Container(
                    width=64, height=64, border_radius=32, bgcolor=fundo_circulo,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(categoria["emoji"], size=30) if categoria["emoji"] else None,
                )
                identificacao = ft.Row(
                    spacing=16,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        circulo,
                        ft.Column(
                            expand=True, spacing=2,
                            controls=[
                                ft.Text(conta["nome"], size=22, weight=ft.FontWeight.BOLD,
                                        color=cores.texto_principal),
                                ft.Text(categoria["nome"], size=14, color=cor_subtitulo),
                            ],
                        ),
                    ],
                )

                # --- Status ao lado da ação de pagamento (quebra em janela estreita)
                cor_status = {"pago": cores.status_pago, "atrasado": cores.status_atrasado,
                              "pendente": cores.status_pendente}[status["status"]]
                chip_status = ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.12, cor_status),
                    border_radius=10,
                    padding=ft.Padding(14, 10, 14, 10),
                    content=ft.Text(status["rotulo"], size=14, weight=ft.FontWeight.BOLD, color=cor_status),
                )
                if status["status"] == "pago":
                    botao_pagamento = ft.OutlinedButton(
                        content=status["acao"], icon=ft.Icons.UNDO, on_click=desmarcar_como_paga_detalhes,
                        style=ft.ButtonStyle(color=cores.acao_primaria),
                    )
                else:
                    botao_pagamento = ft.Button(
                        content=status["acao"], icon=ft.Icons.CHECK,
                        bgcolor=cores.acao_pagamento, color=cores.texto_sobre_acao,
                        on_click=marcar_como_paga_detalhes,
                    )
                linha_status = ft.Row(
                    wrap=True, spacing=10, run_spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[chip_status, botao_pagamento],
                )

                # --- Grade de informações ----------------------------------
                def celula(icone, cor_icone, rotulo, valor, complemento=None, cor_valor=cores.texto_principal,
                           largura_total=False):
                    textos = [
                        ft.Text(rotulo, size=12, color=cores.texto_secundario),
                        ft.Text(valor, size=17, weight=ft.FontWeight.BOLD, color=cor_valor),
                    ]
                    if complemento:
                        textos.append(ft.Text(complemento, size=12, color=cores.texto_secundario))
                    return ft.Container(
                        col={"xs": 12} if largura_total else {"xs": 12, "sm": 6},
                        bgcolor=cores.fundo_card,
                        border=ft.Border.all(1, cores.borda_suave),
                        border_radius=12,
                        padding=14,
                        content=ft.Row(
                            spacing=14,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Container(
                                    width=44, height=44, border_radius=22,
                                    bgcolor=ft.Colors.with_opacity(0.12, cor_icone),
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(icone, size=22, color=cor_icone),
                                ),
                                ft.Column(expand=True, spacing=2, controls=textos),
                            ],
                        ),
                    )

                celulas = [
                    celula(ft.Icons.PAYMENTS_OUTLINED, cores.status_pago, "Valor", formatar_moeda(conta["valor"])),
                    celula(ft.Icons.CALENDAR_MONTH, cores.acao_primaria, "Vencimento", data_venc.strftime("%d/%m/%Y"),
                           complemento="Vence hoje" if status["vence_hoje"] else None),
                ]
                parcela_texto = None
                if serie_ativa:
                    parcela = database.obter_parcela(conta["serie_id"], conta["id"])
                    if parcela:
                        parcela_texto = texto_parcela(parcela)
                celulas.append(
                    celula(ft.Icons.FOLDER_OUTLINED, cores.texto_secundario, "Categoria", categoria["nome"],
                           cor_valor=cores.sem_categoria if categoria["sem_categoria"] else cores.texto_principal,
                           largura_total=parcela_texto is None)
                )
                if parcela_texto:
                    celulas.append(celula(ft.Icons.LAYERS_OUTLINED, cores.status_a_vencer, "Parcela", parcela_texto))
                celulas.append(
                    celula(ft.Icons.REPEAT, cores.status_pago, "Recorrência",
                           texto_recorrencia_detalhes(serie_ativa, info_serie), largura_total=True)
                )
                if conta.get("descricao"):
                    # 5.22: completa, com as quebras de linha; ausente quando vazia.
                    celulas.append(ft.Container(
                        col={"xs": 12},
                        bgcolor=cores.fundo_card,
                        border=ft.Border.all(1, cores.borda_suave),
                        border_radius=12,
                        padding=14,
                        content=ft.Column(spacing=6, controls=[
                            ft.Text("Descrição", size=12, color=cores.texto_secundario),
                            ft.Text(conta["descricao"], size=14, color=cores.texto_principal),
                        ]),
                    ))
                grade = ft.ResponsiveRow(spacing=12, run_spacing=12, controls=celulas)

                # --- Rodapé: Editar e Excluir, menores, iguais e centralizados
                botoes_rodape = ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=16,
                    controls=[
                        ft.Button(content="Editar", icon=ft.Icons.EDIT_OUTLINED, width=140,
                                  bgcolor=cores.acao_primaria, color=cores.texto_sobre_acao,
                                  on_click=lambda e: mostrar_formulario_edicao()),
                        ft.Button(content="Excluir", icon=ft.Icons.DELETE_OUTLINE, width=140,
                                  bgcolor=cores.acao_destrutiva, color=cores.texto_sobre_acao,
                                  on_click=lambda e: confirmar_exclusao_conta()),
                    ],
                )

                cabecalho = ft.Row(controls=[
                    ft.TextButton(content="Voltar", icon=ft.Icons.ARROW_BACK,
                                  on_click=lambda e: mostrar_tela_principal(tuple(mes_atual)),
                                  style=ft.ButtonStyle(color=cores.acao_primaria)),
                ])

                area_corpo.controls = [
                    ft.Container(
                        padding=ft.Padding(20, 32, 20, 24),
                        content=ft.Column(
                            data="tela_detalhes",  # identificação da tela (testes)
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            spacing=16,
                            controls=[
                                cabecalho,
                                identificacao,
                                linha_status,
                                grade,
                                ft.Divider(color=cores.divisor),
                                botoes_rodape,
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
                    title=ft.Text("Não foi possível excluir", color=cores.texto_principal),
                    content=ft.Text(f"Não foi possível excluir '{conta['nome']}'.", color=cores.texto_principal),
                    actions=[
                        ft.Button(content="Entendi", bgcolor=cores.acao_primaria, color=cores.texto_sobre_acao,
                                  on_click=lambda e: page.pop_dialog()),
                    ],
                    bgcolor=cores.fundo_dialogo,
                )
                page.show_dialog(dialogo_erro)

            def mostrar_dialogo_exclusao_simples():
                def excluir(e):
                    sucesso = database.excluir_conta(conta["id"])
                    page.pop_dialog()
                    if sucesso:
                        mostrar_tela_principal(tuple(mes_atual))
                    else:
                        mostrar_erro_exclusao()

                dialogo = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Excluir conta", color=cores.texto_principal),
                    content=ft.Text(f"Deseja realmente excluir a conta '{conta['nome']}'?",
                                    color=cores.texto_principal),
                    actions=[
                        ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog(),
                                      style=ft.ButtonStyle(color=cores.acao_primaria)),
                        ft.Button(content="Excluir", bgcolor=cores.acao_destrutiva, color=cores.texto_sobre_acao, on_click=excluir),
                    ],
                    bgcolor=cores.fundo_dialogo,
                )
                page.show_dialog(dialogo)

            def mostrar_dialogo_exclusao_serie():
                def excluir_somente_este_mes(e):
                    sucesso = database.excluir_conta(conta["id"])
                    page.pop_dialog()
                    if sucesso:
                        mostrar_tela_principal(tuple(mes_atual))
                    else:
                        mostrar_erro_exclusao()

                def excluir_este_mes_em_diante(e):
                    sucesso = database.excluir_conta_serie(conta["id"])
                    page.pop_dialog()
                    if sucesso:
                        mostrar_tela_principal(tuple(mes_atual))
                    else:
                        mostrar_erro_exclusao()

                acoes = [
                    ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog(),
                                  style=ft.ButtonStyle(color=cores.acao_primaria)),
                    ft.TextButton(content="Somente este mês", on_click=excluir_somente_este_mes,
                                  style=ft.ButtonStyle(color=cores.acao_primaria)),
                    ft.Button(content="Este mês em diante", bgcolor=cores.acao_destrutiva, color=cores.texto_sobre_acao,
                              on_click=excluir_este_mes_em_diante),
                ]

                dialogo = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Como deseja excluir esta conta?", color=cores.texto_principal),
                    content=ft.Text(
                        f"'{conta['nome']}' se repete todos os meses. Você pode excluir apenas "
                        "esta ocorrência, ou esta e todas as futuras.",
                        color=cores.texto_principal,
                    ),
                    actions=acoes,
                    bgcolor=cores.fundo_dialogo,
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
                sem_termino_transf = ft.Switch(value=False, active_color=cores.acao_primaria)
                ano_atual_transf = date.today().year
                campo_mes_termino_transf = ft.Dropdown(
                    label="Mês", color=cores.texto_principal, expand=True,
                    value=str(date.today().month),
                    options=[ft.dropdown.Option(key=str(i), text=MESES_PT[i - 1]) for i in range(1, 13)],
                    **estilo_lista(),
                )
                campo_ano_termino_transf = ft.Dropdown(
                    label="Ano", color=cores.texto_principal, expand=True,
                    value=str(ano_atual_transf),
                    options=[ft.dropdown.Option(key=str(a), text=str(a))
                             for a in range(ano_atual_transf, ano_atual_transf + 11)],
                    **estilo_lista(),
                )
                linha_termino_transf = ft.Row(
                    spacing=8, controls=[campo_mes_termino_transf, campo_ano_termino_transf], visible=True,
                )
                erro_transf = ft.Text(value="", color=cores.texto_erro, size=12)

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
                    bgcolor=cores.fundo_dialogo,
                    title=ft.Text("Transformar em recorrente", color=cores.texto_principal),
                    content=ft.Column(
                        tight=True,
                        spacing=12,
                        controls=[
                            ft.Text(
                                "A partir de agora, esta conta passa a se repetir automaticamente. "
                                "Escolha a frequência:",
                                color=cores.texto_principal,
                            ),
                            linha_frequencia_transf,
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text("Sem data de término", size=13, color=cores.texto_principal),
                                    sem_termino_transf,
                                ],
                            ),
                            linha_termino_transf,
                            erro_transf,
                        ],
                    ),
                    actions=[
                        ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog(),
                                      style=ft.ButtonStyle(color=cores.acao_primaria)),
                        ft.Button(content="Transformar", bgcolor=cores.acao_primaria, color=cores.texto_sobre_acao,
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

                sem_termino_alt = ft.Switch(value=False, active_color=cores.acao_primaria)
                ano_atual_alt = date.today().year
                campo_mes_termino_alt = ft.Dropdown(
                    label="Mês", color=cores.texto_principal, expand=True,
                    value=str(date.today().month),
                    options=[ft.dropdown.Option(key=str(i), text=MESES_PT[i - 1]) for i in range(1, 13)],
                    **estilo_lista(),
                )
                campo_ano_termino_alt = ft.Dropdown(
                    label="Ano", color=cores.texto_principal, expand=True,
                    value=str(ano_atual_alt),
                    options=[ft.dropdown.Option(key=str(a), text=str(a))
                             for a in range(ano_atual_alt, ano_atual_alt + 11)],
                    **estilo_lista(),
                )
                linha_termino_alt = ft.Row(
                    spacing=8, controls=[campo_mes_termino_alt, campo_ano_termino_alt], visible=True,
                )
                erro_freq = ft.Text(value="", color=cores.texto_erro, size=12)

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
                    title=ft.Text("Alterar frequência", color=cores.texto_principal),
                    content=ft.Column(
                        tight=True,
                        spacing=12,
                        controls=[
                            ft.Text(
                                "A partir desta ocorrência, a conta passa a se repetir com a "
                                "nova frequência escolhida.",
                                color=cores.texto_principal,
                            ),
                            linha_frequencia_alt,
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text("Sem data de término", size=13, color=cores.texto_principal),
                                    sem_termino_alt,
                                ],
                            ),
                            linha_termino_alt,
                            erro_freq,
                        ],
                    ),
                    actions=[
                        ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog(),
                                      style=ft.ButtonStyle(color=cores.acao_primaria)),
                        ft.Button(content="Confirmar", bgcolor=cores.acao_primaria, color=cores.texto_sobre_acao,
                                  on_click=confirmar_alteracao),
                    ],
                    bgcolor=cores.fundo_dialogo,
                )
                page.show_dialog(dialogo)

            def mostrar_dialogo_encerrar_recorrencia():
                # RF29 revisado (5.8, D7): contextual à ocorrência sendo editada
                # (conta["data_vencimento"]), nunca à data atual do sistema --
                # database.encerrar_recorrencia decide sozinha, a partir da
                # própria referência e de hoje, o que preservar (regra fechada
                # em D7: nunca apaga o que já aconteceu, nem a ocorrência
                # selecionada).
                erro_encerramento = ft.Text(value="", color=cores.texto_erro, size=12)
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
                    title=ft.Text("Encerrar recorrência", color=cores.texto_principal),
                    content=ft.Column(
                        tight=True,
                        spacing=12,
                        controls=[
                            ft.Text(
                                f"{frase_estado} Ao salvar as alterações, a recorrência será "
                                f"encerrada a partir de {mes_referencia_texto}: as contas que já "
                                "aconteceram serão mantidas, e as próximas ainda não realizadas "
                                "serão removidas.",
                                color=cores.texto_principal,
                            ),
                            erro_encerramento,
                        ],
                    ),
                    actions=[
                        ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog(),
                                      style=ft.ButtonStyle(color=cores.acao_primaria)),
                        ft.Button(content="Encerrar recorrência", bgcolor=cores.acao_destrutiva, color=cores.texto_sobre_acao,
                                  on_click=confirmar_encerramento),
                    ],
                    bgcolor=cores.fundo_dialogo,
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

                # 5.23/P4: sem max_length -- dados antigos acima do limite
                # aparecem inteiros; contador e mensagem explicam o excesso e
                # Salvar só é aceito depois de ajustados.
                campo_nome_edit = ft.TextField(
                    label="Nome da conta", value=conta["nome"], color=cores.texto_principal,
                    **estilo_campo_texto(),
                )
                # RF07/RF32 (5.22): descrição pode ser adicionada, editada ou
                # removida (campo vazio = remover).
                descricao_original = conta.get("descricao")
                campo_descricao_edit = ft.TextField(
                    label="Descrição (opcional)", value=descricao_original or "",
                    hint_text=f"Até {limites.LIMITE_DESCRICAO} caracteres",
                    multiline=True, min_lines=2, max_lines=5, color=cores.texto_principal,
                    **estilo_campo_texto(),
                )
                campo_valor_edit = ft.TextField(
                    label="Valor",
                    value=f"{conta['valor']:.2f}".replace(".", ","),
                    keyboard_type=ft.KeyboardType.NUMBER,
                    color=cores.texto_principal,
                    **estilo_campo_texto(),
                )
                campo_data_edit = ft.TextField(
                    label="Data de vencimento",
                    value=data_venc_atual.strftime("%d/%m/%Y"),
                    read_only=True, expand=True, color=cores.texto_principal,
                    **estilo_campo_texto(),
                )
                # RF07/5.11: categoria agora editável -- mesmo Dropdown/opções de
                # Nova Conta (montar_opcoes_categoria, promovida a main()),
                # incluindo "+ Nova categoria". Valor inicial reflete a
                # categoria atual da conta ("" quando não tem nenhuma).
                categoria_id_original = conta.get("categoria_id")
                campo_categoria_edit = ft.Dropdown(
                    label="Categoria",
                    value=str(categoria_id_original) if categoria_id_original is not None else "",
                    options=montar_opcoes_categoria(), color=cores.texto_principal,
                    expand=True,
                    **estilo_lista(),
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
                        or limites.normalizar_descricao(campo_descricao_edit.value)
                        != limites.normalizar_descricao(descricao_original)
                        or rascunho_status["status"] != conta["status"]
                        or rascunho_status["data_pagamento"] != conta.get("data_pagamento")
                        or rascunho_recorrencia["acao"] is not None
                    )

                def atualizar_estado_botao_salvar():
                    # Estado visual sempre derivado da mesma ha_alteracao_pendente()
                    # -- nunca uma segunda lógica de detecção só para a cor.
                    tem_alteracao = ha_alteracao_pendente()
                    botao_salvar.disabled = not tem_alteracao
                    botao_salvar.bgcolor = cores.acao_primaria if tem_alteracao else cores.botao_desabilitado_fundo
                    botao_salvar.color = cores.texto_sobre_acao if tem_alteracao else cores.botao_desabilitado_texto
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

                ligar_contador_de_limite(campo_nome_edit, "nome_conta", limites.LIMITE_NOME_CONTA,
                                         ao_mudar=lambda e: atualizar_estado_botao_salvar())
                ligar_contador_de_limite(campo_descricao_edit, "descricao", limites.LIMITE_DESCRICAO,
                                         ao_mudar=lambda e: atualizar_estado_botao_salvar())
                campo_valor_edit.on_change = lambda e: atualizar_estado_botao_salvar()


                erro_edit = ft.Text(value="", color=cores.texto_erro, size=12)

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
                    descricao = limites.normalizar_descricao(campo_descricao_edit.value)
                    # P4 (decisão da Etapa 2): TODOS os textos do formulário
                    # precisam estar dentro do limite, mesmo que o usuário só
                    # tenha mudado outro campo (valor, status...). Nada é
                    # cortado: o usuário ajusta e salva de novo.
                    erro_textos = (
                        erro_de_limite("nome_conta", nome, limites.LIMITE_NOME_CONTA)
                        or erro_de_limite("descricao", descricao, limites.LIMITE_DESCRICAO)
                    )

                    if not nome:
                        erro_edit.value = "Digite um nome para a conta."
                    elif erro_textos:
                        erro_edit.value = erro_textos
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

                    # RF07/5.11: "" no Dropdown = Sem categoria. Quando a
                    # categoria é removida, campos_alterados_edicao() envia
                    # remover_categoria=True ao db.py (None sozinho
                    # significaria "não mexer").
                    categoria_id_novo = (
                        int(campo_categoria_edit.value) if campo_categoria_edit.value else None
                    )

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
                        descricao_antiga=descricao_original, descricao_nova=descricao,
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
                    # Vencimento/Categoria/Descrição (v6, 5.6) entram nesta checagem -- de propósito, não
                    # volte a juntar as duas perguntas numa só (importante também para
                    # quando Recorrência virar rascunho: a mesma distinção vai valer).
                    # Correção v6.0 (Etapa 0): só os campos realmente alterados
                    # seguem para o db.py -- um campo não alterado (sobretudo a
                    # data) nunca é reenviado, para não redefinir a âncora da
                    # série nem sobrescrever ocorrências futuras.
                    campos_alterados = campos_alterados_edicao(
                        conta["nome"], nome, conta["valor"], valor,
                        data_venc_atual, nova_data, categoria_id_original, categoria_id_novo,
                        descricao_original, descricao,
                    )
                    ha_alteracao_propagavel = bool(campos_alterados)

                    if conta.get("serie_id") is not None and serie_ativa and ha_alteracao_propagavel:
                        # RF20 (5.6): só pergunta o escopo quando existe algo
                        # propagável de fato (Nome/Valor/Vencimento/Categoria/
                        # Descrição -- um único diálogo para todos, CT107) --
                        # uma alteração só de Status/data de pagamento nunca chega
                        # aqui, mesmo numa série ativa. Sem restrição de mês/ano
                        # (removida na Fase 2.6); a nova data pode cair em
                        # qualquer mês/ano. Série já removida (RF29) cai direto no
                        # ramo de baixo, como conta avulsa.
                        mostrar_dialogo_escopo_edicao(campos_alterados, mensagem_alteracao)
                    else:
                        if ha_alteracao_propagavel:
                            # Só grava Nome/Valor/Vencimento/Categoria/Descrição quando algo
                            # deles de fato mudou -- uma alteração só de Status não
                            # deve gerar uma reescrita sem propósito destes campos
                            # (e, numa série ativa, não deve marcar
                            # editado_individualmente=1 à toa só por causa de
                            # Status, que nunca é uma edição desses campos).
                            try:
                                database.editar_conta_ocorrencia(conta["id"], **campos_alterados)
                            except limites.LimiteDeCaracteresError as erro_limite:
                                erro_edit.value = str(erro_limite)
                                page.update()
                                return
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
                        mostrar_tela_principal(tuple(mes_atual))

                    acao_entendi = ft.Button(content="Entendi", bgcolor=cores.acao_primaria, color=cores.texto_sobre_acao,
                                              on_click=fechar_confirmacao)

                    if dialogo_alvo is not None:
                        dialogo_alvo.title = ft.Text("Alteração salva", color=cores.texto_principal)
                        dialogo_alvo.content = ft.Text(mensagem_alteracao, color=cores.texto_principal)
                        dialogo_alvo.actions = [acao_entendi]
                        page.update()
                    else:
                        page.show_dialog(
                            ft.AlertDialog(
                                modal=True,
                                title=ft.Text("Alteração salva", color=cores.texto_principal),
                                content=ft.Text(mensagem_alteracao, color=cores.texto_principal),
                                actions=[acao_entendi],
                                bgcolor=cores.fundo_dialogo,
                            )
                        )

                def mostrar_dialogo_escopo_edicao(campos_alterados, mensagem_alteracao):
                    def mostrar_recusa(erro):
                        # 5.23 (limite de caracteres) e D5 (mês não posterior
                        # ao da parcela anterior): mensagem própria, nunca
                        # "ultrapassaria o término" nem falha genérica. A
                        # recusa acontece antes de qualquer gravação, e
                        # Status/Recorrência (aplicados só depois) também
                        # não são gravados.
                        page.pop_dialog()
                        erro_edit.value = str(erro)
                        page.update()

                    def aplicar_somente_esta(e):
                        try:
                            sucesso = database.editar_conta_ocorrencia(conta["id"], **campos_alterados)
                        except limites.LimiteDeCaracteresError as erro_limite:
                            mostrar_recusa(erro_limite)
                            return
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
                        try:
                            sucesso = database.editar_conta_serie(conta["id"], **campos_alterados)
                        except (limites.LimiteDeCaracteresError,
                                database.VencimentoAntesDaParcelaAnteriorError) as erro:
                            mostrar_recusa(erro)
                            return
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
                        title=ft.Text("Como deseja aplicar esta alteração?", color=cores.texto_principal),
                        content=ft.Text(
                            "Esta conta faz parte de uma recorrência. Você pode alterar "
                            "apenas esta ocorrência ou também as próximas da mesma recorrência.",
                            color=cores.texto_principal,
                        ),
                        actions=[
                            ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog(),
                                          style=ft.ButtonStyle(color=cores.acao_primaria)),
                            ft.Button(content="Somente este mês", bgcolor=cores.acao_primaria, color=cores.texto_sobre_acao,
                                      on_click=aplicar_somente_esta),
                            ft.TextButton(content="Este mês em diante", on_click=aplicar_este_mes_em_diante,
                                          style=ft.ButtonStyle(color=cores.acao_primaria)),
                        ],
                        bgcolor=cores.fundo_dialogo,
                    )
                    page.show_dialog(dialogo)

                cabecalho_edicao = ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=20, icon_color=cores.texto_principal,
                                      on_click=lambda e: voltar_do_formulario()),
                        ft.Text("Editar conta", size=18, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
                        ft.Container(width=40),
                    ],
                )


                # RF07/RF20 (5.6/5.11) + padronização visual pós-validação manual:
                # "Salvar alterações" começa desabilitado (cinza -- #E5E4DE/#888780,
                # mesmas cores já usadas no app para estado inativo) e só habilita
                # (verde -- #1D9E75, mesma cor de toda ação principal do Sino)
                # quando nome/valor/vencimento/categoria/descrição realmente diferirem do
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
                    bgcolor=cores.botao_secundario_fundo,
                    color=cores.botao_secundario_texto,
                    style=ft.ButtonStyle(side=ft.BorderSide(1, cores.borda_suave)),
                    width=110,
                    on_click=lambda e: voltar_do_formulario(),
                )
                botao_salvar = ft.Button(
                    content="Salvar alterações",
                    bgcolor=cores.botao_desabilitado_fundo,
                    color=cores.botao_desabilitado_texto,
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
                                    ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, icon_color=cores.acao_primaria,
                                                  on_click=abrir_seletor_data),
                                ]),
                                campo_categoria_edit,
                                campo_descricao_edit,
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
            if abrir_em_edicao:
                mostrar_formulario_edicao()
            else:
                mostrar_visualizacao()

        def linha_conta(conta, nome_categoria, acao_rapida_pagamento=False, acao_editar=False):
            data_venc = date.fromisoformat(conta["data_vencimento"])
            dias_delta = (data_venc - date.today()).days

            if conta["status"] == "pago":
                cor, rotulo_status = cores.status_pago, "Pago"
                frase = None
            elif conta["status"] == "atrasado":
                cor, rotulo_status = cores.status_atrasado, "Atrasado"
                frase = frase_vencimento_passado(abs(dias_delta))
            else:
                # Três status (Atrasado, Pendente, Pago): vencer hoje continua
                # Pendente -- "vence hoje" é só a mensagem de vencimento (5.17).
                cor, rotulo_status = cores.status_pendente, "Pendente"
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
                        ft.Text(conta["nome"], size=14, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
                        ft.Text(subtitulo, size=12, color=cores.texto_secundario),
                    ],
                    spacing=2,
                ),
                ft.Column(
                    controls=[
                        ft.Text(formatar_moeda(conta["valor"]), size=14, weight=ft.FontWeight.BOLD,
                                 color=cores.texto_principal),
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

            if acao_editar:
                # RF30/5.15 (Etapa 3): atalho para Editar conta, só na Tela
                # Principal -- mesmas dimensões do controle de pagamento
                # (IconButton 22 num Container de 40). O clique no botão não
                # abre os Detalhes (o botão consome o toque, como o de pagamento).
                controles_linha.append(
                    ft.Container(
                        width=40, alignment=ft.Alignment.CENTER,
                        content=ft.IconButton(
                            icon=ft.Icons.EDIT_OUTLINED,
                            icon_color=cores.texto_secundario,
                            icon_size=22,
                            tooltip="Editar conta",
                            on_click=lambda e, c=conta: abrir_detalhe_conta(c, abrir_em_edicao=True),
                        ),
                    )
                )

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
                        icon_color=cores.controle_pago,
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
                        icon_color=cores.controle_pendente,
                        icon_size=22,
                        tooltip="Marcar como paga",
                        on_click=marcar_como_paga_rapido,
                    )
                controles_linha.append(
                    ft.Container(width=40, alignment=ft.Alignment.CENTER, content=icone_pagamento)
                )

            return ft.Container(
                bgcolor=cores.fundo_card,
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

            total, pago, pendente = resumo_do_mes(contas_mes)
            valor_total.value = formatar_moeda(total)
            valor_pago.value = f"pago {formatar_moeda(pago)}"
            valor_pendente.value = f"pendente {formatar_moeda(pendente)}"

            proximas = database.listar_contas_proximas(usuario_atual["id"], dias=7)
            if proximas:
                total_proximas = sum(c["valor"] for c in proximas)
                banner_semana.bgcolor = cores.aviso_fundo
                banner_semana.border_radius = 10
                banner_semana.padding = 12
                banner_semana.content = ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.WARNING_AMBER, size=18, color=cores.aviso_icone),
                        ft.Container(width=8),
                        ft.Column(
                            controls=[
                                ft.Text(frase_resumo_proximas(len(proximas)), size=13,
                                         weight=ft.FontWeight.BOLD, color=cores.aviso_texto),
                                ft.Text(f"Total de {formatar_moeda(total_proximas)}", size=12, color=cores.aviso_texto),
                            ],
                            spacing=0,
                        ),
                    ],
                )
                banner_semana.visible = True
            else:
                banner_semana.visible = False

            construir_bloco_atrasadas(database.listar_contas_atrasadas(usuario_atual["id"]))

            # RF05/5.15 (Etapa 3): TODAS as contas do mês (sem o antigo corte
            # em 5), na rolagem normal da página (`conteudo`); ordem mantida.
            contas_ordenadas = ordenar_contas_do_mes(contas_mes)

            lista_contas.controls.clear()
            if not contas_ordenadas:
                lista_contas.controls.append(
                    ft.Container(
                        content=ft.Text("Nenhuma conta neste mês.", color=cores.texto_secundario, size=13),
                        padding=16,
                    )
                )
            else:
                for c in contas_ordenadas:
                    lista_contas.controls.append(
                        linha_conta(c, categorias.get(c["categoria_id"], ""), acao_rapida_pagamento=True,
                                    acao_editar=True)
                    )

            page.update()

        def mostrar_tela_ver_status(ano_mes):
            # RF09/5.21 (Etapa 3): "Ver status" -- consulta das contas do mês de
            # referência por status (Todas | Pendentes | Pagas | Atrasadas). O
            # mês é o do vencimento real (database.listar_contas), mesma lista e
            # mesma ordem da Tela Principal. Reaproveita linha_conta()/
            # abrir_detalhe_conta() por estar aninhada em mostrar_tela_principal();
            # o filtro vive só nesta tela (recriado a cada abertura).
            page.controls.clear()
            page.padding = 0

            ano, mes = (int(p) for p in ano_mes.split("-"))
            categorias_atuais = {c["id"]: c["nome"] for c in database.listar_categorias(usuario_atual["id"])}
            contas_do_mes_ordenadas = ordenar_contas_do_mes(database.listar_contas(usuario_atual["id"], ano_mes))
            filtro_status = {"valor": "todas"}

            lista_ver_status = ft.ListView(expand=True, spacing=8, padding=ft.Padding(20, 0, 20, 24))

            def recompor_lista():
                lista_ver_status.controls.clear()
                if not contas_do_mes_ordenadas:
                    lista_ver_status.controls.append(
                        ft.Container(
                            content=ft.Text("Nenhuma conta cadastrada neste mês.", color=cores.texto_secundario, size=13),
                            padding=16,
                        )
                    )
                    return
                filtradas = filtrar_por_status(contas_do_mes_ordenadas, filtro_status["valor"])
                if not filtradas:
                    lista_ver_status.controls.append(
                        ft.Container(
                            content=ft.Text("Nenhuma conta encontrada com os filtros selecionados.",
                                             color=cores.texto_secundario, size=13),
                            padding=16,
                        )
                    )
                else:
                    for c in filtradas:
                        lista_ver_status.controls.append(linha_conta(c, categorias_atuais.get(c["categoria_id"], "")))

            linha_filtros = ft.Row(spacing=8, controls=[])

            def botao_filtro(valor, rotulo):
                # 8.2: botões maiores e mais destacados que os chips antigos
                # (mesmo padrão dos chips "Única/Mensal/Anual" de Nova Conta).
                ativo = filtro_status["valor"] == valor
                return ft.Container(
                    content=ft.Text(rotulo, size=13, weight=ft.FontWeight.BOLD,
                                     color=cores.chip_ativo_texto if ativo else cores.chip_inativo_texto),
                    bgcolor=cores.chip_ativo_fundo if ativo else cores.chip_inativo_fundo,
                    border=None if ativo else ft.Border.all(1, cores.borda_suave),
                    border_radius=10,
                    padding=ft.Padding(0, 12, 0, 12),
                    alignment=ft.Alignment.CENTER,
                    expand=True,
                    on_click=lambda e, v=valor: selecionar_filtro(v),
                )

            def montar_filtros():
                linha_filtros.controls = [botao_filtro(valor, rotulo) for valor, rotulo in FILTROS_DE_STATUS]

            def selecionar_filtro(valor):
                filtro_status["valor"] = valor
                montar_filtros()
                recompor_lista()
                page.update()

            montar_filtros()
            recompor_lista()

            cabecalho_ver_status = ft.Container(
                padding=ft.Padding(20, 40, 20, 0),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=20, icon_color=cores.texto_principal,
                                      on_click=lambda e: mostrar_tela_principal((ano, mes))),
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                            controls=[
                                ft.Text("Ver status", size=13, color=cores.texto_secundario),
                                ft.Text(f"{MESES_PT[mes - 1]} de {ano}", size=18, weight=ft.FontWeight.BOLD,
                                        color=cores.texto_principal),
                            ],
                        ),
                        ft.Container(width=40),
                    ],
                ),
            )

            page.add(
                ft.Column(
                    expand=True,
                    controls=[
                        cabecalho_ver_status,
                        ft.Container(padding=ft.Padding(20, 16, 20, 8), content=linha_filtros),
                        lista_ver_status,
                    ],
                )
            )
            page.update()

        def mostrar_tela_atrasadas():
            # RF25 (Fase 3.9): tela dedicada, sempre com TODAS as contas atrasadas
            # do usuário -- database.listar_contas_atrasadas já ignora o mês
            # selecionado na Tela Principal, então esta tela não filtra por
            # mes_atual. Reaproveita linha_conta()/abrir_detalhe_conta() por estar
            # aninhada no mesmo escopo de mostrar_tela_principal() (mesmo padrão de
            # mostrar_tela_ver_status).
            page.controls.clear()
            page.padding = 0

            categorias_atuais = {c["id"]: c["nome"] for c in database.listar_categorias(usuario_atual["id"])}
            atrasadas_todas = database.listar_contas_atrasadas(usuario_atual["id"])

            lista_atrasadas_tela = ft.ListView(expand=True, spacing=8, padding=ft.Padding(20, 0, 20, 24))
            if not atrasadas_todas:
                lista_atrasadas_tela.controls.append(
                    ft.Container(
                        content=ft.Text("Nenhuma conta atrasada.", color=cores.texto_secundario, size=13),
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
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=20, icon_color=cores.texto_principal,
                                      on_click=lambda e: mostrar_tela_principal()),
                        ft.Text("Contas em atraso", size=18, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
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
            content=ft.Icon(ft.Icons.ADD, color=cores.texto_sobre_acao, size=26),
            bgcolor=cores.acao_primaria,
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
        # 5.23: sem max_length -- um nome antigo acima de 30 caracteres é
        # exibido inteiro; o contador (por grafemas) e a mensagem explicam o
        # excesso, e Salvar só é aceito depois de ajustado (P4).
        campo_nome = ft.TextField(label="Nome da categoria", value=cat["nome"] if cat else "", width=280,
                                  color=cores.texto_principal,
                                  **estilo_campo_texto())
        campo_icone = ft.TextField(label="Ícone (emoji, opcional)",
                                    value=cat["icone"] if cat else "", width=280, color=cores.texto_principal,
                                   **estilo_campo_texto())
        erro = ft.Text(value="", color=cores.texto_erro, size=12)

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
                ft.Text("Sugestões", size=12, color=cores.texto_secundario),
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
                        bgcolor=cores.fundo_sugestao_emoji,
                        alignment=ft.Alignment.CENTER,
                        border=ft.Border.all(2, cores.borda_selecao) if selecionado else None,
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

        ligar_contador_de_limite(campo_nome, "nome_categoria", limites.LIMITE_NOME_CATEGORIA,
                                 ao_mudar=ao_mudar_nome)
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
                                size=16, color=cores.texto_secundario,
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
                    border=ft.Border.all(1, cores.borda_suave),
                    border_radius=8,
                    padding=ft.Padding(12, 16, 12, 12),
                    content=ft.Column(spacing=0, controls=conteudo),
                )
                rotulo = ft.Container(
                    content=ft.Text(dados["nome"], size=11, color=cores.texto_secundario),
                    bgcolor=cores.fundo_dialogo,
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
                    ft.TextButton(content="Fechar", on_click=lambda ev: page.pop_dialog(),
                                  style=ft.ButtonStyle(color=cores.acao_primaria)),
                ],
                bgcolor=cores.fundo_dialogo,
            )
            page.show_dialog(dialogo_emoji)

        botao_mais_emojis = ft.TextButton(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=16, color=cores.acao_primaria),
                    ft.Text("Mais emojis", size=12, color=cores.acao_primaria),
                ],
                spacing=4,
                tight=True,
            ),
            on_click=abrir_seletor_emoji_geral,
            style=ft.ButtonStyle(color=cores.acao_primaria),
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
                        border=ft.Border.all(2, cores.borda_selecao_cor) if selecionada else None,
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
            erro_nome = erro_de_limite("nome_categoria", nome, limites.LIMITE_NOME_CATEGORIA)
            if erro_nome:
                erro.value = erro_nome
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
            except limites.LimiteDeCaracteresError as erro_limite:
                # Checado antes do ValueError genérico (é subclasse dele):
                # nunca confundir com cor em uso ou limite de categorias.
                erro.value = str(erro_limite)
                page.update()
                return
            except database.CorReservadaError:
                # 5.13: o cinza é reservado a "Sem categoria" (a paleta não o
                # oferece; esta é a barreira da gravação).
                erro.value = "Essa cor é reservada para “Sem categoria”. Escolha outra."
                page.update()
                return
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
            title=ft.Text("Editar categoria" if cat else "Nova categoria", color=cores.texto_principal),
            content=ft.Column(
                controls=[
                    campo_nome,
                    campo_icone,
                    bloco_sugestoes_emoji,
                    botao_mais_emojis,
                    ft.Text("Cor", size=12, color=cores.texto_secundario),
                    linha_cores,
                    erro,
                ],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog(),
                              style=ft.ButtonStyle(color=cores.acao_primaria)),
                ft.Button(content="Salvar", bgcolor=cores.acao_primaria, color=cores.texto_sobre_acao, on_click=salvar),
            ],
            bgcolor=cores.fundo_dialogo,
        )
        page.show_dialog(dialogo)

    def mostrar_limite_categorias():
        dialogo_limite = ft.AlertDialog(
            modal=True,
            title=ft.Text("Limite atingido", color=cores.texto_principal),
            content=ft.Text(
                f"Você atingiu o limite máximo de "
                f"{database.LIMITE_CATEGORIAS_POR_USUARIO} categorias.",
                color=cores.texto_principal,
            ),
            actions=[
                ft.Button(content="Entendi", bgcolor=cores.acao_primaria, color=cores.texto_sobre_acao,
                          on_click=lambda e: page.pop_dialog()),
            ],
            bgcolor=cores.fundo_dialogo,
        )
        page.show_dialog(dialogo_limite)

    def ponto_cor_categoria(cor):
        return ft.Container(width=10, height=10, border_radius=5, bgcolor=cor or cores.categoria_sem_cor)

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
                    leading_icon=ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, color=cores.acao_primaria, size=16),
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
    # ======================================================
    #  TELA GRÁFICO (ERS v6.0, Etapa 5: RF21-RF23, RF34)
    #  Protótipo 10. Somente consulta: nunca gera ocorrências (5.26).
    # ======================================================
    def mostrar_tela_grafico():
        page.controls.clear()
        page.overlay.clear()
        page.padding = 0

        hoje = date.today()
        anos = database.anos_com_contas(usuario_atual["id"])
        estado = {
            "modo": "mensal",                               # período geral (Mensal | Anual)
            "ano": hoje.year, "mes": hoje.month,            # período mensal
            "ano_anual": ano_inicial_anual(anos, hoje.year),  # período anual
            "perspectiva": "seis_meses",                    # só RF21 (6 meses | Anual)
        }
        # STRETCH: cada bloco ocupa toda a largura (ex.: cartão de comparação).
        corpo = ft.Column(spacing=16, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[])
        ALTURA_CARTOES_TOTAIS = 190  # Total do mês/ano e Total pago com a mesma altura (protótipo 10)

        # ---------------------------------------------------------- auxiliares
        def cartao(conteudo, bgcolor=None, borda=None, col=None, padding=18, height=None):
            return ft.Container(
                col=col, height=height, bgcolor=bgcolor or cores.fundo_card, border_radius=16, padding=padding,
                border=ft.Border.all(1, borda or cores.borda_suave), content=conteudo,
            )

        def circulo_icone(icone, cor, tamanho=52):
            return ft.Container(
                width=tamanho, height=tamanho, border_radius=tamanho / 2,
                bgcolor=ft.Colors.with_opacity(0.14, cor), alignment=ft.Alignment.CENTER,
                content=ft.Icon(icone, color=cor, size=tamanho * 0.5),
            )

        def alternador(opcoes, selecionada, ao_escolher):
            return ft.Container(
                bgcolor=cores.grafico_comparacao_fundo, border_radius=20, padding=3,
                content=ft.Row(tight=True, spacing=0, controls=[
                    ft.Container(
                        border_radius=17, padding=ft.Padding(16, 7, 16, 7),
                        bgcolor=cores.grafico_barra_destaque if valor == selecionada else None,
                        content=ft.Text(rotulo, size=13, weight=ft.FontWeight.BOLD,
                                        color=cores.texto_sobre_acao if valor == selecionada else cores.texto_secundario),
                        on_click=lambda e, v=valor: ao_escolher(v),
                    )
                    for valor, rotulo in opcoes
                ]),
            )

        def periodo_atual():
            if estado["modo"] == "anual":
                return "anual", estado["ano_anual"], None
            return "mensal", estado["ano"], estado["mes"]

        # ---------------------------------------------------------- ações
        def escolher_modo(modo):
            estado["modo"] = modo
            estado["perspectiva"] = "anual" if modo == "anual" else "seis_meses"
            atualizar()

        def escolher_perspectiva(perspectiva):
            estado["perspectiva"] = perspectiva
            atualizar()

        def navegar(delta):
            if estado["modo"] == "anual":
                if estado["ano_anual"] in anos:
                    indice = anos.index(estado["ano_anual"]) + delta
                    if 0 <= indice < len(anos):
                        estado["ano_anual"] = anos[indice]
            else:
                ano, mes = estado["ano"], estado["mes"] + delta
                if mes == 0:
                    ano, mes = ano - 1, 12
                elif mes == 13:
                    ano, mes = ano + 1, 1
                estado["ano"], estado["mes"] = ano, mes
            atualizar()

        # ---------------------------------------------------------- blocos
        def bloco_navegacao():
            modo, ano, mes = periodo_atual()
            if modo == "anual":
                pode_voltar = estado["ano_anual"] in anos and anos.index(estado["ano_anual"]) > 0
                pode_avancar = estado["ano_anual"] in anos and anos.index(estado["ano_anual"]) < len(anos) - 1
            else:
                pode_voltar = pode_avancar = True
            return ft.Row(
                alignment=ft.MainAxisAlignment.CENTER, spacing=12,
                controls=[
                    ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, icon_color=cores.texto_principal,
                                  disabled=not pode_voltar, tooltip="Período anterior",
                                  on_click=lambda e: navegar(-1)),
                    ft.Container(
                        width=240, padding=ft.Padding(0, 10, 0, 10), border_radius=24,
                        border=ft.Border.all(1, cores.borda_suave), bgcolor=cores.fundo_card,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(rotulo_periodo(modo, ano, mes), size=16, weight=ft.FontWeight.BOLD,
                                        color=cores.texto_principal),
                    ),
                    ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, icon_color=cores.texto_principal,
                                  disabled=not pode_avancar, tooltip="Próximo período",
                                  on_click=lambda e: navegar(1)),
                ],
            )

        def bloco_totais(total, pago):
            modo, ano, _ = periodo_atual()
            rotulo_total = "Total do ano" if modo == "anual" else "Total do mês"
            explicacao = (f"Valor total das contas cadastradas em {ano} (pagas, pendentes e atrasadas)."
                          if modo == "anual" else
                          "Todas as contas cadastradas neste mês (pagas, pendentes e atrasadas).")
            cartao_total = cartao(
                col={"xs": 12, "md": 6}, bgcolor=cores.grafico_total_fundo, borda=cores.grafico_total_borda,
                height=ALTURA_CARTOES_TOTAIS,
                conteudo=ft.Row(spacing=16, vertical_alignment=ft.CrossAxisAlignment.START, controls=[
                    circulo_icone(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, cores.grafico_total_icone),
                    ft.Column(expand=True, spacing=4, controls=[
                        ft.Row(spacing=6, controls=[
                            ft.Text(rotulo_total, size=15, color=cores.texto_principal),
                            ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=cores.texto_secundario,
                                    tooltip=explicacao),
                        ]),
                        ft.Text(formatar_moeda(total), size=28, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
                        ft.Text(explicacao, size=12, color=cores.texto_secundario),
                    ]),
                ]),
            )
            fracao = 0 if not total else min(pago / total, 1)
            cartao_pago = cartao(
                col={"xs": 12, "md": 6}, bgcolor=cores.grafico_pago_fundo, borda=cores.grafico_pago_borda,
                height=ALTURA_CARTOES_TOTAIS,
                conteudo=ft.Column(spacing=10, controls=[
                    ft.Row(spacing=16, vertical_alignment=ft.CrossAxisAlignment.START, controls=[
                        circulo_icone(ft.Icons.CHECK_CIRCLE, cores.grafico_pago_icone),
                        ft.Column(expand=True, spacing=4, controls=[
                            ft.Text("Total pago", size=15, color=cores.texto_principal),
                            ft.Text(formatar_moeda(pago), size=28, weight=ft.FontWeight.BOLD,
                                    color=cores.texto_principal),
                        ]),
                    ]),
                    ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        ft.ProgressBar(value=fracao, expand=True, height=10, border_radius=5,
                                       color=cores.grafico_barra_destaque, bgcolor=cores.grafico_progresso_fundo),
                        ft.Text(formatar_percentual(percentual_de(pago, total)), size=13,
                                color=cores.texto_principal),
                    ]),
                    ft.Text(f"{formatar_moeda(pago)} de {formatar_moeda(total)} pagos", size=13,
                            color=cores.texto_secundario),
                ]),
            )
            return ft.ResponsiveRow(spacing=16, run_spacing=16, controls=[cartao_total, cartao_pago])

        def grafico_barras(pontos):
            """pontos: [(rótulo, valor, destaque)] -- valor logo acima de cada barra."""
            maior = max((valor for _, valor, _ in pontos), default=0) or 1
            grupos = [
                fch.BarChartGroup(x=i, rods=[fch.BarChartRod(
                    from_y=0, to_y=valor, width=46,
                    color=cores.grafico_barra_destaque if destaque else cores.grafico_barra,
                    border_radius=ft.BorderRadius.only(top_left=6, top_right=6),
                    selected=True,  # rótulo fixo acima da barra (gráfico não interativo)
                    tooltip=fch.BarChartRodTooltip(
                        text=formatar_moeda(valor),
                        text_style=ft.TextStyle(
                            size=13, weight=ft.FontWeight.BOLD,
                            color=cores.grafico_barra_destaque if destaque else cores.texto_secundario),
                    ),
                )])
                for i, (_, valor, destaque) in enumerate(pontos)
            ]
            return fch.BarChart(
                groups=grupos, height=230, interactive=False,
                min_y=0, max_y=maior * 1.3,
                group_alignment=ft.MainAxisAlignment.SPACE_AROUND,
                tooltip=fch.BarChartTooltip(bgcolor=ft.Colors.TRANSPARENT, padding=0, margin=4),
                bottom_axis=fch.ChartAxis(label_size=30, labels=[
                    fch.ChartAxisLabel(value=i, label=ft.Text(
                        rotulo, size=14,
                        weight=ft.FontWeight.BOLD if destaque else None,
                        color=cores.grafico_barra_destaque if destaque else cores.texto_principal))
                    for i, (rotulo, _, destaque) in enumerate(pontos)
                ]),
                left_axis=fch.ChartAxis(show_labels=False),
                right_axis=fch.ChartAxis(show_labels=False),
                top_axis=fch.ChartAxis(show_labels=False),
                horizontal_grid_lines=fch.ChartGridLines(interval=maior * 1.3, color=cores.divisor, width=1),
            )

        def bloco_evolucao():
            modo, ano, mes = periodo_atual()
            if estado["perspectiva"] == "anual":
                subtitulo = "Total das contas cadastradas por ano"
                ano_destacado = ano
                pontos = [(str(a), total, a == ano_destacado) for a, total in database.totais_por_ano(usuario_atual["id"])]
            else:
                subtitulo = "Total de contas cadastradas nos últimos 6 meses"
                fim = (ano, 12) if modo == "anual" else (ano, mes)
                meses = janela_seis_meses(*fim)
                totais = database.totais_por_mes(usuario_atual["id"], f"{meses[0][0]:04d}-{meses[0][1]:02d}",
                                                 f"{meses[-1][0]:04d}-{meses[-1][1]:02d}")
                pontos = [(MESES_ABREVIADOS[m - 1], totais.get(f"{a:04d}-{m:02d}", 0.0),
                           modo == "mensal" and (a, m) == (ano, mes)) for a, m in meses]
            cabecalho = ft.ResponsiveRow(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Column(col={"xs": 12, "sm": 7}, spacing=2, controls=[
                    ft.Text("Evolução dos gastos", size=20, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
                    ft.Text(subtitulo, size=14, color=cores.texto_secundario),
                ]),
                ft.Row(col={"xs": 12, "sm": 5}, alignment=ft.MainAxisAlignment.END, controls=[
                    alternador((("seis_meses", "6 meses"), ("anual", "Anual")), estado["perspectiva"],
                               escolher_perspectiva),
                ]),
            ])
            conteudo = (grafico_barras(pontos) if pontos else
                        ft.Text("Ainda não há dados para exibir.", size=13, color=cores.texto_secundario))
            return cartao(ft.Column(spacing=16, controls=[cabecalho, conteudo]))

        def bloco_categorias(total, itens):
            modo, ano, mes = periodo_atual()
            titulo = ft.Column(spacing=2, controls=[
                ft.Text("Gastos por categoria", size=20, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
                ft.Text("Distribuição do total do ano" if modo == "anual" else "Distribuição do total do mês",
                        size=14, color=cores.texto_secundario),
            ])
            if not total:
                return cartao(ft.Column(spacing=16, controls=[
                    titulo,
                    ft.Text("Ainda não há dados para exibir neste período.", size=14, color=cores.texto_secundario),
                ]))
            layout = layout_gastos_por_categoria(page.width)
            tamanho = layout["tamanho_rosca"]
            cores_exibicao = database.cores_de_exibicao(database.listar_categorias(usuario_atual["id"]))

            def cor_do_item(item):
                if item["categoria_id"] is None:
                    return cores.sem_categoria
                return cores_exibicao.get(item["categoria_id"]) or item["cor"]

            secoes, linhas = [], []
            for item in itens:
                cor = cor_do_item(item)
                fatia = item["total"] / total
                # Percentuais só na legenda (nenhum título nas fatias).
                secoes.append(fch.PieChartSection(value=item["total"], color=cor,
                                                  radius=layout["tamanho_rosca"] * 0.2, title=""))
                sem_categoria = item["categoria_id"] is None
                linhas.append(ft.Container(
                    padding=ft.Padding(0, 8, 0, 8),
                    border=ft.Border(bottom=ft.BorderSide(1, cores.divisor)),
                    content=ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        ft.Container(width=34, height=34, border_radius=17, bgcolor=cor,
                                     alignment=ft.Alignment.CENTER,
                                     content=None if sem_categoria or not item["icone"]
                                     else ft.Text(item["icone"], size=16)),
                        # Nome completo, sem corte (até 30 caracteres numa linha em
                        # janela larga; em janela estreita quebra linha).
                        ft.Text(item["nome"], size=15,
                                width=layout["largura_nome"], expand=layout["largura_nome"] is None,
                                color=cores.sem_categoria if sem_categoria else cores.texto_principal),
                        ft.Text(formatar_moeda(item["total"]), size=15, width=layout["largura_valor"],
                                text_align=ft.TextAlign.RIGHT, color=cores.texto_principal),
                        ft.Text(formatar_percentual(fatia * 100), size=15, width=layout["largura_percentual"],
                                text_align=ft.TextAlign.RIGHT,
                                weight=ft.FontWeight.BOLD, color=cores.texto_principal),
                    ]),
                ))
            rosca = ft.Stack(width=tamanho, height=tamanho, controls=[
                fch.PieChart(width=tamanho, height=tamanho, sections=secoes, center_space_radius=tamanho * 0.28,
                             sections_space=2, start_degree_offset=-90),
                ft.Container(width=tamanho, height=tamanho, alignment=ft.Alignment.CENTER, content=ft.Column(
                    tight=True, spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        ft.Text("Total do ano" if modo == "anual" else "Total do mês", size=13,
                                color=cores.texto_secundario),
                        ft.Text(formatar_moeda(total), size=18, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
                    ])),
            ])
            periodo = str(ano) if modo == "anual" else f"{MESES_PT[mes - 1].lower()} de {ano}"
            nota = ft.Container(
                bgcolor=cores.grafico_comparacao_fundo, border_radius=10, padding=10,
                content=ft.Row(spacing=8, controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=cores.texto_secundario),
                    ft.Text(f"Apenas categorias com contas em {periodo} são exibidas. Contas sem categoria "
                            "são agrupadas como “Sem categoria”.", size=12, color=cores.texto_secundario, expand=True),
                ]),
            )
            return cartao(ft.Column(spacing=16, controls=[
                titulo,
                ft.ResponsiveRow(spacing=24, run_spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    # Rosca e legenda lado a lado a partir de "lg"; abaixo disso, legenda
                    # embaixo da rosca.
                    ft.Container(col={"xs": 12, "lg": 5}, alignment=ft.Alignment.CENTER, content=rosca),
                    ft.Column(col={"xs": 12, "lg": 7}, spacing=0,
                              horizontal_alignment=ft.CrossAxisAlignment.STRETCH if layout["estreita"]
                              else ft.CrossAxisAlignment.START,
                              controls=linhas + [ft.Container(height=8), nota]),
                ]),
            ]))

        def bloco_comparacao(total):
            modo, ano, mes = periodo_atual()
            if modo == "anual":
                anterior_rotulo = str(ano - 1)
                total_anterior, _ = database.resumo_do_periodo(usuario_atual["id"], *intervalo_do_periodo("anual", ano - 1))
                sujeito = "O total do ano"
            else:
                a, m = mes_anterior(ano, mes)
                anterior_rotulo = MESES_PT[m - 1].lower()
                total_anterior, _ = database.resumo_do_periodo(usuario_atual["id"], *intervalo_do_periodo("mensal", a, m))
                sujeito = "O total do mês"
            comparacao = comparacao_com_anterior(total, total_anterior)
            frase = {"aumento": f"{sujeito} aumentou em", "reducao": f"{sujeito} diminuiu em",
                     "igual": f"{sujeito} não mudou", "sem_base": f"Sem gastos em {anterior_rotulo}",
                     "sem_gastos": "Nenhuma conta nos dois períodos"}[comparacao["tipo"]]
            cor = {"aumento": cores.variacao_aumento, "reducao": cores.variacao_reducao}.get(
                comparacao["tipo"], cores.texto_principal)
            direita = [ft.Text(comparacao["destaque"], size=24 if comparacao["tipo"] in ("aumento", "reducao") else 16,
                               weight=ft.FontWeight.BOLD, color=cor, text_align=ft.TextAlign.RIGHT)]
            if comparacao["complemento"]:
                direita.append(ft.Text(f"({comparacao['complemento']})", size=14, color=cor,
                                       text_align=ft.TextAlign.RIGHT))
            # Largura total: texto à esquerda e variação à direita; em janela
            # estreita as duas partes se empilham (ResponsiveRow).
            return cartao(bgcolor=cores.grafico_comparacao_fundo, borda=cores.grafico_comparacao_fundo,
                          conteudo=ft.ResponsiveRow(
                spacing=16, run_spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(col={"xs": 12, "sm": 8}, spacing=16, controls=[
                        circulo_icone(ft.Icons.BAR_CHART, cores.texto_secundario),
                        ft.Column(expand=True, spacing=2, controls=[
                            ft.Text(f"Comparado a {anterior_rotulo}", size=17, weight=ft.FontWeight.BOLD,
                                    color=cores.texto_principal),
                            ft.Text(frase, size=14, color=cores.texto_secundario),
                        ]),
                    ]),
                    ft.Column(col={"xs": 12, "sm": 4}, spacing=0, horizontal_alignment=ft.CrossAxisAlignment.END,
                              controls=direita),
                ],
            ))

        def atualizar():
            modo, ano, mes = periodo_atual()
            inicio, fim = intervalo_do_periodo(modo, ano, mes)
            total, pago = database.resumo_do_periodo(usuario_atual["id"], inicio, fim)
            itens = ordenar_distribuicao(database.gastos_por_categoria(usuario_atual["id"], inicio, fim))
            corpo.controls = [
                ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
                    alternador((("mensal", "Mensal"), ("anual", "Anual")), estado["modo"], escolher_modo),
                ]),
                bloco_navegacao(),
                bloco_totais(total, pago),
                bloco_evolucao(),
                bloco_categorias(total, itens),
                bloco_comparacao(total),
            ]
            if not total:
                corpo.controls.insert(2, ft.Text("Ainda não há dados para exibir neste período.", size=14,
                                                 color=cores.texto_secundario, text_align=ft.TextAlign.CENTER))
            page.update()

        cabecalho = ft.Row(spacing=14, vertical_alignment=ft.CrossAxisAlignment.START, controls=[
            ft.Icon(ft.Icons.BAR_CHART, size=40, color=cores.grafico_barra_destaque),
            ft.Column(expand=True, spacing=2, controls=[
                ft.Text("Gráfico", size=28, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
                ft.Text("Veja um resumo dos seus gastos e para onde seu dinheiro está indo.", size=14,
                        color=cores.texto_secundario),
            ]),
        ])
        conteudo = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, controls=[
            ft.Container(padding=ft.Padding(20, 32, 20, 24), content=ft.Column(
                data="tela_grafico", spacing=16, controls=[cabecalho, corpo])),
        ])
        raiz = ft.Column(expand=True, controls=[conteudo, barra_navegacao("grafico")])
        layout_desenhado = {"valor": layout_gastos_por_categoria(page.width)}

        def ao_redimensionar(e):
            # Redesenha só se a legenda mudar de forma (larga <-> estreita ou
            # outro tamanho de rosca) e só enquanto o Gráfico estiver na tela.
            if raiz not in page.controls:
                return
            novo = layout_gastos_por_categoria(page.width)
            if novo != layout_desenhado["valor"]:
                layout_desenhado["valor"] = novo
                atualizar()

        page.on_resize = ao_redimensionar
        page.add(raiz)
        atualizar()

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
                                         color=cores.texto_secundario, size=13),
                        padding=16,
                    )
                )
            else:
                for cat in categorias:
                    lista.controls.append(linha_categoria(cat))
            page.update()

        def linha_categoria(cat):
            return ft.Container(
                bgcolor=cores.fundo_card,
                border_radius=12,
                padding=12,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Text(cat["icone"] or cat["nome"][0].upper(),
                                                     size=16, color=cores.texto_sobre_cor_categoria),
                                    bgcolor=cat["cor"] or cores.categoria_cor_padrao,
                                    width=36,
                                    height=36,
                                    border_radius=18,
                                    alignment=ft.Alignment.CENTER,
                                ),
                                ft.Container(width=10),
                                ft.Text(cat["nome"], size=15, color=cores.texto_principal),
                            ]
                        ),
                        ft.Row(
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.ADD, icon_size=18, icon_color=cores.acao_primaria,
                                    tooltip="Nova conta nesta categoria",
                                    on_click=lambda e, c=cat: mostrar_tela_nova_conta(
                                        categoria_pre_selecionada=c["id"]),
                                ),
                                ft.IconButton(icon=ft.Icons.EDIT, icon_size=18,
                                              on_click=lambda e, c=cat: abrir_dialogo_categoria(
                                                  c, ao_salvar=lambda categoria_id: atualizar_lista()),
                                              icon_color=cores.texto_secundario),
                                ft.IconButton(icon=ft.Icons.DELETE, icon_size=18, icon_color=cores.acao_destrutiva,
                                              on_click=lambda e, c=cat: confirmar_exclusao(c)),
                            ]
                        ),
                    ],
                ),
            )

        def mostrar_erro_exclusao_categoria(cat):
            dialogo_erro = ft.AlertDialog(
                modal=True,
                title=ft.Text("Não foi possível excluir", color=cores.texto_principal),
                content=ft.Text(f"Não foi possível excluir '{cat['nome']}'.", color=cores.texto_principal),
                actions=[
                    ft.Button(content="Entendi", bgcolor=cores.acao_primaria, color=cores.texto_sobre_acao,
                              on_click=lambda e: page.pop_dialog()),
                ],
                bgcolor=cores.fundo_dialogo,
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
                title=ft.Text("Excluir categoria", color=cores.texto_principal),
                content=ft.Text(
                    f"Excluir '{cat['nome']}'? As contas associadas não serão excluídas, "
                    "apenas ficarão sem categoria.",
                    color=cores.texto_principal,
                ),
                actions=[
                    ft.TextButton(content="Cancelar", on_click=lambda e: page.pop_dialog(),
                                  style=ft.ButtonStyle(color=cores.acao_primaria)),
                    ft.Button(content="Excluir", bgcolor=cores.acao_destrutiva, color=cores.texto_sobre_acao, on_click=excluir),
                ],
                bgcolor=cores.fundo_dialogo,
            )
            page.show_dialog(dialogo)

        def ao_clicar_nova_categoria(e):
            # Checagem de limite + abertura do formulário agora vivem no
            # helper compartilhado abrir_criacao_categoria (promovido para
            # main(), reaproveitado também por Nova Conta/Editar Conta).
            abrir_criacao_categoria(ao_salvar=lambda categoria_id: atualizar_lista())

        cabecalho = ft.Container(
            bgcolor=cores.fundo_cabecalho_destaque,
            padding=ft.Padding(20, 40, 20, 20),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Categorias", size=20, weight=ft.FontWeight.BOLD, color=cores.texto_sobre_destaque),
                    ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=cores.acento_sobre_destaque, icon_size=28,
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
    #  TELA AJUSTES (ERS v6.0, 8.7; RF35, RF38, RF40, RF41, RF42)
    # ======================================================
    def mostrar_tela_ajustes():
        """
        Protótipo 12, sem as ações das Etapas 8-9 (e-mail, excluir conta):
        Conta (nome editável, e-mail só leitura), Segurança (Alterar senha),
        Aparência (Claro | Escuro), Sobre e privacidade (Termos de Uso e
        Política de Privacidade) e Sair da conta, com confirmação.
        """
        page.controls.clear()
        page.overlay.clear()
        page.padding = 0

        dados = database.obter_usuario(usuario_atual["id"]) or {}
        nome = dados.get("nome", usuario_atual["nome"] or "")
        email = dados.get("email", "")

        # ---------------------------------------------------------- auxiliares
        def circulo_icone(icone):
            return ft.Container(
                width=52, height=52, border_radius=26, alignment=ft.Alignment.CENTER,
                bgcolor=ft.Colors.with_opacity(0.14, cores.acao_primaria),
                content=ft.Icon(icone, color=cores.acao_primaria, size=26),
            )

        def secao(icone, titulo, subtitulo, linhas):
            itens = []
            for linha in linhas:
                itens += [ft.Divider(height=1, color=cores.divisor), linha]
            return ft.Container(
                bgcolor=cores.fundo_card, border_radius=16, padding=16,
                border=ft.Border.all(1, cores.borda_suave),
                content=ft.Row(spacing=16, vertical_alignment=ft.CrossAxisAlignment.START, controls=[
                    circulo_icone(icone),
                    ft.Column(expand=True, spacing=8, controls=[
                        ft.Column(spacing=2, controls=[
                            ft.Text(titulo, size=18, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
                            ft.Text(subtitulo, size=13, color=cores.texto_secundario),
                        ]),
                        *itens,
                    ]),
                ]),
            )

        def rotulo_e_valor(rotulo, valor, descricao=False):
            return ft.Column(expand=True, spacing=2, controls=[
                ft.Text(rotulo, size=14, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
                ft.Text(valor, size=14 if not descricao else 13,
                        color=cores.texto_secundario if descricao else cores.texto_principal,
                        selectable=not descricao),
            ])

        def estilo_botao_texto():
            return ft.ButtonStyle(color=cores.texto_principal)

        # ---------------------------------------------------------- nome (RF35)
        def abrir_dialogo_nome(e=None):
            nome_atual = usuario_atual["nome"] or ""
            campo = ft.TextField(
                label="Nome", value=nome_atual, autofocus=True, width=320,
                color=cores.texto_principal, cursor_color=cores.acao_primaria,
                border_color=cores.borda_campo, focused_border_color=cores.acao_primaria,
                label_style=ft.TextStyle(color=cores.texto_secundario),
                counter_style=ft.TextStyle(color=cores.texto_secundario),
                helper_style=ft.TextStyle(color=cores.texto_secundario),
                error_style=ft.TextStyle(color=cores.texto_erro),
            )
            erro = ft.Text("", size=12, color=cores.texto_erro, visible=False)
            botao_salvar = ft.Button(content="Salvar")

            def nome_normalizado():
                return texto_para_limite("nome_usuario", campo.value)

            def atualizar_botao_salvar():
                habilitado = nome_normalizado() != nome_atual
                botao_salvar.disabled = not habilitado
                botao_salvar.bgcolor = cores.acao_primaria if habilitado else cores.botao_desabilitado_fundo
                botao_salvar.color = cores.texto_sobre_acao if habilitado else cores.botao_desabilitado_texto

            def mostrar_erro(mensagem):
                erro.value = mensagem
                erro.visible = True
                page.update()

            def ao_mudar(ev):
                erro.visible = False
                atualizar_botao_salvar()

            def salvar(ev):
                novo = nome_normalizado()
                if novo == nome_atual:
                    return
                if not novo:
                    mostrar_erro("O nome é obrigatório.")
                    return
                mensagem_limite = erro_de_limite("nome_usuario", novo, limites.LIMITE_NOME_USUARIO)
                if mensagem_limite:
                    mostrar_erro(mensagem_limite)
                    return
                try:
                    gravado = database.alterar_nome_usuario(usuario_atual["id"], novo)
                except ValueError as ex:  # nome vazio ou LimiteDeCaracteresError (5.23)
                    mostrar_erro(str(ex))
                    return
                except Exception:
                    traceback.print_exc()
                    mostrar_erro("Não foi possível salvar o nome. Tente novamente.")
                    return
                if gravado is None:
                    mostrar_erro("Não encontramos a sua conta. Saia e entre novamente.")
                    return
                usuario_atual["nome"] = gravado  # só o valor devolvido pelo banco
                page.pop_dialog()
                mostrar_tela_ajustes()

            botao_salvar.on_click = salvar
            ligar_contador_de_limite(campo, "nome_usuario", limites.LIMITE_NOME_USUARIO, ao_mudar=ao_mudar)
            atualizar_botao_salvar()

            page.show_dialog(ft.AlertDialog(
                modal=True,
                title=ft.Text("Editar nome", color=cores.texto_principal),
                content=ft.Column(tight=True, spacing=8, controls=[campo, erro]),
                actions=[
                    ft.TextButton(content="Cancelar", style=estilo_botao_texto(),
                                  on_click=lambda ev: page.pop_dialog()),
                    botao_salvar,
                ],
                bgcolor=cores.fundo_dialogo,
            ))

        # ---------------------------------------------------------- senha (RF38)
        aviso_senha = ft.Row(visible=False, spacing=6, controls=[
            ft.Icon(ft.Icons.CHECK_CIRCLE, size=18, color=cores.acao_primaria),
            ft.Text("Senha alterada com sucesso.", size=13, color=cores.texto_principal),
        ])

        def abrir_dialogo_senha(e=None):
            """
            5.34: senha atual, nova senha e confirmação, ocultas e com opção de
            mostrar. As senhas nunca são transformadas (a atual pode ser antiga
            e conter espaços) e nunca aparecem em mensagens ou no terminal. Cada abertura cria campos
            novos; Cancelar e o sucesso também os esvaziam.
            """
            def campo_senha(rotulo, ajuda=None, autofocus=False):
                return ft.TextField(
                    label=rotulo, helper=ajuda, password=True, can_reveal_password=True,
                    autofocus=autofocus, width=320, color=cores.texto_principal,
                    **estilo_campo_texto(),
                )

            campo_atual = campo_senha("Senha atual", autofocus=True)
            campo_nova = campo_senha("Nova senha", ajuda=f"Mínimo de {database.SENHA_MINIMO} caracteres")
            campo_confirmacao = campo_senha("Confirmar nova senha")
            campos = (campo_atual, campo_nova, campo_confirmacao)
            erro = ft.Text("", size=12, color=cores.texto_erro, visible=False)
            botao_salvar = ft.Button(content="Salvar")

            def atualizar_botao_salvar():
                habilitado = all(c.value for c in campos)
                botao_salvar.disabled = not habilitado
                botao_salvar.bgcolor = cores.acao_primaria if habilitado else cores.botao_desabilitado_fundo
                botao_salvar.color = cores.texto_sobre_acao if habilitado else cores.botao_desabilitado_texto

            def ao_mudar(ev):
                erro.visible = False
                atualizar_botao_salvar()
                page.update()

            def mostrar_erro(mensagem):
                erro.value = mensagem
                erro.visible = True
                page.update()

            def descartar_campos():
                for campo in campos:
                    campo.value = ""

            def cancelar(ev):
                descartar_campos()
                page.pop_dialog()

            def salvar(ev):
                atual, nova, confirmacao = (c.value or "" for c in campos)
                if not (atual and nova and confirmacao):
                    return
                if nova != confirmacao:
                    mostrar_erro("A confirmação não confere com a nova senha.")
                    return
                mensagem_nova = erro_de_nova_senha(nova)
                if mensagem_nova:
                    mostrar_erro(mensagem_nova)
                    return
                try:
                    alterada = database.alterar_senha(usuario_atual["id"], atual, nova)
                except (database.SenhaAtualIncorretaError, database.SenhaInvalidaError) as ex:
                    mostrar_erro(str(ex))  # atual incorreta, nova inválida ou igual à atual
                    return
                except Exception as ex:
                    # Só o tipo da falha vai para o terminal: nenhuma senha em logs.
                    print(f"Sino: falha ao alterar a senha ({type(ex).__name__}).", file=sys.stderr)
                    mostrar_erro("Não foi possível alterar a senha. Tente novamente.")
                    return
                if not alterada:
                    mostrar_erro("Não encontramos a sua conta. Saia e entre novamente.")
                    return
                descartar_campos()
                page.pop_dialog()
                aviso_senha.visible = True
                page.update()

            for campo in campos:
                campo.on_change = ao_mudar
            botao_salvar.on_click = salvar
            atualizar_botao_salvar()
            aviso_senha.visible = False

            page.show_dialog(ft.AlertDialog(
                modal=True,
                title=ft.Text("Alterar senha", color=cores.texto_principal),
                content=ft.Column(tight=True, spacing=8, controls=[*campos, erro]),
                actions=[
                    ft.TextButton(content="Cancelar", style=estilo_botao_texto(), on_click=cancelar),
                    botao_salvar,
                ],
                on_dismiss=lambda ev: descartar_campos(),
                bgcolor=cores.fundo_dialogo,
            ))

        # ---------------------------------------------------------- tema (RF40)
        aviso_tema = ft.Text("", size=12, color=cores.texto_erro, visible=False)

        def escolher_tema(tema):
            if tema == cores.tema:
                return
            try:
                gravou = database.definir_tema(usuario_atual["id"], tema)
            except Exception:
                traceback.print_exc()
                gravou = False
            if not gravou:
                # Nada foi aplicado: a página continua no tema anterior.
                aviso_tema.value = "Não foi possível salvar o tema. O tema atual foi mantido."
                aviso_tema.visible = True
                page.update()
                return
            aplicar_tema(tema)
            mostrar_tela_ajustes()

        def opcao_tema(valor, rotulo, icone):
            selecionada = cores.tema == valor
            return ft.Container(
                data=f"tema_{valor}",
                padding=ft.Padding(14, 8, 16, 8),
                border_radius=10,
                border=ft.Border.all(2 if selecionada else 1,
                                     cores.acao_primaria if selecionada else cores.borda_campo),
                bgcolor=ft.Colors.with_opacity(0.12, cores.acao_primaria) if selecionada else None,
                on_click=lambda e: escolher_tema(valor),
                content=ft.Row(tight=True, spacing=8, controls=[
                    ft.Icon(ft.Icons.CHECK if selecionada else icone, size=18,
                            color=cores.acao_primaria if selecionada else cores.texto_secundario),
                    ft.Text(rotulo, size=14, color=cores.texto_principal,
                            weight=ft.FontWeight.BOLD if selecionada else ft.FontWeight.NORMAL),
                ]),
            )

        # ---------------------------------------------------------- sair (RF42)
        def confirmar_saida(e=None):
            page.show_dialog(ft.AlertDialog(
                modal=True,
                title=ft.Text("Sair da conta?", color=cores.texto_principal),
                content=ft.Text("Sua sessão será encerrada. Seus dados continuarão salvos no Sino.",
                                color=cores.texto_principal),
                actions=[
                    ft.TextButton(content="Cancelar", style=estilo_botao_texto(),
                                  on_click=lambda ev: page.pop_dialog()),
                    ft.Button(content="Sair", bgcolor=cores.acao_primaria, color=cores.texto_sobre_acao,
                              on_click=lambda ev: sessao.encerrar()),
                ],
                bgcolor=cores.fundo_dialogo,
            ))

        # ---------------------------------------------------------- montagem
        secao_conta = secao(ft.Icons.PERSON, "Conta", "Suas informações pessoais.", [
            ft.Row(controls=[
                rotulo_e_valor("Nome", nome),
                ft.OutlinedButton(
                    content="Editar", icon=ft.Icons.EDIT, on_click=abrir_dialogo_nome,
                    style=ft.ButtonStyle(color=cores.texto_principal, icon_color=cores.acao_primaria,
                                         side=ft.BorderSide(1, cores.acao_primaria)),
                ),
            ]),
            ft.Row(controls=[rotulo_e_valor("E-mail", email)]),
        ])
        item_alterar_senha = ft.Container(
            data="abrir_alterar_senha", border_radius=10, padding=ft.Padding(0, 6, 0, 6),
            on_click=abrir_dialogo_senha, ink=True,
            content=ft.Row(spacing=12, controls=[
                rotulo_e_valor("Alterar senha", "Defina uma nova senha para sua conta.", descricao=True),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, size=22, color=cores.texto_secundario),
            ]),
        )
        secao_seguranca = secao(ft.Icons.LOCK, "Segurança", "Mantenha sua conta protegida.", [
            ft.Column(spacing=6, controls=[item_alterar_senha, aviso_senha]),
        ])
        secao_aparencia = secao(ft.Icons.PALETTE, "Aparência", "Escolha o tema do aplicativo.", [
            ft.Row(wrap=True, run_spacing=8, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Column(spacing=2, controls=[
                    ft.Text("Tema", size=14, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
                    ft.Text("Selecione o modo de cor do Sino.", size=13, color=cores.texto_secundario),
                ]),
                ft.Row(tight=True, spacing=8, controls=[
                    opcao_tema("claro", "Claro", ft.Icons.LIGHT_MODE_OUTLINED),
                    opcao_tema("escuro", "Escuro", ft.Icons.DARK_MODE_OUTLINED),
                ]),
            ]),
            aviso_tema,
        ])
        item_sair = ft.Container(
            border_radius=10, padding=ft.Padding(0, 6, 0, 6), on_click=confirmar_saida, ink=True,
            content=ft.Row(spacing=12, controls=[
                ft.Icon(ft.Icons.LOGOUT, size=22, color=cores.acao_primaria),
                rotulo_e_valor("Sair da conta", "Encerre sua sessão atual. Seus dados serão mantidos.",
                               descricao=True),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, size=22, color=cores.texto_secundario),
            ]),
        )
        secao_sessao = secao(ft.Icons.LOGOUT, "Conta e sessão", "Gerencie sua sessão.", [item_sair])

        # RF41/5.37: documentos dentro do Sino; Voltar retorna a Ajustes.
        def item_documento(chave):
            rotulo, _ = documentos.DOCUMENTOS[chave]
            return ft.Container(
                data=f"abrir_{chave}", border_radius=10, padding=ft.Padding(0, 6, 0, 6), ink=True,
                on_click=lambda e: mostrar_documento(chave, mostrar_tela_ajustes),
                content=ft.Row(controls=[
                    ft.Text(rotulo, size=14, weight=ft.FontWeight.BOLD, color=cores.texto_principal, expand=True),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, size=22, color=cores.texto_secundario),
                ]),
            )

        secao_documentos = secao(ft.Icons.DESCRIPTION, "Sobre e privacidade",
                                 "Consulte os documentos e informações do aplicativo.",
                                 [item_documento("termos"), item_documento("politica")])

        cabecalho = ft.Column(spacing=2, controls=[
            ft.Text("Ajustes", size=28, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
            ft.Text("Gerencie suas informações, preferências e configurações do Sino.", size=14,
                    color=cores.texto_secundario),
        ])
        # Centralizado e adaptável: largura total em telas estreitas, 10/12 e
        # depois 8/12 da largura em telas maiores (protótipo 12).
        conteudo = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, controls=[
            ft.Container(padding=ft.Padding(16, 32, 16, 24), content=ft.ResponsiveRow(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[ft.Column(
                    data="tela_ajustes", col={"xs": 12, "md": 10, "xl": 8}, spacing=12,
                    controls=[cabecalho, secao_conta, secao_seguranca, secao_aparencia, secao_documentos,
                              secao_sessao],
                )],
            )),
        ])
        page.add(ft.Column(expand=True, controls=[conteudo, barra_navegacao("ajustes")]))
        page.update()

    # ======================================================
    #  TELA DE NOVA CONTA
    # ======================================================
    def mostrar_tela_nova_conta(categoria_pre_selecionada=None):
        page.controls.clear()
        page.overlay.clear()
        page.padding = 0

        data_selecionada = {"valor": None}

        campo_nome = ft.TextField(
            label="Nome da conta", hint_text="Ex: Aluguel, Internet...", color=cores.texto_principal,
            counter=texto_contador("", limites.LIMITE_NOME_CONTA),
            **estilo_campo_texto(),
        )
        campo_valor = ft.TextField(
            label="Valor", hint_text="R$ 0,00", keyboard_type=ft.KeyboardType.NUMBER, color=cores.texto_principal,
            **estilo_campo_texto(),
        )
        # RF04/RF32 (5.22): descrição opcional. 5.23: contador por grafemas e
        # mensagem ao passar do limite -- sem max_length (cortaria sem aviso).
        campo_descricao = ft.TextField(
            label="Descrição (opcional)", hint_text=f"Até {limites.LIMITE_DESCRICAO} caracteres",
            multiline=True, min_lines=2, max_lines=5, color=cores.texto_principal,
            counter=texto_contador("", limites.LIMITE_DESCRICAO),
            **estilo_campo_texto(),
        )
        ligar_contador_de_limite(campo_nome, "nome_conta", limites.LIMITE_NOME_CONTA)
        ligar_contador_de_limite(campo_descricao, "descricao", limites.LIMITE_DESCRICAO)
        campo_data = ft.TextField(
            label="Data de vencimento", hint_text="dd/mm/aaaa", read_only=True, expand=True, color=cores.texto_principal,
            **estilo_campo_texto(),
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
            options=montar_opcoes_categoria(), color=cores.texto_principal,
            **estilo_lista(),
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
        sem_termino = ft.Switch(value=False, active_color=cores.acao_primaria)

        ano_atual = date.today().year
        campo_mes_termino = ft.Dropdown(
            label="Mês", color=cores.texto_principal, expand=True,
            value=str(date.today().month),
            options=[ft.dropdown.Option(key=str(i), text=MESES_PT[i - 1]) for i in range(1, 13)],
            **estilo_lista(),
        )
        campo_ano_termino = ft.Dropdown(
            label="Ano", color=cores.texto_principal, expand=True,
            value=str(ano_atual),
            options=[ft.dropdown.Option(key=str(a), text=str(a)) for a in range(ano_atual, ano_atual + 11)],
            **estilo_lista(),
        )
        linha_termino = ft.Row(spacing=8, controls=[campo_mes_termino, campo_ano_termino], visible=False)

        cartao_termino = ft.Container(
            bgcolor=cores.fundo_card,
            border_radius=12,
            padding=14,
            visible=False,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Sem data de término", size=14, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
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
                                 color=cores.chip_ativo_texto if ativo else cores.chip_inativo_texto),
                bgcolor=cores.chip_ativo_fundo if ativo else cores.chip_inativo_fundo,
                border=None if ativo else ft.Border.all(1, cores.borda_suave),
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

        erro = ft.Text(value="", color=cores.texto_erro, size=12)

        def salvar(e):
            nome = campo_nome.value.strip() if campo_nome.value else ""
            valor = parse_valor(campo_valor.value)
            categoria_id = int(campo_categoria.value) if campo_categoria.value else None
            tipo = tipo_selecionado["valor"]
            data_termino = None

            descricao = limites.normalizar_descricao(campo_descricao.value)
            erro_textos = (
                erro_de_limite("nome_conta", nome, limites.LIMITE_NOME_CONTA)
                or erro_de_limite("descricao", descricao, limites.LIMITE_DESCRICAO)
            )

            if not nome:
                erro.value = "Digite um nome para a conta."
            elif erro_textos:
                erro.value = erro_textos
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

            try:
                if tipo == "unica":
                    database.criar_conta_unica(
                        usuario_atual["id"], nome, valor, data_selecionada["valor"].isoformat(),
                        categoria_id=categoria_id, descricao=descricao,
                    )
                else:
                    database.criar_serie_recorrente(
                        usuario_atual["id"], nome, valor, data_selecionada["valor"].isoformat(),
                        "mensal" if tipo == "mensal" else "anual",
                        data_termino=data_termino, categoria_id=categoria_id, descricao=descricao,
                    )
            except limites.LimiteDeCaracteresError as erro_limite:
                # Segunda barreira (a persistência valida de novo, 5.23).
                erro.value = str(erro_limite)
                page.update()
                return
            mostrar_tela_principal()

        cabecalho = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=20, icon_color=cores.texto_principal,
                              on_click=lambda e: mostrar_tela_principal()),
                ft.Text("Nova conta", size=18, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
                ft.Container(width=40),
            ],
        )

        cartao_tipo = ft.Container(
            bgcolor=cores.fundo_card,
            border_radius=12,
            padding=14,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text("Tipo de conta", size=14, weight=ft.FontWeight.BOLD, color=cores.texto_principal),
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
                                ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, icon_color=cores.acao_primaria,
                                              on_click=abrir_seletor_data),
                            ]),
                            campo_categoria,
                            campo_descricao,
                            ft.Container(height=8),
                            cartao_tipo,
                            ft.Container(height=8),
                            cartao_termino,
                            ft.Container(height=8),
                            erro,
                            ft.Button(
                                content="Salvar conta",
                                bgcolor=cores.acao_primaria,
                                color=cores.texto_sobre_acao,
                                on_click=salvar,
                            ),
                        ],
                    ),
                ),
            ],
        )

        page.add(conteudo)

    sessao.ao_encerrar = mostrar_tela_login  # Sair da conta (botão em Ajustes, passo 4)
    mostrar_tela_login()


if __name__ == "__main__":
    ft.run(main)
