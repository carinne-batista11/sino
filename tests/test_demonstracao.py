"""
Comando do modo de demonstração (servidor/ferramentas/demonstracao.py): pasta
fora do projeto, portas livres, cópia do código por `git archive` reutilizada
só na mesma revisão, caminhos do banco dentro da cópia, banco de versão mais
nova recusado, chaves sem sobrescrever, leitura estrita das variáveis do app
e encerramento só dos processos criados pelo comando. Não sobe o serviço nem
o app; sem rede externa (sockets só em 127.0.0.1).
"""

import io
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "servidor", "ferramentas"))

import caixa_dev as cd  # noqa: E402
import demonstracao as dm  # noqa: E402


def pasta_temporaria(teste):
    pasta = tempfile.TemporaryDirectory(prefix="sino_demo_")
    teste.addCleanup(pasta.cleanup)
    return os.path.realpath(pasta.name)


class TestPastaEPortas(unittest.TestCase):
    def test_pasta_dentro_do_projeto_recusada(self):
        for pasta in (cd.RAIZ_DO_PROJETO, os.path.join(cd.RAIZ_DO_PROJETO, "demo")):
            with self.subTest(pasta=pasta), self.assertRaises(SystemExit):
                dm.preparar_pasta(pasta)
        self.assertFalse(os.path.exists(os.path.join(cd.RAIZ_DO_PROJETO, "demo")))

    def test_pasta_nova_criada_com_700(self):
        raiz = dm.preparar_pasta(os.path.join(pasta_temporaria(self), "demo"))
        self.assertEqual(os.stat(raiz).st_mode & 0o777, 0o700)

    def test_pasta_em_repositorio_git_so_se_ignorada(self):
        repo = pasta_temporaria(self)
        subprocess.run(["git", "init", "-q", repo], check=True)
        with self.assertRaises(SystemExit):
            dm.preparar_pasta(os.path.join(repo, "demo"))
        with open(os.path.join(repo, ".git", "info", "exclude"), "a") as exclude:
            exclude.write("/demo/\n")
        self.assertEqual(dm.preparar_pasta(os.path.join(repo, "demo")), os.path.join(repo, "demo"))

    def test_porta_ocupada_detectada(self):
        with socket.socket() as ocupante:
            ocupante.bind(("127.0.0.1", 0))
            ocupante.listen()
            porta = ocupante.getsockname()[1]
            self.assertEqual(dm.portas_ocupadas((porta,)), [porta])
        self.assertEqual(dm.portas_ocupadas((porta,)), [])

    def test_time_wait_nao_bloqueia_mas_listener_ativo_sim(self):
        # o lado da porta fecha primeiro e fica em TIME-WAIT (como o inspetor ao encerrar o wrangler)
        servidor = socket.socket()
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind(("127.0.0.1", 0))
        servidor.listen()
        porta = servidor.getsockname()[1]
        cliente = socket.create_connection(("127.0.0.1", porta))
        conexao, _ = servidor.accept()
        self.assertEqual(dm.portas_ocupadas((porta,)), [porta])  # listener ativo: recusada
        conexao.close()
        cliente.close()
        servidor.close()
        estado = subprocess.run(["ss", "-tan", "sport", f"= :{porta}"], capture_output=True, text=True).stdout
        self.assertIn("TIME-WAIT", estado)
        self.assertEqual(dm.portas_ocupadas((porta,)), [])         # só TIME-WAIT: livre


class TestSaida(unittest.TestCase):
    def test_mensagens_saem_por_linha_mesmo_em_arquivo(self):
        bruto = io.BytesIO()
        fluxo = io.TextIOWrapper(bruto, encoding="utf-8")
        self.assertFalse(fluxo.line_buffering)
        dm.saida_por_linha(fluxo)
        print("demonstração: pronta", file=fluxo)
        self.assertEqual(bruto.getvalue(), "demonstração: pronta\n".encode())


class TestCopiaDoCodigo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.commit = dm.resolver_revisao("HEAD")

    def test_revisao_invalida(self):
        with self.assertRaises(SystemExit):
            dm.resolver_revisao("nao-existe-esta-revisao")

    def test_copia_nova_reutilizada_e_revisao_diferente_recusada(self):
        raiz = pasta_temporaria(self)
        app, nova = dm.preparar_copia(raiz, self.commit)
        self.assertTrue(nova)
        self.assertTrue(os.path.isfile(os.path.join(app, "backend", "main.py")))
        self.assertFalse(os.path.exists(os.path.join(app, "database", "sino.db")))  # o banco real nunca vem junto

        caminhos = dm.conferir_caminhos(app)
        for chave in ("db", "banco", "backups"):
            self.assertTrue(caminhos[chave].startswith(os.path.realpath(app) + os.sep), chave)

        marcador = os.path.join(app, "dado_da_demo.txt")
        with open(marcador, "w") as arquivo:
            arquivo.write("preservar")
        self.assertEqual(dm.preparar_copia(raiz, self.commit), (app, False))  # mesma revisão: reutiliza
        with self.assertRaises(dm.DemonstracaoIncompativel):
            dm.preparar_copia(raiz, "0" * 40)
        with open(marcador) as arquivo:
            self.assertEqual(arquivo.read(), "preservar")  # nada apagado nem sobrescrito

    def test_banco_de_versao_mais_nova_recusado(self):
        app, _ = dm.preparar_copia(pasta_temporaria(self), self.commit)
        banco = os.path.join(app, "database", "sino.db")
        conexao = sqlite3.connect(banco)
        conexao.execute("PRAGMA user_version = 99")
        conexao.close()
        with self.assertRaises(dm.DemonstracaoIncompativel):
            dm.conferir_caminhos(app)
        conexao = sqlite3.connect(banco)
        self.assertEqual(conexao.execute("PRAGMA user_version").fetchone()[0], 99)  # intacto
        conexao.close()


class TestChavesEVariaveis(unittest.TestCase):
    def test_gera_uma_vez_e_reutiliza(self):
        raiz = pasta_temporaria(self)
        segredos, app_env = dm.preparar_chaves(raiz)
        with open(segredos) as arquivo:
            antes = arquivo.read()
        self.assertEqual(dm.preparar_chaves(raiz), (segredos, app_env))
        with open(segredos) as arquivo:
            self.assertEqual(arquivo.read(), antes)
        variaveis = dm.ler_variaveis_do_app(app_env)
        self.assertEqual(variaveis["SINO_SERVICO_URL"], "http://127.0.0.1:8787")
        self.assertTrue(variaveis["SINO_SERVICO_CHAVES"].startswith("dev-1:"))

    def test_chave_pela_metade_recusada(self):
        raiz = pasta_temporaria(self)
        with open(os.path.join(raiz, "app_dev.env"), "w") as arquivo:
            arquivo.write("x")
        with self.assertRaises(dm.DemonstracaoIncompativel):
            dm.preparar_chaves(raiz)
        self.assertFalse(os.path.exists(os.path.join(raiz, "segredos_dev.env")))

    def test_pasta_de_versao_anterior_sem_lista_recusada(self):  # contrato v1.1
        raiz = pasta_temporaria(self)
        for nome in ("segredos_dev.env", "app_dev.env"):  # como gerava a versão anterior
            with open(os.path.join(raiz, nome), "w") as arquivo:
                arquivo.write("CHAVE_HMAC=x\n")
        with self.assertRaises(dm.DemonstracaoIncompativel):
            dm.preparar_chaves(raiz)
        self.assertFalse(os.path.exists(os.path.join(raiz, "destinatarios_ficticios.txt")))
        with open(os.path.join(raiz, "destinatarios_ficticios.txt"), "w") as arquivo:
            arquivo.write("x")
        with self.assertRaises(dm.DemonstracaoIncompativel):
            dm.preparar_chaves(raiz)  # os três existem, mas os segredos não têm a lista

    def test_lista_gerada_so_com_os_ficticios(self):
        raiz = pasta_temporaria(self)
        segredos, _ = dm.preparar_chaves(raiz)
        with open(segredos) as arquivo:
            linhas = dict(l.split("=", 1) for l in arquivo.read().split())
        chave = bytes.fromhex(linhas["CHAVE_HMAC"])
        self.assertEqual(linhas["DESTINATARIOS_PERMITIDOS"],
                         dm.destinatarios.montar(chave, list(dm.destinatarios.DESTINATARIOS_FICTICIOS))[0])

    def test_variaveis_lidas_sem_executar_e_so_as_esperadas(self):
        raiz = pasta_temporaria(self)
        caminho = os.path.join(raiz, "app_dev.env")
        for conteudo in ("SINO_SERVICO_URL=x\n", "SINO_SERVICO_URL=x\nSINO_SERVICO_CHAVES=y\nPATH=/tmp\n",
                         "SINO_SERVICO_URL=x\nSINO_SERVICO_CHAVES=y\nSINO_SERVICO_URL=z\n", "$(rm -rf /)\n"):
            with open(caminho, "w") as arquivo:
                arquivo.write(conteudo)
            with self.subTest(conteudo=conteudo), self.assertRaises(dm.DemonstracaoIncompativel):
                dm.ler_variaveis_do_app(caminho)
        with open(caminho, "w") as arquivo:
            arquivo.write("SINO_SERVICO_URL=http://127.0.0.1:8787\nSINO_SERVICO_CHAVES=dev-1:ab=cd\n")
        self.assertEqual(dm.ler_variaveis_do_app(caminho)["SINO_SERVICO_CHAVES"], "dev-1:ab=cd")


class TestEncerramento(unittest.TestCase):
    def test_encerra_so_o_grupo_criado_pelo_comando(self):
        proprio = subprocess.Popen(["sleep", "60"], start_new_session=True)
        alheio = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.addCleanup(alheio.wait)
        self.addCleanup(alheio.kill)
        inicio = time.monotonic()
        dm.encerrar_processo(proprio, prazo_s=5)
        self.assertIsNotNone(proprio.poll())
        self.assertLess(time.monotonic() - inicio, 5)
        self.assertIsNone(alheio.poll())
        dm.encerrar_processo(proprio)  # já encerrado: nada a fazer
        dm.encerrar_processo(None)


if __name__ == "__main__":
    unittest.main()
