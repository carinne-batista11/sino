"""
Roteiro do ambiente remoto de testes (servidor/ferramentas/teste_remoto.py;
ERS v7.0, E4, T1): URLs aceitas, preparação dos segredos exclusivos (pasta
700, arquivos 600, nunca sobrescritos, fora do repositório), janelas de uma
hora por comando e relatório sem segredos, e-mails ou códigos. Sem rede: os
casos rodam contra um serviço falso em memória.
"""

import contextlib
import datetime
import io
import json
import os
import re
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "servidor", "ferramentas"))

import destinatarios as dt  # noqa: E402
import teste_remoto as tr  # noqa: E402

URL = "https://sino-servico-codigos-teste.carinnebatista11.workers.dev"


class TestUrl(unittest.TestCase):
    def test_aceitas(self):
        self.assertEqual(tr.validar_url(URL), URL)
        self.assertEqual(tr.validar_url(URL + "/"), URL)
        self.assertEqual(tr.validar_url("http://127.0.0.1:8787"), "http://127.0.0.1:8787")

    def test_recusadas(self):
        for ruim in (
            "http://sino-servico-codigos-teste.carinnebatista11.workers.dev",
            "https://sino-servico-codigos.carinnebatista11.workers.dev",
            "https://sino-servico-codigos-teste.a.b.workers.dev",
            "https://sino-servico-codigos-teste.workers.dev",
            "https://sino-servico-codigos-teste.carinnebatista11.workers.dev:8443",
            URL + "/v1",
            URL + "?x=1",
            "https://u:s@sino-servico-codigos-teste.carinnebatista11.workers.dev",
            "https://appsino.com.br",
            "http://localhost:8787",
            "http://127.0.0.1",
            "",
        ):
            with self.subTest(url=ruim):
                with self.assertRaises(tr.Falha):
                    tr.validar_url(ruim)


class TestPreparar(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.pasta = os.path.join(self.base, "e4-teste")

    def preparar(self):
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            tr.preparar(self.pasta, URL)
        return saida.getvalue()

    def ler(self, nome):
        with open(os.path.join(self.pasta, nome), encoding="utf-8") as arquivo:
            return arquivo.read()

    def test_arquivos_privados_e_formatos(self):
        saida = self.preparar()
        self.assertEqual(stat.S_IMODE(os.stat(self.pasta).st_mode), 0o700)
        for nome in ("segredos.json", "segredos.env", "teste_remoto.json"):
            self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.pasta, nome)).st_mode), 0o600)
        segredos = json.loads(self.ler("segredos.json"))
        self.assertEqual(set(segredos), {"CHAVE_HMAC", "CHAVE_ASSINATURA", "DESTINATARIOS_PERMITIDOS", "TOKEN_TESTE"})
        self.assertRegex(segredos["CHAVE_HMAC"], r"^[0-9a-f]{64}$")
        self.assertRegex(segredos["CHAVE_ASSINATURA"], r"^[0-9a-f]{64}$")
        self.assertRegex(segredos["TOKEN_TESTE"], r"^[A-Za-z0-9_-]{43}$")
        self.assertNotEqual(segredos["CHAVE_HMAC"], segredos["CHAVE_ASSINATURA"])
        # Só os endereços fictícios .invalid, com a CHAVE_HMAC deste ambiente.
        chave = bytes.fromhex(segredos["CHAVE_HMAC"])
        self.assertEqual(segredos["DESTINATARIOS_PERMITIDOS"], dt.montar(chave, list(tr.ENDERECOS_TESTE))[0])
        self.assertTrue(all(e.endswith(".invalid") for e in tr.ENDERECOS_TESTE))
        # .env com os mesmos valores; config com URL e token.
        env = dict(l.split("=", 1) for l in self.ler("segredos.env").splitlines())
        self.assertEqual(env, segredos)
        self.assertEqual(json.loads(self.ler("teste_remoto.json")), {"url": URL, "token": segredos["TOKEN_TESTE"]})
        # O terminal não mostra segredos nem e-mails.
        for proibido in (*segredos.values(), *tr.ENDERECOS_TESTE):
            self.assertNotIn(proibido, saida)

    def test_nunca_sobrescreve(self):
        self.preparar()
        antes = self.ler("segredos.json")
        with self.assertRaises(tr.Falha):
            tr.preparar(self.pasta, URL)
        self.assertEqual(self.ler("segredos.json"), antes)

    def test_recusa_pasta_no_repositorio(self):
        with self.assertRaises(tr.Falha):
            tr.preparar(os.path.join(tr.RAIZ_REPOSITORIO, "nao-criar-e4"), URL)
        self.assertFalse(os.path.exists(os.path.join(tr.RAIZ_REPOSITORIO, "nao-criar-e4")))

    def test_ler_config_exige_600(self):
        self.preparar()
        caminho = os.path.join(self.pasta, "teste_remoto.json")
        self.assertEqual(tr.ler_config(caminho)[0], URL)
        os.chmod(caminho, 0o644)
        with self.assertRaises(tr.Falha):
            tr.ler_config(caminho)


class TestJanelas(unittest.TestCase):
    def test_uma_hora_por_comando(self):
        pasta = tempfile.mkdtemp()
        h10 = datetime.datetime(2026, 10, 9, 10, 5, tzinfo=datetime.timezone.utc)
        tr.reservar_janela(pasta, URL, "basico", h10)
        with self.assertRaises(tr.Falha):
            tr.reservar_janela(pasta, URL, "ip", h10.replace(minute=50))
        tr.reservar_janela(pasta, "http://127.0.0.1:8787", "ip", h10)  # outro ambiente
        tr.reservar_janela(pasta, URL, "ip", h10.replace(hour=11))
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(pasta, "janelas.json")).st_mode), 0o600)


class TestLimitesDiarios(unittest.TestCase):
    """O roteiro se planeja pelos limites diários do contrato, sem alterá-los."""

    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.dia = datetime.datetime(2026, 10, 9, 0, 5, tzinfo=datetime.timezone.utc)

    def rodar(self, comando, hora):
        tr.reservar_janela(self.pasta, URL, comando, self.dia.replace(hour=hora))

    def test_tres_comandos_cabem_no_dia_e_repeticao_nao(self):
        self.rodar("basico", 13)
        self.rodar("limite-destino", 14)
        self.rodar("ip", 15)  # 24 de 30
        with self.assertRaises(tr.Falha):
            self.rodar("basico", 16)  # 31
        tr.reservar_janela(self.pasta, URL, "basico", self.dia + datetime.timedelta(days=1))  # novo dia UTC

    def test_limite_destino_no_maximo_duas_vezes_por_dia(self):
        self.rodar("limite-destino", 1)
        self.rodar("limite-destino", 2)
        with self.assertRaises(tr.Falha):
            self.rodar("limite-destino", 3)

    def test_valores_conferem_com_o_servico(self):
        with open(os.path.join(tr.RAIZ_REPOSITORIO, "servidor", "src", "config.ts"), encoding="utf-8") as arquivo:
            config = arquivo.read()
        valor = lambda nome: int(re.search(rf"export const {nome} = (\d+);", config).group(1))  # noqa: E731
        self.assertEqual(tr.LIMITE_IP_DIA, valor("LIMITE_IP_PEDIDOS_DIA"))
        self.assertEqual(tr.EXECUCOES_LIMITE_DESTINO_DIA * valor("LIMITE_DESTINO_HORA"), valor("LIMITE_DESTINO_DIA"))
        self.assertEqual(tr.PEDIDOS_DO_IP["ip"], valor("LIMITE_IP_PEDIDOS_HORA") + 1)
        self.assertLessEqual(tr.PEDIDOS_DO_IP["basico"], valor("LIMITE_IP_PEDIDOS_HORA"))
        self.assertEqual(tr.PEDIDOS_DO_IP["limite-destino"], valor("LIMITE_DESTINO_HORA") + 1)

    def test_registro_ilegivel_recusa(self):
        with open(os.path.join(self.pasta, "janelas.json"), "w", encoding="utf-8") as arquivo:
            arquivo.write("{quebrado")
        with self.assertRaises(tr.Falha):
            self.rodar("basico", 1)


class ServicoFalso(tr.Cliente):
    """Responde como o contrato v1.1, em memória (sem rede)."""

    def __init__(self, token):
        super().__init__("http://127.0.0.1:1", token)
        self.permitidos = set(tr.ENDERECOS_TESTE)
        self.desafios = {}
        self.chaves = {}
        self.pedidos_ip = 0
        self.ultimo = {}
        self.vistos = []

    def enviar(self, caminho, corpo=None, metodo="POST", chave=None, autorizacao=True, extra=None, bruto=None):
        token_ok = autorizacao is True
        self.vistos.append((caminho, metodo))
        if not token_ok:
            return 404, {"erro": "rota_nao_encontrada"}
        if bruto is not None:
            return (413, {"erro": "corpo_grande_demais"}) if len(bruto) > 4096 else (400, {"erro": "requisicao_invalida"})
        if caminho == "/v1/desafios":
            if metodo != "POST":
                return 405, {"erro": "metodo_nao_permitido"}
            self.pedidos_ip += 1
            if self.pedidos_ip > 10:
                return 429, {"erro": "limite_excedido"}
            if chave in self.chaves:
                return self.chaves[chave]
            email = corpo["email"]
            campos = {"desafio_id": f"d{len(self.desafios):021d}", "expira_em": "x", "reenvio_permitido_em": "x", "agora": "x"}
            if email not in self.permitidos:
                if corpo["finalidade"] != "recuperacao_senha":
                    return 403, {"erro": "destinatario_nao_permitido"}
                return 202, campos
            if email in self.ultimo:
                return 429, {"erro": "aguarde", "reenvio_permitido_em": "x", "agora": "x"}
            self.ultimo[email] = True
            self.desafios[campos["desafio_id"]] = {"segredo": corpo["segredo"], "restantes": 5}
            self.chaves[chave or ""] = (201, campos)
            return 201, campos
        m = re.fullmatch(r"/v1/desafios/([^/]+)/validacao", caminho)
        if m:
            d = self.desafios.get(m.group(1))
            if not d or d["segredo"] != corpo["segredo"]:
                return 404, {"erro": "desafio_nao_encontrado"}
            if d["restantes"] == 0:
                return 410, {"erro": "desafio_encerrado"}
            d["restantes"] -= 1
            return 422, {"erro": "codigo_invalido", "tentativas_restantes": d["restantes"]}
        return 404, {"erro": "rota_nao_encontrada"}


class TestCasos(unittest.TestCase):
    TOKEN = "x" * 43

    def rodar(self, funcao, *args):
        relatorio = tr.Relatorio()
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            funcao(*args, relatorio)
            relatorio.fim()
        return relatorio, saida.getvalue()

    def test_basico_aprovado_sem_segredos_na_saida(self):
        servico = ServicoFalso(self.TOKEN)
        relatorio, saida = self.rodar(tr.caso_basico, servico)
        self.assertEqual(relatorio.falhas, 0, saida)
        self.assertIn("resultado: aprovado", saida)
        self.assertEqual(servico.pedidos_ip, 7)  # como documentado no roteiro
        for proibido in (self.TOKEN, *tr.ENDERECOS_TESTE, tr.FORA_DA_LISTA):
            self.assertNotIn(proibido, saida)

    def test_ip_aprovado(self):
        servico = ServicoFalso(self.TOKEN)
        relatorio, saida = self.rodar(tr.caso_ip, servico)
        self.assertEqual(relatorio.falhas, 0, saida)
        self.assertEqual(servico.pedidos_ip, 11)

    def test_relatorio_recusa_codigo_de_6_digitos_na_resposta(self):
        relatorio = tr.Relatorio()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(relatorio.conferir("x", 201, {"codigo": "123456"}, 201))
            self.assertFalse(relatorio.conferir("y", 404, None, 404, "rota_nao_encontrada"))
        self.assertEqual(relatorio.falhas, 2)


if __name__ == "__main__":
    unittest.main()
