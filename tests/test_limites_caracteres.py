"""
ERS v6.0, Etapa 2 — limites de caracteres (5.23, RF33, T5; CT59–CT62,
CT108, CT109).

A contagem usa o caractere percebido pelo usuário (`\\X`, módulo `regex`),
compartilhada pela interface e pela gravação (database/limites.py). Valores
acima do limite são recusados sem gravar nada; dados antigos acima do
limite nunca são cortados e só bloqueiam a gravação quando são enviados.
"""

import os
import sys
import unittest

import apoio_banco
from apoio_banco import TesteComBancoTemporario, db

import limites  # database/ já está no sys.path via apoio_banco

sys.path.insert(0, os.path.join(apoio_banco.RAIZ_PROJETO, "backend"))

import main  # noqa: E402

EMOJI_COMPOSTO = "👩‍💻"  # 👩‍💻: 3 pontos de código, 1 caractere percebido


class TestContarCaracteres(unittest.TestCase):
    def test_ascii_e_acentos(self):
        self.assertEqual(limites.contar_caracteres("Aluguel"), 7)
        self.assertEqual(limites.contar_caracteres("Ação"), 4)

    def test_acento_combinante_conta_um(self):
        self.assertEqual(limites.contar_caracteres("é"), 1)  # "é" em NFD

    def test_emojis_compostos_contam_um(self):
        for emoji in (EMOJI_COMPOSTO, "🇧🇷", "👍🏽", "👨‍👩‍👧‍👦", "❤️"):
            with self.subTest(emoji=emoji):
                self.assertEqual(limites.contar_caracteres(emoji), 1)

    def test_vazio_e_none(self):
        self.assertEqual(limites.contar_caracteres(""), 0)
        self.assertEqual(limites.contar_caracteres(None), 0)

    def test_quebra_de_linha_windows_conta_um(self):
        self.assertEqual(limites.contar_caracteres("a\r\nb"), 3)

    def test_limites_da_ers(self):
        self.assertEqual(
            (limites.LIMITE_NOME_USUARIO, limites.LIMITE_NOME_CONTA,
             limites.LIMITE_NOME_CATEGORIA, limites.LIMITE_DESCRICAO),
            (70, 30, 30, 500),
        )

    def test_interface_e_persistencia_usam_a_mesma_funcao(self):
        self.assertIs(db.contar_caracteres, limites.contar_caracteres)
        self.assertIs(db.LimiteDeCaracteresError, limites.LimiteDeCaracteresError)


class TestNormalizarDescricao(unittest.TestCase):
    def test_vazia_ou_so_espacos_vira_none(self):
        for texto in (None, "", "   ", "\n\t \n"):
            with self.subTest(texto=texto):
                self.assertIsNone(limites.normalizar_descricao(texto))

    def test_strip_nas_bordas_preserva_quebras_internas(self):
        self.assertEqual(limites.normalizar_descricao("  linha 1\n\nlinha 2 \n"), "linha 1\n\nlinha 2")


class TestMensagensDaInterface(unittest.TestCase):
    def test_erro_de_limite(self):
        self.assertIsNone(main.erro_de_limite("nome_conta", "a" * 30, 30))
        self.assertEqual(
            main.erro_de_limite("nome_conta", "a" * 31, 30),
            "O nome da conta pode ter no máximo 30 caracteres (atual: 31).",
        )

    def test_contador_por_grafemas(self):
        self.assertEqual(main.texto_contador("Conta " + EMOJI_COMPOSTO, 30), "7/30")

    def test_texto_para_limite(self):
        self.assertEqual(main.texto_para_limite("nome_conta", "  Luz  "), "Luz")
        self.assertIsNone(main.texto_para_limite("descricao", "   "))


class TestLimitesNaGravacao(TesteComBancoTemporario):
    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()

    def total_contas(self):
        return self.consultar("SELECT COUNT(*) FROM contas")[0][0]

    # CT62 --------------------------------------------------------------
    def test_nome_usuario_70_aceito_71_recusado(self):
        sucesso, _ = db.criar_usuario("a" * 70, "setenta@sino.com", "senha123", aceite_termos=True)
        self.assertTrue(sucesso)
        sucesso, mensagem = db.criar_usuario("a" * 71, "setenta1@sino.com", "senha123", aceite_termos=True)
        self.assertFalse(sucesso)
        self.assertIn("70", mensagem)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM usuarios WHERE email = 'setenta1@sino.com'")[0][0], 0)

    # CT61 --------------------------------------------------------------
    def test_nome_categoria_30_aceito_31_recusado(self):
        self.assertIsNotNone(db.criar_categoria(self.usuario_id, "c" * 30))
        with self.assertRaises(limites.LimiteDeCaracteresError) as contexto:
            db.criar_categoria(self.usuario_id, "c" * 31)
        self.assertEqual((contexto.exception.campo, contexto.exception.limite), ("nome_categoria", 30))
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM categorias WHERE nome = ?", ("c" * 31,))[0][0], 0)

    def test_editar_categoria_nome_31_recusado_sem_alterar(self):
        categoria_id = self.criar_categoria(self.usuario_id, "Casa")
        with self.assertRaises(limites.LimiteDeCaracteresError):
            db.editar_categoria(self.usuario_id, categoria_id, nome="c" * 31)
        self.assertEqual(self.consultar("SELECT nome FROM categorias WHERE id = ?", (categoria_id,))[0][0], "Casa")

    def test_catalogo_pre_criado_respeita_limite(self):
        for nome, _ in db.CATEGORIAS_PRE_CRIADAS:
            self.assertLessEqual(limites.contar_caracteres(nome), limites.LIMITE_NOME_CATEGORIA)

    # CT60 / CT59 -------------------------------------------------------
    def test_nome_conta_30_aceito_31_recusado(self):
        db.criar_conta_unica(self.usuario_id, "n" * 30, 10.0, "2026-10-01")
        with self.assertRaises(limites.LimiteDeCaracteresError):
            db.criar_conta_unica(self.usuario_id, "n" * 31, 10.0, "2026-10-01")
        with self.assertRaises(limites.LimiteDeCaracteresError):
            db.criar_serie_recorrente(self.usuario_id, "n" * 31, 10.0, "2026-10-01", "mensal")
        self.assertEqual(self.total_contas(), 1)
        self.assertEqual(self.consultar("SELECT COUNT(*) FROM series_recorrencia")[0][0], 0)

    def test_descricao_500_aceita_501_recusada(self):
        conta_id = db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-01", descricao="d" * 500)
        self.assertEqual(len(self.consultar("SELECT descricao FROM contas WHERE id = ?", (conta_id,))[0][0]), 500)
        with self.assertRaises(limites.LimiteDeCaracteresError) as contexto:
            db.criar_conta_unica(self.usuario_id, "Luz", 10.0, "2026-10-01", descricao="d" * 501)
        self.assertEqual(contexto.exception.campo, "descricao")
        with self.assertRaises(limites.LimiteDeCaracteresError):
            db.criar_serie_recorrente(self.usuario_id, "Luz", 10.0, "2026-10-01", "mensal", descricao="d" * 501)
        self.assertEqual(self.total_contas(), 1)

    def test_descricao_contada_depois_da_normalizacao(self):
        conta_id = db.criar_conta_unica(
            self.usuario_id, "Luz", 10.0, "2026-10-01", descricao="  " + "d" * 500 + "\n\n",
        )
        self.assertEqual(self.consultar("SELECT descricao FROM contas WHERE id = ?", (conta_id,))[0][0], "d" * 500)

    def test_edicao_recusada_nao_grava_nada(self):
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Luz", 10.0, "2027-01-10", "mensal",
                                                data_termino="2027-04")
        id_fev = self.id_por_data(serie_id, "2027-02-10")
        antes = (self.ocorrencias(serie_id), self.serie(serie_id))
        with self.assertRaises(limites.LimiteDeCaracteresError):
            db.editar_conta_serie(id_fev, valor=99.0, nome="n" * 31)
        with self.assertRaises(limites.LimiteDeCaracteresError):
            db.editar_conta_ocorrencia(id_fev, valor=99.0, descricao="d" * 501)
        self.assertEqual((self.ocorrencias(serie_id), self.serie(serie_id)), antes)

    # CT108 -------------------------------------------------------------
    def test_nome_de_30_caracteres_com_emoji_composto(self):
        nome = "a" * 29 + EMOJI_COMPOSTO
        self.assertEqual(len(nome), 32)  # pontos de código
        conta_id = db.criar_conta_unica(self.usuario_id, nome, 10.0, "2026-10-01")
        self.assertEqual(self.conta(conta_id)["nome"], nome)
        db.criar_categoria(self.usuario_id, "b" * 29 + EMOJI_COMPOSTO)
        self.assertIsNone(main.erro_de_limite("nome_conta", nome, limites.LIMITE_NOME_CONTA))


class TestDadosLegadosAcimaDoLimite(TesteComBancoTemporario):
    """CT109 / P4: exibidos sem corte; só bloqueiam quando enviados."""

    def setUp(self):
        super().setUp()
        self.usuario_id = self.criar_usuario()
        self.nome_longo = "Nome antigo muito longo de conta legado"  # 39
        self.descricao_longa = "x" * 600

    def test_conta_avulsa_legada(self):
        conta_id = self.executar(
            """
            INSERT INTO contas (usuario_id, nome, valor, data_vencimento, status, descricao)
            VALUES (?, ?, 50.0, '2026-10-05', 'pendente', ?)
            """,
            (self.usuario_id, self.nome_longo, self.descricao_longa),
        )
        listada = next(c for c in db.listar_contas(self.usuario_id) if c["id"] == conta_id)
        self.assertEqual((listada["nome"], listada["descricao"]), (self.nome_longo, self.descricao_longa))

        # Campos antigos não enviados não são revalidados nem cortados.
        self.assertTrue(db.editar_conta_ocorrencia(conta_id, valor=60.0))
        self.assertTrue(db.editar_conta_serie(conta_id, valor=70.0, nome=self.nome_longo))
        conta = self.conta(conta_id)
        self.assertEqual((conta["nome"], conta["valor"]), (self.nome_longo, 70.0))

        # Enviar um texto ainda acima do limite é recusado.
        with self.assertRaises(limites.LimiteDeCaracteresError):
            db.editar_conta_ocorrencia(conta_id, nome=self.nome_longo + "!")
        with self.assertRaises(limites.LimiteDeCaracteresError):
            db.editar_conta_ocorrencia(conta_id, descricao=self.descricao_longa + "!")

        # Depois de ajustado, salva.
        self.assertTrue(db.editar_conta_ocorrencia(conta_id, nome="Nome curto", descricao="ok"))
        linha = self.consultar("SELECT nome, descricao FROM contas WHERE id = ?", (conta_id,))[0]
        self.assertEqual(linha, ("Nome curto", "ok"))

    def test_serie_legada_gera_sem_cortar(self):
        serie_id, _ = db.criar_serie_recorrente(self.usuario_id, "Curto", 10.0, "2026-10-10", "mensal")
        self.executar("UPDATE series_recorrencia SET nome = ?, descricao = ? WHERE id = ?",
                      (self.nome_longo, self.descricao_longa, serie_id))
        novos = db.gerar_ocorrencias_sob_demanda(serie_id, "2028-01")
        self.assertTrue(novos)
        linha = self.consultar("SELECT nome, descricao FROM contas WHERE id = ?", (novos[-1],))[0]
        self.assertEqual(linha, (self.nome_longo, self.descricao_longa))

    def test_categoria_legada(self):
        categoria_id = self.executar(
            "INSERT INTO categorias (usuario_id, nome, icone, cor) VALUES (?, ?, NULL, NULL)",
            (self.usuario_id, "c" * 40),
        )
        nomes = {c["id"]: c["nome"] for c in db.listar_categorias(self.usuario_id)}
        self.assertEqual(nomes[categoria_id], "c" * 40)
        # Trocar só o ícone (nome não enviado) funciona; reenviar o nome longo não.
        self.assertTrue(db.editar_categoria(self.usuario_id, categoria_id, icone="🏠"))
        with self.assertRaises(limites.LimiteDeCaracteresError):
            db.editar_categoria(self.usuario_id, categoria_id, nome="c" * 40)
        self.assertTrue(db.editar_categoria(self.usuario_id, categoria_id, nome="Casa"))

    def test_formulario_exige_todos_os_textos_dentro_do_limite(self):
        # Regra da interface (P4): a verificação de salvar_edicao cobre todos os
        # textos exibidos, não só o que mudou.
        self.assertIsNotNone(main.erro_de_limite("nome_conta", self.nome_longo, limites.LIMITE_NOME_CONTA))
        self.assertIsNotNone(main.erro_de_limite("descricao", self.descricao_longa, limites.LIMITE_DESCRICAO))


class TestEdicaoDentroDoLimite(unittest.TestCase):
    """Regra do bloqueio na digitação/colagem (5.23)."""

    def aceita(self, anterior, novo, limite=30):
        return main.edicao_dentro_do_limite(anterior, novo, limite)

    def test_limite_exato_e_tentativa_de_exceder(self):
        self.assertTrue(self.aceita("a" * 29, "a" * 30))
        self.assertFalse(self.aceita("a" * 30, "a" * 31))

    def test_colagem_que_excede_e_recusada_inteira(self):
        self.assertFalse(self.aceita("a" * 20, "a" * 20 + "b" * 11))
        self.assertTrue(self.aceita("a" * 20, "a" * 20 + "b" * 10))

    def test_substituicao_da_selecao(self):
        # 30 caracteres, 5 selecionados substituídos por 5 (aceito) ou 6 (recusado)
        base = "a" * 30
        self.assertTrue(self.aceita(base, "a" * 25 + "bbbbb"))
        self.assertFalse(self.aceita(base, "a" * 25 + "bbbbbb"))

    def test_emoji_composto_completado_no_limite(self):
        # 29 letras + 👩 = 30; os pontos de código seguintes (ZWJ + 💻)
        # completam o mesmo grafema, então a contagem continua 30.
        self.assertTrue(self.aceita("a" * 29, "a" * 29 + "👩"))
        self.assertTrue(self.aceita("a" * 29 + "👩", "a" * 29 + EMOJI_COMPOSTO))
        self.assertFalse(self.aceita("a" * 29 + EMOJI_COMPOSTO, "a" * 29 + EMOJI_COMPOSTO + "🇧🇷"))

    def test_espaco_apos_30_caracteres_e_recusado(self):
        # Conta o valor visível bruto: o espaço seria o 31º grafema.
        self.assertFalse(self.aceita("a" * 30, "a" * 30 + " "))
        self.assertFalse(self.aceita("a" * 30, " " + "a" * 30))
        self.assertTrue(self.aceita("a" * 29, "a" * 29 + " "))

    def test_espacos_e_quebras_na_descricao_no_limite(self):
        self.assertFalse(self.aceita("d" * 500, "d" * 500 + " ", limite=500))
        self.assertFalse(self.aceita("d" * 500, "d" * 500 + "\n", limite=500))
        self.assertTrue(self.aceita("d" * 498, "d" * 498 + "\n ", limite=500))
        self.assertTrue(self.aceita("linha 1", "linha 1\nlinha 2", limite=500))

    def test_dado_antigo_acima_do_limite(self):
        antigo = "n" * 34
        self.assertTrue(self.aceita(antigo, "n" * 33))           # apagar
        self.assertTrue(self.aceita(antigo, "n" * 29 + "xxxx"))  # substituir por menos
        self.assertFalse(self.aceita(antigo, "n" * 30 + "xxxx"))  # substituir sem reduzir
        self.assertFalse(self.aceita(antigo, "n" * 35))          # aumentar
        self.assertFalse(self.aceita("n" * 33, "n" * 33 + " "))  # espaço também conta

    def test_limites_dos_quatro_campos(self):
        for limite in (70, 30, 500):
            with self.subTest(limite=limite):
                self.assertTrue(self.aceita("x" * (limite - 1), "x" * limite, limite))
                self.assertFalse(self.aceita("x" * limite, "x" * (limite + 1), limite))


class TestCursorAposRecusa(unittest.TestCase):
    def test_digitacao_no_fim(self):
        self.assertEqual(main.cursor_apos_recusa("abc", "abcd"), 3)

    def test_colagem_no_meio(self):
        self.assertEqual(main.cursor_apos_recusa("abcdef", "abcXYZdef"), 3)

    def test_substituicao_de_selecao(self):
        self.assertEqual(main.cursor_apos_recusa("abcdef", "abQQQQf"), 2)

    def test_conta_em_unidades_utf16(self):
        # 🇧🇷 são 2 pontos de código e 4 unidades UTF-16.
        self.assertEqual(main.cursor_apos_recusa("🇧🇷ab", "🇧🇷abX"), 6)

    def test_nunca_para_no_meio_de_emoji_composto(self):
        # Prefixo comum termina dentro de 👩‍💻 (👩 igual, ZWJ igual, 💻 ≠ 🔧):
        # o cursor recua para antes do emoji inteiro.
        anterior = "a" + EMOJI_COMPOSTO
        novo = "a👩‍🔧"
        self.assertEqual(main.cursor_apos_recusa(anterior, novo), 1)


class EventoFalso:
    def __init__(self):
        self.atualizacoes = 0
        self.page = self

    def update(self):
        self.atualizacoes += 1


class AvisoFalso:
    def __init__(self):
        self.toques = 0

    def tocar(self):
        self.toques += 1
        return True


class TestLimiteDoCampo(unittest.TestCase):
    """O controle real do Flet, com um evento simulado (sem abrir o app).
    O aviso sonoro é substituído por um falso: a suíte nunca toca som."""

    def ligar(self, valor, campo="nome_conta", limite=30):
        import flet as ft
        self.chamadas = []
        self.aviso = AvisoFalso()
        self.campo = ft.TextField(value=valor)
        self.limite = main.ligar_contador_de_limite(self.campo, campo, limite,
                                                    ao_mudar=lambda e: self.chamadas.append(self.campo.value),
                                                    aviso=self.aviso)
        return self.campo

    def digitar(self, novo):
        self.campo.value = novo
        evento = EventoFalso()
        self.campo.on_change(evento)
        return evento

    def test_tentativa_de_exceder_mantem_ultimo_valor_valido(self):
        self.ligar("a" * 29)
        self.digitar("a" * 30)
        self.assertEqual((self.campo.counter, self.campo.helper, self.chamadas), ("30/30", None, ["a" * 30]))

        evento = self.digitar("a" * 30 + "XYZ")

        self.assertEqual(self.campo.value, "a" * 30)
        self.assertEqual(self.campo.counter, "30/30")
        self.assertEqual(self.campo.helper, "Limite atingido")
        self.assertEqual((self.campo.selection.base_offset, self.campo.selection.extent_offset), (30, 30))
        self.assertEqual(self.chamadas, ["a" * 30])  # ao_mudar não é chamado na recusa
        self.assertEqual(evento.atualizacoes, 1)
        self.assertEqual(self.aviso.toques, 1)  # som pedido na recusa

    def test_edicao_aceita_nao_pede_som(self):
        self.ligar("a" * 10)
        self.digitar("a" * 11)
        self.assertEqual(self.aviso.toques, 0)

    def test_espaco_apos_30_e_recusado_no_campo(self):
        self.ligar("a" * 30)
        self.digitar("a" * 30 + " ")
        self.assertEqual((self.campo.value, self.campo.counter, self.campo.helper),
                         ("a" * 30, "30/30", "Limite atingido"))

    def test_contador_mostra_o_valor_bruto(self):
        self.ligar("  ab  ")
        self.assertEqual(self.campo.counter, "6/30")

    def test_proxima_edicao_valida_limpa_o_aviso(self):
        self.ligar("a" * 30)
        self.digitar("a" * 31)
        self.digitar("a" * 29)
        self.assertEqual((self.campo.value, self.campo.helper, self.campo.counter), ("a" * 29, None, "29/30"))

    def test_colagem_em_emoji_nao_corta_o_grafema(self):
        self.ligar("a" * 29 + EMOJI_COMPOSTO)
        self.digitar("a" * 29 + EMOJI_COMPOSTO + "🇧🇷🇧🇷")
        self.assertEqual(self.campo.value, "a" * 29 + EMOJI_COMPOSTO)
        self.assertEqual(self.campo.counter, "30/30")

    def test_dado_antigo_abre_inteiro_e_pode_ser_reduzido(self):
        antigo = "Nome antigo muito longo de conta legado"  # 39
        self.ligar(antigo)
        self.assertEqual(self.campo.value, antigo)
        self.assertEqual(self.campo.counter, "39/30")
        self.assertIn("30", self.campo.error)

        self.digitar(antigo + "!")
        self.assertEqual(self.campo.value, antigo)  # não cresce

        self.assertEqual(self.aviso.toques, 1)

        self.digitar(antigo[:-5])
        self.assertEqual((self.campo.value, self.campo.counter), (antigo[:-5], "34/30"))
        self.digitar(antigo[:30])
        self.assertEqual((self.campo.counter, self.campo.error), ("30/30", None))

    def test_descricao_multilinha(self):
        self.ligar("linha 1", campo="descricao", limite=500)
        self.digitar("linha 1\nlinha 2")
        self.assertEqual(self.campo.value, "linha 1\nlinha 2")
        self.digitar("linha 1\nlinha 2\n" + "x" * 490)
        self.assertEqual(self.campo.value, "linha 1\nlinha 2")
        self.assertEqual(self.campo.helper, "Limite atingido")

    def test_sincronizar_adota_valor_definido_pelo_codigo(self):
        self.ligar("a" * 30)
        self.campo.value = ""
        self.limite.sincronizar()
        self.assertEqual((self.campo.counter, self.campo.helper), ("0/30", None))
        self.digitar("b")
        self.assertEqual(self.campo.value, "b")


class ProcessoFalso:
    def __init__(self, tocando):
        self.tocando = tocando

    def poll(self):
        return None if self.tocando else 0


class TestAvisoSonoro(unittest.TestCase):
    """aviso_sonoro sem tocar nada: processo, relógio e programas simulados."""

    def aviso(self, comandos=(["som"],), falha=None, tocando=False):
        import aviso_sonoro
        self.iniciados = []
        self.agora = [100.0]

        def iniciar(comando, **opcoes):
            if falha is not None:
                raise falha
            self.iniciados.append((comando, opcoes))
            return ProcessoFalso(tocando)

        return aviso_sonoro.AvisoSonoro(comandos=list(comandos), iniciar=iniciar, relogio=lambda: self.agora[0])

    def test_toca_sem_esperar_e_sem_saida(self):
        import subprocess
        aviso = self.aviso()
        self.assertTrue(aviso.tocar())
        comando, opcoes = self.iniciados[0]
        self.assertEqual(comando, ["som"])
        self.assertEqual(opcoes["stdout"], subprocess.DEVNULL)
        self.assertEqual(opcoes["stderr"], subprocess.DEVNULL)

    def test_tecla_mantida_pressionada_toca_uma_vez(self):
        aviso = self.aviso()
        for _ in range(20):  # repetição automática a cada 30 ms
            aviso.tocar()
            self.agora[0] += 0.03
        self.assertEqual(len(self.iniciados), 1)
        self.agora[0] += 2.0  # nova tentativa depois de uma pausa
        self.assertTrue(aviso.tocar())
        self.assertEqual(len(self.iniciados), 2)

    def test_nunca_dois_sons_ao_mesmo_tempo(self):
        aviso = self.aviso(tocando=True)
        aviso.tocar()
        self.agora[0] += 2.0
        self.assertFalse(aviso.tocar())
        self.assertEqual(len(self.iniciados), 1)

    def test_sem_utilitario_de_audio_e_silencioso(self):
        self.assertFalse(self.aviso(comandos=()).tocar())

    def test_programa_ausente_ou_falha_ao_iniciar_e_silencioso(self):
        self.assertFalse(self.aviso(falha=FileNotFoundError("canberra-gtk-play")).tocar())
        self.assertFalse(self.aviso(falha=PermissionError("negado")).tocar())

    def test_tenta_o_proximo_programa(self):
        import aviso_sonoro
        tentativas = []

        def iniciar(comando, **opcoes):
            tentativas.append(comando[0])
            if comando[0] == "canberra-gtk-play":
                raise FileNotFoundError(comando[0])
            return ProcessoFalso(False)

        aviso = aviso_sonoro.AvisoSonoro(comandos=[["canberra-gtk-play"], ["paplay", "x.oga"]], iniciar=iniciar)
        self.assertTrue(aviso.tocar())
        self.assertEqual(tentativas, ["canberra-gtk-play", "paplay"])

    def test_deteccao_dos_programas_do_sistema(self):
        import aviso_sonoro
        self.assertEqual(aviso_sonoro._comandos_padrao(localizar=lambda nome: None), [])
        comandos = aviso_sonoro._comandos_padrao(localizar=lambda nome: "/usr/bin/" + nome, existe=lambda c: True)
        self.assertEqual([c[0] for c in comandos], ["canberra-gtk-play", "paplay"])


if __name__ == "__main__":
    unittest.main()
