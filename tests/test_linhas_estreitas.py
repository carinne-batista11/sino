"""
ERS v7.0, E10 (M11) — linhas de conta em janelas estreitas (5.52, CT150).

Em Início, Ver status e Contas em atraso, abaixo da largura definida na
implementação (LARGURA_MINIMA_NOME_NA_LINHA para o nome), a linha de conta
se empilha: nome e subtítulo em cima, com toda a largura; valor, status e
botões embaixo. Nome sempre inteiro (sem reticências nem limite de linhas).
Ao redimensionar, só as linhas da tela aberta são refeitas, e só quando o
empilhamento muda. Verificação ESTRUTURAL dos controles criados (páginas
falsas sobre bancos temporários): a quebra de linha real do texto é do
Flutter e só se confere na validação manual.
"""

import unittest

from apoio_banco import db
from test_legibilidade_temas import TesteDeLegibilidade
from test_sessao_tema import CLARO, ESCURO, PaginaFalsa, main
from test_tela_principal import Evento, ft, percorrer

NOME_LONGO = "Supercalifragilisticexpialido"     # 29 caracteres numa palavra só
NOME_COM_EMOJI = "Escola 👩‍💻 das crianças"


class TestRegraDeLargura(unittest.TestCase):
    def test_inicio_com_duas_acoes(self):
        self.assertFalse(main.linha_de_conta_empilhada(380, 2))   # tamanho padrão: lado a lado
        self.assertFalse(main.linha_de_conta_empilhada(370, 2))
        self.assertTrue(main.linha_de_conta_empilhada(369, 2))
        self.assertTrue(main.linha_de_conta_empilhada(200, 2))

    def test_ver_status_e_atrasadas_sem_acoes(self):
        self.assertFalse(main.linha_de_conta_empilhada(270, 0))
        self.assertTrue(main.linha_de_conta_empilhada(269, 0))

    def test_largura_desconhecida_conta_como_larga(self):
        for largura in (None, "380", object()):
            self.assertFalse(main.linha_de_conta_empilhada(largura, 2))

    def test_sem_largura_minima_de_janela(self):
        self.assertTrue(main.linha_de_conta_empilhada(1, 2))
        self.assertTrue(main.linha_de_conta_empilhada(0, 0))


class BaseLinhas(TesteDeLegibilidade):
    def setUp(self):
        super().setUp()
        categoria = db.listar_categorias(self.bia)[0]["id"] if db.listar_categorias(self.bia) else None
        self.paga = db.criar_conta_unica(self.bia, "Luz", 120.0, "2026-09-05", categoria_id=categoria)
        db.marcar_conta_como_paga(self.paga, "2026-09-05")
        self.atrasada = db.criar_conta_unica(self.bia, NOME_LONGO, 50.0, "2026-09-01")
        self.pendente = db.criar_conta_unica(self.bia, NOME_COM_EMOJI, 700.0, "2026-09-20")

    def abrir_com_largura(self, largura, email="bia@sino.com", senha="senha5678"):
        pagina = PaginaFalsa().configurar()
        pagina.width = largura
        main.main(pagina)
        self.entrar(pagina, email, senha)
        return pagina

    def linhas(self, pagina):
        return [c for c in self.todos(pagina) if isinstance(c, ft.Container)
                and getattr(c, "data", None) in ("linha_conta", "linha_conta_empilhada")]

    def textos(self, controle):
        return [t.value for t in percorrer(controle) if isinstance(t, ft.Text) and t.value]

    def assert_nome_inteiro(self, linha, nome):
        texto = next(t for t in percorrer(linha) if isinstance(t, ft.Text) and t.value == nome)
        self.assertIsNone(texto.max_lines)
        self.assertNotEqual(texto.overflow, ft.TextOverflow.ELLIPSIS)
        self.assertFalse(texto.no_wrap)

    def assert_empilhada(self, linha, quantidade_de_acoes):
        self.assertEqual(linha.data, "linha_conta_empilhada")
        self.assertIsInstance(linha.content, ft.Column)
        nome_e_subtitulo, embaixo = linha.content.controls
        self.assertEqual(linha.content.horizontal_alignment, ft.CrossAxisAlignment.STRETCH)  # largura toda
        self.assertIsInstance(nome_e_subtitulo, ft.Column)
        valor_e_status, acoes = embaixo.controls
        self.assertIsNone(valor_e_status.width)
        self.assertTrue(valor_e_status.controls[0].value.startswith("R$"))
        self.assertEqual(len(acoes.controls), quantidade_de_acoes)

    def assert_lado_a_lado(self, linha):
        self.assertEqual(linha.data, "linha_conta")
        self.assertIsInstance(linha.content, ft.Row)
        self.assertTrue(linha.content.controls[0].expand)
        self.assertEqual(linha.content.controls[1].width, 92)


class TestInicio(BaseLinhas):
    def test_estreita_empilha_com_nomes_inteiros(self):  # CT150
        pagina = self.abrir_com_largura(330)
        linhas = self.linhas(pagina)
        self.assertEqual(len(linhas), 3)
        for linha in linhas:
            self.assert_empilhada(linha, 2)
        self.assert_nome_inteiro(next(l for l in linhas if NOME_LONGO in self.textos(l)), NOME_LONGO)
        self.assert_nome_inteiro(next(l for l in linhas if NOME_COM_EMOJI in self.textos(l)), NOME_COM_EMOJI)

    def test_padrao_e_larga_continuam_lado_a_lado(self):
        for largura in (380, 1200):
            with self.subTest(largura=largura):
                for linha in self.linhas(self.abrir_com_largura(largura)):
                    self.assert_lado_a_lado(linha)

    def test_botoes_e_clique_funcionam_empilhada(self):
        pagina = self.abrir_com_largura(300)
        linha = next(l for l in self.linhas(pagina) if NOME_COM_EMOJI in self.textos(l))
        pagar = next(b for b in percorrer(linha) if isinstance(b, ft.IconButton) and b.tooltip == "Marcar como paga")
        pagar.on_click(Evento(pagina, pagar))
        self.assertEqual(self.consultar("SELECT status FROM contas WHERE id = ?", (self.pendente,))[0][0], "pago")
        linha = next(l for l in self.linhas(pagina) if "Luz" in self.textos(l))
        self.assertTrue(any(isinstance(b, ft.IconButton) and b.tooltip == "Editar conta" for b in percorrer(linha)))
        linha.on_click(Evento(pagina, linha))
        self.assertTrue(any(getattr(c, "data", None) == "tela_detalhes" for c in self.todos(pagina)))

    def test_redimensionar_refaz_so_quando_muda(self):
        pagina = self.abrir_com_largura(1200)
        antes = self.linhas(pagina)
        pagina.width = 900
        pagina.on_resize(None)
        self.assertEqual([id(l) for l in self.linhas(pagina)], [id(l) for l in antes])   # nada refeito
        pagina.width = 340
        pagina.on_resize(None)
        for linha in self.linhas(pagina):
            self.assert_empilhada(linha, 2)
        pagina.width = 500
        pagina.on_resize(None)
        for linha in self.linhas(pagina):
            self.assert_lado_a_lado(linha)

    def test_redimensionar_fora_de_inicio_nao_mexe_na_tela(self):
        pagina = self.abrir_com_largura(1200)
        self.clicar(pagina, self.clicavel_com_texto(pagina, "Ajustes"))
        controles = list(pagina.controls)
        pagina.width = 300
        pagina.on_resize(None)
        self.assertEqual(pagina.controls, controles)


class TestVerStatusEAtrasadas(BaseLinhas):
    def ver_status(self, pagina):
        link = next(c for c in self.todos(pagina) if isinstance(c, ft.Container)
                    and isinstance(c.content, ft.Text) and c.content.value == "Ver status")
        self.clicar(pagina, link)

    def test_ver_status(self):  # CT150
        pagina = self.abrir_com_largura(260)
        self.ver_status(pagina)
        linhas = self.linhas(pagina)
        self.assertEqual(len(linhas), 3)
        for linha in linhas:
            self.assert_empilhada(linha, 0)
        pagina.width = 600
        pagina.on_resize(None)
        for linha in self.linhas(pagina):
            self.assert_lado_a_lado(linha)

    def test_ver_status_no_padrao_lado_a_lado(self):
        pagina = self.abrir_com_largura(380)
        self.ver_status(pagina)
        for linha in self.linhas(pagina):
            self.assert_lado_a_lado(linha)

    def test_contas_em_atraso(self):  # CT150
        pagina = self.abrir_com_largura(250)
        self.clicar(pagina, self.clicavel_com_texto(pagina, "Ver essas contas"))
        self.assertIn("Contas em atraso", self.textos(pagina.controls[0]))
        (linha,) = self.linhas(pagina)
        self.assert_empilhada(linha, 0)
        self.assert_nome_inteiro(linha, NOME_LONGO)
        pagina.width = 800
        pagina.on_resize(None)
        (linha,) = self.linhas(pagina)
        self.assert_lado_a_lado(linha)


class TestLegibilidadeEmpilhada(BaseLinhas):
    def test_dois_temas(self):  # RNF09
        db.definir_tema(self.ana, "escuro")
        db.criar_conta_unica(self.ana, NOME_LONGO, 10.0, "2026-09-01")      # atrasada também para Ana
        for email, senha, paleta in (("bia@sino.com", "senha5678", CLARO), ("ana@sino.com", "senha1234", ESCURO)):
            with self.subTest(tema="claro" if paleta is CLARO else "escuro"):
                pagina = self.abrir_com_largura(250, email, senha)          # empilha nas três telas
                self.assertTrue(self.linhas(pagina))
                self.assertTrue(all(l.data == "linha_conta_empilhada" for l in self.linhas(pagina)))
                self.registrar(pagina, f"Início estreito ({email})", paleta)
                self.clicar(pagina, self.clicavel_com_texto(pagina, "Ver essas contas"))
                self.assertTrue(all(l.data == "linha_conta_empilhada" for l in self.linhas(pagina)))
                self.registrar(pagina, f"Contas em atraso estreito ({email})", paleta)
        self.assertEqual(self.problemas_das_vistas(self.vistas, verificar_contraste=True), [])


if __name__ == "__main__":
    unittest.main()
