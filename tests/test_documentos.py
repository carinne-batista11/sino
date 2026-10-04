"""
ERS v6.0, Etapa 6 — Termos de Uso e Política de Privacidade dentro do Sino
(RF15, RF41, 5.37): texto aprovado em backend/documentos.py, exibido em
Ajustes > Sobre e privacidade e no cadastro, antes do aceite.

Fluxos reais sobre páginas falsas e bancos temporários v7: destinos dos
itens, Voltar, preservação do formulário de cadastro, mesmo texto nos dois
lugares, cores da sessão nos dois temas e a regra de aceite inalterada.
"""

import os
import sys
import unittest

import apoio_banco
from apoio_banco import db
from apoio_interface_codigos import ComServicoFalso
from test_cores import MINIMO_TEXTO, contraste
from test_sessao_tema import CLARO, ESCURO, TesteDeSessao, ft, percorrer
from test_tela_principal import Evento

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import documentos  # noqa: E402

CONTATO = ("Dúvidas, sugestões e relatos de problemas podem ser enviados para sino.lembrete.contas@gmail.com. "
           "Não envie senhas, arquivos do banco de dados ou informações financeiras pessoais.")
AUTORIA = "O Sino é um projeto pessoal de portfólio desenvolvido por Carinne Batista."


class TestConteudoAprovado(unittest.TestCase):
    def test_dois_documentos(self):
        self.assertEqual(list(documentos.DOCUMENTOS), ["termos", "politica"])
        self.assertEqual(documentos.DOCUMENTOS["termos"], ("Termos de Uso", documentos.TERMOS_DE_USO))
        self.assertEqual(documentos.DOCUMENTOS["politica"],
                         ("Política de Privacidade", documentos.POLITICA_DE_PRIVACIDADE))

    def test_autoria_data_e_contato(self):
        for chave, (_, texto) in documentos.DOCUMENTOS.items():
            with self.subTest(chave):
                self.assertIn(AUTORIA, texto)
                self.assertIn("Última atualização: 04/10/2026", texto)
                self.assertIn(CONTATO, texto)
                self.assertNotIn("PENDENTE", texto)

    def test_titulos(self):
        self.assertTrue(documentos.TERMOS_DE_USO.startswith("# Termos de Uso do Sino\n"))
        self.assertTrue(documentos.POLITICA_DE_PRIVACIDADE.startswith("# Política de Privacidade do Sino\n"))

    def test_limitacoes_atuais_declaradas(self):
        self.assertIn("demais informações não são criptografadas", documentos.POLITICA_DE_PRIVACIDADE)
        self.assertIn("remove os dados de todos os usuários daquela instalação", documentos.POLITICA_DE_PRIVACIDADE)

    def test_exclusao_da_conta_de_usuario_da_etapa_9(self):  # 5.39, RF43
        termos, politica = documentos.TERMOS_DE_USO, documentos.POLITICA_DE_PRIVACIDADE
        for texto in (termos, politica):
            self.assertNotIn("não existe a opção de excluir o usuário", texto)
            self.assertNotIn("**não está disponível** excluir o usuário", texto)
        self.assertIn("## 6. Sair da conta e excluir a conta", termos)
        self.assertIn("pede a senha atual e uma confirmação final", termos)
        self.assertIn("**não pode ser desfeita** pelo aplicativo", termos)
        self.assertIn("A exclusão **não apaga** as cópias de segurança (backups) já existentes", termos)
        # O que a exclusão não alcança e o limite do secure_delete, sem prometer apagamento completo.
        self.assertIn("(nome, e-mail e sua confirmação, senha protegida, data do aceite e tema)", politica)
        self.assertIn("Se algo falhar no meio, nada é apagado.", politica)
        self.assertIn("Os dados dos outros usuários da mesma instalação não são alterados.", politica)
        self.assertIn("A exclusão da conta de usuário **não alcança**:", politica)
        self.assertIn("continuam contendo seus dados até serem apagadas manualmente", politica)
        self.assertIn("ele não é apagado na exclusão da conta de usuário (item 8)", politica)
        self.assertIn("o Sino não pede a esses serviços que apaguem nada", politica)
        self.assertIn("Essa é uma medida adicional: não garante que a informação não possa ser recuperada", politica)
        self.assertIn("Excluir itens ou a conta de usuário no aplicativo não apaga essas cópias.", politica)
        self.assertNotRegex(politica, r"(?i)apagad[ao]s? (completa|definitiva)mente|eliminação completa")

    def test_codigos_por_email_da_etapa_8(self):  # 5.31, 5.32, 5.35
        termos, politica = documentos.TERMOS_DE_USO, documentos.POLITICA_DE_PRIVACIDADE
        # o que deixou de ser verdade não pode continuar declarado
        self.assertNotIn("**não verifica** se o endereço existe", termos)
        self.assertNotIn("não é possível recuperar uma senha esquecida", termos)
        self.assertNotIn("não estão disponíveis**: alterar o e-mail", politica)
        # regras 5.32 iguais às do serviço
        self.assertIn("Cada código vale por 10 minutos, aceita até 5 tentativas e só pode ser usado uma vez; "
                      "um novo código pode ser pedido depois de 60 segundos e invalida o anterior.", termos)
        # estado atual: serviço não publicado, login local
        self.assertIn("**Nesta versão, o serviço ainda não foi publicado para uso por outras pessoas**", termos)
        self.assertIn("Entrar com uma conta já existente continua funcionando sem o serviço.", termos)
        self.assertIn("**Nesta versão, o serviço de códigos ainda não foi publicado para uso por outras pessoas.**",
                      politica)
        # forma de guarda conferida no código do serviço e da caixa de demonstração
        self.assertNotIn("só em forma protegida", politica)
        self.assertIn("resumos de mão única (HMAC-SHA256)", politica)
        self.assertIn("Isso não é criptografia reversível", politica)
        self.assertIn("gravada como **texto legível** em um arquivo com acesso restrito", politica)
        self.assertIn("não comprova acesso ao endereço informado", politica)
        # demonstração: tratamento local, sem afirmação absoluta; envio real x demonstração; neutralidade limitada
        for texto in (termos, politica):
            self.assertNotIn("nada sai dele", texto)
            self.assertIn("os dados do fluxo de códigos são tratados localmente, sem envio ao provedor de e-mail",
                          texto)
        self.assertIn("informar o código recebido demonstra acesso à mensagem enviada àquele endereço", termos)
        self.assertIn("apenas conclui o fluxo demonstrativo e não comprova acesso ao e-mail", termos)
        self.assertIn("não revela se o endereço corresponde a uma conta que pode recuperar a senha", termos)
        self.assertNotIn("sempre a mesma", termos)
        self.assertIn("Esta política será atualizada antes da publicação.", politica)
        self.assertIn("O Sino não envia nome, senha, informações financeiras nem o arquivo do banco.", politica)

    def test_regras_de_senha_da_etapa_7(self):  # 5.33, 5.34
        termos = documentos.TERMOS_DE_USO
        self.assertIn(f"Toda nova senha precisa ter **pelo menos {db.SENHA_MINIMO} caracteres** e não pode "
                      "conter espaços. Senhas criadas antes dessa regra continuam permitindo a entrada no "
                      "aplicativo.", termos)
        for frase_antiga in ("formada apenas por espaços", "inclusive espaços", "exatamente como você a digita"):
            self.assertNotIn(frase_antiga, termos)
        self.assertIn("Em Ajustes, você pode alterar sua senha informando a senha atual e confirmando a nova, "
                      "que precisa ser diferente da atual.", termos)
        self.assertIn("alterar seu nome e sua senha e escolher o tema", documentos.POLITICA_DE_PRIVACIDADE)

    def test_alterar_senha_nao_aparece_como_indisponivel(self):
        self.assertNotIn("alterar o e-mail ou a senha", documentos.TERMOS_DE_USO)
        self.assertNotIn("alterar ou recuperar a senha", documentos.POLITICA_DE_PRIVACIDADE)
        for chave, (_, texto) in documentos.DOCUMENTOS.items():
            with self.subTest(chave):
                for paragrafo in texto.split("\n\n"):
                    if "não estão disponíveis" in paragrafo or "não é possível" in paragrafo:
                        self.assertNotRegex(paragrafo, r"alterar (o e-mail ou )?a senha|alterar ou recuperar")


class TesteDeDocumentos(TesteDeSessao):
    @staticmethod
    def clicar(pagina, controle):
        controle.on_click(Evento(pagina, controle))

    def documento_aberto(self, pagina):
        cartao = next((c for c in self.controles(pagina) if str(getattr(c, "data", "")).startswith("documento_")), None)
        if cartao is None:
            return None, None
        return cartao.data.removeprefix("documento_"), cartao.content

    def voltar(self, pagina):
        voltar = next(b for b in self.controles(pagina, ft.TextButton) if b.content == "Voltar")
        self.clicar(pagina, voltar)

    def assert_cores_da_sessao(self, pagina, paleta):
        chave, markdown = self.documento_aberto(pagina)
        cartao = next(c for c in self.controles(pagina) if getattr(c, "data", None) == f"documento_{chave}")
        self.assertEqual(cartao.bgcolor, paleta["fundo_card"])
        folha = markdown.md_style_sheet
        for estilo in (folha.p_text_style, folha.h1_text_style, folha.h2_text_style, folha.strong_text_style,
                       folha.em_text_style, folha.list_bullet_text_style, folha.code_text_style, folha.a_text_style):
            self.assertEqual(estilo.color, paleta["texto_principal"])
        self.assertGreaterEqual(contraste(paleta["texto_principal"], paleta["fundo_card"]), MINIMO_TEXTO)
        self.assertGreaterEqual(contraste(folha.code_text_style.color, folha.code_text_style.bgcolor), MINIMO_TEXTO)
        voltar = next(b for b in self.controles(pagina, ft.TextButton) if b.content == "Voltar")
        self.assertEqual(voltar.style.color, paleta["texto_principal"])
        self.assertGreaterEqual(contraste(voltar.style.color, paleta["fundo_pagina"]), MINIMO_TEXTO)

    def assert_documento_com_rolagem(self, pagina, chave):
        aberto, markdown = self.documento_aberto(pagina)
        self.assertEqual(aberto, chave)
        self.assertIsInstance(markdown, ft.Markdown)
        self.assertIs(markdown.value, documentos.DOCUMENTOS[chave][1])   # a mesma fonte
        self.assertFalse(markdown.auto_follow_links)                      # e-mail não vira ação
        self.assertEqual(markdown.extension_set, ft.MarkdownExtensionSet.NONE)
        rolagem = next(c for c in self.controles(pagina, ft.Column) if c.scroll == ft.ScrollMode.AUTO)
        self.assertIn(markdown, list(percorrer(rolagem)))


class TestDocumentosEmAjustes(TesteDeDocumentos):
    def abrir_ajustes(self, email="bia@sino.com", senha="senha5678"):
        pagina, sessao = self.abrir_app()
        self.entrar(pagina, email, senha)
        self.abrir_aba(pagina, "Ajustes")
        return pagina, sessao

    def item(self, pagina, chave):
        return next(c for c in self.controles(pagina, ft.Container) if c.data == f"abrir_{chave}")

    def test_cada_item_abre_o_documento_correto_e_volta(self):  # RF41, CT98
        pagina, sessao = self.abrir_ajustes()
        for chave, (rotulo, _) in documentos.DOCUMENTOS.items():
            with self.subTest(chave):
                item = self.item(pagina, chave)
                self.assertIn(rotulo, [t.value for t in percorrer(item) if isinstance(t, ft.Text)])
                self.clicar(pagina, item)
                self.assert_documento_com_rolagem(pagina, chave)
                self.voltar(pagina)
                self.assertTrue(any(getattr(c, "data", None) == "tela_ajustes" for c in self.controles(pagina)))
                self.assertEqual(sessao.usuario["id"], self.bia)

    def test_cores_da_sessao_nos_dois_temas(self):
        for email, senha, paleta in (("bia@sino.com", "senha5678", CLARO), ("ana@sino.com", "senha1234", ESCURO)):
            for chave in documentos.DOCUMENTOS:
                with self.subTest(tema="claro" if paleta is CLARO else "escuro", documento=chave):
                    pagina, _ = self.abrir_ajustes(email, senha)
                    self.clicar(pagina, self.item(pagina, chave))
                    self.assert_cores_da_sessao(pagina, paleta)

    def test_documento_depois_de_trocar_o_tema(self):
        pagina, _ = self.abrir_ajustes()
        tema_escuro = next(c for c in self.controles(pagina, ft.Container) if c.data == "tema_escuro")
        self.clicar(pagina, tema_escuro)
        self.clicar(pagina, self.item(pagina, "politica"))
        self.assert_cores_da_sessao(pagina, ESCURO)


class TestDocumentosNoCadastro(ComServicoFalso, TesteDeDocumentos):
    def abrir_cadastro(self):
        pagina, sessao = self.abrir_app()
        alternar = next(b for b in self.controles(pagina, ft.TextButton) if b.content == "Não tem conta? Criar conta")
        self.clicar(pagina, alternar)
        return pagina, sessao

    def campos(self, pagina):
        return {c.label: c for c in self.controles(pagina, ft.TextField)}

    def aceite(self, pagina):
        return next(c for c in self.controles(pagina, ft.Checkbox))

    def link(self, pagina, chave):
        return next(b for b in self.controles(pagina, ft.TextButton)
                    if b.content == f"Ler {documentos.DOCUMENTOS[chave][0]}")

    def preencher(self, pagina):
        campos = self.campos(pagina)
        campos["Nome completo"].value = "Carla"
        campos["E-mail"].value = "carla@sino.com"
        campos["Senha"].value = "senha9999"
        campos["Confirmar senha"].value = "senha9999"

    def test_links_so_no_cadastro_antes_do_aceite(self):
        pagina, _ = self.abrir_app()
        linha = self.link(pagina, "termos")
        container = next(c for c in self.controles(pagina, ft.Row) if linha in c.controls)
        self.assertFalse(container.visible)                                 # modo Entrar
        pagina, _ = self.abrir_cadastro()
        container = next(c for c in self.controles(pagina, ft.Row) if self.link(pagina, "termos") in c.controls)
        self.assertTrue(container.visible)
        ordem = self.controles(pagina)
        self.assertLess(ordem.index(container), ordem.index(self.aceite(pagina)))

    def test_ler_e_voltar_preserva_o_formulario(self):
        pagina, sessao = self.abrir_cadastro()
        self.preencher(pagina)
        for chave in documentos.DOCUMENTOS:
            with self.subTest(chave):
                self.clicar(pagina, self.link(pagina, chave))
                self.assert_documento_com_rolagem(pagina, chave)
                self.assert_cores_da_sessao(pagina, CLARO)                   # autenticação: sempre Claro
                self.voltar(pagina)
                campos = self.campos(pagina)
                self.assertEqual((campos["Nome completo"].value, campos["E-mail"].value, campos["Senha"].value),
                                 ("Carla", "carla@sino.com", "senha9999"))
                self.assertIn("Crie sua conta", [t.value for t in self.controles(pagina, ft.Text)])
                self.assertIs(self.aceite(pagina).value, False)             # ler não aceita
                self.assertEqual(pagina.padding, 24)
                self.assertEqual(sessao.usuario, {"id": None, "nome": None})

    def test_aceite_marcado_antes_de_ler_continua_marcado(self):
        pagina, _ = self.abrir_cadastro()
        self.aceite(pagina).value = True
        self.clicar(pagina, self.link(pagina, "politica"))
        self.voltar(pagina)
        self.assertIs(self.aceite(pagina).value, True)

    def test_regra_de_aceite_inalterada_depois_de_ler(self):  # RF15
        pagina, _ = self.abrir_cadastro()
        self.preencher(pagina)
        self.clicar(pagina, self.link(pagina, "termos"))
        self.voltar(pagina)
        criar = next(b for b in self.controles(pagina, ft.Button) if b.content == "Criar conta")
        self.clicar(pagina, criar)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM usuarios WHERE email = 'carla@sino.com'")[0][0], 0)

        self.aceite(pagina).value = True
        self.clicar(pagina, criar)
        pagina.executar_pendentes()
        # Etapa 8: a conta só é criada depois do código do e-mail.
        self.campo(pagina, "Código").value = self.servidor.ultimo_codigo("carla@sino.com")
        self.clicar(pagina, self.botao(pagina, "Confirmar"))
        pagina.executar_pendentes()
        linhas = self.consultar("SELECT termos_aceitos_em FROM usuarios WHERE email = 'carla@sino.com'")
        self.assertEqual(linhas, [(self.HOJE.isoformat(),)])

    def test_usuarios_existentes_nao_mudam(self):
        antes = self.consultar("SELECT id, termos_aceitos_em FROM usuarios ORDER BY id")
        pagina, _ = self.abrir_cadastro()
        self.clicar(pagina, self.link(pagina, "termos"))
        self.voltar(pagina)
        self.entrar_depois_de_voltar(pagina)
        self.assertEqual(self.consultar("SELECT id, termos_aceitos_em FROM usuarios ORDER BY id"), antes)

    def entrar_depois_de_voltar(self, pagina):
        alternar = next(b for b in self.controles(pagina, ft.TextButton) if b.content == "Já tem conta? Entrar")
        self.clicar(pagina, alternar)
        self.entrar(pagina, "ana@sino.com", "senha1234")      # login continua funcionando, sem novo aceite
        self.assertIn("Olá,", [t.value for t in self.controles(pagina, ft.Text)])


class TestMesmoTextoNosDoisLugares(TesteDeDocumentos):
    def texto_exibido(self, pagina):
        return self.documento_aberto(pagina)[1].value

    def test_cadastro_e_ajustes_usam_a_mesma_fonte(self):
        for chave, (rotulo, texto) in documentos.DOCUMENTOS.items():
            with self.subTest(chave):
                pagina, _ = self.abrir_app()
                alternar = next(b for b in self.controles(pagina, ft.TextButton)
                                if b.content == "Não tem conta? Criar conta")
                self.clicar(pagina, alternar)
                self.clicar(pagina, next(b for b in self.controles(pagina, ft.TextButton)
                                         if b.content == f"Ler {rotulo}"))
                no_cadastro = self.texto_exibido(pagina)

                pagina, _ = self.abrir_app()
                self.entrar(pagina, "bia@sino.com", "senha5678")
                self.abrir_aba(pagina, "Ajustes")
                self.clicar(pagina, next(c for c in self.controles(pagina, ft.Container) if c.data == f"abrir_{chave}"))
                em_ajustes = self.texto_exibido(pagina)

                self.assertIs(no_cadastro, texto)
                self.assertIs(em_ajustes, texto)


if __name__ == "__main__":
    unittest.main()
