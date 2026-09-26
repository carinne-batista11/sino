"""
fixture_schema_v5.py — Schema v5.0 congelado para os testes de migração v6.

`criar_tabelas()` passou a gerar o schema v6; este DDL é a cópia literal do
que ela gerava no commit 959c4bf (v5.0) e não deve acompanhar mudanças
futuras do `db.py`. `popular_banco_v5` grava um conjunto de dados que cobre
os casos relevantes para a migração: séries mensal e anual, conta avulsa,
pago/pendente, data de pagamento, ocorrência editada individualmente,
`categoria_id` NULL ("Sem categoria"), categoria excluída sem contas,
nomes com emoji/acentos e hash de senha legado.
"""

import sqlite3

DDL_V5 = """
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    termos_aceitos_em TEXT NOT NULL
);

CREATE TABLE categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    icone TEXT,
    cor TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

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

CREATE TABLE contas (
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

CREATE INDEX idx_contas_usuario ON contas(usuario_id);
CREATE INDEX idx_contas_categoria ON contas(categoria_id);
CREATE INDEX idx_contas_vencimento ON contas(data_vencimento);
CREATE INDEX idx_contas_serie ON contas(serie_id);
CREATE INDEX idx_series_usuario ON series_recorrencia(usuario_id);
"""

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

USUARIOS = [
    (3, "Ana 🌷", "ana@sino.com", "pbkdf2_sha256$200000$00$00", "2026-09-01"),
    (7, "João Álvares", "joao@sino.com", "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
     "2026-09-02"),
]

CATEGORIAS = [
    (10, 3, "Casa", "🏡", "#96E199"),
    (11, 3, "Academia", "🏋🏻‍♀️", "#CE93D8"),
    (12, 7, "Streaming", "📽️", "#F3756A"),
    (13, 7, "Sem cor", None, None),
]

SERIES = [
    (20, 3, "Aluguel", 1500.0, 10, "mensal", 31, None, "2026-01-31", "2026-12-31", 1, "2026-12-31"),
    (21, 3, "IPVA", 980.55, None, "anual", 29, 2, "2028-02-29", None, 1, "2029-02-28"),
    (22, 7, "Netflix", 55.9, 12, "mensal", 5, None, "2026-08-05", None, 0, "2026-09-05"),
]

CONTAS = [
    (100, 3, 10, 20, "Aluguel", 1500.0, "2026-08-31", "pago", "2026-08-30", 0),
    (101, 3, 10, 20, "Aluguel reajustado", 1620.0, "2026-09-30", "pendente", None, 1),
    (102, 3, None, 21, "IPVA", 980.55, "2028-02-29", "pendente", None, 0),
    (103, 3, None, 21, "IPVA", 980.55, "2029-02-28", "pendente", None, 0),
    (104, 3, None, None, "Presente 🎁", 89.9, "2026-09-10", "pago", "2026-09-09", 0),
    (105, 7, 12, 22, "Netflix", 55.9, "2026-09-05", "pendente", None, 0),
    (106, 7, None, None, "Conta avulsa", 0.01, "2026-07-01", "pendente", None, 0),
]

SEQUENCIAS = {"usuarios": 9, "categorias": 15, "series_recorrencia": 25, "contas": 120}


def criar_banco_v5(caminho, conectar=sqlite3.connect, popular=True, usuarios_extras=()):
    """
    Cria um banco v5 em `caminho`. `usuarios_extras` recebe tuplas no mesmo
    formato de USUARIOS (ex.: para simular colisão de e-mail).
    """
    conexao = conectar(caminho)
    try:
        conexao.executescript(DDL_V5)
        if popular:
            _inserir(conexao, "usuarios", list(USUARIOS) + list(usuarios_extras))
            _inserir(conexao, "categorias", CATEGORIAS)
            _inserir(conexao, "series_recorrencia", SERIES)
            _inserir(conexao, "contas", CONTAS)
            for tabela, seq in SEQUENCIAS.items():
                conexao.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (seq, tabela))
        conexao.commit()
    finally:
        conexao.close()


def _inserir(conexao, tabela, linhas):
    colunas = COLUNAS_V5[tabela]
    marcadores = ", ".join("?" for _ in colunas)
    conexao.executemany(
        f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({marcadores})",
        linhas,
    )
