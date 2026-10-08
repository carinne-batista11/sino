"""
Roteiro do AMBIENTE REMOTO DE TESTES do serviço de códigos (ERS v7.0, E4,
T1): Worker sino-servico-codigos-teste (wrangler.teste.jsonc, entrada
src/teste.ts), com envio descartado e token obrigatório. Só biblioteca padrão.

    python3 teste_remoto.py preparar --pasta PASTA --url URL
    python3 teste_remoto.py basico          --config PASTA/teste_remoto.json
    python3 teste_remoto.py limite-destino  --config PASTA/teste_remoto.json
    python3 teste_remoto.py ip              --config PASTA/teste_remoto.json

preparar  cria PASTA (nova, permissão 700, fora do repositório) com os
          segredos EXCLUSIVOS deste ambiente, em arquivos 600 que nunca são
          sobrescritos: segredos.json (para `wrangler deploy --secrets-file`),
          segredos.env (para `wrangler dev --env-file`, só no ensaio local) e
          teste_remoto.json (URL e token, lido pelos outros comandos). A lista
          de destinatários tem só os endereços fictícios ENDERECOS_TESTE
          (domínio reservado .invalid). URL: o endereço do Worker de teste
          (https://sino-servico-codigos-teste.<subdomínio>.workers.dev) ou,
          no ensaio local, http://127.0.0.1:<porta>.
basico          casos 1 a 6 e o intervalo de 60 s (7 pedidos do IP);
limite-destino  limite por destino na hora (6 pedidos do IP; cerca de 5 min);
ip              limite por IP com CF-Connecting-IP forjado (11 pedidos do IP).

Limites do serviço (contrato; o roteiro não os altera, só se planeja por
eles). As janelas são fixas em UTC: hora cheia e dia de 00:00 a 23:59 UTC, ou
seja, em Brasília (UTC-3) de HH:00 a HH:59 e de 21:00 a 20:59 do dia seguinte.
Só contam as requisições ao Worker de teste, e as recusadas pelo token (404)
não contam.

  comando          pedidos do IP  pedidos por destino           duração
  basico           7 (de 10/h)    pessoa1 1, pessoa2 1 (de 5/h)  < 1 min
  limite-destino   6 (de 10/h)    pessoa3 5 + 1 recusado         ~5 min
  ip               11 (de 10/h)   nenhum (fora da lista)         < 1 min

Por isso o roteiro (registro em PASTA/janelas.json) recusa:
  * dois comandos na mesma hora UTC (o caso "ip" precisa da hora sem nenhum
    outro pedido, e os outros dois juntos passariam de 10 na hora);
  * passar de 30 pedidos do IP no dia UTC (os três uma vez = 24; uma
    repetição de qualquer um no mesmo dia passaria de 30 ou chegaria perto);
  * "limite-destino" mais de 2 vezes no dia UTC (pessoa3 tem 10 pedidos/dia);
  * "limite-destino" depois do minuto 51 da hora (os 6 pedidos com 61 s de
    intervalo precisam caber na mesma hora).
Horários possíveis: três horas UTC diferentes no mesmo dia UTC (por exemplo,
em Brasília, basico às 10:05, limite-destino entre 11:00 e 11:51, ip às 12:05)
ou em dias diferentes; o ambiente dura no máximo 7 dias após o deploy.

Nada sensível é mostrado: nem o token, nem segredos, nem e-mails; das
respostas, só o status e o nome do erro. O envio é descartado pelo serviço, por
isso o código correto nunca é conhecido e o caminho "código certo -> 200" não
é testado aqui (fica com os testes locais).
"""

import argparse
import datetime
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import destinatarios  # noqa: E402

ENDERECOS_TESTE = (
    "pessoa1@teste.invalid",
    "pessoa2@teste.invalid",
    "pessoa3@teste.invalid",
)
FORA_DA_LISTA = "fora@teste.invalid"
KID_TESTE = "teste-1"
NOME_WORKER = "sino-servico-codigos-teste"
TEMPO_LIMITE_S = 15
INTERVALO_REENVIO_S = 61
CAMPOS_PEDIDO = {"desafio_id", "expira_em", "reenvio_permitido_em", "agora"}
# Limites do contrato usados só para planejar as execuções (não alteram nada).
LIMITE_IP_DIA = 30
EXECUCOES_LIMITE_DESTINO_DIA = 2  # 5 pedidos aceitos por execução; 10 por dia
ULTIMO_MINUTO_LIMITE_DESTINO = 51
PEDIDOS_DO_IP = {"basico": 7, "limite-destino": 6, "ip": 11}
RAIZ_REPOSITORIO = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


class Falha(Exception):
    """Configuração recusada; a mensagem nunca contém segredos."""


# ======================================================================
#  Preparação
# ======================================================================

def validar_url(url):
    partes = urllib.parse.urlsplit(url)
    if partes.path not in ("", "/") or partes.query or partes.fragment or partes.username or partes.password:
        raise Falha("URL com caminho, consulta ou credenciais")
    if partes.scheme == "https":
        host = partes.hostname or ""
        prefixo = f"{NOME_WORKER}."
        sub = host[len(prefixo):-len(".workers.dev")] if host.startswith(prefixo) and host.endswith(".workers.dev") else ""
        if partes.port is None and sub and "." not in sub:
            return f"https://{host}"
        raise Falha(f"URL remota precisa ser https://{NOME_WORKER}.<subdomínio>.workers.dev")
    if partes.scheme == "http" and partes.hostname == "127.0.0.1" and partes.port:
        return f"http://127.0.0.1:{partes.port}"
    raise Falha("URL aceita: o Worker de teste em workers.dev ou http://127.0.0.1:<porta>")


def gravar_privado(caminho, texto):
    descritor = os.open(caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
        arquivo.write(texto)


def preparar(pasta, url):
    url = validar_url(url)
    real = os.path.realpath(pasta)
    if real == RAIZ_REPOSITORIO or real.startswith(RAIZ_REPOSITORIO + os.sep):
        raise Falha("a pasta não pode ficar dentro do repositório")
    if os.path.exists(real):
        raise Falha("a pasta já existe; use uma pasta nova (nada é sobrescrito)")
    os.makedirs(real, mode=0o700)
    chave_hmac = secrets.token_bytes(32)
    lista, _ = destinatarios.montar(chave_hmac, list(ENDERECOS_TESTE))
    segredos = {
        "CHAVE_HMAC": chave_hmac.hex(),
        # Semente Ed25519: quaisquer 32 bytes servem.
        "CHAVE_ASSINATURA": secrets.token_bytes(32).hex(),
        "DESTINATARIOS_PERMITIDOS": lista,
        "TOKEN_TESTE": secrets.token_urlsafe(32),
    }
    gravar_privado(os.path.join(real, "segredos.json"), json.dumps(segredos, indent=2) + "\n")
    gravar_privado(os.path.join(real, "segredos.env"), "".join(f"{k}={v}\n" for k, v in segredos.items()))
    gravar_privado(os.path.join(real, "teste_remoto.json"),
                   json.dumps({"url": url, "token": segredos["TOKEN_TESTE"]}, indent=2) + "\n")
    print(f"pasta: {real}")
    print("arquivos (600): segredos.json, segredos.env, teste_remoto.json")
    print(f"destinatários fictícios na lista: {len(ENDERECOS_TESTE)}")


def ler_config(caminho):
    if os.stat(caminho).st_mode & 0o077:
        raise Falha("o arquivo de configuração precisa ter permissão 600")
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except ValueError:
        raise Falha("arquivo de configuração ilegível") from None
    if not isinstance(dados, dict):
        raise Falha("arquivo de configuração ilegível")
    token = dados.get("token")
    if not isinstance(token, str) or len(token) != 43:
        raise Falha("token ausente ou fora do formato no arquivo de configuração")
    return validar_url(dados.get("url", "")), token


# ======================================================================
#  Janelas (uma hora UTC por comando)
# ======================================================================

def hora_utc(agora=None):
    agora = agora or datetime.datetime.now(datetime.timezone.utc)
    return agora.strftime("%Y-%m-%dT%H")


def reservar_janela(pasta, url, comando, agora=None):
    caminho = os.path.join(pasta, "janelas.json")
    janelas = []
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding="utf-8") as arquivo:
                janelas = json.load(arquivo)
        except ValueError:
            raise Falha("janelas.json ilegível; não executo sem o registro das horas usadas") from None
    hora = hora_utc(agora)
    dia = hora[:10]
    do_ambiente = [j for j in janelas if j["url"] == url]
    for j in do_ambiente:
        if j["hora"] == hora:
            raise Falha(f"'{j['comando']}' já rodou nesta hora UTC ({hora}h); "
                        "espere a próxima hora cheia para não misturar os limites por IP")
    no_dia = [j for j in do_ambiente if j["hora"][:10] == dia]
    pedidos = sum(PEDIDOS_DO_IP[j["comando"]] for j in no_dia) + PEDIDOS_DO_IP[comando]
    if pedidos > LIMITE_IP_DIA:
        raise Falha(f"passaria de {LIMITE_IP_DIA} pedidos do IP no dia UTC {dia}; "
                    "rode depois das 00:00 UTC (21:00 em Brasília)")
    if comando == "limite-destino" and sum(j["comando"] == comando for j in no_dia) >= EXECUCOES_LIMITE_DESTINO_DIA:
        raise Falha(f"'limite-destino' já rodou {EXECUCOES_LIMITE_DESTINO_DIA} vezes no dia UTC {dia} "
                    "(limite diário do destino); rode depois das 00:00 UTC")
    janelas.append({"url": url, "hora": hora, "comando": comando})
    temporario = caminho + ".novo"
    with open(os.open(temporario, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600), "w", encoding="utf-8") as arquivo:
        json.dump(janelas, arquivo, indent=2)
    os.replace(temporario, caminho)


# ======================================================================
#  Requisições
# ======================================================================

class Cliente:
    def __init__(self, url, token):
        self.url = url
        self.token = token

    def enviar(self, caminho, corpo=None, metodo="POST", chave=None, autorizacao=True, extra=None, bruto=None):
        cabecalhos = {"User-Agent": "sino-teste-remoto/1"}
        if autorizacao is True:
            cabecalhos["Authorization"] = f"Bearer {self.token}"
        elif isinstance(autorizacao, str):
            cabecalhos["Authorization"] = autorizacao
        dados = None
        if bruto is not None or corpo is not None:
            dados = bruto if bruto is not None else json.dumps(corpo, separators=(",", ":")).encode("utf-8")
            cabecalhos["Content-Type"] = "application/json"
        if metodo == "POST":
            cabecalhos["Idempotency-Key"] = chave or f"remoto-{secrets.token_urlsafe(16)}"
        cabecalhos.update(extra or {})
        pedido = urllib.request.Request(self.url + caminho, data=dados, headers=cabecalhos, method=metodo)
        try:
            with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE_S) as resposta:
                return resposta.status, ler_json(resposta.read())
        except urllib.error.HTTPError as erro:
            return erro.code, ler_json(erro.read())

    def pedido(self, finalidade, email, chave=None, extra=None, contexto=None, segredo=None):
        corpo = {
            "finalidade": finalidade,
            "email": email,
            "contexto": contexto or secrets.token_hex(32),
            "segredo": segredo or secrets.token_urlsafe(32),
        }
        return self.enviar("/v1/desafios", corpo, chave=chave, extra=extra)

    def validacao(self, desafio_id, email, segredo, codigo):
        return self.enviar(f"/v1/desafios/{desafio_id}/validacao",
                           {"email": email, "segredo": segredo, "codigo": codigo})


def ler_json(bytes_):
    try:
        dados = json.loads(bytes_.decode("utf-8"))
        return dados if isinstance(dados, dict) else None
    except (UnicodeDecodeError, ValueError):
        return None


class Relatorio:
    def __init__(self):
        self.falhas = 0

    def conferir(self, nome, status, corpo, esperado_status, esperado_erro=None, campos=None, extra_ok=True):
        erro = (corpo or {}).get("erro")
        ok = status == esperado_status and erro == esperado_erro and extra_ok
        if campos is not None:
            ok = ok and corpo is not None and set(corpo) == campos
        # Nenhuma resposta pode trazer um código de 6 dígitos.
        if corpo is not None and any(isinstance(v, str) and v.isdigit() and len(v) == 6 for v in corpo.values()):
            ok = False
        recebido = f"{status}" + (f" {erro}" if erro else "") + ("" if corpo is not None else " (sem JSON)")
        if ok:
            print(f"OK      {nome}: {recebido}")
        else:
            self.falhas += 1
            esperado = f"{esperado_status}" + (f" {esperado_erro}" if esperado_erro else "")
            print(f"FALHOU  {nome}: esperado {esperado}, recebido {recebido}")
        return ok

    def fim(self):
        print("resultado:", "aprovado" if self.falhas == 0 else f"{self.falhas} caso(s) com falha")
        return 0 if self.falhas == 0 else 1


# ======================================================================
#  Casos
# ======================================================================

def caso_basico(c, r):
    pessoa1, pessoa2 = ENDERECOS_TESTE[0], ENDERECOS_TESTE[1]

    # 1. Token (antes de qualquer objeto; não consome limites).
    s, b = c.enviar("/v1/desafios", {}, autorizacao=False)
    r.conferir("1a sem token", s, b, 404, "rota_nao_encontrada")
    s, b = c.enviar("/v1/desafios", {}, autorizacao=f"Bearer {secrets.token_urlsafe(32)}")
    r.conferir("1b token errado", s, b, 404, "rota_nao_encontrada")

    # 2. Rotas e formato (não consomem o limite do IP).
    s, b = c.enviar("/x", {})
    r.conferir("2a rota inexistente", s, b, 404, "rota_nao_encontrada")
    s, b = c.enviar("/v1/desafios", metodo="GET")
    r.conferir("2b GET /v1/desafios", s, b, 405, "metodo_nao_permitido")
    s, b = c.enviar("/v1/desafios", bruto=b"{" + b" " * 5000 + b"}")
    r.conferir("2c corpo acima de 4 KiB", s, b, 413, "corpo_grande_demais")
    s, b = c.enviar("/v1/desafios", bruto=b"{nao e json")
    r.conferir("2d JSON inválido", s, b, 400, "requisicao_invalida")

    # 3. Cadastro na lista e repetição (2 pedidos do IP).
    chave, contexto, segredo = f"remoto-{secrets.token_urlsafe(16)}", secrets.token_hex(32), secrets.token_urlsafe(32)
    s, b = c.pedido("cadastro", pessoa1, chave=chave, contexto=contexto, segredo=segredo)
    criado = r.conferir("3a cadastro na lista", s, b, 201, campos=CAMPOS_PEDIDO)
    desafio = (b or {}).get("desafio_id")
    s, b2 = c.pedido("cadastro", pessoa1, chave=chave, contexto=contexto, segredo=segredo)
    r.conferir("3b repetição com a mesma chave", s, b2, 201, campos=CAMPOS_PEDIDO,
               extra_ok=(b2 or {}).get("desafio_id") == desafio)

    # 4. Código errado até esgotar (validações; não consomem pedidos).
    if criado and desafio:
        s, b = c.validacao(desafio, pessoa1, secrets.token_urlsafe(32), "000000")
        r.conferir("4a segredo que não confere", s, b, 404, "desafio_nao_encontrado")
        for restantes in (4, 3, 2, 1, 0):
            s, b = c.validacao(desafio, pessoa1, segredo, "000000")
            if s == 200:
                # Probabilidade 1 em 1 milhão: o código sorteado era 000000.
                print("AVISO   4 o código sorteado coincidiu com 000000; caso 4 inconclusivo")
                break
            r.conferir(f"4b código errado (restam {restantes})", s, b, 422, "codigo_invalido",
                       extra_ok=(b or {}).get("tentativas_restantes") == restantes)
        else:
            s, b = c.validacao(desafio, pessoa1, segredo, "000000")
            r.conferir("4c depois de esgotar", s, b, 410, "desafio_encerrado")

    # 5. Fora da lista (2 pedidos do IP).
    s, b = c.pedido("cadastro", FORA_DA_LISTA)
    r.conferir("5a cadastro fora da lista", s, b, 403, "destinatario_nao_permitido")
    s, b = c.pedido("alteracao_email", FORA_DA_LISTA)
    r.conferir("5b alteração fora da lista", s, b, 403, "destinatario_nao_permitido")

    # 6. Recuperação fora da lista: resposta neutra (1 pedido do IP).
    s, b = c.pedido("recuperacao_senha", FORA_DA_LISTA)
    r.conferir("6 recuperação fora da lista (neutra)", s, b, 202, campos=CAMPOS_PEDIDO)

    # 7a. Intervalo de 60 s por destino (2 pedidos do IP).
    s, b = c.pedido("cadastro", pessoa2)
    r.conferir("7a primeiro pedido", s, b, 201, campos=CAMPOS_PEDIDO)
    s, b = c.pedido("cadastro", pessoa2)
    r.conferir("7a segundo pedido antes de 60 s", s, b, 429, "aguarde",
               campos={"erro", "reenvio_permitido_em", "agora"})


def caso_limite_destino(c, r, esperar):
    pessoa3 = ENDERECOS_TESTE[2]
    for i in range(1, 6):
        s, b = c.pedido("cadastro", pessoa3)
        r.conferir(f"7b pedido {i} de 5 para o mesmo destino", s, b, 201, campos=CAMPOS_PEDIDO)
        esperar(INTERVALO_REENVIO_S)
    s, b = c.pedido("cadastro", pessoa3)
    r.conferir("7b sexto pedido na hora", s, b, 429, "limite_excedido")


def caso_ip(c, r):
    # O limite do IP é consumido antes da conferência da lista: 10 pedidos
    # fora da lista -> 403 e o seguinte -> 429, mesmo com CF-Connecting-IP
    # forjado e diferente a cada pedido. Se a borda recusar o cabeçalho, o
    # caso fica inconclusivo (status e corpo mostram o que aconteceu). Um 403
    # no 11.º indica que o valor do cliente foi usado OU que a conexão alternou
    # entre IPv4 e IPv6 (dois limites separados); repetir noutra hora antes de
    # concluir.
    for i in range(1, 11):
        forjado = f"198.51.100.{i}"
        s, b = c.pedido("cadastro", FORA_DA_LISTA, extra={"CF-Connecting-IP": forjado})
        r.conferir(f"9 pedido {i} com IP forjado", s, b, 403, "destinatario_nao_permitido")
    s, b = c.pedido("cadastro", FORA_DA_LISTA, extra={"CF-Connecting-IP": "198.51.100.200"})
    r.conferir("9 pedido 11 com IP forjado (limite do IP real)", s, b, 429, "limite_excedido")


def main(argv=None, esperar=None):
    import time

    analisador = argparse.ArgumentParser(description="Roteiro do ambiente remoto de testes (E4, T1).")
    sub = analisador.add_subparsers(dest="comando", required=True)
    p = sub.add_parser("preparar")
    p.add_argument("--pasta", required=True)
    p.add_argument("--url", required=True)
    for nome in ("basico", "limite-destino", "ip"):
        sub.add_parser(nome).add_argument("--config", required=True)
    args = analisador.parse_args(argv)
    try:
        if args.comando == "preparar":
            preparar(args.pasta, args.url)
            return 0
        url, token = ler_config(args.config)
        minuto = datetime.datetime.now(datetime.timezone.utc).minute
        if args.comando == "limite-destino" and minuto > ULTIMO_MINUTO_LIMITE_DESTINO:
            # Os 6 pedidos levam cerca de 5 min e precisam caber na mesma hora.
            raise Falha("menos de 8 minutos até a próxima hora UTC; comece depois da hora cheia")
        reservar_janela(os.path.dirname(os.path.realpath(args.config)), url, args.comando)
        print(f"ambiente: {url}  hora UTC: {hora_utc()}h  comando: {args.comando}")
        cliente, relatorio = Cliente(url, token), Relatorio()
        if args.comando == "basico":
            caso_basico(cliente, relatorio)
        elif args.comando == "limite-destino":
            caso_limite_destino(cliente, relatorio, esperar or time.sleep)
        else:
            caso_ip(cliente, relatorio)
        return relatorio.fim()
    except Falha as erro:
        print(f"recusado: {erro}", file=sys.stderr)
        return 2
    except (urllib.error.URLError, TimeoutError, OSError) as erro:
        print(f"falha de conexão ({type(erro).__name__})", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
