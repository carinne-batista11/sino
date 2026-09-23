"""
cores.py — Paletas de tema da interface do Sino (ERS v6.0, T3).

Cada cor é nomeada pelo PAPEL visual que cumpre (texto_principal,
fundo_card_total, status_atrasado...), nunca pelo hexadecimal: a mesma cor
pode cumprir papéis diferentes num tema e se separar em outro (ex.:
#0B1410 é o texto principal e também o fundo do card "Total do mês" no
tema Claro).

Uso em backend/main.py: `cores.texto_principal` devolve a cor do papel no
tema atual.

Nesta etapa só existe o tema Claro, que reproduz exatamente as cores
usadas antes da centralização. A paleta oficial das categorias NÃO faz
parte do tema: continua em database/db.py (PALETA_CORES_CATEGORIAS).
"""

PALETAS = {
    "claro": {
        # Fundos e superfícies
        "fundo_pagina": "#F4F4F1",
        "fundo_card": "white",
        "fundo_dialogo": "white",
        "fundo_card_total": "#0B1410",
        "fundo_marca": "#0B1410",
        "fundo_cabecalho_destaque": "#0B1410",
        "fundo_sugestao_emoji": "#F5F4F0",

        # Textos
        "texto_principal": "#0B1410",
        "texto_secundario": "#888780",
        "texto_marca": "#39D67C",
        "texto_sucesso": "#1D9E75",
        "texto_erro": "#A32D2D",
        "texto_sobre_acao": "white",
        "texto_sobre_destaque": "white",
        "texto_sobre_cor_categoria": "white",
        "texto_card_total": "white",
        "texto_secundario_card_total": "#888780",

        # Ações e controles
        "acao_primaria": "#1D9E75",
        "acao_destrutiva": "#A32D2D",
        "acao_pagamento": "#39D67C",
        "acento_sobre_destaque": "#39D67C",
        "controle_pago": "#39D67C",
        "controle_pendente": "#888780",
        "botao_secundario_fundo": "white",
        "botao_secundario_texto": "#0B1410",
        "botao_desabilitado_fundo": "#E5E4DE",
        "botao_desabilitado_texto": "#888780",
        "chip_ativo_fundo": "#1D9E75",
        "chip_ativo_texto": "white",
        "chip_inativo_fundo": "white",
        "chip_inativo_texto": "#0B1410",
        "filtro_ativo_fundo": "#39D67C",
        "filtro_ativo_texto": "#0B1410",
        "filtro_inativo_texto": "#888780",
        "filtro_inativo_borda": "#3A413B",
        "nav_ativo": "#1D9E75",
        "nav_inativo": "#888780",

        # Bordas e divisores
        "borda_suave": "#E5E4DE",
        "borda_campo": "#0B1410",
        "borda_selecao": "#1D9E75",
        "borda_selecao_cor": "#0B1410",
        "divisor": "#E5E4DE",

        # Status das contas
        "status_pago": "#1D9E75",
        "status_pendente": "#888780",
        "status_a_vencer": "#C9820A",
        "status_atrasado": "#A32D2D",

        # Card "Total do mês"
        "total_pago": "#39D67C",
        "total_pendente": "#E0A030",

        # Avisos
        "indicador_notificacao": "#A32D2D",
        "alerta_atraso_fundo": "#FBE4E4",
        "alerta_atraso_texto": "#A32D2D",
        "aviso_fundo": "#FDF1D6",
        "aviso_icone": "#B8860B",
        "aviso_texto": "#7A5B00",

        # Categorias sem cor definida (a paleta oficial fica em db.py)
        "categoria_sem_cor": "#E5E4DE",
        "categoria_cor_padrao": "#1D9E75",
    },
}

TEMA_PADRAO = "claro"
_tema_atual = TEMA_PADRAO


def __getattr__(nome):
    try:
        return PALETAS[_tema_atual][nome]
    except KeyError:
        raise AttributeError(f"cor {nome!r} não existe no tema {_tema_atual!r}") from None
