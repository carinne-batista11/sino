"""
limites.py — Limites de caracteres dos campos de texto (ERS v6.0, 5.23 / T5).

Fonte única da contagem e dos máximos, usada tanto pela interface
(backend/main.py) quanto pela gravação (database/db.py): o que a tela aceita
é exatamente o que o banco aceita.

A contagem considera o caractere percebido pelo usuário (agrupamento de
grafemas estendido, `\\X` do módulo `regex`): um emoji composto como 👩‍💻,
uma bandeira ou uma letra com acento combinante contam como 1.

Nada aqui corta ou modifica texto: valores acima do limite são apenas
recusados (P4). Dados antigos já gravados acima do limite continuam
intactos até que o usuário os edite.
"""

import regex

LIMITE_NOME_USUARIO = 70
LIMITE_NOME_CONTA = 30
LIMITE_NOME_CATEGORIA = 30
LIMITE_DESCRICAO = 500

# Rótulos usados nas mensagens amigáveis (sujeito da frase).
ROTULOS_CAMPOS = {
    "nome_usuario": "O nome",
    "nome_conta": "O nome da conta",
    "nome_categoria": "O nome da categoria",
    "descricao": "A descrição",
}

_GRAFEMA = regex.compile(r"\X")


def grafemas(texto):
    """Caracteres percebidos pelo usuário (agrupamentos `\\X`), em ordem."""
    if not texto:
        return []
    return _GRAFEMA.findall(texto)


def contar_caracteres(texto):
    """Quantidade de caracteres percebidos pelo usuário; `None` conta 0."""
    return len(grafemas(texto))


def mensagem_limite(campo, limite, contagem):
    """Mensagem amigável para um texto acima do limite."""
    return (
        f"{ROTULOS_CAMPOS.get(campo, 'O texto')} pode ter no máximo {limite} "
        f"caracteres (atual: {contagem})."
    )


class LimiteDeCaracteresError(ValueError):
    """Texto acima do limite de caracteres (5.23). Nada foi gravado."""

    def __init__(self, campo, limite, contagem):
        self.campo = campo
        self.limite = limite
        self.contagem = contagem
        super().__init__(mensagem_limite(campo, limite, contagem))


def excede_limite(texto, limite):
    return contar_caracteres(texto) > limite


def validar_limite(campo, texto, limite):
    """Levanta `LimiteDeCaracteresError` se `texto` passar de `limite`."""
    contagem = contar_caracteres(texto)
    if contagem > limite:
        raise LimiteDeCaracteresError(campo, limite, contagem)


def normalizar_descricao(texto):
    """
    Descrição (5.22) como deve ser comparada, contada e gravada: sem
    espaços/quebras nas bordas, quebras de linha internas preservadas.
    Vazia ou só com espaços vira `None` (NULL no banco).
    """
    if texto is None:
        return None
    texto = texto.strip()
    return texto or None
