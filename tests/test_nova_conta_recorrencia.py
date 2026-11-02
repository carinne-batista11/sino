"""
Sino 6.11 — Nova conta: diálogo "Configurar recorrência", no padrão de
"Transformar em recorrente" de Editar conta (aprovado no protótipo v3 de
02/11/2026). Abertura e fechamento, Única/Mensal/Anual, "Sem data de término",
Mês e Ano, Cancelar sem aplicar, Confirmar com resumo, reabertura com a
configuração confirmada, término guardado ao passar por Única, nada gravado
antes do Salvar, gravação pelo Salvar (mesmas regras da 6.10), nomes acessíveis
e foco, e comparação da estrutura com o diálogo real de Editar. Páginas falsas
e bancos temporários; "hoje" = 15/09/2026.
"""
import os
import sys
import unittest
from datetime import datetime
from unittest import mock

import apoio_banco
from apoio_banco import DataFixa, TesteComBancoTemporario, db
from test_sessao_tema import PaginaFalsa
from test_tela_principal import Evento, percorrer

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))
import cores  # noqa: E402
import flet as ft  # noqa: E402
import main  # noqa: E402

CLARO = cores.PALETAS["claro"]


class Base(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(main, "date", DataFixa)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.usuario_id = self.criar_usuario(email="nova611@sino.com", senha="senha1234")
        self.pagina = PaginaFalsa().configurar()

    def entrar(self):
        self.pagina.controls.clear()
        main.main(self.pagina)
        campos = {c.label: c for c in self.controles(ft.TextField)}
        campos["E-mail"].value, campos["Senha"].value = "nova611@sino.com", "senha1234"
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Entrar"))

    def controles(self, tipo=None, raizes=None):
        raizes = self.pagina.controls if raizes is None else raizes
        todos = [c for raiz in raizes for c in percorrer(raiz)]
        return [c for c in todos if tipo is None or isinstance(c, tipo)]

    def clicar(self, c):
        c.on_click(Evento(self.pagina, c))


class TestDialogoRecorrencia(Base):
    def setUp(self):
        super().setUp()
        self.entrar()
        self.clicar(next(c for c in self.controles(ft.Container) if c.data == "nova_conta"))

    # auxiliares
    def campo(self, rotulo, raizes=None):
        return next(c for c in self.controles((ft.TextField, ft.Dropdown), raizes) if c.label == rotulo)

    def abertos(self):
        return [d for d in self.pagina.dialogos if d.open]

    def abrir(self, pelo_campo=False):
        c = self.campo("Recorrência")
        self.clicar(c if pelo_campo else c.suffix_icon)
        self.assertEqual(len(self.abertos()), 1)
        return self.abertos()[0]

    def dlg(self):
        return self.abertos()[0]

    def no_dialogo(self, data):
        return next(c for c in percorrer(self.dlg().content) if getattr(c, "data", None) == data)

    def tipo(self, valor):
        self.clicar(self.no_dialogo(f"tipo_recorrencia_{valor}"))

    def ligar_sem_termino(self, valor):
        chave = self.no_dialogo("sem_termino_recorrencia")
        chave.value = valor
        chave.on_change(Evento(self.pagina, chave))

    def escolher(self, rotulo, valor):
        lista = self.campo(rotulo, [self.dlg().content])
        lista.value = valor
        lista.on_select(Evento(self.pagina, lista))

    def acao(self, texto):
        return next(b for b in self.dlg().actions if b.content == texto)

    def confirmar(self):
        d = self.dlg()
        self.clicar(self.acao("Confirmar"))
        self.assertFalse(d.open)

    def cancelar(self):
        d = self.dlg()
        self.clicar(self.acao("Cancelar"))
        self.assertFalse(d.open)

    def selecionado(self):
        return [v for v in ("unica", "mensal", "anual")
                if self.no_dialogo(f"tipo_recorrencia_{v}").style.bgcolor == CLARO["chip_ativo_fundo"]]

    def visivel_no_dialogo(self, alvo):
        """alvo e todos os seus ancestrais dentro do conteúdo do diálogo estão visíveis."""
        def busca(c, pilha):
            if c is alvo:
                return pilha + [c]
            for atributo in ("controls", "content"):
                filho = getattr(c, atributo, None)
                for f in (filho if isinstance(filho, list) else [filho] if isinstance(filho, ft.Control) else []):
                    r = busca(f, pilha + [c])
                    if r:
                        return r
            return None
        caminho = busca(self.dlg().content, [])
        self.assertIsNotNone(caminho)
        return all(c.visible is not False for c in caminho)

    def chave_visivel(self):
        return self.visivel_no_dialogo(self.no_dialogo("sem_termino_recorrencia"))

    def mes_ano_visiveis(self):
        return (self.visivel_no_dialogo(self.campo("Mês", [self.dlg().content]))
                and self.visivel_no_dialogo(self.campo("Ano", [self.dlg().content])))

    def preencher(self, nome="Curso", valor="200", data=(2026, 10, 5)):
        for rotulo, v in (("Nome da conta", nome), ("Valor", valor)):
            c = self.campo(rotulo)
            c.value = v
            if c.on_change:
                c.on_change(Evento(self.pagina, c))
        seletor = next(o for o in self.pagina.overlay if isinstance(o, ft.DatePicker))
        seletor.value = datetime(*data)
        seletor.on_change(Evento(self.pagina, seletor))

    def salvar(self):
        self.clicar(next(b for b in self.controles(ft.Button) if b.content == "Salvar conta"))

    # 1. abertura e fechamento
    def test_estado_inicial_com_orientacao_e_sem_dialogo(self):
        campo = self.campo("Recorrência")
        self.assertEqual(campo.value, "Escolha o tipo da conta")
        self.assertEqual(campo.color, CLARO["texto_secundario"])
        self.assertEqual(self.pagina.dialogos, [])

    def test_abre_pelo_campo_e_pela_seta_e_fecha(self):
        for pelo_campo in (True, False):
            d = self.abrir(pelo_campo)
            self.assertIsInstance(d, ft.AlertDialog)
            self.assertTrue(d.modal)
            self.assertEqual(d.title.value, "Configurar recorrência")
            textos = [c.value for c in percorrer(d.content) if isinstance(c, ft.Text)]
            self.assertIn("Escolha como esta conta deverá se repetir.", textos)
            self.assertEqual([b.content for b in d.actions], ["Cancelar", "Confirmar"])
            self.cancelar()
            self.assertEqual(self.abertos(), [])

    def test_formulario_nao_muda_ao_abrir(self):
        antes = [id(c) for c in self.controles()]
        self.abrir()
        self.assertEqual([id(c) for c in self.controles()], antes)      # nada entra no cartão
        self.cancelar()
        self.assertEqual([id(c) for c in self.controles()], antes)

    # 2-4. tipos, sem término, Mês e Ano
    def test_unica_por_padrao_sem_termino_oculto(self):
        self.abrir()
        self.assertEqual(self.selecionado(), ["unica"])
        self.assertFalse(self.chave_visivel())
        self.assertFalse(self.mes_ano_visiveis())

    def test_alternancia_e_sem_data_de_termino(self):
        self.abrir()
        for valor in ("mensal", "anual", "unica", "mensal"):
            self.tipo(valor)
            self.assertEqual(self.selecionado(), [valor])
            self.assertEqual(self.chave_visivel(), valor != "unica")
            self.assertEqual(self.mes_ano_visiveis(), valor != "unica")
        self.assertEqual((self.campo("Mês", [self.dlg().content]).value,
                          self.campo("Ano", [self.dlg().content]).value), ("9", "2026"))   # mês e ano atuais
        self.ligar_sem_termino(True)
        self.assertFalse(self.mes_ano_visiveis())
        self.ligar_sem_termino(False)
        self.assertTrue(self.mes_ano_visiveis())
        self.ligar_sem_termino(True)
        self.tipo("unica")
        self.assertFalse(self.chave_visivel())
        self.tipo("anual")
        self.assertTrue(self.chave_visivel())
        self.assertFalse(self.mes_ano_visiveis())                          # chave ligada continua ligada

    # 5. Cancelar
    def test_cancelar_nao_aplica(self):
        self.abrir()
        self.tipo("mensal")
        self.escolher("Mês", "5")
        self.escolher("Ano", "2027")
        self.cancelar()
        self.assertEqual(self.campo("Recorrência").value, "Escolha o tipo da conta")  # nada confirmado
        self.abrir()
        self.assertEqual(self.selecionado(), ["unica"])
        self.tipo("mensal")
        self.assertEqual((self.campo("Mês", [self.dlg().content]).value,
                          self.campo("Ano", [self.dlg().content]).value), ("9", "2026"))

    def test_cancelar_depois_de_confirmado_volta_ao_confirmado(self):
        self.abrir()
        self.tipo("mensal")
        self.escolher("Mês", "5")
        self.escolher("Ano", "2027")
        self.confirmar()
        self.abrir()
        self.tipo("anual")
        self.ligar_sem_termino(True)
        self.cancelar()
        self.assertEqual(self.campo("Recorrência").value, "Mensal até maio de 2027")
        self.abrir()
        self.assertEqual(self.selecionado(), ["mensal"])
        self.assertFalse(self.no_dialogo("sem_termino_recorrencia").value)
        self.assertTrue(self.mes_ano_visiveis())

    # 6-7. Confirmar e reabrir
    def test_confirmar_atualiza_o_resumo_e_reabre_com_o_confirmado(self):
        self.abrir()
        self.tipo("anual")
        self.ligar_sem_termino(True)
        self.confirmar()
        campo = self.campo("Recorrência")
        self.assertEqual(campo.value, "Anual, sem término")
        self.assertEqual(campo.color, CLARO["texto_principal"])
        self.abrir()
        self.assertEqual(self.selecionado(), ["anual"])
        self.assertTrue(self.no_dialogo("sem_termino_recorrencia").value)
        self.assertFalse(self.mes_ano_visiveis())

    def test_confirmar_unica_mostra_unica(self):
        self.abrir()
        self.confirmar()
        self.assertEqual(self.campo("Recorrência").value, "Única")

    def test_resumos_curtos(self):
        casos = [("unica", None, None, "Única"), ("mensal", True, None, "Mensal, sem término"),
                 ("mensal", False, ("3", "2027"), "Mensal até março de 2027"),
                 ("anual", True, None, "Anual, sem término"),
                 ("anual", False, ("12", "2028"), "Anual até dezembro de 2028")]
        for tipo, sem, termino, texto in casos:
            with self.subTest(texto):
                self.abrir()
                self.tipo(tipo)
                if sem is not None:
                    self.ligar_sem_termino(sem)
                if termino:
                    self.escolher("Mês", termino[0])
                    self.escolher("Ano", termino[1])
                self.confirmar()
                self.assertEqual(self.campo("Recorrência").value, texto)

    # 8. término guardado ao passar por Única
    def test_termino_guardado_ao_passar_por_unica(self):
        self.abrir()
        self.tipo("mensal")
        self.escolher("Mês", "5")
        self.escolher("Ano", "2027")
        self.tipo("unica")
        self.tipo("anual")                                                   # na mesma abertura
        self.assertEqual((self.campo("Mês", [self.dlg().content]).value,
                          self.campo("Ano", [self.dlg().content]).value), ("5", "2027"))
        self.tipo("unica")
        self.confirmar()
        self.assertEqual(self.campo("Recorrência").value, "Única")
        self.abrir()                                                         # em outra abertura
        self.tipo("anual")
        self.assertEqual((self.campo("Mês", [self.dlg().content]).value,
                          self.campo("Ano", [self.dlg().content]).value), ("5", "2027"))
        self.confirmar()
        self.assertEqual(self.campo("Recorrência").value, "Anual até maio de 2027")

    # 9. nada gravado antes do Salvar; Salvar grava o confirmado
    def test_confirmar_nao_grava_no_banco(self):
        self.preencher()
        self.abrir()
        self.tipo("mensal")
        self.confirmar()
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas")[0][0], 0)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM series_recorrencia")[0][0], 0)

    def test_salvar_mensal_com_termino(self):
        self.preencher()
        self.abrir()
        self.tipo("mensal")
        self.escolher("Mês", "12")
        self.escolher("Ano", "2026")
        self.confirmar()
        self.salvar()
        self.assertEqual(self.consultar("SELECT frequencia, data_termino FROM series_recorrencia"),
                         [("mensal", "2026-12")])

    def test_salvar_unica_depois_de_mensal_nao_aplica_termino(self):
        self.preencher()
        self.abrir()
        self.tipo("mensal")
        self.escolher("Mês", "12")
        self.escolher("Ano", "2026")
        self.tipo("unica")
        self.confirmar()
        self.salvar()
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM series_recorrencia")[0][0], 0)
        self.assertEqual(self.consultar("SELECT nome, serie_id FROM contas"), [("Curso", None)])

    def test_salvar_sem_abrir_grava_unica(self):
        self.preencher()
        self.salvar()
        self.assertEqual(self.consultar("SELECT nome, serie_id FROM contas"), [("Curso", None)])

    def test_salvar_ignora_o_que_foi_cancelado(self):
        self.preencher()
        self.abrir()
        self.tipo("anual")
        self.ligar_sem_termino(True)
        self.cancelar()
        self.salvar()
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM series_recorrencia")[0][0], 0)

    def test_termino_anterior_continua_conferido_so_no_salvar(self):
        self.preencher(data=(2026, 10, 5))
        self.abrir()
        self.tipo("mensal")
        self.escolher("Mês", "9")
        self.escolher("Ano", "2026")
        self.confirmar()                                                     # o diálogo não valida
        self.assertEqual(self.abertos(), [])
        self.salvar()
        erros = [t.value for t in self.controles(ft.Text) if t.color == CLARO["texto_erro"] and t.value]
        self.assertEqual(erros, ["O término não pode ser anterior à data de vencimento inicial."])
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM contas")[0][0], 0)

    # 10. teclado e nomes acessíveis
    def test_nomes_acessiveis_e_foco(self):
        campo = self.campo("Recorrência")
        seta = campo.suffix_icon
        self.assertIsInstance(seta, ft.IconButton)                           # focável (Tab; Enter/Espaço)
        self.assertEqual(seta.icon.semantics_label, "Escolher recorrência")
        self.assertFalse(campo.can_request_focus)                            # o foco vai para a seta
        self.pagina.run_task.reset_mock()
        self.abrir()
        foco_ao_abrir = self.pagina.run_task.call_args[0][1]
        self.assertEqual(foco_ao_abrir.data, "tipo_recorrencia_unica")         # foco na opção confirmada
        for v in ("unica", "mensal", "anual"):
            self.assertIsInstance(self.no_dialogo(f"tipo_recorrencia_{v}"), ft.Button)
        self.assertEqual([self.no_dialogo(f"tipo_recorrencia_{v}").content for v in ("unica", "mensal", "anual")],
                         ["Única", "Mensal", "Anual"])
        for acao in ("Cancelar", "Confirmar"):
            with self.subTest(acao):
                self.clicar(self.acao(acao))
                self.assertIs(self.pagina.run_task.call_args[0][1], seta)    # o foco volta para a seta
                self.abrir()


class TestMesmoPadraoDeEditar(Base):
    """A estrutura do diálogo novo é a de "Transformar em recorrente" (Editar)."""

    def assinatura(self, d):
        col = d.content
        partes = col.controls
        texto, linha_tipo, linha_chave, linha_termino = partes[:4]
        acao_cancelar, acao_confirmar = d.actions
        return {
            "modal": d.modal, "fundo": d.bgcolor, "titulo": (type(d.title), d.title.color, d.title.size),
            "coluna": (type(col), col.tight, col.spacing), "texto": (type(texto), texto.color, texto.size),
            "linha_tipo": (type(linha_tipo), linha_tipo.spacing,
                           [c.expand for c in linha_tipo.controls]),
            "linha_chave": (linha_chave.alignment, [type(c) for c in linha_chave.controls],
                            linha_chave.controls[0].size, linha_chave.controls[0].color,
                            linha_chave.controls[1].active_color),
            "linha_termino": (linha_termino.spacing,
                              [(type(c), c.label, c.expand, c.color, c.value) for c in linha_termino.controls]),
            "cancelar": (type(acao_cancelar), acao_cancelar.content, acao_cancelar.style.color),
            "confirmar": (type(acao_confirmar), acao_confirmar.bgcolor, acao_confirmar.color),
        }

    def test_mesma_estrutura_e_estilo(self):
        db.criar_conta_unica(self.usuario_id, "Internet", 400.0, "2026-09-20")
        self.entrar()
        linha = next(c for c in self.controles(ft.Container)
                     if c.data in ("linha_conta", "linha_conta_empilhada")
                     and "Internet" in [t.value for t in percorrer(c) if isinstance(t, ft.Text)])
        self.clicar(linha)
        self.clicar(next(c for c in self.controles(ft.Button) if c.content == "Editar"))
        menu = next(c for c in self.controles(ft.TextField) if c.label == "Recorrência").suffix_icon
        item = next(i for i in menu.items if i.content == "Transformar em recorrente")
        item.on_click(Evento(self.pagina, item))
        editar = self.pagina.dialogos[-1]
        self.assertEqual(editar.title.value, "Transformar em recorrente")

        self.entrar()
        self.clicar(next(c for c in self.controles(ft.Container) if c.data == "nova_conta"))
        campo = next(c for c in self.controles(ft.TextField) if c.label == "Recorrência")
        self.clicar(campo.suffix_icon)
        novo = self.pagina.dialogos[-1]
        # Para comparar a linha do término, as duas abertas em Mensal.
        next(c for c in percorrer(novo.content) if getattr(c, "data", None) == "tipo_recorrencia_mensal") \
            .on_click(Evento(self.pagina, None))

        a, b = self.assinatura(editar), self.assinatura(novo)
        # Diferenças intencionais: 3 opções (Única|Mensal|Anual) em vez de 2,
        # botões focáveis em vez de contêineres, rótulo "Confirmar" e nenhuma
        # mensagem de erro no diálogo (o término é conferido no Salvar).
        self.assertEqual(a["linha_tipo"][:2], b["linha_tipo"][:2])
        self.assertEqual(len(b["linha_tipo"][2]), 3)
        self.assertTrue(all(b["linha_tipo"][2]) and all(a["linha_tipo"][2]))
        for chave in ("modal", "fundo", "titulo", "coluna", "texto", "linha_chave", "linha_termino"):
            with self.subTest(chave):
                self.assertEqual(a[chave], b[chave])
        self.assertEqual(a["cancelar"], b["cancelar"])
        self.assertEqual((a["confirmar"][0], a["confirmar"][1:]), (b["confirmar"][0], b["confirmar"][1:]))
        self.assertEqual(b["confirmar"], (ft.Button, CLARO["acao_primaria"], CLARO["texto_sobre_acao"]))
        self.assertEqual(len(editar.content.controls), 5)                    # 5ª: mensagem de erro
        self.assertEqual(len(novo.content.controls), 5)                      # 5ª: mesma linha, sempre vazia
        reserva_editar, reserva_novo = editar.content.controls[4], novo.content.controls[4]
        self.assertEqual((type(reserva_editar), reserva_editar.size, reserva_editar.value, reserva_editar.color),
                         (type(reserva_novo), reserva_novo.size, reserva_novo.value, reserva_novo.color))
        self.assertEqual(novo.content.width, 548)
        # Chips de Editar: texto 13 negrito, raio 10, 12 px em cima e embaixo.
        chip = editar.content.controls[1].controls[0]
        estilo = next(c for c in percorrer(novo.content) if getattr(c, "data", None) == "tipo_recorrencia_mensal").style
        self.assertEqual((chip.content.size, chip.content.weight, chip.border_radius, chip.padding.top),
                         (estilo.text_style.size, estilo.text_style.weight, estilo.shape.radius, estilo.padding.top))
        self.assertEqual((chip.bgcolor, chip.content.color),
                         (estilo.bgcolor, estilo.color))                     # Mensal ativo nos dois


if __name__ == "__main__":
    unittest.main(verbosity=2)
