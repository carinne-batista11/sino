"""
Lista de destinatários permitidos do serviço de códigos (ERS v7.0, 5.49;
contrato v1.1). Ferramenta local: gera o valor do segredo
DESTINATARIOS_PERMITIDOS a partir dos e-mails, sem nunca mostrá-los.

    python destinatarios.py gerar --chave ARQUIVO --saida ARQUIVO

  --chave  arquivo com a CHAVE_HMAC do ambiente (64 hex), sozinha ou numa linha
           CHAVE_HMAC=... (como segredos_dev.env);
  --saida  arquivo NOVO (permissão 600, nunca sobrescrito) com o valor do
           segredo, numa linha. Na publicação (só com autorização), por exemplo:
           wrangler secret put DESTINATARIOS_PERMITIDOS < ARQUIVO

Os e-mails são lidos sem eco no terminal (um por vez; vazio termina) ou, se a
entrada não for um terminal, um por linha. O terminal mostra só contagens:
nunca e-mails, a chave ou os resumos.

Formato do valor (o mesmo de servidor/src/nucleo/destinatarios.ts):

    v1:<HMAC("verificacao-lista")>,<HMAC("email" + 0x1f + e-mail normalizado)>,...

com HMAC-SHA256 pela CHAVE_HMAC, em hexadecimal minúsculo. A verificação só
detecta uma lista gerada com outra CHAVE_HMAC; não prova a integridade do
restante do conteúdo. Trocar a CHAVE_HMAC exige gerar a lista de novo.

O formato e a normalização do e-mail são os do contrato (sem a M1): aparar só
espaços comuns (U+0020) nas bordas; ASCII imprimível, exatamente um "@",
partes não vazias, até 254 caracteres; minúsculas ASCII. Endereços repetidos
depois da normalização entram uma vez; um endereço inválido interrompe tudo.
"""

import argparse
import getpass
import hashlib
import hmac
import os
import re
import sys

VERSAO = "v1"
LIMITE = 50
TAMANHO_MAXIMO_EMAIL = 254
_RE_EMAIL = re.compile(r"[\x21-\x3f\x41-\x7e]+@[\x21-\x3f\x41-\x7e]+")
_RE_CHAVE = re.compile(r"[0-9a-fA-F]{64}")

# Endereços FICTÍCIOS do modo de demonstração e das rodadas locais de
# validação. O domínio .invalid é reservado (RFC 2606) e nunca recebe e-mail;
# as mensagens vão só para a caixa local deste computador.
DESTINATARIOS_FICTICIOS = (
    "pessoa1@demonstracao.invalid",
    "pessoa2@demonstracao.invalid",
    "pessoa3@demonstracao.invalid",
)


class ListaInvalida(ValueError):
    """Entrada recusada; a mensagem nunca contém o e-mail."""


def aparar(texto):
    return texto.strip(" ")


def email_valido(texto):
    if not isinstance(texto, str):
        return False
    email = aparar(texto)
    return len(email) <= TAMANHO_MAXIMO_EMAIL and _RE_EMAIL.fullmatch(email) is not None


_MINUSCULAS_ASCII = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def normalizar(texto):
    """Forma de comparação do serviço; só para endereços válidos."""
    return aparar(texto).translate(_MINUSCULAS_ASCII)


def _hmac(chave, *partes):
    return hmac.new(chave, "\x1f".join(partes).encode("utf-8"), hashlib.sha256).hexdigest()


def resumo(chave, email):
    return _hmac(chave, "email", normalizar(email))


def verificacao(chave):
    return f"{VERSAO}:{_hmac(chave, 'verificacao-lista')}"


def montar(chave, emails):
    """(valor do segredo, quantidade de repetidos ignorados)."""
    resumos = []
    for posicao, email in enumerate(emails, start=1):
        if not email_valido(email):
            raise ListaInvalida(f"o {posicao}º endereço não está no formato aceito; nada foi gravado")
        r = resumo(chave, email)
        if r not in resumos:
            resumos.append(r)
    if not resumos:
        raise ListaInvalida("nenhum endereço informado; nada foi gravado")
    if len(resumos) > LIMITE:
        raise ListaInvalida(f"mais de {LIMITE} endereços diferentes; nada foi gravado")
    return ",".join([verificacao(chave), *resumos]), len(emails) - len(resumos)


def ler_chave(caminho):
    """CHAVE_HMAC (32 bytes) de um arquivo; os erros nunca mostram o conteúdo."""
    with open(caminho, encoding="utf-8") as arquivo:
        linhas = [linha.strip() for linha in arquivo.read().splitlines() if linha.strip()]
    candidatos = [l.split("=", 1)[1] for l in linhas if l.startswith("CHAVE_HMAC=")]
    if not candidatos and len(linhas) == 1:
        candidatos = linhas
    if len(candidatos) != 1 or not _RE_CHAVE.fullmatch(candidatos[0]):
        raise ListaInvalida("CHAVE_HMAC ausente ou fora do formato (64 hexadecimais) no arquivo da chave")
    return bytes.fromhex(candidatos[0])


def gravar_privado(caminho, texto):
    """Cria o arquivo com permissão 600; nunca sobrescreve."""
    descritor = os.open(caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
        arquivo.write(texto)


def ler_emails(entrada=None, pedir=getpass.getpass):
    entrada = sys.stdin if entrada is None else entrada
    if not entrada.isatty():
        return [linha.rstrip("\r\n") for linha in entrada if linha.strip(" \r\n")]
    emails = []
    while True:
        email = pedir("E-mail (não aparece na tela; vazio para terminar): ")
        if not email:
            return emails
        emails.append(email)


def gerar(caminho_chave, caminho_saida, entrada=None, pedir=getpass.getpass):
    if os.path.exists(caminho_saida):
        raise ListaInvalida("o arquivo de saída já existe (não sobrescrevo)")
    chave = ler_chave(caminho_chave)
    texto, repetidos = montar(chave, ler_emails(entrada, pedir))
    gravar_privado(caminho_saida, texto + "\n")
    total = texto.count(",")
    print(f"destinatarios: {total} endereço(s) gravado(s) em {caminho_saida}"
          + (f"; {repetidos} repetido(s) ignorado(s)" if repetidos else ""))


def main(argv=None):
    analisador = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    comandos = analisador.add_subparsers(dest="comando", required=True)
    g = comandos.add_parser("gerar")
    g.add_argument("--chave", required=True)
    g.add_argument("--saida", required=True)
    args = analisador.parse_args(argv)
    try:
        gerar(args.chave, args.saida)
    except (ListaInvalida, OSError) as erro:
        detalhe = erro if isinstance(erro, ListaInvalida) else type(erro).__name__
        raise SystemExit(f"destinatarios: {detalhe}") from None
    return 0


if __name__ == "__main__":
    sys.exit(main())
