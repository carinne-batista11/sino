"""
Testes do cliente do serviço de códigos (Etapa 8, bloco 2): configuração,
operação, pedidos, repetições, prazos, validação e robustez, com transporte
falso, relógio falso e sem sleep, rede ou banco.
"""

import asyncio
import gzip
import hashlib
import json
import os
import unittest
from unittest import mock

import httpx

from apoio_servico import (
    AGORA_SERVIDOR_MS,
    DESAFIO,
    KID,
    URL_BASE,
    VALIDADE_MS,
    Aleatorio,
    Atraso,
    assinar,
    cabecalho,
    capturar_stderr,
    conteudo_autorizacao,
    corpo_desafio,
    iso,
    novo_cliente,
    resposta,
)

import servico_codigos as sc

EMAIL = "  Pessoa@Exemplo.com "
T = AGORA_SERVIDOR_MS
EXP_S = (T + VALIDADE_MS) // 1000


def autorizacao_ok(operacao, agora=T + 30_000, exp_s=EXP_S, **trocas):
    token = assinar(conteudo_autorizacao(operacao, exp_s, **trocas))
    return resposta(200, {"autorizacao": token, "expira_em": iso(T + VALIDADE_MS), "agora": iso(agora)})


class TestConfiguracao(unittest.TestCase):
    CHAVE = "11" * 32

    def test_url_https_e_localhost(self):
        self.assertEqual(sc.validar_url_base("https://codigos.exemplo.com/"), "https://codigos.exemplo.com")
        self.assertEqual(sc.validar_url_base("http://127.0.0.1:8787"), "http://127.0.0.1:8787")
        self.assertEqual(sc.validar_url_base("http://localhost:8787"), "http://localhost:8787")

    def test_url_recusada(self):
        for url in ["http://codigos.exemplo.com", "ftp://x", "https://u:s@x.com", "https://x.com/caminho",
                    "https://x.com/?a=1", "https://x.com/#f", "", None]:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    sc.validar_url_base(url)

    def test_configuracao_do_ambiente(self):
        self.assertIsNone(sc.configuracao_do_ambiente({}))
        config = sc.configuracao_do_ambiente(
            {"SINO_SERVICO_URL": "http://127.0.0.1:8787", "SINO_SERVICO_CHAVES": f"dev-1:{'22' * 32}"},
        )
        self.assertEqual(config.url_base, "http://127.0.0.1:8787")
        self.assertEqual(list(config.chaves_publicas), ["dev-1"])
        # Sem chaves públicas, o serviço é considerado não configurado.
        self.assertIsNone(sc.configuracao_do_ambiente({"SINO_SERVICO_URL": "https://x.com"}))

    def test_configuracao_invalida_registra_so_o_tipo(self):
        with capturar_stderr() as saida:
            self.assertIsNone(sc.configuracao_do_ambiente(
                {"SINO_SERVICO_URL": "http://servidor.exemplo", "SINO_SERVICO_CHAVES": f"k:{self.CHAVE}"},
            ))
            self.assertIsNone(sc.configuracao_do_ambiente(
                {"SINO_SERVICO_URL": "https://x.com", "SINO_SERVICO_CHAVES": "k:zz,k:zz"},
            ))
        self.assertIn("(ValueError)", saida.getvalue())
        self.assertNotIn("servidor.exemplo", saida.getvalue())


class TestOperacao(unittest.TestCase):
    def test_contexto_e_email_normalizado(self):
        nonce = bytes(range(32))
        cliente, *_ = novo_cliente([], aleatorio=Aleatorio([nonce, b"s" * 32]))
        op = cliente.nova_operacao("cadastro", EMAIL)
        self.assertEqual(op.email, "Pessoa@Exemplo.com")
        self.assertEqual(op.email_normalizado, "pessoa@exemplo.com")
        esperado = hashlib.sha256(f"cadastro\x1fpessoa@exemplo.com\x1f{nonce.hex()}".encode()).hexdigest()
        self.assertEqual(op.contexto, esperado)

    def test_repr_sem_segredos_e_descartar(self):
        cliente, *_ = novo_cliente([])
        op = cliente.nova_operacao("cadastro", EMAIL)
        texto = repr(op)
        for proibido in [op._segredo, op.contexto, "Pessoa", "pessoa"]:
            self.assertNotIn(proibido, texto)
        op.descartar()
        self.assertIsNone(op._segredo)
        self.assertIsNone(op.contexto)

    def test_entrada_invalida(self):
        cliente, *_ = novo_cliente([])
        with self.assertRaises(ValueError):
            cliente.nova_operacao("login", EMAIL)
        with self.assertRaises(ValueError):
            cliente.nova_operacao("cadastro", "  ")


class TestPedido(unittest.IsolatedAsyncioTestCase):
    async def test_cadastro_201(self):
        cliente, transporte, relogio, _ = novo_cliente([resposta(201, corpo_desafio())])
        op = cliente.nova_operacao("cadastro", EMAIL)
        self.assertEqual(await cliente.pedir_codigo(op), sc.CodigoSolicitado())
        req = transporte.requisicoes[0]
        self.assertEqual((req.metodo, req.url), ("POST", f"{URL_BASE}/v1/desafios"))
        self.assertEqual(req.tempo_limite, sc.TEMPO_LIMITE_PEDIDO_COM_ENVIO_S)
        self.assertEqual(cabecalho(req, "Accept-Encoding"), "identity")
        self.assertRegex(cabecalho(req, "Idempotency-Key"), r"^[A-Za-z0-9_-]{24}$")
        corpo = json.loads(req.corpo)
        self.assertEqual(list(corpo), ["finalidade", "email", "contexto", "segredo"])
        self.assertEqual(corpo["email"], "Pessoa@Exemplo.com")
        self.assertNotIn(corpo["segredo"], req.url)
        self.assertEqual(op.desafio_id, DESAFIO)
        self.assertEqual(op.expira_em_utc_ms, T + VALIDADE_MS)

    async def test_recuperacao_tem_o_mesmo_formato_com_e_sem_envio(self):
        corpos = []
        for sem_envio in (False, True):
            cliente, transporte, *_ = novo_cliente([resposta(202, corpo_desafio())])
            op = cliente.nova_operacao("recuperacao_senha", EMAIL)
            self.assertEqual(await cliente.pedir_codigo(op, sem_envio=sem_envio), sc.CodigoSolicitado())
            self.assertEqual(transporte.requisicoes[0].tempo_limite, sc.TEMPO_LIMITE_PADRAO_S)
            corpos.append(json.loads(transporte.requisicoes[0].corpo))
        self.assertEqual(list(corpos[0]), list(corpos[1]))
        self.assertEqual([c["sem_envio"] for c in corpos], [False, True])

    async def test_sem_envio_so_na_recuperacao_e_201_na_recuperacao_e_invalido(self):
        cliente, *_ = novo_cliente([resposta(201, corpo_desafio())])
        with self.assertRaises(ValueError):
            await cliente.pedir_codigo(cliente.nova_operacao("cadastro", EMAIL), sem_envio=True)
        op = cliente.nova_operacao("recuperacao_senha", EMAIL)
        with capturar_stderr():
            self.assertEqual(await cliente.pedir_codigo(op), sc.RespostaInvalida())

    async def test_falha_de_rede_repete_com_a_mesma_chave_e_o_mesmo_corpo(self):
        erro = sc.ErroDeConexao("ConnectError")
        cliente, transporte, _, esperas = novo_cliente([erro, erro, resposta(201, corpo_desafio())])
        op = cliente.nova_operacao("cadastro", EMAIL)
        with capturar_stderr():
            self.assertEqual(await cliente.pedir_codigo(op), sc.CodigoSolicitado())
        self.assertEqual(len({cabecalho(r, "Idempotency-Key") for r in transporte.requisicoes}), 1)
        self.assertEqual(len({r.corpo for r in transporte.requisicoes}), 1)
        self.assertEqual(esperas.feitas, [0.5, 1.0])

    async def test_sem_conexao_depois_das_repeticoes(self):
        erro = sc.ErroDeConexao("ReadTimeout")
        cliente, transporte, *_ = novo_cliente([erro, erro, erro])
        with capturar_stderr():
            self.assertEqual(await cliente.pedir_codigo(cliente.nova_operacao("cadastro", EMAIL)), sc.SemConexao())
        self.assertEqual(len(transporte.requisicoes), 3)

    async def test_em_processamento_espera_retry_after_e_repete_a_mesma_requisicao(self):
        em_proc = resposta(202, corpo_desafio(estado="em_processamento"), {"Retry-After": "2"})
        cliente, transporte, _, esperas = novo_cliente([em_proc, resposta(201, corpo_desafio())])
        op = cliente.nova_operacao("cadastro", EMAIL)
        self.assertEqual(await cliente.pedir_codigo(op), sc.CodigoSolicitado())
        self.assertEqual(esperas.feitas, [2])
        self.assertEqual(len({(cabecalho(r, "Idempotency-Key"), r.corpo) for r in transporte.requisicoes}), 1)

    async def test_em_processamento_persistente_termina_sem_dormir(self):
        em_proc = resposta(202, corpo_desafio(estado="em_processamento"), {"Retry-After": "999"})
        cliente, transporte, relogio, esperas = novo_cliente([em_proc] * 40)
        inicio = relogio()
        resultado = await cliente.pedir_codigo(cliente.nova_operacao("cadastro", EMAIL))
        self.assertEqual(resultado, sc.EnvioNaoConfirmado())
        self.assertTrue(all(e == sc.RETRY_AFTER_MAXIMO_S for e in esperas.feitas))
        self.assertLessEqual(relogio() - inicio, sc.ESPERA_MAXIMA_EM_PROCESSAMENTO_S)

    async def test_retry_after_invalido_usa_o_padrao(self):
        em_proc = resposta(202, corpo_desafio(estado="em_processamento"), {"Retry-After": "Wed, 21 Oct"})
        cliente, _, _, esperas = novo_cliente([em_proc, resposta(201, corpo_desafio())])
        await cliente.pedir_codigo(cliente.nova_operacao("cadastro", EMAIL))
        self.assertEqual(esperas.feitas, [sc.RETRY_AFTER_PADRAO_S])

    async def test_em_processamento_na_recuperacao_esta_fora_do_contrato(self):
        em_proc = resposta(202, corpo_desafio(estado="em_processamento"))
        cliente, *_ = novo_cliente([em_proc])
        with capturar_stderr():
            resultado = await cliente.pedir_codigo(cliente.nova_operacao("recuperacao_senha", EMAIL))
        self.assertEqual(resultado, sc.RespostaInvalida())

    async def test_respostas_de_erro(self):
        casos = [
            (resposta(429, {"erro": "aguarde", "reenvio_permitido_em": iso(T + 45_000), "agora": iso(T)}),
             sc.Aguarde(segundos=45.0)),
            (resposta(429, {"erro": "limite_excedido"}), sc.LimiteExcedido()),
            (resposta(502, {"erro": "falha_envio", "reenvio_permitido_em": iso(T + 60_000), "agora": iso(T)}),
             sc.FalhaEnvio(segundos_para_reenvio=60.0)),
            (resposta(503, {"erro": "servico_indisponivel"}), sc.ServicoIndisponivel()),
            (resposta(500, b"<html>erro</html>", tipo="text/html"), sc.ServicoIndisponivel()),
            (resposta(410, {"erro": "desafio_encerrado"}), sc.DesafioEncerrado()),
        ]
        for item, esperado in casos:
            with self.subTest(status=item.status):
                cliente, *_ = novo_cliente([item])
                self.assertEqual(await cliente.pedir_codigo(cliente.nova_operacao("cadastro", EMAIL)), esperado)

    async def test_falha_de_envio_encerra_o_desafio_anterior(self):
        falha = resposta(502, {"erro": "falha_envio", "reenvio_permitido_em": iso(T + 60_000), "agora": iso(T)})
        cliente, *_ = novo_cliente([resposta(201, corpo_desafio()), falha])
        op = cliente.nova_operacao("cadastro", EMAIL)
        await cliente.pedir_codigo(op)
        await cliente.pedir_codigo(op)
        self.assertIsNone(op.desafio_id)

    async def test_respostas_fora_do_contrato(self):
        casos = {
            "redirecionamento": resposta(302, b"", {"Location": "https://outro.exemplo/"}, tipo=None),
            "conflito": resposta(409, {"erro": "conflito_idempotencia"}),
            "chave_duplicada": resposta(201, b'{"desafio_id":"QUFBQUFBQUFBQUFBQUFBQQ","desafio_id":"x",'
                                             b'"expira_em":"2026-10-01T12:10:00.000Z",'
                                             b'"reenvio_permitido_em":"2026-10-01T12:01:00.000Z",'
                                             b'"agora":"2026-10-01T12:00:00.000Z"}'),
            "chave_extra": resposta(201, corpo_desafio(email="x@y.z")),
            "content_type": resposta(201, corpo_desafio(), tipo="text/plain"),
            "desafio_malformado": resposta(201, corpo_desafio(desafio="curto")),
            "instante_malformado": resposta(201, {**corpo_desafio(), "agora": "2026-10-01T12:00:00Z"}),
            "ja_expirado": resposta(201, corpo_desafio(expira=T)),
            "nan": resposta(201, json.dumps(corpo_desafio()).replace('"agora"', '"x":NaN,"agora"').encode()),
        }
        for nome, item in casos.items():
            with self.subTest(caso=nome):
                cliente, transporte, *_ = novo_cliente([item])
                op = cliente.nova_operacao("cadastro", EMAIL)
                with capturar_stderr():
                    self.assertEqual(await cliente.pedir_codigo(op), sc.RespostaInvalida())
                self.assertEqual(len(transporte.requisicoes), 1)
                self.assertIsNone(op.desafio_id)

    async def test_resposta_grande_demais_ou_comprimida(self):
        for erro in (sc.RespostaGrandeDemaisError(), sc.CodificacaoNaoSuportadaError()):
            with self.subTest(erro=type(erro).__name__):
                cliente, *_ = novo_cliente([erro])
                with capturar_stderr():
                    resultado = await cliente.pedir_codigo(cliente.nova_operacao("cadastro", EMAIL))
                self.assertEqual(resultado, sc.RespostaInvalida())


class TestPrazos(unittest.IsolatedAsyncioTestCase):
    async def test_atraso_da_resposta_nao_amplia_a_validade(self):
        cliente, _, relogio, _ = novo_cliente([Atraso(5.0, resposta(201, corpo_desafio()))])
        op = cliente.nova_operacao("cadastro", EMAIL)
        inicio = relogio()
        await cliente.pedir_codigo(op)
        # Conta do início da requisição: 600 s - margem; 5 s já se passaram.
        self.assertAlmostEqual(op._prazo_monotonico, inicio + 600 - sc.MARGEM_SEGURANCA_S)
        self.assertAlmostEqual(op.segundos_para_expirar(relogio()), 600 - sc.MARGEM_SEGURANCA_S - 5)

    async def test_repeticao_perto_da_expiracao_nao_amplia(self):
        # 1ª resposta: em processamento, agora = T. 2ª (2 s depois no cliente)
        # chega com o servidor ainda em T: daria um prazo maior, que é ignorado.
        em_proc = resposta(202, corpo_desafio(estado="em_processamento"), {"Retry-After": "2"})
        cliente, _, relogio, _ = novo_cliente([em_proc, resposta(201, corpo_desafio())])
        op = cliente.nova_operacao("cadastro", EMAIL)
        inicio = relogio()
        await cliente.pedir_codigo(op)
        self.assertAlmostEqual(op._prazo_monotonico, inicio + 600 - sc.MARGEM_SEGURANCA_S)

    async def test_resposta_posterior_com_validade_maior_e_ignorada(self):
        em_proc = resposta(202, corpo_desafio(estado="em_processamento"), {"Retry-After": "1"})
        maior = resposta(201, corpo_desafio(expira=T + VALIDADE_MS + 300_000))
        cliente, _, relogio, _ = novo_cliente([em_proc, maior])
        op = cliente.nova_operacao("cadastro", EMAIL)
        inicio = relogio()
        with capturar_stderr() as saida:
            await cliente.pedir_codigo(op)
        self.assertEqual(op.expira_em_utc_ms, T + VALIDADE_MS)
        self.assertAlmostEqual(op._prazo_monotonico, inicio + 600 - sc.MARGEM_SEGURANCA_S)
        self.assertIn("validade divergente", saida.getvalue())

    async def test_exp_assinado_diferente_do_original_e_recusado(self):
        for exp in (EXP_S + 60, EXP_S - 1):
            with self.subTest(exp=exp):
                cliente, transporte, *_ = novo_cliente([resposta(201, corpo_desafio())])
                op = cliente.nova_operacao("cadastro", EMAIL)
                await cliente.pedir_codigo(op)
                transporte.roteiro.append(autorizacao_ok(op, exp_s=exp))
                with capturar_stderr():
                    self.assertEqual(await cliente.validar_codigo(op, "123456"), sc.RespostaInvalida())

    async def test_autorizacao_que_chega_atrasada_demais_e_recusada(self):
        cliente, transporte, relogio, _ = novo_cliente([resposta(201, corpo_desafio())])
        op = cliente.nova_operacao("cadastro", EMAIL)
        await cliente.pedir_codigo(op)
        relogio.avancar(590)
        # A resposta leva 9 s: chega depois do prazo conservador (600 - 2).
        transporte.roteiro.append(Atraso(9, autorizacao_ok(op, agora=T + 590_000)))
        self.assertEqual(await cliente.validar_codigo(op, "123456"), sc.DesafioEncerrado())
        self.assertIsNone(op.desafio_id)

    async def test_prazo_local_vencido_nao_envia(self):
        cliente, transporte, relogio, _ = novo_cliente([resposta(201, corpo_desafio())])
        op = cliente.nova_operacao("cadastro", EMAIL)
        await cliente.pedir_codigo(op)
        relogio.avancar(600 - sc.MARGEM_SEGURANCA_S)
        self.assertEqual(await cliente.validar_codigo(op, "123456"), sc.DesafioEncerrado())
        self.assertEqual(len(transporte.requisicoes), 1)

    async def test_prazo_da_autorizacao_nunca_passa_o_do_desafio(self):
        cliente, transporte, relogio, _ = novo_cliente([resposta(201, corpo_desafio())])
        op = cliente.nova_operacao("cadastro", EMAIL)
        await cliente.pedir_codigo(op)
        prazo_desafio = op._prazo_monotonico
        relogio.avancar(100)
        # Servidor "atrasado" (agora = T): o cálculo daria mais tempo; vale o do desafio.
        transporte.roteiro.append(autorizacao_ok(op, agora=T))
        aut = await cliente.validar_codigo(op, "123456")
        self.assertIsInstance(aut, sc.AutorizacaoVerificada)
        self.assertEqual(aut.prazo_monotonico, prazo_desafio)
        self.assertTrue(aut.vigente(relogio()))
        self.assertFalse(aut.vigente(prazo_desafio))


class TestValidacao(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cliente, self.transporte, self.relogio, self.esperas = novo_cliente([resposta(201, corpo_desafio())])
        self.op = self.cliente.nova_operacao("cadastro", EMAIL)
        await self.cliente.pedir_codigo(self.op)

    def chave(self, i):
        return cabecalho(self.transporte.requisicoes[i], "Idempotency-Key")

    async def test_sucesso(self):
        self.transporte.roteiro.append(autorizacao_ok(self.op))
        aut = await self.cliente.validar_codigo(self.op, "042137")
        self.assertEqual(aut.jti, "anRpLWRlLXRlc3RlLTAwMQ")
        self.assertEqual((aut.finalidade, aut.exp_utc_s), ("cadastro", EXP_S))
        # Para a camada de dados: iat assinado (limpeza) e e-mail vinculado à operação.
        self.assertEqual(aut.iat_utc_s, AGORA_SERVIDOR_MS // 1000)
        self.assertEqual(aut.email_normalizado, "pessoa@exemplo.com")
        req = self.transporte.requisicoes[1]
        self.assertEqual(req.url, f"{URL_BASE}/v1/desafios/{DESAFIO}/validacao")
        self.assertEqual(list(json.loads(req.corpo)), ["email", "segredo", "codigo"])
        self.assertNotEqual(self.chave(1), self.chave(0))

    async def test_mesmo_codigo_sem_resposta_reusa_a_chave_outro_codigo_nao(self):
        erro = sc.ErroDeConexao("ReadTimeout")
        self.transporte.roteiro.extend([erro, erro, erro])
        with capturar_stderr():
            self.assertEqual(await self.cliente.validar_codigo(self.op, "111111"), sc.SemConexao())
        self.transporte.roteiro.append(resposta(503, {"erro": "servico_indisponivel"}))
        self.assertEqual(await self.cliente.validar_codigo(self.op, "111111"), sc.ServicoIndisponivel())
        self.transporte.roteiro.append(resposta(422, {"erro": "codigo_invalido", "tentativas_restantes": 4}))
        self.assertEqual(await self.cliente.validar_codigo(self.op, "111111"), sc.CodigoInvalido(4))
        self.assertEqual({self.chave(i) for i in range(1, 6)}, {self.chave(1)})
        # Depois de uma resposta definitiva, o mesmo código é uma nova tentativa.
        self.transporte.roteiro.append(resposta(422, {"erro": "codigo_invalido", "tentativas_restantes": 3}))
        await self.cliente.validar_codigo(self.op, "111111")
        self.assertNotEqual(self.chave(6), self.chave(1))
        self.transporte.roteiro.append(resposta(422, {"erro": "codigo_invalido", "tentativas_restantes": 2}))
        await self.cliente.validar_codigo(self.op, "222222")
        self.assertNotEqual(self.chave(7), self.chave(6))

    async def test_autorizacao_de_outra_operacao_e_recusada(self):
        casos = {
            "contexto": {"ctx": "b" * 64},
            "finalidade": {"fin": "recuperacao_senha"},
            "kid": {"kid": "outro"},
        }
        for nome, troca in casos.items():
            with self.subTest(caso=nome):
                self.transporte.roteiro.append(autorizacao_ok(self.op, **troca))
                with capturar_stderr():
                    self.assertEqual(await self.cliente.validar_codigo(self.op, "123456"), sc.RespostaInvalida())

    async def test_corpo_200_fora_do_contrato(self):
        token = assinar(conteudo_autorizacao(self.op, EXP_S))
        self.transporte.roteiro.append(
            resposta(200, {"autorizacao": token, "expira_em": iso(T + VALIDADE_MS), "agora": iso(T), "x": 1}),
        )
        with capturar_stderr():
            self.assertEqual(await self.cliente.validar_codigo(self.op, "123456"), sc.RespostaInvalida())

    async def test_encerrado_e_nao_encontrado(self):
        for status, erro in ((410, "desafio_encerrado"), (404, "desafio_nao_encontrado")):
            with self.subTest(status=status):
                await self.asyncSetUp()
                self.transporte.roteiro.append(resposta(status, {"erro": erro}))
                self.assertEqual(await self.cliente.validar_codigo(self.op, "123456"), sc.DesafioEncerrado())
                self.assertIsNone(self.op.desafio_id)
                self.assertEqual(await self.cliente.validar_codigo(self.op, "123456"), sc.DesafioEncerrado())

    async def test_jti_nao_canonico_e_recusado(self):
        self.transporte.roteiro.append(autorizacao_ok(self.op, jti="anRpLWRlLXRlc3RlLTAwMB"))
        with capturar_stderr():
            self.assertEqual(await self.cliente.validar_codigo(self.op, "123456"), sc.RespostaInvalida())

    async def test_tentativas_restantes_estritas(self):
        for valor in (True, 4.0, 6, -1, "4"):
            with self.subTest(valor=valor):
                self.transporte.roteiro.append(resposta(422, {"erro": "codigo_invalido", "tentativas_restantes": valor}))
                with capturar_stderr():
                    self.assertEqual(await self.cliente.validar_codigo(self.op, "123456"), sc.RespostaInvalida())

    async def test_codigo_mal_formado(self):
        for codigo in ("12345", "1234567", "12a456", 123456, "١٢٣٤٥٦"):
            with self.subTest(codigo=codigo):
                with self.assertRaises(ValueError):
                    await self.cliente.validar_codigo(self.op, codigo)


class TestDestinatarioNaoPermitido(unittest.IsolatedAsyncioTestCase):
    """Contrato v1.1: 403 destinatario_nao_permitido só no cadastro e na alteração."""

    RECUSA = {"erro": "destinatario_nao_permitido"}

    async def test_pedido_recusado_no_cadastro_e_na_alteracao(self):
        for finalidade in ("cadastro", "alteracao_email"):
            with self.subTest(finalidade=finalidade):
                cliente, transporte, *_ = novo_cliente([resposta(403, self.RECUSA)])
                op = cliente.nova_operacao(finalidade, EMAIL)
                self.assertEqual(await cliente.pedir_codigo(op), sc.DestinatarioNaoPermitido())
                # Resposta definitiva: nenhuma repetição e nenhum desafio registrado.
                self.assertEqual(len(transporte.requisicoes), 1)
                self.assertIsNone(op.desafio_id)

    async def test_reenvio_recusado_nao_registra_novo_desafio(self):
        cliente, transporte, *_ = novo_cliente([resposta(201, corpo_desafio()), resposta(403, self.RECUSA)])
        op = cliente.nova_operacao("cadastro", EMAIL)
        await cliente.pedir_codigo(op)
        self.assertEqual(await cliente.pedir_codigo(op), sc.DestinatarioNaoPermitido())
        self.assertEqual(len(transporte.requisicoes), 2)

    async def test_403_na_recuperacao_esta_fora_do_contrato(self):
        cliente, *_ = novo_cliente([resposta(403, self.RECUSA)])
        with capturar_stderr():
            resultado = await cliente.pedir_codigo(cliente.nova_operacao("recuperacao_senha", EMAIL), sem_envio=False)
        self.assertEqual(resultado, sc.RespostaInvalida())

    async def test_403_com_outro_corpo_esta_fora_do_contrato(self):
        casos = {
            "outro_erro": resposta(403, {"erro": "proibido"}),
            "chave_extra": resposta(403, {**self.RECUSA, "email": "x@y.z"}),
            "sem_json": resposta(403, b"<html>403</html>", tipo="text/html"),
        }
        for nome, item in casos.items():
            with self.subTest(caso=nome):
                cliente, *_ = novo_cliente([item])
                with capturar_stderr():
                    self.assertEqual(
                        await cliente.pedir_codigo(cliente.nova_operacao("cadastro", EMAIL)), sc.RespostaInvalida(),
                    )

    async def test_validacao_recusada_encerra_o_desafio(self):
        for finalidade in ("cadastro", "alteracao_email"):
            with self.subTest(finalidade=finalidade):
                cliente, *_ = novo_cliente([resposta(201, corpo_desafio()), resposta(403, self.RECUSA)])
                op = cliente.nova_operacao(finalidade, EMAIL)
                await cliente.pedir_codigo(op)
                self.assertEqual(await cliente.validar_codigo(op, "123456"), sc.DestinatarioNaoPermitido())
                self.assertIsNone(op.desafio_id)

    async def test_validacao_403_na_recuperacao_esta_fora_do_contrato(self):
        cliente, *_ = novo_cliente([resposta(202, corpo_desafio()), resposta(403, self.RECUSA)])
        op = cliente.nova_operacao("recuperacao_senha", EMAIL)
        await cliente.pedir_codigo(op, sem_envio=False)
        with capturar_stderr():
            self.assertEqual(await cliente.validar_codigo(op, "123456"), sc.RespostaInvalida())


class TestCancelamento(unittest.IsolatedAsyncioTestCase):
    async def test_descartar_durante_a_espera_do_em_processamento(self):
        em_proc = resposta(202, corpo_desafio(estado="em_processamento"), {"Retry-After": "2"})
        cliente, transporte, _, esperas = novo_cliente([em_proc, resposta(201, corpo_desafio())])
        op = cliente.nova_operacao("cadastro", EMAIL)
        espera_original = cliente._esperar

        async def esperar_e_descartar(segundos):
            await espera_original(segundos)
            op.descartar()

        cliente._esperar = esperar_e_descartar
        self.assertEqual(await cliente.pedir_codigo(op), sc.OperacaoCancelada())
        self.assertEqual(len(transporte.requisicoes), 1)
        self.assertIsNone(op.desafio_id)

    async def test_descartar_entre_repeticoes_de_rede(self):
        def falhar_e_descartar(requisicao):
            op.descartar()
            return sc.ErroDeConexao("ConnectError")

        cliente, transporte, _, esperas = novo_cliente([falhar_e_descartar, resposta(201, corpo_desafio())])
        op = cliente.nova_operacao("cadastro", EMAIL)
        with capturar_stderr():
            self.assertEqual(await cliente.pedir_codigo(op), sc.OperacaoCancelada())
        self.assertEqual(len(transporte.requisicoes), 1)
        self.assertEqual(esperas.feitas, [])

    async def test_resposta_que_chega_depois_do_descarte_nao_e_registrada(self):
        def responder_depois_de_descartar(requisicao):
            op.descartar()
            return resposta(201, corpo_desafio())

        cliente, *_ = novo_cliente([responder_depois_de_descartar])
        op = cliente.nova_operacao("cadastro", EMAIL)
        self.assertEqual(await cliente.pedir_codigo(op), sc.OperacaoCancelada())
        self.assertIsNone(op.desafio_id)
        self.assertIsNone(op.expira_em_utc_ms)

    async def test_validacao_depois_do_descarte(self):
        cliente, transporte, *_ = novo_cliente([resposta(201, corpo_desafio())])
        op = cliente.nova_operacao("cadastro", EMAIL)
        await cliente.pedir_codigo(op)

        def autorizar_depois_de_descartar(requisicao):
            resposta_ok = autorizacao_ok(op)
            op.descartar()
            return resposta_ok

        transporte.roteiro.append(autorizar_depois_de_descartar)
        self.assertEqual(await cliente.validar_codigo(op, "123456"), sc.OperacaoCancelada())
        # Operação cancelada: nada mais é enviado.
        self.assertEqual(await cliente.validar_codigo(op, "123456"), sc.OperacaoCancelada())
        self.assertEqual(await cliente.pedir_codigo(op), sc.OperacaoCancelada())
        self.assertEqual(len(transporte.requisicoes), 2)

    async def test_cancelar_a_tarefa_interrompe_a_chamada_sem_repetir(self):
        iniciou = asyncio.Event()
        estado = {"cancelada": False, "chamadas": 0}

        class TransportePendurado:
            async def enviar(self, requisicao):
                estado["chamadas"] += 1
                iniciou.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    estado["cancelada"] = True
                    raise

        cliente = sc.ClienteServicoCodigos(
            novo_cliente([])[0]._configuracao, TransportePendurado(), relogio=lambda: 0.0,
            esperar=lambda s: self.fail("não deveria esperar"),
        )
        op = cliente.nova_operacao("cadastro", EMAIL)
        tarefa = asyncio.create_task(cliente.pedir_codigo(op))
        await iniciou.wait()
        tarefa.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await tarefa
        self.assertEqual(estado, {"cancelada": True, "chamadas": 1})
        self.assertIsNone(op.desafio_id)


class TestRegistrosSemDadosSensiveis(unittest.IsolatedAsyncioTestCase):
    async def test_nada_sensivel_no_stderr(self):
        erro = sc.ErroDeConexao("ConnectError")
        cliente, transporte, *_ = novo_cliente([erro, resposta(201, corpo_desafio())])
        op = cliente.nova_operacao("cadastro", EMAIL)
        with capturar_stderr() as saida:
            await cliente.pedir_codigo(op)
            transporte.roteiro.extend([erro, erro, erro])
            await cliente.validar_codigo(op, "424242")
            transporte.roteiro.append(autorizacao_ok(op, ctx="c" * 64))
            await cliente.validar_codigo(op, "424242")
        texto = saida.getvalue()
        self.assertTrue(texto)
        chaves = {cabecalho(r, "Idempotency-Key") for r in transporte.requisicoes}
        for proibido in [op._segredo, op.contexto, "Pessoa", "pessoa", "424242", *chaves]:
            self.assertNotIn(proibido, texto)


class TestTransporteHttpx(unittest.IsolatedAsyncioTestCase):
    def requisicao(self, url=f"{URL_BASE}/v1/desafios"):
        return sc.RequisicaoHttp(
            metodo="POST", url=url, cabecalhos=(("Content-Type", "application/json"), ("Idempotency-Key", "k" * 24)),
            corpo=b'{"a":1}', tempo_limite=5.0,
        )

    async def test_envia_e_devolve_cabecalhos_em_minusculas(self):
        vistas = []

        def tratar(req):
            vistas.append(req)
            return httpx.Response(201, headers={"Content-Type": "application/json"}, content=b'{"ok":1}')

        transporte = sc.TransporteHttpx(httpx.MockTransport(tratar))
        r = await transporte.enviar(self.requisicao())
        await transporte.fechar()
        self.assertEqual((r.status, r.cabecalhos["content-type"], r.corpo), (201, "application/json", b'{"ok":1}'))
        self.assertEqual(vistas[0].headers["idempotency-key"], "k" * 24)
        self.assertEqual(vistas[0].content, b'{"a":1}')

    async def test_nao_segue_redirecionamento(self):
        vistas = []

        def tratar(req):
            vistas.append(str(req.url))
            return httpx.Response(307, headers={"Location": "https://outro.exemplo/roubar"})

        transporte = sc.TransporteHttpx(httpx.MockTransport(tratar))
        r = await transporte.enviar(self.requisicao())
        await transporte.fechar()
        self.assertEqual(r.status, 307)
        self.assertEqual(vistas, [f"{URL_BASE}/v1/desafios"])

    async def test_ignora_proxy_e_netrc_do_ambiente(self):
        with mock.patch.dict(os.environ, {"HTTPS_PROXY": "http://proxy.exemplo:3128", "NETRC": "/tmp/nao-existe"}):
            transporte = sc.TransporteHttpx(httpx.MockTransport(lambda req: httpx.Response(204)))
            self.assertFalse(transporte.cliente_httpx.trust_env)
            r = await transporte.enviar(self.requisicao())
            await transporte.fechar()
        self.assertEqual(r.status, 204)

    async def test_limite_da_resposta_com_e_sem_content_length(self):
        grande = b"x" * (sc.TAMANHO_MAXIMO_RESPOSTA + 1)

        async def em_partes():
            for i in range(0, len(grande), 1000):
                yield grande[i:i + 1000]

        casos = {
            "com_content_length": lambda req: httpx.Response(200, content=grande),
            "sem_content_length": lambda req: httpx.Response(200, content=em_partes()),
            "content_length_mentiroso": lambda req: httpx.Response(200, headers={"Content-Length": "10"},
                                                                    content=em_partes()),
        }
        for nome, tratar in casos.items():
            with self.subTest(caso=nome):
                transporte = sc.TransporteHttpx(httpx.MockTransport(tratar))
                with self.assertRaises(sc.RespostaGrandeDemaisError):
                    await transporte.enviar(self.requisicao())
                await transporte.fechar()

    async def test_erros_de_rede_viram_erro_de_conexao(self):
        for erro in (httpx.ConnectError("x"), httpx.ReadTimeout("x"), httpx.RemoteProtocolError("x")):
            with self.subTest(erro=type(erro).__name__):
                def tratar(req, erro=erro):
                    raise erro

                transporte = sc.TransporteHttpx(httpx.MockTransport(tratar))
                with self.assertRaises(sc.ErroDeConexao):
                    await transporte.enviar(self.requisicao())
                await transporte.fechar()

    async def test_forca_accept_encoding_identity(self):
        vistos = []

        def tratar(req):
            vistos.append(req.headers.get_list("accept-encoding"))
            return httpx.Response(204)

        transporte = sc.TransporteHttpx(httpx.MockTransport(tratar))
        await transporte.enviar(self.requisicao())
        pedido_gzip = sc.RequisicaoHttp("POST", f"{URL_BASE}/x", (("Accept-Encoding", "gzip"),), b"", 5.0)
        await transporte.enviar(pedido_gzip)
        await transporte.fechar()
        self.assertEqual(vistos, [["identity"], ["identity"]])

    async def test_recusa_resposta_comprimida_antes_de_ler(self):
        comprimido = gzip.compress(json.dumps({"a": "x" * 50_000}).encode())
        lidos = []

        async def em_fluxo():
            lidos.append(True)
            yield comprimido

        casos = {
            "fluxo": lambda req: httpx.Response(200, headers={"Content-Encoding": "gzip"}, content=em_fluxo()),
            "ja_carregada": lambda req: httpx.Response(200, headers={"Content-Encoding": "gzip"}, content=comprimido),
            "deflate": lambda req: httpx.Response(200, headers={"Content-Encoding": "deflate"}, content=b"x"),
        }
        for nome, tratar in casos.items():
            with self.subTest(caso=nome):
                transporte = sc.TransporteHttpx(httpx.MockTransport(tratar))
                with self.assertRaises(sc.CodificacaoNaoSuportadaError):
                    await transporte.enviar(self.requisicao())
                await transporte.fechar()
        self.assertEqual(lidos, [])

    async def test_identity_explicito_e_aceito(self):
        transporte = sc.TransporteHttpx(httpx.MockTransport(
            lambda req: httpx.Response(200, headers={"Content-Encoding": "Identity"}, content=b"{}"),
        ))
        r = await transporte.enviar(self.requisicao())
        await transporte.fechar()
        self.assertEqual(r.corpo, b"{}")

    async def test_tempo_limite_total_cancela_e_libera_a_chamada(self):
        # tempo_limite = 0: o prazo vence na próxima volta do loop, sem espera real.
        estado = {"iniciou": False, "cancelada": False}

        async def pendurar(req):
            estado["iniciou"] = True
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                estado["cancelada"] = True
                raise

        transporte = sc.TransporteHttpx(httpx.MockTransport(pendurar))
        requisicao = sc.RequisicaoHttp("POST", f"{URL_BASE}/v1/desafios", (), b"{}", 0)
        with self.assertRaises(sc.ErroDeConexao):
            await transporte.enviar(requisicao)
        self.assertEqual(estado, {"iniciou": True, "cancelada": True})
        # O cliente continua utilizável depois do cancelamento.
        transporte_ok = sc.TransporteHttpx(httpx.MockTransport(lambda req: httpx.Response(204)))
        self.assertEqual((await transporte_ok.enviar(self.requisicao())).status, 204)
        await transporte_ok.fechar()
        await transporte.fechar()

    async def test_cancelar_a_tarefa_fecha_a_chamada_httpx(self):
        iniciou = asyncio.Event()
        estado = {"cancelada": False}

        async def pendurar(req):
            iniciou.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                estado["cancelada"] = True
                raise

        transporte = sc.TransporteHttpx(httpx.MockTransport(pendurar))
        tarefa = asyncio.create_task(transporte.enviar(self.requisicao()))
        await iniciou.wait()
        tarefa.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await tarefa
        self.assertTrue(estado["cancelada"])
        await transporte.fechar()

    async def test_descarta_cookies(self):
        transporte = sc.TransporteHttpx(httpx.MockTransport(
            lambda req: httpx.Response(200, headers={"Set-Cookie": "sessao=abc; Path=/"}, content=b"{}"),
        ))
        await transporte.enviar(self.requisicao())
        self.assertEqual(len(transporte.cliente_httpx.cookies), 0)
        await transporte.fechar()


if __name__ == "__main__":
    unittest.main()
