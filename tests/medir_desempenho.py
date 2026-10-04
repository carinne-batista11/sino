"""
Medição de desempenho da v6.0 (RNF03 e RNF06) -- não faz parte da suíte.

    .venv/bin/python tests/medir_desempenho.py [--repeticoes N] [--json arquivo]

Monta um banco DESCARTÁVEL (pasta temporária, com as mesmas guardas dos
testes: o banco real e os backups nunca são abertos) com 1 usuário e
exatamente 1.000 contas, e mede:

  * operações de dados (database/db.py) usadas pelas telas;
  * operações da interface (backend/main.py) com a página falsa dos testes:
    o tempo do Python para consultar o banco e montar os controles da tela.

Não mede a renderização do Flutter nem a troca de mensagens entre o Python e
a janela do Flet. Cada operação roda 1 vez de aquecimento e N vezes medidas
(time.perf_counter); o resultado traz mediana, p95 e máximo, em ms.

Cenários (determinísticos, semente fixa; "hoje" fixado em 15/09/2026):
  * distribuído: 11 categorias padrão; 10 séries mensais com término
    (jan/2025 a dez/2027, 36 ocorrências cada); 2 séries mensais sem término;
    contas únicas de jan/2025 a dez/2027 até completar 1.000, ~30% pagas,
    ~25% com descrição e ~10% sem categoria;
  * mês único (pior caso da Tela Principal, que mostra todas as contas do
    mês): as 1.000 contas em setembro de 2026.

--banco CAMINHO guarda uma cópia do banco do cenário distribuído (fora do
projeto) para abrir numa cópia isolada do app.
"""

import argparse
import shutil
import io
import json
import os
import platform
import random
import sqlite3
import statistics
import subprocess
import sys
import time
from contextlib import redirect_stderr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flet as ft  # noqa: E402

from apoio_banco import db  # noqa: E402
from test_legibilidade_temas import TesteDeLegibilidade  # noqa: E402
from test_sessao_tema import main  # noqa: E402

TOTAL_CONTAS = 1000
SEMENTE = 2026


def ambiente():
    def comando(*args):
        try:
            return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return "?"
    cpu = next((l.split(":", 1)[1].strip() for l in comando("lscpu").splitlines()
                if l.startswith(("Model name", "Nome do modelo"))), platform.processor() or "?")
    memoria = next((l.split()[1] for l in open("/proc/meminfo") if l.startswith("MemTotal")), "?") \
        if os.path.exists("/proc/meminfo") else "?"
    return {
        "data": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "sistema": platform.platform(),
        "cpu": cpu,
        "nucleos": os.cpu_count(),
        "memoria_kb": memoria,
        "python": platform.python_version(),
        "flet": getattr(ft, "__version__", "?"),
        "sqlite": sqlite3.sqlite_version,
        "commit": comando("git", "-C", os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "rev-parse", "--short", "HEAD"),
    }


class Medicao(TesteDeLegibilidade):
    repeticoes = 30
    resultados = {}
    copiar_banco_para = None

    def runTest(self):  # noqa: N802 -- unittest
        pass

    # ---------------------------------------------------------------- dados
    def popular_mil(self, usuario_id):
        rnd = random.Random(SEMENTE)
        db.inicializar_categorias_padrao(usuario_id)
        categorias = [c["id"] for c in db.listar_categorias(usuario_id)]
        for i in range(10):
            db.criar_serie_recorrente(usuario_id, f"Série {i + 1}", 50.0 + i * 10, f"2025-01-{(i % 27) + 1:02d}",
                                      "mensal", data_termino="2027-12", categoria_id=categorias[i % len(categorias)])
        self.series_sem_termino = [
            db.criar_serie_recorrente(usuario_id, f"Assinatura {i + 1}", 39.9, "2026-01-10", "mensal",
                                      categoria_id=categorias[i])[0] for i in range(2)]
        existentes = self.consultar("SELECT COUNT(*) FROM contas WHERE usuario_id = ?", (usuario_id,))[0][0]
        for n in range(TOTAL_CONTAS - existentes):
            ano = rnd.choice((2025, 2026, 2027))
            mes, dia = rnd.randint(1, 12), rnd.randint(1, 28)
            conta = db.criar_conta_unica(
                usuario_id, f"Conta {n + 1}", round(rnd.uniform(5, 900), 2), f"{ano}-{mes:02d}-{dia:02d}",
                categoria_id=None if rnd.random() < 0.1 else rnd.choice(categorias),
                descricao=f"Descrição da conta {n + 1}" if rnd.random() < 0.25 else None)
            if rnd.random() < 0.3:
                db.marcar_conta_como_paga(conta, f"{ano}-{mes:02d}-{dia:02d}")
        total = self.consultar("SELECT COUNT(*) FROM contas WHERE usuario_id = ?", (usuario_id,))[0][0]
        assert total == TOTAL_CONTAS, total
        return total

    def popular_mes_unico(self, usuario_id):
        rnd = random.Random(SEMENTE)
        db.inicializar_categorias_padrao(usuario_id)
        categorias = [c["id"] for c in db.listar_categorias(usuario_id)]
        for n in range(TOTAL_CONTAS):
            conta = db.criar_conta_unica(usuario_id, f"Conta {n + 1}", round(rnd.uniform(5, 900), 2),
                                         f"2026-09-{rnd.randint(1, 30):02d}", categoria_id=rnd.choice(categorias))
            if rnd.random() < 0.3:
                db.marcar_conta_como_paga(conta, "2026-09-10")
        return self.consultar("SELECT COUNT(*) FROM contas WHERE usuario_id = ?", (usuario_id,))[0][0]

    def executar_mes_unico(self):
        self.setUp()
        try:
            self.resultados["_dados_mes_unico"] = {"contas": self.popular_mes_unico(self.bia)}
            pagina, _ = self.abrir_app()
            self.medir("mês único: entrar e montar a Tela Principal (1.000 linhas)",
                       lambda: self.entrar(pagina, "bia@sino.com", "senha5678"),
                       preparar=lambda: self._voltar_ao_login(pagina))
            self.medir("mês único: Ver status + filtro Pendentes", lambda: (
                self.clicar(pagina, self.botao(pagina, "Ver status") or self.clicavel_com_texto(pagina, "Ver status")),
                self.clicar(pagina, self.clicavel_com_texto(pagina, "Pendentes"))),
                preparar=lambda: self.ir_para_inicio(pagina))
            self.medir("mês único: Gráfico mensal", lambda: self.clicar(pagina, self.clicavel_com_texto(pagina, "Gráfico")),
                       preparar=lambda: self.ir_para_inicio(pagina))
        finally:
            self.doCleanups()

    # ---------------------------------------------------------------- medição
    def medir(self, nome, operacao, preparar=None):
        tempos = []
        for i in range(self.repeticoes + 1):
            if preparar:
                preparar()
            inicio = time.perf_counter()
            with redirect_stderr(io.StringIO()):
                operacao()
            decorrido = (time.perf_counter() - inicio) * 1000
            if i:  # a primeira é aquecimento
                tempos.append(decorrido)
        tempos.sort()
        self.resultados[nome] = {
            "mediana_ms": round(statistics.median(tempos), 1),
            "p95_ms": round(tempos[max(0, int(len(tempos) * 0.95) - 1)], 1),
            "max_ms": round(tempos[-1], 1),
            "n": len(tempos),
        }

    def executar_medicao(self):
        self.setUp()
        try:
            uid = self.bia
            self.resultados["_dados"] = {"contas": self.popular_mil(uid)}
            if self.copiar_banco_para:
                destino = os.path.abspath(self.copiar_banco_para)
                assert "/Projetos/sino/" not in destino + "/", "a cópia precisa ficar fora do projeto"
                shutil.copyfile(self.caminho_banco, destino)
            conta_serie = self.consultar("SELECT id FROM contas WHERE usuario_id = ? AND serie_id IS NOT NULL "
                                         "AND data_vencimento LIKE '2026-09-%' LIMIT 1", (uid,))[0][0]
            conta_unica = self.consultar("SELECT id FROM contas WHERE usuario_id = ? AND serie_id IS NULL "
                                         "AND status != 'pago' LIMIT 1", (uid,))[0][0]

            # --- dados -----------------------------------------------------
            self.medir("dados: login (PBKDF2)", lambda: db.verificar_login("bia@sino.com", "senha5678"))
            self.medir("dados: contas do mês", lambda: db.listar_contas(uid, "2026-09"))
            self.medir("dados: contas atrasadas", lambda: db.listar_contas_atrasadas(uid))
            self.medir("dados: próximos 7 dias", lambda: db.listar_contas_proximas(uid))
            self.medir("dados: gastos por categoria (ano)",
                       lambda: db.gastos_por_categoria(uid, "2026-01-01", "2026-12-31"))
            self.medir("dados: totais por ano", lambda: db.totais_por_ano(uid))
            self.medir("dados: criar conta única", lambda: db.criar_conta_unica(uid, "Nova", 10.0, "2026-09-20"))
            self.medir("dados: marcar/desmarcar como paga", lambda: (db.marcar_conta_como_paga(conta_unica, "2026-09-15"),
                                                                    db.marcar_conta_como_pendente(conta_unica)))
            self.medir("dados: editar série (este mês em diante)",
                       lambda: db.editar_conta_serie(conta_serie, valor=round(random.uniform(10, 99), 2)))
            criadas = []
            self.medir("dados: excluir conta única", lambda: db.excluir_conta(criadas.pop()),
                       preparar=lambda: criadas.append(db.criar_conta_unica(uid, "Apagar", 1.0, "2026-09-21")))

            # --- interface (página falsa) -----------------------------------
            pagina, _ = self.abrir_app()
            self.medir("tela: entrar e montar a Tela Principal",
                       lambda: self.entrar(pagina, "bia@sino.com", "senha5678"),
                       preparar=lambda: self._voltar_ao_login(pagina))
            self.medir("tela: Início (voltar)", lambda: self.ir_para_inicio(pagina),
                       preparar=lambda: self.clicar(pagina, self.clicavel_com_texto(pagina, "Categorias")))
            proximo = lambda: next(b for b in self.todos(pagina)  # noqa: E731
                                   if isinstance(b, ft.IconButton) and b.icon == ft.Icons.CHEVRON_RIGHT)
            self.medir("tela: próximo mês (gera ocorrências sob demanda)", lambda: self.clicar(pagina, proximo()),
                       preparar=lambda: self.ir_para_inicio(pagina))
            self.medir("tela: Ver status + filtro Atrasadas", lambda: (
                self.clicar(pagina, self.botao(pagina, "Ver status") or self.clicavel_com_texto(pagina, "Ver status")),
                self.clicar(pagina, self.clicavel_com_texto(pagina, "Atrasadas"))),
                preparar=lambda: self.ir_para_inicio(pagina))
            self.medir("tela: abrir Detalhes (série)", lambda: self.abrir_linha(pagina, "Série 1"),
                       preparar=lambda: self.ir_para_inicio(pagina))
            self.medir("tela: Detalhes → Editar", lambda: self.clicar(pagina, self.botao(pagina, "Editar")),
                       preparar=lambda: (self.ir_para_inicio(pagina), self.abrir_linha(pagina, "Série 1")))
            self.medir("tela: Gráfico mensal", lambda: self.clicar(pagina, self.clicavel_com_texto(pagina, "Gráfico")),
                       preparar=lambda: self.ir_para_inicio(pagina))
            self.medir("tela: Gráfico anual", lambda: self.clicar(pagina, self.clicavel_com_texto(pagina, "Anual")),
                       preparar=lambda: (self.ir_para_inicio(pagina),
                                         self.clicar(pagina, self.clicavel_com_texto(pagina, "Gráfico"))))
            self.medir("tela: Categorias", lambda: self.clicar(pagina, self.clicavel_com_texto(pagina, "Categorias")),
                       preparar=lambda: self.ir_para_inicio(pagina))
        finally:
            self.doCleanups()

    def _voltar_ao_login(self, pagina):
        """Sai da sessão (sem diálogo) para medir de novo a entrada."""
        if self.sessoes and self.sessoes[-1].usuario["id"] is not None:
            self.sessoes[-1].encerrar()


def principal():
    argumentos = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    argumentos.add_argument("--repeticoes", type=int, default=30)
    argumentos.add_argument("--json", help="grava o resultado completo neste arquivo")
    argumentos.add_argument("--banco", help="guarda uma cópia do banco do cenário distribuído (fora do projeto)")
    opcoes = argumentos.parse_args()
    Medicao.repeticoes = opcoes.repeticoes
    Medicao.copiar_banco_para = opcoes.banco
    Medicao().executar_medicao()
    Medicao().executar_mes_unico()
    resultado = {"ambiente": ambiente(), "repeticoes": opcoes.repeticoes, "operacoes": Medicao.resultados}
    largura = max(len(n) for n in Medicao.resultados)
    print(f"{'operação':<{largura}}  mediana    p95     máx (ms)")
    for nome, r in Medicao.resultados.items():
        if not nome.startswith("_"):
            print(f"{nome:<{largura}}  {r['mediana_ms']:>7}  {r['p95_ms']:>6}  {r['max_ms']:>7}")
    print(json.dumps(resultado["ambiente"], ensure_ascii=False))
    if opcoes.json:
        with open(opcoes.json, "w", encoding="utf-8") as arquivo:
            json.dump(resultado, arquivo, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    principal()
