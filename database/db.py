"""
database.py — Camada de banco de dados do Sino (v2)
"""

import sqlite3
import hashlib
import os
import shutil
from datetime import date, datetime, timedelta
from calendar import monthrange

NOME_DO_BANCO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sino.db")
PASTA_BACKUPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")


def conectar():
    conexao = sqlite3.connect(NOME_DO_BANCO)
    conexao.execute("PRAGMA foreign_keys = ON;")
    return conexao


def criar_tabelas():
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            termos_aceitos_em TEXT NOT NULL
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

    conexao.commit()
    conexao.close()


def criar_backup(caminho_banco=None):
    """
    Copia o arquivo do banco para database/backups/ com timestamp no nome,
    antes de qualquer migração destrutiva de schema. Retorna o caminho do
    backup criado, ou None se o arquivo do banco ainda não existir.
    """
    caminho_banco = caminho_banco or NOME_DO_BANCO
    if not os.path.exists(caminho_banco):
        return None
    os.makedirs(PASTA_BACKUPS, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho_backup = os.path.join(PASTA_BACKUPS, f"sino_pre_migracao_v5_{timestamp}.db")
    shutil.copy2(caminho_banco, caminho_backup)
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


def _gerar_hash_senha(senha):
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def criar_usuario(nome, email, senha):
    conexao = conectar()
    cursor = conexao.cursor()
    senha_hash = _gerar_hash_senha(senha)
    agora = date.today().isoformat()
    try:
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
    conexao = conectar()
    cursor = conexao.cursor()
    senha_hash = _gerar_hash_senha(senha)
    cursor.execute(
        "SELECT id, nome, email FROM usuarios WHERE email = ? AND senha_hash = ?",
        (email, senha_hash),
    )
    resultado = cursor.fetchone()
    conexao.close()
    if resultado is None:
        return None
    return {"id": resultado[0], "nome": resultado[1], "email": resultado[2]}


def criar_categoria(usuario_id, nome, icone=None):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "INSERT INTO categorias (usuario_id, nome, icone) VALUES (?, ?, ?)",
        (usuario_id, nome, icone),
    )
    conexao.commit()
    novo_id = cursor.lastrowid
    conexao.close()
    return novo_id


def listar_categorias(usuario_id):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id, nome, icone FROM categorias WHERE usuario_id = ? ORDER BY nome",
        (usuario_id,),
    )
    linhas = cursor.fetchall()
    conexao.close()
    return [{"id": l[0], "nome": l[1], "icone": l[2]} for l in linhas]


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


def criar_conta(usuario_id, nome, valor, data_vencimento, categoria_id=None,
                 conta_fixa=0, repetir_ate=None):
    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        """
        INSERT INTO contas
            (usuario_id, categoria_id, nome, valor, data_vencimento,
             status, conta_fixa, repetir_ate)
        VALUES (?, ?, ?, ?, ?, 'pendente', ?, ?)
        """,
        (usuario_id, categoria_id, nome, valor, data_vencimento, conta_fixa, repetir_ate),
    )
    primeiro_id = cursor.lastrowid

    if conta_fixa == 1:
        cursor.execute("UPDATE contas SET serie_id = ? WHERE id = ?", (primeiro_id, primeiro_id))

        ano, mes, dia = map(int, data_vencimento.split("-"))
        limite_ano, limite_mes = map(int, repetir_ate.split("-"))
        proxima_data = _somar_mes(ano, mes, dia)

        while True:
            ano_atual, mes_atual, _ = map(int, proxima_data.split("-"))
            if (ano_atual, mes_atual) > (limite_ano, limite_mes):
                break
            cursor.execute(
                """
                INSERT INTO contas
                    (usuario_id, categoria_id, serie_id, nome, valor,
                     data_vencimento, status, conta_fixa, repetir_ate)
                VALUES (?, ?, ?, ?, ?, ?, 'pendente', 1, ?)
                """,
                (usuario_id, categoria_id, primeiro_id, nome, valor, proxima_data, repetir_ate),
            )
            proxima_data = _somar_mes(ano_atual, mes_atual, dia)

    conexao.commit()
    conexao.close()
    return primeiro_id


def listar_contas(usuario_id, ano_mes=None):
    conexao = conectar()
    cursor = conexao.cursor()

    if ano_mes:
        cursor.execute(
            """
            SELECT id, nome, valor, data_vencimento, status, categoria_id,
                   serie_id, data_pagamento, editado_individualmente
            FROM contas WHERE usuario_id = ? AND data_vencimento LIKE ?
            ORDER BY data_vencimento
            """,
            (usuario_id, f"{ano_mes}%"),
        )
    else:
        cursor.execute(
            """
            SELECT id, nome, valor, data_vencimento, status, categoria_id,
                   serie_id, data_pagamento, editado_individualmente
            FROM contas WHERE usuario_id = ?
            ORDER BY data_vencimento
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
        SELECT id, nome, valor, data_vencimento, status, categoria_id, serie_id
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
         "status": l[4], "categoria_id": l[5], "serie_id": l[6]}
        for l in linhas
    ]


def listar_contas_atrasadas(usuario_id):
    """Contas pendentes com vencimento já passado, de qualquer mês (RF25)."""
    conexao = conectar()
    cursor = conexao.cursor()

    hoje = date.today().isoformat()

    cursor.execute(
        """
        SELECT id, nome, valor, data_vencimento, categoria_id, serie_id
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
         "status": "atrasado", "categoria_id": l[4], "serie_id": l[5]}
        for l in linhas
    ]


def obter_parcela(serie_id, conta_id):
    """
    Posição (X) e total (Y) de uma ocorrência dentro da série (RF26/5.19).

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
        "SELECT id FROM contas WHERE serie_id = ? ORDER BY data_vencimento",
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


def marcar_conta_como_paga(conta_id):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("UPDATE contas SET status = 'pago' WHERE id = ?", (conta_id,))
    conexao.commit()
    conexao.close()


def marcar_conta_como_pendente(conta_id):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("UPDATE contas SET status = 'pendente' WHERE id = ?", (conta_id,))
    conexao.commit()
    conexao.close()


def editar_conta_ocorrencia(conta_id, nome=None, valor=None, data_vencimento=None):
    """
    Atualiza nome/valor/data_vencimento de uma única ocorrência.

    Para contas fixas (conta_fixa = 1), a ocorrência representa um mês/ano
    específico da série: a data só pode mudar de dia, nunca de mês/ano. Se
    isso for tentado, a chamada inteira é rejeitada (nada é alterado) e a
    função retorna False. Contas não fixas continuam podendo mudar de
    mês/ano livremente. Retorna True quando a alteração é aplicada.
    """
    conexao = conectar()
    cursor = conexao.cursor()

    if data_vencimento is not None:
        cursor.execute("SELECT conta_fixa, data_vencimento FROM contas WHERE id = ?", (conta_id,))
        linha = cursor.fetchone()
        if linha is None:
            conexao.close()
            return False
        conta_fixa, data_atual = linha
        if conta_fixa == 1:
            ano_novo, mes_novo, _ = map(int, data_vencimento.split("-"))
            ano_atual, mes_atual, _ = map(int, data_atual.split("-"))
            if (ano_novo, mes_novo) != (ano_atual, mes_atual):
                conexao.close()
                return False

    if nome is not None:
        cursor.execute("UPDATE contas SET nome = ? WHERE id = ?", (nome, conta_id))
    if valor is not None:
        cursor.execute("UPDATE contas SET valor = ? WHERE id = ?", (valor, conta_id))
    if data_vencimento is not None:
        cursor.execute("UPDATE contas SET data_vencimento = ? WHERE id = ?", (data_vencimento, conta_id))
    conexao.commit()
    conexao.close()
    return True


def editar_conta_serie(conta_id, nome=None, valor=None, data_vencimento=None):
    """
    Aplica nome/valor/data à ocorrência informada e às futuras da mesma série
    (data_vencimento >= referência, capturada antes de qualquer alteração).

    nome e valor são copiados literalmente para todas as ocorrências afetadas.
    data_vencimento segue uma regra diferente: cada ocorrência futura permanece
    no seu próprio mês/ano, apenas o dia é recalculado a partir do dia da nova
    data informada (com o mesmo ajuste de fim de mês usado na geração da série);
    a ocorrência editada recebe exatamente a data informada — mas só se essa
    data mantiver o mesmo mês/ano que a ocorrência já tinha. Caso contrário,
    a chamada inteira é rejeitada (nada é alterado) e a função retorna False.
    Retorna True quando a alteração é aplicada.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT serie_id, data_vencimento FROM contas WHERE id = ?", (conta_id,))
    linha = cursor.fetchone()
    if linha is None:
        conexao.close()
        return False
    serie_id, data_referencia = linha
    if serie_id is None:
        conexao.close()
        return editar_conta_ocorrencia(conta_id, nome=nome, valor=valor, data_vencimento=data_vencimento)

    if data_vencimento is not None:
        ano_novo, mes_novo, _ = map(int, data_vencimento.split("-"))
        ano_ref, mes_ref, _ = map(int, data_referencia.split("-"))
        if (ano_novo, mes_novo) != (ano_ref, mes_ref):
            conexao.close()
            return False

    campos, valores = [], []
    if nome is not None:
        campos.append("nome = ?")
        valores.append(nome)
    if valor is not None:
        campos.append("valor = ?")
        valores.append(valor)
    if campos:
        sql = f"UPDATE contas SET {', '.join(campos)} WHERE serie_id = ? AND data_vencimento >= ?"
        cursor.execute(sql, (*valores, serie_id, data_referencia))

    if data_vencimento is not None:
        cursor.execute(
            "SELECT id, data_vencimento FROM contas WHERE serie_id = ? AND data_vencimento >= ?",
            (serie_id, data_referencia),
        )
        ocorrencias_futuras = cursor.fetchall()
        dia_novo = date.fromisoformat(data_vencimento).day

        for ocorrencia_id, data_atual in ocorrencias_futuras:
            if ocorrencia_id == conta_id:
                nova_data = data_vencimento
            else:
                ano_linha, mes_linha, _ = map(int, data_atual.split("-"))
                dia_ajustado = _ajustar_dia(ano_linha, mes_linha, dia_novo)
                nova_data = date(ano_linha, mes_linha, dia_ajustado).isoformat()
            cursor.execute(
                "UPDATE contas SET data_vencimento = ? WHERE id = ?",
                (nova_data, ocorrencia_id),
            )

    conexao.commit()
    conexao.close()
    return True


def editar_categoria(categoria_id, nome=None, icone=None):
    """Atualiza nome e/ou ícone de uma categoria existente."""
    conexao = conectar()
    cursor = conexao.cursor()
    if nome is not None:
        cursor.execute("UPDATE categorias SET nome = ? WHERE id = ?", (nome, categoria_id))
    if icone is not None:
        cursor.execute("UPDATE categorias SET icone = ? WHERE id = ?", (icone, categoria_id))
    conexao.commit()
    conexao.close()


def excluir_categoria(categoria_id):
    """
    Exclui uma categoria. Contas associadas NÃO são excluídas (RF14 / seção 5):
    elas passam a ficar sem categoria (categoria_id = NULL).
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("UPDATE contas SET categoria_id = NULL WHERE categoria_id = ?", (categoria_id,))
    cursor.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))
    conexao.commit()
    conexao.close()


def excluir_conta(conta_id):
    """
    Exclui somente esta ocorrência da conta (RF08).

    Se a ocorrência for a âncora de uma série (serie_id == id, a mais antiga)
    e ainda existirem outras ocorrências da mesma série apontando para ela,
    excluí-la sozinha quebraria a referência dessas ocorrências (FOREIGN
    KEY): nesse caso a chamada é recusada (nada é alterado) e a função
    retorna False. Use excluir_conta_serie() para remover a série inteira
    a partir da âncora. Retorna True quando a exclusão é aplicada.
    """
    conexao = conectar()
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT serie_id FROM contas WHERE id = ?", (conta_id,))
        linha = cursor.fetchone()
        if linha is None:
            return False
        serie_id = linha[0]
        if serie_id == conta_id:
            cursor.execute(
                "SELECT COUNT(*) FROM contas WHERE serie_id = ? AND id != ?",
                (serie_id, conta_id),
            )
            if cursor.fetchone()[0] > 0:
                return False
        cursor.execute("DELETE FROM contas WHERE id = ?", (conta_id,))
        conexao.commit()
        return True
    finally:
        conexao.close()


def excluir_conta_serie(conta_id):
    """
    Exclui esta ocorrência e todas as futuras da mesma série (mesmo critério
    de 'data_vencimento >= referência' usado em editar_conta_serie).
    Ocorrências passadas da série são preservadas.
    """
    conexao = conectar()
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT serie_id, data_vencimento FROM contas WHERE id = ?", (conta_id,))
        linha = cursor.fetchone()
        if linha is None:
            return
        serie_id, data_referencia = linha
        if serie_id is None:
            cursor.execute("DELETE FROM contas WHERE id = ?", (conta_id,))
        else:
            cursor.execute(
                "DELETE FROM contas WHERE serie_id = ? AND data_vencimento >= ?",
                (serie_id, data_referencia),
            )
        conexao.commit()
    finally:
        conexao.close()

if __name__ == "__main__":
    criar_tabelas()
    print("Tabelas criadas (ou já existiam): usuarios, categorias, contas.")
