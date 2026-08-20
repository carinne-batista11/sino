"""
database.py — Camada de banco de dados do Sino (v2)
"""

import sqlite3
import hashlib
import os
from datetime import date, timedelta
from calendar import monthrange

NOME_DO_BANCO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sino.db")


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
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
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
            conta_fixa INTEGER NOT NULL DEFAULT 0,
            repetir_ate TEXT,

            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (categoria_id) REFERENCES categorias(id),
            FOREIGN KEY (serie_id) REFERENCES contas(id),

            CHECK (status IN ('pago', 'pendente')),
            CHECK (conta_fixa IN (0, 1)),
            CHECK (
                (conta_fixa = 0 AND repetir_ate IS NULL)
                OR
                (conta_fixa = 1 AND repetir_ate IS NOT NULL)
            )
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contas_usuario ON contas(usuario_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contas_categoria ON contas(categoria_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contas_vencimento ON contas(data_vencimento);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contas_serie ON contas(serie_id);")

    conexao.commit()
    conexao.close()


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


def _somar_mes(ano, mes, dia):
    mes += 1
    if mes > 12:
        mes = 1
        ano += 1
    ultimo_dia_do_mes = monthrange(ano, mes)[1]
    dia_ajustado = min(dia, ultimo_dia_do_mes)
    return date(ano, mes, dia_ajustado).isoformat()


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
            SELECT id, nome, valor, data_vencimento, status, categoria_id, conta_fixa
            FROM contas WHERE usuario_id = ? AND data_vencimento LIKE ?
            ORDER BY data_vencimento
            """,
            (usuario_id, f"{ano_mes}%"),
        )
    else:
        cursor.execute(
            """
            SELECT id, nome, valor, data_vencimento, status, categoria_id, conta_fixa
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
            "status": status, "categoria_id": l[5], "conta_fixa": l[6],
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
        SELECT id, nome, valor, data_vencimento, status, categoria_id, conta_fixa
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
         "status": l[4], "categoria_id": l[5], "conta_fixa": l[6]}
        for l in linhas
    ]


def marcar_conta_como_paga(conta_id):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("UPDATE contas SET status = 'pago' WHERE id = ?", (conta_id,))
    conexao.commit()
    conexao.close()


def editar_conta_ocorrencia(conta_id, nome=None, valor=None, data_vencimento=None):
    conexao = conectar()
    cursor = conexao.cursor()
    if nome is not None:
        cursor.execute("UPDATE contas SET nome = ? WHERE id = ?", (nome, conta_id))
    if valor is not None:
        cursor.execute("UPDATE contas SET valor = ? WHERE id = ?", (valor, conta_id))
    if data_vencimento is not None:
        cursor.execute("UPDATE contas SET data_vencimento = ? WHERE id = ?", (data_vencimento, conta_id))
    conexao.commit()
    conexao.close()


def editar_conta_serie(conta_id, nome=None, valor=None):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT serie_id, data_vencimento FROM contas WHERE id = ?", (conta_id,))
    linha = cursor.fetchone()
    if linha is None:
        conexao.close()
        return
    serie_id, data_referencia = linha
    if serie_id is None:
        conexao.close()
        editar_conta_ocorrencia(conta_id, nome=nome, valor=valor)
        return
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
    conexao.commit()
    conexao.close()


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
    """Exclui somente esta ocorrência da conta (RF08)."""
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM contas WHERE id = ?", (conta_id,))
    conexao.commit()
    conexao.close()


def excluir_conta_serie(conta_id):
    """
    Exclui esta ocorrência e todas as futuras da mesma série (mesmo critério
    de 'data_vencimento >= referência' usado em editar_conta_serie).
    Ocorrências passadas da série são preservadas.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("SELECT serie_id, data_vencimento FROM contas WHERE id = ?", (conta_id,))
    linha = cursor.fetchone()
    if linha is None:
        conexao.close()
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
    conexao.close()

if __name__ == "__main__":
    criar_tabelas()
    print("Tabelas criadas (ou já existiam): usuarios, categorias, contas.")
