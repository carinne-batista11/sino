"""
fluxos_codigo.py -- Apoio das telas com código de e-mail (ERS v6.0, Etapa 8):
cadastro, alteração de e-mail e recuperação de senha. Sem Flet.

  * mensagens em português para cada resultado do cliente do serviço de
    códigos (identificados pelo nome da classe, para este módulo não depender
    do `cryptography`) e para os erros da camada de dados;
  * ControleOperacao: tarefas de uma tela/diálogo, cliques repetidos,
    cancelamento e execução fora do loop da interface. Leituras e cálculos
    de hash rodam em thread e podem ser abandonados; a gravação local roda
    em thread protegida (shield) e, enquanto o loop estiver rodando, o
    resultado real é obtido mesmo que a tarefa da tela seja cancelada no meio
    -- uma operação gravada nunca é apresentada como cancelada nem como
    falha. Erros inesperados registram só o tipo e liberam a tela;
  * nova tentativa (Etapa 10, B1): depois de uma falha transitória da
    gravação, a tela guarda a MESMA gravação (função e argumentos, com a
    autorização já verificada) em `ControleOperacao.gravacao_pendente` e a
    repete sem validar o código de novo. `encerrar()` descarta essa gravação;
  * Fechamento (Etapa 10, Bloco 2): rotina ÚNICA de fechamento da janela e
    de fim da sessão. Bloqueia novas ações e gravações, mostra um aviso se
    há gravação em curso, espera as gravações terminarem (sem tempo limite)
    e só então fecha a janela;
  * ContadorReenvio (Etapa 10, Bloco 3): "Reenviar código em N s" a partir
    de `segundos_para_reenvio` da operação; para quando a tela sai, a
    operação muda ou o fechamento começa, sem tocar em controles antigos.
    A recusa do serviço ("Aguarde") continua valendo mesmo com o contador
    em zero.
"""

import asyncio
import contextvars
import math
import os
import re
import sqlite3
import sys

MENSAGEM_RECUPERACAO_NEUTRA = (
    "Se o e-mail informado estiver associado a uma conta, você receberá um código para redefinir sua senha."
)
MENSAGEM_NAO_CONFIGURADO = "A confirmação por e-mail não está disponível nesta instalação."
MENSAGEM_CODIGO_FORMATO = "Digite o código de 6 dígitos."
MENSAGEM_EXPIRADA = "O código expirou. Solicite um novo código."
MENSAGEM_FALHA_GENERICA = "Não foi possível concluir agora. Tente novamente mais tarde."
MENSAGEM_NOVA_TENTATIVA = "Não foi possível salvar agora. Seu código já foi confirmado: tente novamente."
# Erro inesperado DEPOIS de uma gravação concluída: os dados foram salvos; só a
# atualização da tela falhou (nunca apresentado como falha da operação).
MENSAGEM_CONCLUIDA_SEM_ATUALIZAR = "A operação foi concluída, mas a tela não pôde ser atualizada. Volte e entre novamente."

# Gravações locais em andamento em todo o processo: referência forte até o fim.
_GRAVACOES = set()


# Modo de demonstração (só desenvolvimento): os códigos vão para a caixa local
# deste computador (servidor/ferramentas/demonstracao.py), não para
# o e-mail. Só vale com a variável explícita E o serviço em 127.0.0.1.
TITULO_DEMONSTRACAO = "Sino — Demonstração"
AVISO_DEMONSTRACAO = "Modo de demonstração — códigos recebidos neste computador"
_RE_SERVICO_LOCAL = re.compile(r"http://127\.0\.0\.1:[0-9]{1,5}/?")


def modo_demonstracao(ambiente=None):
    ambiente = os.environ if ambiente is None else ambiente
    return (ambiente.get("SINO_MODO_DEMONSTRACAO") == "1"
            and _RE_SERVICO_LOCAL.fullmatch(ambiente.get("SINO_SERVICO_URL") or "") is not None)


def registrar_falha(contexto, erro):
    print(f"Sino: falha em {contexto} ({type(erro).__name__}).", file=sys.stderr)


def falha_transitoria(erro):
    """
    Falha da gravação local que pode passar com uma nova tentativa (banco
    ocupado ou travado, erro de E/S): a transação foi desfeita e a
    autorização continua sem uso. Recusas da camada de dados (ValueError e
    subclasses) e erros de programação não são transitórios.
    """
    return isinstance(erro, sqlite3.OperationalError)


def segundos_inteiros(segundos):
    return max(1, math.ceil(segundos))


TEXTO_REENVIAR = "Reenviar código"


def texto_reenvio(segundos):
    """Rótulo do botão de reenvio: com espera, "Reenviar código em N s"."""
    if segundos <= 0:
        return TEXTO_REENVIAR
    return f"{TEXTO_REENVIAR} em {segundos_inteiros(segundos)} s"


class ContadorReenvio:
    """
    Contagem regressiva do reenvio de UMA tela (Etapa 10, Bloco 3). A
    referência é sempre `operacao.segundos_para_reenvio(relogio())` -- o
    instante informado pelo serviço, guardado pelo cliente --; o contador
    só decide quando redesenhar.

      * `iniciar(operacao)` mostra o valor atual e devolve True se ainda há
        espera e há tique automático (`esperar` não é None): a tela então
        roda `rodar(geracao)` como tarefa;
      * `parar()` e qualquer novo `iniciar()` invalidam a tarefa anterior
        (geração); a tarefa também termina quando o controle da tela fica
        inativo ou o fechamento começa -- e nesses casos não chama
        `ao_mostrar`, então controles antigos nunca são atualizados;
      * `restante()` serve à guarda do clique: com espera, o clique é
        ignorado. Em zero o pedido é enviado, e uma recusa do serviço
        ("Aguarde") é mostrada normalmente.
    """

    def __init__(self, controle, relogio, esperar, ao_mostrar):
        self._controle = controle
        self._relogio = relogio
        self._esperar = esperar
        self._ao_mostrar = ao_mostrar
        self._operacao = None
        self.geracao = 0

    def restante(self):
        if self._operacao is None:
            return 0.0
        return self._operacao.segundos_para_reenvio(self._relogio())

    def _vigente(self, geracao=None):
        return ((geracao is None or geracao == self.geracao)
                and self._controle.ativo and not self._controle.fechando)

    def mostrar(self):
        """Redesenha uma vez com o valor atual (se a tela ainda está ativa)."""
        if self._vigente():
            self._ao_mostrar(self.restante())

    def iniciar(self, operacao):
        self._operacao = operacao
        self.geracao += 1
        self.mostrar()
        return self._esperar is not None and self.restante() > 0 and self._vigente()

    def parar(self):
        self._operacao = None
        self.geracao += 1

    async def rodar(self, geracao):
        while self._vigente(geracao):
            restante = self.restante()
            if restante <= 0:
                return
            # Até o próximo segundo inteiro exibido (entre 0 e 1 s).
            await self._esperar(restante - math.ceil(restante) + 1)
            if not self._vigente(geracao):
                return
            self._ao_mostrar(self.restante())


def mensagem_do_pedido(resultado, email=None, recuperacao=False):
    """(texto, eh_erro) para o resultado de pedir_codigo; None se não há o que mostrar."""
    nome = type(resultado).__name__
    if nome == "CodigoSolicitado":
        if recuperacao:
            return MENSAGEM_RECUPERACAO_NEUTRA, False
        return f"Enviamos um código de 6 dígitos para {email}.", False
    if nome == "Aguarde":
        return f"Aguarde {segundos_inteiros(resultado.segundos)} s para pedir outro código.", True
    if nome == "FalhaEnvio":
        return "Não foi possível enviar o código. Tente novamente em instantes.", True
    if nome == "EnvioNaoConfirmado":
        return "Não foi possível confirmar o envio do código. Tente novamente em instantes.", True
    if nome == "LimiteExcedido":
        return "Limite de pedidos de código atingido. Tente novamente mais tarde.", True
    if nome == "SemConexao":
        return "Sem conexão com a internet. Verifique sua conexão e tente novamente.", True
    if nome == "ServicoIndisponivel":
        return "O serviço de confirmação por e-mail não está disponível agora. Tente novamente mais tarde.", True
    if nome == "DesafioEncerrado":
        return "Este pedido não vale mais. Solicite um novo código.", True
    if nome == "OperacaoCancelada":
        return None
    return MENSAGEM_FALHA_GENERICA, True


def mensagem_da_validacao(resultado):
    """(texto, eh_erro) para um resultado de validar_codigo que não é a autorização."""
    nome = type(resultado).__name__
    if nome == "CodigoInvalido":
        if resultado.tentativas_restantes <= 0:
            return "Código incorreto. Solicite um novo código.", True
        plural = "tentativa" if resultado.tentativas_restantes == 1 else "tentativas"
        return f"Código incorreto. Restam {resultado.tentativas_restantes} {plural}.", True
    if nome == "DesafioEncerrado":
        return "Este código não vale mais. Solicite um novo código.", True
    if nome == "LimiteExcedido":
        return "Muitas tentativas a partir desta conexão. Tente novamente mais tarde.", True
    return mensagem_do_pedido(resultado)


class ControleOperacao:
    """
    Estado das tarefas de UMA tela ou diálogo com código. `encerrar()` é
    chamado ao sair dela (Voltar, Cancelar, troca de tela, sair da conta,
    fim da sessão): descarta a operação do serviço, cancela as tarefas que
    ainda não estão gravando e marca o controle como inativo -- depois disso
    nenhum controle da tela é atualizado.
    """

    def __init__(self, ao_encerrar=None, ao_falhar=None, fechamento=None):
        self.ativo = True
        self._fechamento = fechamento  # Fechamento da página: depois que começa, nada novo é feito
        self.ocupado = False
        self.em_gravacao = False
        self.operacao = None
        self._tarefas = set()
        self._gravacoes = set()
        self._ao_encerrar = ao_encerrar
        # Chamado com (texto, é_erro) quando uma ação termina com erro
        # inesperado e a tela ainda está ativa: libera os botões e mostra a
        # mensagem. A tela troca esta função quando muda de etapa.
        self.ao_falhar = ao_falhar
        self.resultado_gravacao = None  # último resultado real de uma gravação
        self.gravacao_concluida = False  # a ação em curso já gravou com sucesso
        # (função, argumentos) da gravação que falhou de forma transitória e
        # pode ser repetida tal como foi pedida; None fora desse estado.
        self.gravacao_pendente = None

    # ------------------------------------------------------------- tarefas
    def reservar(self):
        """
        Chamado no clique, antes de agendar a ação: devolve False (e a tela
        ignora o clique) se a tela já saiu ou se outra ação dela está em
        andamento -- inclusive uma ação agendada que ainda não começou.
        """
        if not self.ativo or self.ocupado or self.fechando:
            return False
        self.ocupado = True
        return True

    @property
    def fechando(self):
        return self._fechamento is not None and self._fechamento.iniciado

    async def executar(self, corotina_fn, *args):
        """
        Roda a ação reservada (via page.run_task) e libera a tela ao terminar.
        Cancelamento: termina em silêncio. Erro inesperado: registra só o tipo
        e, se a tela ainda está ativa, chama `ao_falhar` -- com a mensagem
        genérica de falha, ou, se a ação já tinha gravado com sucesso, com a
        mensagem de operação concluída (a transação não falhou).
        """
        if not self.ativo:
            self.ocupado = False
            return None
        self.gravacao_concluida = False
        tarefa = asyncio.current_task()
        if tarefa is not None:
            self._tarefas.add(tarefa)
        try:
            return await corotina_fn(*args)
        except asyncio.CancelledError:
            return None
        except Exception as erro:
            if self.gravacao_concluida:
                registrar_falha("atualização da tela após gravar", erro)
                conteudo = (MENSAGEM_CONCLUIDA_SEM_ATUALIZAR, False)
            else:
                registrar_falha("ação da tela", erro)
                conteudo = (MENSAGEM_FALHA_GENERICA, True)
            if self.ativo and self.ao_falhar is not None:
                try:
                    self.ao_falhar(conteudo)
                except Exception as erro_tela:
                    registrar_falha("liberação da tela após erro", erro_tela)
            return None
        finally:
            self.ocupado = False
            if tarefa is not None:
                self._tarefas.discard(tarefa)

    async def em_thread(self, funcao, *args):
        """Leitura ou cálculo (sem gravação) fora do loop; pode ser abandonado."""
        return await asyncio.to_thread(funcao, *args)

    async def gravar(self, funcao, *args):
        """
        Gravação local fora do loop, protegida: o futuro da thread fica com
        referência forte e é aguardado até o fim mesmo se a tarefa da tela for
        cancelada (shield sozinho não faz a tarefa externa esperar). Devolve o
        resultado ou levanta a exceção real da gravação. Se a tarefa da tela
        foi cancelada, guarda o resultado real em `resultado_gravacao` e
        propaga o cancelamento sem tocar na tela.

        A gravação é um futuro do executor (`run_in_executor`, com o contexto
        copiado como em `asyncio.to_thread`), não uma Task: ao fechar a janela
        o Flet encerra o `asyncio.run`, que cancela todas as Tasks pendentes;
        este futuro fica de fora e a tarefa da tela continua esperando a
        thread terminar. Se o próprio futuro for cancelado (ex.: executor
        encerrado), não há mais resultado a esperar: o cancelamento é
        propagado na hora -- a transação SQLite segue atômica na thread.
        """
        if self.fechando:
            # A janela está fechando: nenhuma gravação nova começa. A ação
            # termina em silêncio, como um cancelamento (nada foi gravado).
            raise asyncio.CancelledError()
        self.em_gravacao = True
        loop = asyncio.get_running_loop()
        contexto = contextvars.copy_context()
        gravacao = loop.run_in_executor(None, contexto.run, funcao, *args)
        for conjunto in (self._gravacoes, _GRAVACOES):
            conjunto.add(gravacao)
            gravacao.add_done_callback(conjunto.discard)
        cancelada = False
        try:
            while True:
                try:
                    resultado = await asyncio.shield(gravacao)
                    break
                except asyncio.CancelledError as cancelamento:
                    if not gravacao.done():
                        cancelada = True  # só a tarefa da tela foi cancelada: continua esperando a thread
                        continue
                    if gravacao.cancelled():
                        # O próprio futuro foi cancelado: esperar de novo giraria
                        # sem ceder ao loop. Resultado desconhecido.
                        self.resultado_gravacao = None
                        registrar_falha("gravação sem confirmação no encerramento", cancelamento)
                        raise
                    resultado = gravacao.result()  # a exceção real, se houver, sobe daqui
                    break
        except asyncio.CancelledError:
            raise
        except BaseException as erro:
            self.resultado_gravacao = erro
            if cancelada:
                registrar_falha("gravação concluída após o fechamento da tela", erro)
                raise asyncio.CancelledError() from None
            raise
        finally:
            self.em_gravacao = False
        self.resultado_gravacao = resultado
        self.gravacao_concluida = True
        if cancelada:
            raise asyncio.CancelledError()
        return resultado

    async def gravar_com_nova_tentativa(self, funcao, *args):
        """
        `gravar`, e numa falha transitória (`falha_transitoria`) guarda
        exatamente esta gravação em `gravacao_pendente` antes de levantar a
        exceção. Recusas, outros erros e o sucesso deixam a pendência vazia.
        """
        self.gravacao_pendente = None
        try:
            return await self.gravar(funcao, *args)
        except Exception as erro:
            if falha_transitoria(erro) and self.ativo:
                self.gravacao_pendente = (funcao, args)
            raise

    async def repetir_gravacao(self, ja_gravada):
        """
        Nova tentativa: repete a gravação pendente com os mesmos argumentos
        (a autorização já verificada, os mesmos dados), sem validar o código
        de novo. Antes, `ja_gravada(*args)` (leitura, em thread) diz se a
        tentativa anterior chegou a gravar -- nesse caso não grava de novo e
        devolve None. A camada de dados confere outra vez finalidade, vínculo
        e validade da autorização.
        """
        funcao, args = self.gravacao_pendente
        try:
            gravada = await self.em_thread(ja_gravada, *args)
        except Exception as erro:
            if not falha_transitoria(erro):
                self.gravacao_pendente = None
            raise
        if gravada:
            self.gravacao_pendente = None
            return None
        return await self.gravar_com_nova_tentativa(funcao, *args)

    def encerrar(self):
        """Sai da tela: nada mais é enviado ou mostrado; gravações em curso terminam sozinhas."""
        if not self.ativo:
            return
        self.ativo = False
        self.gravacao_pendente = None  # a autorização guardada não sai desta tela
        if self.operacao is not None:
            self.operacao.descartar()
        if not self.em_gravacao:
            try:
                atual = asyncio.current_task()
            except RuntimeError:  # fora de um loop
                atual = None
            for tarefa in list(self._tarefas):
                if tarefa is not atual:  # a própria ação que encerrou a tela termina normalmente
                    tarefa.cancel()
        if self._ao_encerrar is not None:
            self._ao_encerrar(self)


async def aguardar_todas_as_gravacoes():
    """
    Usado pelo Fechamento: espera todas as gravações locais em curso,
    inclusive as que começarem durante a espera (o Fechamento já bloqueou
    novas gravações das suas telas). Falhas e cancelamentos das gravações só
    são registrados. As gravações são futuros do executor (fora do
    cancelamento das Tasks); a atomicidade vem da transação SQLite.
    """
    aguardadas = set()
    while pendentes := [g for g in _GRAVACOES if g not in aguardadas]:
        for gravacao in pendentes:
            aguardadas.add(gravacao)
            try:
                await asyncio.shield(gravacao)
            except asyncio.CancelledError as cancelamento:
                if not gravacao.cancelled():
                    raise  # quem aguarda foi cancelado
                registrar_falha("gravação sem confirmação no encerramento", cancelamento)
            except Exception as erro:  # noqa: BLE001
                registrar_falha("gravação aguardada no encerramento", erro)


def ha_gravacao_em_curso():
    return any(not g.done() for g in _GRAVACOES)


class Fechamento:
    """
    Fechamento seguro da janela e fim da sessão de UMA página (Etapa 10,
    Bloco 2). `pedir()` é chamado pelo pedido de fechamento da janela (X,
    com `prevent_close`) e pelo fim da sessão (`on_close`/`on_disconnect`);
    todos os pedidos compartilham a mesma rotina, criada no primeiro.

    A rotina, em ordem:
      1. marca `iniciado`: os ControleOperacao ligados a este fechamento
         recusam novas ações e novas gravações;
      2. `encerrar_operacoes()` (tarefas da tela que ainda não gravam);
      3. se há gravação em curso: `avisar()` (falha só é registrada e não
         pula a espera) e espera TODAS as gravações terminarem, sem tempo
         limite -- `destroy()` não interromperia uma thread gravando; a
         garantia dos dados continua sendo a transação SQLite;
      4. se a espera falhar, registra o limite e segue para fechar, sem
         afirmar que a gravação terminou;
      5. `ao_terminar()` (ex.: fechar o transporte do serviço);
      6. se algum pedido veio da janela, `fechar_janela()` (destroy).

    Encerrar o processo pelo sistema continua possível e não é tratado aqui.
    """

    def __init__(self, avisar, fechar_janela, encerrar_operacoes=None, ao_terminar=None):
        self._avisar = avisar
        self._fechar_janela = fechar_janela
        self._encerrar_operacoes = encerrar_operacoes
        self._ao_terminar = ao_terminar
        self.iniciado = False
        self._pela_janela = False
        self._janela_fechada = False
        self._rotina = None

    def pedir(self, pela_janela):
        """Devolve a tarefa da rotina única (criada no primeiro pedido)."""
        if pela_janela:
            self._pela_janela = True
        if self._rotina is None:
            self.iniciado = True
            self._rotina = asyncio.ensure_future(self._executar())
        elif self._rotina.done() and pela_janela and not self._janela_fechada:
            # A rotina já terminou por fim de sessão: só falta fechar a janela.
            self._rotina = asyncio.ensure_future(self._fechar())
        return self._rotina

    async def _fechar(self):
        self._janela_fechada = True
        try:
            await self._fechar_janela()
        except Exception as erro:  # noqa: BLE001
            registrar_falha("fechamento da janela", erro)
        return True

    async def _executar(self):
        self.iniciado = True
        espera_confirmada = True
        try:
            if self._encerrar_operacoes is not None:
                self._encerrar_operacoes()
        except Exception as erro:  # noqa: BLE001
            registrar_falha("encerramento das operações no fechamento", erro)
        if ha_gravacao_em_curso():
            try:
                self._avisar()
            except Exception as erro:  # noqa: BLE001
                registrar_falha("aviso de fechamento", erro)  # continua esperando
            try:
                await aguardar_todas_as_gravacoes()
            except BaseException as erro:  # noqa: BLE001 -- inclusive cancelamento
                espera_confirmada = False
                registrar_falha("espera das gravações no fechamento", erro)
                print("Sino: a janela será fechada sem confirmar o fim da gravação em curso.", file=sys.stderr)
        if self._ao_terminar is not None:
            try:
                await self._ao_terminar()
            except Exception as erro:  # noqa: BLE001
                registrar_falha("fim da sessão", erro)
        if self._pela_janela:
            await self._fechar()
        return espera_confirmada
