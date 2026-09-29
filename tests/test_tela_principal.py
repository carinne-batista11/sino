"""
Tela Principal e Ver status (ERS v6.0, Etapa 3): RF05, RF09, RF12, RF30.

Funções puras (resumo do mês, ordem, filtro de status) e o fluxo real da
interface com uma página falsa sobre um banco temporário v7: login, lista
completa do mês, cartão do total sem filtros, lápis, clique na linha,
pagamento rápido e Ver status. Nenhuma janela é aberta.
"""

import os
import sys
import unittest
from unittest import mock

import apoio_banco
from apoio_banco import DataFixa, TesteComBancoTemporario, db

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import flet as ft  # noqa: E402
import main  # noqa: E402


def conta(status, valor, vencimento="2026-10-10"):
    return {"status": status, "valor": valor, "data_vencimento": vencimento}


class TestFuncoesDaTelaPrincipal(unittest.TestCase):
    def test_total_soma_todas_as_contas_em_qualquer_status(self):
        contas = [conta("pago", 100.0), conta("pendente", 50.0), conta("atrasado", 25.0)]
        self.assertEqual(main.resumo_do_mes(contas), (175.0, 100.0, 75.0))

    def test_marcar_como_paga_nao_altera_o_total(self):
        antes = main.resumo_do_mes([conta("pendente", 80.0), conta("pendente", 20.0)])
        depois = main.resumo_do_mes([conta("pago", 80.0), conta("pendente", 20.0)])
        self.assertEqual(antes[0], depois[0])
        self.assertEqual((depois[1], depois[2]), (80.0, 20.0))

    def test_mes_vazio(self):
        self.assertEqual(main.resumo_do_mes([]), (0, 0, 0))

    def test_ordem_atrasadas_primeiro_depois_vencimento_sem_corte(self):
        contas = [conta("pendente", 1.0, f"2026-10-{d:02d}") for d in range(12, 0, -1)]
        contas.append(conta("atrasado", 1.0, "2026-10-20"))
        ordenadas = main.ordenar_contas_do_mes(contas)
        self.assertEqual(len(ordenadas), 13)
        self.assertEqual(ordenadas[0]["status"], "atrasado")
        self.assertEqual([c["data_vencimento"] for c in ordenadas[1:]],
                         [f"2026-10-{d:02d}" for d in range(1, 13)])

    def test_filtros_de_status(self):
        contas = [conta("pago", 1.0), conta("pendente", 2.0), conta("atrasado", 3.0)]
        self.assertEqual([f for f, _ in main.FILTROS_DE_STATUS], ["todas", "pendentes", "pagas", "atrasadas"])
        self.assertEqual(len(main.filtrar_por_status(contas, "todas")), 3)
        for filtro, status in (("pendentes", "pendente"), ("pagas", "pago"), ("atrasadas", "atrasado")):
            self.assertEqual([c["status"] for c in main.filtrar_por_status(contas, filtro)], [status])


class Evento:
    def __init__(self, pagina, controle=None):
        self.page = pagina
        self.control = controle


def percorrer(controle):
    """Todos os controles da árvore (controls/content/actions)."""
    yield controle
    for atributo in ("controls", "content", "actions"):
        filho = getattr(controle, atributo, None)
        if isinstance(filho, list):
            for item in filho:
                yield from percorrer(item)
        elif isinstance(filho, ft.Control):
            yield from percorrer(filho)


class TestFluxoDaTelaPrincipal(TesteComBancoTemporario):
    """Hoje fixo em 15/09/2026 (db e main); as contas ficam em outubro/2026."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.usuario_id = self.criar_usuario(email="tela@sino.com", senha="senha1234")
        self.pagina = mock.MagicMock()
        self.pagina.controls = []
        self.pagina.add.side_effect = lambda *controles: self.pagina.controls.extend(controles)

    # ---------------------------------------------------------------- auxiliares
    def controles(self, tipo=None):
        todos = [c for raiz in self.pagina.controls for c in percorrer(raiz)]
        return [c for c in todos if tipo is None or isinstance(c, tipo)]

    def textos(self):
        return [c.value for c in self.controles(ft.Text)]

    def clicar(self, controle):
        controle.on_click(Evento(self.pagina, controle))

    def entrar(self):
        main.main(self.pagina)
        campos = {c.label: c for c in self.controles(ft.TextField)}
        campos["E-mail"].value = "tela@sino.com"
        campos["Senha"].value = "senha1234"
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Entrar"))

    def icones(self, dica):
        return [b for b in self.controles(ft.IconButton) if b.tooltip == dica]

    def ir_para_outubro(self):
        seta = next(b for b in self.controles(ft.IconButton) if b.icon == ft.Icons.CHEVRON_RIGHT)
        self.clicar(seta)
        self.assertIn("Outubro 2026", self.textos())

    def botao(self, texto):
        return next(c for c in self.controles() if isinstance(c, (ft.Button, ft.TextButton)) and c.content == texto)

    def valor_do_total(self):
        textos = self.textos()
        return textos[textos.index("Total do mês") + 1]

    def criar_contas_de_outubro(self, quantidade):
        return [db.criar_conta_unica(self.usuario_id, f"Conta {i}", 10.0, f"2026-10-{i + 1:02d}")
                for i in range(quantidade)]

    # ---------------------------------------------------------------- lista
    def test_todas_as_contas_do_mes_na_rolagem_da_pagina(self):
        self.criar_contas_de_outubro(12)
        self.entrar()
        self.ir_para_outubro()

        self.assertIn("Suas contas de outubro", self.textos())
        self.assertEqual(len(self.icones("Editar conta")), 12)
        self.assertEqual(len(self.icones("Marcar como paga")), 12)
        # nada de lista com rolagem própria na Tela Principal
        self.assertEqual(self.controles(ft.ListView), [])
        rolagens = [c for c in self.controles(ft.Column) if c.scroll is not None]
        self.assertEqual(len(rolagens), 1)  # só a página

    def test_cartao_do_total_sem_filtros_e_com_pago_e_pendente(self):
        self.criar_contas_de_outubro(2)
        self.entrar()
        self.ir_para_outubro()
        textos = self.textos()
        for rotulo in ("Todas", "Pendentes", "Pagas"):
            self.assertNotIn(rotulo, textos)
        self.assertEqual(self.valor_do_total(), "R$ 20,00")
        self.assertIn("pago R$ 0,00", textos)
        self.assertIn("pendente R$ 20,00", textos)

    def test_pagamento_rapido_nao_altera_o_total(self):
        self.criar_contas_de_outubro(2)
        self.entrar()
        self.ir_para_outubro()

        self.clicar(self.icones("Marcar como paga")[0])

        self.assertEqual(self.valor_do_total(), "R$ 20,00")
        self.assertIn("pago R$ 10,00", self.textos())
        self.assertIn("pendente R$ 10,00", self.textos())
        self.assertIn("Outubro 2026", self.textos())  # continua no mês
        self.assertNotIn("Editar conta", self.textos())
        self.assertNotIn("Detalhes da conta", self.textos())

    def test_lapis_e_pagamento_tem_as_mesmas_dimensoes(self):
        self.criar_contas_de_outubro(1)
        self.entrar()
        self.ir_para_outubro()
        lapis, pagamento = self.icones("Editar conta")[0], self.icones("Marcar como paga")[0]
        self.assertEqual(lapis.icon_size, pagamento.icon_size)
        caixas = [c for c in self.controles(ft.Container) if c.content in (lapis, pagamento)]
        self.assertEqual({c.width for c in caixas}, {40})

    # ---------------------------------------------------------------- lápis
    def test_lapis_abre_editar_direto(self):
        self.criar_contas_de_outubro(1)
        self.entrar()
        self.ir_para_outubro()
        self.clicar(self.icones("Editar conta")[0])
        self.assertIn("Editar conta", self.textos())
        self.assertNotIn("Detalhes da conta", self.textos())

    def test_cancelar_e_voltar_pelo_lapis_retornam_ao_mesmo_mes(self):
        self.criar_contas_de_outubro(1)
        self.entrar()
        self.ir_para_outubro()

        self.clicar(self.icones("Editar conta")[0])
        self.clicar(self.botao("Cancelar"))
        self.assertIn("Outubro 2026", self.textos())
        self.assertIn("Suas contas de outubro", self.textos())

        self.clicar(self.icones("Editar conta")[0])
        voltar = next(b for b in self.controles(ft.IconButton) if b.icon == ft.Icons.ARROW_BACK)
        self.clicar(voltar)
        self.assertIn("Outubro 2026", self.textos())

    def test_salvar_pelo_lapis_retorna_ao_mesmo_mes(self):
        conta_id = self.criar_contas_de_outubro(1)[0]
        self.entrar()
        self.ir_para_outubro()

        self.clicar(self.icones("Editar conta")[0])
        campo_valor = next(c for c in self.controles(ft.TextField) if c.label == "Valor")
        campo_valor.value = "15,00"
        self.clicar(self.botao("Salvar alterações"))

        dialogo = self.pagina.show_dialog.call_args[0][0]
        self.assertEqual(dialogo.title.value, "Alteração salva")
        dialogo.actions[0].on_click(Evento(self.pagina))
        self.assertIn("Outubro 2026", self.textos())
        self.assertEqual(self.conta(conta_id)["valor"], 15.0)

    def test_salvar_serie_somente_este_mes_pelo_lapis_retorna_ao_mesmo_mes(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Escola", 700.0, "2026-10-10", "mensal")
        self.entrar()
        self.ir_para_outubro()

        self.clicar(self.icones("Editar conta")[0])
        next(c for c in self.controles(ft.TextField) if c.label == "Valor").value = "750,00"
        self.clicar(self.botao("Salvar alterações"))
        escopo = self.pagina.show_dialog.call_args[0][0]
        next(a for a in escopo.actions if a.content == "Somente este mês").on_click(Evento(self.pagina))
        escopo.actions[0].on_click(Evento(self.pagina))  # "Entendi"

        self.assertIn("Outubro 2026", self.textos())
        self.assertEqual([self.conta(c)["valor"] for c in ids[:2]], [750.0, 700.0])

    # ---------------------------------------------------------------- Detalhes
    def test_clique_na_linha_abre_detalhes_e_editar_volta_aos_detalhes(self):
        self.criar_contas_de_outubro(1)
        self.entrar()
        self.ir_para_outubro()
        linha = next(c for c in self.controles(ft.Container)
                     if c.on_click is not None and isinstance(c.content, ft.Row) and c.border is not None)

        self.clicar(linha)
        self.assertIn("Detalhes da conta", self.textos())

        self.clicar(self.botao("Editar"))
        self.assertIn("Editar conta", self.textos())
        self.clicar(self.botao("Cancelar"))
        self.assertIn("Detalhes da conta", self.textos())
        self.assertNotIn("Editar conta", self.textos())

    # ---------------------------------------------------------------- Ver status
    def abrir_ver_status(self):
        link = next(c for c in self.controles(ft.Container)
                    if isinstance(c.content, ft.Text) and c.content.value == "Ver status")
        self.clicar(link)

    def linhas_ver_status(self):
        return self.controles(ft.ListView)[0].controls

    def test_ver_status_mostra_mes_e_quatro_filtros_maiores(self):
        self.criar_contas_de_outubro(3)
        self.entrar()
        self.ir_para_outubro()
        self.abrir_ver_status()

        self.assertIn("Outubro de 2026", self.textos())
        filtros = [c for c in self.controles(ft.Container)
                   if isinstance(c.content, ft.Text) and c.content.value in ("Todas", "Pendentes", "Pagas", "Atrasadas")
                   and c.on_click is not None]
        self.assertEqual([f.content.value for f in filtros], ["Todas", "Pendentes", "Pagas", "Atrasadas"])
        self.assertEqual({f.content.size for f in filtros}, {13})
        self.assertEqual(len(self.linhas_ver_status()), 3)
        self.assertEqual(self.icones("Editar conta"), [])  # lápis só na Tela Principal

        voltar = next(b for b in self.controles(ft.IconButton) if b.icon == ft.Icons.ARROW_BACK)
        self.clicar(voltar)
        self.assertIn("Outubro 2026", self.textos())

    def test_filtros_do_ver_status_usam_o_mes_do_vencimento_real(self):
        serie_id, ids = db.criar_serie_recorrente(self.usuario_id, "Escola", 700.0, "2026-10-10", "mensal")
        db.editar_conta_ocorrencia(ids[0], data_vencimento="2026-11-20")  # outubro movida para novembro
        db.marcar_conta_como_paga(ids[1], "2026-09-10")                   # novembro paga
        self.entrar()
        self.ir_para_outubro()
        self.abrir_ver_status()
        self.assertEqual(len(self.linhas_ver_status()), 1)
        self.assertIn("Nenhuma conta cadastrada neste mês.", self.textos())

        voltar = next(b for b in self.controles(ft.IconButton) if b.icon == ft.Icons.ARROW_BACK)
        self.clicar(voltar)
        self.clicar(next(b for b in self.controles(ft.IconButton) if b.icon == ft.Icons.CHEVRON_RIGHT))
        self.abrir_ver_status()
        self.assertIn("Novembro de 2026", self.textos())
        self.assertEqual(len(self.linhas_ver_status()), 2)

        pagas = next(c for c in self.controles(ft.Container)
                     if isinstance(c.content, ft.Text) and c.content.value == "Pagas" and c.on_click)
        self.clicar(pagas)
        self.assertEqual(len(self.linhas_ver_status()), 1)
        pendentes = next(c for c in self.controles(ft.Container)
                         if isinstance(c.content, ft.Text) and c.content.value == "Pendentes" and c.on_click)
        self.clicar(pendentes)
        self.assertEqual(len(self.linhas_ver_status()), 1)


if __name__ == "__main__":
    unittest.main()
