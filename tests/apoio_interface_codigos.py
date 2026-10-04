"""
apoio_interface_codigos.py -- Apoio aos testes das telas com código (Etapa 8).

  * PaginaAssincrona: a PaginaFalsa dos testes de sessão com `run_task`
    funcionando. Dentro de um loop (testes assíncronos) cria tarefas reais;
    fora dele (testes síncronos) guarda as ações e `executar_pendentes()` as
    roda com asyncio.run, em ordem.
  * ServidorFalso: transporte do cliente REAL do serviço de códigos que
    responde como o contrato v1 (desafios, intervalo de 60 s, tentativas,
    sem_envio, repetição pela chave, autorização assinada com a chave de
    teste), com relógio injetável, falhas programáveis e um portão para
    segurar pedidos em andamento. Sem rede.
  * ComServicoFalso: mistura para os testes de tela: troca
    `main.criar_servico_codigos` pelo cliente real com o ServidorFalso, sem
    tique automático do contador de reenvio (nenhuma espera real).
"""

import asyncio
import base64
import hashlib
import json
from unittest import mock

from apoio_servico import (
    AGORA_SERVIDOR_MS,
    KID,
    Esperas,
    Relogio,
    assinar,
    configuracao,
    iso,
    resposta,
)
from test_sessao_tema import PaginaFalsa, main, percorrer

import servico_codigos as sc

VALIDADE_MS = 600_000
INTERVALO_MS = 60_000


class PaginaAssincrona(PaginaFalsa):
    def configurar(self):
        super().configurar()
        self.tarefas = []
        self.pendentes = []
        self.run_task.side_effect = self._agendar
        return self

    def _agendar(self, funcao, *args):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self.pendentes.append((funcao, args))
            return None
        tarefa = loop.create_task(funcao(*args))
        self.tarefas.append(tarefa)
        return tarefa

    def executar_pendentes(self):
        """Testes síncronos: roda as ações agendadas (e as que elas agendarem)."""
        while self.pendentes:
            funcao, args = self.pendentes.pop(0)
            asyncio.run(funcao(*args))

    async def concluir_tarefas(self):
        """Testes assíncronos: espera todas as tarefas criadas (inclusive as novas)."""
        while True:
            pendentes = [t for t in self.tarefas if not t.done()]
            if not pendentes:
                return
            await asyncio.gather(*pendentes, return_exceptions=True)


class ServidorFalso:
    def __init__(self, relogio):
        self.relogio = relogio
        self.desafios = {}
        self.por_chave = {}
        self.ultimo_pedido = {}
        self.enviados = []          # (e-mail, código) dos pedidos com envio
        self.pedidos = []           # corpos dos pedidos recebidos
        self.validacoes = []
        self.falhas = []            # próximas respostas/erros forçados (pedido ou validação)
        self.portao = None          # asyncio.Event: segura o próximo pedido até ser liberado
        self.contador = 0

    # ---------------------------------------------------------------- apoio
    def agora(self):
        return AGORA_SERVIDOR_MS + int((self.relogio() - 1000.0) * 1000)

    def _id(self, rotulo):
        self.contador += 1
        return base64.urlsafe_b64encode(hashlib.sha256(f"{rotulo}{self.contador}".encode()).digest()[:16]) \
            .rstrip(b"=").decode()

    def ultimo_codigo(self, email):
        for destino, codigo in reversed(self.enviados):
            if destino.lower() == email.lower():
                return codigo
        return None

    # ------------------------------------------------------------ transporte
    async def enviar(self, requisicao):
        if self.portao is not None:
            portao, self.portao = self.portao, None
            await portao.wait()
        if self.falhas:
            falha = self.falhas.pop(0)
            if isinstance(falha, BaseException):
                raise falha
            return falha
        corpo = json.loads(requisicao.corpo)
        chave = dict(requisicao.cabecalhos)["Idempotency-Key"]
        caminho = requisicao.url.split("://", 1)[1].split("/", 1)[1]
        if caminho == "v1/desafios":
            return self._pedido(corpo, chave)
        return self._validacao(caminho.split("/")[2], corpo, chave)

    def _pedido(self, corpo, chave):
        if chave in self.por_chave:
            return self.por_chave[chave]
        self.pedidos.append(corpo)
        agora = self.agora()
        email = corpo["email"].lower()
        ultimo = self.ultimo_pedido.get(email)
        if ultimo is not None and agora < ultimo + INTERVALO_MS:
            return resposta(429, {"erro": "aguarde", "reenvio_permitido_em": iso(ultimo + INTERVALO_MS),
                                  "agora": iso(agora)})
        for desafio in self.desafios.values():  # o novo código invalida o anterior da finalidade
            if desafio["email"] == email and desafio["finalidade"] == corpo["finalidade"]:
                desafio["encerrado"] = True
        desafio_id = self._id("desafio")
        codigo = f"{(self.contador * 7919) % 1_000_000:06d}"
        sem_envio = corpo.get("sem_envio", False)
        self.desafios[desafio_id] = {
            "email": email, "finalidade": corpo["finalidade"], "contexto": corpo["contexto"],
            "segredo": corpo["segredo"], "codigo": codigo, "expira": agora + VALIDADE_MS, "tentativas": 0,
            "encerrado": False, "sem_envio": sem_envio, "autorizacao": None, "validacoes": {},
        }
        if not sem_envio:
            self.enviados.append((corpo["email"], codigo))
        self.ultimo_pedido[email] = agora
        status = 202 if corpo["finalidade"] == "recuperacao_senha" else 201
        r = resposta(status, {"desafio_id": desafio_id, "expira_em": iso(agora + VALIDADE_MS),
                              "reenvio_permitido_em": iso(agora + INTERVALO_MS), "agora": iso(agora)})
        self.por_chave[chave] = r
        return r

    def _validacao(self, desafio_id, corpo, chave):
        self.validacoes.append(corpo["codigo"])
        desafio = self.desafios.get(desafio_id)
        if desafio is None or desafio["segredo"] != corpo["segredo"]:
            return resposta(404, {"erro": "desafio_nao_encontrado"})
        if chave in desafio["validacoes"]:
            return desafio["validacoes"][chave]
        agora = self.agora()
        if desafio["encerrado"] or agora >= desafio["expira"] or desafio["autorizacao"] or desafio["tentativas"] >= 5:
            return resposta(410, {"erro": "desafio_encerrado"})
        if desafio["sem_envio"] or corpo["codigo"] != desafio["codigo"]:
            desafio["tentativas"] += 1
            r = resposta(422, {"erro": "codigo_invalido", "tentativas_restantes": 5 - desafio["tentativas"]})
        else:
            conteudo = {"v": 1, "kid": KID, "jti": self._id("jti"), "fin": desafio["finalidade"],
                        "ctx": desafio["contexto"], "iat": agora // 1000, "exp": desafio["expira"] // 1000}
            desafio["autorizacao"] = assinar(conteudo)
            r = resposta(200, {"autorizacao": desafio["autorizacao"], "expira_em": iso(desafio["expira"]),
                               "agora": iso(agora)})
        desafio["validacoes"][chave] = r
        return r


class ComServicoFalso:
    """Mistura para TesteDeSessao: serviço de códigos com o ServidorFalso."""

    servico_configurado = True

    def setUp(self):
        super().setUp()
        self.relogio = Relogio()
        self.servidor = ServidorFalso(self.relogio)
        cliente = sc.ClienteServicoCodigos(configuracao(), self.servidor, relogio=self.relogio,
                                           esperar=Esperas(self.relogio))
        # esperar=None: sem tique automático do contador de reenvio (Bloco 3);
        # o valor é mostrado na hora e o clique confere o restante ao vivo.
        self.servico = main.ServicoCodigos(cliente, None, self.relogio, esperar=None)
        fabrica = mock.patch.object(main, "criar_servico_codigos",
                                    side_effect=lambda: self.servico if self.servico_configurado else None)
        fabrica.start()
        self.addCleanup(fabrica.stop)

    def abrir_app(self):
        pagina = PaginaAssincrona().configurar()
        main.main(pagina)
        return pagina, self.sessoes[-1]

    # ------------------------------------------------------------- consultas
    @staticmethod
    def todos(pagina):
        raizes = list(pagina.controls) + [d for d in pagina.dialogos if d.open]
        return [c for raiz in raizes for c in percorrer(raiz)]

    @staticmethod
    def visiveis(controle):
        """Como `percorrer`, mas sem descer em controles ocultos."""
        import flet as ft
        if getattr(controle, "visible", True) is False:
            return
        yield controle
        for atributo in ("controls", "content", "actions"):
            filho = getattr(controle, atributo, None)
            if isinstance(filho, list):
                for item in filho:
                    yield from ComServicoFalso.visiveis(item)
            elif isinstance(filho, ft.Control):
                yield from ComServicoFalso.visiveis(filho)

    def textos_visiveis(self, pagina):
        import flet as ft
        raizes = list(pagina.controls) + [d for d in pagina.dialogos if d.open]
        return [t.value for raiz in raizes for t in self.visiveis(raiz) if isinstance(t, ft.Text) and t.value]

    def campo(self, pagina, rotulo):
        import flet as ft
        return next(c for c in self.todos(pagina) if isinstance(c, ft.TextField) and c.label == rotulo)

    def botao(self, pagina, rotulo):
        import flet as ft
        return next(b for b in self.todos(pagina)
                    if isinstance(b, (ft.Button, ft.TextButton, ft.OutlinedButton)) and b.content == rotulo)

    @staticmethod
    def acionar(pagina, controle):
        from test_tela_principal import Evento
        controle.on_click(Evento(pagina, controle))

    def autorizacoes_usadas(self):
        return self.consultar("SELECT COUNT(*) FROM autorizacoes_usadas")[0][0]
