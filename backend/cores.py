"""
cores.py — Paletas de tema da interface do Sino (ERS v6.0, T3).

Cada cor é nomeada pelo PAPEL visual que cumpre (texto_principal,
fundo_card_total, status_atrasado...), nunca pelo hexadecimal: a mesma cor
pode cumprir papéis diferentes num tema e se separar em outro (ex.:
#0B1410 é o texto principal e também o fundo do card "Total do mês" no
tema Claro).

Dois temas, com exatamente os mesmos papéis (5.36, RF40): "claro" (padrão)
e "escuro". Etapa 10 (RNF09, opção A): no Claro, o verde de texto e botões
passou a #16795A e o cinza secundário a #6C6B66; o verde da marca #1D9E75
continua onde não há texto (bordas de seleção, cor padrão de categoria) e o cinza reservado #888780 continua nas fatias de "Sem
categoria" (o rótulo usa `texto_sem_categoria`).

Isolamento entre sessões: o tema escolhido NÃO é estado global do módulo.
O Flet pode atender várias páginas no mesmo processo e executa os handlers
num pool de threads compartilhado; um `_tema_atual` global faria a troca de
tema de uma página mudar as cores da outra. Por isso cada sessão usa a sua
própria instância de `Paleta` (`paleta.texto_principal` devolve a cor do
papel no tema daquela instância). O acesso direto pelo módulo
(`cores.texto_principal`) é somente leitura e sempre devolve o tema padrão
-- usado por telas anteriores ao login (sempre Claro, P8) e pelos testes.

A paleta oficial das categorias NÃO faz parte do tema: continua em
database/db.py (PALETA_CORES_CATEGORIAS) e é a mesma nos dois temas.
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
        "texto_secundario": "#6C6B66",
        "texto_marca": "#39D67C",
        "texto_sucesso": "#16795A",
        "texto_erro": "#A32D2D",
        "texto_sobre_acao": "white",
        "texto_sobre_destaque": "white",
        "texto_sobre_cor_categoria": "white",
        "texto_card_total": "white",
        # Inicial de categoria sem emoji (tela Categorias): o texto escolhido
        # entre este e texto_sobre_cor_categoria é o de maior contraste com a
        # cor da categoria (>= 4,6:1 nas 30 cores da paleta oficial).
        "texto_escuro_sobre_cor_categoria": "#000000",
        "texto_secundario_card_total": "#888780",

        # Ações e controles
        "acao_primaria": "#16795A",
        "acao_destrutiva": "#A32D2D",
        "acao_pagamento": "#39D67C",
        "acento_sobre_destaque": "#39D67C",
        "controle_pago": "#24945A",
        "controle_pendente": "#888780",
        "botao_secundario_fundo": "white",
        "botao_secundario_texto": "#0B1410",
        "botao_desabilitado_fundo": "#E5E4DE",
        "botao_desabilitado_texto": "#888780",
        "chip_ativo_fundo": "#16795A",
        "chip_ativo_texto": "white",
        "chip_inativo_fundo": "white",
        "chip_inativo_texto": "#0B1410",
        "filtro_ativo_fundo": "#39D67C",
        "filtro_ativo_texto": "#0B1410",
        "filtro_inativo_texto": "#6C6B66",
        "filtro_inativo_borda": "#3A413B",
        "nav_ativo": "#16795A",
        "nav_inativo": "#6C6B66",

        # Bordas e divisores
        "borda_suave": "#E5E4DE",
        "borda_campo": "#0B1410",
        "borda_selecao": "#1D9E75",
        "borda_selecao_cor": "#0B1410",
        "divisor": "#E5E4DE",

        # Status das contas
        "status_pago": "#16795A",
        "status_pendente": "#6C6B66",
        "status_a_vencer": "#C9820A",
        "status_atrasado": "#A32D2D",
        # Texto das pílulas de status (Detalhes/Editar): a pílula mantém o
        # fundo com 12% da cor do status; só o texto escurece para passar de
        # 4,5:1 com margem sobre o fundo efetivo (5,07 e 5,18 sobre #F4F4F1).
        "texto_pilula_pago": "#126A4F",
        "texto_pilula_pendente": "#5E5D58",

        # Card "Total do mês"
        "total_pago": "#39D67C",
        "total_pendente": "#E0A030",

        # Avisos
        "indicador_notificacao": "#A32D2D",
        "alerta_atraso_fundo": "#FBE4E4",
        "alerta_atraso_texto": "#A32D2D",
        "aviso_fundo": "#FDF1D6",
        "aviso_icone": "#9A7000",
        "aviso_texto": "#7A5B00",

        # Categorias sem cor definida (a paleta oficial fica em db.py)
        "categoria_sem_cor": "#E5E4DE",
        # "Sem categoria" (conta sem categoria): cinza reservado, sem emoji --
        # ERS 8.4/5.25; mesmo valor de db.COR_RESERVADA_SEM_CATEGORIA.
        "sem_categoria": "#888780",
        # Rótulo "Sem categoria" (texto): o cinza secundário legível; a cor
        # reservada acima continua nas fatias e círculos (não texto, 3:1).
        "texto_sem_categoria": "#6C6B66",
        # Texto sobre o botão de pagamento (verde vivo): escuro, 9,88:1.
        "texto_sobre_pagamento": "#0B1410",

        # Ícones informativos de Detalhes (Valor, Vencimento, Categoria,
        # Parcela, Recorrência): um único verde sobre círculo com 12% dele;
        # 4,55:1 sobre o fundo efetivo (#E3EFEB).
        "detalhes_icone": "#16795A",

        # Tela Gráfico (Etapa 5, protótipo 10)
        "grafico_total_fundo": "#EEF7F2",
        "grafico_total_borda": "#D5EDE1",
        "grafico_total_icone": "#16795A",
        "grafico_pago_fundo": "#EEF4FB",
        "grafico_pago_borda": "#D8E6F5",
        "grafico_pago_icone": "#1565C0",
        "grafico_progresso_fundo": "#E3E7EC",
        "grafico_barra": "#3FA382",
        "grafico_barra_destaque": "#16795A",
        "grafico_comparacao_fundo": "#F0F0EC",
        "variacao_aumento": "#A32D2D",
        "variacao_reducao": "#16795A",
        "categoria_cor_padrao": "#1D9E75",
    },
    # Tema Escuro (RF40, T3): base neutra esverdeada, verdes da marca
    # preservados (#1D9E75/#39D67C) e tons de status/avisos clareados para
    # manter o contraste sobre fundo escuro (RNF09). Sobre os botões verdes
    # e vermelhos o texto é escuro (#0B1410): branco sobre #1D9E75 não chega
    # a 4,5:1. Acabamento visual fica para a Etapa 10.
    "escuro": {
        # Fundos e superfícies
        "fundo_pagina": "#0F1512",
        "fundo_card": "#18201C",
        "fundo_dialogo": "#1E2723",
        "fundo_card_total": "#10281E",
        "fundo_marca": "#1F2B25",
        "fundo_cabecalho_destaque": "#16241D",
        "fundo_sugestao_emoji": "#232C27",

        # Textos
        "texto_principal": "#E8EBE7",
        "texto_secundario": "#A3A8A2",
        "texto_marca": "#39D67C",
        "texto_sucesso": "#3DC08F",
        "texto_erro": "#F07A7A",
        "texto_sobre_acao": "#0B1410",
        "texto_sobre_destaque": "white",
        "texto_sobre_cor_categoria": "white",
        "texto_card_total": "white",
        "texto_escuro_sobre_cor_categoria": "#000000",  # cores de categoria não mudam com o tema
        "texto_secundario_card_total": "#A3A8A2",

        # Ações e controles
        "acao_primaria": "#1D9E75",
        "acao_destrutiva": "#E06666",
        "acao_pagamento": "#39D67C",
        "acento_sobre_destaque": "#39D67C",
        "controle_pago": "#39D67C",
        "controle_pendente": "#8E948E",
        "botao_secundario_fundo": "#232C27",
        "botao_secundario_texto": "#E8EBE7",
        "botao_desabilitado_fundo": "#2A322E",
        "botao_desabilitado_texto": "#7C827D",
        "chip_ativo_fundo": "#1D9E75",
        "chip_ativo_texto": "#0B1410",
        "chip_inativo_fundo": "#232C27",
        "chip_inativo_texto": "#E8EBE7",
        "filtro_ativo_fundo": "#39D67C",
        "filtro_ativo_texto": "#0B1410",
        "filtro_inativo_texto": "#A3A8A2",
        "filtro_inativo_borda": "#4A534D",
        "nav_ativo": "#3DC08F",
        "nav_inativo": "#8E948E",

        # Bordas e divisores
        "borda_suave": "#2C3530",
        "borda_campo": "#8E948E",
        "borda_selecao": "#3DC08F",
        "borda_selecao_cor": "#E8EBE7",
        "divisor": "#2C3530",

        # Status das contas
        "status_pago": "#3DC08F",
        "status_pendente": "#A3A8A2",
        "status_a_vencer": "#E0A030",
        "status_atrasado": "#F07A7A",
        "texto_pilula_pago": "#3DC08F",
        "texto_pilula_pendente": "#A3A8A2",

        # Card "Total do mês"
        "total_pago": "#39D67C",
        "total_pendente": "#E0A030",

        # Avisos
        "indicador_notificacao": "#F07A7A",
        "alerta_atraso_fundo": "#3A1F1F",
        "alerta_atraso_texto": "#F4A3A3",
        "aviso_fundo": "#3A3120",
        "aviso_icone": "#E0B040",
        "aviso_texto": "#F0D080",

        # Categorias sem cor definida (a paleta oficial fica em db.py)
        "categoria_sem_cor": "#3A423D",
        # "Sem categoria": cinza de EXIBIÇÃO clareado para o fundo escuro
        # (5.36). Não é gravado no banco: a cor reservada continua sendo
        # db.COR_RESERVADA_SEM_CATEGORIA.
        "sem_categoria": "#9A9F99",
        "texto_sem_categoria": "#9A9F99",
        "texto_sobre_pagamento": "#0B1410",

        "detalhes_icone": "#3DC08F",  # 5,87:1 sobre o círculo (#1C332A)

        # Tela Gráfico
        "grafico_total_fundo": "#15291F",
        "grafico_total_borda": "#1F3D2E",
        "grafico_total_icone": "#3DC08F",
        "grafico_pago_fundo": "#152230",
        "grafico_pago_borda": "#223850",
        "grafico_pago_icone": "#64B5F6",
        "grafico_progresso_fundo": "#2C3530",
        "grafico_barra": "#3F7F66",
        "grafico_barra_destaque": "#39D67C",
        "grafico_comparacao_fundo": "#232C27",
        "variacao_aumento": "#F07A7A",
        "variacao_reducao": "#3DC08F",
        "categoria_cor_padrao": "#1D9E75",
    },
}

TEMAS = ("claro", "escuro")  # os mesmos aceitos em usuarios.tema (db.TEMAS)
TEMA_PADRAO = "claro"


class TemaInvalidoError(ValueError):
    """Tema fora de TEMAS; nada foi alterado."""

    def __init__(self, tema):
        self.tema = tema
        super().__init__(f"tema inválido: {tema!r} (aceitos: {', '.join(TEMAS)})")


def validar_tema(tema):
    """Devolve `tema` se for um dos TEMAS; senão levanta TemaInvalidoError."""
    if tema not in TEMAS:
        raise TemaInvalidoError(tema)
    return tema


class Paleta:
    """
    Cores de UMA sessão: `Paleta("escuro").texto_principal`. Cada página
    cria a sua instância; trocar o tema de uma não afeta as outras.
    """

    def __init__(self, tema=TEMA_PADRAO):
        self._tema = validar_tema(tema)

    @property
    def tema(self):
        return self._tema

    def definir_tema(self, tema):
        """Troca o tema desta instância; tema inválido não altera nada."""
        self._tema = validar_tema(tema)

    def __getattr__(self, nome):
        # Só chamado para nomes que não são atributos da instância/classe.
        if nome.startswith("_"):
            raise AttributeError(nome)
        try:
            return PALETAS[self._tema][nome]
        except KeyError:
            raise AttributeError(f"cor {nome!r} não existe no tema {self._tema!r}") from None


def __getattr__(nome):
    """Acesso somente leitura pelo módulo: sempre o tema padrão (Claro)."""
    try:
        return PALETAS[TEMA_PADRAO][nome]
    except KeyError:
        raise AttributeError(f"cor {nome!r} não existe no tema {TEMA_PADRAO!r}") from None
