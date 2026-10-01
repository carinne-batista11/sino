"""
servico_codigos.py -- Cliente do serviço de códigos de e-mail do Sino (ERS
v6.0, Etapa 8; contrato em docs/contrato-servico-codigos.md).

Responsabilidades deste módulo (sem banco e sem telas):
  * chamadas HTTP assíncronas por um transporte injetável (httpx no app);
  * estado de cada operação em memória: nonce, contexto, segredo S, chaves de
    idempotência e prazos;
  * repetições seguras (sempre com a mesma Idempotency-Key) e interpretação
    estrita das respostas do contrato;
  * conferência da autorização assinada (via autorizacao_servico) contra a
    finalidade, o contexto e a validade original da operação.

Prazos: a validade original é guardada em UTC (expira_em do servidor) e só é
comparada com o `exp` assinado, também UTC. O tempo restante usa um prazo no
relógio monotônico, calculado de forma conservadora a partir do INÍCIO da
requisição e nunca ampliado para o mesmo desafio. UTC e monotônico nunca são
comparados entre si.

Cancelamento: `OperacaoCodigo.descartar()` marca a operação como cancelada; o
cliente confere isso antes de cada envio, espera e repetição e depois de cada
resposta, e não registra nada numa operação cancelada (resultado
`OperacaoCancelada`). Isso não corta uma chamada HTTP que já está em
andamento: as telas devem também cancelar a tarefa assíncrona (task.cancel()),
o que propaga CancelledError e fecha a resposta HTTP imediatamente.

Nada aqui registra S, chaves, código, token ou e-mail: os registros mostram só
o contexto e o tipo do erro.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from urllib.parse import urlsplit

import autorizacao_servico as autorizacao

FINALIDADES = autorizacao.FINALIDADES
TAMANHO_MAXIMO_RESPOSTA = 16 * 1024
MARGEM_SEGURANCA_S = 2.0
TEMPO_LIMITE_PADRAO_S = 10.0
# Cadastro e alteração: o serviço só responde depois de tentar o envio.
TEMPO_LIMITE_PEDIDO_COM_ENVIO_S = 40.0
REPETICOES_DE_REDE = 2
ESPERAS_DE_REDE_S = (0.5, 1.0)
RETRY_AFTER_PADRAO_S = 2
RETRY_AFTER_MAXIMO_S = 5
ESPERA_MAXIMA_EM_PROCESSAMENTO_S = 70.0
BYTES_NONCE = 32
BYTES_SEGREDO = 32
BYTES_CHAVE = 18

# Produção: definidos quando o serviço for publicado (hospedagem pendente).
URL_PRODUCAO = None
CHAVES_PUBLICAS_PRODUCAO = {}

_RE_DESAFIO = re.compile(r"[A-Za-z0-9_-]{22}")
_RE_INSTANTE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")
_RE_CODIGO = re.compile(r"[0-9]{6}")
_RE_DIGITOS = re.compile(r"[0-9]{1,6}")
_HOSTS_LOCAIS = ("localhost", "127.0.0.1", "::1")
_EPOCA = datetime(1970, 1, 1, tzinfo=timezone.utc)


def registrar_falha(contexto, erro=None):
    tipo = f" ({type(erro).__name__})" if erro is not None else ""
    print(f"Sino: falha em {contexto}{tipo}.", file=sys.stderr)


# ======================================================================
#  Configuração
# ======================================================================

@dataclass(frozen=True)
class ConfiguracaoServico:
    url_base: str
    chaves_publicas: dict  # kid -> Ed25519PublicKey


def validar_url_base(url):
    """HTTPS obrigatório; HTTP só para o próprio computador (desenvolvimento)."""
    if not isinstance(url, str):
        raise ValueError("URL do serviço ausente")
    partes = urlsplit(url.strip())
    host = (partes.hostname or "").lower()
    if partes.scheme not in ("https", "http") or not host:
        raise ValueError("URL do serviço inválida")
    if partes.scheme == "http" and host not in _HOSTS_LOCAIS:
        raise ValueError("URL do serviço precisa usar HTTPS")
    if partes.username or partes.password or partes.query or partes.fragment or partes.path not in ("", "/"):
        raise ValueError("URL do serviço deve ter só esquema, host e porta")
    return f"{partes.scheme}://{partes.netloc}"


def ler_chaves_publicas(texto):
    """'kid:hex,kid:hex' -> {kid: Ed25519PublicKey}."""
    chaves = {}
    for item in (texto or "").split(","):
        if not item.strip():
            continue
        kid, separador, chave_hex = item.strip().partition(":")
        if not separador or not autorizacao.RE_KID.fullmatch(kid) or kid in chaves:
            raise ValueError("lista de chaves públicas inválida")
        chaves[kid] = autorizacao.chave_publica_de_hex(chave_hex)
    return chaves


def configuracao_do_ambiente(ambiente=None):
    """
    Configuração do serviço: SINO_SERVICO_URL e SINO_SERVICO_CHAVES no
    desenvolvimento; os valores de produção quando existirem. Devolve None se
    o serviço não estiver configurado (as telas mostram indisponível).
    """
    ambiente = os.environ if ambiente is None else ambiente
    try:
        url = ambiente.get("SINO_SERVICO_URL") or URL_PRODUCAO
        if not url:
            return None
        chaves_texto = ambiente.get("SINO_SERVICO_CHAVES")
        chaves = ler_chaves_publicas(chaves_texto) if chaves_texto else dict(CHAVES_PUBLICAS_PRODUCAO)
        if not chaves:
            return None
        return ConfiguracaoServico(url_base=validar_url_base(url), chaves_publicas=chaves)
    except ValueError as erro:
        registrar_falha("configuração do serviço de códigos", erro)
        return None


# ======================================================================
#  Transporte
# ======================================================================

@dataclass(frozen=True)
class RequisicaoHttp:
    metodo: str
    url: str
    cabecalhos: tuple
    corpo: bytes
    tempo_limite: float


@dataclass(frozen=True)
class RespostaHttp:
    status: int
    cabecalhos: dict  # nomes em minúsculas
    corpo: bytes


class ErroDeConexao(Exception):
    """Rede indisponível ou tempo esgotado: a requisição pode ter sido processada."""


class RespostaGrandeDemaisError(Exception):
    """Resposta acima de TAMANHO_MAXIMO_RESPOSTA."""


class CodificacaoNaoSuportadaError(Exception):
    """Resposta com Content-Encoding diferente de identity (o cliente não descomprime)."""


class Transporte(Protocol):
    async def enviar(self, requisicao: RequisicaoHttp) -> RespostaHttp: ...


class TransporteHttpx:
    """
    Transporte do app: httpx assíncrono sem seguir redirecionamentos, sem
    variáveis de ambiente (proxy/.netrc), sem guardar cookies e com a resposta
    lida em partes até TAMANHO_MAXIMO_RESPOSTA. `transporte_httpx` permite
    injetar um httpx.MockTransport nos testes.

    Compressão: o transporte sempre pede `Accept-Encoding: identity` e recusa,
    antes de ler o corpo, qualquer `Content-Encoding` diferente de identity;
    assim o limite vale sobre os bytes recebidos e nada é descomprimido. Um
    transporte injetado que já entregue a resposta descomprimida (e sem o
    cabeçalho) não tem essa descompressão desfeita aqui: o limite passa a
    valer sobre o conteúdo já descomprimido.
    """

    def __init__(self, transporte_httpx=None, tamanho_maximo=TAMANHO_MAXIMO_RESPOSTA):
        import httpx

        self._httpx = httpx
        self._tamanho_maximo = tamanho_maximo
        self._cliente = httpx.AsyncClient(transport=transporte_httpx, follow_redirects=False, trust_env=False)

    @property
    def cliente_httpx(self):
        return self._cliente

    async def enviar(self, requisicao):
        httpx = self._httpx
        try:
            async with asyncio.timeout(requisicao.tempo_limite):
                async with self._cliente.stream(
                    requisicao.metodo,
                    requisicao.url,
                    headers=[(nome, valor) for nome, valor in requisicao.cabecalhos
                             if nome.lower() != "accept-encoding"] + [("Accept-Encoding", "identity")],
                    content=requisicao.corpo,
                    timeout=httpx.Timeout(requisicao.tempo_limite),
                ) as resposta:
                    codificacao = resposta.headers.get("content-encoding", "identity").strip().lower()
                    if codificacao != "identity":
                        raise CodificacaoNaoSuportadaError()
                    declarado = resposta.headers.get("content-length")
                    if declarado is not None and (
                        not _RE_DIGITOS.fullmatch(declarado) or int(declarado) > self._tamanho_maximo
                    ):
                        raise RespostaGrandeDemaisError()
                    corpo = bytearray()
                    try:
                        # aiter_raw: bytes como recebidos (sem descompressão).
                        async for parte in resposta.aiter_raw():
                            corpo += parte
                            if len(corpo) > self._tamanho_maximo:
                                raise RespostaGrandeDemaisError()
                    except httpx.StreamConsumed:
                        # Resposta já carregada em memória (transporte injetado).
                        corpo = bytearray(resposta.content)
                        if len(corpo) > self._tamanho_maximo:
                            raise RespostaGrandeDemaisError() from None
                    cabecalhos = {nome.lower(): valor for nome, valor in resposta.headers.items()}
                    return RespostaHttp(resposta.status_code, cabecalhos, bytes(corpo))
        except (TimeoutError, httpx.TimeoutException, httpx.TransportError) as erro:
            raise ErroDeConexao(type(erro).__name__) from None
        finally:
            self._cliente.cookies.clear()

    async def fechar(self):
        await self._cliente.aclose()


# ======================================================================
#  Operação e resultados
# ======================================================================

def _base64url(dados):
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode("ascii")


# Formato de e-mail dos fluxos com código, igual ao do serviço
# (servidor/src/email.ts) e ao da camada de dados (database/db.py): aparam-se
# só espaços comuns (U+0020) nas bordas; depois, só ASCII imprimível, um único
# "@", partes não vazias e até 254 caracteres. Comparação em minúsculas ASCII.
TAMANHO_MAXIMO_EMAIL = 254
_RE_EMAIL = re.compile(r"[\x21-\x3f\x41-\x7e]+@[\x21-\x3f\x41-\x7e]+")


class EmailInvalidoError(ValueError):
    def __init__(self):
        super().__init__("Informe um e-mail válido.")


def aparar_email(texto):
    """Remove só espaços comuns (U+0020) das bordas (sem str.strip, que é mais amplo)."""
    return texto.strip(" ")


def validar_email(texto):
    """Devolve o e-mail sem espaços nas bordas, ou levanta EmailInvalidoError."""
    if type(texto) is not str:
        raise EmailInvalidoError()
    email = aparar_email(texto)
    if len(email) > TAMANHO_MAXIMO_EMAIL or not _RE_EMAIL.fullmatch(email):
        raise EmailInvalidoError()
    return email


def normalizar_email(texto):
    """Forma de comparação (valida antes): sem espaços nas bordas, minúsculas ASCII."""
    return validar_email(texto).lower()


def calcular_contexto(finalidade, email_normalizado, nonce):
    """contexto = SHA-256 hex de 'finalidade␟e-mail normalizado␟nonce hex' (UTF-8)."""
    texto = f"{finalidade}\x1f{email_normalizado}\x1f{nonce.hex()}"
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


class OperacaoCodigo:
    """
    Uma operação de código (cadastro, alteração de e-mail ou recuperação),
    só em memória. Cancelar = `descartar()`. O repr não mostra segredos.
    """

    def __init__(self, finalidade, email, aleatorio):
        if finalidade not in FINALIDADES:
            raise ValueError("finalidade desconhecida")
        # Mesmo formato nas três finalidades, antes de qualquer requisição:
        # na recuperação, a recusa por formato não depende de haver conta.
        self.finalidade = finalidade
        self.email = validar_email(email)
        self.email_normalizado = self.email.lower()
        nonce = aleatorio(BYTES_NONCE)
        self.contexto = calcular_contexto(finalidade, self.email_normalizado, nonce)
        self._segredo = _base64url(aleatorio(BYTES_SEGREDO))
        self.desafio_id = None
        self.expira_em_utc_ms = None  # validade original do desafio (UTC)
        self._prazo_monotonico = None  # conservador; nunca ampliado
        self._reenvio_monotonico = None
        self._validacao_pendente = None  # (código, chave) de uma tentativa sem resposta
        self.cancelada = False

    def __repr__(self):
        return f"OperacaoCodigo(finalidade={self.finalidade!r}, com_desafio={self.desafio_id is not None})"

    def segundos_para_expirar(self, agora_monotonico):
        if self._prazo_monotonico is None:
            return None
        return max(0.0, self._prazo_monotonico - agora_monotonico)

    def segundos_para_reenvio(self, agora_monotonico):
        if self._reenvio_monotonico is None:
            return 0.0
        return max(0.0, self._reenvio_monotonico - agora_monotonico)

    def _encerrar_desafio(self):
        self.desafio_id = None
        self.expira_em_utc_ms = None
        self._prazo_monotonico = None
        self._validacao_pendente = None

    def descartar(self):
        """Cancela a operação: nada mais é enviado, esperado ou registrado nela."""
        self.cancelada = True
        self._encerrar_desafio()
        self._segredo = None
        self.contexto = None


@dataclass(frozen=True)
class CodigoSolicitado:
    pass


@dataclass(frozen=True)
class EnvioNaoConfirmado:
    """A reserva do envio seguiu em andamento além da espera máxima."""


@dataclass(frozen=True)
class Aguarde:
    segundos: float


@dataclass(frozen=True)
class LimiteExcedido:
    pass


@dataclass(frozen=True)
class FalhaEnvio:
    segundos_para_reenvio: float


@dataclass(frozen=True)
class ServicoIndisponivel:
    pass


@dataclass(frozen=True)
class SemConexao:
    pass


@dataclass(frozen=True)
class DesafioEncerrado:
    pass


@dataclass(frozen=True)
class CodigoInvalido:
    tentativas_restantes: int


@dataclass(frozen=True)
class OperacaoCancelada:
    """A operação foi descartada; nenhum resultado foi registrado nela."""


@dataclass(frozen=True)
class RespostaInvalida:
    """O serviço respondeu fora do contrato (ou com autorização inválida)."""


@dataclass(frozen=True)
class AutorizacaoVerificada:
    """
    Autorização conferida. O uso único do `jti` e a gravação local ficam com a
    camada de dados (database/db.py, tabela autorizacoes_usadas), que confere
    de novo a finalidade, o vínculo com o e-mail da operação e `vigente()` no
    momento de gravar. `iat_utc_s` (assinado) é a referência de horário do
    servidor usada na limpeza segura dos registros vencidos.
    """
    jti: str
    finalidade: str
    exp_utc_s: int
    iat_utc_s: int
    email_normalizado: str
    prazo_monotonico: float

    def vigente(self, agora_monotonico):
        return agora_monotonico < self.prazo_monotonico


class _ForaDoContrato(Exception):
    pass


# ======================================================================
#  Leitura estrita das respostas
# ======================================================================

def _corpo_json(resposta):
    tipo = resposta.cabecalhos.get("content-type", "").split(";")[0].strip().lower()
    if tipo != "application/json" or len(resposta.corpo) > TAMANHO_MAXIMO_RESPOSTA:
        raise _ForaDoContrato()
    try:
        corpo = autorizacao.carregar_json_estrito(resposta.corpo)
    except autorizacao.JsonEstritoError as erro:
        raise _ForaDoContrato() from erro
    if type(corpo) is not dict:
        raise _ForaDoContrato()
    return corpo


def _exigir_chaves(corpo, chaves):
    if set(corpo.keys()) != set(chaves):
        raise _ForaDoContrato()


def _erro(corpo, codigo, *extras):
    _exigir_chaves(corpo, ("erro", *extras))
    if corpo["erro"] != codigo:
        raise _ForaDoContrato()


def _instante_ms(valor):
    if type(valor) is not str or not _RE_INSTANTE.fullmatch(valor):
        raise _ForaDoContrato()
    try:
        momento = datetime.strptime(valor, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError as erro:
        raise _ForaDoContrato() from erro
    return (momento - _EPOCA) // timedelta(milliseconds=1)


def _desafio_id(valor):
    if type(valor) is not str or not _RE_DESAFIO.fullmatch(valor):
        raise _ForaDoContrato()
    return valor


def _retry_after(resposta):
    valor = resposta.cabecalhos.get("retry-after", "")
    if _RE_DIGITOS.fullmatch(valor):
        return min(int(valor), RETRY_AFTER_MAXIMO_S)
    return RETRY_AFTER_PADRAO_S


# ======================================================================
#  Cliente
# ======================================================================

class ClienteServicoCodigos:
    def __init__(self, configuracao, transporte, relogio=time.monotonic, esperar=asyncio.sleep,
                 aleatorio=secrets.token_bytes):
        self._configuracao = configuracao
        self._transporte = transporte
        self._relogio = relogio
        self._esperar = esperar
        self._aleatorio = aleatorio

    def nova_operacao(self, finalidade, email):
        return OperacaoCodigo(finalidade, email, self._aleatorio)

    def _nova_chave(self):
        return _base64url(self._aleatorio(BYTES_CHAVE))

    async def _enviar(self, operacao, caminho, chave, corpo, tempo_limite):
        """
        POST com repetições de rede usando a MESMA chave e o mesmo corpo.
        Devolve (t0, resposta, t_recebimento), com t0 = início da tentativa
        respondida, ou um resultado final (SemConexao, RespostaInvalida ou
        OperacaoCancelada). Confere o cancelamento antes de cada espera e envio
        e depois da resposta.
        """
        requisicao = RequisicaoHttp(
            metodo="POST",
            url=self._configuracao.url_base + caminho,
            cabecalhos=(
                ("Content-Type", "application/json"),
                ("Accept", "application/json"),
                ("Accept-Encoding", "identity"),
                ("Idempotency-Key", chave),
            ),
            corpo=json.dumps(corpo, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            tempo_limite=tempo_limite,
        )
        for tentativa in range(1 + REPETICOES_DE_REDE):
            if tentativa:
                if operacao.cancelada:
                    return OperacaoCancelada()
                await self._esperar(ESPERAS_DE_REDE_S[min(tentativa - 1, len(ESPERAS_DE_REDE_S) - 1)])
            if operacao.cancelada:
                return OperacaoCancelada()
            inicio = self._relogio()
            try:
                resposta = await self._transporte.enviar(requisicao)
            except ErroDeConexao as erro:
                registrar_falha("conexão com o serviço de códigos", erro)
                continue
            except (RespostaGrandeDemaisError, CodificacaoNaoSuportadaError) as erro:
                if operacao.cancelada:
                    return OperacaoCancelada()
                registrar_falha("resposta do serviço de códigos", erro)
                return RespostaInvalida()
            if operacao.cancelada:
                return OperacaoCancelada()
            return inicio, resposta, self._relogio()
        return OperacaoCancelada() if operacao.cancelada else SemConexao()

    def _registrar_desafio(self, operacao, corpo, inicio, recebido):
        desafio_id = _desafio_id(corpo["desafio_id"])
        expira = _instante_ms(corpo["expira_em"])
        reenvio = _instante_ms(corpo["reenvio_permitido_em"])
        agora = _instante_ms(corpo["agora"])
        if expira <= agora:
            raise _ForaDoContrato()
        # Conservador: o "agora" do servidor é posterior ao início da requisição.
        prazo = inicio + (expira - agora) / 1000 - MARGEM_SEGURANCA_S
        reenvio_mono = recebido + max(0, reenvio - agora) / 1000
        if operacao.desafio_id != desafio_id:
            operacao.desafio_id = desafio_id
            operacao.expira_em_utc_ms = expira
            operacao._prazo_monotonico = prazo
            operacao._reenvio_monotonico = reenvio_mono
            operacao._validacao_pendente = None
            return
        if expira != operacao.expira_em_utc_ms:
            registrar_falha("validade divergente para o mesmo desafio", _ForaDoContrato())
        operacao._prazo_monotonico = min(operacao._prazo_monotonico, prazo)
        operacao._reenvio_monotonico = max(operacao._reenvio_monotonico, reenvio_mono)

    def _registrar_reenvio(self, operacao, corpo, recebido):
        reenvio = _instante_ms(corpo["reenvio_permitido_em"])
        agora = _instante_ms(corpo["agora"])
        operacao._reenvio_monotonico = recebido + max(0, reenvio - agora) / 1000
        return operacao._reenvio_monotonico - recebido

    async def pedir_codigo(self, operacao, sem_envio=False):
        """
        Pede um código (novo desafio, nova Idempotency-Key). Na recuperação,
        `sem_envio` vai sempre no corpo, para pedidos com e sem envio terem o
        mesmo formato.
        """
        recuperacao = operacao.finalidade == "recuperacao_senha"
        if sem_envio and not recuperacao:
            raise ValueError("sem_envio só existe na recuperação de senha")
        if operacao.cancelada:
            return OperacaoCancelada()
        corpo = {
            "finalidade": operacao.finalidade,
            "email": operacao.email,
            "contexto": operacao.contexto,
            "segredo": operacao._segredo,
        }
        if recuperacao:
            corpo["sem_envio"] = bool(sem_envio)
        chave = self._nova_chave()
        tempo_limite = TEMPO_LIMITE_PADRAO_S if recuperacao else TEMPO_LIMITE_PEDIDO_COM_ENVIO_S
        comeco = self._relogio()

        while True:
            enviado = await self._enviar(operacao, "/v1/desafios", chave, corpo, tempo_limite)
            if not isinstance(enviado, tuple):
                return enviado
            inicio, resposta, recebido = enviado
            try:
                resultado = self._interpretar_pedido(operacao, resposta, inicio, recebido, recuperacao)
            except _ForaDoContrato:
                registrar_falha("resposta do serviço de códigos", _ForaDoContrato())
                return RespostaInvalida()
            if resultado is not None:
                return resultado
            # 202 em_processamento: repetir a MESMA requisição depois do Retry-After.
            espera = _retry_after(resposta)
            if self._relogio() + espera - comeco > ESPERA_MAXIMA_EM_PROCESSAMENTO_S:
                return EnvioNaoConfirmado()
            if operacao.cancelada:
                return OperacaoCancelada()
            await self._esperar(espera)
            if operacao.cancelada:
                return OperacaoCancelada()

    def _interpretar_pedido(self, operacao, resposta, inicio, recebido, recuperacao):
        status = resposta.status
        if status >= 500 and status != 502:
            return ServicoIndisponivel()
        corpo = _corpo_json(resposta)
        if status in (201, 202):
            em_processamento = "estado" in corpo
            if em_processamento:
                if recuperacao or status != 202 or corpo["estado"] != "em_processamento":
                    raise _ForaDoContrato()
                _exigir_chaves(corpo, ("estado", "desafio_id", "expira_em", "reenvio_permitido_em", "agora"))
            else:
                if status != (202 if recuperacao else 201):
                    raise _ForaDoContrato()
                _exigir_chaves(corpo, ("desafio_id", "expira_em", "reenvio_permitido_em", "agora"))
            self._registrar_desafio(operacao, corpo, inicio, recebido)
            return None if em_processamento else CodigoSolicitado()
        if status == 429:
            if corpo.get("erro") == "aguarde":
                _erro(corpo, "aguarde", "reenvio_permitido_em", "agora")
                return Aguarde(segundos=self._registrar_reenvio(operacao, corpo, recebido))
            _erro(corpo, "limite_excedido")
            return LimiteExcedido()
        if status == 502:
            _erro(corpo, "falha_envio", "reenvio_permitido_em", "agora")
            operacao._encerrar_desafio()
            return FalhaEnvio(segundos_para_reenvio=self._registrar_reenvio(operacao, corpo, recebido))
        if status == 410:
            _erro(corpo, "desafio_encerrado")
            operacao._encerrar_desafio()
            return DesafioEncerrado()
        # 3xx, 400, 404, 409, 413 ou qualquer outro: fora do uso esperado.
        raise _ForaDoContrato()

    async def validar_codigo(self, operacao, codigo):
        """
        Valida o código do desafio atual. Uma tentativa sem resposta (sem
        conexão ou serviço indisponível) é repetida com a mesma chave se o
        mesmo código for enviado de novo; outro código é uma nova tentativa.
        """
        if type(codigo) is not str or not _RE_CODIGO.fullmatch(codigo):
            raise ValueError("o código tem 6 dígitos")
        if operacao.cancelada:
            return OperacaoCancelada()
        if operacao.desafio_id is None or operacao._prazo_monotonico is None:
            return DesafioEncerrado()
        if self._relogio() >= operacao._prazo_monotonico:
            operacao._encerrar_desafio()
            return DesafioEncerrado()

        pendente = operacao._validacao_pendente
        if pendente is not None and hmac.compare_digest(pendente[0], codigo):
            chave = pendente[1]
        else:
            chave = self._nova_chave()
        operacao._validacao_pendente = (codigo, chave)
        corpo = {"email": operacao.email, "segredo": operacao._segredo, "codigo": codigo}

        enviado = await self._enviar(
            operacao, f"/v1/desafios/{operacao.desafio_id}/validacao", chave, corpo, TEMPO_LIMITE_PADRAO_S,
        )
        if isinstance(enviado, SemConexao):
            return enviado
        if not isinstance(enviado, tuple):
            operacao._validacao_pendente = None
            return enviado
        inicio, resposta, recebido = enviado
        try:
            resultado = self._interpretar_validacao(operacao, resposta, inicio, recebido)
        except _ForaDoContrato:
            registrar_falha("resposta do serviço de códigos", _ForaDoContrato())
            operacao._validacao_pendente = None
            return RespostaInvalida()
        except autorizacao.AutorizacaoInvalidaError as erro:
            registrar_falha("autorização do serviço de códigos", erro)
            operacao._validacao_pendente = None
            return RespostaInvalida()
        if not isinstance(resultado, ServicoIndisponivel):
            operacao._validacao_pendente = None
        return resultado

    def _interpretar_validacao(self, operacao, resposta, inicio, recebido):
        status = resposta.status
        if status >= 500:
            return ServicoIndisponivel()
        corpo = _corpo_json(resposta)
        if status == 200:
            _exigir_chaves(corpo, ("autorizacao", "expira_em", "agora"))
            expira = _instante_ms(corpo["expira_em"])
            agora = _instante_ms(corpo["agora"])
            conteudo = autorizacao.verificar_assinatura(corpo["autorizacao"], self._configuracao.chaves_publicas)
            if conteudo.finalidade != operacao.finalidade or not hmac.compare_digest(
                conteudo.contexto, operacao.contexto
            ):
                raise autorizacao.AutorizacaoInvalidaError("operação")
            # Validade UTC: o exp assinado é o expira_em ORIGINAL do desafio.
            if conteudo.exp != operacao.expira_em_utc_ms // 1000:
                raise autorizacao.AutorizacaoInvalidaError("validade")
            if expira != operacao.expira_em_utc_ms:
                registrar_falha("validade divergente para o mesmo desafio", _ForaDoContrato())
            # Tempo restante: monotônico, conservador e nunca maior que o do desafio.
            prazo = min(
                operacao._prazo_monotonico,
                inicio + (conteudo.exp * 1000 - agora) / 1000 - MARGEM_SEGURANCA_S,
            )
            if recebido >= prazo:
                operacao._encerrar_desafio()
                return DesafioEncerrado()
            return AutorizacaoVerificada(
                jti=conteudo.jti, finalidade=conteudo.finalidade, exp_utc_s=conteudo.exp,
                iat_utc_s=conteudo.iat, email_normalizado=operacao.email_normalizado, prazo_monotonico=prazo,
            )
        if status == 422:
            _erro(corpo, "codigo_invalido", "tentativas_restantes")
            restantes = corpo["tentativas_restantes"]
            if type(restantes) is not int or not 0 <= restantes <= 5:
                raise _ForaDoContrato()
            return CodigoInvalido(tentativas_restantes=restantes)
        if status in (404, 410):
            _erro(corpo, "desafio_nao_encontrado" if status == 404 else "desafio_encerrado")
            operacao._encerrar_desafio()
            return DesafioEncerrado()
        if status == 429:
            _erro(corpo, "limite_excedido")
            return LimiteExcedido()
        raise _ForaDoContrato()
