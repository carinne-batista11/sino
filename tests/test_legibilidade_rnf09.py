"""
RNF09 no encerramento da v6.0: complementa test_legibilidade_temas com o que
a varredura das telas autenticadas não alcançava.

  * Autenticação (sempre Claro, P8): Login, erro de login, Cadastro e suas
    recusas ("As senhas não coincidem."), tela do código (mensagens, erro,
    contagem do reenvio), faixa do modo de demonstração, serviço
    indisponível e os três passos de "Esqueci minha senha". Os campos dessas
    telas usam as cores do tema do Flet (tema_flet), medidas como tal.
  * Estados das telas autenticadas, nos dois temas: categoria sem emoji (a
    inicial aparece no círculo da cor da categoria), categoria sem cor,
    conta que vence hoje e a legenda do Gráfico com essas categorias.
  * Gráfico: cada fatia da rosca tem uma linha na legenda com nome, valor e
    percentual em texto -- as cores das categorias (pastéis, da paleta
    oficial, fora do tema) não são o único meio de identificar a fatia.

Mesma regra de contraste de test_legibilidade_temas: texto 4,5:1; ícones,
bordas e barras 3:1; controles desativados ficam fora (WCAG 1.4.3).
"""

from unittest import mock

import flet as ft
import flet_charts as fch

from apoio_banco import DataFixa, db
from apoio_interface_codigos import ComServicoFalso
from test_cores import MINIMO_TEXTO, contraste
from test_legibilidade_temas import TesteDeLegibilidade, percorrer_com_fundo
from test_sessao_tema import CLARO, ESCURO, main

import fluxos_codigo as fc  # noqa: E402 -- backend/ entra no caminho pelos módulos de apoio

SENHA = "senhaforte1"


class TestAutenticacaoLegivel(ComServicoFalso, TesteDeLegibilidade):
    """As telas de autenticação mudam os mesmos controles no lugar: cada uma é conferida ao ser registrada."""

    def setUp(self):
        super().setUp()
        self.problemas = []
        self.telas = 0

    def registrar_tela(self, pagina, local):
        self.vistas = []
        self.registrar(pagina, local, CLARO)
        self.problemas += self.problemas_das_vistas(self.vistas, verificar_contraste=True, estilo_do_tema=True)
        self.telas += 1

    def verificar_telas(self, minimo):
        self.assertGreaterEqual(self.telas, minimo)
        self.assertEqual(sorted(set(self.problemas)), [])

    def ir_ao_login(self, pagina):
        voltar = next((b for b in self.todos(pagina) if isinstance(b, (ft.TextButton, ft.Button))
                       and b.content in ("Já tem conta? Entrar", "Voltar ao login", "Voltar")), None)
        if voltar is not None:
            self.acionar(pagina, voltar)

    def test_telas_de_autenticacao_legiveis(self):
        db.criar_usuario("Bia", "bia@sino.com", SENHA, aceite_termos=True)
        self.executar("UPDATE usuarios SET email_verificado = 1")
        pagina, _ = self.abrir_app()
        self.registrar_tela(pagina, "Login")
        self.campo(pagina, "E-mail").value = "bia@sino.com"
        self.campo(pagina, "Senha").value = "errada123"
        self.acionar(pagina, self.botao(pagina, "Entrar"))
        self.registrar_tela(pagina, "Login/erro")

        # Cadastro: recusas antes do código e a tela do código.
        self.acionar(pagina, self.botao(pagina, "Não tem conta? Criar conta"))
        self.registrar_tela(pagina, "Cadastro")
        self.campo(pagina, "Nome completo").value = "Carla"
        self.campo(pagina, "E-mail").value = "carla@sino.com"
        self.campo(pagina, "Senha").value = SENHA
        self.campo(pagina, "Confirmar senha").value = SENHA + "x"
        next(c for c in self.todos(pagina) if isinstance(c, ft.Checkbox)).value = True
        self.acionar(pagina, self.botao(pagina, "Criar conta"))
        self.assertIn("As senhas não coincidem.", self.textos_visiveis(pagina))
        self.registrar_tela(pagina, "Cadastro/senhas diferentes")
        self.campo(pagina, "Senha").value = self.campo(pagina, "Confirmar senha").value = "curta"
        self.acionar(pagina, self.botao(pagina, "Criar conta"))
        self.registrar_tela(pagina, "Cadastro/senha curta")
        self.campo(pagina, "Senha").value = self.campo(pagina, "Confirmar senha").value = SENHA
        self.acionar(pagina, self.botao(pagina, "Criar conta"))
        pagina.executar_pendentes()
        self.assertIn("Confirme seu e-mail", self.textos_visiveis(pagina))
        self.registrar_tela(pagina, "Código (contagem do reenvio)")
        self.campo(pagina, "Código").value = "000000" if self.servidor.ultimo_codigo("carla@sino.com") != "000000" \
            else "111111"
        self.acionar(pagina, self.botao(pagina, "Confirmar"))
        pagina.executar_pendentes()
        self.registrar_tela(pagina, "Código/erro")

        # "Esqueci minha senha": e-mail, código e nova senha.
        pagina, _ = self.abrir_app()
        self.acionar(pagina, self.botao(pagina, "Esqueci minha senha"))
        self.registrar_tela(pagina, "Recuperação/e-mail")
        self.campo(pagina, "E-mail").value = "bia@sino.com"
        enviar = next(b for b in self.todos(pagina) if isinstance(b, ft.Button) and b.visible is not False)
        self.acionar(pagina, enviar)
        pagina.executar_pendentes()
        self.registrar_tela(pagina, "Recuperação/código")
        codigo = self.servidor.ultimo_codigo("bia@sino.com")
        self.assertIsNotNone(codigo)
        self.campo(pagina, "Código").value = codigo
        avancar = next(b for b in self.todos(pagina) if isinstance(b, ft.Button) and b.visible is not False)
        self.acionar(pagina, avancar)
        pagina.executar_pendentes()
        self.registrar_tela(pagina, "Recuperação/nova senha")

        self.verificar_telas(9)

    def test_servico_indisponivel_e_modo_de_demonstracao_legiveis(self):
        self.servico_configurado = False
        pagina, _ = self.abrir_app()
        self.acionar(pagina, self.botao(pagina, "Não tem conta? Criar conta"))
        self.campo(pagina, "Nome completo").value = "Carla"
        self.campo(pagina, "E-mail").value = "carla@sino.com"
        self.campo(pagina, "Senha").value = self.campo(pagina, "Confirmar senha").value = SENHA
        next(c for c in self.todos(pagina) if isinstance(c, ft.Checkbox)).value = True
        self.acionar(pagina, self.botao(pagina, "Criar conta"))
        self.assertIn(fc.MENSAGEM_NAO_CONFIGURADO, self.textos_visiveis(pagina))
        self.registrar_tela(pagina, "Cadastro/serviço indisponível")

        self.servico_configurado = True
        with mock.patch.object(main.fluxos_codigo, "modo_demonstracao", return_value=True):
            pagina, _ = self.abrir_app()
        self.acionar(pagina, self.botao(pagina, "Não tem conta? Criar conta"))
        self.campo(pagina, "Nome completo").value = "Carla"
        self.campo(pagina, "E-mail").value = "carla@sino.com"
        self.campo(pagina, "Senha").value = self.campo(pagina, "Confirmar senha").value = SENHA
        next(c for c in self.todos(pagina) if isinstance(c, ft.Checkbox)).value = True
        self.acionar(pagina, self.botao(pagina, "Criar conta"))
        pagina.executar_pendentes()
        self.assertIn(fc.AVISO_DEMONSTRACAO, self.textos_visiveis(pagina))
        self.registrar_tela(pagina, "Código (demonstração)")

        self.verificar_telas(2)


class TestEstadosLegiveis(TesteDeLegibilidade):
    """Categoria sem emoji, sem cor, conta que vence hoje e a legenda do Gráfico."""

    def popular_estados(self, usuario_id):
        db.inicializar_categorias_padrao(usuario_id)
        hoje = DataFixa.hoje.isoformat()   # "hoje" fixo dos testes
        cores_da_paleta = db.PALETA_CORES_CATEGORIAS
        self.sem_emoji = {}
        for i, cor in enumerate(cores_da_paleta[:10]):
            categoria = self.executar("INSERT INTO categorias (usuario_id, nome, icone, cor) VALUES (?, ?, NULL, ?)",
                                      (usuario_id, f"Inicial {chr(65 + i)}", cor))
            self.sem_emoji[cor] = categoria
            db.criar_conta_unica(usuario_id, f"Conta {chr(65 + i)}", 10.0 + i, hoje, categoria_id=categoria)
        sem_cor = self.executar("INSERT INTO categorias (usuario_id, nome, icone, cor) VALUES (?, 'Diversos', NULL, NULL)",
                                (usuario_id,))
        db.criar_conta_unica(usuario_id, "Hoje", 80.0, hoje, categoria_id=sem_cor)
        db.criar_conta_unica(usuario_id, "Sem cat", 20.0, hoje)

    def percorrer_estados(self, pagina, paleta):
        self.ir_para_inicio(pagina)
        self.registrar(pagina, "Início (vence hoje)", paleta)
        for nome in ("Hoje", "Conta A"):
            self.abrir_linha(pagina, nome)
            self.registrar(pagina, f"Detalhes/{nome}", paleta)
            self.ir_para_inicio(pagina)
        self.clicar(pagina, self.clicavel_com_texto(pagina, "Categorias"))
        self.registrar(pagina, "Categorias (sem emoji, sem cor)", paleta)
        self.clicar(pagina, self.clicavel_com_texto(pagina, "Gráfico"))
        self.registrar(pagina, "Gráfico (categorias sem emoji)", paleta)
        return pagina

    def legenda_completa(self, pagina):
        """Cada fatia da rosca tem uma linha da legenda com nome, valor (R$) e percentual."""
        rosca = next(c for c in self.todos(pagina) if isinstance(c, fch.PieChart))
        linhas = [c for c in self.todos(pagina) if isinstance(c, ft.Container) and c.border is not None
                  and isinstance(c.content, ft.Row) and len(c.content.controls) == 4
                  and isinstance(c.content.controls[0], ft.Container) and c.content.controls[0].width == 34]
        self.assertEqual(len(linhas), len(rosca.sections))
        for linha, fatia in zip(linhas, rosca.sections):
            circulo, nome, valor, percentual = linha.content.controls
            self.assertEqual(circulo.bgcolor, fatia.color)
            self.assertTrue(nome.value and valor.value.startswith("R$") and percentual.value.endswith("%"))

    def test_estados_no_claro(self):
        self.popular_estados(self.bia)
        pagina, _ = self.abrir_app()
        self.entrar(pagina, "bia@sino.com", "senha5678")
        self.percorrer_estados(pagina, CLARO)
        self.legenda_completa(pagina)
        self.verificar_vistas(verificar_contraste=True, minimo_de_vistas=4)

    def test_estados_no_escuro(self):
        self.popular_estados(self.ana)
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "ana@sino.com", "senha1234")
        self.assertEqual(sessao.cores.tema, "escuro")
        self.percorrer_estados(pagina, ESCURO)
        self.legenda_completa(pagina)
        self.verificar_vistas(verificar_contraste=True, minimo_de_vistas=4)

    def test_inicial_da_categoria_legivel_em_todas_as_cores_da_paleta(self):
        # A inicial (categoria sem emoji) aparece sobre a cor da categoria, que
        # não muda com o tema: o texto precisa de 4,5:1 em cada uma das 30 cores.
        for cor in db.PALETA_CORES_CATEGORIAS + [None]:
            with self.subTest(cor=cor):
                fundo = cor or CLARO["categoria_cor_padrao"]
                texto = main.texto_sobre_cor_de_categoria(fundo, CLARO["texto_sobre_cor_categoria"],
                                                          CLARO["texto_escuro_sobre_cor_categoria"])
                self.assertGreaterEqual(contraste(texto, fundo), MINIMO_TEXTO)
