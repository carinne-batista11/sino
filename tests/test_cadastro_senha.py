"""
ERS v6.0, Etapa 7 (passo 2) — senha mínima no cadastro da interface (5.33,
RF37; CT81, CT82): a tela reutiliza database.validar_nova_senha antes de
qualquer outra coisa (desde a Etapa 8, antes de calcular o hash e de pedir o
código do e-mail), preserva os campos e o aceite numa recusa, usa a senha
exatamente como digitada e não aplica as regras novas ao login. Fluxos reais
sobre páginas falsas, bancos temporários e o serviço de códigos falso;
nenhuma janela é aberta.
"""

import hashlib
import unittest
from unittest import mock

from apoio_banco import db
from apoio_interface_codigos import ComServicoFalso
from test_sessao_tema import CLARO, TesteDeSessao, ft, main
from test_tela_principal import Evento

EMOJI_COMPOSTO = "👩‍💻"  # 3 pontos de código, 1 caractere percebido
MENSAGEM_CURTA = "A senha deve ter pelo menos 8 caracteres."
MENSAGEM_ESPACOS = "A senha não pode conter espaços."
MENSAGEM_ACEITE = "Você precisa aceitar os Termos de Uso e a Política de Privacidade para criar sua conta."


class TesteDeCadastro(ComServicoFalso, TesteDeSessao):
    @staticmethod
    def clicar(pagina, controle):
        controle.on_click(Evento(pagina, controle))

    def botao_texto(self, pagina, rotulo):
        return next(b for b in self.controles(pagina, ft.TextButton) if b.content == rotulo)

    def campos(self, pagina):
        return {c.label: c for c in self.controles(pagina, ft.TextField)}

    def aceite(self, pagina):
        return next(c for c in self.controles(pagina, ft.Checkbox))

    def textos(self, pagina):
        return [t.value for t in self.controles(pagina, ft.Text)]

    def mensagem(self, pagina, valor):
        return next(t for t in self.controles(pagina, ft.Text) if t.value == valor)

    def abrir_cadastro(self):
        pagina, sessao = self.abrir_app()
        self.clicar(pagina, self.botao_texto(pagina, "Não tem conta? Criar conta"))
        return pagina, sessao

    def cadastrar(self, pagina, senha, aceite=True, email="carla@sino.com", confirmacao=None):
        """Preenche e envia; se o código for pedido, confirma com o código recebido."""
        campos = self.campos(pagina)
        campos["Nome completo"].value = "Carla"
        campos["E-mail"].value = email
        campos["Senha"].value = senha
        campos["Confirmar senha"].value = senha if confirmacao is None else confirmacao
        self.aceite(pagina).value = aceite
        criar = next(b for b in self.controles(pagina, ft.Button) if b.content == "Criar conta")
        with mock.patch.object(main.database, "hash_de_nova_senha", wraps=db.hash_de_nova_senha) as hash_senha:
            self.clicar(pagina, criar)
            pagina.executar_pendentes()
            codigo = self.servidor.ultimo_codigo(email)
            if codigo is not None and "Confirme seu e-mail" in self.textos(pagina):
                self.campo(pagina, "Código").value = codigo
                self.clicar(pagina, self.botao(pagina, "Confirmar"))
                pagina.executar_pendentes()
        return hash_senha

    def usuarios_com_email(self, email="carla@sino.com"):
        return self.consultar("SELECT COUNT(*) FROM usuarios WHERE email = ?", (email,))[0][0]

    def assert_recusado_sem_chamar(self, pagina, hash_senha, mensagem, senha):
        hash_senha.assert_not_called()
        self.assertEqual(self.servidor.pedidos, [])                    # nenhum código pedido
        erro = self.mensagem(pagina, mensagem)
        self.assertEqual(erro.color, CLARO["texto_erro"])
        self.assertEqual(self.usuarios_com_email(), 0)
        campos = self.campos(pagina)
        self.assertEqual((campos["Nome completo"].value, campos["E-mail"].value, campos["Senha"].value),
                         ("Carla", "carla@sino.com", senha))           # nada é apagado nem cortado
        self.assertIn("Crie sua conta", self.textos(pagina))


class TestAjudaDaSenha(TesteDeCadastro):
    def test_ajuda_so_no_cadastro(self):
        pagina, _ = self.abrir_app()
        senha = self.campos(pagina)["Senha"]
        self.assertIsNone(senha.helper)                                # login
        self.clicar(pagina, self.botao_texto(pagina, "Não tem conta? Criar conta"))
        self.assertEqual(senha.helper, "Mínimo de 8 caracteres")
        self.clicar(pagina, self.botao_texto(pagina, "Já tem conta? Entrar"))
        self.assertIsNone(senha.helper)

    def test_sem_limite_maximo_no_campo(self):
        pagina, _ = self.abrir_cadastro()
        self.assertIsNone(self.campos(pagina)["Senha"].max_length)


class TestSenhaNoCadastro(TesteDeCadastro):
    def test_ct81_sete_caracteres_recusados_sem_chamar_o_banco(self):
        pagina, _ = self.abrir_cadastro()
        hash_senha = self.cadastrar(pagina, "a" * 7)
        self.assert_recusado_sem_chamar(pagina, hash_senha, MENSAGEM_CURTA, "a" * 7)
        self.assertIs(self.aceite(pagina).value, True)                 # aceite preservado

    def test_oito_caracteres_criam_a_conta(self):
        pagina, _ = self.abrir_cadastro()
        hash_senha = self.cadastrar(pagina, "a" * 8)
        hash_senha.assert_called_once_with("a" * 8)
        self.assertEqual(self.usuarios_com_email(), 1)
        self.assertIn("Conta criada com sucesso! Faça login para continuar.", self.textos(pagina))

    def test_emoji_composto_conta_um(self):
        pagina, _ = self.abrir_cadastro()
        sete = "abcdef" + EMOJI_COMPOSTO                               # 9 pontos de código
        hash_senha = self.cadastrar(pagina, sete)
        self.assert_recusado_sem_chamar(pagina, hash_senha, MENSAGEM_CURTA, sete)

        oito = "abcdefg" + EMOJI_COMPOSTO
        hash_senha = self.cadastrar(pagina, oito)
        hash_senha.assert_called_once()
        self.assertIsNotNone(db.verificar_login("carla@sino.com", oito))

    def test_qualquer_espaco_recusado(self):
        for senha in (" " * 8, "\t" * 10, " senha-boa", "senha-boa ", "senha boa1", "senha\tboa1",
                      "senha\nboa1", "senha\u00a0boa1"):
            with self.subTest(senha=repr(senha)):
                pagina, _ = self.abrir_cadastro()
                hash_senha = self.cadastrar(pagina, senha)
                self.assert_recusado_sem_chamar(pagina, hash_senha, MENSAGEM_ESPACOS, senha)

    def test_senha_valida_enviada_exatamente_como_digitada(self):
        senha = "Senhá-Ç#1"
        pagina, _ = self.abrir_cadastro()
        hash_senha = self.cadastrar(pagina, senha)
        hash_senha.assert_called_once_with(senha)
        self.assertIsNotNone(db.verificar_login("carla@sino.com", senha))
        self.assertIsNone(db.verificar_login("carla@sino.com", senha.lower()))

    def test_senha_invalida_e_aceite_desmarcado(self):
        pagina, _ = self.abrir_cadastro()
        hash_senha = self.cadastrar(pagina, "curta", aceite=False)
        self.assert_recusado_sem_chamar(pagina, hash_senha, MENSAGEM_CURTA, "curta")
        self.assertIs(self.aceite(pagina).value, False)

    def test_aceite_continua_obrigatorio_com_senha_valida(self):  # RF15
        pagina, _ = self.abrir_cadastro()
        hash_senha = self.cadastrar(pagina, "senha-valida", aceite=False)
        self.assert_recusado_sem_chamar(pagina, hash_senha, MENSAGEM_ACEITE, "senha-valida")

    def test_corrigir_a_senha_depois_da_recusa(self):
        pagina, _ = self.abrir_cadastro()
        self.cadastrar(pagina, "curta")
        hash_senha = self.cadastrar(pagina, "agora-sim")
        hash_senha.assert_called_once()
        self.assertEqual(self.usuarios_com_email(), 1)

    def test_documentos_continuam_acessiveis_antes_do_aceite(self):
        pagina, _ = self.abrir_cadastro()
        self.cadastrar(pagina, "curta", aceite=False)
        self.clicar(pagina, self.botao_texto(pagina, "Ler Termos de Uso"))
        self.clicar(pagina, self.botao_texto(pagina, "Voltar"))
        self.assertEqual(self.campos(pagina)["Senha"].value, "curta")
        self.assertIn(MENSAGEM_CURTA, self.textos(pagina))


MENSAGEM_NAO_COINCIDEM = "As senhas não coincidem."


class TestConfirmacaoDaSenha(TesteDeCadastro):
    """Etapa 10, Bloco 4: "Confirmar senha" no cadastro."""

    def test_campo_so_no_cadastro_com_o_padrao_do_campo_senha(self):
        pagina, _ = self.abrir_app()
        confirmar, senha = self.campos(pagina)["Confirmar senha"], self.campos(pagina)["Senha"]
        self.assertFalse(confirmar.visible)                                # login
        self.clicar(pagina, self.botao_texto(pagina, "Não tem conta? Criar conta"))
        self.assertTrue(confirmar.visible)
        for atributo in ("password", "can_reveal_password", "width", "color", "hint_text"):
            self.assertEqual(getattr(confirmar, atributo), getattr(senha, atributo), atributo)
        ordem = self.controles(pagina)
        self.assertEqual(ordem.index(confirmar), ordem.index(senha) + 1)  # logo abaixo da senha
        self.clicar(pagina, self.botao_texto(pagina, "Já tem conta? Entrar"))
        self.assertFalse(confirmar.visible)

    def test_senhas_diferentes_nao_pedem_codigo_nem_gravam(self):
        for confirmacao in ("senhaforte2", "", "senhaforte1 ", "SENHAFORTE1"):  # sem transformar nada
            with self.subTest(confirmacao=confirmacao):
                pagina, _ = self.abrir_cadastro()
                hash_senha = self.cadastrar(pagina, "senhaforte1", confirmacao=confirmacao)
                self.assert_recusado_sem_chamar(pagina, hash_senha, MENSAGEM_NAO_COINCIDEM, "senhaforte1")
                self.assertEqual(self.campos(pagina)["Confirmar senha"].value, confirmacao)  # nada apagado

    def test_regras_da_senha_continuam_antes_da_confirmacao(self):
        for senha, mensagem in (("curta", MENSAGEM_CURTA), ("senha forte", MENSAGEM_ESPACOS)):
            with self.subTest(senha=senha):
                pagina, _ = self.abrir_cadastro()
                hash_senha = self.cadastrar(pagina, senha, confirmacao="outra-coisa")
                self.assert_recusado_sem_chamar(pagina, hash_senha, mensagem, senha)

    def test_senhas_iguais_seguem_o_fluxo(self):
        pagina, _ = self.abrir_cadastro()
        self.cadastrar(pagina, "senhaforte1")
        self.assertEqual(self.usuarios_com_email(), 1)
        self.assertIsNotNone(db.verificar_login("carla@sino.com", "senhaforte1"))

    def test_corrigir_a_confirmacao_depois_da_recusa(self):
        pagina, _ = self.abrir_cadastro()
        self.cadastrar(pagina, "senhaforte1", confirmacao="senhaforte2")
        self.assertEqual(self.servidor.pedidos, [])
        self.cadastrar(pagina, "senhaforte1")
        self.assertEqual(self.usuarios_com_email(), 1)

    def test_confirmacao_esvaziada_ao_ir_para_o_codigo_e_ao_trocar_de_modo(self):
        pagina, _ = self.abrir_cadastro()
        confirmar = self.campos(pagina)["Confirmar senha"]
        confirmar.value = "qualquer"
        self.clicar(pagina, self.botao_texto(pagina, "Já tem conta? Entrar"))
        self.assertEqual(confirmar.value, "")
        self.clicar(pagina, self.botao_texto(pagina, "Não tem conta? Criar conta"))
        campos = self.campos(pagina)
        campos["Nome completo"].value, campos["E-mail"].value = "Carla", "carla@sino.com"
        campos["Senha"].value = campos["Confirmar senha"].value = "senhaforte1"
        self.aceite(pagina).value = True
        self.clicar(pagina, next(b for b in self.controles(pagina, ft.Button) if b.content == "Criar conta"))
        pagina.executar_pendentes()
        self.assertIn("Confirme seu e-mail", self.textos(pagina))
        self.assertEqual(confirmar.value, "")                             # a senha não fica em memória na tela


class TestLoginDeSenhasAntigas(TesteDeCadastro):
    """CT82: o login pela tela não aplica as regras de nova senha."""

    def entrar_com_hash(self, senha_hash, senha):
        self.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (senha_hash, self.bia))
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, "bia@sino.com", senha)
        return pagina, sessao

    def test_senha_curta_em_hash_legado(self):
        pagina, sessao = self.entrar_com_hash(hashlib.sha256("abc".encode("utf-8")).hexdigest(), "abc")
        self.assertEqual(sessao.usuario["id"], self.bia)
        self.assertIn("Olá,", self.textos(pagina))

    def test_senha_curta_em_hash_pbkdf2(self):
        _, sessao = self.entrar_com_hash(db._gerar_hash_senha("curta"), "curta")
        self.assertEqual(sessao.usuario["id"], self.bia)

    def test_senha_antiga_so_de_espacos(self):
        _, sessao = self.entrar_com_hash(db._gerar_hash_senha("   "), "   ")
        self.assertEqual(sessao.usuario["id"], self.bia)

    def test_senha_curta_errada_so_recebe_a_mensagem_de_login(self):
        pagina, sessao = self.entrar_com_hash(db._gerar_hash_senha("curta"), "outra")
        self.assertIsNone(sessao.usuario["id"])
        textos = self.textos(pagina)
        self.assertIn("E-mail ou senha incorretos.", textos)
        self.assertNotIn(MENSAGEM_CURTA, textos)

    def test_login_nao_chama_a_validacao_de_nova_senha(self):
        self.executar("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (db._gerar_hash_senha("curta"), self.bia))
        pagina, sessao = self.abrir_app()
        with mock.patch.object(main.database, "validar_nova_senha") as validar:
            self.entrar(pagina, "bia@sino.com", "curta")
        validar.assert_not_called()
        self.assertEqual(sessao.usuario["id"], self.bia)


if __name__ == "__main__":
    unittest.main()
