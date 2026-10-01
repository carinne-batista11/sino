"""
database.py — Camada de banco de dados do Sino (v2)
"""

import sqlite3
import hashlib
import os
import secrets
from datetime import date, datetime, timedelta
from calendar import monthrange

from limites import (  # noqa: F401 -- reexportados para a interface (database.*)
    LIMITE_DESCRICAO,
    LIMITE_NOME_CATEGORIA,
    LIMITE_NOME_CONTA,
    LIMITE_NOME_USUARIO,
    LimiteDeCaracteresError,
    contar_caracteres,
    normalizar_descricao,
    validar_limite,
)

NOME_DO_BANCO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sino.db")
PASTA_BACKUPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")


def conectar():
    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.execute("PRAGMA foreign_keys = ON;")
    return conexao


def criar_tabelas():
    """
    Cria o schema atual (v7: ERS v6.0, 9.2, mais a posição lógica das
    ocorrências da Etapa 2b) em um banco novo. Em um banco que já existe,
    `CREATE TABLE IF NOT EXISTS` não acrescenta colunas; por isso os índices
    de e-mail e de posição e o `user_version` só são gravados quando
    `usuarios` nasce nesta chamada. Um banco v5/v6 existente permanece
    intocado até `migrar_schema_v6()`/`migrar_schema_v7()` (com backup).

    Tudo roda em uma única transação (em modo legado, o sqlite3 do Python
    faria autocommit de cada DDL): um banco novo nunca fica com as tabelas
    criadas e sem o índice/`user_version`. `BEGIN` diferido: sobre um banco
    existente, os `IF NOT EXISTS` só leem o schema e nada é gravado.
    """
    conexao = conectar()
    conexao.isolation_level = None  # DDL em uma única transação explícita
    try:
        cursor = conexao.cursor()
        cursor.execute("BEGIN;")
        banco_novo = not _tabela_existe(cursor, "usuarios")
        _criar_tabelas_v6(cursor, banco_novo)
        cursor.execute("COMMIT;")
    except BaseException:
        _reverter_transacao(conexao)
        raise
    finally:
        conexao.close()


def _reverter_transacao(conexao):
    """ROLLBACK que nunca mascara a exceção original; close() descarta o resto."""
    if conexao.in_transaction:
        try:
            conexao.execute("ROLLBACK;")
        except sqlite3.Error:
            pass


def _criar_tabelas_v6(cursor, banco_novo):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            termos_aceitos_em TEXT NOT NULL,
            email_verificado INTEGER NOT NULL DEFAULT 0 CHECK (email_verificado IN (0, 1)),
            tema TEXT NOT NULL DEFAULT 'claro' CHECK (tema IN ('claro', 'escuro'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            icone TEXT,
            cor TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS series_recorrencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            valor REAL NOT NULL,
            categoria_id INTEGER,
            frequencia TEXT NOT NULL,
            dia_ancora INTEGER NOT NULL,
            mes_ancora INTEGER,
            data_inicio TEXT NOT NULL,
            data_termino TEXT,
            ativa INTEGER NOT NULL DEFAULT 1,
            horizonte_gerado_ate TEXT NOT NULL,
            descricao TEXT,
            posicao_ancora INTEGER,

            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (categoria_id) REFERENCES categorias(id),

            CHECK (frequencia IN ('mensal', 'anual')),
            CHECK (ativa IN (0, 1))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            categoria_id INTEGER,
            serie_id INTEGER,
            nome TEXT NOT NULL,
            valor REAL NOT NULL,
            data_vencimento TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendente',
            data_pagamento TEXT,
            editado_individualmente INTEGER NOT NULL DEFAULT 0,
            descricao TEXT,
            posicao INTEGER,
            data_prevista TEXT,

            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (categoria_id) REFERENCES categorias(id),
            FOREIGN KEY (serie_id) REFERENCES series_recorrencia(id),

            CHECK (status IN ('pago', 'pendente')),
            CHECK (editado_individualmente IN (0, 1))
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contas_usuario ON contas(usuario_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contas_categoria ON contas(categoria_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contas_vencimento ON contas(data_vencimento);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contas_serie ON contas(serie_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_series_usuario ON series_recorrencia(usuario_id);")

    if banco_novo:
        cursor.execute(f"CREATE UNIQUE INDEX {INDICE_EMAIL_CI} ON usuarios(lower(email));")
        cursor.execute(f"CREATE UNIQUE INDEX {INDICE_POSICAO} ON contas(serie_id, posicao);")
        cursor.execute(f"PRAGMA user_version = {VERSAO_SCHEMA_ATUAL};")


def criar_backup(caminho_banco=None, rotulo="v5"):
    """
    Copia o banco para database/backups/ com timestamp no nome, antes de
    qualquer migração de schema. Usa a API de backup do SQLite (cópia
    consistente página a página, mesmo com outra conexão aberta) e nunca
    sobrescreve um backup anterior do mesmo segundo. Retorna o caminho do
    backup criado, ou None se o arquivo do banco ainda não existir.

    `rotulo` entra no nome do arquivo (`sino_pre_migracao_<rotulo>_...`);
    o padrão "v5" mantém o nome usado por `migrar_schema_v5()`.
    """
    caminho_banco = caminho_banco or NOME_DO_BANCO
    if not os.path.exists(caminho_banco):
        return None
    os.makedirs(PASTA_BACKUPS, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(PASTA_BACKUPS, f"sino_pre_migracao_{rotulo}_{timestamp}")
    caminho_backup = f"{base}.db"
    sufixo = 1
    while os.path.exists(caminho_backup):
        caminho_backup = f"{base}_{sufixo}.db"
        sufixo += 1

    try:
        origem = sqlite3.connect(caminho_banco)
        try:
            destino = sqlite3.connect(caminho_backup)
            try:
                origem.backup(destino)
            finally:
                destino.close()
        finally:
            origem.close()
    except BaseException:
        if os.path.exists(caminho_backup):
            os.remove(caminho_backup)  # nunca deixar um backup incompleto no disco
        raise
    return caminho_backup


def _tabela_existe(cursor, nome_tabela):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (nome_tabela,),
    )
    return cursor.fetchone() is not None


def _coluna_existe(cursor, nome_tabela, nome_coluna):
    cursor.execute(f"PRAGMA table_info({nome_tabela})")
    return any(linha[1] == nome_coluna for linha in cursor.fetchall())


def migrar_schema_v5(caminho_banco=None):
    """
    Migração de schema do modelo v4.1 para a ERS v5.0 (seções 9.2 e 9.5).

    Idempotente: se `series_recorrencia` já existir, não faz nada e retorna
    {"executado": False, "motivo": "já migrado"}.

    Passos:
      1. Backup do banco atual (criar_backup) antes de qualquer alteração.
      2. Adiciona `categorias.cor` (aditivo).
      3. Cria `series_recorrencia`, uma linha por `serie_id` distinto hoje
         existente em `contas`, usando a ocorrência-âncora (id == serie_id)
         como fonte do nome/valor/categoria-modelo e da âncora (dia,
         data_inicio); frequência fixada em 'mensal' (única existente hoje);
         `data_termino` copiado de `repetir_ate`; `horizonte_gerado_ate` =
         maior data_vencimento já gerada para aquela série.
      4. Recria `contas` (via tabela auxiliar `contas_novo`, porque SQLite
         não permite alterar o alvo de uma FOREIGN KEY nem remover colunas
         acopladas a CHECK via ALTER TABLE): sem `conta_fixa`/`repetir_ate`,
         com `data_pagamento` e `editado_individualmente` (ambos nascem
         nulos/0 — RNF08, ERS 9.5.3), `serie_id` apontando para
         `series_recorrencia`. Todo id, nome, valor, data_vencimento e
         status são copiados literalmente — nenhum dado de negócio muda.

    Roda inteira dentro de uma transação: qualquer falha reverte (ROLLBACK)
    e nada fica em estado parcial. O backup do passo 1 permanece no disco
    independente de sucesso ou falha.
    """
    caminho_banco = caminho_banco or NOME_DO_BANCO

    conexao = sqlite3.connect(caminho_banco)
    conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
    conexao.execute("PRAGMA foreign_keys = OFF;")
    cursor = conexao.cursor()

    if _tabela_existe(cursor, "series_recorrencia"):
        conexao.close()
        return {"executado": False, "motivo": "já migrado", "backup": None}

    caminho_backup = criar_backup(caminho_banco)
    mapa_serie_antiga_para_nova = {}
    linhas_antigas = []
    try:
        cursor.execute("BEGIN;")

        if not _coluna_existe(cursor, "categorias", "cor"):
            cursor.execute("ALTER TABLE categorias ADD COLUMN cor TEXT;")

        cursor.execute("""
            CREATE TABLE series_recorrencia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                valor REAL NOT NULL,
                categoria_id INTEGER,
                frequencia TEXT NOT NULL,
                dia_ancora INTEGER NOT NULL,
                mes_ancora INTEGER,
                data_inicio TEXT NOT NULL,
                data_termino TEXT,
                ativa INTEGER NOT NULL DEFAULT 1,
                horizonte_gerado_ate TEXT NOT NULL,

                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (categoria_id) REFERENCES categorias(id),

                CHECK (frequencia IN ('mensal', 'anual')),
                CHECK (ativa IN (0, 1))
            );
        """)

        cursor.execute("SELECT DISTINCT serie_id FROM contas WHERE serie_id IS NOT NULL;")
        series_antigas = [linha[0] for linha in cursor.fetchall()]

        for serie_id_antigo in series_antigas:
            cursor.execute(
                """
                SELECT usuario_id, categoria_id, nome, valor, data_vencimento, repetir_ate
                FROM contas WHERE id = ?
                """,
                (serie_id_antigo,),
            )
            ancora = cursor.fetchone()
            if ancora is None:
                raise RuntimeError(
                    f"serie_id={serie_id_antigo} não corresponde a nenhuma ocorrência-âncora "
                    "(id == serie_id) — dado pré-existente inconsistente, migração abortada."
                )
            usuario_id, categoria_id, nome, valor, data_vencimento, repetir_ate = ancora
            ano, mes, dia = map(int, data_vencimento.split("-"))

            cursor.execute(
                "SELECT MAX(data_vencimento) FROM contas WHERE serie_id = ?",
                (serie_id_antigo,),
            )
            horizonte_gerado_ate = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO series_recorrencia
                    (usuario_id, nome, valor, categoria_id, frequencia,
                     dia_ancora, mes_ancora, data_inicio, data_termino,
                     ativa, horizonte_gerado_ate)
                VALUES (?, ?, ?, ?, 'mensal', ?, NULL, ?, ?, 1, ?)
                """,
                (usuario_id, nome, valor, categoria_id, dia,
                 data_vencimento, repetir_ate, horizonte_gerado_ate),
            )
            mapa_serie_antiga_para_nova[serie_id_antigo] = cursor.lastrowid

        cursor.execute("""
            CREATE TABLE contas_novo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                categoria_id INTEGER,
                serie_id INTEGER,
                nome TEXT NOT NULL,
                valor REAL NOT NULL,
                data_vencimento TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente',
                data_pagamento TEXT,
                editado_individualmente INTEGER NOT NULL DEFAULT 0,

                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (categoria_id) REFERENCES categorias(id),
                FOREIGN KEY (serie_id) REFERENCES series_recorrencia(id),

                CHECK (status IN ('pago', 'pendente')),
                CHECK (editado_individualmente IN (0, 1))
            );
        """)

        cursor.execute("""
            SELECT id, usuario_id, categoria_id, serie_id, nome, valor,
                   data_vencimento, status
            FROM contas;
        """)
        linhas_antigas = cursor.fetchall()

        for (id_, usuario_id, categoria_id, serie_id_antigo, nome, valor,
             data_vencimento, status) in linhas_antigas:
            serie_id_novo = (
                mapa_serie_antiga_para_nova.get(serie_id_antigo)
                if serie_id_antigo is not None else None
            )
            cursor.execute(
                """
                INSERT INTO contas_novo
                    (id, usuario_id, categoria_id, serie_id, nome, valor,
                     data_vencimento, status, data_pagamento, editado_individualmente)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 0)
                """,
                (id_, usuario_id, categoria_id, serie_id_novo, nome, valor,
                 data_vencimento, status),
            )

        cursor.execute("DROP TABLE contas;")
        cursor.execute("ALTER TABLE contas_novo RENAME TO contas;")

        cursor.execute("CREATE INDEX idx_contas_usuario ON contas(usuario_id);")
        cursor.execute("CREATE INDEX idx_contas_categoria ON contas(categoria_id);")
        cursor.execute("CREATE INDEX idx_contas_vencimento ON contas(data_vencimento);")
        cursor.execute("CREATE INDEX idx_contas_serie ON contas(serie_id);")
        cursor.execute("CREATE INDEX idx_series_usuario ON series_recorrencia(usuario_id);")

        cursor.execute("COMMIT;")
    except Exception:
        cursor.execute("ROLLBACK;")
        raise
    finally:
        conexao.execute("PRAGMA foreign_keys = ON;")
        conexao.close()

    return {
        "executado": True,
        "backup": caminho_backup,
        "series_migradas": len(mapa_serie_antiga_para_nova),
        "contas_migradas": len(linhas_antigas),
    }


def validar_migracao_v5(caminho_banco=None):
    """
    Checagens de integridade pós-migração (contagens, FKs órfãs, presença
    das colunas novas e ausência das antigas). Retorna um dicionário com
    os resultados e uma chave "ok" resumindo se tudo passou; não levanta
    exceção por si só — quem chama decide o que fazer com falhas.
    """
    caminho_banco = caminho_banco or NOME_DO_BANCO
    conexao = sqlite3.connect(caminho_banco)
    conexao.execute("PRAGMA foreign_keys = ON;")
    cursor = conexao.cursor()

    resultado = {}

    cursor.execute("SELECT COUNT(*) FROM contas;")
    resultado["total_contas"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM series_recorrencia;")
    resultado["total_series"] = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(valor) FROM contas;")
    resultado["soma_valor_contas"] = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*) FROM contas
        WHERE serie_id IS NOT NULL
              AND serie_id NOT IN (SELECT id FROM series_recorrencia);
        """
    )
    resultado["series_id_orfaos"] = cursor.fetchone()[0]

    cursor.execute("PRAGMA foreign_key_check(contas);")
    resultado["violacoes_fk_contas"] = cursor.fetchall()

    cursor.execute("PRAGMA foreign_key_check(series_recorrencia);")
    resultado["violacoes_fk_series"] = cursor.fetchall()

    for coluna in ("conta_fixa", "repetir_ate"):
        resultado[f"contas_ainda_tem_{coluna}"] = _coluna_existe(cursor, "contas", coluna)

    for coluna in ("data_pagamento", "editado_individualmente"):
        resultado[f"contas_tem_{coluna}"] = _coluna_existe(cursor, "contas", coluna)

    resultado["categorias_tem_cor"] = _coluna_existe(cursor, "categorias", "cor")

    conexao.close()

    resultado["ok"] = (
        resultado["series_id_orfaos"] == 0
        and not resultado["violacoes_fk_contas"]
        and not resultado["violacoes_fk_series"]
        and not resultado["contas_ainda_tem_conta_fixa"]
        and not resultado["contas_ainda_tem_repetir_ate"]
        and resultado["contas_tem_data_pagamento"]
        and resultado["contas_tem_editado_individualmente"]
        and resultado["categorias_tem_cor"]
    )
    return resultado


# ERS v6.0, 9.2: alterações aditivas de schema. Cada item é detectado
# individualmente, para que a migração complete estados parciais e possa
# ser executada repetidas vezes. Cada coluna leva a definição usada no
# ALTER TABLE e o que `PRAGMA table_info` deve devolver para ela
# (tipo, notnull, default) -- uma coluna homônima com outra definição não
# é aceita como "já migrada".
VERSAO_SCHEMA_V6 = 6
INDICE_EMAIL_CI = "idx_usuarios_email_ci"
COLUNAS_V6 = (
    ("contas", "descricao", "TEXT", ("TEXT", 0, None)),
    ("series_recorrencia", "descricao", "TEXT", ("TEXT", 0, None)),
    ("usuarios", "email_verificado",
     "INTEGER NOT NULL DEFAULT 0 CHECK (email_verificado IN (0, 1))", ("INTEGER", 1, "0")),
    ("usuarios", "tema",
     "TEXT NOT NULL DEFAULT 'claro' CHECK (tema IN ('claro', 'escuro'))", ("TEXT", 1, "'claro'")),
)
TABELAS_V5 = ("usuarios", "categorias", "series_recorrencia", "contas")
# Colunas do schema v5.0. Um banco só é tratado como v5 se cada tabela tiver
# exatamente estas colunas (mais as da v6 já presentes, em estado parcial);
# um schema anterior (ex.: v4.1, com `conta_fixa`/`repetir_ate`) ou
# desconhecido é recusado, nunca "migrado" só por não ser v6.
COLUNAS_V5 = {
    "usuarios": ("id", "nome", "email", "senha_hash", "termos_aceitos_em"),
    "categorias": ("id", "usuario_id", "nome", "icone", "cor"),
    "series_recorrencia": (
        "id", "usuario_id", "nome", "valor", "categoria_id", "frequencia", "dia_ancora",
        "mes_ancora", "data_inicio", "data_termino", "ativa", "horizonte_gerado_ate",
    ),
    "contas": (
        "id", "usuario_id", "categoria_id", "serie_id", "nome", "valor", "data_vencimento",
        "status", "data_pagamento", "editado_individualmente",
    ),
}
# Etapa 2b (v7): posição lógica das ocorrências de uma série, independente
# do vencimento real -- `contas.posicao` (escopo, parcela), `contas.data_prevista`
# (a vaga da grade que a ocorrência ocupa) e `series_recorrencia.posicao_ancora`
# (posição onde a grade atual foi ancorada). Mesmo formato de COLUNAS_V6.
VERSAO_SCHEMA_V7 = 7
VERSAO_SCHEMA_ATUAL = VERSAO_SCHEMA_V7
INDICE_POSICAO = "idx_contas_serie_posicao"
COLUNAS_V7 = (
    ("contas", "posicao", "INTEGER", ("INTEGER", 0, None)),
    ("contas", "data_prevista", "TEXT", ("TEXT", 0, None)),
    ("series_recorrencia", "posicao_ancora", "INTEGER", ("INTEGER", 0, None)),
)
# user_version que esta versão do app sabe tratar: 0 (bancos anteriores ao
# controle de versão, validados estruturalmente como v5), 6 e 7.
VERSOES_SUPORTADAS = (0, VERSAO_SCHEMA_V6, VERSAO_SCHEMA_V7)


class ColisaoDeEmailError(RuntimeError):
    """
    Há e-mails que só diferem em maiúsculas/minúsculas, o que impede o
    índice UNIQUE por lower(email). `grupos_ids` lista os ids de cada grupo
    em colisão; nenhum e-mail aparece na mensagem nem é modificado.
    """

    def __init__(self, grupos_ids):
        self.grupos_ids = grupos_ids
        descricao = "; ".join(", ".join(str(i) for i in grupo) for grupo in grupos_ids)
        super().__init__(
            "Migração v6 abortada: e-mails que colidem sem diferenciar maiúsculas "
            f"de minúsculas (ids de usuários por grupo: {descricao}). Nenhuma alteração foi feita."
        )


class SchemaV6IncompativelError(RuntimeError):
    """
    Já existe um objeto com o nome de um item da v6 (coluna ou índice), mas
    com definição diferente da esperada. A migração não o aceita como
    migrado nem o substitui: `problemas` descreve cada divergência, e a
    correção fica a cargo de uma intervenção manual.
    """

    def __init__(self, problemas):
        self.problemas = problemas
        super().__init__(
            "Migração v6 abortada: schema incompatível ("
            + "; ".join(problemas)
            + "). Nenhuma alteração foi feita."
        )


class SchemaV7IncompativelError(RuntimeError):
    """
    O banco não está no estado que a migração v7 aceita: item da v7 com
    definição diferente, itens da v7 presentes num banco ainda marcado
    como v6 (estado parcial desconhecido) ou v6 incompleto. Nada é alterado.
    """

    def __init__(self, problemas):
        self.problemas = problemas
        super().__init__(
            "Migração v7 abortada: schema incompatível ("
            + "; ".join(problemas)
            + "). Nenhuma alteração foi feita."
        )


class VagasNaoInferiveisError(RuntimeError):
    """
    D3 (Etapa 2b): há ocorrências editadas individualmente cuja vaga
    original na série não pode ser reconstruída com segurança a partir dos
    dados v6. A migração v7 é recusada antes de qualquer escrita e sem
    backup. `diagnostico` lista (conta_id, serie_id, motivo), sem dados
    pessoais.
    """

    def __init__(self, diagnostico):
        self.diagnostico = diagnostico
        itens = "; ".join(f"conta {c} (série {s}): {m}" for c, s, m in diagnostico)
        super().__init__(
            "Migração v7 recusada: vaga não inferível para "
            f"{len(diagnostico)} ocorrência(s) editada(s) -- {itens}. Nenhuma alteração foi feita."
        )


class VersaoDeBancoNaoSuportadaError(RuntimeError):
    """
    `PRAGMA user_version` fora de VERSOES_SUPORTADAS -- em especial, um banco
    de uma versão mais nova do Sino. Detectado antes de qualquer escrita:
    nada é migrado, alterado ou copiado para backup.
    """

    def __init__(self, versao):
        self.versao = versao
        origem = "de uma versão mais nova do Sino" if versao > VERSAO_SCHEMA_ATUAL else "desconhecida"
        super().__init__(
            f"Banco com user_version = {versao} ({origem}); esta versão do Sino só abre "
            f"bancos com user_version {' ou '.join(map(str, VERSOES_SUPORTADAS))}. "
            "Nenhuma alteração foi feita."
        )


def _exigir_versao_suportada(cursor):
    cursor.execute("PRAGMA user_version")
    versao = cursor.fetchone()[0]
    if versao not in VERSOES_SUPORTADAS:
        raise VersaoDeBancoNaoSuportadaError(versao)
    return versao


def _divergencias_schema_v5(cursor):
    """Tabelas cujas colunas não são exatamente as da v5 (+ as da v6/v7 já presentes)."""
    problemas = []
    for tabela, colunas_v5 in COLUNAS_V5.items():
        cursor.execute(f"PRAGMA table_info({tabela})")
        existentes = {linha[1] for linha in cursor.fetchall()}
        colunas_v6 = {coluna for t, coluna, _, _ in COLUNAS_V6 + COLUNAS_V7 if t == tabela}
        faltando = [c for c in colunas_v5 if c not in existentes]
        desconhecidas = sorted(existentes - set(colunas_v5) - colunas_v6)
        if faltando or desconhecidas:
            problemas.append(
                f"tabela {tabela} fora do schema v5 (faltando: {', '.join(faltando) or '-'}; "
                f"desconhecidas: {', '.join(desconhecidas) or '-'})"
            )
    return problemas


def _estado_coluna_v6(cursor, tabela, coluna, esperado):
    """'ausente', 'valida' ou 'incompativel', pela definição em `PRAGMA table_info`."""
    cursor.execute(f"PRAGMA table_info({tabela})")
    for _, nome, tipo, notnull, default, _pk in cursor.fetchall():
        if nome == coluna:
            return "valida" if (tipo.upper(), notnull, default) == esperado else "incompativel"
    return "ausente"


def _estado_indice_email_ci(cursor):
    """
    'ausente', 'valido' ou 'incompativel'. Válido = índice UNIQUE, não
    parcial, da tabela `usuarios`, com uma única chave, que é uma expressão
    com colação BINARY, e que o planejador do SQLite reconhece como a
    expressão lower(email): com `INDEXED BY`, a consulta
    `WHERE lower(email) = ?` precisa ser uma busca (SEARCH) nesse índice. A
    comparação é feita pelo próprio SQLite sobre a árvore da expressão, sem
    depender da formatação do `CREATE INDEX` (espaços, maiúsculas etc.).
    """
    cursor.execute("SELECT type, tbl_name FROM sqlite_master WHERE name = ?", (INDICE_EMAIL_CI,))
    objeto = cursor.fetchone()
    if objeto is None:
        return "ausente"
    if objeto != ("index", "usuarios"):
        return "incompativel"

    cursor.execute("PRAGMA index_list(usuarios)")
    # (seq, name, unique, origin, partial)
    info = next((linha for linha in cursor.fetchall() if linha[1] == INDICE_EMAIL_CI), None)
    if info is None or info[2] != 1 or info[4] != 0:
        return "incompativel"

    cursor.execute(f"PRAGMA index_xinfo({INDICE_EMAIL_CI})")
    # (seqno, cid, name, desc, coll, key); cid -2 = expressão
    chaves = [linha for linha in cursor.fetchall() if linha[5] == 1]
    if len(chaves) != 1 or chaves[0][1] != -2 or chaves[0][4] != "BINARY":
        return "incompativel"

    try:
        cursor.execute(
            f"EXPLAIN QUERY PLAN SELECT id FROM usuarios INDEXED BY {INDICE_EMAIL_CI} "
            "WHERE lower(email) = ?",
            ("",),
        )
        plano = [linha[3] for linha in cursor.fetchall()]
    except sqlite3.OperationalError:  # "no query solution": o índice não serve à consulta
        return "incompativel"
    busca_no_indice = any(
        detalhe.startswith("SEARCH") and INDICE_EMAIL_CI in detalhe for detalhe in plano
    )
    return "valido" if busca_no_indice else "incompativel"


def _colisoes_de_email(cursor):
    cursor.execute(
        """
        SELECT GROUP_CONCAT(id) FROM usuarios
        GROUP BY lower(email) HAVING COUNT(*) > 1
        """
    )
    return sorted(sorted(int(i) for i in linha[0].split(",")) for linha in cursor.fetchall())


def _contagens(cursor):
    contagens = {}
    for tabela in TABELAS_V5:
        cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
        contagens[tabela] = cursor.fetchone()[0]
    return contagens


def _verificar_schema_v6(cursor):
    resultado = {}
    for tabela, coluna, _, esperado in COLUNAS_V6:
        resultado[f"{tabela}.{coluna}"] = _estado_coluna_v6(cursor, tabela, coluna, esperado)

    resultado["indice_email_ci"] = _estado_indice_email_ci(cursor)

    cursor.execute("PRAGMA user_version")
    resultado["user_version"] = cursor.fetchone()[0]

    cursor.execute("PRAGMA integrity_check")
    resultado["integridade"] = [linha[0] for linha in cursor.fetchall()]

    cursor.execute("PRAGMA foreign_key_check")
    resultado["violacoes_fk"] = cursor.fetchall()

    resultado["ok"] = (
        all(resultado[f"{tabela}.{coluna}"] == "valida" for tabela, coluna, _, _ in COLUNAS_V6)
        and resultado["indice_email_ci"] == "valido"
        and resultado["user_version"] in (VERSAO_SCHEMA_V6, VERSAO_SCHEMA_V7)
        and resultado["integridade"] == ["ok"]
        and not resultado["violacoes_fk"]
    )
    return resultado


def _verificar_integridade_backup(caminho_backup):
    try:
        conexao = sqlite3.connect(caminho_backup)
        try:
            return conexao.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        finally:
            conexao.close()
    except sqlite3.DatabaseError:  # inclui "file is not a database"
        return False


def migrar_schema_v6(caminho_banco=None):
    """
    Migração de schema da v5.0 para a ERS v6.0 (seção 9.2). Totalmente
    aditiva: nenhuma tabela é recriada e nenhum dado existente é alterado
    (RNF08). `categoria_id = NULL` continua representando "Sem categoria".

      * `contas.descricao` e `series_recorrencia.descricao` (TEXT, NULL);
      * `usuarios.email_verificado` (0/1, padrão 0) e `usuarios.tema`
        ('claro'/'escuro', padrão 'claro');
      * índice UNIQUE `idx_usuarios_email_ci` em lower(email);
      * `PRAGMA user_version = 6`.

    Cada item é detectado individualmente: o que já existe com a definição
    esperada é mantido e só o que falta é aplicado. Sem pendências, retorna
    {"executado": False, "motivo": "já migrado"} sem criar backup. Um item
    homônimo com definição diferente aborta com `SchemaV6IncompativelError`
    (também quando todo o resto já estiver migrado).

    Ordem, tudo dentro de `BEGIN IMMEDIATE` (nenhuma outra conexão grava a
    partir daqui):
      1. checagens sem escrita: `user_version` suportada
         (`VersaoDeBancoNaoSuportadaError`), quatro tabelas com exatamente as
         colunas da v5, itens da v6 incompatíveis (`SchemaV6IncompativelError`)
         e colisões de e-mail sob lower(email) (`ColisaoDeEmailError`) --
         falhas aqui abortam sem backup e sem alteração;
      2. backup consistente, lido por outra conexão, com `integrity_check`;
      3. alterações, com `user_version` por último;
      4. validação de schema, integridade, FKs e contagens;
      5. COMMIT -- o único ponto em que qualquer alteração, inclusive o
         `user_version`, se torna visível.
    Qualquer falha reverte tudo (ROLLBACK) e a conexão é sempre fechada; o
    backup, se já tiver sido criado, permanece no disco.
    """
    caminho_banco = caminho_banco or NOME_DO_BANCO
    if not os.path.exists(caminho_banco):
        raise FileNotFoundError(f"Banco não encontrado: {caminho_banco}")

    conexao = sqlite3.connect(caminho_banco)
    caminho_backup = None
    try:
        conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
        cursor = conexao.cursor()
        cursor.execute("BEGIN IMMEDIATE;")

        versao = _exigir_versao_suportada(cursor)

        tabelas_ausentes = [t for t in TABELAS_V5 if not _tabela_existe(cursor, t)]
        if tabelas_ausentes:
            raise RuntimeError(
                f"Schema v5 incompleto (tabelas ausentes: {', '.join(tabelas_ausentes)}); "
                "migração v6 abortada."
            )

        problemas = _divergencias_schema_v5(cursor)
        colunas_pendentes = []
        for tabela, coluna, definicao, esperado in COLUNAS_V6:
            estado = _estado_coluna_v6(cursor, tabela, coluna, esperado)
            if estado == "ausente":
                colunas_pendentes.append((tabela, coluna, definicao))
            elif estado == "incompativel":
                problemas.append(f"coluna {tabela}.{coluna} com definição diferente da esperada")
        estado_indice = _estado_indice_email_ci(cursor)
        if estado_indice == "incompativel":
            problemas.append(f"objeto {INDICE_EMAIL_CI} diferente do índice UNIQUE em lower(email)")
        if problemas:
            raise SchemaV6IncompativelError(problemas)

        indice_pendente = estado_indice == "ausente"
        versao_pendente = versao < VERSAO_SCHEMA_V6

        if not (colunas_pendentes or indice_pendente or versao_pendente):
            cursor.execute("ROLLBACK;")
            return {"executado": False, "motivo": "já migrado", "backup": None}

        if indice_pendente:
            colisoes = _colisoes_de_email(cursor)
            if colisoes:
                raise ColisaoDeEmailError(colisoes)

        # Lido por outra conexão: o RESERVED lock deste BEGIN IMMEDIATE ainda
        # permite leitura e garante que nada muda entre o backup e as alterações.
        caminho_backup = criar_backup(caminho_banco, rotulo="v6")
        if not _verificar_integridade_backup(caminho_backup):
            raise RuntimeError(
                f"Backup pré-migração v6 falhou no integrity_check ({caminho_backup}); "
                "migração abortada."
            )

        contagens_antes = _contagens(cursor)

        for tabela, coluna, definicao in colunas_pendentes:
            cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao};")
        if indice_pendente:
            cursor.execute(f"CREATE UNIQUE INDEX {INDICE_EMAIL_CI} ON usuarios(lower(email));")
        if versao_pendente:
            cursor.execute(f"PRAGMA user_version = {VERSAO_SCHEMA_V6};")

        verificacao = _verificar_schema_v6(cursor)
        if not verificacao["ok"] or _contagens(cursor) != contagens_antes:
            raise RuntimeError("Validação pós-migração v6 falhou; alterações revertidas.")

        cursor.execute("COMMIT;")
    except BaseException:
        _reverter_transacao(conexao)
        raise
    finally:
        conexao.close()

    return {
        "executado": True,
        "backup": caminho_backup,
        "colunas_adicionadas": [f"{tabela}.{coluna}" for tabela, coluna, _ in colunas_pendentes],
        "indice_criado": indice_pendente,
        "versao_atualizada": versao_pendente,
    }


def validar_migracao_v6(caminho_banco=None):
    """
    Checagens pós-migração v6 (definição das colunas novas, índice UNIQUE
    por lower(email), user_version, integrity_check e FKs). Retorna um
    dicionário com os resultados e a chave "ok"; só consulta o banco e não
    cria o arquivo se ele não existir (FileNotFoundError).
    """
    caminho_banco = caminho_banco or NOME_DO_BANCO
    if not os.path.exists(caminho_banco):
        raise FileNotFoundError(f"Banco não encontrado: {caminho_banco}")
    conexao = sqlite3.connect(caminho_banco)
    try:
        return _verificar_schema_v6(conexao.cursor())
    finally:
        conexao.close()


class BancoNaoPreparadoError(RuntimeError):
    """
    O banco não passou na validação depois da preparação (ex.: integridade
    ou FKs com problema), ou um banco v6 não pôde seguir para a v7 por não
    estar íntegro. `validacao` guarda o resultado completo, que não contém
    dados pessoais.
    """

    def __init__(self, validacao):
        self.validacao = validacao
        v7 = "indice_posicao" in validacao
        colunas = COLUNAS_V6 + (COLUNAS_V7 if v7 else ())
        falhas = [f"{tabela}.{coluna}" for tabela, coluna, _, _ in colunas
                  if validacao.get(f"{tabela}.{coluna}") != "valida"]
        if validacao.get("indice_email_ci") != "valido":
            falhas.append("indice_email_ci")
        if v7 and validacao.get("indice_posicao") != "valido":
            falhas.append("indice_posicao")
        versoes_aceitas = (VERSAO_SCHEMA_ATUAL,) if v7 else (VERSAO_SCHEMA_V6, VERSAO_SCHEMA_V7)
        if validacao.get("user_version") not in versoes_aceitas:
            falhas.append("user_version")
        if validacao.get("integridade") != ["ok"]:
            falhas.append("integridade")
        if validacao.get("violacoes_fk"):
            falhas.append("violacoes_fk")
        for chave in ("ocorrencias_sem_posicao", "series_sem_posicao_ancora", "colunas_fora_do_schema"):
            if validacao.get(chave):
                falhas.append(chave)
        super().__init__(f"Banco não está pronto (itens com problema: {', '.join(falhas)}).")


def _estado_indice_posicao(cursor):
    """'ausente', 'valido' ou 'incompativel': UNIQUE, não parcial, em contas(serie_id, posicao)."""
    cursor.execute("SELECT type, tbl_name FROM sqlite_master WHERE name = ?", (INDICE_POSICAO,))
    objeto = cursor.fetchone()
    if objeto is None:
        return "ausente"
    if objeto != ("index", "contas"):
        return "incompativel"
    cursor.execute("PRAGMA index_list(contas)")
    info = next((linha for linha in cursor.fetchall() if linha[1] == INDICE_POSICAO), None)
    if info is None or info[2] != 1 or info[4] != 0:
        return "incompativel"
    cursor.execute(f"PRAGMA index_info({INDICE_POSICAO})")
    colunas = [linha[2] for linha in sorted(cursor.fetchall())]
    return "valido" if colunas == ["serie_id", "posicao"] else "incompativel"


def _verificar_schema_v7(cursor):
    """Checagens da v6 + colunas/índice da v7, posições preenchidas, nenhuma
    coluna fora do schema conhecido (M1) e user_version 7."""
    resultado = _verificar_schema_v6(cursor)
    resultado["colunas_fora_do_schema"] = _divergencias_schema_v5(cursor)
    for tabela, coluna, _, esperado in COLUNAS_V7:
        resultado[f"{tabela}.{coluna}"] = _estado_coluna_v6(cursor, tabela, coluna, esperado)
    resultado["indice_posicao"] = _estado_indice_posicao(cursor)
    colunas_v7_validas = all(resultado[f"{t}.{c}"] == "valida" for t, c, _, _ in COLUNAS_V7)
    if colunas_v7_validas:
        cursor.execute(
            "SELECT COUNT(*) FROM contas WHERE serie_id IS NOT NULL "
            "AND (posicao IS NULL OR data_prevista IS NULL)"
        )
        resultado["ocorrencias_sem_posicao"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM series_recorrencia WHERE posicao_ancora IS NULL")
        resultado["series_sem_posicao_ancora"] = cursor.fetchone()[0]
    resultado["ok"] = (
        resultado["ok"]
        and colunas_v7_validas
        and resultado["indice_posicao"] == "valido"
        and resultado["user_version"] == VERSAO_SCHEMA_V7
        and resultado.get("ocorrencias_sem_posicao") == 0
        and resultado.get("series_sem_posicao_ancora") == 0
        and not resultado["colunas_fora_do_schema"]
    )
    return resultado


def validar_schema_atual(caminho_banco=None):
    """
    Checagens do schema atual (v7): tudo o que `validar_migracao_v6()`
    verifica, mais as colunas e o índice da posição lógica, nenhuma
    ocorrência de série sem posição/vaga, nenhuma coluna fora do schema
    conhecido e `user_version = 7`. Só consulta
    o banco (FileNotFoundError se não existir).
    """
    caminho_banco = caminho_banco or NOME_DO_BANCO
    if not os.path.exists(caminho_banco):
        raise FileNotFoundError(f"Banco não encontrado: {caminho_banco}")
    conexao = sqlite3.connect(caminho_banco)
    try:
        return _verificar_schema_v7(conexao.cursor())
    finally:
        conexao.close()


def _classificar_vagas(cursor):
    """
    D3 (Etapa 2b): classifica, só lendo, a vaga de cada ocorrência de série
    para o preenchimento de `data_prevista`:

      * não editada individualmente -> EXATA: o vencimento dela só é
        gravado pela geração ou pela reorganização da série, que também
        definem a vaga;
      * editada, na competência de uma vaga da grade atual (de
        `data_inicio` até o horizonte) e sozinha nessa competência ->
        PROVÁVEL (a competência da vaga é a do vencimento);
      * qualquer outra editada -> NÃO INFERÍVEL.

    Retorna (ids_provaveis, diagnostico) -- diagnostico com
    (conta_id, serie_id, motivo) das não inferíveis.
    """
    provaveis, diagnostico = [], []
    cursor.execute(
        "SELECT id, frequencia, data_inicio, horizonte_gerado_ate FROM series_recorrencia ORDER BY id"
    )
    for serie_id, frequencia, inicio, horizonte in cursor.fetchall():
        if horizonte >= inicio:
            grade = {d[:7] for d in _gerar_datas_ocorrencias(frequencia, inicio, horizonte[:7])}
        else:
            grade = {inicio[:7]}
        cursor.execute(
            "SELECT id, data_vencimento, editado_individualmente FROM contas WHERE serie_id = ? ORDER BY id",
            (serie_id,),
        )
        ocorrencias = cursor.fetchall()
        por_competencia = {}
        for _, vencimento, _ in ocorrencias:
            por_competencia[vencimento[:7]] = por_competencia.get(vencimento[:7], 0) + 1
        for conta_id, vencimento, editado in ocorrencias:
            if not editado:
                continue
            if vencimento < inicio:
                diagnostico.append((conta_id, serie_id, "anterior à âncora atual (grade antiga desconhecida)"))
            elif vencimento[:7] not in grade:
                diagnostico.append((conta_id, serie_id, "fora das competências da grade atual"))
            elif por_competencia[vencimento[:7]] > 1:
                diagnostico.append((conta_id, serie_id, "competência compartilhada com outra ocorrência"))
            else:
                provaveis.append(conta_id)
    return provaveis, diagnostico


def _dados_v6(cursor):
    """Todas as linhas das quatro tabelas com as colunas v5+v6 (para provar RNF08)."""
    dados = {}
    for tabela, colunas in COLUNAS_V5.items():
        colunas = list(colunas) + [c for t, c, _, _ in COLUNAS_V6 if t == tabela]
        cursor.execute(f"SELECT {', '.join(colunas)} FROM {tabela} ORDER BY id")
        dados[tabela] = cursor.fetchall()
    return dados


def migrar_schema_v7(caminho_banco=None):
    """
    Migração v6 -> v7 (Etapa 2b): posição lógica das ocorrências. Aditiva
    (RNF08): nenhuma coluna existente é alterada.

      * `contas.posicao` e `contas.data_prevista`, preenchidas para cada
        série na ordem (vencimento, id), com `data_prevista = vencimento`;
      * `series_recorrencia.posicao_ancora = 1` (0 numa série sem
        ocorrências) -- seguro: a ordem do segmento é a mesma do preenchimento;
      * índice UNIQUE `idx_contas_serie_posicao`;
      * `PRAGMA user_version = 7`.

    Tudo dentro de `BEGIN IMMEDIATE`. Antes de qualquer escrita e sem
    backup, recusa: `user_version` não suportada ou anterior à 6
    (`SchemaV7IncompativelError` -- a v6 vem antes, por `migrar_schema_v6`),
    colunas fora do schema, itens v6 ausentes/incompatíveis, itens v7 já
    presentes num banco ainda v6 (estado parcial desconhecido), banco v6 que
    não passa na própria validação (`BancoNaoPreparadoError`) e ocorrências
    editadas cuja vaga não é inferível (`VagasNaoInferiveisError`, D3).
    Banco já v7 e íntegro: {"executado": False, "motivo": "já migrado"},
    sem backup. Depois: backup com integrity_check, alterações, validação
    (schema, posições, contagens e dados v6 idênticos) e COMMIT. Qualquer
    falha reverte tudo; o backup, se já criado, permanece no disco.

    Retorna {"executado": True, "backup": caminho, "ocorrencias_provaveis":
    [ids das editadas cuja vaga foi inferida pela competência]}.
    """
    caminho_banco = caminho_banco or NOME_DO_BANCO
    if not os.path.exists(caminho_banco):
        raise FileNotFoundError(f"Banco não encontrado: {caminho_banco}")

    conexao = sqlite3.connect(caminho_banco)
    caminho_backup = None
    try:
        conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
        cursor = conexao.cursor()
        cursor.execute("BEGIN IMMEDIATE;")

        versao = _exigir_versao_suportada(cursor)
        if versao < VERSAO_SCHEMA_V6:
            raise SchemaV7IncompativelError(
                [f"user_version {versao}: o banco precisa passar pela migração v6 antes da v7"]
            )
        tabelas_ausentes = [t for t in TABELAS_V5 if not _tabela_existe(cursor, t)]
        if tabelas_ausentes:
            raise SchemaV7IncompativelError([f"tabelas ausentes: {', '.join(tabelas_ausentes)}"])

        problemas = _divergencias_schema_v5(cursor)
        for tabela, coluna, _, esperado in COLUNAS_V6:
            if _estado_coluna_v6(cursor, tabela, coluna, esperado) != "valida":
                problemas.append(f"coluna v6 {tabela}.{coluna} ausente ou diferente da esperada")
        if _estado_indice_email_ci(cursor) != "valido":
            problemas.append(f"índice v6 {INDICE_EMAIL_CI} ausente ou diferente do esperado")
        estados_v7 = {
            f"{tabela}.{coluna}": _estado_coluna_v6(cursor, tabela, coluna, esperado)
            for tabela, coluna, _, esperado in COLUNAS_V7
        }
        estados_v7[INDICE_POSICAO] = _estado_indice_posicao(cursor)
        for item, estado in estados_v7.items():
            if estado == "incompativel":
                problemas.append(f"{item} com definição diferente da esperada")

        if versao == VERSAO_SCHEMA_V7:
            completos = all(e in ("valida", "valido") for e in estados_v7.values())
            if not completos:
                problemas.append("user_version 7 sem todos os itens da v7")
            if problemas:
                raise SchemaV7IncompativelError(problemas)
            cursor.execute("ROLLBACK;")
            return {"executado": False, "motivo": "já migrado", "backup": None}

        presentes = [item for item, estado in estados_v7.items() if estado != "ausente"]
        if presentes:
            problemas.append(f"itens da v7 já presentes num banco v6: {', '.join(presentes)}")
        if problemas:
            raise SchemaV7IncompativelError(problemas)

        validacao_v6 = _verificar_schema_v6(cursor)
        if not validacao_v6["ok"]:
            raise BancoNaoPreparadoError(validacao_v6)

        provaveis, diagnostico = _classificar_vagas(cursor)
        if diagnostico:
            raise VagasNaoInferiveisError(diagnostico)

        # Lido por outra conexão: o RESERVED lock deste BEGIN IMMEDIATE ainda
        # permite leitura e garante que nada muda entre o backup e as alterações.
        caminho_backup = criar_backup(caminho_banco, rotulo="v7")
        if not _verificar_integridade_backup(caminho_backup):
            raise RuntimeError(
                f"Backup pré-migração v7 falhou no integrity_check ({caminho_backup}); "
                "migração abortada."
            )

        contagens_antes = _contagens(cursor)
        dados_antes = _dados_v6(cursor)

        for tabela, coluna, definicao, _ in COLUNAS_V7:
            cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao};")

        cursor.execute("SELECT id FROM series_recorrencia ORDER BY id")
        for (serie_id,) in cursor.fetchall():
            cursor.execute(
                "SELECT id FROM contas WHERE serie_id = ? ORDER BY data_vencimento, id", (serie_id,)
            )
            ids = [linha[0] for linha in cursor.fetchall()]
            for posicao, conta_id in enumerate(ids, start=1):
                cursor.execute(
                    "UPDATE contas SET posicao = ?, data_prevista = data_vencimento WHERE id = ?",
                    (posicao, conta_id),
                )
            cursor.execute(
                "UPDATE series_recorrencia SET posicao_ancora = ? WHERE id = ?",
                (1 if ids else 0, serie_id),
            )

        cursor.execute(f"CREATE UNIQUE INDEX {INDICE_POSICAO} ON contas(serie_id, posicao);")
        cursor.execute(f"PRAGMA user_version = {VERSAO_SCHEMA_V7};")

        verificacao = _verificar_schema_v7(cursor)
        if (not verificacao["ok"] or _contagens(cursor) != contagens_antes
                or _dados_v6(cursor) != dados_antes):
            raise RuntimeError("Validação pós-migração v7 falhou; alterações revertidas.")

        cursor.execute("COMMIT;")
    except BaseException:
        _reverter_transacao(conexao)
        raise
    finally:
        conexao.close()

    return {"executado": True, "backup": caminho_backup, "ocorrencias_provaveis": provaveis}


def _banco_existente_vazio(caminho_banco):
    """
    Só leitura. Recusa `user_version` não suportada (VersaoDeBancoNaoSuportadaError)
    e retorna True para um arquivo sem nenhum objeto de schema (ex.: 0 bytes).
    """
    conexao = sqlite3.connect(caminho_banco)
    try:
        cursor = conexao.cursor()
        _exigir_versao_suportada(cursor)
        cursor.execute("SELECT COUNT(*) FROM sqlite_master")
        return cursor.fetchone()[0] == 0
    finally:
        conexao.close()


def preparar_banco():
    """
    Garante, na inicialização do app, que `NOME_DO_BANCO` está no schema
    atual (v7), reutilizando `criar_tabelas()`, `migrar_schema_v6()`,
    `migrar_schema_v7()` e `validar_schema_atual()`:

      * `user_version` fora de VERSOES_SUPORTADAS (ex.: banco de uma versão
        futura): `VersaoDeBancoNaoSuportadaError` antes de qualquer escrita;
      * banco inexistente, ou arquivo sem nenhuma tabela: `criar_tabelas()`
        gera o schema v7 direto, sem backup -> situação "criado";
      * banco que já passa em `validar_schema_atual()`: nada é gravado, nem
        lock de escrita é pedido -> "atual";
      * banco v5 (ou v6 incompleto): `migrar_schema_v6()` e depois
        `migrar_schema_v7()` -- duas transações e dois backups. Se a v7
        falhar, o banco fica em v6 válido (com o backup v6) e a próxima
        inicialização retoma a partir dele;
      * banco v6: só `migrar_schema_v7()` -> "migrado".

    `criar_tabelas()` nunca é chamada sobre um banco existente. Ao final, o
    banco precisa passar em `validar_schema_atual()`; caso contrário,
    `BancoNaoPreparadoError`. Erros das migrações (inclusive
    `VagasNaoInferiveisError`, D3) são propagados sem tratamento: nenhum
    reparo silencioso, e quem chama decide como interromper o app.

    Retorna {"situacao": "criado" | "migrado" | "atual",
             "migracao": dict | None (v6), "migracao_v7": dict | None}.
    """
    caminho_banco = NOME_DO_BANCO
    migracao_v6 = migracao_v7 = None
    if not os.path.exists(caminho_banco) or _banco_existente_vazio(caminho_banco):
        criar_tabelas()
        situacao = "criado"
    elif validar_schema_atual(caminho_banco)["ok"]:
        return {"situacao": "atual", "migracao": None, "migracao_v7": None}
    else:
        if not validar_migracao_v6(caminho_banco)["ok"]:
            migracao_v6 = migrar_schema_v6(caminho_banco)
        migracao_v7 = migrar_schema_v7(caminho_banco)
        executou = any(m is not None and m["executado"] for m in (migracao_v6, migracao_v7))
        situacao = "migrado" if executou else "atual"

    validacao = validar_schema_atual(caminho_banco)
    if not validacao["ok"]:
        raise BancoNaoPreparadoError(validacao)
    return {"situacao": situacao, "migracao": migracao_v6, "migracao_v7": migracao_v7}


# RNF05: PBKDF2-HMAC-SHA256 (stdlib, sem dependência nova) com salt aleatório
# individual por usuário. Parâmetros nomeados em vez de números mágicos --
# qualquer mudança futura de custo do hash fica visível e centralizada aqui.
PBKDF2_ALGORITMO = "pbkdf2_sha256"
PBKDF2_ITERACOES = 200_000
PBKDF2_TAMANHO_SALT_BYTES = 16


def _derivar_pbkdf2(senha, salt_hex, iteracoes):
    salt = bytes.fromhex(salt_hex)
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iteracoes).hex()


def _gerar_hash_senha(senha):
    """
    RNF05: gera o valor armazenado em `usuarios.senha_hash` no formato novo,
    autodescritivo -- "pbkdf2_sha256$iteracoes$salt$hash" -- para que
    algoritmo e custo fiquem registrados junto do próprio hash, sem exigir
    coluna extra (sem alteração de schema). Salt gerado com `secrets`
    (criptograficamente seguro), único a cada chamada.
    """
    salt_hex = secrets.token_hex(PBKDF2_TAMANHO_SALT_BYTES)
    hash_hex = _derivar_pbkdf2(senha, salt_hex, PBKDF2_ITERACOES)
    return f"{PBKDF2_ALGORITMO}${PBKDF2_ITERACOES}${salt_hex}${hash_hex}"


def _gerar_hash_senha_legado(senha):
    # Formato pré-RNF05 (sha256 puro, sem salt) -- mantido só para permitir
    # que contas já cadastradas nesse formato ainda autentiquem; nunca usado
    # para gerar hash novo.
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def _verificar_senha(senha, senha_hash_armazenada):
    """
    RNF05: compara `senha` contra o valor armazenado, reconhecendo tanto o
    formato novo (`pbkdf2_sha256$...`) quanto o legado (sha256 puro, sem
    "$"). Qualquer valor armazenado corrompido ou em formato inesperado
    resulta em False -- nunca lança exceção, para que o login falhe de
    forma controlada em vez de quebrar. Comparação sempre feita com
    `secrets.compare_digest` (resistente a timing attack), nos dois
    formatos.
    """
    if not senha_hash_armazenada:
        return False

    if "$" in senha_hash_armazenada:
        partes = senha_hash_armazenada.split("$")
        if len(partes) != 4:
            return False
        algoritmo, iteracoes_str, salt_hex, hash_esperado = partes
        if algoritmo != PBKDF2_ALGORITMO:
            return False
        try:
            iteracoes = int(iteracoes_str)
            hash_calculado = _derivar_pbkdf2(senha, salt_hex, iteracoes)
        except (ValueError, TypeError):
            return False
        return secrets.compare_digest(hash_calculado, hash_esperado)

    # Formato legado -- sem salt.
    hash_calculado = _gerar_hash_senha_legado(senha)
    return secrets.compare_digest(hash_calculado, senha_hash_armazenada)


# ERS v6.0, 5.33/RF37 (Etapa 7): regras para toda senha DEFINIDA a partir da
# v6.0 -- cadastro, alteração e, na Etapa 8, recuperação. A senha nunca é
# transformada (sem strip nem normalização): uma nova senha com qualquer
# espaço em branco é recusada como veio; o mínimo conta caracteres
# percebidos, com o mesmo mecanismo dos limites de texto (T5). O login e a
# conferência da senha atual NÃO aplicam estas regras: senhas anteriores,
# mesmo curtas ou com espaços, continuam valendo (CT82).
SENHA_MINIMO = 8


class SenhaInvalidaError(ValueError):
    """Nova senha recusada. A mensagem é amigável e nunca contém a senha."""


class SenhaCurtaError(SenhaInvalidaError):
    def __init__(self):
        super().__init__(f"A senha deve ter pelo menos {SENHA_MINIMO} caracteres.")


class SenhaComEspacosError(SenhaInvalidaError):
    def __init__(self):
        super().__init__("A senha não pode conter espaços.")


class SenhaAtualIncorretaError(ValueError):
    def __init__(self):
        super().__init__("A senha atual está incorreta.")


class SenhaIgualAtualError(SenhaInvalidaError):
    def __init__(self):
        super().__init__("A nova senha deve ser diferente da atual.")


def validar_nova_senha(senha):
    """
    5.33: levanta `SenhaInvalidaError` (ou uma subclasse) para entrada que
    não é texto, senha com qualquer espaço em branco (espaço, tabulação,
    quebra de linha, espaço não separável...; em qualquer posição) ou com
    menos de `SENHA_MINIMO` caracteres percebidos. Devolve a senha intacta.
    """
    if not isinstance(senha, str):
        raise SenhaInvalidaError("A senha precisa ser um texto.")
    if any(caractere.isspace() for caractere in senha):
        raise SenhaComEspacosError()
    if contar_caracteres(senha) < SENHA_MINIMO:
        raise SenhaCurtaError()
    return senha


def criar_usuario(nome, email, senha, aceite_termos=False):
    """
    RF15: `termos_aceitos_em` só é gravado quando `aceite_termos` é True --
    representa o aceite explícito e real do usuário no cadastro (nunca um
    carimbo automático). Sem aceite, nenhuma conta é criada.

    ERS v6.0: o e-mail é único sem diferenciar maiúsculas de minúsculas. A
    consulta prévia por lower(email) mantém a regra também em bancos v5
    ainda não migrados; em bancos v6, o índice `idx_usuarios_email_ci` a
    garante na gravação. O e-mail é gravado como informado.

    5.33 (Etapa 7): a senha segue `validar_nova_senha`; recusada, nenhuma
    conta é criada e a mensagem amigável volta no mesmo contrato.
    """
    if not aceite_termos:
        return False, "É necessário aceitar os Termos de Uso e a Política de Privacidade."
    try:
        validar_limite("nome_usuario", nome, LIMITE_NOME_USUARIO)  # 5.23
    except LimiteDeCaracteresError as erro:
        return False, str(erro)
    try:
        validar_nova_senha(senha)
    except SenhaInvalidaError as erro:
        return False, str(erro)

    conexao = conectar()
    cursor = conexao.cursor()
    senha_hash = _gerar_hash_senha(senha)
    agora = date.today().isoformat()
    try:
        cursor.execute("SELECT 1 FROM usuarios WHERE lower(email) = lower(?)", (email,))
        if cursor.fetchone() is not None:
            return False, "Já existe uma conta com esse e-mail."
        cursor.execute(
            "INSERT INTO usuarios (nome, email, senha_hash, termos_aceitos_em) VALUES (?, ?, ?, ?)",
            (nome, email, senha_hash, agora),
        )
        conexao.commit()
        return True, "Usuário criado com sucesso."
    except sqlite3.IntegrityError:
        return False, "Já existe uma conta com esse e-mail."
    finally:
        conexao.close()


def verificar_login(email, senha):
    """
    RNF05: busca o usuário só por e-mail (a senha não entra mais na consulta
    SQL, pois o hash depende de um salt por usuário) e valida via
    `_verificar_senha`, que reconhece formato novo e legado. Quando a conta
    autentica com sucesso e ainda está no formato legado (sha256 sem salt),
    o hash é substituído pelo formato novo nesse mesmo momento -- nunca
    antes da senha ser confirmada, e nunca para contas que não fizerem
    login (não precisamos conhecer a senha delas para isso). Contrato de
    retorno: dict (id/nome/email/tema) ou None.

    ERS v6.0: a busca por e-mail não diferencia maiúsculas de minúsculas
    (usa `idx_usuarios_email_ci` em bancos v6). `email_verificado` não
    bloqueia o login. Em um banco v5 legado com e-mails que só diferem na
    caixa, a correspondência exata tem prioridade.

    5.36 (Etapa 6): `tema` é a preferência gravada do usuário, para o app
    aplicá-la logo após o login. Em um banco v5 ainda não migrado (sem a
    coluna), vale o padrão `TEMA_PADRAO`.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    tem_tema = _coluna_existe(cursor, "usuarios", "tema")
    cursor.execute(
        f"""
        SELECT id, nome, email, senha_hash{", tema" if tem_tema else ""} FROM usuarios
        WHERE lower(email) = lower(?)
        ORDER BY email = ? DESC, id
        LIMIT 1
        """,
        (email, email),
    )
    resultado = cursor.fetchone()
    if resultado is None:
        conexao.close()
        return None

    usuario_id, nome, email_encontrado, senha_hash_armazenada = resultado[:4]
    tema = resultado[4] if tem_tema else TEMA_PADRAO
    if not _verificar_senha(senha, senha_hash_armazenada):
        conexao.close()
        return None

    if "$" not in senha_hash_armazenada:
        novo_hash = _gerar_hash_senha(senha)
        cursor.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (novo_hash, usuario_id))
        conexao.commit()

    conexao.close()
    return {"id": usuario_id, "nome": nome, "email": email_encontrado, "tema": tema}


# 5.36: temas aceitos em `usuarios.tema` (o CHECK do schema é o mesmo).
TEMAS = ("claro", "escuro")
TEMA_PADRAO = "claro"


def obter_usuario(usuario_id):
    """
    Dados do usuário para a tela Ajustes (RF35, RF40): dict com id, nome,
    email, email_verificado (bool) e tema, ou None se o usuário não existir.
    Nunca devolve `senha_hash` nem `termos_aceitos_em`.
    """
    conexao = conectar()
    try:
        linha = conexao.execute(
            "SELECT id, nome, email, email_verificado, tema FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
    finally:
        conexao.close()
    if linha is None:
        return None
    return {"id": linha[0], "nome": linha[1], "email": linha[2],
            "email_verificado": bool(linha[3]), "tema": linha[4]}


def alterar_nome_usuario(usuario_id, nome):
    """
    RF35/5.23: grava o novo nome do usuário, sem espaços nas bordas.

    Nome vazio (ou só com espaços) levanta ValueError; acima de 70
    caracteres percebidos levanta `LimiteDeCaracteresError`. Nos dois
    casos nada é gravado. Só a linha de `usuario_id` é alterada.

    Retorna o nome gravado, ou None se o usuário não existir -- quem chama
    só atualiza a sessão/interface com esse retorno.
    """
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("O nome é obrigatório.")
    validar_limite("nome_usuario", nome, LIMITE_NOME_USUARIO)

    conexao = conectar()
    try:
        cursor = conexao.execute("UPDATE usuarios SET nome = ? WHERE id = ?", (nome, usuario_id))
        conexao.commit()
        return nome if cursor.rowcount == 1 else None
    finally:
        conexao.close()


def alterar_senha(usuario_id, senha_atual, nova_senha):
    """
    RF38/5.34: troca a senha do usuário, em uma única transação, nesta ordem:

      * usuário inexistente -> devolve False;
      * senha atual incorreta (ou que não é texto) -> SenhaAtualIncorretaError;
      * nova senha inválida (`validar_nova_senha`) -> SenhaInvalidaError;
      * nova senha igual à atual -> SenhaIgualAtualError.

    Em qualquer recusa ou falha nada é gravado. A nova senha é guardada no
    formato PBKDF2 (RNF05), inclusive quando a atual ainda estava no formato
    legado. A confirmação da nova senha é responsabilidade da interface.
    Devolve True quando a senha é alterada.
    """
    conexao = conectar()
    conexao.isolation_level = None  # controle explícito da transação
    try:
        cursor = conexao.cursor()
        cursor.execute("BEGIN IMMEDIATE;")
        linha = cursor.execute("SELECT senha_hash FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if linha is None:
            cursor.execute("ROLLBACK;")
            return False
        senha_hash_atual = linha[0]
        if not isinstance(senha_atual, str) or not _verificar_senha(senha_atual, senha_hash_atual):
            raise SenhaAtualIncorretaError()
        validar_nova_senha(nova_senha)
        if _verificar_senha(nova_senha, senha_hash_atual):
            raise SenhaIgualAtualError()
        cursor.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (_gerar_hash_senha(nova_senha), usuario_id))
        cursor.execute("COMMIT;")
        return True
    except BaseException:
        _reverter_transacao(conexao)
        raise
    finally:
        conexao.close()


def definir_tema(usuario_id, tema):
    """
    RF40/5.36: grava a preferência de tema do usuário ("claro" ou
    "escuro"). Qualquer outro valor levanta ValueError sem gravar nada.
    Retorna True se gravou, False se o usuário não existir.
    """
    if tema not in TEMAS:
        raise ValueError(f"tema inválido: {tema!r} (aceitos: {', '.join(TEMAS)})")

    conexao = conectar()
    try:
        cursor = conexao.execute("UPDATE usuarios SET tema = ? WHERE id = ?", (tema, usuario_id))
        conexao.commit()
        return cursor.rowcount == 1
    finally:
        conexao.close()


# RF14/5.11: catálogo pré-criado, disponível "desde o primeiro acesso... não é
# necessário criá-las manualmente". Emoji = primeira sugestão de cada linha da
# tabela 5.12 (proposta inicial de UX, não valor imutável da ERS).
CATEGORIAS_PRE_CRIADAS = [
    ("Casa", "🏡"),
    ("Automóvel", "🚗"),
    ("Lazer", "🎡"),
    ("Faculdade", "📚"),
    ("Academia", "🏋🏻‍♀️"),
    ("Saúde", "🏥"),
    ("Cartão de crédito", "💳"),
    ("Beleza", "💄"),
    ("Streaming", "📽️"),
    ("Creche", "👶"),
    ("Outro", "💕"),
]

# RF18/5.13: "paleta de até 30 cores... valores exatos não são fixados nesta
# ERS como decisão definitiva". 30 posições FIXAS, em progressão de matiz
# (azuis -> índigos -> violetas/roxos -> rosas -> vermelhos/corais -> laranjas
# -> amarelos -> verdes -> turquesas -> ciano) -- revisão visual da usuária
# pós-Bloco 1. A ORDEM É A FONTE DE VERDADE da apresentação visual: o
# seletor de cores (montar_paleta() em backend/main.py) só filtra cores já
# em uso, nunca reordena -- uma cor liberada por edição/exclusão de
# categoria volta a aparecer exatamente nesta mesma posição, nunca no
# início/fim da lista renderizada. As 11 cores de CORES_CATEGORIAS_PRE_CRIADAS
# (abaixo) são um subconjunto desta lista -- existe uma única paleta oficial
# de 30 cores, e as categorias pré-criadas usam 11 delas.
PALETA_CORES_CATEGORIAS = [
    "#64B5F6", "#1976D2", "#0277BD", "#3F51B5", "#5C6BC0",
    "#A990D8", "#7E57C2", "#8E24AA", "#CE93D8", "#C2185B",
    "#EC407A", "#F48FB1", "#E53935", "#EF5350", "#F3756A",
    "#EF9A9A", "#FF7043", "#FFAB91", "#F57C00", "#FFA000",
    "#FFD54F", "#FBC02D", "#AFB42B", "#96E199", "#43A047",
    "#00897B", "#80CBC4", "#77E3D3", "#0097A7", "#00ACC1",
]

# Cor de cada uma das 11 categorias pré-criadas (5.11/5.13), definida
# EXPLICITAMENTE por categoria -- mesma ordem de CATEGORIAS_PRE_CRIADAS.
# Cada valor aqui é uma das 30 cores de PALETA_CORES_CATEGORIAS (não uma cor
# externa), mas a ASSOCIAÇÃO categoria->cor é deliberadamente desacoplada da
# posição de cada HEX na paleta (que existe só para a ordem visual do
# seletor). Reordenar a paleta acima nunca muda estas associações nem afeta
# categorias já existentes no banco -- só rege a cor atribuída a usuários
# novos via inicializar_categorias_padrao().
CORES_CATEGORIAS_PRE_CRIADAS = [
    "#96E199",  # Casa
    "#FFD54F",  # Automóvel
    "#FFAB91",  # Lazer
    "#64B5F6",  # Faculdade
    "#CE93D8",  # Academia
    "#80CBC4",  # Saúde
    "#A990D8",  # Cartão de crédito
    "#F48FB1",  # Beleza
    "#F3756A",  # Streaming
    "#77E3D3",  # Creche
    "#EF9A9A",  # Outro
]

LIMITE_CATEGORIAS_POR_USUARIO = 30  # 5.11, contando as pré-criadas

# 5.13/5.25 (Etapa 5): cinza reservado ao agrupamento "Sem categoria" --
# nenhuma categoria pode usá-lo (não está na paleta, e a gravação recusa).
# backend/cores.py (`sem_categoria`) usa exatamente este valor.
COR_RESERVADA_SEM_CATEGORIA = "#888780"


class CorReservadaError(ValueError):
    """Tentativa de gravar o cinza reservado a "Sem categoria" (5.13)."""

    def __init__(self):
        super().__init__("o cinza é reservado para 'Sem categoria' e não pode ser usado por uma categoria")


def _recusar_cor_reservada(cor):
    if cor is not None and str(cor).strip().upper() == COR_RESERVADA_SEM_CATEGORIA:
        raise CorReservadaError()


def cores_de_exibicao(categorias):
    """
    Etapa 5: cor de cada categoria nos gráficos, {categoria_id: cor}. A cor
    gravada é usada como está; uma categoria sem cor recebe, só para a
    exibição (nada é gravado), uma cor da paleta que nenhuma categoria do
    usuário usa -- na ordem da paleta, distribuídas por ordem de id. Assim a
    cor é estável entre períodos e nunca é o cinza reservado. Pelo limite
    de 30 categorias sempre há cor livre; se um banco legado passar do
    limite, a paleta é reaproveitada em ciclo (a legenda desambigua pelo nome).
    """
    usadas = {c["cor"].upper() for c in categorias if c.get("cor")}
    livres = [cor for cor in PALETA_CORES_CATEGORIAS if cor.upper() not in usadas] or list(PALETA_CORES_CATEGORIAS)
    sem_cor = sorted(c["id"] for c in categorias if not c.get("cor"))
    resultado = {c["id"]: c["cor"] for c in categorias if c.get("cor")}
    resultado.update({categoria_id: livres[i % len(livres)] for i, categoria_id in enumerate(sem_cor)})
    return resultado


def _proxima_cor_disponivel(cursor, usuario_id, ignorar_categoria_id=None):
    """Primeira cor da paleta ainda não usada por outra categoria do usuário (5.13)."""
    sql = "SELECT cor FROM categorias WHERE usuario_id = ? AND cor IS NOT NULL"
    parametros = [usuario_id]
    if ignorar_categoria_id is not None:
        sql += " AND id != ?"
        parametros.append(ignorar_categoria_id)
    cursor.execute(sql, parametros)
    cores_em_uso = {linha[0] for linha in cursor.fetchall()}
    for cor in PALETA_CORES_CATEGORIAS:
        if cor not in cores_em_uso:
            return cor
    return None


def criar_categoria(usuario_id, nome, icone=None, cor=None):
    """
    RF14/RF18 (5.11/5.13): cria uma categoria para o usuário.

    Respeita o limite de 30 categorias por usuário (contando as
    pré-criadas) -- levanta ValueError se já atingido. Se `cor` não for
    informada, atribui automaticamente a primeira cor disponível da
    paleta; se for informada e já estiver em uso por outra categoria do
    mesmo usuário, ou se não houver nenhuma cor disponível para
    atribuição automática, a chamada é rejeitada (levanta ValueError) --
    nunca falha silenciosamente nem atribui cor duplicada.

    Nome com no máximo 30 caracteres (5.11/5.23): acima disso levanta
    `LimiteDeCaracteresError` (subclasse de ValueError) sem gravar nada.

    Operação transacional. Retorna o id da categoria criada. O cinza
    reservado a "Sem categoria" é recusado (`CorReservadaError`, 5.13).
    """
    validar_limite("nome_categoria", nome, LIMITE_NOME_CATEGORIA)
    _recusar_cor_reservada(cor)

    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
    conexao.execute("PRAGMA foreign_keys = ON;")
    cursor = conexao.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM categorias WHERE usuario_id = ?", (usuario_id,))
        if cursor.fetchone()[0] >= LIMITE_CATEGORIAS_POR_USUARIO:
            raise ValueError(
                f"limite de {LIMITE_CATEGORIAS_POR_USUARIO} categorias atingido "
                f"para o usuário {usuario_id}"
            )

        if cor is not None:
            cursor.execute(
                "SELECT COUNT(*) FROM categorias WHERE usuario_id = ? AND cor = ?",
                (usuario_id, cor),
            )
            if cursor.fetchone()[0] > 0:
                raise ValueError(f"cor {cor!r} já está em uso por outra categoria deste usuário")
        else:
            cor = _proxima_cor_disponivel(cursor, usuario_id)
            if cor is None:
                raise ValueError(f"nenhuma cor disponível na paleta para o usuário {usuario_id}")

        try:
            cursor.execute("BEGIN;")
            cursor.execute(
                "INSERT INTO categorias (usuario_id, nome, icone, cor) VALUES (?, ?, ?, ?)",
                (usuario_id, nome, icone, cor),
            )
            novo_id = cursor.lastrowid
            cursor.execute("COMMIT;")
        except Exception:
            cursor.execute("ROLLBACK;")
            raise
    finally:
        conexao.close()

    return novo_id


def inicializar_categorias_padrao(usuario_id):
    """
    RF14 (5.11): cria as 11 categorias pré-criadas para um usuário, cada
    uma com emoji sugerido (5.12) e cor própria da paleta (5.13). Pensada
    para ser chamada uma vez ao cadastrar o usuário (RF01) -- o catálogo
    fica disponível "desde o primeiro acesso... não é necessário
    criá-las manualmente".

    Idempotente: se o usuário já tiver qualquer categoria (deste
    catálogo ou não), não faz nada -- evita duplicar caso seja chamada
    de novo. Operação transacional. Retorna a lista de ids criados, ou
    lista vazia se o usuário já tinha categorias.
    """
    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
    conexao.execute("PRAGMA foreign_keys = ON;")
    cursor = conexao.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM categorias WHERE usuario_id = ?", (usuario_id,))
        if cursor.fetchone()[0] > 0:
            return []

        try:
            cursor.execute("BEGIN;")
            ids_criados = []
            for indice, (nome, icone) in enumerate(CATEGORIAS_PRE_CRIADAS):
                cursor.execute(
                    "INSERT INTO categorias (usuario_id, nome, icone, cor) VALUES (?, ?, ?, ?)",
                    (usuario_id, nome, icone, CORES_CATEGORIAS_PRE_CRIADAS[indice]),
                )
                ids_criados.append(cursor.lastrowid)
            cursor.execute("COMMIT;")
        except Exception:
            cursor.execute("ROLLBACK;")
            raise
    finally:
        conexao.close()

    return ids_criados


def listar_categorias(usuario_id):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id, nome, icone, cor FROM categorias WHERE usuario_id = ? ORDER BY nome",
        (usuario_id,),
    )
    linhas = cursor.fetchall()
    conexao.close()
    return [{"id": l[0], "nome": l[1], "icone": l[2], "cor": l[3]} for l in linhas]


def _ajustar_dia(ano, mes, dia):
    """Reduz `dia` ao último dia válido de `ano/mes`, se necessário (ex.: 31 -> 28/29 em fevereiro)."""
    ultimo_dia_do_mes = monthrange(ano, mes)[1]
    return min(dia, ultimo_dia_do_mes)


def _somar_mes(ano, mes, dia):
    mes += 1
    if mes > 12:
        mes = 1
        ano += 1
    dia_ajustado = _ajustar_dia(ano, mes, dia)
    return date(ano, mes, dia_ajustado).isoformat()


def _somar_ano(ano, mes_ancora, dia_ancora):
    """
    Próxima ocorrência anual a partir de `ano`, sem arrasto (ERS 5.2.2):
    sempre recalcula a partir de `mes_ancora`/`dia_ancora` fixos (nunca do
    dia já ajustado de uma ocorrência anterior), então 29/02 é ajustado
    para 28/02 em ano não bissexto, mas volta a 29/02 assim que o próximo
    ano bissexto chega — a data-âncora em si nunca muda.
    """
    proximo_ano = ano + 1
    dia_ajustado = _ajustar_dia(proximo_ano, mes_ancora, dia_ancora)
    return date(proximo_ano, mes_ancora, dia_ajustado).isoformat()


def _validar_textos_conta(nome=None, descricao=None):
    """5.23: valida só os textos que serão gravados (`None` = não enviado)."""
    if nome is not None:
        validar_limite("nome_conta", nome, LIMITE_NOME_CONTA)
    if descricao is not None:
        validar_limite("descricao", descricao, LIMITE_DESCRICAO)


def criar_conta_unica(usuario_id, nome, valor, data_vencimento, categoria_id=None, descricao=None):
    """
    Cria uma conta avulsa (RF04/RF10 — tipo Única): uma única linha em
    `contas`, sem série. `serie_id` fica `NULL` e nenhum registro é criado
    em `series_recorrencia`.

    `descricao` é opcional (5.22) e gravada já normalizada (sem espaços nas
    bordas; vazia vira NULL). Nome acima de 30 ou descrição acima de 500
    caracteres levantam `LimiteDeCaracteresError` sem gravar nada (5.23).
    """
    descricao = normalizar_descricao(descricao)
    _validar_textos_conta(nome, descricao)

    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        """
        INSERT INTO contas (usuario_id, categoria_id, nome, valor, data_vencimento, status, descricao)
        VALUES (?, ?, ?, ?, ?, 'pendente', ?)
        """,
        (usuario_id, categoria_id, nome, valor, data_vencimento, descricao),
    )
    novo_id = cursor.lastrowid
    conexao.commit()
    conexao.close()
    return novo_id


def _avancar_ate_limite(avancar, data_referencia, limite_ano, limite_mes):
    """
    Datas seguintes a (mas sem incluir) `data_referencia`, avançando via
    `avancar(ano, mes) -> proxima_data_iso`, até `limite_ano`/`limite_mes`
    inclusive. Lista vazia se `data_referencia` já está no limite ou além
    dele. Cada chamada de `avancar` recalcula a partir do ano/mês atuais —
    quem fecha `avancar` (mensal: `_somar_mes`; anual: `_somar_ano`) é
    responsável por manter o dia/mês-âncora fixos, garantindo "sem
    arrasto" (5.2).
    """
    datas = []
    ultima = data_referencia
    while True:
        ano_atual, mes_atual, _ = map(int, ultima.split("-"))
        proxima = avancar(ano_atual, mes_atual)
        ano_proxima, mes_proxima, _ = map(int, proxima.split("-"))
        if (ano_proxima, mes_proxima) > (limite_ano, limite_mes):
            break
        datas.append(proxima)
        ultima = proxima
    return datas


def _gerar_datas_ocorrencias(frequencia, data_inicio, data_termino):
    """
    Lista de datas (ISO, em ordem) da ocorrência-âncora (`data_inicio`) até
    onde a geração inicial da série deve chegar, sem arrasto (5.2).

    Com `data_termino` ("AAAA-MM"): gera até esse mês, inclusive, sem
    limite de 12 meses (5.3/CT34) — mesmo critério (comparação de ano/mês)
    já usado pelo modelo anterior para "conta fixa".

    Sem `data_termino`: gera até o horizonte inicial de "os 12 meses
    seguintes à ocorrência-âncora" (5.3/9.4/CT07). Isso é uma janela de
    calendário — 12 meses corridos a partir da âncora, ou seja, até
    ano_ancora+1/mes_ancora inclusive — e não uma contagem fixa de
    ocorrências: numa série mensal essa janela produz 12 ocorrências além
    da âncora (uma por mês); numa série anual, a próxima ocorrência já cai
    exatamente na borda dessa janela (12 meses = 1 ano depois), então
    produz só mais 1. É só o horizonte inicial, não o fim da recorrência —
    a série continua aberta e a extensão contínua fica a cargo da geração
    sob demanda (`gerar_ocorrencias_sob_demanda`, seção 5.20).
    """
    ano_ancora, mes_ancora, dia_ancora = map(int, data_inicio.split("-"))
    avancar = (
        (lambda ano, mes: _somar_mes(ano, mes, dia_ancora))
        if frequencia == "mensal"
        else (lambda ano, mes: _somar_ano(ano, mes_ancora, dia_ancora))
    )

    if data_termino is not None:
        limite_ano, limite_mes = map(int, data_termino.split("-"))
    else:
        limite_ano, limite_mes = ano_ancora + 1, mes_ancora

    return [data_inicio] + _avancar_ate_limite(avancar, data_inicio, limite_ano, limite_mes)


def _competencia(data_iso):
    """Competência (AAAA-MM) de uma data ISO."""
    return data_iso[:7]


def _inserir_ocorrencia(cursor, usuario_id, categoria_id, serie_id, nome, valor, data, descricao,
                        posicao=None):
    """
    Nova ocorrência pendente de série, na vaga `data` (vencimento real =
    vaga). Sem `posicao`, entra com NULL e ganha a posição na próxima
    `_renumerar_segmento` da mesma transação.
    """
    cursor.execute(
        """
        INSERT INTO contas
            (usuario_id, categoria_id, serie_id, nome, valor, data_vencimento, status, descricao,
             posicao, data_prevista)
        VALUES (?, ?, ?, ?, ?, ?, 'pendente', ?, ?, ?)
        """,
        (usuario_id, categoria_id, serie_id, nome, valor, data, descricao, posicao, data),
    )
    return cursor.lastrowid


def _renumerar_segmento(cursor, serie_id, apos_posicao):
    """
    Etapa 2b, invariante I3: as ocorrências da série com posição maior que
    `apos_posicao` (e as recém-inseridas, com posição NULL) passam a ter
    posições apos_posicao+1, +2, ... na ordem (data_prevista, id). As
    posições até `apos_posicao` (a âncora e tudo antes dela) nunca mudam.
    Duas fases (primeiro -id, depois o valor final) para o índice UNIQUE
    (serie_id, posicao) nunca colidir no meio da transação.
    """
    filtro = "serie_id = ? AND (posicao > ? OR posicao IS NULL)"
    cursor.execute(f"SELECT id FROM contas WHERE {filtro} ORDER BY data_prevista, id",
                   (serie_id, apos_posicao))
    ids = [linha[0] for linha in cursor.fetchall()]
    cursor.execute(f"UPDATE contas SET posicao = -id WHERE {filtro}", (serie_id, apos_posicao))
    for posicao, conta_id in enumerate(ids, start=apos_posicao + 1):
        cursor.execute("UPDATE contas SET posicao = ? WHERE id = ?", (posicao, conta_id))


def _grade_a_partir_da_vaga(frequencia, dia_ancora, mes_ancora, vaga, data_termino):
    """
    D1, variante "d" (Etapa 2b): nova grade ao alterar a frequência a partir
    de uma ocorrência cuja VAGA é `vaga`. O dia (e o mês, se anual) vêm do
    vencimento real da selecionada; as novas vagas começam na competência
    seguinte à vaga dela, até o término (ou 12 meses depois da vaga, se
    aberta). Sem vencimento movido para outro mês, é exatamente a grade que
    `_gerar_datas_ocorrencias` gera a partir do vencimento.

    Retorna (data_inicio da grade, [datas das novas vagas]).
    """
    vaga_data = date.fromisoformat(vaga)
    if frequencia == "mensal":
        ano, mes = vaga_data.year, vaga_data.month
        avancar = lambda a, m: _somar_mes(a, m, dia_ancora)  # noqa: E731
    else:
        ano = vaga_data.year if mes_ancora <= vaga_data.month else vaga_data.year - 1
        mes = mes_ancora
        avancar = lambda a, m: _somar_ano(a, mes_ancora, dia_ancora)  # noqa: E731
    base = date(ano, mes, _ajustar_dia(ano, mes, dia_ancora)).isoformat()
    if data_termino is not None:
        limite_ano, limite_mes = map(int, data_termino.split("-"))
    else:
        limite_ano, limite_mes = vaga_data.year + 1, vaga_data.month
    return base, _avancar_ate_limite(avancar, base, limite_ano, limite_mes)


def _vaga_na_grade(data_prevista, frequencia, mes_ancora, data_termino):
    """
    D2/D4: a vaga pertence à grade atual da série? Não pertence quando está
    além do término ou, numa série anual, em outro mês que não o da âncora
    (ex.: uma editada preservada depois de mensal -> anual).
    """
    if data_termino is not None and _competencia(data_prevista) > data_termino:
        return False
    return frequencia == "mensal" or int(data_prevista[5:7]) == mes_ancora


def _competencias_ocupadas(cursor, serie_id, apos_posicao):
    """Competências previstas já ocupadas por ocorrências depois de `apos_posicao`."""
    cursor.execute(
        "SELECT data_prevista FROM contas WHERE serie_id = ? AND posicao > ?",
        (serie_id, apos_posicao),
    )
    return {_competencia(linha[0]) for linha in cursor.fetchall()}


def criar_serie_recorrente(usuario_id, nome, valor, data_vencimento, frequencia,
                            data_termino=None, categoria_id=None, descricao=None):
    """
    Cria uma série recorrente (RF10 — Mensal/Anual): insere `series_recorrencia`
    e gera as ocorrências correspondentes em `contas`, cada uma apontando
    para a série via `serie_id`. `data_vencimento` é a ocorrência-âncora —
    define `data_inicio`/`dia_ancora`/`mes_ancora` (5.2).

    Sem `data_termino`: gera o horizonte inicial de 12 meses (5.3/CT07); a
    série fica aberta (`ativa=1`, `data_termino=NULL`).
    Com `data_termino` ("AAAA-MM"): gera integralmente até esse mês,
    inclusive, sem cap de 12 meses (5.3/CT34).

    Operação atômica: qualquer falha reverte tudo (ROLLBACK) — nunca deixa
    a série sem suas ocorrências, nem ocorrências órfãs. Retorna
    (serie_id, [ids das ocorrências criadas, em ordem]).

    `descricao` (5.22) vai para o modelo da série e para cada ocorrência,
    normalizada como em `criar_conta_unica`; limites de nome/descrição
    (5.23) são verificados antes de qualquer gravação.
    """
    if frequencia not in ("mensal", "anual"):
        raise ValueError(f"frequencia inválida: {frequencia!r} (use 'mensal' ou 'anual')")
    descricao = normalizar_descricao(descricao)
    _validar_textos_conta(nome, descricao)

    ano_ancora, mes_ancora_da_data, dia_ancora = map(int, data_vencimento.split("-"))
    mes_ancora = mes_ancora_da_data if frequencia == "anual" else None

    datas = _gerar_datas_ocorrencias(frequencia, data_vencimento, data_termino)
    horizonte_gerado_ate = datas[-1]

    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
    conexao.execute("PRAGMA foreign_keys = ON;")
    cursor = conexao.cursor()
    try:
        cursor.execute("BEGIN;")

        cursor.execute(
            """
            INSERT INTO series_recorrencia
                (usuario_id, nome, valor, categoria_id, frequencia, dia_ancora,
                 mes_ancora, data_inicio, data_termino, ativa, horizonte_gerado_ate, descricao,
                 posicao_ancora)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 1)
            """,
            (usuario_id, nome, valor, categoria_id, frequencia, dia_ancora,
             mes_ancora, data_vencimento, data_termino, horizonte_gerado_ate, descricao),
        )
        serie_id = cursor.lastrowid

        ids_ocorrencias = [
            _inserir_ocorrencia(cursor, usuario_id, categoria_id, serie_id, nome, valor,
                                data_ocorrencia, descricao, posicao=posicao)
            for posicao, data_ocorrencia in enumerate(datas, start=1)
        ]

        cursor.execute("COMMIT;")
    except Exception:
        cursor.execute("ROLLBACK;")
        raise
    finally:
        conexao.close()

    return serie_id, ids_ocorrencias


def gerar_ocorrencias_sob_demanda(serie_id, ate_data):
    """
    Gera as ocorrências que faltam para cobrir `ate_data` ("AAAA-MM") de
    uma série ativa e sem término (RF10/5.20/9.4/CT08) — o mecanismo que
    estende o horizonte inicial de 12 meses (2.4) conforme a necessidade
    real de exibir um período futuro ainda não gerado.

    - Série inativa (`ativa=0`) ou com `data_termino`: não gera nada,
      retorna `[]` — séries com término já saem geradas integralmente na
      criação (2.4); séries removidas (RF29, fora do escopo desta fase)
      não devem voltar a gerar ocorrências, só se preserva essa checagem.
    - As novas ocorrências copiam o modelo da série: nome, valor,
      categoria e descrição (5.6/5.22 -- "Este mês em diante" atualiza
      esse modelo, então elas já nascem com os dados novos).
    - Nunca toca ocorrências existentes (passadas, pagas, editadas
      individualmente ou não) — só insere o que falta a partir de
      `horizonte_gerado_ate`, sempre usando `dia_ancora`/`mes_ancora` da
      própria série (nunca redevirados de uma ocorrência já gerada), o
      que garante ausência de arrasto (5.2) e preserva a âncora original.
    - Etapa 2b: uma vaga só é criada se nenhuma ocorrência do segmento
      atual (posição >= `posicao_ancora`) já ocupar a mesma competência
      prevista -- uma editada preservada ocupa a própria vaga mesmo com o
      vencimento real movido, e uma ocorrência movida para a data da
      próxima vaga não a suprime (a comparação é pela vaga, não pelo
      vencimento). As novas entram no segmento em ordem de vaga.
    - Idempotente: se `ate_data` já está coberto por `horizonte_gerado_ate`
      (ou atrás dele), não há nada a avançar e a função retorna `[]` sem
      abrir transação nenhuma; chamar de novo com o mesmo `ate_data` nunca
      duplica nem altera o estado.
    - `horizonte_gerado_ate` passa a ser a última vaga da grade coberta
      por esta chamada (inclusive se ela já estava ocupada por uma
      preservada) -- nunca salta para o vencimento de uma ocorrência.
    - Atômica: qualquer falha reverte tudo (ROLLBACK); nunca deixa parte
      das ocorrências criadas nem o horizonte atualizado parcialmente.

    Retorna a lista de ids das novas ocorrências criadas (vazia se não
    havia nada a gerar). Levanta ValueError se `serie_id` não existir.
    """
    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
    conexao.execute("PRAGMA foreign_keys = ON;")
    cursor = conexao.cursor()
    try:
        cursor.execute(
            """
            SELECT usuario_id, nome, valor, categoria_id, frequencia,
                   dia_ancora, mes_ancora, data_termino, ativa, horizonte_gerado_ate, descricao,
                   posicao_ancora
            FROM series_recorrencia WHERE id = ?
            """,
            (serie_id,),
        )
        linha = cursor.fetchone()
        if linha is None:
            raise ValueError(f"series_recorrencia com id={serie_id} não existe")

        (usuario_id, nome, valor, categoria_id, frequencia, dia_ancora,
         mes_ancora, data_termino, ativa, horizonte_gerado_ate, descricao, posicao_ancora) = linha

        if ativa == 0 or data_termino is not None:
            return []

        limite_ano, limite_mes = map(int, ate_data.split("-"))
        avancar = (
            (lambda ano, mes: _somar_mes(ano, mes, dia_ancora))
            if frequencia == "mensal"
            else (lambda ano, mes: _somar_ano(ano, mes_ancora, dia_ancora))
        )
        novas_datas = _avancar_ate_limite(avancar, horizonte_gerado_ate, limite_ano, limite_mes)

        if not novas_datas:
            return []

        # Só a partir daqui uma transação é aberta -- o ROLLBACK abaixo deve
        # cobrir exclusivamente este trecho, nunca as checagens acima (uma
        # série inexistente/inativa/já coberta nunca chega a abrir transação).
        try:
            cursor.execute("BEGIN;")

            ocupadas = _competencias_ocupadas(cursor, serie_id, posicao_ancora - 1)
            ids_novos = [
                _inserir_ocorrencia(cursor, usuario_id, categoria_id, serie_id, nome, valor,
                                    data_ocorrencia, descricao)
                for data_ocorrencia in novas_datas
                if _competencia(data_ocorrencia) not in ocupadas
            ]
            _renumerar_segmento(cursor, serie_id, posicao_ancora)

            cursor.execute(
                "UPDATE series_recorrencia SET horizonte_gerado_ate = ? WHERE id = ?",
                (novas_datas[-1], serie_id),
            )

            cursor.execute("COMMIT;")
        except Exception:
            cursor.execute("ROLLBACK;")
            raise
    finally:
        conexao.close()

    return ids_novos


def transformar_em_recorrente(conta_id, frequencia, data_termino=None):
    """
    RF28 (5.4): transforma uma conta avulsa (Única) em recorrente. A
    ocorrência existente passa a ser a âncora de uma nova série -- não é
    duplicada nem recriada, só passa a referenciar a série nova via
    `serie_id`. "Não existem ocorrências anteriores a incorporar — a
    série começa exatamente a partir daquela ocorrência" (5.4).

    RF28 se aplica tanto a uma conta avulsa de verdade (`serie_id IS NULL`)
    quanto a uma conta cuja recorrência já foi encerrada (RF29/§5.8,
    `serie_id` aponta para uma série com `ativa = 0`): depois do
    encerramento, a conta passa a ser tratada como avulsa em toda a camada
    de produto/UI, então "Transformar em recorrente" deve funcionar nela
    exatamente como funcionaria numa conta que nunca foi recorrente. Só é
    rejeitada quando `serie_id` aponta para uma série **ativa** -- nesse
    caso a operação correta é "Alterar frequência" (RF27), não RF28. O
    `serie_id` antigo (da série encerrada) nunca é apagado nem alterado
    por esta função além do próprio `UPDATE` que aponta a conta para a
    série nova -- a série antiga permanece intacta no banco, preservando o
    histórico das demais ocorrências que ainda a referenciam.

    Gera as ocorrências futuras a partir da âncora com a mesma regra de
    horizonte de `criar_serie_recorrente` (2.4): integral até
    `data_termino` se houver, ou até o horizonte inicial de "12 meses
    seguintes à âncora" se não houver (5.3/9.4).

    Levanta ValueError se `conta_id` não existir, já pertencer a uma
    série ativa, ou `frequencia` for inválida. Operação transacional:
    qualquer falha reverte tudo (ROLLBACK), inclusive o `UPDATE` que
    vincula a âncora à nova série.

    Retorna (serie_id, ids_das_novas_ocorrencias) -- a própria `conta_id`
    não está nessa lista: ela é a âncora, mantém seu id e todos os seus
    dados (nome/valor/categoria/descricao/status/data_pagamento), só ganha
    um `serie_id` novo. Nome, valor, categoria e descrição da conta viram o
    modelo da série e são copiados para as ocorrências criadas; como são
    dados já gravados (não uma entrada nova), não são revalidados (P4).
    """
    if frequencia not in ("mensal", "anual"):
        raise ValueError(f"frequencia inválida: {frequencia!r} (use 'mensal' ou 'anual')")

    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
    conexao.execute("PRAGMA foreign_keys = ON;")
    cursor = conexao.cursor()
    try:
        cursor.execute(
            """
            SELECT usuario_id, categoria_id, serie_id, nome, valor, data_vencimento, descricao
            FROM contas WHERE id = ?
            """,
            (conta_id,),
        )
        linha = cursor.fetchone()
        if linha is None:
            raise ValueError(f"conta com id={conta_id} não existe")
        usuario_id, categoria_id, serie_id_atual, nome, valor, data_vencimento, descricao = linha
        if serie_id_atual is not None:
            cursor.execute("SELECT ativa FROM series_recorrencia WHERE id = ?", (serie_id_atual,))
            linha_serie_atual = cursor.fetchone()
            serie_atual_ativa = linha_serie_atual is not None and linha_serie_atual[0] == 1
            if serie_atual_ativa:
                raise ValueError(
                    f"conta id={conta_id} já pertence a uma série ativa (serie_id={serie_id_atual}) -- "
                    "RF28 só se aplica a conta avulsa ou com recorrência encerrada"
                )

        ano_ancora, mes_ancora_da_data, dia_ancora = map(int, data_vencimento.split("-"))
        mes_ancora = mes_ancora_da_data if frequencia == "anual" else None

        datas = _gerar_datas_ocorrencias(frequencia, data_vencimento, data_termino)
        datas_futuras = datas[1:]  # a primeira (data_vencimento) já existe -- é a própria conta_id
        horizonte_gerado_ate = datas[-1]

        try:
            cursor.execute("BEGIN;")

            cursor.execute(
                """
                INSERT INTO series_recorrencia
                    (usuario_id, nome, valor, categoria_id, frequencia, dia_ancora,
                     mes_ancora, data_inicio, data_termino, ativa, horizonte_gerado_ate, descricao,
                     posicao_ancora)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 1)
                """,
                (usuario_id, nome, valor, categoria_id, frequencia, dia_ancora,
                 mes_ancora, data_vencimento, data_termino, horizonte_gerado_ate, descricao),
            )
            serie_id = cursor.lastrowid

            # Etapa 2b: a conta vira a âncora (posição 1) e sua vaga é o
            # próprio vencimento.
            cursor.execute(
                "UPDATE contas SET serie_id = ?, posicao = 1, data_prevista = data_vencimento WHERE id = ?",
                (serie_id, conta_id),
            )

            ids_novos = [
                _inserir_ocorrencia(cursor, usuario_id, categoria_id, serie_id, nome, valor,
                                    data_ocorrencia, descricao, posicao=posicao)
                for posicao, data_ocorrencia in enumerate(datas_futuras, start=2)
            ]

            cursor.execute("COMMIT;")
        except Exception:
            cursor.execute("ROLLBACK;")
            raise
    finally:
        conexao.close()

    return serie_id, ids_novos


def listar_contas(usuario_id, ano_mes=None):
    conexao = conectar()
    cursor = conexao.cursor()

    if ano_mes:
        cursor.execute(
            """
            SELECT id, nome, valor, data_vencimento, status, categoria_id,
                   serie_id, data_pagamento, editado_individualmente, descricao
            FROM contas WHERE usuario_id = ? AND data_vencimento LIKE ?
            ORDER BY data_vencimento, posicao, id
            """,
            (usuario_id, f"{ano_mes}%"),
        )
    else:
        cursor.execute(
            """
            SELECT id, nome, valor, data_vencimento, status, categoria_id,
                   serie_id, data_pagamento, editado_individualmente, descricao
            FROM contas WHERE usuario_id = ?
            ORDER BY data_vencimento, posicao, id
            """,
            (usuario_id,),
        )

    linhas = cursor.fetchall()
    conexao.close()

    hoje = date.today().isoformat()
    contas = []
    for l in linhas:
        status = l[4]
        if status == "pendente" and l[3] < hoje:
            status = "atrasado"
        contas.append({
            "id": l[0], "nome": l[1], "valor": l[2], "data_vencimento": l[3],
            "status": status, "categoria_id": l[5], "serie_id": l[6],
            "data_pagamento": l[7], "editado_individualmente": l[8],
            "descricao": l[9],
        })
    return contas


def listar_contas_proximas(usuario_id, dias=7):
    """Contas pendentes com vencimento entre hoje e os próximos `dias` dias (RF17)."""
    conexao = conectar()
    cursor = conexao.cursor()

    hoje = date.today()
    limite = hoje + timedelta(days=dias)

    cursor.execute(
        """
        SELECT id, nome, valor, data_vencimento, status, categoria_id, serie_id, descricao
        FROM contas
        WHERE usuario_id = ? AND status = 'pendente'
              AND data_vencimento BETWEEN ? AND ?
        ORDER BY data_vencimento
        """,
        (usuario_id, hoje.isoformat(), limite.isoformat()),
    )
    linhas = cursor.fetchall()
    conexao.close()

    return [
        {"id": l[0], "nome": l[1], "valor": l[2], "data_vencimento": l[3],
         "status": l[4], "categoria_id": l[5], "serie_id": l[6], "descricao": l[7]}
        for l in linhas
    ]


def listar_contas_atrasadas(usuario_id):
    """Contas pendentes com vencimento já passado, de qualquer mês (RF25)."""
    conexao = conectar()
    cursor = conexao.cursor()

    hoje = date.today().isoformat()

    cursor.execute(
        """
        SELECT id, nome, valor, data_vencimento, categoria_id, serie_id, descricao
        FROM contas
        WHERE usuario_id = ? AND status = 'pendente' AND data_vencimento < ?
        ORDER BY data_vencimento
        """,
        (usuario_id, hoje),
    )
    linhas = cursor.fetchall()
    conexao.close()

    return [
        {"id": l[0], "nome": l[1], "valor": l[2], "data_vencimento": l[3],
         "status": "atrasado", "categoria_id": l[4], "serie_id": l[5], "descricao": l[6]}
        for l in linhas
    ]


# ------------------------------------------------------------------
#  Gráfico (ERS v6.0, Etapa 5: RF21-RF23, 5.24-5.30)
#
#  Somente leitura. Consideram todas as contas JÁ REGISTRADAS do usuário,
#  em qualquer status, pelo mês do vencimento real e pela categoria de cada
#  ocorrência. Nenhuma delas gera ocorrências recorrentes (5.26, CT114).
# ------------------------------------------------------------------
def _somas(cursor, sql, parametros):
    cursor.execute(sql, parametros)
    return cursor.fetchall()


def resumo_do_periodo(usuario_id, inicio, fim):
    """(total, pago) das contas com vencimento entre `inicio` e `fim` (ISO,
    inclusive), em centavos arredondados. Status não altera o total (5.24)."""
    conexao = conectar()
    try:
        total, pago = conexao.execute(
            """
            SELECT COALESCE(SUM(valor), 0),
                   COALESCE(SUM(CASE WHEN status = 'pago' THEN valor END), 0)
            FROM contas WHERE usuario_id = ? AND data_vencimento BETWEEN ? AND ?
            """,
            (usuario_id, inicio, fim),
        ).fetchone()
    finally:
        conexao.close()
    return round(total, 2), round(pago, 2)


def totais_por_mes(usuario_id, primeiro_ano_mes, ultimo_ano_mes):
    """{"AAAA-MM": total} dos meses com contas no intervalo (inclusive)."""
    conexao = conectar()
    try:
        linhas = _somas(
            conexao.cursor(),
            """
            SELECT substr(data_vencimento, 1, 7), SUM(valor) FROM contas
            WHERE usuario_id = ? AND substr(data_vencimento, 1, 7) BETWEEN ? AND ?
            GROUP BY 1
            """,
            (usuario_id, primeiro_ano_mes, ultimo_ano_mes),
        )
    finally:
        conexao.close()
    return {mes: round(total, 2) for mes, total in linhas}


def totais_por_ano(usuario_id):
    """[(ano, total)] só dos anos com contas registradas, em ordem (5.26)."""
    conexao = conectar()
    try:
        linhas = _somas(
            conexao.cursor(),
            "SELECT substr(data_vencimento, 1, 4), SUM(valor) FROM contas WHERE usuario_id = ? GROUP BY 1 ORDER BY 1",
            (usuario_id,),
        )
    finally:
        conexao.close()
    return [(int(ano), round(total, 2)) for ano, total in linhas]


def anos_com_contas(usuario_id):
    return [ano for ano, _ in totais_por_ano(usuario_id)]


def gastos_por_categoria(usuario_id, inicio, fim):
    """
    RF22: [{categoria_id, nome, icone, cor, total}] das categorias com contas
    no período, pela categoria de cada ocorrência (5.28). Contas sem
    categoria formam o item com `categoria_id` None ("Sem categoria", 5.25).
    Sem ordenação de apresentação (feita na interface).
    """
    conexao = conectar()
    try:
        linhas = _somas(
            conexao.cursor(),
            """
            SELECT c.categoria_id, cat.nome, cat.icone, cat.cor, SUM(c.valor)
            FROM contas c LEFT JOIN categorias cat ON cat.id = c.categoria_id
            WHERE c.usuario_id = ? AND c.data_vencimento BETWEEN ? AND ?
            GROUP BY c.categoria_id
            """,
            (usuario_id, inicio, fim),
        )
    finally:
        conexao.close()
    return [
        {"categoria_id": categoria_id, "nome": nome if categoria_id is not None else "Sem categoria",
         "icone": icone, "cor": cor, "total": round(total, 2)}
        for categoria_id, nome, icone, cor, total in linhas
    ]


def obter_parcela(serie_id, conta_id):
    """
    Posição (X) e total (Y) de uma ocorrência dentro da série (RF26/5.19).
    Etapa 2b: X segue a posição lógica (`contas.posicao`), não o
    vencimento -- uma ocorrência movida com "Somente este mês" mantém a
    própria parcela.

    Série com data de término definida: retorna (posição, total).
    Série sem data de término: retorna (posição, None) -- a ERS proíbe
    exibir um "total" nesse caso, por não haver um número definitivo de
    ocorrências (mostrar "quantas já foram geradas até agora" seria
    enganoso). Quem exibe o texto decide o formato a partir do segundo
    elemento ser ou não None.
    """
    if serie_id is None:
        return None

    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id FROM contas WHERE serie_id = ? ORDER BY posicao, id",
        (serie_id,),
    )
    ids_ordenados = [linha[0] for linha in cursor.fetchall()]

    if conta_id not in ids_ordenados:
        conexao.close()
        return None

    cursor.execute(
        "SELECT data_termino FROM series_recorrencia WHERE id = ?",
        (serie_id,),
    )
    linha_serie = cursor.fetchone()
    conexao.close()

    tem_termino = linha_serie is not None and linha_serie[0] is not None
    posicao = ids_ordenados.index(conta_id) + 1
    total = len(ids_ordenados) if tem_termino else None
    return posicao, total


def obter_info_serie(serie_id):
    """
    Dados de uma série para exibição (frase contextual de recorrência,
    §5.8/RF29 revisado -- D7): frequência, término e se está ativa.
    Somente leitura. Retorna `None` se `serie_id` for `None` ou não
    corresponder a nenhuma série.
    """
    if serie_id is None:
        return None
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT frequencia, data_termino, ativa FROM series_recorrencia WHERE id = ?",
        (serie_id,),
    )
    linha = cursor.fetchone()
    conexao.close()
    if linha is None:
        return None
    frequencia, data_termino, ativa = linha
    return {"frequencia": frequencia, "data_termino": data_termino, "ativa": ativa == 1}


def serie_esta_ativa(serie_id):
    """
    True se `serie_id` existe e está ativa (`series_recorrencia.ativa = 1`);
    False se foi encerrada (RF29 revisado -- `encerrar_recorrencia`, `ativa = 0`) ou
    se `serie_id` não corresponde a nenhuma série -- nos dois casos a
    resposta prática para quem chama é a mesma: não deve ser tratada como
    recorrência em funcionamento (RF27, "Este mês em diante" do RF20,
    geração sob demanda).

    Somente leitura -- não altera nenhum dado.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT ativa FROM series_recorrencia WHERE id = ?", (serie_id,))
    linha = cursor.fetchone()
    conexao.close()
    return linha is not None and linha[0] == 1


def marcar_conta_como_paga(conta_id, data_pagamento=None):
    """
    Marca a ocorrência como paga (RF06/RF24/5.10). Se `data_pagamento` não
    for informada, usa a data atual. Rejeita data de pagamento futura --
    nada é alterado e a função retorna False. Afeta somente esta
    ocorrência: nunca outras da mesma série (5.9/5.1). Retorna True quando
    a alteração é aplicada.
    """
    data_pagamento = data_pagamento or date.today().isoformat()
    if data_pagamento > date.today().isoformat():
        return False

    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "UPDATE contas SET status = 'pago', data_pagamento = ? WHERE id = ?",
        (data_pagamento, conta_id),
    )
    conexao.commit()
    conexao.close()
    return True


def marcar_conta_como_pendente(conta_id):
    """
    Reverte a ocorrência para pendente e limpa `data_pagamento` (RF06/5.10).
    Afeta somente esta ocorrência.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "UPDATE contas SET status = 'pendente', data_pagamento = NULL WHERE id = ?",
        (conta_id,),
    )
    conexao.commit()
    conexao.close()


def editar_data_pagamento(conta_id, nova_data):
    """
    Altera a data de pagamento de uma ocorrência (RF06/5.10). Rejeita data
    futura -- nada é alterado e a função retorna False. Não altera
    `data_vencimento` nem qualquer outra ocorrência da série (5.9/5.1).
    Retorna True quando a alteração é aplicada.
    """
    if nova_data > date.today().isoformat():
        return False

    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "UPDATE contas SET data_pagamento = ? WHERE id = ?",
        (nova_data, conta_id),
    )
    conexao.commit()
    conexao.close()
    return True


def _normalizar_entrada_descricao(descricao, remover_descricao):
    """
    5.22: `(descricao, remover_descricao)` já normalizados. Uma descrição
    informada que fica vazia após o strip é o mesmo que removê-la; a
    remoção explícita tem prioridade sobre um texto informado junto.
    """
    if remover_descricao:
        return None, True
    if descricao is None:
        return None, False  # não enviada: não alterar
    descricao = normalizar_descricao(descricao)
    return descricao, descricao is None


def editar_conta_ocorrencia(conta_id, nome=None, valor=None, categoria_id=None, data_vencimento=None,
                             remover_categoria=False, descricao=None, remover_descricao=False):
    """
    RF20 "Somente este mês" (5.6): altera nome/valor/categoria/data de
    vencimento de uma única ocorrência. Sem restrição de mês/ano — a trava
    do modelo antigo (conta_fixa) não existe mais no v5.0 (seção 9); quem
    determina o que pode mudar é a posição da ocorrência e seu estado, não
    o mês do calendário atual.

    Se a ocorrência pertence a uma série (`serie_id IS NOT NULL`), marca
    `editado_individualmente = 1`: passa a ser histórico protegido contra
    um ajuste mecânico futuro da série (RF27, seção 5.5) — ver o princípio
    geral em 5.1. Para conta avulsa (`serie_id` NULL) o campo não é
    tocado — não há série para a ocorrência "seguir" ou se desviar.

    `None` em `nome`/`valor`/`data_vencimento`/`categoria_id` significa "não
    alterar este campo" (não "limpar" — mesma convenção já usada em
    `editar_categoria`). Como essa convenção não permite distinguir "não
    mexer na categoria" de "remover a categoria" (RF07/5.11 -- ambos
    seriam `categoria_id=None`), `remover_categoria=True` é o sinal
    explícito para o segundo caso -- aplica `categoria_id = NULL` e tem
    prioridade sobre `categoria_id` quando os dois forem informados juntos
    (não deveria acontecer, mas a prioridade evita ambiguidade). Retorna
    False se a conta não existir; True quando a alteração é aplicada
    (inclusive quando nenhum campo foi informado — nada a fazer).

    Descrição (5.22): mesma convenção -- `descricao=None` é "não alterar" e
    `remover_descricao=True` grava NULL. O texto é gravado normalizado
    (strip nas bordas, quebras internas preservadas); uma descrição
    informada que fica vazia equivale a removê-la.

    Limites (5.23): só `nome`/`descricao` efetivamente enviados são
    validados, antes de qualquer gravação (`LimiteDeCaracteresError`);
    valores antigos não enviados nunca são revalidados nem cortados (P4).
    """
    descricao, remover_descricao = _normalizar_entrada_descricao(descricao, remover_descricao)
    _validar_textos_conta(nome, descricao)

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT serie_id FROM contas WHERE id = ?", (conta_id,))
    linha = cursor.fetchone()
    if linha is None:
        conexao.close()
        return False
    serie_id = linha[0]

    campos, valores = [], []
    if nome is not None:
        campos.append("nome = ?")
        valores.append(nome)
    if valor is not None:
        campos.append("valor = ?")
        valores.append(valor)
    if remover_categoria:
        campos.append("categoria_id = NULL")
    elif categoria_id is not None:
        campos.append("categoria_id = ?")
        valores.append(categoria_id)
    if data_vencimento is not None:
        campos.append("data_vencimento = ?")
        valores.append(data_vencimento)
    if remover_descricao:
        campos.append("descricao = NULL")
    elif descricao is not None:
        campos.append("descricao = ?")
        valores.append(descricao)
    if serie_id is not None and campos:
        campos.append("editado_individualmente = 1")

    if campos:
        sql = f"UPDATE contas SET {', '.join(campos)} WHERE id = ?"
        cursor.execute(sql, (*valores, conta_id))
        conexao.commit()
    conexao.close()
    return True


MENSAGEM_VENCIMENTO_ANTES_DA_PARCELA_ANTERIOR = (
    "Para alterar esta conta e as próximas, escolha um mês posterior ao da parcela anterior."
)


class VencimentoAntesDaParcelaAnteriorError(ValueError):
    """
    D5 (Etapa 2b): "Este mês em diante" com um novo vencimento cuja
    competência não é posterior à VAGA (`data_prevista`) da ocorrência
    imediatamente anterior na série. Recusado antes de qualquer gravação.
    """

    def __init__(self):
        super().__init__(MENSAGEM_VENCIMENTO_ANTES_DA_PARCELA_ANTERIOR)


def editar_conta_serie(conta_id, nome=None, valor=None, categoria_id=None, data_vencimento=None,
                        remover_categoria=False, descricao=None, remover_descricao=False):
    """
    RF20 "Este mês em diante" (5.6): aplica nome/valor/categoria/data à
    ocorrência selecionada e às futuras da mesma série (posição lógica >=
    a da selecionada -- Etapa 2b; nunca pelo vencimento real) — INCLUSIVE
    ocorrências já editadas individualmente (`editado_individualmente=1`)
    ou já pagas. Decisão fechada da ERS (5.1): "Este mês em diante" é uma
    ação deliberada do usuário sobre a série no escopo que ele escolheu, e
    continua se aplicando à selecionada e às futuras exatamente como
    definido — a proteção de `editado_individualmente` só vale contra um
    ajuste MECÂNICO de outra operação (RF27, seção 5.5), nunca contra este
    escopo. `status` e `data_pagamento` nunca são tocados, para nenhuma
    ocorrência (5.9) — não fazem parte do que esta função altera.

    nome/valor/categoria são copiados literalmente para as ocorrências
    afetadas e para o "modelo" da série (`series_recorrencia`), para que
    ocorrências futuras ainda não geradas já nasçam com o novo padrão
    (9.3). Só campos realmente alterados em relação à ocorrência
    selecionada são propagados: um campo informado com o mesmo valor que
    ela já tem é ignorado (correção v6.0, Etapa 0).

    data_vencimento redefine a âncora da série a partir desta ocorrência
    (9.3): a ocorrência selecionada recebe exatamente a data informada (e
    essa passa a ser a sua vaga), e as futuras que ocupam vagas da grade
    atual -- a mesma quantidade -- são recalculadas
    em sequência a partir da nova âncora (dia/mês) e da frequência atual
    da série, sem arrasto (mesmo mecanismo de `_somar_mes`/`_somar_ano`
    usado na geração — seção 5.2). `dia_ancora`/`mes_ancora`/`data_inicio`
    da série são atualizados de acordo, `posicao_ancora` passa a ser a
    posição da selecionada e `horizonte_gerado_ate` a última vaga da nova
    sequência. D2: editadas preservadas fora da grade (outro mês numa série
    anual, ou além do término -- D4) mantêm data e vaga, e a sequência pula
    as competências que elas ocupam.
    D5: um novo vencimento cuja competência não seja posterior à vaga da
    ocorrência imediatamente anterior levanta
    `VencimentoAntesDaParcelaAnteriorError` antes de qualquer gravação
    (nenhum campo é alterado). Na primeira ocorrência não há limite.
    Se a série tem `data_termino` e a reorganização ultrapassaria esse
    limite, a chamada inteira é rejeitada (nada é alterado) e a função
    retorna False.

    `remover_categoria=True` (RF07/5.11) aplica `categoria_id = NULL` tanto
    às ocorrências afetadas quanto ao "modelo" da série, com prioridade
    sobre `categoria_id` -- mesma convenção de `editar_conta_ocorrencia`.

    Descrição (5.6/5.22, P3): `descricao`/`remover_descricao` seguem a mesma
    convenção de `editar_conta_ocorrencia` (normalizada; vazia = remover) e
    entram na mesma regra de "só o que mudou": adicionar, alterar ou
    remover a descrição da ocorrência selecionada é aplicado a ela, às
    futuras e ao modelo, de onde `gerar_ocorrencias_sob_demanda` a copia.

    Limites (5.23): validados DEPOIS do descarte dos campos iguais aos da
    ocorrência selecionada -- um nome antigo acima do limite que não foi
    alterado nunca bloqueia a edição de outro campo (P4). Acima do limite,
    levanta `LimiteDeCaracteresError` antes de qualquer gravação.

    Conta avulsa (`serie_id` NULL): delega para `editar_conta_ocorrencia`
    (CT40 — sem diálogo de escopo, edição direta).

    Série inativa (`ativa = 0`, encerrada via RF29 -- `encerrar_recorrencia`):
    a chamada é rejeitada (nada é alterado), mesmo contrato de retorno já
    usado para "reorganização ultrapassaria o término" -- False, sem
    exceção. RF29 (5.8) encerra o ajuste mecânico da série; sem esta
    checagem, "Este mês em diante" continuaria reorganizando âncora/datas
    de uma série que o usuário já havia removido. A rejeição acontece
    antes de qualquer UPDATE/DELETE/INSERT.

    Operação transacional: qualquer falha reverte tudo (ROLLBACK). Retorna
    True quando aplicada, False se rejeitada (conta inexistente, série
    inativa, ou reorganização ultrapassaria o término).
    """
    conexao_leitura = conectar()
    cursor_leitura = conexao_leitura.cursor()
    cursor_leitura.execute(
        """
        SELECT serie_id, data_vencimento, nome, valor, categoria_id, descricao, posicao
        FROM contas WHERE id = ?
        """,
        (conta_id,),
    )
    linha = cursor_leitura.fetchone()
    if linha is None:
        conexao_leitura.close()
        return False
    (serie_id, data_referencia, nome_atual, valor_atual, categoria_id_atual, descricao_atual,
     posicao_referencia) = linha
    descricao, remover_descricao = _normalizar_entrada_descricao(descricao, remover_descricao)

    # Correção v6.0 (Etapa 0): só propaga o que o usuário realmente alterou
    # em relação à ocorrência selecionada. Um campo repetido com o mesmo
    # valor é tratado como "não alterar": a data repetida não redefine a
    # âncora (5.2, "sem arrasto" -- ex.: 28/02 numa série de âncora 31), e
    # nome/valor/categoria repetidos não sobrescrevem ocorrências futuras
    # que tenham valores próprios (editadas individualmente).
    if nome == nome_atual:
        nome = None
    if valor == valor_atual:
        valor = None
    if data_vencimento == data_referencia:
        data_vencimento = None
    if remover_categoria and categoria_id_atual is None:
        remover_categoria = False
    if not remover_categoria and categoria_id == categoria_id_atual:
        categoria_id = None
    if remover_descricao and descricao_atual is None:
        remover_descricao = False
    if descricao is not None and descricao == descricao_atual:
        descricao = None

    try:
        _validar_textos_conta(nome, descricao)
    except LimiteDeCaracteresError:
        conexao_leitura.close()
        raise

    if serie_id is None:
        conexao_leitura.close()
        return editar_conta_ocorrencia(conta_id, nome=nome, valor=valor,
                                        categoria_id=categoria_id, data_vencimento=data_vencimento,
                                        remover_categoria=remover_categoria,
                                        descricao=descricao, remover_descricao=remover_descricao)

    cursor_leitura.execute(
        "SELECT frequencia, data_termino, ativa, mes_ancora FROM series_recorrencia WHERE id = ?",
        (serie_id,),
    )
    frequencia, data_termino, ativa, mes_ancora_atual = cursor_leitura.fetchone()
    if ativa == 0:
        conexao_leitura.close()
        return False

    # D5: o novo vencimento precisa cair numa competência posterior à VAGA
    # da ocorrência imediatamente anterior (não ao vencimento real dela, que
    # pode ter sido movido). Sem anterior (primeira ocorrência), sem limite.
    if data_vencimento is not None:
        cursor_leitura.execute(
            "SELECT data_prevista FROM contas WHERE serie_id = ? AND posicao < ? "
            "ORDER BY posicao DESC LIMIT 1",
            (serie_id, posicao_referencia),
        )
        anterior = cursor_leitura.fetchone()
        if anterior is not None and _competencia(data_vencimento) <= _competencia(anterior[0]):
            conexao_leitura.close()
            raise VencimentoAntesDaParcelaAnteriorError()

    # Etapa 2b: "futuras" = posição lógica maior que a da selecionada (não
    # o vencimento real), em ordem de posição.
    cursor_leitura.execute(
        """
        SELECT id, data_prevista, editado_individualmente FROM contas
        WHERE serie_id = ? AND posicao > ?
        ORDER BY posicao
        """,
        (serie_id, posicao_referencia),
    )
    ocorrencias_futuras = cursor_leitura.fetchall()
    conexao_leitura.close()

    novas_datas_por_id = None
    dia_ancora_novo = mes_ancora_novo = None
    horizonte_novo = None
    if data_vencimento is not None:
        data_nova = date.fromisoformat(data_vencimento)
        dia_ancora_novo, mes_ancora_novo = data_nova.day, data_nova.month
        avancar = (
            (lambda ano, mes: _somar_mes(ano, mes, dia_ancora_novo))
            if frequencia == "mensal"
            else (lambda ano, mes: _somar_ano(ano, mes_ancora_novo, dia_ancora_novo))
        )
        # D2: as futuras são resequenciadas, exceto as EDITADAS preservadas
        # fora da grade atual (outro mês numa série anual, ou além do
        # término -- D4), que mantêm data e vaga; a nova sequência pula as
        # competências que elas ocupam. Uma não editada é sempre mecânica
        # e sempre resequenciada, mesmo vinda de um bloco antigo da grade
        # (ex.: meses de antes de uma mudança mensal -> anual) -- C3.
        da_grade = [oc_id for oc_id, prevista, editado in ocorrencias_futuras
                    if not editado or _vaga_na_grade(prevista, frequencia, mes_ancora_atual, data_termino)]
        ocupadas_fora_da_grade = {
            _competencia(prevista) for oc_id, prevista, _ in ocorrencias_futuras if oc_id not in da_grade
        }
        novas_datas = []
        ultima = data_vencimento
        while len(novas_datas) < len(da_grade):
            ano_atual, mes_atual, _ = map(int, ultima.split("-"))
            ultima = avancar(ano_atual, mes_atual)
            if _competencia(ultima) not in ocupadas_fora_da_grade:
                novas_datas.append(ultima)
        horizonte_novo = novas_datas[-1] if novas_datas else data_vencimento

        if data_termino is not None and _competencia(horizonte_novo) > data_termino:
            return False

        novas_datas_por_id = {conta_id: data_vencimento}
        novas_datas_por_id.update(zip(da_grade, novas_datas))

    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
    conexao.execute("PRAGMA foreign_keys = ON;")
    cursor = conexao.cursor()
    try:
        cursor.execute("BEGIN;")

        campos, valores = [], []
        if nome is not None:
            campos.append("nome = ?"); valores.append(nome)
        if valor is not None:
            campos.append("valor = ?"); valores.append(valor)
        if remover_categoria:
            campos.append("categoria_id = NULL")
        elif categoria_id is not None:
            campos.append("categoria_id = ?"); valores.append(categoria_id)
        if remover_descricao:
            campos.append("descricao = NULL")
        elif descricao is not None:
            campos.append("descricao = ?"); valores.append(descricao)
        if campos:
            sql = f"UPDATE contas SET {', '.join(campos)} WHERE serie_id = ? AND posicao >= ?"
            cursor.execute(sql, (*valores, serie_id, posicao_referencia))

        if novas_datas_por_id is not None:
            for oc_id, nova_data in novas_datas_por_id.items():
                cursor.execute(
                    "UPDATE contas SET data_vencimento = ?, data_prevista = ? WHERE id = ?",
                    (nova_data, nova_data, oc_id),
                )
            _renumerar_segmento(cursor, serie_id, posicao_referencia)

        campos_serie, valores_serie = [], []
        if nome is not None:
            campos_serie.append("nome = ?"); valores_serie.append(nome)
        if valor is not None:
            campos_serie.append("valor = ?"); valores_serie.append(valor)
        if remover_categoria:
            campos_serie.append("categoria_id = NULL")
        elif categoria_id is not None:
            campos_serie.append("categoria_id = ?"); valores_serie.append(categoria_id)
        if remover_descricao:
            campos_serie.append("descricao = NULL")
        elif descricao is not None:
            campos_serie.append("descricao = ?"); valores_serie.append(descricao)
        if data_vencimento is not None:
            campos_serie.append("dia_ancora = ?"); valores_serie.append(dia_ancora_novo)
            campos_serie.append("mes_ancora = ?")
            valores_serie.append(mes_ancora_novo if frequencia == "anual" else None)
            campos_serie.append("data_inicio = ?"); valores_serie.append(data_vencimento)
            campos_serie.append("posicao_ancora = ?"); valores_serie.append(posicao_referencia)
            campos_serie.append("horizonte_gerado_ate = ?"); valores_serie.append(horizonte_novo)
        if campos_serie:
            sql = f"UPDATE series_recorrencia SET {', '.join(campos_serie)} WHERE id = ?"
            cursor.execute(sql, (*valores_serie, serie_id))


        cursor.execute("COMMIT;")
    except Exception:
        cursor.execute("ROLLBACK;")
        raise
    finally:
        conexao.close()

    return True


def alterar_frequencia_serie(conta_id, nova_frequencia, data_termino=None):
    """
    RF27 (5.5): altera a frequência de uma série a partir da ocorrência
    selecionada, que passa a ser a nova âncora.

    Etapa 2b: anteriores/futuras pela posição lógica (`contas.posicao`),
    nunca pelo vencimento real.

    - Ocorrências anteriores à selecionada: nunca tocadas.
    - A ocorrência selecionada em si: não é alterada (nem a vaga) -- só a
      configuração da série muda a partir dela.
    - D1, variante "d": o dia (e o mês, se anual) da nova grade vêm do
      vencimento real da selecionada, mas as novas vagas começam na
      competência seguinte à VAGA dela (`_grade_a_partir_da_vaga`) -- uma
      selecionada movida para antes do histórico não gera vagas por cima
      das anteriores.
    - Ocorrências futuras que ainda seguem
      o padrão mecânico da série (`editado_individualmente = 0`) são
      substituídas: removidas e regeradas sob a nova frequência e o novo
      término, a partir da nova âncora (sem arrasto —
      `_somar_mes`/`_somar_ano`).
    - Ocorrências futuras já editadas individualmente
      (`editado_individualmente = 1`): preservadas, nunca substituídas —
      exceção fechada em 5.1/5.5, independente do novo término escolhido
      (D4: além do término continuam existindo e contando). Cada uma
      ocupa a própria vaga: a nova grade não cria outra ocorrência na
      mesma competência prevista.
    - `status` e `data_pagamento` nunca são tocados, para nenhuma
      ocorrência (5.9).
    - As ocorrências regeneradas copiam o modelo da série (nome, valor,
      categoria e descrição); o modelo não é alterado por esta função.
    - `series_recorrencia.frequencia/dia_ancora/mes_ancora/data_inicio/
      data_termino/posicao_ancora` são atualizados para refletir a nova
      configuração; `horizonte_gerado_ate` é a última vaga da nova grade
      -- nunca uma preservada distante, que faria a geração sob demanda
      saltar períodos (E3).

    Fase D5 (decisão de produto): `data_termino` ("AAAA-MM" ou `None`) é
    uma escolha nova e explícita do usuário a cada alteração de
    frequência -- o término anterior da série NUNCA é preservado
    automaticamente. `None` = a série passa a ser sem término (aberta,
    sujeita à geração sob demanda — 5.20). Reaproveita
    `_gerar_datas_ocorrencias` (a mesma função usada por
    `criar_serie_recorrente`/`transformar_em_recorrente`) para não
    duplicar a regra de horizonte: geração integral até o término quando
    informado, ou 12 meses a partir da nova âncora quando aberta (5.3).
    Isso substitui o comportamento anterior (Fase 3.8), que reaproveitava
    cegamente o `horizonte_gerado_ate` antigo como teto -- o que podia
    deixar uma série com término travada permanentemente quando a nova
    frequência não coubesse mais nenhuma vez antes do término antigo
    (bug identificado na auditoria pós-Fase-3, item D3).

    Operação transacional: qualquer falha reverte tudo (ROLLBACK). Retorna
    um dicionário com os ids afetados. Levanta ValueError se `conta_id`
    não existir, não pertencer a nenhuma série, a série estiver inativa
    (encerrada via RF29 -- `encerrar_recorrencia`), ou `nova_frequencia` for
    inválida.

    Fase de correção D2 (série inativa): RF29 (5.8) encerra o ajuste
    mecânico de uma série -- "a série deixa de gerar novas ocorrências".
    Sem esta checagem, uma série já removida (`ativa = 0`) ainda podia ter
    sua âncora/frequência reescritas e suas ocorrências futuras não
    editadas individualmente substituídas, contradizendo RF29. A rejeição
    acontece antes de qualquer UPDATE/DELETE/INSERT -- nada é tocado numa
    tentativa contra série inativa.
    """
    if nova_frequencia not in ("mensal", "anual"):
        raise ValueError(f"frequencia inválida: {nova_frequencia!r} (use 'mensal' ou 'anual')")

    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
    conexao.execute("PRAGMA foreign_keys = ON;")
    cursor = conexao.cursor()
    try:
        cursor.execute(
            "SELECT serie_id, data_vencimento, posicao, data_prevista FROM contas WHERE id = ?", (conta_id,)
        )
        linha = cursor.fetchone()
        if linha is None:
            raise ValueError(f"conta com id={conta_id} não existe")
        serie_id, referencia, posicao_referencia, vaga_referencia = linha
        if serie_id is None:
            raise ValueError("RF27 não se aplica a conta avulsa (sem série)")

        cursor.execute(
            """
            SELECT usuario_id, nome, valor, categoria_id, ativa, descricao
            FROM series_recorrencia WHERE id = ?
            """,
            (serie_id,),
        )
        usuario_id, nome_serie, valor_serie, categoria_id_serie, ativa, descricao_serie = cursor.fetchone()
        if ativa == 0:
            raise ValueError(
                f"série id={serie_id} não está ativa -- recorrência já removida (RF29), "
                "não é possível alterar sua frequência"
            )

        data_referencia = date.fromisoformat(referencia)
        dia_ancora_novo = data_referencia.day
        mes_ancora_novo = data_referencia.month if nova_frequencia == "anual" else None
        data_inicio_nova, novas_datas = _grade_a_partir_da_vaga(
            nova_frequencia, dia_ancora_novo, mes_ancora_novo, vaga_referencia, data_termino,
        )

        # Etapa 2b: futuras pela posição lógica, não pelo vencimento real.
        cursor.execute(
            "SELECT id, editado_individualmente FROM contas WHERE serie_id = ? AND posicao > ?",
            (serie_id, posicao_referencia),
        )
        futuras = cursor.fetchall()
        substituiveis = [oc_id for oc_id, editado in futuras if editado == 0]
        preservadas = [oc_id for oc_id, editado in futuras if editado == 1]

        try:
            cursor.execute("BEGIN;")

            if substituiveis:
                placeholders = ",".join("?" * len(substituiveis))
                cursor.execute(f"DELETE FROM contas WHERE id IN ({placeholders})", substituiveis)

            # Uma editada preservada ocupa a própria vaga: a nova grade não
            # cria outra ocorrência na mesma competência prevista (E1/E2).
            ocupadas = _competencias_ocupadas(cursor, serie_id, posicao_referencia)
            ids_novos = [
                _inserir_ocorrencia(cursor, usuario_id, categoria_id_serie, serie_id, nome_serie,
                                    valor_serie, nova_data, descricao_serie)
                for nova_data in novas_datas
                if _competencia(nova_data) not in ocupadas
            ]
            _renumerar_segmento(cursor, serie_id, posicao_referencia)

            cursor.execute(
                """
                UPDATE series_recorrencia
                SET frequencia = ?, dia_ancora = ?, mes_ancora = ?, data_inicio = ?, data_termino = ?,
                    horizonte_gerado_ate = ?, posicao_ancora = ?
                WHERE id = ?
                """,
                (nova_frequencia, dia_ancora_novo, mes_ancora_novo, data_inicio_nova, data_termino,
                 novas_datas[-1] if novas_datas else data_inicio_nova, posicao_referencia, serie_id),
            )

            cursor.execute("COMMIT;")
        except Exception:
            cursor.execute("ROLLBACK;")
            raise
    finally:
        conexao.close()

    return {
        "serie_id": serie_id,
        "ocorrencias_substituidas": substituiveis,
        "ocorrencias_preservadas": preservadas,
        "ocorrencias_novas": ids_novos,
    }


def editar_categoria(usuario_id, categoria_id, nome=None, icone=None, cor=None):
    """
    Atualiza nome/ícone/cor de uma categoria (RF18/5.13). Isolamento
    entre usuários: só altera se `categoria_id` pertencer a `usuario_id`
    -- retorna False caso contrário (a categoria de um usuário não pode
    ser alterada por outro).

    Se `cor` for informada, deve estar livre entre as OUTRAS categorias
    do mesmo usuário -- caso contrário a chamada é rejeitada (nada é
    alterado) e a função levanta ValueError. Trocar a cor libera a
    anterior automaticamente (5.13): assim que a linha é atualizada, a
    cor antiga deixa de estar em uso por qualquer categoria, sem
    nenhuma ação extra necessária.

    `nome`, quando informado, tem no máximo 30 caracteres (5.23) --
    acima disso levanta `LimiteDeCaracteresError` sem alterar nada. Um
    nome antigo não informado (`None`) nunca é revalidado.

    Operação transacional. Retorna True quando a alteração é aplicada
    (inclusive quando nenhum campo foi informado).
    """
    if nome is not None:
        validar_limite("nome_categoria", nome, LIMITE_NOME_CATEGORIA)
    _recusar_cor_reservada(cor)

    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
    conexao.execute("PRAGMA foreign_keys = ON;")
    cursor = conexao.cursor()
    try:
        cursor.execute(
            "SELECT id FROM categorias WHERE id = ? AND usuario_id = ?",
            (categoria_id, usuario_id),
        )
        if cursor.fetchone() is None:
            return False

        if cor is not None:
            cursor.execute(
                "SELECT COUNT(*) FROM categorias WHERE usuario_id = ? AND cor = ? AND id != ?",
                (usuario_id, cor, categoria_id),
            )
            if cursor.fetchone()[0] > 0:
                raise ValueError(f"cor {cor!r} já está em uso por outra categoria deste usuário")

        campos, valores = [], []
        if nome is not None:
            campos.append("nome = ?"); valores.append(nome)
        if icone is not None:
            campos.append("icone = ?"); valores.append(icone)
        if cor is not None:
            campos.append("cor = ?"); valores.append(cor)

        if campos:
            try:
                cursor.execute("BEGIN;")
                sql = f"UPDATE categorias SET {', '.join(campos)} WHERE id = ?"
                cursor.execute(sql, (*valores, categoria_id))
                cursor.execute("COMMIT;")
            except Exception:
                cursor.execute("ROLLBACK;")
                raise
    finally:
        conexao.close()

    return True


def excluir_categoria(usuario_id, categoria_id):
    """
    Exclui uma categoria do usuário informado (RF14/5.11). Contas
    associadas NÃO são excluídas: passam a ficar sem categoria
    (`categoria_id = NULL`). Séries recorrentes associadas também ficam
    sem categoria, para que ocorrências futuras geradas por elas
    (`gerar_ocorrencias_sob_demanda`) não voltem a herdar a categoria
    excluída. A cor da categoria excluída volta a ficar disponível
    automaticamente (5.13) -- basta a linha deixar de existir.

    Isolamento entre usuários: só exclui se `categoria_id` pertencer a
    `usuario_id` -- retorna False caso contrário. Operação transacional.
    Retorna True quando a exclusão é aplicada.
    """
    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
    conexao.execute("PRAGMA foreign_keys = ON;")
    cursor = conexao.cursor()
    try:
        cursor.execute(
            "SELECT id FROM categorias WHERE id = ? AND usuario_id = ?",
            (categoria_id, usuario_id),
        )
        if cursor.fetchone() is None:
            return False

        try:
            cursor.execute("BEGIN;")
            cursor.execute("UPDATE contas SET categoria_id = NULL WHERE categoria_id = ?", (categoria_id,))
            cursor.execute("UPDATE series_recorrencia SET categoria_id = NULL WHERE categoria_id = ?", (categoria_id,))
            cursor.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))
            cursor.execute("COMMIT;")
        except Exception:
            cursor.execute("ROLLBACK;")
            raise
    finally:
        conexao.close()

    return True


def excluir_conta(conta_id):
    """
    RF08 "Somente este mês" (5.7): exclui APENAS esta ocorrência. Nenhuma
    outra ocorrência da mesma série é tocada, passada ou futura. Funciona
    mesmo quando a ocorrência é a primeira da série — a limitação do
    modelo antigo (serie_id autorreferenciado, seção 9.1) não existe mais:
    `contas.serie_id` aponta para `series_recorrencia`, nunca para outra
    linha de `contas`, então não há mais FK para quebrar.

    Se a ocorrência excluída pertencia a uma série:
      - se ainda restar ao menos uma ocorrência da série,
        `horizonte_gerado_ate` NÃO muda (Etapa 2b): ele é a última vaga que
        a grade já gerou, não a maior vaga restante. Assim a vaga excluída
        fica vazia de vez (excluir a última gerada não a faz ser recriada
        ao navegar -- C2), as seguintes continuam sendo geradas, e uma
        editada preservada muito além da grade não faz o horizonte saltar
        competências (C1);
      - se não restar nenhuma ocorrência, o próprio registro em
        `series_recorrencia` é removido junto — sem ocorrências, não há
        mais nada para a série rastrear.

    Retorna False se a conta não existir; True quando a exclusão é
    aplicada. Operação transacional.
    """
    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
    conexao.execute("PRAGMA foreign_keys = ON;")
    cursor = conexao.cursor()
    try:
        cursor.execute("SELECT serie_id FROM contas WHERE id = ?", (conta_id,))
        linha = cursor.fetchone()
        if linha is None:
            return False
        serie_id = linha[0]

        try:
            cursor.execute("BEGIN;")
            cursor.execute("DELETE FROM contas WHERE id = ?", (conta_id,))

            if serie_id is not None:
                cursor.execute("SELECT 1 FROM contas WHERE serie_id = ? LIMIT 1", (serie_id,))
                if cursor.fetchone() is None:
                    cursor.execute("DELETE FROM series_recorrencia WHERE id = ?", (serie_id,))

            cursor.execute("COMMIT;")
        except Exception:
            cursor.execute("ROLLBACK;")
            raise
    finally:
        conexao.close()

    return True


def excluir_conta_serie(conta_id):
    """
    RF08 "Este mês em diante" (5.7): exclui a ocorrência selecionada e
    todas as futuras da mesma série (posição lógica >= a da selecionada,
    Etapa 2b -- não o vencimento real).
    Ocorrências anteriores permanecem no histórico. Sem exceção para
    ocorrências já pagas ou editadas individualmente dentro do trecho
    excluído — a ERS (5.7) não prevê nenhuma proteção nesse sentido para
    exclusão (diferente da edição, RF20/RF27, onde `editado_individualmente`
    protege contra RF27): "Este mês em diante" aqui é definido sem
    ressalvas, exclui tudo dali pra frente.

    Funciona mesmo quando a ocorrência selecionada é a primeira da série
    (CT15): nesse caso todas as ocorrências desaparecem e o próprio
    registro em `series_recorrencia` é removido junto — "a série inteira
    é removida", sem erro de integridade referencial. Quando restam
    ocorrências anteriores à referência, a série persiste e
    `horizonte_gerado_ate` é recalculado para a última ocorrência que de
    fato permanece.

    Fase 3.10 (fecho de arquitetura): se a série sobrevive à exclusão e
    era sem término (`data_termino IS NULL`), `data_termino` passa a ser
    definido como o mês/ano da última ocorrência que restou. Sem isso,
    `horizonte_gerado_ate` sozinho não distingue "nunca gerado" de
    "gerado e depois excluído por decisão explícita do usuário" — uma
    chamada futura de `gerar_ocorrencias_sob_demanda` (5.20) recriaria,
    a partir do novo horizonte mais baixo, exatamente as ocorrências que
    "Este mês em diante" acabou de remover. Fechar a série no ponto onde
    ela de fato termina agora reaproveita um mecanismo já existente e já
    coberto por teste (`gerar_ocorrencias_sob_demanda` já recusa gerar
    quando `data_termino is not None`) — não introduz nenhum campo ou
    conceito novo. Não é o mesmo que RF29 revisado (`encerrar_recorrencia`,
    seção 5.8): esta função (RF08) exclui a partir da própria ocorrência
    selecionada (`>=`), sem nenhuma proteção para ocorrências pagas ou
    editadas individualmente; `encerrar_recorrencia` preserva a ocorrência
    selecionada e tudo que já aconteceu, removendo só o que ainda não se
    realizou, com proteção explícita para ocorrências pagas/editadas.
    Séries que já tinham `data_termino` não são alteradas.

    Conta avulsa (`serie_id` NULL): exclui diretamente, sem efeito em
    nenhuma série.

    Retorna False se a conta não existir; True quando a exclusão é
    aplicada. Operação transacional.
    """
    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
    conexao.execute("PRAGMA foreign_keys = ON;")
    cursor = conexao.cursor()
    try:
        cursor.execute("SELECT serie_id, posicao FROM contas WHERE id = ?", (conta_id,))
        linha = cursor.fetchone()
        if linha is None:
            return False
        serie_id, posicao_referencia = linha

        try:
            cursor.execute("BEGIN;")

            if serie_id is None:
                cursor.execute("DELETE FROM contas WHERE id = ?", (conta_id,))
            else:
                cursor.execute(
                    "SELECT data_termino FROM series_recorrencia WHERE id = ?", (serie_id,)
                )
                (termino_atual,) = cursor.fetchone()

                # Etapa 2b: "daqui em diante" pela posição lógica -- uma
                # ocorrência anterior com o vencimento movido para depois
                # da selecionada é preservada.
                cursor.execute(
                    "DELETE FROM contas WHERE serie_id = ? AND posicao >= ?",
                    (serie_id, posicao_referencia),
                )
                cursor.execute(
                    "SELECT MAX(data_prevista) FROM contas WHERE serie_id = ?", (serie_id,)
                )
                novo_horizonte = cursor.fetchone()[0]
                if novo_horizonte is None:
                    cursor.execute("DELETE FROM series_recorrencia WHERE id = ?", (serie_id,))
                else:
                    # Série era sem término: fecha-a no mês/ano da última ocorrência
                    # que restou, para que gerar_ocorrencias_sob_demanda nunca mais
                    # recrie o que "Este mês em diante" acabou de excluir (ver
                    # docstring). Série que já tinha término fica como estava.
                    novo_termino = termino_atual if termino_atual is not None else novo_horizonte[:7]
                    cursor.execute(
                        """
                        UPDATE series_recorrencia
                        SET horizonte_gerado_ate = ?, data_termino = ?
                        WHERE id = ?
                        """,
                        (novo_horizonte, novo_termino, serie_id),
                    )

            cursor.execute("COMMIT;")
        except Exception:
            cursor.execute("ROLLBACK;")
            raise
    finally:
        conexao.close()

    return True


def encerrar_recorrencia(conta_id):
    """
    RF29 revisado (5.8, decisão D7): encerra a recorrência de uma série a
    partir da ocorrência selecionada (`conta_id`) -- a série para de gerar
    novas ocorrências (`ativa = 0`) e as ocorrências que ainda não se
    realizaram são removidas, mas **tudo que já aconteceu é preservado**.

    Substitui o antigo "Remover recorrência" (que nunca excluía nenhuma
    ocorrência). A regra fundamental é nunca apagar histórico: o corte
    usado para decidir o que remover é sempre o **maior** entre a data da
    ocorrência selecionada e a data atual --
    `corte = max(data_vencimento da ocorrência selecionada, hoje)` (5.8),
    aplicado só às ocorrências POSTERIORES à selecionada na posição lógica
    (Etapa 2b) -- uma anterior com o vencimento movido nunca é removida:

    - se a ocorrência selecionada é passada (ex.: hoje é setembro/2026 e o
      usuário está editando março/2026), o corte vira "hoje" -- tudo até
      setembro/2026, inclusive o que aconteceu entre março e setembro,
      permanece; só outubro/2026 em diante é removido;
    - se a ocorrência selecionada é futura (ainda não chegou), o corte é a
      própria ocorrência -- ela e tudo antes dela permanecem, só o que vem
      estritamente depois é removido.
    Em ambos os casos, a ocorrência selecionada nunca é removida.

    Proteção adicional (defensiva, sem pedir nada extra ao usuário):
    ocorrências que estariam no intervalo removido, mas que já carregam
    informação histórica relevante -- `status = 'pago'`, `data_pagamento`
    preenchida, ou `editado_individualmente = 1` -- são preservadas em vez
    de apagadas silenciosamente.

    `series_recorrencia.ativa = 0` já é respeitado por
    `gerar_ocorrencias_sob_demanda`, que se recusa a gerar qualquer
    ocorrência nova para uma série inativa -- nenhuma mudança adicional
    foi necessária ali. Pelo mesmo motivo, `alterar_frequencia_serie` e
    `editar_conta_serie` ("este mês em diante") já rejeitam série
    inativa -- uma série encerrada não pode mais ser mecanicamente
    ajustada.

    `horizonte_gerado_ate` é recalculado como o maior `data_vencimento`
    realmente restante na série (nunca `NULL`, pois a ocorrência
    selecionada e tudo até o corte sempre permanecem).

    Operação transacional. Levanta ValueError se `conta_id` não existir,
    não pertencer a nenhuma série (conta avulsa), ou a série já estiver
    encerrada.
    """
    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.isolation_level = None  # controle explícito de transação (BEGIN/COMMIT/ROLLBACK)
    conexao.execute("PRAGMA foreign_keys = ON;")
    cursor = conexao.cursor()
    try:
        cursor.execute("SELECT serie_id, data_vencimento, posicao FROM contas WHERE id = ?", (conta_id,))
        linha = cursor.fetchone()
        if linha is None:
            raise ValueError(f"conta com id={conta_id} não existe")
        serie_id, referencia, posicao_referencia = linha
        if serie_id is None:
            raise ValueError("RF29 não se aplica a conta avulsa (sem série)")

        cursor.execute("SELECT ativa FROM series_recorrencia WHERE id = ?", (serie_id,))
        linha_serie = cursor.fetchone()
        if linha_serie is None:
            raise ValueError(f"series_recorrencia com id={serie_id} não existe")
        if linha_serie[0] == 0:
            raise ValueError(f"série id={serie_id} já está encerrada")

        corte = max(referencia, date.today().isoformat())

        try:
            cursor.execute("BEGIN;")

            cursor.execute(
                """
                DELETE FROM contas
                WHERE serie_id = ?
                  AND posicao > ?
                  AND data_vencimento > ?
                  AND status != 'pago'
                  AND data_pagamento IS NULL
                  AND editado_individualmente = 0
                """,
                (serie_id, posicao_referencia, corte),
            )
            ocorrencias_removidas = cursor.rowcount

            cursor.execute("SELECT MAX(data_prevista) FROM contas WHERE serie_id = ?", (serie_id,))
            novo_horizonte = cursor.fetchone()[0]

            cursor.execute(
                "UPDATE series_recorrencia SET ativa = 0, horizonte_gerado_ate = ? WHERE id = ?",
                (novo_horizonte, serie_id),
            )

            cursor.execute("COMMIT;")
        except Exception:
            cursor.execute("ROLLBACK;")
            raise
    finally:
        conexao.close()

    return {"serie_id": serie_id, "ocorrencias_removidas": ocorrencias_removidas}


if __name__ == "__main__":
    criar_tabelas()
    print("Tabelas criadas (ou já existiam): usuarios, categorias, contas.")
