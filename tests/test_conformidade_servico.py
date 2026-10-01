"""
Conformidade do cliente com o servidor (Etapa 8): reproduz as transcrições
geradas pelo servidor (servidor/test/conformidade/transcricoes.json). O
cliente usa os mesmos valores aleatórios do servidor; cada requisição precisa
coincidir byte a byte (método, caminho, Idempotency-Key e corpo), e cada
resposta real precisa ser interpretada como o contrato prevê. Sem rede.
"""

import unittest

from apoio_servico import (
    URL_BASE,
    Aleatorio,
    Esperas,
    Relogio,
    cabecalho,
    capturar_stderr,
    carregar_conformidade,
)

import autorizacao_servico as aut
import servico_codigos as sc


class TransporteDaTranscricao:
    def __init__(self, teste, passos):
        self.teste = teste
        self.passos = list(passos)

    async def enviar(self, requisicao):
        self.teste.assertTrue(self.passos, "requisição além da transcrição")
        passo = self.passos.pop(0)
        esperada = passo["requisicao"]
        self.teste.assertEqual(requisicao.metodo, esperada["metodo"])
        self.teste.assertEqual(requisicao.url, URL_BASE + esperada["caminho"])
        self.teste.assertEqual(cabecalho(requisicao, "Idempotency-Key"), esperada["idempotency_key"])
        self.teste.assertEqual(cabecalho(requisicao, "Content-Type"), "application/json")
        self.teste.assertEqual(requisicao.corpo, esperada["corpo"].encode("utf-8"))
        if passo.get("falha_conexao"):
            raise sc.ErroDeConexao("ReadTimeout")
        r = passo["resposta"]
        cabecalhos = {"content-type": r["content_type"]}
        if r["retry_after"] is not None:
            cabecalhos["retry-after"] = r["retry_after"]
        return sc.RespostaHttp(r["status"], cabecalhos, r["corpo"].encode("utf-8"))


class TestTranscricoesDoServidor(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.dados = carregar_conformidade("transcricoes.json")

    def preparar(self, nome):
        cenario = self.dados["cenarios"][nome]
        a = cenario["aleatorios"]
        fila = [bytes.fromhex(a["nonce"]), bytes.fromhex(a["segredo"])] + [bytes.fromhex(c) for c in a["chaves"]]
        relogio = Relogio()
        self.esperas = Esperas(relogio)
        self.transporte = TransporteDaTranscricao(self, cenario["passos"])
        config = sc.ConfiguracaoServico(
            url_base=URL_BASE,
            chaves_publicas={self.dados["kid"]: aut.chave_publica_de_hex(self.dados["chave_publica_hex"])},
        )
        cliente = sc.ClienteServicoCodigos(
            config, self.transporte, relogio=relogio, esperar=self.esperas, aleatorio=Aleatorio(fila),
        )
        return cenario, cliente, cliente.nova_operacao(cenario["finalidade"], cenario["email"])

    def tearDown(self):
        self.assertEqual(self.transporte.passos, [], "a transcrição tinha passos não usados")

    async def test_cadastro_validado(self):
        cenario, cliente, op = self.preparar("cadastro_validado")
        self.assertEqual(await cliente.pedir_codigo(op), sc.CodigoSolicitado())
        resultado = await cliente.validar_codigo(op, cenario["codigo"])
        self.assertIsInstance(resultado, sc.AutorizacaoVerificada)
        self.assertEqual(resultado.finalidade, "cadastro")
        self.assertEqual(resultado.exp_utc_s, op.expira_em_utc_ms // 1000)

    async def test_recuperacao_sem_envio(self):
        cenario, cliente, op = self.preparar("recuperacao_sem_envio")
        self.assertEqual(await cliente.pedir_codigo(op, sem_envio=True), sc.CodigoSolicitado())
        self.assertEqual(await cliente.validar_codigo(op, cenario["codigo"]), sc.CodigoInvalido(4))

    async def test_recuperacao_com_envio(self):
        _, cliente, op = self.preparar("recuperacao_com_envio")
        self.assertEqual(await cliente.pedir_codigo(op, sem_envio=False), sc.CodigoSolicitado())

    async def test_reenvio_antes_de_60s(self):
        _, cliente, op = self.preparar("reenvio_antes_de_60s")
        self.assertEqual(await cliente.pedir_codigo(op), sc.CodigoSolicitado())
        self.assertEqual(await cliente.pedir_codigo(op), sc.Aguarde(segundos=60.0))

    async def test_em_processamento(self):
        _, cliente, op = self.preparar("em_processamento")
        with capturar_stderr():
            self.assertEqual(await cliente.pedir_codigo(op), sc.CodigoSolicitado())
        self.assertEqual(self.esperas.feitas, [sc.ESPERAS_DE_REDE_S[0], 2])

    async def test_falha_envio(self):
        _, cliente, op = self.preparar("falha_envio")
        self.assertEqual(await cliente.pedir_codigo(op), sc.FalhaEnvio(segundos_para_reenvio=60.0))

    async def test_teto_global(self):
        _, cliente, op = self.preparar("teto_global")
        self.assertEqual(await cliente.pedir_codigo(op, sem_envio=False), sc.ServicoIndisponivel())

    async def test_desafio_substituido(self):
        cenario, cliente, op = self.preparar("desafio_substituido")
        self.assertEqual(await cliente.pedir_codigo(op), sc.CodigoSolicitado())
        self.assertEqual(await cliente.validar_codigo(op, cenario["codigo"]), sc.DesafioEncerrado())

    def test_todos_os_cenarios_tem_teste(self):
        nomes = {n[len("test_"):] for n in dir(self) if n.startswith("test_") and n != "test_todos_os_cenarios_tem_teste"}
        self.assertEqual(set(self.dados["cenarios"]), nomes)
        self.transporte = TransporteDaTranscricao(self, [])


if __name__ == "__main__":
    unittest.main()
