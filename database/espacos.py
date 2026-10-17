"""
espacos.py — Caracteres de espaço e invisíveis (ERS v7.0, 5.40 / M1, lista E1).

Fonte única da lista de 31 caracteres usada pela interface (backend/main.py)
na limpeza do e-mail digitado (5.41) e nas orientações sobre senhas (5.42), e
pela camada de dados (database/db.py) na recusa de senhas novas (5.42).

A lista explícita é a regra, independentemente da definição de espaço de cada
linguagem: os 29 primeiros são os que o Python 3.11 considera espaço em
branco (`str.isspace`), mais U+200B e U+FEFF.

Nada aqui altera dados gravados nem a regra compartilhada de formato do
e-mail (serviço, cliente e camada de dados), que continua estrita.
"""

CARACTERES_E1 = frozenset(
    # Controles de espaço
    "\u0009\u000a\u000b\u000c\u000d\u001c\u001d\u001e\u001f\u0085"
    # Espaços
    "   " + "".join(chr(c) for c in range(0x2000, 0x200B)) + "  　"
    # Separadores
    "  "
    # Invisíveis de largura zero
    "​﻿"
)
_CARACTERES_E1_TEXTO = "".join(sorted(CARACTERES_E1))

MENSAGEM_EMAIL_COM_INVISIVEL_NO_MEIO = "Remova os espaços ou caracteres invisíveis do meio do e-mail."
MENSAGEM_SENHA_COM_INVISIVEL_NAS_PONTAS = "Verifique se há espaços ou caracteres invisíveis no início ou no fim da senha."
MENSAGEM_SENHA_NOVA_COM_INVISIVEL = "A senha não pode conter espaços nem caracteres invisíveis."


def limpar_email_digitado(texto):
    """5.41 (E1, E2): remove os caracteres da lista só das extremidades,
    repetidamente; nada do meio. Entrada que não é texto vira ""."""
    return texto.strip(_CARACTERES_E1_TEXTO) if isinstance(texto, str) else ""


def contem_caractere_e1(texto):
    """Algum caractere da lista, em qualquer posição."""
    return isinstance(texto, str) and any(caractere in CARACTERES_E1 for caractere in texto)


def tem_caractere_e1_nas_pontas(texto):
    """5.42 (S1): o texto começa ou termina com algum caractere da lista."""
    return isinstance(texto, str) and bool(texto) and (texto[0] in CARACTERES_E1 or texto[-1] in CARACTERES_E1)


def email_com_invisivel_no_meio(texto):
    """5.41 (E3): depois da limpeza das extremidades, sobra algum caractere da lista?"""
    return contem_caractere_e1(limpar_email_digitado(texto))
