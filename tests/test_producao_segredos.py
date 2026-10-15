"""
Ferramenta de segredos da produção restrita (servidor/ferramentas/
producao_segredos.py; ERS v7.0, E4/M8, decisão 5): segredos novos em pasta 700
e arquivos 600 fora do repositório, cópia de recuperação da CHAVE_HMAC e da
semente Ed25519, chave pública do KID prod-1 conferida contra wrangler.jsonc e
contra o cliente do aplicativo, chave da Resend só do terminal e conferência
sem mostrar valores. Também a proteção dos arquivos .env no .gitignore. Tudo
com dados FICTÍCIOS, em pastas temporárias; nada é publicado e nenhuma
credencial real é gerada nem pedida. As operações de pasta e de arquivo
privado reaproveitadas de t2_segredos.py têm os testes em test_t2_ferramentas.py.
"""

import contextlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(RAIZ, "servidor", "ferramentas"))
sys.path.insert(0, os.path.join(RAIZ, "backend"))

import destinatarios as dt  # noqa: E402
import producao_segredos as ps  # noqa: E402
import servico_codigos as sc  # noqa: E402

URL = "https://sino-servico-codigos.subdominio-ficticio.workers.dev"
EMAILS = ("autora1@exemplo.invalid", "Autora2@Exemplo.invalid", "autora1@exemplo.invalid")
CHAVE_RESEND_FICTICIA = "re_FICTICIA_sem_valor_real_000000"
BANCO_REAL = os.path.join(RAIZ, "database", "sino.db")
ARQUIVOS = sorted([".producao_segredos_estado", "app_producao.json", "recuperacao.json", "segredos.json"])


def pasta_temporaria(teste):
    """Pasta temporária do teste, removida ao final mesmo se ele falhar."""
    pasta = tempfile.TemporaryDirectory(prefix="sino_producao_")
    teste.addCleanup(pasta.cleanup)
    return os.path.realpath(pasta.name)


def modo(caminho):
    return stat.S_IMODE(os.lstat(caminho).st_mode)


def estado_protegido():
    """Repositório principal e banco real, sem abrir o banco (só metadados)."""
    status = subprocess.run(["git", "-C", RAIZ, "status", "--porcelain=v1", "--untracked-files=all"],
                            capture_output=True, text=True, check=True).stdout
    banco = os.stat(BANCO_REAL) if os.path.exists(BANCO_REAL) else None
    return status, banco and (banco.st_size, banco.st_mtime_ns, banco.st_atime_ns)


ESTADO_INICIAL = None


def setUpModule():
    global ESTADO_INICIAL
    ESTADO_INICIAL = estado_protegido()


def tearDownModule():
    if estado_protegido() != ESTADO_INICIAL:
        raise AssertionError("o repositório principal ou o banco real mudou durante os testes da produção")


@contextlib.contextmanager
def capturar():
    saida, erro = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
        yield saida, erro


def preparar_segredos(teste, pasta=None, emails=EMAILS, **extra):
    pasta = pasta or os.path.join(pasta_temporaria(teste), "segredos")
    with capturar() as (saida, erro):
        ps.preparar(pasta, URL, entrada=io.StringIO("".join(f"{e}\n" for e in emails)), **extra)
    return pasta, saida.getvalue() + erro.getvalue()


def ler_bytes(caminho):
    with open(caminho, "rb") as arquivo:
        return arquivo.read()


def ler_json(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def regravar_json(caminho, dados):
    """Altera um arquivo da pasta mantendo a permissão 600 (simula divergência)."""
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo)


def conteudo(pasta):
    return {n: ler_bytes(os.path.join(pasta, n)) for n in sorted(os.listdir(pasta))}


def configuracao_com_kid(teste, kid):
    caminho = os.path.join(pasta_temporaria(teste), "wrangler.jsonc")
    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write(f'// comentário\n{{\n  "vars": {{ "KID_ASSINATURA": "{kid}" }}\n}}\n')
    return caminho


def valores_sensiveis(pasta):
    segredos = ler_json(os.path.join(pasta, "segredos.json"))
    lista = segredos["DESTINATARIOS_PERMITIDOS"].split(",")
    return [*segredos.values(), *lista, *(lista[0].split(":")), *EMAILS, "autora2@exemplo.invalid"]


class Terminal(io.StringIO):
    def isatty(self):
        return True


# ======================================================================
#  Formatos e configuração
# ======================================================================

class TestUrl(unittest.TestCase):
    def test_aceitas(self):
        self.assertEqual(ps.validar_url(URL), URL)
        self.assertEqual(ps.validar_url(URL + "/"), URL)
        self.assertEqual(ps.validar_url("https://sino-servico-codigos.appsino.workers.dev"),
                         "https://sino-servico-codigos.appsino.workers.dev")

    def test_recusadas(self):
        for ruim in (
            "http://sino-servico-codigos.subdominio-ficticio.workers.dev",
            "https://sino-servico-codigos-t2.subdominio-ficticio.workers.dev",
            "https://sino-servico-codigos-teste.subdominio-ficticio.workers.dev",
            "https://sino-servico-codigos-dev.subdominio-ficticio.workers.dev",
            "https://sino-servico-codigos.a.b.workers.dev",
            "https://sino-servico-codigos.workers.dev",
            URL + ":8443", URL + "/v1", URL + "?x=1", URL + "#f",
            "https://u:s@sino-servico-codigos.subdominio-ficticio.workers.dev",
            "http://127.0.0.1:8787", "https://appsino.com.br", "", None,
        ):
            with self.subTest(url=ruim):
                with self.assertRaises(ps.Falha):
                    ps.validar_url(ruim)


class TestConfiguracaoDoRepositorio(unittest.TestCase):
    def test_kid_da_ferramenta_e_o_de_wrangler_jsonc(self):
        self.assertEqual(ps.kid_da_configuracao(), "prod-1")
        self.assertEqual(ps.KID_PRODUCAO, "prod-1")
        self.assertEqual(ps.CONFIGURACAO_PRODUCAO, os.path.join(RAIZ, "servidor", "wrangler.jsonc"))

    def test_kid_diferente_ou_configuracao_ilegivel_e_recusado(self):
        for kid in ("dev-1", "t2-1", "teste-1", "prod-2"):
            with self.subTest(kid=kid), self.assertRaises(ps.Falha):
                ps.kid_da_configuracao(configuracao_com_kid(self, kid))
        with self.assertRaises(ps.Falha):
            ps.kid_da_configuracao(os.path.join(pasta_temporaria(self), "inexistente.jsonc"))

    def test_preparar_recusa_configuracao_com_outro_kid_sem_criar_nada(self):
        pasta = os.path.join(pasta_temporaria(self), "nova")
        with self.assertRaises(ps.Falha):
            preparar_segredos(self, pasta=pasta, configuracao=configuracao_com_kid(self, "dev-1"))
        self.assertFalse(os.path.exists(pasta))

    def test_arquivos_env_protegidos_pelo_gitignore(self):
        # Só consulta as regras (check-ignore --no-index); nenhum arquivo é criado.
        caminhos = [".env", ".env.local", ".env.production", "servidor/.env", "servidor/.env.producao",
                    "backend/.env", "servidor/.dev.vars", "servidor/.dev.vars.producao"]
        r = subprocess.run(["git", "-C", RAIZ, "check-ignore", "--no-index", "--stdin"], input="\n".join(caminhos),
                           capture_output=True, text=True)
        self.assertEqual(sorted(r.stdout.split()), sorted(caminhos))
        r = subprocess.run(["git", "-C", RAIZ, "check-ignore", "--no-index", "servidor/.dev.vars.example"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)   # o modelo continua versionado
        rastreados = subprocess.run(["git", "-C", RAIZ, "ls-files", "--", "*.env", "*.env.*", ".env*"],
                                    capture_output=True, text=True, check=True).stdout
        self.assertEqual(rastreados, "")


# ======================================================================
#  preparar
# ======================================================================

class TestPreparar(unittest.TestCase):
    def test_arquivos_permissoes_estado_e_formatos(self):
        pasta, texto = preparar_segredos(self)
        self.assertEqual(modo(pasta), 0o700)
        self.assertEqual(sorted(os.listdir(pasta)), ARQUIVOS)
        for nome in os.listdir(pasta):
            self.assertEqual(modo(os.path.join(pasta, nome)), 0o600)
        self.assertEqual(ler_bytes(os.path.join(pasta, ".producao_segredos_estado")),
                         b"sino-producao-segredos\nconcluido\ncriada\n")
        segredos = ler_json(os.path.join(pasta, "segredos.json"))
        self.assertEqual(sorted(segredos), sorted(ps.CAMPOS_SEGREDOS))   # sem token e sem a chave da Resend
        self.assertRegex(segredos["CHAVE_HMAC"], r"^[0-9a-f]{64}$")
        self.assertRegex(segredos["CHAVE_ASSINATURA"], r"^[0-9a-f]{64}$")
        self.assertNotEqual(segredos["CHAVE_HMAC"], segredos["CHAVE_ASSINATURA"])
        chave = bytes.fromhex(segredos["CHAVE_HMAC"])
        lista = segredos["DESTINATARIOS_PERMITIDOS"].split(",")
        self.assertEqual(lista[0], dt.verificacao(chave))
        self.assertEqual(lista[1:], [dt.resumo(chave, "autora1@exemplo.invalid"),
                                     dt.resumo(chave, "autora2@exemplo.invalid")])
        self.assertIn("destinatários autorizados: 2; 1 repetido(s) ignorado(s)", texto)
        for valor in valores_sensiveis(pasta):
            self.assertNotIn(valor, texto)

    def test_copia_de_recuperacao_igual_aos_segredos(self):
        pasta, _ = preparar_segredos(self)
        segredos = ler_json(os.path.join(pasta, "segredos.json"))
        recuperacao = ler_json(os.path.join(pasta, "recuperacao.json"))
        self.assertEqual(sorted(recuperacao), sorted(ps.CAMPOS_RECUPERACAO))
        self.assertEqual(recuperacao["kid"], "prod-1")
        self.assertEqual(recuperacao["CHAVE_HMAC"], segredos["CHAVE_HMAC"])
        self.assertEqual(recuperacao["CHAVE_ASSINATURA"], segredos["CHAVE_ASSINATURA"])
        publica = ps.base.chave_publica_de_semente(bytes.fromhex(segredos["CHAVE_ASSINATURA"])).hex()
        self.assertEqual(recuperacao["chave_publica"], publica)
        self.assertNotIn("DESTINATARIOS_PERMITIDOS", recuperacao)   # regenerável a partir da CHAVE_HMAC

    def test_app_so_com_valores_publicos_e_compativel_com_o_cliente(self):
        pasta, _ = preparar_segredos(self)
        segredos = ler_json(os.path.join(pasta, "segredos.json"))
        app = ler_json(os.path.join(pasta, "app_producao.json"))
        self.assertEqual(sorted(app), ["chaves", "url"])
        self.assertEqual(app["url"], URL)
        for valor in segredos.values():
            self.assertNotIn(valor, json.dumps(app))
        with capturar():
            config = sc.configuracao_do_ambiente({"SINO_SERVICO_URL": app["url"], "SINO_SERVICO_CHAVES": app["chaves"]})
        self.assertEqual((config.url_base, list(config.chaves_publicas), config.token_acesso), (URL, ["prod-1"], None))

    def test_segredos_novos_a_cada_preparacao(self):
        a, _ = preparar_segredos(self)
        b, _ = preparar_segredos(self)
        sa, sb = ler_json(os.path.join(a, "segredos.json")), ler_json(os.path.join(b, "segredos.json"))
        for campo in ("CHAVE_HMAC", "CHAVE_ASSINATURA", "DESTINATARIOS_PERMITIDOS"):
            self.assertNotEqual(sa[campo], sb[campo])

    def test_nao_sobrescreve(self):
        pasta, _ = preparar_segredos(self)
        antes = conteudo(pasta)
        with self.assertRaises(ps.Falha):
            preparar_segredos(self, pasta=pasta)
        self.assertEqual(conteudo(pasta), antes)

    def test_email_invalido_ou_lista_vazia_nao_cria_nada_nem_mostra_o_endereco(self):
        tmp = pasta_temporaria(self)
        for emails in (("valido@exemplo.invalid", "sem-arroba"), ()):
            with self.subTest(emails=emails):
                pasta = os.path.join(tmp, f"p{len(emails)}")
                with capturar() as (saida, erro), self.assertRaises(ps.Falha) as falha:
                    ps.preparar(pasta, URL, entrada=io.StringIO("".join(f"{e}\n" for e in emails)))
                self.assertFalse(os.path.exists(pasta))
                for e in emails:
                    self.assertNotIn(e, str(falha.exception) + saida.getvalue() + erro.getvalue())

    def test_recusa_pasta_no_repositorio(self):
        with self.assertRaises(ps.Falha):
            preparar_segredos(self, pasta=os.path.join(RAIZ, "segredos_producao"))
        self.assertFalse(os.path.exists(os.path.join(RAIZ, "segredos_producao")))

    def test_main_com_url_invalida_nao_mostra_nada_sensivel(self):
        tmp = pasta_temporaria(self)
        with capturar(), self.assertRaises(SystemExit) as saida:
            ps.main(["preparar", "--pasta", os.path.join(tmp, "x"), "--url", "http://inseguro.exemplo"])
        self.assertIn("producao:", str(saida.exception.code))
        self.assertFalse(os.path.exists(os.path.join(tmp, "x")))


class TestFalhasNaPreparacao(unittest.TestCase):
    def falhar_em(self, posicao, excecao=OSError("disco cheio")):
        chamadas = []

        def criar(fd, nome, dados):
            chamadas.append(nome)
            if len(chamadas) == posicao:
                raise excecao
            ps.base.criar_privado(fd, nome, dados)
        return criar

    def test_falha_em_cada_gravacao_nao_deixa_credenciais(self):
        tmp = pasta_temporaria(self)
        for posicao in (1, 2, 3, 4):
            for excecao in (OSError("disco cheio"), KeyboardInterrupt()):
                with self.subTest(posicao=posicao, excecao=type(excecao).__name__):
                    pasta = os.path.join(tmp, f"nova{posicao}{type(excecao).__name__}")
                    with self.assertRaises(type(excecao)):
                        preparar_segredos(self, pasta=pasta, _criar=self.falhar_em(posicao, excecao))
                    self.assertFalse(os.path.exists(pasta))

    def test_falha_na_conclusao_desfaz_tudo(self):
        pasta = os.path.join(pasta_temporaria(self), "nova")
        with mock.patch.object(ps.base, "substituir_privado", side_effect=OSError("falha")):
            with self.assertRaises(OSError):
                preparar_segredos(self, pasta=pasta)
        self.assertFalse(os.path.exists(pasta))

    def test_pasta_preexistente_e_mantida_vazia(self):
        pasta = os.path.join(pasta_temporaria(self), "existente")
        os.mkdir(pasta, 0o700)
        with self.assertRaises(OSError):
            preparar_segredos(self, pasta=pasta, _criar=self.falhar_em(4))
        self.assertEqual(os.listdir(pasta), [])

    def criar_interrompida(self, pasta, criada=True, extras=()):
        os.mkdir(pasta, 0o700)
        ps.base.gravar_privado(os.path.join(pasta, ".producao_segredos_estado"),
                               ps.texto_do_estado(ps.INCOMPLETO, criada))
        ps.base.gravar_privado(os.path.join(pasta, "segredos.json"), '{"CHAVE_HMAC": "ficticia"}')
        for nome in extras:
            with open(os.path.join(pasta, nome), "w") as f:
                f.write("do usuário")

    def test_descartar_recupera_preparacao_interrompida(self):
        tmp = pasta_temporaria(self)
        criada = os.path.join(tmp, "criada")
        self.criar_interrompida(criada)
        with capturar() as (saida, _):
            ps.descartar(criada)
        self.assertFalse(os.path.exists(criada))
        self.assertNotIn("ficticia", saida.getvalue())
        existente = os.path.join(tmp, "existente")
        self.criar_interrompida(existente, criada=False)
        with capturar():
            ps.descartar(existente)
        self.assertEqual(os.listdir(existente), [])

    def test_descartar_recusa_concluida_alheia_ou_do_t2(self):
        concluida, _ = preparar_segredos(self)
        antes = conteudo(concluida)
        with self.assertRaises(ps.Falha):
            ps.descartar(concluida)
        self.assertEqual(conteudo(concluida), antes)
        alheia = os.path.join(pasta_temporaria(self), "alheia")
        self.criar_interrompida(alheia, extras=("notas.txt",))
        antes = conteudo(alheia)
        with self.assertRaises(ps.Falha):
            ps.descartar(alheia)
        self.assertEqual(conteudo(alheia), antes)
        # Pasta de outra ferramenta (estado do T2): não é reconhecida.
        do_t2 = os.path.join(pasta_temporaria(self), "t2")
        os.mkdir(do_t2, 0o700)
        ps.base.gravar_privado(os.path.join(do_t2, ".t2_segredos_estado"),
                               ps.base.texto_do_estado(ps.INCOMPLETO, True))
        with self.assertRaises(ps.Falha):
            ps.descartar(do_t2)
        self.assertEqual(os.listdir(do_t2), [".t2_segredos_estado"])


# ======================================================================
#  chave-resend
# ======================================================================

class TestChaveResend(unittest.TestCase):
    def ler(self, valor=CHAVE_RESEND_FICTICIA):
        return lambda: valor

    def test_acrescenta_sem_mostrar_e_sem_sobrescrever(self):
        pasta, _ = preparar_segredos(self)
        caminho = os.path.join(pasta, "segredos.json")
        antes = ler_json(caminho)
        recuperacao = ler_bytes(os.path.join(pasta, "recuperacao.json"))
        with capturar() as (saida, erro):
            ps.chave_resend(pasta, ler_chave=self.ler())
        depois = ler_json(caminho)
        self.assertEqual(depois, {**antes, "RESEND_API_KEY": CHAVE_RESEND_FICTICIA})
        self.assertEqual(modo(caminho), 0o600)
        self.assertEqual(sorted(os.listdir(pasta)), ARQUIVOS)
        self.assertEqual(ler_bytes(os.path.join(pasta, "recuperacao.json")), recuperacao)   # a chave da Resend não entra
        self.assertNotIn(CHAVE_RESEND_FICTICIA, saida.getvalue() + erro.getvalue())
        with self.assertRaises(ps.Falha):
            ps.chave_resend(pasta, ler_chave=self.ler("re_OUTRA_chave_ficticia_0000"))
        self.assertEqual(ler_json(caminho), depois)

    def test_formato_invalido_nao_grava_nem_ecoa(self):
        pasta, _ = preparar_segredos(self)
        antes = conteudo(pasta)
        for ruim in ("", "re_chave ficticia_x", "re_acentuação", "x" * 513, "re_ok\n"):
            with self.subTest(ruim=ruim[:10]):
                with capturar() as (saida, erro), self.assertRaises(ps.Falha) as falha:
                    ps.chave_resend(pasta, ler_chave=self.ler(ruim))
                if ruim:
                    self.assertNotIn(ruim, str(falha.exception) + saida.getvalue() + erro.getvalue())
        self.assertEqual(conteudo(pasta), antes)

    def test_recusa_preparacao_incompleta_e_permissoes_abertas(self):
        pasta, _ = preparar_segredos(self)
        os.chmod(os.path.join(pasta, "segredos.json"), 0o644)
        with self.assertRaises(ps.Falha):
            ps.chave_resend(pasta, ler_chave=self.ler())
        incompleta, _ = preparar_segredos(self)
        os.unlink(os.path.join(incompleta, ".producao_segredos_estado"))
        ps.base.gravar_privado(os.path.join(incompleta, ".producao_segredos_estado"),
                               ps.texto_do_estado(ps.INCOMPLETO, True))
        with self.assertRaises(ps.Falha):
            ps.chave_resend(incompleta, ler_chave=self.ler())

    def test_comando_recusa_pipe_sem_gravar_nem_mostrar(self):
        pasta, _ = preparar_segredos(self)
        antes = conteudo(pasta)
        with mock.patch.object(sys, "stdin", io.StringIO(CHAVE_RESEND_FICTICIA + "\n")), \
                capturar() as (saida, erro), self.assertRaises(SystemExit) as fim:
            ps.main(["chave-resend", "--pasta", pasta])
        self.assertIn("terminal interativo", str(fim.exception.code))
        self.assertNotIn(CHAVE_RESEND_FICTICIA, str(fim.exception.code) + saida.getvalue() + erro.getvalue())
        self.assertEqual(conteudo(pasta), antes)

    def test_leitura_padrao_e_a_do_terminal_sem_eco(self):
        # A mesma função do T2 (testada em test_t2_ferramentas.py), sem alternativa na linha de comando.
        import inspect

        padrao = inspect.signature(ps.chave_resend).parameters["ler_chave"].default
        self.assertIs(padrao, ps.base.ler_chave_do_terminal)
        self.assertEqual(ps.base.ler_chave_do_terminal(Terminal(), pedir=lambda p: CHAVE_RESEND_FICTICIA),
                         CHAVE_RESEND_FICTICIA)


# ======================================================================
#  conferir
# ======================================================================

class TestConferir(unittest.TestCase):
    def conferir(self, pasta, **extra):
        with capturar() as (saida, erro):
            pronta = ps.conferir(pasta, **extra)
        return pronta, saida.getvalue() + erro.getvalue()

    def test_sem_a_chave_da_resend_nao_esta_pronta(self):
        pasta, _ = preparar_segredos(self)
        antes = conteudo(pasta)
        pronta, texto = self.conferir(pasta)
        self.assertFalse(pronta)
        self.assertIn("lista com 2 destinatário(s)", texto)
        self.assertIn("aceita pelo cliente do aplicativo", texto)
        self.assertIn("NÃO está pronta", texto)
        for valor in valores_sensiveis(pasta):
            self.assertNotIn(valor, texto)
        self.assertEqual(conteudo(pasta), antes)   # só leitura

    def test_completa_esta_pronta_sem_mostrar_valores(self):
        pasta, _ = preparar_segredos(self)
        with capturar():
            ps.chave_resend(pasta, ler_chave=lambda: CHAVE_RESEND_FICTICIA)
        pronta, texto = self.conferir(pasta)
        self.assertTrue(pronta)
        self.assertIn("pronta para o deploy", texto)
        for valor in [*valores_sensiveis(pasta), CHAVE_RESEND_FICTICIA]:
            self.assertNotIn(valor, texto)
        with capturar():
            self.assertEqual(ps.main(["conferir", "--pasta", pasta]), 0)

    def test_divergencias_sao_recusadas_sem_mostrar_valores(self):
        outra_chave = bytes(range(32))
        casos = {
            "lista de outra CHAVE_HMAC": ("segredos.json", lambda d: {
                **d, "DESTINATARIOS_PERMITIDOS": dt.montar(outra_chave, ["autora1@exemplo.invalid"])[0]}),
            "lista com resumo repetido": ("segredos.json", lambda d: {
                **d, "DESTINATARIOS_PERMITIDOS": d["DESTINATARIOS_PERMITIDOS"] + ","
                + d["DESTINATARIOS_PERMITIDOS"].split(",")[1]}),
            "semente trocada": ("segredos.json", lambda d: {**d, "CHAVE_ASSINATURA": outra_chave.hex()}),
            "campo inesperado": ("segredos.json", lambda d: {**d, "TOKEN_ACESSO": "x" * 43}),
            "recuperação de outra semente": ("recuperacao.json", lambda d: {**d, "CHAVE_ASSINATURA": outra_chave.hex()}),
            "recuperação de outro KID": ("recuperacao.json", lambda d: {**d, "kid": "t2-1"}),
            "recuperação com texto não ASCII": ("recuperacao.json", lambda d: {**d, "CHAVE_HMAC": "ç" * 64}),
            "lista com verificação não ASCII": ("segredos.json", lambda d: {
                **d, "DESTINATARIOS_PERMITIDOS": "v1:" + "ç" * 64 + "," + "a" * 64}),
            "chave pública de outro KID": ("app_producao.json", lambda d: {
                **d, "chaves": d["chaves"].replace("prod-1:", "dev-1:")}),
            "chave pública de outra semente": ("app_producao.json", lambda d: {
                **d, "chaves": "prod-1:" + ps.base.chave_publica_de_semente(outra_chave).hex()}),
            "URL do T2": ("app_producao.json", lambda d: {
                **d, "url": "https://sino-servico-codigos-t2.subdominio-ficticio.workers.dev"}),
        }
        for nome, (arquivo, alterar) in casos.items():
            with self.subTest(caso=nome):
                pasta, _ = preparar_segredos(self)
                caminho = os.path.join(pasta, arquivo)
                regravar_json(caminho, alterar(ler_json(caminho)))
                with capturar() as (saida, erro), self.assertRaises(ps.Falha) as falha:
                    ps.conferir(pasta)
                texto = str(falha.exception) + saida.getvalue() + erro.getvalue()
                for valor in [*valores_sensiveis(pasta), outra_chave.hex()]:
                    self.assertNotIn(valor, texto)

    def test_configuracao_com_outro_kid_e_recusada(self):
        pasta, _ = preparar_segredos(self)
        with capturar(), self.assertRaises(ps.Falha):
            ps.conferir(pasta, configuracao=configuracao_com_kid(self, "dev-1"))

    def test_recusa_preparacao_incompleta_ou_pasta_aberta(self):
        pasta, _ = preparar_segredos(self)
        os.chmod(pasta, 0o755)
        with capturar(), self.assertRaises(ps.Falha):
            ps.conferir(pasta)
        os.chmod(pasta, 0o700)
        os.unlink(os.path.join(pasta, ".producao_segredos_estado"))
        with capturar(), self.assertRaises(ps.Falha):
            ps.conferir(pasta)

    def test_autorizacao_ficticia_no_formato_do_worker(self):
        import autorizacao_servico as au

        semente = bytes(range(32))
        token = ps.autorizacao_ficticia(semente, "prod-1", agora=1_800_000_000)
        chaves = sc.ler_chaves_publicas("prod-1:" + ps.base.chave_publica_de_semente(semente).hex())
        conteudo_ = au.verificar_assinatura(token, chaves)
        self.assertEqual((conteudo_.kid, conteudo_.finalidade, conteudo_.exp - conteudo_.iat),
                         ("prod-1", "cadastro", 600))
        with self.assertRaises(au.AutorizacaoInvalidaError):
            au.verificar_assinatura(token, sc.ler_chaves_publicas(
                "prod-1:" + ps.base.chave_publica_de_semente(bytes(32)).hex()))


if __name__ == "__main__":
    unittest.main()
