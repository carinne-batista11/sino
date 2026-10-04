"""
Cores do tema (ERS v6.0, T3; Etapa 0 e Etapa 6): todo papel de cor usado em
backend/main.py existe nos dois temas, main.py não tem cores fixas, os temas
Claro e Escuro têm os mesmos papéis, a troca de tema é validada e isolada
por sessão (instância de `cores.Paleta`) e o contraste dos pares principais
é verificado (RNF09, parcial: só os pares mapeados): desde a Etapa 10 (opção
A da paleta) os dois temas atendem todos os pares listados, sem limitações
conhecidas. (A paleta oficial das categorias continua em database/db.py,
fora do tema.)
"""

import os
import re
import sys
import unittest

import apoio_banco
from apoio_banco import db

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import cores  # noqa: E402

CAMINHO_MAIN = os.path.join(apoio_banco.RAIZ_PROJETO, "backend", "main.py")
COR_VALIDA = re.compile(r"^(#[0-9A-F]{6}|white)$")


def luminancia(cor):
    cor = "#FFFFFF" if cor == "white" else cor
    canais = (int(cor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(cor_a, cor_b):
    """Razão de contraste WCAG 2.x entre duas cores."""
    clara, escura = sorted((luminancia(cor_a), luminancia(cor_b)), reverse=True)
    return (clara + 0.05) / (escura + 0.05)


# RNF09 / WCAG 2.x, conforme o USO real de cada papel em backend/main.py.
# Texto (1.4.3, 4,5:1): todo texto do app é de tamanho normal -- secundário,
# status textual, rótulos pequenos e botões inclusive; negrito sozinho não
# o torna "texto grande".
MINIMO_TEXTO = 4.5
PARES_TEXTO = (
    ("texto_principal", "fundo_pagina"),
    ("texto_principal", "fundo_card"),
    ("texto_principal", "fundo_dialogo"),
    ("texto_secundario", "fundo_pagina"),
    ("texto_secundario", "fundo_card"),
    ("texto_secundario", "fundo_dialogo"),
    ("texto_erro", "fundo_pagina"),
    ("texto_erro", "fundo_card"),
    ("texto_sucesso", "fundo_pagina"),
    ("texto_sucesso", "fundo_card"),
    ("texto_sobre_acao", "acao_primaria"),
    ("texto_sobre_acao", "acao_destrutiva"),
    ("texto_sobre_pagamento", "acao_pagamento"),
    ("texto_sobre_acao", "grafico_barra_destaque"),
    ("texto_card_total", "fundo_card_total"),
    ("texto_secundario_card_total", "fundo_card_total"),
    ("total_pago", "fundo_card_total"),
    ("total_pendente", "fundo_card_total"),
    ("texto_marca", "fundo_marca"),
    ("texto_sobre_destaque", "fundo_cabecalho_destaque"),
    ("botao_secundario_texto", "botao_secundario_fundo"),
    ("chip_ativo_texto", "chip_ativo_fundo"),
    ("chip_inativo_texto", "chip_inativo_fundo"),
    ("filtro_ativo_texto", "filtro_ativo_fundo"),
    ("filtro_inativo_texto", "fundo_pagina"),
    ("status_pago", "fundo_card"),
    ("status_pendente", "fundo_card"),
    ("status_atrasado", "fundo_card"),
    # Pílulas de status: o fundo efetivo (12% da cor do status) é medido em
    # test_legibilidade_temas; aqui, o par sólido de referência.
    ("texto_pilula_pago", "fundo_pagina"),
    ("texto_pilula_pendente", "fundo_pagina"),
    ("nav_ativo", "fundo_card"),
    ("nav_inativo", "fundo_card"),
    ("alerta_atraso_texto", "alerta_atraso_fundo"),
    ("aviso_texto", "aviso_fundo"),
    ("acao_primaria", "fundo_pagina"),       # "Ver status"
    ("acao_primaria", "fundo_card"),
    ("texto_sem_categoria", "fundo_card"),    # rótulo "Sem categoria"
    ("variacao_aumento", "fundo_card"),
    ("variacao_reducao", "fundo_card"),
    ("grafico_barra_destaque", "fundo_card"),  # rótulo do mês em destaque
)
# Não texto (1.4.11, 3:1): ícones, bordas de campo e barras do gráfico.
MINIMO_NAO_TEXTO = 3.0
PARES_NAO_TEXTO = (
    ("acao_destrutiva", "fundo_card"),         # ícone de excluir
    ("acento_sobre_destaque", "fundo_cabecalho_destaque"),
    ("grafico_total_icone", "grafico_total_fundo"),
    ("grafico_pago_icone", "grafico_pago_fundo"),
    ("borda_campo", "fundo_card"),
    ("status_a_vencer", "fundo_card"),         # sem uso atual em main.py (Parcela usa detalhes_icone)
    ("detalhes_icone", "fundo_card"),          # ícones informativos de Detalhes (círculo medido nas telas)
    ("controle_pago", "fundo_card"),
    ("controle_pendente", "fundo_card"),
    ("aviso_icone", "aviso_fundo"),
    ("grafico_barra", "fundo_card"),
    ("grafico_barra_destaque", "grafico_progresso_fundo"),
    ("sem_categoria", "fundo_card"),          # fatias e círculos de "Sem categoria"
)
# Limitações conhecidas do Claro: a lista ficou vazia na Etapa 10 (opção A da
# paleta, RNF09). Continua exata -- o teste falha se um par voltar a ficar
# abaixo do mínimo sem ser registrado aqui. Cobertura: só os pares listados
# acima (papéis e usos mapeados); não é uma auditoria de todos os pixels.
LIMITACOES_CONHECIDAS_CLARO = set()


def pares_com_minimo():
    return [(f, b, MINIMO_TEXTO) for f, b in PARES_TEXTO] + [(f, b, MINIMO_NAO_TEXTO) for f, b in PARES_NAO_TEXTO]


class TesteSemContaminarTema(unittest.TestCase):
    """O tema padrão do módulo nunca pode mudar por efeito de um teste."""

    def tearDown(self):
        self.assertFalse(hasattr(cores, "_tema_atual"))
        self.assertEqual(cores.texto_principal, cores.PALETAS[cores.TEMA_PADRAO]["texto_principal"])


class TestCores(TesteSemContaminarTema):
    def setUp(self):
        with open(CAMINHO_MAIN, encoding="utf-8") as arquivo:
            self.codigo_main = arquivo.read()

    def test_papeis_usados_existem_nos_dois_temas(self):
        api_da_paleta = {nome for nome in dir(cores.Paleta) if not nome.startswith("_")}  # ex.: cores.tema
        usados = set(re.findall(r"(?<![\w.])cores\.([a-z_]+)", self.codigo_main)) - api_da_paleta
        self.assertTrue(usados)
        for tema in cores.TEMAS:
            with self.subTest(tema=tema):
                self.assertEqual(usados - set(cores.PALETAS[tema]), set())

    def test_paridade_de_papeis(self):
        self.assertEqual(list(cores.PALETAS["escuro"]), list(cores.PALETAS["claro"]))

    def test_valores_validos(self):
        for tema in cores.TEMAS:
            for papel, valor in cores.PALETAS[tema].items():
                with self.subTest(tema=tema, papel=papel):
                    self.assertRegex(valor, COR_VALIDA)

    def test_sem_cor_fixa_em_main(self):
        self.assertEqual(re.findall(r'"#[0-9A-Fa-f]{3,8}"|"white"', self.codigo_main), [])

    def test_temas_e_padrao(self):
        self.assertEqual(cores.TEMAS, ("claro", "escuro"))
        self.assertEqual(tuple(cores.PALETAS), cores.TEMAS)
        self.assertEqual(cores.TEMAS, db.TEMAS)
        self.assertEqual(cores.TEMA_PADRAO, "claro")
        self.assertEqual(cores.TEMA_PADRAO, db.TEMA_PADRAO)
        self.assertEqual(cores.texto_principal, cores.PALETAS["claro"]["texto_principal"])

    def test_identidade_verde_e_categorias_preservadas_no_escuro(self):
        claro, escuro = cores.PALETAS["claro"], cores.PALETAS["escuro"]
        for papel in ("texto_marca", "acao_pagamento", "filtro_ativo_fundo", "categoria_cor_padrao",
                      "texto_sobre_cor_categoria"):
            with self.subTest(papel=papel):
                self.assertEqual(escuro[papel], claro[papel])
        # Etapa 10 (RNF09, opção A): no Claro, texto e botões usam o verde
        # acessível #16795A; o verde da marca #1D9E75 segue nos botões do
        # Escuro e, no Claro, onde não há texto.
        for papel in ("acao_primaria", "chip_ativo_fundo"):
            self.assertEqual(escuro[papel], "#1D9E75")
            self.assertEqual(claro[papel], "#16795A")
        for papel in ("borda_selecao", "categoria_cor_padrao"):
            self.assertEqual(claro[papel], "#1D9E75")
        # O ícone do total no Gráfico fica sobre um círculo translúcido; no
        # Claro usa o verde acessível para passar de 3:1 sobre o fundo efetivo.
        self.assertEqual(claro["grafico_total_icone"], "#16795A")
        verdes_da_marca = {"#1D9E75", "#39D67C"}
        self.assertIn(escuro["grafico_barra_destaque"], verdes_da_marca)
        self.assertIn(escuro["nav_ativo"], verdes_da_marca | {"#3DC08F"})
        cores_de_categoria = set(db.PALETA_CORES_CATEGORIAS)
        for tema in cores.TEMAS:
            self.assertNotIn(cores.PALETAS[tema]["sem_categoria"], cores_de_categoria)

    def test_papel_inexistente(self):
        with self.assertRaises(AttributeError):
            cores.papel_que_nao_existe


class TestPaleta(TesteSemContaminarTema):
    def test_padrao_e_claro(self):
        paleta = cores.Paleta()
        self.assertEqual(paleta.tema, "claro")
        self.assertEqual(paleta.fundo_pagina, cores.PALETAS["claro"]["fundo_pagina"])

    def test_consulta_no_tema_escolhido(self):
        paleta = cores.Paleta("escuro")
        self.assertEqual(paleta.tema, "escuro")
        for papel, valor in cores.PALETAS["escuro"].items():
            self.assertEqual(getattr(paleta, papel), valor)

    def test_troca_de_tema(self):
        paleta = cores.Paleta()
        paleta.definir_tema("escuro")
        self.assertEqual((paleta.tema, paleta.fundo_card), ("escuro", cores.PALETAS["escuro"]["fundo_card"]))
        paleta.definir_tema("claro")
        self.assertEqual((paleta.tema, paleta.fundo_card), ("claro", cores.PALETAS["claro"]["fundo_card"]))

    def test_tema_invalido_recusado(self):
        for tema in ("azul", "Escuro", "", None, "sistema"):
            with self.subTest(tema=tema):
                with self.assertRaises(cores.TemaInvalidoError):
                    cores.Paleta(tema)
                paleta = cores.Paleta("escuro")
                with self.assertRaises(ValueError):  # TemaInvalidoError é um ValueError
                    paleta.definir_tema(tema)
                self.assertEqual(paleta.tema, "escuro")  # nada foi alterado

    def test_validar_tema(self):
        for tema in cores.TEMAS:
            self.assertEqual(cores.validar_tema(tema), tema)
        with self.assertRaises(cores.TemaInvalidoError):
            cores.validar_tema("azul")

    def test_papel_inexistente_e_nomes_privados(self):
        paleta = cores.Paleta("escuro")
        with self.assertRaises(AttributeError):
            paleta.papel_que_nao_existe
        with self.assertRaises(AttributeError):
            paleta._qualquer

    def test_papeis_nao_colidem_com_a_api_da_paleta(self):
        self.assertEqual(set(cores.PALETAS["claro"]) & set(dir(cores.Paleta)), set())


class TestIsolamentoEntreSessoes(TesteSemContaminarTema):
    def test_troca_em_uma_sessao_nao_afeta_outra(self):
        sessao_a, sessao_b = cores.Paleta(), cores.Paleta()
        sessao_a.definir_tema("escuro")
        self.assertEqual(sessao_b.tema, "claro")
        self.assertEqual(sessao_b.fundo_pagina, cores.PALETAS["claro"]["fundo_pagina"])
        self.assertEqual(sessao_a.fundo_pagina, cores.PALETAS["escuro"]["fundo_pagina"])

    def test_troca_nao_altera_o_acesso_pelo_modulo(self):
        cores.Paleta().definir_tema("escuro")
        self.assertEqual(cores.fundo_pagina, cores.PALETAS["claro"]["fundo_pagina"])

    def test_modulo_nao_guarda_tema_mutavel(self):
        self.assertFalse(hasattr(cores, "_tema_atual"))
        self.assertFalse(hasattr(cores, "definir_tema"))


class TestContraste(TesteSemContaminarTema):
    def test_referencias_wcag(self):
        self.assertAlmostEqual(contraste("#000000", "white"), 21.0)
        self.assertAlmostEqual(contraste("#777777", "#777777"), 1.0)

    def test_escuro_atende_todos_os_pares(self):
        paleta = cores.Paleta("escuro")
        for frente, fundo, minimo in pares_com_minimo():
            with self.subTest(frente=frente, fundo=fundo):
                razao = contraste(getattr(paleta, frente), getattr(paleta, fundo))
                self.assertGreaterEqual(razao, minimo, f"{razao:.2f}")

    def test_claro_atende_todos_fora_das_limitacoes_conhecidas(self):
        paleta = cores.Paleta("claro")
        for frente, fundo, minimo in pares_com_minimo():
            if (frente, fundo) in LIMITACOES_CONHECIDAS_CLARO:
                continue
            with self.subTest(frente=frente, fundo=fundo):
                razao = contraste(getattr(paleta, frente), getattr(paleta, fundo))
                self.assertGreaterEqual(razao, minimo, f"{razao:.2f}")

    def test_limitacoes_conhecidas_do_claro_sao_exatas(self):
        paleta = cores.Paleta("claro")
        todos = {(f, b): m for f, b, m in pares_com_minimo()}
        self.assertLessEqual(LIMITACOES_CONHECIDAS_CLARO, set(todos))
        for frente, fundo in LIMITACOES_CONHECIDAS_CLARO:
            with self.subTest(frente=frente, fundo=fundo):
                razao = contraste(getattr(paleta, frente), getattr(paleta, fundo))
                self.assertLess(razao, todos[(frente, fundo)],
                                "par já atende o critério: retire-o das limitações conhecidas")

    def test_pares_sem_repeticao_e_papeis_existentes(self):
        pares = PARES_TEXTO + PARES_NAO_TEXTO
        self.assertEqual(len(set(PARES_TEXTO)), len(PARES_TEXTO))
        self.assertEqual(len(set(PARES_NAO_TEXTO)), len(PARES_NAO_TEXTO))
        self.assertEqual({p for par in pares for p in par} - set(cores.PALETAS["claro"]), set())


if __name__ == "__main__":
    unittest.main()
