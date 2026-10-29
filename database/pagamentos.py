"""
Pagamentos parciais de contas comuns (Sino 6.10).

Regras aprovadas (validadas no protótipo de pagamentos parciais, 26-28/10/2026):

  * cada pagamento é uma linha de `pp_pagamentos`, em centavos inteiros, ligada
    a UMA ocorrência; nunca se propaga para outras ocorrências da série;
  * enquanto houver saldo, `contas.status` continua 'pendente' (Pendente ou
    Atrasada pelo vencimento, como sempre); "pago parcialmente" é informação
    complementar, calculada pelos pagamentos;
  * quando os pagamentos somam exatamente o valor, a conta passa a 'pago', com
    a data do pagamento que a quitou;
  * pagamento zero, negativo, com mais de dois decimais, com data futura, acima
    do saldo ou numa conta já paga é recusado sem gravar nada;
  * `saldo_esperado_centavos` (o saldo que a tela mostrava) evita registrar duas
    vezes o mesmo pagamento: se o saldo mudou desde então, nada é gravado;
  * conta paga sem pagamentos registrados (legado ou paga de uma vez) continua
    como sempre: total pago = valor, sem linhas ou datas inventadas;
  * "Desmarcar como paga" numa conta quitada com pagamentos registrados estorna
    o último pagamento ativo ou todos (`desfazer_pagamentos`): o registro fica no
    histórico com a data da reversão e deixa de contar no total pago.

"Marcar como paga" com pagamentos parciais é `db.marcar_conta_como_paga`, que
registra só o saldo restante. "Hoje" vem de `db.date` (fixado nos testes).
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

import db

TIPOS = {"parcial": "Pagamento parcial", "saldo": "Pagamento do saldo", "integral": "Pagamento integral"}


class PagamentoError(ValueError):
    pass


class ContaNaoEncontradaError(PagamentoError):
    def __init__(self):
        super().__init__("Esta conta não existe mais.")


class ValorDePagamentoInvalidoError(PagamentoError):
    def __init__(self):
        super().__init__("Informe um valor maior que zero, com no máximo dois decimais.")


class PagamentoAcimaDoSaldoError(PagamentoError):
    def __init__(self, saldo_centavos):
        self.saldo_centavos = saldo_centavos
        super().__init__("O valor informado é maior que o saldo devedor desta conta.")


class ContaJaPagaError(PagamentoError):
    def __init__(self):
        super().__init__("Esta conta já está paga.")


class DataDePagamentoFuturaError(PagamentoError):
    def __init__(self):
        super().__init__("A data de pagamento não pode ser no futuro.")


class SaldoDesatualizadoError(PagamentoError):
    def __init__(self):
        super().__init__("O saldo desta conta mudou desde que a tela foi aberta. "
                         "Nada foi registrado; confira os valores e tente de novo.")


class ReversaoDesatualizadaError(PagamentoError):
    def __init__(self):
        super().__init__("Os pagamentos desta conta mudaram desde que a confirmação foi aberta. "
                         "Nada foi desfeito; confira os valores e tente de novo.")


class PagamentoDesatualizadoError(PagamentoError):
    def __init__(self):
        super().__init__("Este pagamento mudou desde que a tela foi aberta. "
                         "Nada foi alterado; confira os valores e tente de novo.")


class RegistroEstornadoIndisponivelError(PagamentoError):
    def __init__(self):
        super().__init__("Este registro não pode ser excluído: ele não está estornado, não pertence a esta "
                         "conta ou já foi excluído. Nada foi alterado.")


class PagamentosAcimaDoValorError(PagamentoError):
    def __init__(self, limite_centavos):
        self.limite_centavos = limite_centavos
        super().__init__("Com este valor, os pagamentos somariam mais que o valor da conta.")


def centavos_do_texto(texto):
    """Texto digitado ("1.234,56", "150", "R$ 99,9") em centavos inteiros, ou
    None se não for um valor positivo com no máximo dois decimais."""
    texto = (texto or "").strip().replace("R$", "").strip()
    if not texto:
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "." in texto and len(texto.rsplit(".", 1)[-1]) == 3:
        texto = texto.replace(".", "")
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        return None
    if not valor.is_finite() or valor <= 0 or valor != valor.quantize(Decimal("0.01")):
        return None
    return int(valor * 100)


def reais(centavos):
    """Centavos inteiros em Decimal exato (para formatar na tela)."""
    return Decimal(centavos) / 100


def obter_situacao(conta_id):
    """Valor, total pago, saldo e pagamentos registrados de uma ocorrência
    (centavos inteiros). None se a conta não existir. Só leitura."""
    conexao = db.conectar()
    try:
        cursor = conexao.cursor()
        linha = cursor.execute(
            "SELECT valor, status, data_pagamento, data_vencimento FROM contas WHERE id = ?", (conta_id,),
        ).fetchone()
        if linha is None:
            return None
        valor, status, data_pagamento, vencimento = linha
        pagamentos = []
        if db._tabela_existe(cursor, db.TABELA_PAGAMENTOS):
            pagamentos = [
                {"id": i, "valor_centavos": v, "data_pagamento": d, "tipo": t, "rotulo": TIPOS[t],
                 "estornado_em": e, "ativo": e is None}
                for i, v, d, t, e in cursor.execute(
                    f"SELECT id, valor_centavos, data_pagamento, tipo, estornado_em FROM {db.TABELA_PAGAMENTOS} "
                    "WHERE conta_id = ? ORDER BY data_pagamento, id",
                    (conta_id,),
                )
            ]
    finally:
        conexao.close()
    valor_centavos = db.centavos_de(valor)
    ativos = [p for p in pagamentos if p["ativo"]]
    registrados = sum(p["valor_centavos"] for p in ativos)
    pago_centavos = valor_centavos if status == "pago" and not ativos else registrados
    em_aberto = status != "pago"
    return {
        "conta_id": conta_id,
        "valor_centavos": valor_centavos,
        "pago_centavos": pago_centavos,
        "saldo_centavos": valor_centavos - pago_centavos,
        "status": ("atrasado" if vencimento < db.date.today().isoformat() else "pendente") if em_aberto else "pago",
        "data_pagamento": data_pagamento,
        "pago_parcialmente": em_aberto and registrados > 0,
        "pagamentos": pagamentos,   # histórico completo, em ordem de data (ativos e estornados)
        "ativos": ativos,           # só os que contam no total pago
        "paga_sem_registros": not em_aberto and not ativos,
    }


def ultimo_lancado(pagamentos_ativos):
    """Etapa 4.1: "último pagamento" = o último LANÇADO no Sino (maior id, a
    ordem persistida do registro), nunca a maior data informada. Editar um
    pagamento não muda o id, então não o torna "último"."""
    return max(pagamentos_ativos, key=lambda p: p["id"])


def pagamento_que_quitou(situacao):
    """Id do pagamento ativo que completou o valor de uma conta quitada (o
    último lançado, o mesmo que dá a data da quitação); None em aberto."""
    if situacao["status"] != "pago" or not situacao["ativos"]:
        return None
    return ultimo_lancado(situacao["ativos"])["id"]


def rotulos_para_exibir(situacao):
    """Etapa 3: rótulo de cada pagamento no histórico, calculado na leitura (o
    `tipo` gravado, a origem do lançamento, nunca muda). Ativos: um único
    pagamento que cobre o valor da conta = integral; o que completou a
    quitação depois de outros = do saldo; os demais = parcial. Estornados
    mantêm o rótulo de origem. {id: rótulo}."""
    ativos = situacao["ativos"]
    quitou = pagamento_que_quitou(situacao)
    rotulos = {}
    for p in situacao["pagamentos"]:
        if not p["ativo"]:
            rotulos[p["id"]] = TIPOS[p["tipo"]]
        elif len(ativos) == 1 and p["valor_centavos"] == situacao["valor_centavos"]:
            rotulos[p["id"]] = TIPOS["integral"]
        elif p["id"] == quitou:
            rotulos[p["id"]] = TIPOS["saldo"]
        else:
            rotulos[p["id"]] = TIPOS["parcial"]
    return rotulos


def previa_da_reversao(situacao, modo):
    """(valor revertido, continua pago, fica em aberto) em centavos, para a
    confirmação de "Desmarcar como paga". `modo`: 'ultimo' ou 'todos'."""
    ativos = situacao["ativos"]
    revertido = (ultimo_lancado(ativos)["valor_centavos"] if modo == "ultimo"
                 else sum(p["valor_centavos"] for p in ativos))
    continua = situacao["pago_centavos"] - revertido
    return revertido, continua, situacao["valor_centavos"] - continua


def pagamentos_da_escolha(situacao):
    """Etapa 4.2 (Editar conta): o que a escolha de "Marcar como pendente" viu --
    (id, valor em centavos, data) de cada pagamento ativo, na ordem da situação."""
    return [(p["id"], p["valor_centavos"], p["data_pagamento"]) for p in situacao["ativos"]]


def _ativos_da_conta(cursor, conta_id):
    return [tuple(linha) for linha in cursor.execute(
        f"SELECT id, valor_centavos, data_pagamento FROM {db.TABELA_PAGAMENTOS} "
        "WHERE conta_id = ? AND estornado_em IS NULL ORDER BY data_pagamento, id", (conta_id,))]


def conferir_reversao_da_edicao(conta_id, pagamentos_esperados):
    """Etapa 4.2 (Editar conta), antes de qualquer gravação do Salvar: a conta
    continua quitada e com exatamente os pagamentos ativos (id, valor e data) que
    a escolha mostrava? Senão, ReversaoDesatualizadaError. Só leitura."""
    conexao = db.conectar()
    try:
        cursor = conexao.cursor()
        linha = cursor.execute("SELECT status FROM contas WHERE id = ?", (conta_id,)).fetchone()
        if linha is None:
            raise ContaNaoEncontradaError()
        if (linha[0] != "pago" or not pagamentos_esperados
                or _ativos_da_conta(cursor, conta_id) != [tuple(p) for p in pagamentos_esperados]):
            raise ReversaoDesatualizadaError()
    finally:
        conexao.close()


def desfazer_pagamentos(conta_id, modo, ids_esperados, pagamentos_esperados=None):
    """Estorna pagamentos de UMA ocorrência quitada com pagamentos registrados:
    'ultimo' = o último pagamento ATIVO LANÇADO (ordem de registro, maior id;
    nunca a maior data informada); 'todos' = todos os ativos. Nada é apagado: cada estornado recebe
    `estornado_em` (data da reversão) e deixa de contar. A conta volta a
    'pendente' sem data de pagamento (Pendente/Atrasada pelo vencimento).
    `ids_esperados` = ids dos pagamentos ativos que a confirmação mostrava, em
    ordem; se mudaram (reversão repetida, outra tela), nada é gravado
    (ReversaoDesatualizadaError). Devolve a situação atualizada.

    `pagamentos_esperados` (só o Salvar de Editar conta, etapa 4.2): (id, valor,
    data) de cada ativo que a escolha mostrava. Com ele, a conferência é pelos
    próprios pagamentos -- todos iguais, nenhum a mais ou a menos -- e não pelo
    status, que o mesmo Salvar pode ter acabado de mudar ao aumentar o valor."""
    if modo not in ("ultimo", "todos"):
        raise ValueError(f"modo inválido: {modo!r}")
    conexao = db.conectar()
    conexao.isolation_level = None
    try:
        cursor = conexao.cursor()
        cursor.execute("BEGIN IMMEDIATE;")
        linha = cursor.execute("SELECT status FROM contas WHERE id = ?", (conta_id,)).fetchone()
        if linha is None:
            raise ContaNaoEncontradaError()
        detalhados = _ativos_da_conta(cursor, conta_id)
        ativos = [p[0] for p in detalhados]
        if pagamentos_esperados is None:
            if linha[0] != "pago" or not ativos or ativos != list(ids_esperados):
                raise ReversaoDesatualizadaError()
        elif (not ativos or ativos != list(ids_esperados)
              or detalhados != [tuple(p) for p in pagamentos_esperados]):
            raise ReversaoDesatualizadaError()
        alvo = [max(ativos)] if modo == "ultimo" else ativos  # último lançado (maior id)
        hoje = db.date.today().isoformat()
        for pagamento_id in alvo:
            cursor.execute(f"UPDATE {db.TABELA_PAGAMENTOS} SET estornado_em = ? WHERE id = ? AND estornado_em IS NULL",
                           (hoje, pagamento_id))
            if cursor.rowcount != 1:
                raise ReversaoDesatualizadaError()
        cursor.execute("UPDATE contas SET status = 'pendente', data_pagamento = NULL WHERE id = ?", (conta_id,))
        cursor.execute("COMMIT;")
    except BaseException:
        db._reverter_transacao(conexao)
        raise
    finally:
        conexao.close()
    return obter_situacao(conta_id)


def registrar_pagamento_parcial(conta_id, valor_centavos, data_pagamento=None, saldo_esperado_centavos=None):
    """Registra um pagamento desta ocorrência (só dela). Quita a conta quando
    o pagamento completa o valor. Recusa (PagamentoError) sem gravar nada.
    Devolve a situação atualizada (`obter_situacao`)."""
    if not isinstance(valor_centavos, int) or isinstance(valor_centavos, bool) or valor_centavos <= 0:
        raise ValorDePagamentoInvalidoError()
    data_pagamento = data_pagamento or db.date.today().isoformat()
    if data_pagamento > db.date.today().isoformat():
        raise DataDePagamentoFuturaError()

    conexao = db.conectar()
    conexao.isolation_level = None
    try:
        cursor = conexao.cursor()
        cursor.execute("BEGIN IMMEDIATE;")
        linha = cursor.execute(
            f"SELECT status, valor, {db._sql_total_pago_centavos(cursor, 'c.id')} FROM contas c WHERE c.id = ?",
            (conta_id,),
        ).fetchone()
        if linha is None:
            raise ContaNaoEncontradaError()
        status, valor, pago_centavos = linha
        if status == "pago":
            raise ContaJaPagaError()
        saldo = db.centavos_de(valor) - pago_centavos
        if saldo_esperado_centavos is not None and saldo != saldo_esperado_centavos:
            raise SaldoDesatualizadoError()
        if valor_centavos > saldo:
            raise PagamentoAcimaDoSaldoError(saldo)
        cursor.execute(
            f"INSERT INTO {db.TABELA_PAGAMENTOS} (conta_id, valor_centavos, data_pagamento, tipo, registrado_em) "
            "VALUES (?, ?, ?, ?, ?)",
            (conta_id, valor_centavos, data_pagamento,
             "integral" if pago_centavos == 0 and valor_centavos == saldo else "parcial",
             datetime.now().isoformat(timespec="seconds")),
        )
        if valor_centavos == saldo:
            cursor.execute(
                "UPDATE contas SET status = 'pago', data_pagamento = "
                f"(SELECT data_pagamento FROM {db.TABELA_PAGAMENTOS} WHERE conta_id = ? AND estornado_em IS NULL "
                "ORDER BY id DESC LIMIT 1) WHERE id = ?",
                (conta_id, conta_id),
            )
        cursor.execute("COMMIT;")
    except BaseException:
        db._reverter_transacao(conexao)
        raise
    finally:
        conexao.close()
    return obter_situacao(conta_id)


def tem_pagamentos(conta_id):
    conexao = db.conectar()
    try:
        return bool(db._contas_com_pagamentos(conexao.cursor(), "id = ?", (conta_id,)))
    finally:
        conexao.close()



def _pagamento_ativo(cursor, pagamento_id, esperado):
    """(conta_id, valor da conta em centavos, soma dos ATIVOS) do pagamento, se
    ele ainda está ativo e igual ao que a tela mostrava (`esperado` = valor em
    centavos e data); senão PagamentoDesatualizadoError."""
    linha = cursor.execute(
        f"SELECT conta_id, valor_centavos, data_pagamento, estornado_em FROM {db.TABELA_PAGAMENTOS} WHERE id = ?",
        (pagamento_id,),
    ).fetchone()
    if linha is None or linha[3] is not None or (linha[1], linha[2]) != tuple(esperado):
        raise PagamentoDesatualizadoError()
    conta_id = linha[0]
    valor, pago = cursor.execute(
        f"SELECT c.valor, {db._sql_total_pago_centavos(cursor, 'c.id')} FROM contas c WHERE c.id = ?", (conta_id,),
    ).fetchone()
    return conta_id, db.centavos_de(valor), pago


def editar_pagamento(pagamento_id, valor_centavos, data_pagamento, esperado):
    """Corrige valor e data de UM pagamento ativo, no próprio registro (sem
    guardar versões anteriores). A soma dos ativos não pode passar do valor da
    conta. Status e data de quitação são recalculados pelos pagamentos ativos.
    Devolve a situação atualizada da conta."""
    if not isinstance(valor_centavos, int) or isinstance(valor_centavos, bool) or valor_centavos <= 0:
        raise ValorDePagamentoInvalidoError()
    if not data_pagamento or data_pagamento > db.date.today().isoformat():
        raise DataDePagamentoFuturaError()
    conexao = db.conectar()
    conexao.isolation_level = None
    try:
        cursor = conexao.cursor()
        cursor.execute("BEGIN IMMEDIATE;")
        conta_id, valor_conta, pago = _pagamento_ativo(cursor, pagamento_id, esperado)
        limite = valor_conta - (pago - esperado[0])
        if valor_centavos > limite:
            raise PagamentosAcimaDoValorError(limite)
        cursor.execute(f"UPDATE {db.TABELA_PAGAMENTOS} SET valor_centavos = ?, data_pagamento = ? WHERE id = ?",
                       (valor_centavos, data_pagamento, pagamento_id))
        db._sincronizar_quitacao(cursor, "id = ?", (conta_id,))
        cursor.execute("COMMIT;")
    except BaseException:
        db._reverter_transacao(conexao)
        raise
    finally:
        conexao.close()
    return obter_situacao(conta_id)


def estornar_pagamento(pagamento_id, esperado):
    """Desfaz UM pagamento ativo (conta paga ou parcialmente paga): o registro
    fica no histórico com a data do estorno e deixa de contar. A conta passa a
    pendente (Pendente/Atrasada pelo vencimento) se ficar com saldo. Um pagamento
    já estornado, ou diferente do que a tela mostrava, não é tocado
    (PagamentoDesatualizadoError). Devolve a situação atualizada da conta."""
    conexao = db.conectar()
    conexao.isolation_level = None
    try:
        cursor = conexao.cursor()
        cursor.execute("BEGIN IMMEDIATE;")
        conta_id, _, _ = _pagamento_ativo(cursor, pagamento_id, esperado)
        cursor.execute(f"UPDATE {db.TABELA_PAGAMENTOS} SET estornado_em = ? WHERE id = ? AND estornado_em IS NULL",
                       (db.date.today().isoformat(), pagamento_id))
        if cursor.rowcount != 1:
            raise PagamentoDesatualizadoError()
        # Sem pagamentos ativos restantes, a quitação (que dependia deles) é desfeita.
        cursor.execute(
            f"UPDATE contas SET status = 'pendente', data_pagamento = NULL WHERE id = ? AND NOT EXISTS "
            f"(SELECT 1 FROM {db.TABELA_PAGAMENTOS} p WHERE p.conta_id = contas.id AND p.estornado_em IS NULL)",
            (conta_id,),
        )
        db._sincronizar_quitacao(cursor, "id = ?", (conta_id,))
        cursor.execute("COMMIT;")
    except BaseException:
        db._reverter_transacao(conexao)
        raise
    finally:
        conexao.close()
    return obter_situacao(conta_id)


def excluir_estornado(pagamento_id, conta_id):
    """Etapa 3: exclui DEFINITIVAMENTE um registro ESTORNADO da conta `conta_id`.
    Simplificação (etapa 1, 28/10): o registro deixa de existir também para as
    proteções de recorrência -- sem marca de histórico; se não restar nenhum
    registro (ativo ou estornado), a ocorrência volta a ser tratada como sem
    pagamentos. Pagamentos ativos, total pago, saldo, status e quitação não
    mudam (o registro já não contava). Ativo, de outra conta ou inexistente:
    RegistroEstornadoIndisponivelError e nada é gravado. Devolve a situação
    atualizada da conta."""
    conexao = db.conectar()
    conexao.isolation_level = None
    try:
        cursor = conexao.cursor()
        cursor.execute("BEGIN IMMEDIATE;")
        condicao = "id = ? AND conta_id = ? AND estornado_em IS NOT NULL"
        if cursor.execute(f"SELECT 1 FROM {db.TABELA_PAGAMENTOS} WHERE {condicao}",
                          (pagamento_id, conta_id)).fetchone() is None:
            raise RegistroEstornadoIndisponivelError()
        cursor.execute(f"DELETE FROM {db.TABELA_PAGAMENTOS} WHERE {condicao}", (pagamento_id, conta_id))
        if cursor.rowcount != 1:
            raise RegistroEstornadoIndisponivelError()
        cursor.execute("COMMIT;")
    except BaseException:
        db._reverter_transacao(conexao)
        raise
    finally:
        conexao.close()
    return obter_situacao(conta_id)
