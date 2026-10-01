"""
apoio_servico.py -- Apoio aos testes do cliente do serviço de códigos.

Relógio monotônico falso, esperas que só avançam esse relógio (sem sleep),
aleatoriedade controlada, transporte falso com roteiro e chave Ed25519 de
teste (a mesma dos testes do servidor; não é credencial). Nenhum teste aqui
usa rede nem banco.
"""

import base64
import contextlib
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone

RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ_PROJETO, "backend"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

import autorizacao_servico  # noqa: E402
import servico_codigos  # noqa: E402

PASTA_CONFORMIDADE = os.path.join(RAIZ_PROJETO, "servidor", "test", "conformidade")
KID = "teste-1"
CHAVE_PRIVADA = Ed25519PrivateKey.from_private_bytes(bytes([0x22]) * 32)
URL_BASE = "https://servico.teste"
# Relógio do servidor nos testes: 2026-10-01 12:00:00.000 UTC.
AGORA_SERVIDOR_MS = int(datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc).timestamp()) * 1000
VALIDADE_MS = 600_000
DESAFIO = "QUFBQUFBQUFBQUFBQUFBQQ"


def carregar_conformidade(nome):
    with open(os.path.join(PASTA_CONFORMIDADE, nome), encoding="utf-8") as arquivo:
        return json.load(arquivo)


def configuracao(chaves=None):
    return servico_codigos.ConfiguracaoServico(
        url_base=URL_BASE,
        chaves_publicas=chaves if chaves is not None else {KID: CHAVE_PRIVADA.public_key()},
    )


def iso(ms):
    momento = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return momento.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms % 1000:03d}Z"


def b64url(dados):
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode("ascii")


def assinar(conteudo, chave=CHAVE_PRIVADA):
    """Token no formato do contrato; `conteudo` pode ser dict ou texto JSON."""
    texto = conteudo if isinstance(conteudo, str) else json.dumps(conteudo, separators=(",", ":"))
    payload = b64url(texto.encode("utf-8"))
    return f"{payload}.{b64url(chave.sign(autorizacao_servico.PREFIXO_ASSINATURA + payload.encode('ascii')))}"


def conteudo_autorizacao(operacao, exp_s, iat_s=None, jti="anRpLWRlLXRlc3RlLTAwMQ", **trocas):
    conteudo = {
        "v": 1, "kid": KID, "jti": jti, "fin": operacao.finalidade, "ctx": operacao.contexto,
        "iat": iat_s if iat_s is not None else AGORA_SERVIDOR_MS // 1000, "exp": exp_s,
    }
    conteudo.update(trocas)
    return conteudo


class Relogio:
    """Relógio monotônico falso."""

    def __init__(self, agora=1000.0):
        self.agora = agora

    def __call__(self):
        return self.agora

    def avancar(self, segundos):
        self.agora += segundos


class Esperas:
    """Substitui asyncio.sleep: registra a espera e avança o relógio falso."""

    def __init__(self, relogio):
        self.relogio = relogio
        self.feitas = []

    async def __call__(self, segundos):
        self.feitas.append(segundos)
        self.relogio.avancar(segundos)


class Aleatorio:
    """Bytes de uma fila (na ordem em que o cliente sorteia) ou determinísticos."""

    def __init__(self, fila=None):
        self.fila = list(fila or [])
        self.contador = 0

    def __call__(self, n):
        if self.fila:
            dados = self.fila.pop(0)
            if len(dados) != n:
                raise AssertionError(f"esperava sortear {n} bytes, a fila tinha {len(dados)}")
            return dados
        self.contador += 1
        return hashlib.sha256(f"aleatorio-{self.contador}".encode()).digest()[:n]


def resposta(status, corpo, cabecalhos=None, tipo="application/json; charset=utf-8"):
    dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo, separators=(",", ":")).encode("utf-8")
    base = {"content-type": tipo} if tipo else {}
    base.update({k.lower(): v for k, v in (cabecalhos or {}).items()})
    return servico_codigos.RespostaHttp(status, base, dados)


def corpo_desafio(desafio=DESAFIO, agora=AGORA_SERVIDOR_MS, expira=None, reenvio=None, **extra):
    corpo = {
        "desafio_id": desafio,
        "expira_em": iso(expira if expira is not None else agora + VALIDADE_MS),
        "reenvio_permitido_em": iso(reenvio if reenvio is not None else agora + 60_000),
        "agora": iso(agora),
    }
    corpo.update(extra)
    return corpo


class Atraso:
    """Item de roteiro: avança o relógio durante o envio e depois responde."""

    def __init__(self, segundos, item):
        self.segundos = segundos
        self.item = item


class TransporteFalso:
    """Transporte com roteiro: RespostaHttp, exceção, Atraso ou função(requisição)."""

    def __init__(self, roteiro, relogio=None):
        self.roteiro = list(roteiro)
        self.relogio = relogio
        self.requisicoes = []

    async def enviar(self, requisicao):
        self.requisicoes.append(requisicao)
        if not self.roteiro:
            raise AssertionError("requisição além do roteiro")
        item = self.roteiro.pop(0)
        if isinstance(item, Atraso):
            self.relogio.avancar(item.segundos)
            item = item.item
        if callable(item) and not isinstance(item, servico_codigos.RespostaHttp):
            item = item(requisicao)
        if isinstance(item, BaseException):
            raise item
        return item


def cabecalho(requisicao, nome):
    for chave, valor in requisicao.cabecalhos:
        if chave.lower() == nome.lower():
            return valor
    return None


def novo_cliente(roteiro, relogio=None, aleatorio=None, chaves=None):
    relogio = relogio or Relogio()
    esperas = Esperas(relogio)
    transporte = TransporteFalso(roteiro, relogio)
    cliente = servico_codigos.ClienteServicoCodigos(
        configuracao(chaves), transporte, relogio=relogio, esperar=esperas, aleatorio=aleatorio or Aleatorio(),
    )
    return cliente, transporte, relogio, esperas


@contextlib.contextmanager
def capturar_stderr():
    saida = io.StringIO()
    with contextlib.redirect_stderr(saida):
        yield saida
