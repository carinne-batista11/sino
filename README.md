<p align="center">
  <img src="docs/capasino_github.png" alt="Sino — Controle de contas pessoais" width="100%">
</p>

# 🔔 Sino

**Controle de contas pessoais, simples e sem surpresas no fim do mês.**

![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Flet 0.86.5](https://img.shields.io/badge/Flet-0.86.5-1D9E75)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-green)

O Sino é um aplicativo desktop para registrar e acompanhar as contas do dia a dia: aluguel, internet, faculdade, assinaturas e parcelas. Ele mostra o que vence, o que está em atraso e quanto do mês já foi pago, com os dados guardados localmente no seu computador. A única comunicação do app com a internet é a confirmação de e-mail por código, descrita abaixo.

É um projeto de portfólio, desenvolvido a partir de uma Especificação de Requisitos de Software (ERS) versionada, com as decisões de produto registradas a cada versão e testes automatizados.

## ✨ Funcionalidades

A **v5.0**, descrita na [ERS v5.0](docs/ERS_Controle_de_Contas_v5.0.md), está concluída e auditada. A v6.0 está em implementação (veja a seção seguinte).

- **Contas únicas, mensais ou anuais**, com ou sem data de término. Os vencimentos respeitam o calendário: uma conta do dia 31 vence em 28/02 e volta para 31/03.
- **Edição e exclusão com escopo**: em contas recorrentes, você escolhe entre "Somente este mês" e "Este mês em diante".
- **Recorrência flexível**: transforme uma conta avulsa em recorrente, altere a frequência ou encerre a recorrência sem perder o histórico.
- **Pagamentos** com data efetiva e status de atraso calculado automaticamente.
- **Visão do mês**: total do mês, contas que vencem nos próximos 7 dias e aviso de contas em atraso, com uma tela dedicada a elas.
- **Categorias** com emoji e cor própria: 11 prontas para usar e até 30 por usuário.
- **Parcelas**: cada ocorrência mostra sua posição na série, como "Parcela 3 de 12".
- **Contas de usuário** com aceite dos Termos de Uso e senhas armazenadas com PBKDF2.

## 🚧 v6.0 em implementação

A v6.0 está especificada na [ERS v6.0](docs/ERS_Controle_de_Contas_v6.0.md) e é implementada em etapas (seção 15 da ERS). As mudanças estão resumidas nas [notas da versão](docs/notas-da-versao.md).

- **Etapas 1 a 7, concluídas:** descrição opcional e limites de caracteres, escopo de edição nas séries, Tela Principal com todas as contas, "Ver status", **Detalhes da conta** reformulada, tela **Gráfico**, tela **Ajustes** (nome, tema claro/escuro, Termos e Política, sair da conta), senha mínima de 8 caracteres e alteração de senha.
- **Etapa 8, em andamento:** cadastro com confirmação do e-mail por **código**, alteração de e-mail e "Esqueci minha senha".
  - **Entrega local concluída e validada:** os códigos vêm de um serviço próprio ([`servidor/`](servidor/)), que roda no próprio computador com uma caixa de mensagens local.
  - **Publicação para outras pessoas pendente:** a integração com a Resend está implementada, mas o serviço ainda não foi publicado e a entrega real de e-mails não foi validada.
  - Sem o serviço configurado, criar conta, alterar o e-mail e recuperar a senha ficam indisponíveis (o app avisa). **O login continua local** e funciona sem internet.
  - Para experimentar esses fluxos no próprio computador, há um [modo de demonstração](servidor/README.md#modo-de-demonstração-desenvolvimento): os códigos chegam a uma caixa local, o que **não comprova** acesso ao endereço de e-mail.
  - Fechar a janela durante uma gravação não corrompe dados; o fechamento seguro da janela ainda não foi implementado (Etapa 10).
- **Próximas:** excluir conta (Etapa 9), revisão geral de UX e do tema escuro (Etapa 10), testes finais e README.

### Protótipos da v6.0

> [!NOTE]
> As imagens abaixo são **protótipos** da v6.0. Elas mostram a direção visual da versão e podem diferir das telas implementadas.

<p align="center">
  <img src="docs/prototipos/13_detalhe_conta.png" width="640" alt="Protótipo da v6.0: tela Detalhes da conta">
</p>

<p align="center">
  <img src="docs/prototipos/10_grafico_mensal.png" width="300" alt="Protótipo da v6.0: tela Gráfico, visualização mensal">
  &nbsp;&nbsp;
  <img src="docs/prototipos/12_ajustes.png" width="520" alt="Protótipo da v6.0: tela Ajustes">
</p>

## 🛠️ Tecnologias

- **Python 3.11**
- **[Flet](https://flet.dev) 0.86.5**, para a interface desktop
- **SQLite**, para o armazenamento local dos dados
- **unittest** (biblioteca padrão do Python), para os testes automatizados
- **httpx** e **cryptography**, no cliente do serviço de códigos de e-mail (em desenvolvimento)
- **TypeScript**, **Cloudflare Workers** com **Durable Objects** (SQLite) e **Resend**, no serviço de códigos de e-mail, em desenvolvimento local e ainda não publicado; testes com **Vitest**

## ▶️ Como executar

Pré-requisito: Python 3.11.

```bash
git clone https://github.com/carinne-batista11/sino.git
cd sino

python3 -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate

pip install -r requirements.txt
python3 backend/main.py
```

Na primeira execução, o banco de dados é criado automaticamente em `database/sino.db`. Esse arquivo fica apenas na sua máquina e não é versionado.

Sem o serviço de códigos configurado, a tela de cadastro avisa que a confirmação por e-mail não está disponível e não cria a conta. Para testar o cadastro, a recuperação de senha e a alteração de e-mail localmente, use o [modo de demonstração](servidor/README.md#modo-de-demonstração-desenvolvimento), que também precisa do Node.js 24.

## 🧪 Testes

Com o ambiente virtual `.venv` ativado e as dependências instaladas (veja "Como executar"):

```bash
python3 -m unittest discover tests
```

A suíte precisa do `.venv`: o cliente do serviço de códigos usa o `cryptography`, instalado pelo `requirements.txt`. Ela cobre a camada de dados (recorrência e geração de ocorrências, edição e exclusão com escopo, pagamentos, categorias e autenticação), as telas e o cliente do serviço de códigos. Cada teste de dados roda em um banco SQLite temporário e isolado, sem tocar nos dados reais do aplicativo. Nenhum teste acessa a rede externa; alguns usam conexões locais em `127.0.0.1` e os comandos `git`, `tar` e `ss` (Linux).

Os testes do serviço de códigos (`servidor/`) usam Node.js 24 e rodam localmente, sem conta em serviços externos:

```bash
cd servidor
npm ci
npm test
```

## 📁 Estrutura

```
backend/    interface do aplicativo (Flet), paleta de cores do tema e cliente do serviço de códigos
database/   camada de dados (SQLite)
docs/       especificações (ERS), contrato do serviço de códigos e protótipos de interface
servidor/   serviço de códigos de e-mail (em desenvolvimento local, não publicado)
tests/      testes automatizados do aplicativo
```

## 📄 Documentação

- [ERS v6.0](docs/ERS_Controle_de_Contas_v6.0.md): versão em implementação (estado da Etapa 8 na seção 13.3)
- [ERS v5.0](docs/ERS_Controle_de_Contas_v5.0.md): versão implementada e auditada
- [Notas da versão](docs/notas-da-versao.md)
- [Contrato do serviço de códigos](docs/contrato-servico-codigos.md)
- [Validação da Etapa 8](docs/validacao-etapa8.md): resumo das validações manuais, com ressalvas

Versões anteriores da ERS e os protótipos de interface estão em [`docs/`](docs/).

## 👩‍💻 Autora

**Carinne Batista**

O Sino é um projeto de portfólio, construído para praticar o ciclo completo de desenvolvimento de software: especificação de requisitos, modelagem de dados, implementação, testes e documentação.

## Licença

Distribuído sob a licença MIT. Veja o arquivo [`LICENSE`](LICENSE).
