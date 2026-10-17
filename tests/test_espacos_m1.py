"""
ERS v7.0, E9 (M1) — espaços e caracteres invisíveis no e-mail e nas senhas
(5.40, 5.41, 5.42; P13–P17; CT119–CT125; decisões E1–E4, S1 e S2).

Lista E1 de 31 caracteres; limpeza única do e-mail digitado só nas
extremidades (Login, Cadastro, "Esqueci minha senha" e novo e-mail em
Ajustes), com o campo mostrando a versão limpa ao enviar; mensagem própria
para caractere da lista no meio do e-mail (no login, só depois da recusa);
orientação sobre as pontas da senha depois de uma recusa nos quatro lugares
que conferem uma senha existente; senhas novas sem nenhum dos 31 caracteres.
Senhas existentes continuam comparadas exatamente, sem alterar hashes. Telas
reais sobre páginas falsas, cliente real do serviço sobre o ServidorFalso e
bancos temporários; nenhum envio real.
"""

import unittest
from unittest import mock

import flet as ft

from apoio_banco import db
from test_alterar_email_interface import BaseAlteracao
from test_tela_principal import Evento, percorrer

import espacos  # noqa: E402 -- database/ entra no caminho por apoio_banco

E1 = (["\u0009", "\u000a", "\u000b", "\u000c", "\u000d", "\u001c", "\u001d", "\u001e", "\u001f", "\u0085",
       " ", " ", " "] + [chr(c) for c in range(0x2000, 0x200B)]
      + [" ", " ", "　", " ", " ", "​", "﻿"])
MEIO_EMAIL = "Remova os espaços ou caracteres invisíveis do meio do e-mail."
PONTAS_SENHA = "Verifique se há espaços ou caracteres invisíveis no início ou no fim da senha."
SENHA_NOVA = "A senha não pode conter espaços nem caracteres invisíveis."
INCORRETOS = "E-mail ou senha incorretos."


class TestListaE1(unittest.TestCase):
    def test_31_caracteres_exatos(self):  # 5.40
        self.assertEqual(len(E1), 31)
        self.assertEqual(espacos.CARACTERES_E1, frozenset(E1))

    def test_29_do_python_mais_dois_invisiveis(self):  # 5.40
        do_python = {chr(c) for c in range(0x110000) if chr(c).isspace()}
        self.assertEqual(len(do_python), 29)
        self.assertEqual(espacos.CARACTERES_E1, do_python | {"​", "﻿"})

    def test_limpeza_so_nas_extremidades_e_repetida(self):  # 5.41 (E1)
        for caractere in E1:
            with self.subTest(caractere=hex(ord(caractere))):
                self.assertEqual(espacos.limpar_email_digitado(caractere + "a@b.com" + caractere), "a@b.com")
        self.assertEqual(espacos.limpar_email_digitado(" ﻿\t​ a@b.com  \n　"), "a@b.com")
        self.assertEqual(espacos.limpar_email_digitado(" a ​@b.com "), "a ​@b.com")  # meio intacto
        self.assertEqual(espacos.limpar_email_digitado("​﻿ "), "")
        self.assertEqual(espacos.limpar_email_digitado(None), "")

    def test_outros_caracteres_nao_sao_tratados(self):
        for caractere in ("‌", "‍", "⁠", "­", "᠎"):   # fora da lista
            with self.subTest(caractere=hex(ord(caractere))):
                self.assertEqual(espacos.limpar_email_digitado(caractere + "a@b.com"), caractere + "a@b.com")
                self.assertFalse(espacos.contem_caractere_e1("senha" + caractere + "boa"))

    def test_consultas(self):
        self.assertTrue(espacos.email_com_invisivel_no_meio(" a b@c.com "))
        self.assertFalse(espacos.email_com_invisivel_no_meio(" ab@c.com​"))
        self.assertTrue(espacos.tem_caractere_e1_nas_pontas("senha﻿"))
        self.assertTrue(espacos.tem_caractere_e1_nas_pontas(" senha"))
        self.assertFalse(espacos.tem_caractere_e1_nas_pontas("sen ha"))
        self.assertFalse(espacos.tem_caractere_e1_nas_pontas(""))


class TestSenhaNovaNaCamadaDeDados(unittest.TestCase):
    def test_recusa_os_31_em_qualquer_posicao(self):  # CT125, 5.42 (S2)
        for caractere in E1:
            for senha in (caractere + "senhaboa1", "senha" + caractere + "boa1", "senhaboa1" + caractere):
                with self.subTest(caractere=hex(ord(caractere)), posicao=senha.index(caractere)):
                    with self.assertRaises(db.SenhaComEspacosError) as recusa:
                        db.validar_nova_senha(senha)
                    self.assertEqual(str(recusa.exception), SENHA_NOVA)

    def test_outros_unicode_continuam_aceitos(self):
        for senha in ("Senhá-Ç#1", "senha‌boa1", "abcdefg👩‍💻"):
            with self.subTest(senha=repr(senha)):
                self.assertEqual(db.validar_nova_senha(senha), senha)   # intacta

    def test_ordem_das_regras_preservada(self):
        with self.assertRaises(db.SenhaComEspacosError):
            db.validar_nova_senha("a​")                            # curta e com invisível


class BaseM1(BaseAlteracao):
    """Ana (escuro) e Bia (claro) de TesteDeSessao; serviço de códigos falso."""

    def entrar_com(self, email, senha):
        pagina, _ = self.abrir_app()
        self.entrar(pagina, email, senha)
        return pagina

    def mensagem_do_login(self, pagina):
        return next(t.value for t in self.todos(pagina) if isinstance(t, ft.Text) and t.value
                    and t.value.startswith(("E-mail ou senha", "Preencha")))

    def na_tela_principal(self, pagina):
        return "Olá," in self.textos_visiveis(pagina)

    def hashes(self):
        return self.consultar("SELECT id, senha_hash FROM usuarios ORDER BY id")


class TestLogin(BaseM1):
    def test_extremidades_limpas_e_campo_atualizado(self):  # 5.41 (E1, E4)
        pagina = self.entrar_com("﻿​ bia@sino.com\t ", "senha5678")
        self.assertTrue(self.na_tela_principal(pagina))

    def test_campo_mostra_a_versao_limpa_mesmo_com_recusa(self):  # 5.41 (E4)
        pagina, _ = self.abrir_app()
        self.entrar(pagina, "  bia@sino.com　", "")
        self.assertEqual(self.campo(pagina, "E-mail").value, "bia@sino.com")
        self.assertEqual(self.mensagem_do_login(pagina), "Preencha e-mail e senha.")

    def test_meio_do_email_com_falha(self):  # CT121
        pagina = self.entrar_com("bia @sino.com", "senha5678")
        self.assertEqual(self.mensagem_do_login(pagina), INCORRETOS + "\n" + MEIO_EMAIL)
        self.assertEqual(self.campo(pagina, "E-mail").value, "bia @sino.com")   # meio preservado

    def test_conta_antiga_com_espaco_no_meio_entra(self):  # CT122
        self.executar("UPDATE usuarios SET email = ? WHERE id = ?", ("bia @sino.com", self.bia))
        pagina = self.entrar_com(" bia @sino.com ", "senha5678")
        self.assertTrue(self.na_tela_principal(pagina))
        self.assertEqual(self.consultar("SELECT email FROM usuarios WHERE id = ?", (self.bia,))[0][0],
                         "bia @sino.com")                                           # nada gravado

    def test_senha_com_espaco_no_fim_recusada_com_orientacao(self):  # CT123
        antes = self.hashes()
        for senha in ("senha5678 ", "​senha5678", "senha5678﻿"):
            with self.subTest(senha=repr(senha)):
                pagina = self.entrar_com("bia@sino.com", senha)
                self.assertFalse(self.na_tela_principal(pagina))
                self.assertEqual(self.mensagem_do_login(pagina), INCORRETOS + "\n" + PONTAS_SENHA)
        self.assertEqual(self.hashes(), antes)                                      # nenhum hash alterado

    def test_duas_orientacoes_sem_repetir_a_mensagem(self):  # 5.42
        pagina = self.entrar_com("bia @sino.com", " senha5678")
        self.assertEqual(self.mensagem_do_login(pagina), "\n".join([INCORRETOS, MEIO_EMAIL, PONTAS_SENHA]))

    def test_sem_orientacao_quando_nada_se_aplica(self):
        pagina = self.entrar_com("bia@sino.com", "sen ha5678")                    # espaço só no meio
        self.assertEqual(self.mensagem_do_login(pagina), INCORRETOS)

    def test_orientacao_nao_depende_da_conta(self):  # neutralidade
        existente = self.entrar_com("bia@sino.com", "errada ")
        inexistente = self.entrar_com("ninguem@sino.com", "errada ")
        self.assertEqual(self.mensagem_do_login(existente), self.mensagem_do_login(inexistente))

    def test_senha_antiga_com_espaco_aceita_sem_orientacao(self):  # CT124
        antiga = " senha antiga "
        self.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (db._gerar_hash_senha(antiga), self.bia))
        pagina = self.entrar_com("bia@sino.com", antiga)
        self.assertTrue(self.na_tela_principal(pagina))
        self.assertNotIn(PONTAS_SENHA, self.textos_visiveis(pagina))


class TestCadastro(BaseM1):
    def abrir_cadastro(self):
        pagina, _ = self.abrir_app()
        self.acionar(pagina, self.botao(pagina, "Não tem conta? Criar conta"))
        return pagina

    def preencher(self, pagina, email, senha="senhaforte1"):
        self.campo(pagina, "Nome completo").value = "Carla"
        self.campo(pagina, "E-mail").value = email
        self.campo(pagina, "Senha").value = senha
        self.campo(pagina, "Confirmar senha").value = senha
        next(c for c in self.todos(pagina) if isinstance(c, ft.Checkbox)).value = True
        self.acionar(pagina, self.botao(pagina, "Criar conta"))
        pagina.executar_pendentes()

    def test_extremidades_limpas_e_codigo_pedido_ao_endereco_limpo(self):  # CT119
        pagina = self.abrir_cadastro()
        campo = self.campo(pagina, "E-mail")
        self.preencher(pagina, " ﻿carla@sino.com \t")
        self.assertEqual(campo.value, "carla@sino.com")
        self.assertEqual([p["email"] for p in self.servidor.pedidos], ["carla@sino.com"])
        self.assertIn("Enviamos um código de 6 dígitos para carla@sino.com. Digite-o abaixo para concluir o cadastro.",
                      self.textos_visiveis(pagina))

    def test_campo_limpo_mesmo_com_outra_recusa(self):  # 5.41 (E4)
        pagina = self.abrir_cadastro()
        self.preencher(pagina, " carla@sino.com ", senha="curta")
        self.assertEqual(self.campo(pagina, "E-mail").value, "carla@sino.com")
        self.assertIn("A senha deve ter pelo menos 8 caracteres.", self.textos_visiveis(pagina))
        self.assertEqual(self.servidor.pedidos, [])

    def test_meio_do_email_recusado_sem_consultar(self):  # CT120
        with mock.patch.object(db, "email_em_uso", side_effect=AssertionError("consultou")):
            for email in ("carla @sino.com", "carla@​sino.com", " carla @sino.com "):
                with self.subTest(email=repr(email)):
                    pagina = self.abrir_cadastro()
                    self.preencher(pagina, email)
                    self.assertIn(MEIO_EMAIL, self.textos_visiveis(pagina))
                    self.assertIn("Crie sua conta", self.textos_visiveis(pagina))
        self.assertEqual(self.servidor.pedidos, [])

    def test_senha_nova_com_invisivel(self):  # CT125
        for senha in ("senha​forte", " senhaforte", "senhaforte﻿"):
            with self.subTest(senha=repr(senha)):
                pagina = self.abrir_cadastro()
                self.preencher(pagina, "carla@sino.com", senha=senha)
                self.assertIn(SENHA_NOVA, self.textos_visiveis(pagina))
        self.assertEqual(self.servidor.pedidos, [])


class TestRecuperacao(BaseM1):
    def setUp(self):
        super().setUp()
        self.executar("UPDATE usuarios SET email_verificado = 1 WHERE id = ?", (self.bia,))

    def pedir(self, email):
        pagina, _ = self.abrir_app()
        self.acionar(pagina, self.botao(pagina, "Esqueci minha senha"))
        campo = self.campo(pagina, "E-mail")
        campo.value = email
        self.acionar(pagina, self.botao(pagina, "Enviar código"))
        pagina.executar_pendentes()
        return pagina, campo

    def test_extremidades_limpas(self):  # 5.41
        pagina, campo = self.pedir("​ bia@sino.com ")
        self.assertEqual(campo.value, "bia@sino.com")
        self.assertEqual([p["email"] for p in self.servidor.pedidos], ["bia@sino.com"])

    def test_meio_recusado_antes_de_consultar(self):  # CT120, neutralidade
        with mock.patch.object(db, "existe_conta_verificada", side_effect=AssertionError("consultou")):
            for email in ("bia @sino.com", "ninguem　@sino.com"):
                with self.subTest(email=repr(email)):
                    pagina, _ = self.pedir(email)
                    self.assertIn(MEIO_EMAIL, self.textos_visiveis(pagina))
        self.assertEqual(self.servidor.pedidos, [])

    def test_nova_senha_com_invisivel(self):  # CT125
        pagina, _ = self.pedir("bia@sino.com")
        self.campo(pagina, "Código").value = self.servidor.ultimo_codigo("bia@sino.com")
        self.acionar(pagina, self.botao(pagina, "Confirmar código"))
        pagina.executar_pendentes()
        for campo in ("Nova senha", "Confirmar nova senha"):
            self.campo(pagina, campo).value = "nova​senha9"
        self.acionar(pagina, self.botao(pagina, "Redefinir senha"))
        pagina.executar_pendentes()
        self.assertIn(SENHA_NOVA, self.textos_visiveis(pagina))
        self.assertIsNotNone(db.verificar_login("bia@sino.com", "senha5678"))       # nada gravado


class TestAjustes(BaseM1):
    def dialogo(self, pagina):
        return [d for d in pagina.dialogos if d.open][-1]

    def erro(self, dialogo):
        return [t.value for t in percorrer(dialogo) if isinstance(t, ft.Text) and t.visible and t.value
                and ("incorreta" in t.value or "Verifique" in t.value)]

    def test_novo_email_extremidades_e_meio(self):  # CT120, 5.41 (E4)
        pagina, _ = self.abrir_ajustes()
        self.editar(pagina)
        self.pedir(pagina, novo=" bia nova@sino.com﻿")
        self.assertEqual(self.campo(pagina, "Novo e-mail").value, "bia nova@sino.com")
        self.assertIn(MEIO_EMAIL, self.textos_visiveis(pagina))
        self.assertEqual(self.servidor.pedidos, [])

        self.pedir(pagina, novo="　Bia.Nova@Sino.com\t")
        self.assertEqual(self.campo(pagina, "Novo e-mail").value, "Bia.Nova@Sino.com")
        self.assertEqual([p["email"] for p in self.servidor.pedidos], ["Bia.Nova@Sino.com"])

    def test_alterar_email_senha_recusada_com_orientacao(self):  # 5.42 (S1)
        pagina, _ = self.abrir_ajustes()
        self.editar(pagina)
        self.pedir(pagina, senha="senha5678 ")
        self.assertIn("A senha atual está incorreta.\n" + PONTAS_SENHA, self.textos_visiveis(pagina))
        self.pedir(pagina, senha="errada")
        self.assertIn("A senha atual está incorreta.", self.textos_visiveis(pagina))
        self.assertNotIn(PONTAS_SENHA, "\n".join(self.textos_visiveis(pagina)))
        self.assertEqual(self.servidor.pedidos, [])

    def test_alterar_senha_atual_recusada_com_orientacao(self):  # 5.42 (S1)
        pagina, _ = self.abrir_ajustes()
        item = next(c for c in self.todos(pagina) if isinstance(c, ft.Container) and c.data == "abrir_alterar_senha")
        self.acionar(pagina, item)
        dialogo = self.dialogo(pagina)
        campos = {c.label: c for c in percorrer(dialogo) if isinstance(c, ft.TextField)}
        antes = self.hashes()
        for atual, esperado in ((" senha5678", ["A senha atual está incorreta.\n" + PONTAS_SENHA]),
                                ("errada", ["A senha atual está incorreta."])):
            with self.subTest(atual=repr(atual)):
                for rotulo, valor in (("Senha atual", atual), ("Nova senha", "Nova-Senha#1"),
                                      ("Confirmar nova senha", "Nova-Senha#1")):
                    campos[rotulo].value = valor
                    campos[rotulo].on_change(Evento(pagina, campos[rotulo]))
                self.acionar(pagina, self.botao(pagina, "Salvar"))
                self.assertEqual(self.erro(dialogo), esperado)
        self.assertEqual(self.hashes(), antes)

    def test_alterar_senha_nova_com_invisivel(self):  # CT125
        pagina, _ = self.abrir_ajustes()
        item = next(c for c in self.todos(pagina) if isinstance(c, ft.Container) and c.data == "abrir_alterar_senha")
        self.acionar(pagina, item)
        dialogo = self.dialogo(pagina)
        campos = {c.label: c for c in percorrer(dialogo) if isinstance(c, ft.TextField)}
        for rotulo, valor in (("Senha atual", "senha5678"), ("Nova senha", "Nova﻿Senha#1"),
                              ("Confirmar nova senha", "Nova﻿Senha#1")):
            campos[rotulo].value = valor
            campos[rotulo].on_change(Evento(pagina, campos[rotulo]))
        self.acionar(pagina, self.botao(pagina, "Salvar"))
        self.assertIn(SENHA_NOVA, [t.value for t in percorrer(dialogo) if isinstance(t, ft.Text) and t.visible])

    def test_excluir_conta_senha_recusada_com_orientacao(self):  # 5.42 (S1)
        pagina, _ = self.abrir_ajustes()
        item = next(c for c in self.todos(pagina) if isinstance(c, ft.Container) and c.data == "abrir_excluir_conta")
        self.acionar(pagina, item)
        self.acionar(pagina, self.botao(pagina, "Continuar"))
        dialogo = self.dialogo(pagina)
        self.assertEqual(dialogo.data, "exclusao_senha")
        campo = next(c for c in percorrer(dialogo) if isinstance(c, ft.TextField))
        for senha, esperado in (("senha5678 ", ["A senha atual está incorreta.\n" + PONTAS_SENHA]),
                                ("errada", ["A senha atual está incorreta."])):
            with self.subTest(senha=repr(senha)):
                campo.value = senha
                campo.on_change(Evento(pagina, campo))
                self.acionar(pagina, self.botao(pagina, "Continuar"))
                self.assertEqual(self.dialogo(pagina).data, "exclusao_senha")
                self.assertEqual(self.erro(dialogo), esperado)
        self.assertEqual(len(self.consultar("SELECT id FROM usuarios")), 2)          # nada excluído


if __name__ == "__main__":
    unittest.main()
