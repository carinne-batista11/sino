"""
documentos.py — Termos de Uso e Política de Privacidade do Sino (ERS v6.0,
5.37, RF15/RF41), em Markdown.

Texto aprovado pela autora em 30/09/2026. É a mesma fonte exibida no
cadastro (antes do aceite) e em Ajustes > Sobre e privacidade. Qualquer
mudança de conteúdo deve ser revisada antes e mencionada nas notas da
versão (seção "Alterações" de cada documento). O endereço de contato é
apenas informativo: o Sino não envia e-mails.
"""

TERMOS_DE_USO = """\
# Termos de Uso do Sino

Última atualização: 30/09/2026

O Sino é um projeto pessoal de portfólio desenvolvido por Carinne Batista. Estes termos descrevem a **versão desktop atual** do Sino.

## 1. O que é o Sino

O Sino é um aplicativo para computador que ajuda você a registrar e acompanhar suas contas do dia a dia, como aluguel, internet, assinaturas e parcelas.

O Sino funciona localmente: cada instalação guarda suas informações no próprio computador onde está instalada. O aplicativo não envia essas informações à desenvolvedora nem a outras pessoas.

## 2. Aceite

Ao criar sua conta no Sino, você marca a opção "Li e aceito os Termos de Uso e a Política de Privacidade". Sem esse aceite, a conta não é criada. O Sino guarda a data em que o aceite foi feito.

## 3. O que o Sino faz e o que ele não faz

O Sino registra as informações financeiras que **você mesmo digita**: nome da conta, valor, data de vencimento, categoria, descrição, recorrência e se a conta foi paga. Com elas, o app mostra totais, lembretes na tela, listas por situação e gráficos.

O Sino **não** faz pagamentos, **não** acessa contas bancárias, cartões ou qualquer instituição financeira, e **não** confere se as informações registradas estão corretas. Marcar uma conta como "paga" no Sino é apenas um registro seu; não quita nenhuma dívida.

Os lembretes aparecem somente dentro do aplicativo, quando ele está aberto. O Sino não envia avisos por e-mail, mensagem ou notificação.

O Sino não oferece orientação financeira, contábil ou jurídica.

## 4. Sua conta de usuário

Para usar o Sino, você informa nome, e-mail e senha. O e-mail é usado para entrar no aplicativo; nesta versão, o Sino **não verifica** se o endereço existe ou pertence a você e não envia e-mails.

Nesta versão, **não é possível recuperar uma senha esquecida**, nem alterar o e-mail ou a senha pelo aplicativo. Guarde sua senha com cuidado.

Em Ajustes, você pode alterar seu nome e escolher o tema (Claro ou Escuro).

## 5. Seus cuidados

Ao usar o Sino, é importante:

* conferir as informações que você registra antes de tomar decisões com base nelas;
* proteger o acesso ao computador e à pasta do Sino;
* manter suas próprias cópias de segurança, se desejar, já que o Sino não as cria de forma periódica.

## 6. Sair da conta não apaga dados

"Sair da conta" apenas encerra a sessão e volta à tela de entrada. Suas contas, categorias e preferências continuam guardadas e reaparecem quando você entrar novamente.

Excluir uma conta financeira ou uma categoria remove esse item do aplicativo. Nesta versão, **não existe a opção de excluir o usuário** com todos os seus dados.

## 7. Limitações conhecidas

O Sino pode conter erros. Nenhum sistema é totalmente seguro, e o Sino não promete proteção absoluta das informações.

## 8. Alterações destes termos

Estes termos podem mudar em versões futuras do Sino. Quando isso acontecer, o texto atualizado ficará disponível dentro do aplicativo e as alterações serão mencionadas nas notas da versão. Nesta versão, o Sino não registra qual versão do texto foi aceita nem pede um novo aceite quando o texto muda.

## 9. Contato

Dúvidas, sugestões e relatos de problemas podem ser enviados para sino.lembrete.contas@gmail.com. Não envie senhas, arquivos do banco de dados ou informações financeiras pessoais.
"""

POLITICA_DE_PRIVACIDADE = """\
# Política de Privacidade do Sino

Última atualização: 30/09/2026

O Sino é um projeto pessoal de portfólio desenvolvido por Carinne Batista. Esta política descreve como a **versão desktop atual** do Sino trata as informações registradas nele. As afirmações sobre o que o Sino guarda, usa e envia se referem ao próprio aplicativo; bibliotecas de terceiros são tratadas no item 7.

## 1. Funcionamento local

O Sino é instalado e usado no computador. As informações de cada instalação ficam nesse computador, e o aplicativo não as envia à desenvolvedora nem a terceiros. A desenvolvedora não recebe, por meio do Sino, os dados registrados em instalações de outras pessoas.

## 2. Quais informações o Sino guarda

*Dados da sua conta de usuário:* nome, e-mail, senha (guardada de forma protegida, veja o item 5), a data em que você aceitou os Termos de Uso e esta Política, e sua preferência de tema (Claro ou Escuro).

*Informações financeiras que você registra:* nome, valor, data de vencimento, situação (paga ou pendente), data de pagamento, categoria, descrição (opcional) e recorrência de cada conta; nome, emoji e cor de cada categoria.

O Sino não coleta outras informações, como localização, contatos, dados bancários ou dados do seu computador.

## 3. Para que essas informações são usadas

Somente para o funcionamento do aplicativo: permitir que você entre na sua conta, mostrar e organizar suas contas, calcular totais, indicar vencimentos e atrasos, exibir gráficos e aplicar o tema escolhido. O Sino não usa suas informações para publicidade.

## 4. Onde as informações ficam

Todas as informações ficam no computador da instalação, em um arquivo de banco de dados (`database/sino.db`) dentro da pasta do Sino. O Sino não envia esse arquivo nem as suas informações para servidores ou nuvem e não sincroniza dados entre dispositivos.

Se mais de uma pessoa usar a mesma instalação do Sino, os dados de todas ficam no mesmo arquivo. Dentro do aplicativo, cada usuário vê apenas as próprias informações.

## 5. Como as informações são protegidas

A senha não é guardada como texto: o Sino guarda apenas um resumo protegido dela (PBKDF2-HMAC-SHA256, com um valor aleatório diferente para cada usuário). Senhas cadastradas em um formato antigo são atualizadas para esse formato quando a pessoa entra no aplicativo.

As **demais informações não são criptografadas** no arquivo. Qualquer pessoa ou programa com acesso a esse arquivo pode conseguir lê-las. Por isso, proteja o acesso ao computador e à pasta do Sino.

Nenhum sistema é totalmente seguro, e o Sino não promete proteção absoluta.

## 6. Cópias de segurança (backups)

Quando uma nova versão do Sino precisa atualizar a estrutura do banco de dados, o aplicativo cria **automaticamente** uma cópia completa do arquivo antes da atualização, na pasta `database/backups/`. Cada cópia contém as informações de **todos os usuários** daquela instalação no momento em que foi feita.

As cópias são **arquivos separados** do banco principal e **não são apagadas pelo aplicativo**. Por isso, uma informação que você alterou ou excluiu no Sino pode continuar existindo em uma cópia anterior.

## 7. Bibliotecas de terceiros e comunicações externas

O Sino não envia suas informações a terceiros e não inclui telemetria nem coleta de estatísticas de uso.

Para exibir as telas, o Sino usa a biblioteca Flet. Na primeira execução em um computador, se o componente de interface da Flet ainda não estiver disponível, a própria biblioteca pode baixá-lo da internet, a partir do GitHub, onde a Flet publica suas versões. Esse download é feito pela biblioteca, não pelo Sino.

A verificação técnica feita para esta política abrangeu o código do Sino e esse comportamento da Flet. As demais partes das bibliotecas de terceiros usadas pelo Sino não foram examinadas por completo.

O aviso sonoro de "limite atingido" usa programas de som do próprio computador. Em caso de erro, detalhes técnicos podem aparecer no terminal do computador; o Sino não os envia para fora.

## 8. O que você pode fazer com suas informações

No aplicativo, você pode ver, editar e excluir suas contas financeiras e categorias, alterar seu nome e escolher o tema.

Nesta versão, **não estão disponíveis**: alterar o e-mail, alterar ou recuperar a senha, e excluir o usuário com todos os seus dados.

Ao excluir um item, ele deixa de aparecer no aplicativo. As cópias de segurança anteriores (item 6) não são alteradas, e o próprio arquivo do banco pode manter vestígios técnicos da informação apagada até que esse espaço seja reutilizado.

## 9. Sair da conta não apaga dados

"Sair da conta" apenas encerra a sessão. Nenhuma informação é removida, e ao entrar novamente tudo continua lá, inclusive o tema escolhido.

## 10. Por quanto tempo as informações ficam guardadas

As informações permanecem no banco de dados enquanto o arquivo `database/sino.db` for mantido. As cópias de segurança permanecem enquanto os seus próprios arquivos em `database/backups/` forem mantidos. Excluir itens no aplicativo não apaga essas cópias.

Desinstalar ou apagar apenas o programa não garante que o banco e os backups sejam removidos. **Atenção:** apagar manualmente `database/sino.db` remove os dados de todos os usuários daquela instalação, não apenas os seus. Os backups são arquivos separados em `database/backups/` e permanecem até serem apagados também. O aplicativo não oferece uma função para desfazer essa remoção.

## 11. Alterações desta política

Esta política pode mudar em versões futuras do Sino. Quando isso acontecer, o texto atualizado ficará disponível dentro do aplicativo e as alterações serão mencionadas nas notas da versão. Nesta versão, não há controle de versões do texto nem novo pedido de aceite.

## 12. Contato

Dúvidas, sugestões e relatos de problemas podem ser enviados para sino.lembrete.contas@gmail.com. Não envie senhas, arquivos do banco de dados ou informações financeiras pessoais.
"""

# Chave -> (rótulo exibido nos itens clicáveis, texto em Markdown).
DOCUMENTOS = {
    "termos": ("Termos de Uso", TERMOS_DE_USO),
    "politica": ("Política de Privacidade", POLITICA_DE_PRIVACIDADE),
}
