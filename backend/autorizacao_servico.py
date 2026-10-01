"""
autorizacao_servico.py -- Verificação da autorização assinada pelo serviço de
códigos do Sino (ERS v6.0, Etapa 8; docs/contrato-servico-codigos.md).

Único módulo do Sino que importa a biblioteca `cryptography`, e só pela API
pública de Ed25519. Aqui se confere apenas o formato e a assinatura do token;
finalidade, contexto e prazo são conferidos por `servico_codigos`, que conhece
a operação.

Tudo é estrito: base64url canônico sem preenchimento, JSON sem chaves
duplicadas nem NaN/Infinity, chaves exatas na ordem do contrato e tipos sem
ambiguidade (booleano não vale como inteiro, 1.0 não vale como inteiro).
"""

import base64
import json
import re
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PREFIXO_ASSINATURA = b"sino-autorizacao-v1."
TAMANHO_MAXIMO_TOKEN = 1024
TAMANHO_MAXIMO_CONTEUDO = 512
TAMANHO_ASSINATURA = 64
CHAVES_DO_CONTEUDO = ("v", "kid", "jti", "fin", "ctx", "iat", "exp")
FINALIDADES = ("cadastro", "alteracao_email", "recuperacao_senha")

_RE_TOKEN = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_RE_BASE64URL = re.compile(r"[A-Za-z0-9_-]*")
RE_KID = re.compile(r"[A-Za-z0-9_.-]{1,64}")
_RE_JTI = re.compile(r"[A-Za-z0-9_-]{22}")
_RE_CONTEXTO = re.compile(r"[0-9a-f]{64}")


class AutorizacaoInvalidaError(ValueError):
    """Token recusado. A mensagem é só um motivo curto, nunca o conteúdo."""


class JsonEstritoError(ValueError):
    """JSON fora das regras estritas (duplicatas, NaN/Infinity, UTF-8 inválido)."""


def _rejeitar_duplicadas(pares):
    objeto = {}
    for chave, valor in pares:
        if chave in objeto:
            raise JsonEstritoError("chave duplicada")
        objeto[chave] = valor
    return objeto


def _rejeitar_constante(_nome):
    raise JsonEstritoError("constante não permitida")


def carregar_json_estrito(dados: bytes):
    """JSON a partir de bytes UTF-8, recusando chaves duplicadas e NaN/Infinity."""
    try:
        texto = dados.decode("utf-8", errors="strict")
    except UnicodeDecodeError as erro:
        raise JsonEstritoError("UTF-8 inválido") from erro
    try:
        return json.loads(texto, object_pairs_hook=_rejeitar_duplicadas, parse_constant=_rejeitar_constante)
    except json.JSONDecodeError as erro:
        raise JsonEstritoError("JSON inválido") from erro


def decodificar_base64url(texto: str) -> bytes:
    """Base64url sem preenchimento, canônico (bits de sobra zerados)."""
    if not isinstance(texto, str) or not _RE_BASE64URL.fullmatch(texto) or len(texto) % 4 == 1:
        raise ValueError("base64url inválido")
    dados = base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))
    if base64.urlsafe_b64encode(dados).rstrip(b"=").decode("ascii") != texto:
        raise ValueError("base64url não canônico")
    return dados


def chave_publica_de_hex(texto: str) -> Ed25519PublicKey:
    if not isinstance(texto, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", texto):
        raise ValueError("chave pública Ed25519 deve ter 64 caracteres hexadecimais")
    return Ed25519PublicKey.from_public_bytes(bytes.fromhex(texto))


@dataclass(frozen=True)
class ConteudoAutorizacao:
    kid: str
    jti: str
    finalidade: str
    contexto: str
    iat: int
    exp: int


def _inteiro(valor) -> bool:
    return type(valor) is int


def verificar_assinatura(token, chaves_publicas: dict) -> ConteudoAutorizacao:
    """
    Confere formato, tamanhos, JSON estrito e a assinatura Ed25519 com a chave
    pública do `kid`. Devolve o conteúdo ou levanta AutorizacaoInvalidaError.
    """
    if type(token) is not str or len(token) > TAMANHO_MAXIMO_TOKEN or not _RE_TOKEN.fullmatch(token):
        raise AutorizacaoInvalidaError("formato")
    payload, assinatura_b64 = token.split(".")
    try:
        conteudo_bytes = decodificar_base64url(payload)
        assinatura = decodificar_base64url(assinatura_b64)
    except ValueError as erro:
        raise AutorizacaoInvalidaError("base64url") from erro
    if len(conteudo_bytes) > TAMANHO_MAXIMO_CONTEUDO or len(assinatura) != TAMANHO_ASSINATURA:
        raise AutorizacaoInvalidaError("tamanho")
    try:
        conteudo = carregar_json_estrito(conteudo_bytes)
    except JsonEstritoError as erro:
        raise AutorizacaoInvalidaError("json") from erro
    if type(conteudo) is not dict or tuple(conteudo.keys()) != CHAVES_DO_CONTEUDO:
        raise AutorizacaoInvalidaError("chaves")

    v, kid, jti, fin, ctx, iat, exp = (conteudo[c] for c in CHAVES_DO_CONTEUDO)
    if not (
        _inteiro(v) and v == 1
        and type(kid) is str and RE_KID.fullmatch(kid)
        and type(jti) is str and _RE_JTI.fullmatch(jti)
        and type(fin) is str and fin in FINALIDADES
        and type(ctx) is str and _RE_CONTEXTO.fullmatch(ctx)
        and _inteiro(iat) and _inteiro(exp) and 0 < iat <= exp
    ):
        raise AutorizacaoInvalidaError("campos")

    chave = chaves_publicas.get(kid)
    if chave is None:
        raise AutorizacaoInvalidaError("kid desconhecido")
    try:
        chave.verify(assinatura, PREFIXO_ASSINATURA + payload.encode("ascii"))
    except InvalidSignature as erro:
        raise AutorizacaoInvalidaError("assinatura") from erro
    return ConteudoAutorizacao(kid=kid, jti=jti, finalidade=fin, contexto=ctx, iat=iat, exp=exp)
