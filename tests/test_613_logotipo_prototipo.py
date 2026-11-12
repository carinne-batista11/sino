"""
Protótipo 6.13 (logotipo) -- a imagem aprovada do logotipo "$ino" substitui a marca em texto
no login, ao lado da saudação em Início e (opção A, 12/11) na recuperação de senha e na
confirmação do código do cadastro.

Confere: o arquivo usado é o aprovado (sha256), a imagem entra inteira na proporção 1:1, o
enquadramento corta só a sobra preta fora do quadrado arredondado (nunca o texto "$ino"), as quatro
telas usam a mesma imagem (Início nos dois temas), a marca em texto antiga não aparece mais em
nenhuma delas e o código do cadastro continua funcionando (ServidorFalso, sem envio real).
"""
import hashlib
import os
import sys
import unittest
from unittest import mock

import apoio_banco
from apoio_banco import DataFixa, TesteComBancoTemporario, db

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import flet as ft  # noqa: E402
import main  # noqa: E402

SHA256_APROVADO = "1448953d7a2339c8336523925010bd7e0e258e2171a35509c4247cdbdd6305a1"
# Caixa do texto "$ino" (cifrão, sininho e "ino") na imagem original de 1254 px.
TEXTO_X = (215, 1090)
TEXTO_Y = (375, 835)


class Evento:
    def __init__(self, pagina, controle=None):
        self.page = pagina
        self.control = controle


def percorrer(controle):
    yield controle
    for atributo in ("controls", "content", "actions", "title", "icon"):
        filho = getattr(controle, atributo, None)
        if isinstance(filho, list):
            for item in filho:
                yield from percorrer(item)
        elif isinstance(filho, ft.Control):
            yield from percorrer(filho)


class TestArquivoEEnquadramento(unittest.TestCase):
    def test_arquivo_e_o_aprovado(self):
        with open(main.CAMINHO_DO_LOGOTIPO, "rb") as arquivo:
            conteudo = arquivo.read()
        self.assertEqual(hashlib.sha256(conteudo).hexdigest(), SHA256_APROVADO)
        self.assertEqual(main.origem_do_logotipo(), main.CAMINHO_DO_LOGOTIPO)
        self.assertTrue(os.path.isabs(main.CAMINHO_DO_LOGOTIPO))
        # PNG 1254 x 1254 (cabeçalho IHDR)
        self.assertEqual(conteudo[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(int.from_bytes(conteudo[16:20], "big"), main.LOGOTIPO_LADO_ORIGINAL)
        self.assertEqual(int.from_bytes(conteudo[20:24], "big"), main.LOGOTIPO_LADO_ORIGINAL)

    def test_recorte_nao_toca_no_texto(self):
        inicio = main.LOGOTIPO_RECORTE_INICIO
        fim = inicio + main.LOGOTIPO_RECORTE_LADO
        self.assertGreaterEqual(inicio, 55)           # dentro do quadrado arredondado
        self.assertLessEqual(fim, 1197)
        # Mesmo com o arredondamento dos cantos, o texto fica na faixa reta do recorte.
        raio = main.LOGOTIPO_RAIO_RELATIVO * main.LOGOTIPO_RECORTE_LADO
        for minimo, maximo in (TEXTO_X, TEXTO_Y):
            self.assertLess(inicio, minimo)
            self.assertGreater(fim, maximo)
        self.assertLess(inicio + raio, TEXTO_Y[1])     # canto não alcança a altura do texto
        self.assertGreater(fim - raio, TEXTO_Y[0])


class BaseLogotipo(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.uid = self.criar_usuario(email="logo@sino.com", senha="senha1234")
        self.pagina = mock.MagicMock()
        self.pagina.controls = []
        self.pagina.width = 380
        self.pagina.height = 900
        self.pagina.add.side_effect = lambda *controles: self.pagina.controls.extend(controles)

    def controles(self, tipo=None):
        todos = [c for raiz in self.pagina.controls for c in percorrer(raiz)]
        return [c for c in todos if tipo is None or isinstance(c, tipo)]

    def com_data(self, data):
        return [c for c in self.controles() if getattr(c, "data", None) == data]

    def clicar(self, controle):
        controle.on_click(Evento(self.pagina, controle))

    def conferir_logotipo(self, recipiente, lado):
        self.assertEqual((recipiente.width, recipiente.height), (lado, lado))
        self.assertEqual(recipiente.clip_behavior, ft.ClipBehavior.ANTI_ALIAS)
        self.assertAlmostEqual(recipiente.border_radius, round(lado * main.LOGOTIPO_RAIO_RELATIVO, 1))
        imagens = [c for c in percorrer(recipiente) if isinstance(c, ft.Image)]
        self.assertEqual(len(imagens), 1)
        imagem = imagens[0]
        self.assertEqual(imagem.src, main.CAMINHO_DO_LOGOTIPO)
        self.assertEqual(imagem.width, imagem.height)                       # proporção 1:1
        escala = lado / main.LOGOTIPO_RECORTE_LADO
        self.assertAlmostEqual(imagem.width, main.LOGOTIPO_LADO_ORIGINAL * escala)
        self.assertAlmostEqual(imagem.left, -main.LOGOTIPO_RECORTE_INICIO * escala)
        self.assertAlmostEqual(imagem.top, imagem.left)
        self.assertEqual(imagem.semantics_label, "Sino")
        # Sem a marca em texto antiga no mesmo lugar.
        self.assertFalse([c for c in percorrer(recipiente) if isinstance(c, ft.Text)])

    def entrar(self):
        main.main(self.pagina)
        campos = {c.label: c for c in self.controles(ft.TextField)}
        campos["E-mail"].value = "logo@sino.com"
        campos["Senha"].value = "senha1234"
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Entrar"))


class TestLogotipoNosDoisLocais(BaseLogotipo):
    def test_login(self):
        main.main(self.pagina)
        (logo,) = self.com_data("logotipo_login")
        self.conferir_logotipo(logo, main.LOGOTIPO_LADO_LOGIN)
        self.assertNotIn("$ino", [c.value for c in self.controles(ft.Text)])

    def test_inicio_ao_lado_da_saudacao_nos_dois_temas(self):
        for tema in ("claro", "escuro"):
            with self.subTest(tema=tema):
                db.definir_tema(self.uid, tema)
                self.pagina.controls.clear()
                self.entrar()
                (logo,) = self.com_data("logotipo_inicio")
                self.conferir_logotipo(logo, main.LOGOTIPO_LADO_INICIO)
                linha = next(c for c in self.controles(ft.Row) if logo in c.controls)
                textos = [t.value for c in linha.controls for t in percorrer(c) if isinstance(t, ft.Text)]
                self.assertEqual(textos[0], "Olá,")
                self.assertNotIn("$", textos)

    def test_recuperacao_de_senha(self):  # opção A (12/11): antes mantinha o círculo "$ino"
        main.main(self.pagina)
        self.clicar(next(b for b in self.controles(ft.TextButton) if b.content == "Esqueci minha senha"))
        (logo,) = self.com_data("logotipo_recuperacao")
        self.conferir_logotipo(logo, main.LOGOTIPO_LADO_LOGIN)
        self.assertNotIn("$ino", [c.value for c in self.controles(ft.Text)])
        # Formulário inalterado: mesmos campos e ações de antes.
        self.assertEqual([c.label for c in self.controles(ft.TextField) if c.visible],
                         ["E-mail"])
        self.assertTrue(any(getattr(b, "content", None) == "Voltar ao login"
                            for b in self.controles(ft.TextButton)))

    def test_marca_em_texto_antiga_removida_do_codigo(self):
        with open(main.__file__, encoding="utf-8") as arquivo:
            fonte = arquivo.read()
        self.assertNotIn("def logo_sino(", fonte)
        self.assertEqual(fonte.count("logotipo_sino(LOGOTIPO_LADO_LOGIN"), 3)   # login, código, recuperação
        self.assertEqual(fonte.count("logotipo_sino(LOGOTIPO_LADO_INICIO"), 1)


class TestSemArquivo(BaseLogotipo):
    def test_sem_o_arquivo_volta_a_marca_em_texto(self):
        with mock.patch.object(main, "CAMINHO_DO_LOGOTIPO", "/caminho/inexistente/logo_sino.png"):
            main.main(self.pagina)
            (logo,) = self.com_data("logotipo_login")
            self.assertFalse([c for c in percorrer(logo) if isinstance(c, ft.Image)])
            self.assertEqual(logo.content.value, "$ino")


from test_cadastro_codigo_interface import BaseCadastro  # noqa: E402


class TestConfirmacaoDoCodigo(BaseCadastro):
    def test_etapa_do_codigo_com_o_logotipo_e_fluxo_inalterado(self):
        pagina, _ = self.abrir_cadastro()
        self.ate_o_codigo(pagina)
        logos = [c for c in self.todos(pagina) if getattr(c, "data", None) == "logotipo_codigo"]
        self.assertEqual(len(logos), 1)
        (logo,) = logos
        lado = main.LOGOTIPO_LADO_LOGIN
        self.assertEqual((logo.width, logo.height), (lado, lado))
        (imagem,) = [c for c in percorrer(logo) if isinstance(c, ft.Image)]
        self.assertEqual(imagem.src, main.CAMINHO_DO_LOGOTIPO)
        self.assertEqual(imagem.width, imagem.height)
        self.assertNotIn("$ino", self.textos_visiveis(pagina))
        # O código continua concluindo o cadastro.
        self.confirmar(pagina, self.servidor.ultimo_codigo("carla@sino.com"))
        pagina.executar_pendentes()
        self.assertIn("Conta criada com sucesso! Faça login para continuar.", self.textos_visiveis(pagina))
        logos = [c for c in self.todos(pagina) if getattr(c, "data", None) == "logotipo_login"]
        self.assertEqual(len(logos), 1)


if __name__ == "__main__":
    unittest.main()
