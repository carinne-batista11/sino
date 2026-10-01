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
    falha. Erros inesperados registram só o tipo e liberam a tela.
"""

import asyncio
import math
import sys

MENSAGEM_RECUPERACAO_NEUTRA = (
    "Se o e-mail informado estiver associado a uma conta, você receberá um código para redefinir sua senha."
)
MENSAGEM_NAO_CONFIGURADO = "A confirmação por e-mail não está disponível nesta instalação."
MENSAGEM_CODIGO_FORMATO = "Digite o código de 6 dígitos."
MENSAGEM_EXPIRADA = "O código expirou. Solicite um novo código."
MENSAGEM_FALHA_GENERICA = "Não foi possível concluir agora. Tente novamente mais tarde."
# Erro inesperado DEPOIS de uma gravação concluída: os dados foram salvos; só a
# atualização da tela falhou (nunca apresentado como falha da operação).
MENSAGEM_CONCLUIDA_SEM_ATUALIZAR = "A operação foi concluída, mas a tela não pôde ser atualizada. Volte e entre novamente."

# Gravações locais em andamento em todo o processo: referência forte até o fim.
_GRAVACOES = set()


def registrar_falha(contexto, erro):
    print(f"Sino: falha em {contexto} ({type(erro).__name__}).", file=sys.stderr)


def segundos_inteiros(segundos):
    return max(1, math.ceil(segundos))


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

    def __init__(self, ao_encerrar=None, ao_falhar=None):
        self.ativo = True
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

    # ------------------------------------------------------------- tarefas
    def reservar(self):
        """
        Chamado no clique, antes de agendar a ação: devolve False (e a tela
        ignora o clique) se a tela já saiu ou se outra ação dela está em
        andamento -- inclusive uma ação agendada que ainda não começou.
        """
        if not self.ativo or self.ocupado:
            return False
        self.ocupado = True
        return True

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
        Gravação local fora do loop, protegida: a tarefa da thread fica com
        referência forte e é aguardada até o fim mesmo se a tarefa da tela for
        cancelada (shield sozinho não faz a tarefa externa esperar). Devolve o
        resultado ou levanta a exceção real da gravação. Se a tarefa da tela
        foi cancelada, guarda o resultado real em `resultado_gravacao` e
        propaga o cancelamento sem tocar na tela.
        """
        self.em_gravacao = True
        gravacao = asyncio.ensure_future(asyncio.to_thread(funcao, *args))
        for conjunto in (self._gravacoes, _GRAVACOES):
            conjunto.add(gravacao)
            gravacao.add_done_callback(conjunto.discard)
        cancelada = False
        try:
            while True:
                try:
                    resultado = await asyncio.shield(gravacao)
                    break
                except asyncio.CancelledError:
                    if gravacao.done() and not gravacao.cancelled():
                        resultado = gravacao.result()  # a exceção real, se houver, sobe daqui
                        break
                    cancelada = True  # a tela foi cancelada: continua esperando a thread
        except asyncio.CancelledError:  # pragma: no cover -- defensivo
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

    def encerrar(self):
        """Sai da tela: nada mais é enviado ou mostrado; gravações em curso terminam sozinhas."""
        if not self.ativo:
            return
        self.ativo = False
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
    Usado no fim da sessão do Flet: espera qualquer gravação local ainda em
    curso. Não há garantia de que o Flet aguarde quem chama esta função: no
    desktop, ao fechar a janela, o evento de fim de sessão é disparado sem
    espera e as tarefas em execução são canceladas. Nesse caso, a gravação
    depende da atomicidade da transação SQLite e do encerramento do loop e do
    executor de threads (validação real do fechamento: pendente).
    """
    for gravacao in list(_GRAVACOES):
        try:
            await asyncio.shield(gravacao)
        except Exception as erro:  # noqa: BLE001
            registrar_falha("gravação aguardada no encerramento", erro)
