"""
Ferramentas do ambiente T2 (servidor/ferramentas/t2_segredos.py e t2_app.py;
ERS v7.0, E4): segredos novos em pasta 700 e arquivos 600 fora do
repositório, com estado incompleto/concluído, desfazimento de falhas e sem
mostrar nada sensível; chave da Resend só do terminal; cópia isolada do app a
partir de uma revisão publicada, com banco próprio, ambiente fechado e
remoção ancorada em descritores. Tudo com dados FICTÍCIOS, em pastas
temporárias e num repositório Git descartável; o aplicativo nunca é
executado (Popen falso) e nenhuma pasta real é removida.
"""

import contextlib
import fcntl
import io
import json
import os
import shutil
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
import servico_codigos as sc  # noqa: E402
import t2_app  # noqa: E402
import t2_segredos as t2s  # noqa: E402

URL = "https://sino-servico-codigos-t2.subdominio-ficticio.workers.dev"
EMAILS = ("autora1@exemplo.invalid", "Autora2@Exemplo.invalid", "autora1@exemplo.invalid")
CHAVE_RESEND_FICTICIA = "re_FICTICIA_sem_valor_real_000000"
BANCO_REAL = os.path.join(RAIZ, "database", "sino.db")
GIT_ISOLADO = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
CREDENCIAIS_FICTICIAS = {
    "CLOUDFLARE_API_TOKEN": "cf_ficticio_0001", "RESEND_API_KEY": "re_ficticia_0002",
    "AWS_SECRET_ACCESS_KEY": "aws_ficticia_0003", "SSH_AUTH_SOCK": "/tmp/ficticio.sock",
    "LD_PRELOAD": "/tmp/ficticio.so", "PYTHONSTARTUP": "/tmp/ficticio.py", "PYTHONPATH": "/algum/lugar",
    "PYTHONHOME": "/outro/python", "GIT_DIR": "/tmp/ficticio.git", "SINO_MODO_DEMONSTRACAO": "1",
    "SINO_SERVICO_URL": "http://127.0.0.1:8787",
}


def pasta_temporaria(teste):
    """Pasta temporária do teste, removida ao final mesmo se ele falhar."""
    pasta = tempfile.TemporaryDirectory(prefix="sino_t2_")
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
    # Nenhuma gravação no repositório principal e nenhum acesso ao banco real
    # (nem leitura: o horário de acesso também não muda).
    if estado_protegido() != ESTADO_INICIAL:
        raise AssertionError("o repositório principal ou o banco real mudou durante os testes do T2")


@contextlib.contextmanager
def capturar():
    saida, erro = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
        yield saida, erro


def preparar_segredos(teste, pasta=None, emails=EMAILS, **extra):
    pasta = pasta or os.path.join(pasta_temporaria(teste), "segredos")
    with capturar() as (saida, erro):
        t2s.preparar(pasta, URL, entrada=io.StringIO("".join(f"{e}\n" for e in emails)), **extra)
    return pasta, saida.getvalue() + erro.getvalue()


def ler_bytes(caminho):
    with open(caminho, "rb") as arquivo:
        return arquivo.read()


def ler_json(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def conteudo(pasta):
    return {n: ler_bytes(os.path.join(pasta, n)) for n in sorted(os.listdir(pasta))}


class Terminal(io.StringIO):
    def isatty(self):
        return True


# ======================================================================
#  t2_segredos: URL, caminhos, Git e arquivos privados
# ======================================================================

class TestUrl(unittest.TestCase):
    def test_aceitas(self):
        self.assertEqual(t2s.validar_url(URL), URL)
        self.assertEqual(t2s.validar_url(URL + "/"), URL)

    def test_recusadas(self):
        for ruim in (
            "http://sino-servico-codigos-t2.subdominio-ficticio.workers.dev",
            "https://sino-servico-codigos-teste.subdominio-ficticio.workers.dev",
            "https://sino-servico-codigos.subdominio-ficticio.workers.dev",
            "https://sino-servico-codigos-t2.a.b.workers.dev",
            "https://sino-servico-codigos-t2.workers.dev",
            URL + ":8443", URL + "/v1", URL + "?x=1", URL + "#f",
            "https://u:s@sino-servico-codigos-t2.subdominio-ficticio.workers.dev",
            "http://127.0.0.1:8787", "https://appsino.com.br", "", None,
        ):
            with self.subTest(url=ruim):
                with self.assertRaises(t2s.Falha):
                    t2s.validar_url(ruim)


class TestCaminhos(unittest.TestCase):
    def test_recusa_caminhos_perigosos(self):
        tmp = pasta_temporaria(self)
        os.symlink(RAIZ, os.path.join(tmp, "atalho_para_o_projeto"))
        os.symlink(tmp, os.path.join(tmp, "atalho_para_tmp"))
        with open(os.path.join(tmp, "arquivo"), "w") as f:
            f.write("x")
        os.mkdir(os.path.join(tmp, "cheia"))
        with open(os.path.join(tmp, "cheia", "algo"), "w") as f:
            f.write("x")
        repo = os.path.join(tmp, "repo")
        subprocess.run(["git", "init", "-q", repo], check=True, env={**os.environ, **GIT_ISOLADO})
        for ruim in (
            "relativo/pasta",
            os.sep,
            os.path.expanduser("~"),
            os.path.join(RAIZ, "nova_pasta"),
            os.path.join(RAIZ, "database", "nova"),
            os.path.join(tmp, "atalho_para_o_projeto", "nova"),   # link no meio aponta para o projeto
            os.path.join(tmp, "atalho_para_tmp"),                 # o próprio destino é um link
            os.path.join(tmp, "inexistente", "nova"),             # pai inexistente
            os.path.join(repo, "nova"),                           # dentro de outro repositório Git
            os.path.join(tmp, "arquivo"),                         # existe e não é pasta
            os.path.join(tmp, "cheia"),                           # pasta não vazia
        ):
            with self.subTest(caminho=ruim):
                with self.assertRaises(t2s.Falha):
                    t2s.criar_pasta_privada(ruim)
        self.assertFalse(os.path.exists(os.path.join(RAIZ, "nova_pasta")))
        self.assertEqual(os.listdir(os.path.join(tmp, "cheia")), ["algo"])

    def test_mesma_pasta_por_outro_caminho_e_recusada(self):
        # Simula um bind mount: a identidade (dispositivo, inode) de uma pasta protegida.
        tmp = pasta_temporaria(self)
        info = os.stat(tmp)
        with mock.patch.object(t2s, "identidades_protegidas", return_value={(info.st_dev, info.st_ino)}):
            with self.assertRaises(t2s.Falha) as falha:
                t2s.conferir_destino(os.path.join(tmp, "nova"))
        self.assertIn("outro caminho", str(falha.exception))
        raiz = os.stat(RAIZ)
        self.assertIn((raiz.st_dev, raiz.st_ino), t2s.identidades_protegidas(RAIZ))

    def test_pasta_nova_ou_vazia_fica_700(self):
        tmp = pasta_temporaria(self)
        real, fd, criada = t2s.criar_pasta_privada(os.path.join(tmp, "nova"))
        os.close(fd)
        self.assertEqual((modo(real), criada), (0o700, True))
        vazia = os.path.join(tmp, "vazia")
        os.mkdir(vazia, 0o755)
        real, fd, criada = t2s.criar_pasta_privada(vazia)
        os.close(fd)
        self.assertEqual((modo(real), criada), (0o700, False))


class TestGitControlado(unittest.TestCase):
    def test_variaveis_do_git_do_usuario_nao_interferem(self):   # M6
        tmp = pasta_temporaria(self)
        repo = os.path.join(tmp, "repo")
        subprocess.run(["git", "init", "-q", repo], check=True, env={**os.environ, **GIT_ISOLADO})
        fora = os.path.join(tmp, "fora")
        os.mkdir(fora)
        with mock.patch.dict(os.environ, {"GIT_DIR": os.path.join(repo, ".git"), "GIT_WORK_TREE": repo}):
            self.assertFalse(t2s.em_repositorio_git(fora))
        ambiente = t2s.ambiente_git()
        for nome in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY"):
            self.assertNotIn(nome, ambiente)
        self.assertEqual((ambiente["GIT_NO_REPLACE_OBJECTS"], ambiente["GIT_CONFIG_GLOBAL"],
                          ambiente["GIT_CONFIG_NOSYSTEM"]), ("1", os.devnull, "1"))


class TestArquivosPrivados(unittest.TestCase):   # M1, M2
    def setUp(self):
        self.tmp = pasta_temporaria(self)

    def test_leitura_confere_o_descritor_aberto(self):
        caminho = os.path.join(self.tmp, "ok")
        t2s.gravar_privado(caminho, "conteúdo")
        self.assertEqual((t2s.ler_privado(caminho), modo(caminho)), ("conteúdo", 0o600))
        aberto = os.path.join(self.tmp, "aberto")
        t2s.gravar_privado(aberto, "x")
        os.chmod(aberto, 0o644)
        fifo = os.path.join(self.tmp, "fifo")
        os.mkfifo(fifo, 0o600)
        link = os.path.join(self.tmp, "link")
        os.symlink(caminho, link)
        for ruim in (aberto, fifo, link, os.path.join(self.tmp, "ausente")):
            with self.subTest(ruim=os.path.basename(ruim)):
                with self.assertRaises(t2s.Falha):
                    t2s.ler_privado(ruim)

    def test_troca_do_arquivo_depois_de_aberto_nao_engana_a_conferencia(self):
        caminho = os.path.join(self.tmp, "alvo")
        t2s.gravar_privado(caminho, "x")
        original = os.open
        def abrir_e_trocar(nome, flags, *a, **k):
            fd = original(nome, flags, *a, **k)
            os.chmod(fd, 0o644)   # muda depois de aberto: a conferência usa o descritor
            return fd
        with mock.patch.object(t2s.os, "open", side_effect=abrir_e_trocar):
            with self.assertRaises(t2s.Falha):
                t2s.ler_privado(caminho)

    def test_criacao_ancorada_nao_sobrescreve_nem_segue_links(self):
        fd = os.open(self.tmp, t2s.FLAGS_PASTA)
        self.addCleanup(os.close, fd)
        t2s.criar_privado(fd, "a", "1")
        with self.assertRaises(FileExistsError):
            t2s.criar_privado(fd, "a", "2")
        alvo = os.path.join(self.tmp, "alvo_do_link")
        os.symlink(alvo, os.path.join(self.tmp, "link"))
        with self.assertRaises(OSError):
            t2s.criar_privado(fd, "link", "3")
        self.assertFalse(os.path.exists(alvo))
        self.assertEqual(ler_bytes(os.path.join(self.tmp, "a")), b"1")

    def test_falha_na_escrita_apaga_so_o_arquivo_criado(self):
        fd = os.open(self.tmp, t2s.FLAGS_PASTA)
        self.addCleanup(os.close, fd)
        with mock.patch.object(t2s.os, "fsync", side_effect=OSError("disco")):
            with self.assertRaises(OSError):
                t2s.criar_privado(fd, "parcial", "x")
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "parcial")))


# ======================================================================
#  t2_segredos: preparar, descartar e chave-resend
# ======================================================================

class TestPreparar(unittest.TestCase):
    def test_arquivos_permissoes_estado_e_formatos(self):
        pasta, texto = preparar_segredos(self)
        self.assertEqual(modo(pasta), 0o700)
        self.assertEqual(sorted(os.listdir(pasta)), [".t2_segredos_estado", "app_t2.json", "segredos.json"])
        for nome in os.listdir(pasta):
            self.assertEqual(modo(os.path.join(pasta, nome)), 0o600)
        self.assertEqual(ler_bytes(os.path.join(pasta, ".t2_segredos_estado")), b"sino-t2-segredos\nconcluido\ncriada\n")
        segredos = ler_json(os.path.join(pasta, "segredos.json"))
        app = ler_json(os.path.join(pasta, "app_t2.json"))
        self.assertEqual(sorted(segredos), sorted(t2s.CAMPOS_SEGREDOS))
        self.assertNotIn("RESEND_API_KEY", segredos)   # nunca preenchida automaticamente
        self.assertRegex(segredos["CHAVE_HMAC"], r"^[0-9a-f]{64}$")
        self.assertRegex(segredos["CHAVE_ASSINATURA"], r"^[0-9a-f]{64}$")
        self.assertRegex(segredos["TOKEN_ACESSO"], r"^[A-Za-z0-9_-]{43}$")
        self.assertNotEqual(segredos["CHAVE_HMAC"], segredos["CHAVE_ASSINATURA"])
        chave = bytes.fromhex(segredos["CHAVE_HMAC"])
        lista = segredos["DESTINATARIOS_PERMITIDOS"].split(",")
        self.assertEqual(lista[0], dt.verificacao(chave))
        self.assertRegex(lista[0], r"^v1:[0-9a-f]{64}$")
        self.assertEqual(lista[1:], [dt.resumo(chave, "autora1@exemplo.invalid"), dt.resumo(chave, "autora2@exemplo.invalid")])
        self.assertEqual(sorted(app), ["chaves", "token", "url"])
        self.assertEqual(app["url"], URL)
        self.assertEqual(app["token"], segredos["TOKEN_ACESSO"])
        publica = t2s.chave_publica_de_semente(bytes.fromhex(segredos["CHAVE_ASSINATURA"]))
        self.assertEqual(app["chaves"], f"t2-1:{publica.hex()}")
        for valor in [*segredos.values(), *lista, app["chaves"].split(":")[1], *EMAILS, "autora2@exemplo.invalid"]:
            self.assertNotIn(valor, texto)
        self.assertIn("destinatários autorizados: 2", texto)

    def test_compativel_com_o_cliente_do_app(self):
        pasta, _ = preparar_segredos(self)
        app = ler_json(os.path.join(pasta, "app_t2.json"))
        with capturar():
            config = sc.configuracao_do_ambiente(
                {"SINO_SERVICO_URL": app["url"], "SINO_SERVICO_CHAVES": app["chaves"], "SINO_SERVICO_TOKEN": app["token"]},
            )
        self.assertEqual((config.url_base, list(config.chaves_publicas), config.token_acesso),
                         (URL, ["t2-1"], app["token"]))

    def test_assinatura_confere_com_a_chave_publica(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

        pasta, _ = preparar_segredos(self)
        segredos = ler_json(os.path.join(pasta, "segredos.json"))
        publica = t2s.validar_chaves_publicas(ler_json(os.path.join(pasta, "app_t2.json"))["chaves"])
        privada = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(segredos["CHAVE_ASSINATURA"]))
        Ed25519PublicKey.from_public_bytes(publica).verify(privada.sign(b"teste"), b"teste")

    def test_segredos_novos_a_cada_preparacao(self):
        a, _ = preparar_segredos(self)
        b, _ = preparar_segredos(self)
        sa, sb = ler_json(os.path.join(a, "segredos.json")), ler_json(os.path.join(b, "segredos.json"))
        for campo in ("CHAVE_HMAC", "CHAVE_ASSINATURA", "TOKEN_ACESSO"):
            self.assertNotEqual(sa[campo], sb[campo])

    def test_nao_sobrescreve(self):
        pasta, _ = preparar_segredos(self)
        antes = conteudo(pasta)
        with self.assertRaises(t2s.Falha):
            preparar_segredos(self, pasta=pasta)
        self.assertEqual(conteudo(pasta), antes)

    def test_email_invalido_ou_lista_vazia_nao_cria_nada_nem_mostra_o_endereco(self):
        tmp = pasta_temporaria(self)
        for emails in (("valido@exemplo.invalid", "sem-arroba"), ()):
            with self.subTest(emails=emails):
                pasta = os.path.join(tmp, f"p{len(emails)}")
                with capturar() as (saida, erro), self.assertRaises(t2s.Falha) as falha:
                    t2s.preparar(pasta, URL, entrada=io.StringIO("".join(f"{e}\n" for e in emails)))
                self.assertFalse(os.path.exists(pasta))
                for e in emails:
                    self.assertNotIn(e, str(falha.exception) + saida.getvalue() + erro.getvalue())

    def test_subprocessos_sem_segredos_nos_argumentos(self):
        chamadas = []
        original = subprocess.run

        def registrar(args, *a, **k):
            chamadas.append((list(args), k.get("env")))
            return original(args, *a, **k)

        with mock.patch.object(t2s.subprocess, "run", side_effect=registrar):
            pasta, _ = preparar_segredos(self)
        segredos = ler_json(os.path.join(pasta, "segredos.json"))
        self.assertTrue(chamadas)
        juntos = " ".join(" ".join(c) for c, _ in chamadas)
        for valor in [*segredos.values(), *EMAILS]:
            self.assertNotIn(valor, juntos)
        self.assertTrue(all(c[:2] == ["git", "-C"] and env == t2s.ambiente_git() for c, env in chamadas))

    def test_main_com_url_invalida_nao_mostra_nada_sensivel(self):
        tmp = pasta_temporaria(self)
        with capturar(), self.assertRaises(SystemExit) as saida:
            t2s.main(["preparar", "--pasta", os.path.join(tmp, "x"), "--url", "http://inseguro.exemplo"])
        self.assertIn("t2:", str(saida.exception.code))
        self.assertFalse(os.path.exists(os.path.join(tmp, "x")))


class TestFalhasNaPreparacao(unittest.TestCase):   # I3
    def falhar_em(self, posicao, excecao=OSError("disco cheio")):
        chamadas = []

        def criar(fd, nome, dados):
            chamadas.append(nome)
            if len(chamadas) == posicao:
                raise excecao
            t2s.criar_privado(fd, nome, dados)
        return criar

    def test_falha_em_cada_gravacao_nao_deixa_credenciais(self):
        tmp = pasta_temporaria(self)
        for posicao in (1, 2, 3):
            for excecao in (OSError("disco cheio"), KeyboardInterrupt()):
                with self.subTest(posicao=posicao, excecao=type(excecao).__name__):
                    pasta = os.path.join(tmp, f"nova{posicao}{type(excecao).__name__}")
                    with self.assertRaises(type(excecao)):
                        preparar_segredos(self, pasta=pasta, _criar=self.falhar_em(posicao, excecao))
                    self.assertFalse(os.path.exists(pasta))   # criada agora: removida, vazia

    def test_falha_na_conclusao_desfaz_tudo(self):
        pasta = os.path.join(pasta_temporaria(self), "nova")
        with mock.patch.object(t2s, "substituir_privado", side_effect=OSError("falha")):
            with self.assertRaises(OSError):
                preparar_segredos(self, pasta=pasta)
        self.assertFalse(os.path.exists(pasta))

    def test_pasta_preexistente_e_mantida_vazia(self):
        pasta = os.path.join(pasta_temporaria(self), "existente")
        os.mkdir(pasta, 0o700)
        with self.assertRaises(OSError):
            preparar_segredos(self, pasta=pasta, _criar=self.falhar_em(3))
        self.assertEqual(os.listdir(pasta), [])

    def criar_interrompida(self, pasta, criada=True, extras=()):
        """Estado de uma execução morta no meio (sem chance de desfazer)."""
        os.mkdir(pasta, 0o700)
        t2s.gravar_privado(os.path.join(pasta, ".t2_segredos_estado"),
                           t2s.texto_do_estado(t2s.INCOMPLETO, criada))
        t2s.gravar_privado(os.path.join(pasta, "segredos.json"), '{"CHAVE_HMAC": "ficticia"}')
        for nome in extras:
            with open(os.path.join(pasta, nome), "w") as f:
                f.write("do usuário")

    def test_descartar_recupera_preparacao_interrompida(self):
        tmp = pasta_temporaria(self)
        criada = os.path.join(tmp, "criada")
        self.criar_interrompida(criada)
        with capturar() as (saida, _):
            t2s.descartar(criada)
        self.assertFalse(os.path.exists(criada))
        self.assertNotIn("ficticia", saida.getvalue())
        existente = os.path.join(tmp, "existente")
        self.criar_interrompida(existente, criada=False)
        with capturar():
            t2s.descartar(existente)
        self.assertEqual(os.listdir(existente), [])          # a pasta preexistente fica

    def test_descartar_recusa_concluida_ou_com_arquivos_alheios(self):
        concluida, _ = preparar_segredos(self)
        antes = conteudo(concluida)
        with self.assertRaises(t2s.Falha):
            t2s.descartar(concluida)
        self.assertEqual(conteudo(concluida), antes)
        alheia = os.path.join(pasta_temporaria(self), "alheia")
        self.criar_interrompida(alheia, extras=("notas.txt",))
        antes = conteudo(alheia)
        with self.assertRaises(t2s.Falha):
            t2s.descartar(alheia)
        self.assertEqual(conteudo(alheia), antes)
        sem_estado = t2s.criar_pasta_privada(os.path.join(pasta_temporaria(self), "sem_estado"))
        os.close(sem_estado[1])
        with self.assertRaises(t2s.Falha):
            t2s.descartar(sem_estado[0])


class TestChaveResend(unittest.TestCase):
    def ler(self, valor=CHAVE_RESEND_FICTICIA):
        return lambda: valor

    def test_acrescenta_sem_mostrar_e_sem_sobrescrever(self):
        pasta, _ = preparar_segredos(self)
        caminho = os.path.join(pasta, "segredos.json")
        antes = ler_json(caminho)
        with capturar() as (saida, erro):
            t2s.chave_resend(pasta, ler_chave=self.ler())
        depois = ler_json(caminho)
        self.assertEqual(depois, {**antes, "RESEND_API_KEY": CHAVE_RESEND_FICTICIA})
        self.assertEqual(modo(caminho), 0o600)
        self.assertEqual(sorted(os.listdir(pasta)), [".t2_segredos_estado", "app_t2.json", "segredos.json"])
        self.assertNotIn(CHAVE_RESEND_FICTICIA, saida.getvalue() + erro.getvalue())
        with self.assertRaises(t2s.Falha):
            t2s.chave_resend(pasta, ler_chave=self.ler("re_OUTRA_chave_ficticia_0000"))
        self.assertEqual(ler_json(caminho), depois)

    def test_formato_invalido_nao_grava_nem_ecoa(self):   # M8
        pasta, _ = preparar_segredos(self)
        antes = conteudo(pasta)
        for ruim in ("", "re_chave ficticia_x", "re_chave\tficticia", "re_acentuação", "x" * 513, "re_ok\n"):
            with self.subTest(ruim=ruim[:10]):
                with capturar() as (saida, erro), self.assertRaises(t2s.Falha) as falha:
                    t2s.chave_resend(pasta, ler_chave=self.ler(ruim))
                if ruim:
                    self.assertNotIn(ruim, str(falha.exception) + saida.getvalue() + erro.getvalue())
        self.assertEqual(conteudo(pasta), antes)
        # Sem exigência inventada de prefixo: a documentação não define o formato.
        self.assertEqual(t2s.validar_chave_resend("chave_sem_prefixo_123"), "chave_sem_prefixo_123")

    def test_recusa_permissoes_abertas_links_e_preparacao_incompleta(self):
        pasta, _ = preparar_segredos(self)
        caminho = os.path.join(pasta, "segredos.json")
        os.chmod(caminho, 0o644)
        with self.assertRaises(t2s.Falha):
            t2s.chave_resend(pasta, ler_chave=self.ler())
        os.chmod(caminho, 0o600)
        os.chmod(pasta, 0o755)
        with self.assertRaises(t2s.Falha):
            t2s.chave_resend(pasta, ler_chave=self.ler())
        os.chmod(pasta, 0o700)
        os.rename(caminho, caminho + ".real")
        os.symlink(caminho + ".real", caminho)
        with self.assertRaises(t2s.Falha):
            t2s.chave_resend(pasta, ler_chave=self.ler())
        self.assertNotIn("RESEND_API_KEY", ler_json(caminho + ".real"))
        incompleta, _ = preparar_segredos(self)
        os.unlink(os.path.join(incompleta, ".t2_segredos_estado"))
        t2s.gravar_privado(os.path.join(incompleta, ".t2_segredos_estado"), t2s.texto_do_estado(t2s.INCOMPLETO, True))
        with self.assertRaises(t2s.Falha):
            t2s.chave_resend(incompleta, ler_chave=self.ler())

    def test_temporario_remanescente_e_falha_na_troca(self):   # M5
        pasta, _ = preparar_segredos(self)
        caminho = os.path.join(pasta, "segredos.json")
        antes = ler_bytes(caminho)
        t2s.gravar_privado(caminho + ".novo", '{"resto": "de uma execução interrompida"}')
        with capturar() as (saida, erro), self.assertRaises(t2s.Falha) as falha:
            t2s.chave_resend(pasta, ler_chave=self.ler())
        self.assertIn("execução interrompida", str(falha.exception))
        self.assertNotIn(CHAVE_RESEND_FICTICIA, str(falha.exception) + saida.getvalue() + erro.getvalue())
        self.assertEqual(ler_bytes(caminho), antes)
        os.unlink(caminho + ".novo")
        with mock.patch.object(t2s.os, "replace", side_effect=OSError("falha")):
            with self.assertRaises(OSError):
                t2s.chave_resend(pasta, ler_chave=self.ler())
        self.assertEqual(ler_bytes(caminho), antes)
        self.assertFalse(os.path.exists(caminho + ".novo"))   # o temporário com a chave não fica


class TestEntradaDaChave(unittest.TestCase):   # I4
    def test_entrada_que_nao_e_terminal_e_recusada_sem_ler(self):
        pedidos = []
        for entrada in (io.StringIO(CHAVE_RESEND_FICTICIA + "\n"), io.StringIO("")):
            with self.assertRaises(t2s.Falha):
                t2s.ler_chave_do_terminal(entrada, pedir=lambda p: pedidos.append(p) or "x")
        self.assertEqual(pedidos, [])

    def test_terminal_usa_leitura_sem_eco(self):
        self.assertEqual(t2s.ler_chave_do_terminal(Terminal(), pedir=lambda p: CHAVE_RESEND_FICTICIA),
                         CHAVE_RESEND_FICTICIA)

    def test_comando_recusa_pipe_sem_gravar_nem_mostrar(self):
        pasta, _ = preparar_segredos(self)
        antes = conteudo(pasta)
        with mock.patch.object(sys, "stdin", io.StringIO(CHAVE_RESEND_FICTICIA + "\n")), \
                capturar() as (saida, erro), self.assertRaises(SystemExit) as fim:
            t2s.main(["chave-resend", "--pasta", pasta])
        self.assertIn("terminal interativo", str(fim.exception.code))
        self.assertNotIn(CHAVE_RESEND_FICTICIA, str(fim.exception.code) + saida.getvalue() + erro.getvalue())
        self.assertEqual(conteudo(pasta), antes)


# ======================================================================
#  t2_app: repositório Git descartável
# ======================================================================

DB_FALSO = (
    "import os\n"
    "NOME_DO_BANCO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sino.db')\n"
    "PASTA_BACKUPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')\n"
)
# Se este main.py rodar, deixa um rastro: os testes conferem que nunca roda.
MAIN_FALSO = "open(__file__ + '.EXECUTADO', 'w').close()\n"
CLIENTE_COM_TOKEN = (
    "def ler_token_de_acesso(texto):\n    return texto\n\n"
    "def configuracao_do_ambiente(ambiente):\n    return ambiente.get('SINO_SERVICO_TOKEN')\n\n"
    "CABECALHO = 'Authorization'\n"
)
CLIENTE_SO_COMENTARIO = "# SINO_SERVICO_TOKEN Authorization ler_token_de_acesso\n"
T2_TS = "import { comToken } from './acesso_teste';\n// TOKEN_ACESSO\n"


class RepositorioFalso:
    def __init__(self, pasta):
        self.raiz = os.path.join(pasta, "origem")
        self.ambiente = {**os.environ, **GIT_ISOLADO}
        self.git("init", "-q", "-b", "main", self.raiz, cwd=pasta)

    def git(self, *args, cwd=None):
        return subprocess.run(["git", "-c", "user.name=Teste", "-c", "user.email=teste@exemplo.invalid",
                               "-c", "commit.gpgsign=false", *args], cwd=cwd or self.raiz, env=self.ambiente,
                              capture_output=True, text=True, check=True).stdout.strip()

    def commit(self, arquivos, mensagem, links=()):
        for caminho, texto in arquivos.items():
            completo = os.path.join(self.raiz, caminho)
            os.makedirs(os.path.dirname(completo), exist_ok=True)
            if texto is None:
                os.unlink(completo)
                continue
            with open(completo, "w", encoding="utf-8") as f:
                f.write(texto)
        for caminho, alvo in links:
            os.symlink(alvo, os.path.join(self.raiz, caminho))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", mensagem)
        return self.git("rev-parse", "HEAD")

    def publicar(self, commit):
        self.git("update-ref", "refs/remotes/origin/main", commit)


class BaseApp(unittest.TestCase):
    def setUp(self):
        self.tmp = pasta_temporaria(self)
        self.repo = RepositorioFalso(self.tmp)
        base = {"database/db.py": DB_FALSO, "backend/main.py": MAIN_FALSO, "database/.gitkeep": "",
                "servidor/src/t2.ts": T2_TS, "servidor/wrangler.t2.jsonc": "{}\n"}
        self.sem_token = self.repo.commit({**base, "backend/servico_codigos.py": "# cliente antigo\n"}, "antigo")
        self.com_token = self.repo.commit({"backend/servico_codigos.py": CLIENTE_COM_TOKEN}, "t2")
        self.repo.publicar(self.com_token)
        self.nao_publicado = self.repo.commit({"backend/extra.py": "x = 1\n"}, "local")

    def preparar_copia(self, nome="copia", revisao=None, **extra):
        destino = os.path.join(self.tmp, nome)
        with capturar() as (saida, erro):
            t2_app.preparar(destino, revisao or self.com_token, raiz=self.repo.raiz, **extra)
        return destino, saida.getvalue() + erro.getvalue()

    def publicado(self, arquivos, mensagem, links=()):
        commit = self.repo.commit(arquivos, mensagem, links)
        self.repo.publicar(commit)
        return commit

    def marca(self, destino):
        return ler_json(os.path.join(destino, ".sino_t2_copia"))


class TestRevisao(BaseApp):
    def test_so_sha_completo_publicado_e_com_token(self):
        self.assertEqual(t2_app.validar_revisao(self.com_token, self.repo.raiz), self.com_token)
        for ruim in ("HEAD", "main", self.com_token[:12], self.com_token.upper(), "0" * 40,
                     self.nao_publicado, self.sem_token, "", None):
            with self.subTest(revisao=ruim):
                with self.assertRaises(t2_app.Falha):
                    t2_app.validar_revisao(ruim, self.repo.raiz)

    def test_presenca_textual_do_token_nao_basta(self):   # M3
        so_texto = self.publicado({"backend/servico_codigos.py": CLIENTE_SO_COMENTARIO}, "comentário")
        with self.assertRaises(t2_app.Falha):
            t2_app.validar_revisao(so_texto, self.repo.raiz)

    def test_exige_os_arquivos_do_t2_e_recusa_links_e_submodulos(self):   # M3
        sem_t2 = self.publicado({"backend/servico_codigos.py": CLIENTE_COM_TOKEN, "servidor/src/t2.ts": None}, "sem t2")
        with self.assertRaises(t2_app.Falha):
            t2_app.validar_revisao(sem_t2, self.repo.raiz)
        com_link = self.publicado({"servidor/src/t2.ts": T2_TS}, "link", links=(("database/atalho", RAIZ),))
        with self.assertRaises(t2_app.Falha) as falha:
            t2_app.validar_revisao(com_link, self.repo.raiz)
        self.assertIn("links simbólicos", str(falha.exception))

    def test_variaveis_git_do_usuario_nao_desviam_a_validacao(self):   # M6
        lugar = os.path.join(self.tmp, "outro_lugar")
        os.mkdir(lugar)
        outro = RepositorioFalso(lugar)
        with mock.patch.dict(os.environ, {"GIT_DIR": os.path.join(outro.raiz, ".git"), "GIT_WORK_TREE": outro.raiz}):
            self.assertEqual(t2_app.validar_revisao(self.com_token, self.repo.raiz), self.com_token)


class TestCopia(BaseApp):
    def test_copia_isolada_concluida_sem_abrir_o_app(self):
        destino, texto = self.preparar_copia()
        app = os.path.join(destino, "app")
        self.assertEqual(modo(destino), 0o700)
        self.assertEqual(modo(os.path.join(destino, ".sino_t2_copia")), 0o600)
        marca = self.marca(destino)
        info = os.stat(destino)
        self.assertEqual((marca["estado"], marca["commit"], marca["dev"], marca["ino"], marca["pasta_criada"]),
                         ("concluida", self.com_token, info.st_dev, info.st_ino, True))
        self.assertRegex(marca["id"], r"^[0-9a-f]{32}$")
        self.assertTrue(os.path.isfile(os.path.join(app, "backend", "servico_codigos.py")))
        self.assertFalse(os.path.exists(os.path.join(app, "backend", "extra.py")))   # revisão exata
        self.assertFalse(os.path.exists(os.path.join(app, "database", "sino.db")))
        self.assertFalse(os.path.exists(os.path.join(app, "backend", "main.py.EXECUTADO")))
        self.assertIn(self.com_token[:12], texto)
        self.assertIn("não foi aberto", texto)
        real, fd, _, _ = t2_app.conferir_copia(destino, self.repo.raiz)
        os.close(fd)
        self.assertEqual(real, destino)

    def test_recusa_revisao_nao_autorizada_sem_criar_nada(self):
        for revisao in (self.nao_publicado, self.sem_token, "HEAD"):
            with self.subTest(revisao=revisao):
                with self.assertRaises(t2_app.Falha):
                    self.preparar_copia(f"c-{revisao[:4]}", revisao)
                self.assertFalse(os.path.exists(os.path.join(self.tmp, f"c-{revisao[:4]}")))

    def test_recusa_destinos_inseguros(self):
        os.symlink(RAIZ, os.path.join(self.tmp, "atalho"))
        for destino in (os.path.join(self.repo.raiz, "copia"), os.path.join(RAIZ, "copia_t2"),
                        os.path.join(self.tmp, "atalho", "copia"), os.path.join(self.tmp, "atalho")):
            with self.subTest(destino=destino):
                with self.assertRaises(t2_app.Falha):
                    with capturar():
                        t2_app.preparar(destino, self.com_token, raiz=self.repo.raiz)
        self.assertFalse(os.path.exists(os.path.join(RAIZ, "copia_t2")))

    def test_nao_sobrescreve_uma_copia_existente(self):
        destino, _ = self.preparar_copia()
        antes = self.marca(destino)
        with self.assertRaises(t2_app.Falha):
            self.preparar_copia()
        self.assertEqual(self.marca(destino), antes)

    def test_falhas_intermediarias_deixam_marca_incompleta_e_remover_limpa(self):   # I3
        def falhar(*_):
            raise t2_app.Falha("extração simulada falhou")
        destino = os.path.join(self.tmp, "parcial")
        with capturar() as (saida, _), self.assertRaises(t2_app.Falha):
            t2_app.preparar(destino, self.com_token, raiz=self.repo.raiz, _extrair=falhar)
        self.assertIn("incompleta", saida.getvalue())
        self.assertEqual(self.marca(destino)["estado"], "incompleta")
        with self.assertRaises(t2_app.Falha):
            t2_app.conferir_copia(destino, self.repo.raiz)          # abrir exige "concluida"
        with capturar():
            self.assertTrue(t2_app.remover(destino, confirmar=True, raiz=self.repo.raiz, processos=lambda r: []))
        self.assertFalse(os.path.lexists(destino))

    def test_recusa_copia_cujo_banco_aponta_para_fora(self):
        # Uma revisão cujo db.py aponta para o banco real é recusada (o banco não é aberto).
        commit = self.publicado({"database/db.py": f"NOME_DO_BANCO = {BANCO_REAL!r}\nPASTA_BACKUPS = '/tmp'\n"}, "fora")
        with self.assertRaises(t2_app.Falha) as falha:
            self.preparar_copia("fora", commit)
        self.assertIn("fora da cópia", str(falha.exception))
        self.assertEqual(self.marca(os.path.join(self.tmp, "fora"))["estado"], "incompleta")

    def test_marca_copiada_para_outra_pasta_nao_vale(self):   # M4
        destino, _ = self.preparar_copia()
        outra = os.path.join(self.tmp, "outra")
        os.mkdir(outra, 0o700)
        shutil.copytree(os.path.join(destino, "app"), os.path.join(outra, "app"))
        shutil.copy2(os.path.join(destino, ".sino_t2_copia"), os.path.join(outra, ".sino_t2_copia"))
        for funcao in (lambda: t2_app.conferir_copia(outra, self.repo.raiz),
                       lambda: t2_app.remover(outra, confirmar=True, raiz=self.repo.raiz, processos=lambda r: [])):
            with self.assertRaises(t2_app.Falha) as falha, capturar():
                funcao()
            self.assertIn("copiada", str(falha.exception))
        self.assertTrue(os.path.isdir(os.path.join(outra, "app")))


class TestAbrir(BaseApp):
    def setUp(self):
        super().setUp()
        self.destino, _ = self.preparar_copia()
        self.segredos, _ = preparar_segredos(self, pasta=os.path.join(self.tmp, "segredos"))
        self.app = ler_json(os.path.join(self.segredos, "app_t2.json"))

    def popen_falso(self, durante=None):
        chamadas = []

        class Processo:
            def wait(self):
                if durante:
                    durante()
                return 0

        def popen(args, **kwargs):
            chamadas.append((list(args), kwargs))
            return Processo()

        return popen, chamadas

    def abrir(self, popen, **extra):
        return t2_app.abrir(self.destino, self.segredos, raiz=self.repo.raiz, popen=popen, **extra)

    def test_ambiente_fechado_e_token_so_no_ambiente_do_processo(self):   # I1
        popen, chamadas = self.popen_falso()
        ambiente_antes = dict(os.environ)
        extras = {**CREDENCIAIS_FICTICIAS, "DISPLAY": ":0", "LC_TIME": "pt_BR.UTF-8", "HOME": "/home/ficticia"}
        with mock.patch.dict(os.environ, extras), capturar() as (saida, erro):
            self.assertEqual(self.abrir(popen), 0)
        self.assertEqual(dict(os.environ), ambiente_antes)          # nada permanente
        args, kwargs = chamadas[0]
        app = os.path.join(self.destino, "app")
        self.assertEqual(args, [sys.executable, "-E", "-s", os.path.join(app, "backend", "main.py")])
        self.assertEqual((kwargs["cwd"], kwargs["start_new_session"]), (app, True))
        env = kwargs["env"]
        permitidas = set(t2_app.VARIAVEIS_DO_SISTEMA) | set(t2_app.VARIAVEIS_DO_T2)
        self.assertTrue(all(k in permitidas or k.startswith("LC_") for k in env), sorted(env))
        for nome in CREDENCIAIS_FICTICIAS:
            if nome != "SINO_SERVICO_URL":
                self.assertNotIn(nome, env)
        self.assertEqual((env["DISPLAY"], env["LC_TIME"], env["HOME"]), (":0", "pt_BR.UTF-8", "/home/ficticia"))
        self.assertEqual((env["SINO_SERVICO_URL"], env["SINO_SERVICO_CHAVES"], env["SINO_SERVICO_TOKEN"]),
                         (URL, self.app["chaves"], self.app["token"]))
        texto = saida.getvalue() + erro.getvalue()
        # (valores curtos, como "1", aparecem por acaso em qualquer caminho; ficam de fora)
        for valor in (self.app["token"], self.app["chaves"].split(":")[1],
                      *(v for v in CREDENCIAIS_FICTICIAS.values() if len(v) > 3)):
            self.assertNotIn(valor, " ".join(args))
            self.assertNotIn(valor, texto)
        self.assertEqual(modo(os.path.join(self.destino, "app.log")), 0o600)
        self.assertFalse(os.path.exists(os.path.join(app, "backend", "main.py.EXECUTADO")))

    def test_cada_variavel_do_sistema_tem_justificativa(self):
        self.assertTrue(all(isinstance(m, str) and len(m) > 10 for m in t2_app.VARIAVEIS_DO_SISTEMA.values()))
        for proibida in ("PYTHONPATH", "PYTHONHOME", "LD_PRELOAD", "LD_LIBRARY_PATH", "SSH_AUTH_SOCK"):
            self.assertNotIn(proibida, t2_app.VARIAVEIS_DO_SISTEMA)

    def test_interpretador_conferido_com_E_s_sem_abrir_o_app(self):   # M7
        self.assertEqual(t2_app.validar_interpretador(sys.executable), sys.executable)   # .venv do projeto

        def resposta(dados, codigo=0):
            return lambda args, **k: subprocess.CompletedProcess(args, codigo, json.dumps(dados), "")
        casos = {
            "falta_flet": resposta({"faltam": ["flet"], "versao": [3, 11], "E": 1, "s": 1}),
            "sem_E": resposta({"faltam": [], "versao": [3, 11], "E": 0, "s": 1}),
            "antigo": resposta({"faltam": [], "versao": [3, 8], "E": 1, "s": 1}),
            "erro": resposta({}, codigo=1),
        }
        for nome, executar in casos.items():
            with self.subTest(caso=nome):
                with self.assertRaises(t2_app.Falha):
                    t2_app.validar_interpretador(sys.executable, executar)
        for ruim in ("python3", "/nao/existe/python", None):
            with self.subTest(python=ruim):
                with self.assertRaises(t2_app.Falha):
                    t2_app.validar_interpretador(ruim)
        popen, chamadas = self.popen_falso()
        with capturar(), self.assertRaises(t2_app.Falha):
            self.abrir(popen, executar=casos["falta_flet"])
        self.assertEqual(chamadas, [])

    def gravar_app(self, **trocas):
        caminho = os.path.join(self.segredos, "app_t2.json")
        os.unlink(caminho)
        t2s.gravar_privado(caminho, json.dumps({**self.app, **trocas}))

    def test_recusa_configuracao_invalida_sem_abrir(self):
        casos = {
            "http": {"url": URL.replace("https", "http")},
            "outro_worker": {"url": "https://sino-servico-codigos.subdominio-ficticio.workers.dev"},
            "kid": {"chaves": self.app["chaves"].replace("t2-1", "teste-1")},
            "chave_curta": {"chaves": "t2-1:abcd"},
            "token": {"token": "curto"},
        }
        for nome, trocas in casos.items():
            with self.subTest(caso=nome):
                self.gravar_app(**trocas)
                popen, chamadas = self.popen_falso()
                with capturar() as (saida, erro), self.assertRaises(t2_app.Falha) as falha:
                    self.abrir(popen)
                self.assertEqual(chamadas, [])
                self.assertNotIn(self.app["token"], str(falha.exception) + saida.getvalue() + erro.getvalue())

    def test_recusa_permissoes_abertas_e_segredos_incompletos(self):
        os.chmod(os.path.join(self.segredos, "app_t2.json"), 0o644)
        popen, chamadas = self.popen_falso()
        with capturar(), self.assertRaises(t2_app.Falha):
            self.abrir(popen)
        os.chmod(os.path.join(self.segredos, "app_t2.json"), 0o600)
        estado = os.path.join(self.segredos, ".t2_segredos_estado")
        os.unlink(estado)
        t2s.gravar_privado(estado, t2s.texto_do_estado(t2s.INCOMPLETO, True))
        with capturar(), self.assertRaises(t2_app.Falha):
            self.abrir(popen)
        self.assertEqual(chamadas, [])

    def test_recusa_pasta_que_nao_e_copia(self):
        real, fd, _ = t2s.criar_pasta_privada(os.path.join(self.tmp, "outra"))
        os.close(fd)
        popen, chamadas = self.popen_falso()
        with capturar(), self.assertRaises(t2_app.Falha):
            t2_app.abrir(real, self.segredos, raiz=self.repo.raiz, popen=popen)
        self.assertEqual(chamadas, [])

    def test_remover_e_recusado_enquanto_o_app_esta_aberto(self):   # I2
        resultado = []

        def tentar_remover():
            with self.assertRaises(t2_app.Falha) as falha, capturar():
                t2_app.remover(self.destino, confirmar=True, raiz=self.repo.raiz, processos=lambda r: [])
            resultado.append(str(falha.exception))
        popen, _ = self.popen_falso(durante=tentar_remover)
        with capturar():
            self.abrir(popen)
        self.assertIn("em uso", resultado[0])
        self.assertTrue(os.path.isdir(os.path.join(self.destino, "app")))


class TestRemover(BaseApp):
    def remover(self, destino, confirmar=True, processos=lambda r: []):
        with capturar() as (saida, _):
            resultado = t2_app.remover(destino, confirmar=confirmar, raiz=self.repo.raiz, processos=processos)
        return resultado, saida.getvalue()

    def test_sem_confirmar_nao_apaga(self):
        destino, _ = self.preparar_copia()
        resultado, texto = self.remover(destino, confirmar=False)
        self.assertFalse(resultado)
        self.assertTrue(os.path.isdir(os.path.join(destino, "app")))
        self.assertIn("--confirmar", texto)

    def test_remove_so_a_copia_sem_seguir_links(self):
        destino, _ = self.preparar_copia()
        fora = os.path.join(self.tmp, "fora.txt")
        with open(fora, "w") as f:
            f.write("fica")
        pasta_fora = os.path.join(self.tmp, "pasta_fora")
        os.mkdir(pasta_fora)
        with open(os.path.join(pasta_fora, "dentro.txt"), "w") as f:
            f.write("fica")
        os.symlink(fora, os.path.join(destino, "app", "link_arquivo"))
        os.symlink(pasta_fora, os.path.join(destino, "app", "link_pasta"))
        self.assertTrue(self.remover(destino)[0])
        self.assertFalse(os.path.lexists(destino))
        self.assertTrue(os.path.isfile(fora))
        self.assertTrue(os.path.isfile(os.path.join(pasta_fora, "dentro.txt")))
        self.assertTrue(os.path.isdir(self.repo.raiz))

    def test_troca_de_pasta_por_link_durante_a_remocao_para_sem_sair_da_copia(self):   # I2
        destino, _ = self.preparar_copia()
        externa = os.path.join(self.tmp, "externa")
        os.mkdir(externa)
        with open(os.path.join(externa, "valioso.txt"), "w") as f:
            f.write("não apagar")

        def trocar(fd, nome):
            if nome == "backend":
                alvo = os.path.join(destino, "app", "backend")
                os.rename(alvo, alvo + "_movida")
                os.symlink(externa, alvo)
        with mock.patch.object(t2_app, "_antes_de_entrar", trocar):
            with self.assertRaises(t2_app.Falha) as falha, capturar():
                t2_app.remover(destino, confirmar=True, raiz=self.repo.raiz, processos=lambda r: [])
        self.assertIn("trocada", str(falha.exception))
        self.assertEqual(os.listdir(externa), ["valioso.txt"])
        self.assertTrue(os.path.isfile(os.path.join(destino, ".sino_t2_copia")))   # nova tentativa possível

    def test_troca_por_outra_pasta_real_tambem_para(self):   # I2
        destino, _ = self.preparar_copia()
        externa = os.path.join(self.tmp, "externa_real")
        os.mkdir(externa)
        with open(os.path.join(externa, "valioso.txt"), "w") as f:
            f.write("não apagar")

        def trocar(fd, nome):
            if nome == "backend":
                alvo = os.path.join(destino, "app", "backend")
                os.rename(alvo, alvo + "_movida")
                os.rename(externa, alvo)
        with mock.patch.object(t2_app, "_antes_de_entrar", trocar):
            with self.assertRaises(t2_app.Falha), capturar():
                t2_app.remover(destino, confirmar=True, raiz=self.repo.raiz, processos=lambda r: [])
        self.assertEqual(os.listdir(os.path.join(destino, "app", "backend")), ["valioso.txt"])

    def test_recusa_com_processo_ativo_trava_ou_sqlite_temporario(self):   # I2
        destino, _ = self.preparar_copia()
        app = os.path.join(destino, "app")
        processo = subprocess.Popen(["sleep", "30"], cwd=app)   # comando local inofensivo, não o app
        self.addCleanup(processo.wait)
        self.addCleanup(processo.kill)
        with self.assertRaises(t2_app.Falha) as falha, capturar():
            t2_app.remover(destino, confirmar=True, raiz=self.repo.raiz)   # /proc de verdade
        self.assertIn("em uso", str(falha.exception))
        self.assertIn(processo.pid, t2_app.processos_da_copia(destino))
        processo.kill()
        processo.wait()
        trava = os.open(os.path.join(destino, ".em_uso"), os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, trava)
        fcntl.flock(trava, fcntl.LOCK_EX)
        with self.assertRaises(t2_app.Falha):
            self.remover(destino)
        fcntl.flock(trava, fcntl.LOCK_UN)
        for sufixo in ("-wal", "-journal", "-shm"):
            with self.subTest(sufixo=sufixo):
                temporario = os.path.join(app, "database", "sino.db" + sufixo)
                with open(temporario, "w") as f:
                    f.write("")
                with self.assertRaises(t2_app.Falha):
                    self.remover(destino)
                os.unlink(temporario)
        self.assertTrue(os.path.isdir(app))
        self.assertFalse(t2_app.processos_da_copia(destino))

    def test_pasta_preexistente_e_mantida_e_pasta_sem_marca_recusada(self):
        destino = os.path.join(self.tmp, "existente")
        os.mkdir(destino, 0o755)
        self.preparar_copia("existente")
        self.assertTrue(self.remover(destino)[0])
        self.assertEqual(os.listdir(destino), [])
        real, fd, _ = t2s.criar_pasta_privada(os.path.join(self.tmp, "sem_marca"))
        os.close(fd)
        with open(os.path.join(real, "algo"), "w") as f:
            f.write("x")
        with self.assertRaises(t2_app.Falha):
            self.remover(real)
        self.assertTrue(os.path.isfile(os.path.join(real, "algo")))


if __name__ == "__main__":
    unittest.main()
