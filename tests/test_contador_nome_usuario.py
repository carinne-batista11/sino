"""
ERS v7.0, E5 (M5) — contador do nome do usuário oculto (5.46, RF01, RF35;
CT134; decisões M5-A e M5-B).

O contador "x/70" fica sempre oculto em "Nome completo" (Cadastro) e em
"Nome" (Editar nome, em Ajustes), nos dois temas; o limite de 70 caracteres
percebidos, a recusa do 71º, "Limite atingido" e o som continuam. Os
contadores dos demais campos (nome da conta, descrição, nome da categoria)
continuam visíveis. Fluxos reais da interface sobre páginas falsas e bancos
temporários; o som é simulado e nenhuma janela é aberta.
"""

import unittest
from unittest import mock

from apoio_banco import db
from test_cadastro_senha import EMOJI_COMPOSTO, TesteDeCadastro
from test_sessao_tema import ft, main
from test_tela_ajustes import TesteDeAjustes
from test_tela_principal import Evento

NOME_70 = "a" * 69 + EMOJI_COMPOSTO   # 70 caracteres percebidos


def som_simulado():
    """Substitui o som da recusa (a suíte nunca toca áudio)."""
    return mock.patch.object(main.aviso_sonoro.aviso_limite, "tocar", return_value=True)


class TestContadorOcultoNoCadastro(TesteDeCadastro):
    def campo_nome(self, pagina):
        return self.campos(pagina)["Nome completo"]

    @staticmethod
    def digitar(pagina, campo, valor):
        campo.value = valor
        campo.on_change(Evento(pagina, campo))

    def test_oculto_ao_abrir_e_ao_digitar(self):  # CT134
        pagina, _ = self.abrir_cadastro()
        campo = self.campo_nome(pagina)
        self.assertTrue(campo.visible)
        self.assertIsNone(campo.counter)
        self.digitar(pagina, campo, "Carla")
        self.assertIsNone(campo.counter)
        self.digitar(pagina, campo, NOME_70)
        self.assertEqual(campo.value, NOME_70)
        self.assertIsNone(campo.counter)
        self.assertIsNone(campo.helper)

    def test_71o_recusado_com_aviso_e_som(self):  # CT134
        pagina, _ = self.abrir_cadastro()
        campo = self.campo_nome(pagina)
        self.digitar(pagina, campo, NOME_70)
        with som_simulado() as tocar:
            self.digitar(pagina, campo, NOME_70 + "b")
        self.assertEqual(campo.value, NOME_70)
        self.assertEqual(campo.helper, "Limite atingido")
        self.assertIsNone(campo.counter)
        tocar.assert_called_once_with()

    def test_oculto_ao_alternar_entre_entrar_e_criar_conta(self):
        pagina, _ = self.abrir_cadastro()
        campo = self.campo_nome(pagina)
        with som_simulado():
            self.digitar(pagina, campo, NOME_70 + "b")          # deixa "Limite atingido" no campo
        self.clicar(pagina, self.botao_texto(pagina, "Já tem conta? Entrar"))
        self.assertFalse(campo.visible)
        self.assertEqual((campo.value, campo.counter, campo.helper), ("", None, None))
        self.clicar(pagina, self.botao_texto(pagina, "Não tem conta? Criar conta"))
        self.assertTrue(campo.visible)
        self.assertEqual((campo.value, campo.counter, campo.helper), ("", None, None))
        self.digitar(pagina, campo, "Carla")
        self.assertIsNone(campo.counter)


class TestContadorOcultoEmAjustes(TesteDeAjustes):
    def test_oculto_no_tema_escuro(self):  # CT134, nos dois temas
        pagina, _ = self.abrir_ajustes()
        self.clicar(pagina, self.opcao_tema(pagina, "escuro"))
        campo, _ = self.abrir_dialogo_nome(pagina)
        self.assertIsNone(campo.counter)
        with som_simulado() as tocar:
            self.digitar(pagina, campo, NOME_70 + "b")
        self.assertEqual((campo.value, campo.helper, campo.counter), ("Bia", "Limite atingido", None))
        tocar.assert_called_once_with()


class TestDemaisContadoresVisiveis(TesteDeAjustes):
    """5.46: só o nome do usuário perde o contador."""

    def campos_da_pagina(self, pagina):
        return {c.label: c for c in self.controles(pagina, ft.TextField)}

    def test_nova_conta_mantem_os_contadores(self):
        pagina, _ = self.abrir_ajustes()
        self.abrir_aba(pagina, "Início")
        fab = next(c for c in self.controles(pagina, ft.Container) if c.data == "nova_conta")
        self.clicar(pagina, fab)
        campos = self.campos_da_pagina(pagina)
        self.assertEqual(campos["Nome da conta"].counter, "0/30")
        self.assertEqual(campos["Descrição (opcional)"].counter, "0/1000")   # v7.0 5.45 (E6)
        self.digitar(pagina, campos["Nome da conta"], "Aluguel")
        self.assertEqual(campos["Nome da conta"].counter, "7/30")

    def test_categoria_mantem_o_contador(self):
        db.criar_categoria(self.bia, "Casa")                 # banco temporário
        pagina, _ = self.abrir_ajustes()
        self.abrir_aba(pagina, "Categorias")
        editar = next(b for b in self.controles(pagina, ft.IconButton) if b.icon == ft.Icons.EDIT)
        self.clicar(pagina, editar)
        campo = next(c for c in self.no_dialogo(pagina, ft.TextField) if c.label == "Nome da categoria")
        self.assertEqual((campo.value, campo.counter), ("Casa", "4/30"))


if __name__ == "__main__":
    unittest.main()
