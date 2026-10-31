"""
documentos.py — Termos de Uso e Política de Privacidade do Sino (ERS v6.0,
5.37, RF15/RF41), em Markdown.

Texto aprovado pela autora em 30/09/2026; atualização de 02/10/2026
(Etapa 8: códigos por e-mail), rascunho de 03/10/2026 (Etapa 9: excluir
a conta de usuário) e ajustes de 04/10/2026 (Termos item 4 e Política
item 2, pedidos pela autora na leitura). O texto atual foi REVISADO E
APROVADO pela autora em 04/10/2026 para a versão de portfólio e
demonstração local, com apoio de revisão técnica e de clareza. A revisão
jurídica continua PENDENTE e é necessária antes do uso por terceiros.
Versão de 06/10/2026 (ERS v7.0, P38): Termos item 8 e Política itens 2, 3,
8, 10 e 11 passam a descrever as versões e os registros de aceite e de
ciência; texto aprovado pela autora; mudança relevante (novo aceite).
Versão de 13/10/2026 (ERS v7.0, P41; preparação do T2 da E4): Termos itens
1, 2, 4 e 9 e Política itens 1, 2, 7, 8, 10 e 12 passam a descrever o
serviço real de códigos em fase restrita de testes (quem o opera,
Cloudflare, Resend, retenção, transferência internacional e contato); o
envio real ainda não está ativo; texto aprovado pela autora; mudança
relevante (novo aceite).
Versão de 30/10/2026 da Política (Sino 6.10, pagamentos parciais): itens 2,
3, 6, 8 e 10 passam a descrever os registros de pagamento (parciais,
correções e estornos), a exclusão e os backups; Termos inalterados; texto,
resumo e classificação aprovados pela autora; mudança relevante (novo
aceite). Revisão jurídica continua PENDENTE.
É a mesma fonte exibida no cadastro (antes do aceite) e em Ajustes > Sobre e
privacidade. Qualquer mudança de conteúdo deve ser revisada
antes e mencionada nas notas da versão (docs/notas-da-versao.md). O endereço
de contato é apenas informativo: os únicos e-mails ligados ao Sino são os de
código, enviados pelo serviço de códigos (não pelo aplicativo).

ERS v7.0, 5.53 (M12): cada documento tem versões identificadas pela data do
texto (HISTORICO_VERSOES). O texto de cada versão fica guardado em
docs/legal/<documento>_<AAAA-MM-DD>.md; o texto vigente aqui precisa ser
idêntico ao arquivo da versão mais recente (conferido pelos testes). Uma
mudança de conteúdo exige uma nova versão, com a classificação feita pela
autora ("relevante" ou "menor", 5.53; na dúvida, relevante) e o resumo das
mudanças exibido no login.
"""

from datetime import date
from pathlib import Path

TERMOS_DE_USO = """\
# Termos de Uso do Sino

Última atualização: 13/10/2026

O Sino é um projeto pessoal de portfólio desenvolvido por Carinne Batista. Estes termos descrevem a **versão desktop atual** do Sino.

## 1. O que é o Sino

O Sino é um aplicativo para computador que ajuda você a registrar e acompanhar suas contas do dia a dia, como aluguel, internet, assinaturas e parcelas.

O Sino funciona localmente: cada instalação guarda suas informações no próprio computador onde está instalada. O aplicativo não envia essas informações à desenvolvedora nem a outras pessoas, com uma única exceção: a confirmação de e-mail por código (item 4). Quando o serviço real estiver em uso, o endereço de e-mail informado será enviado pela internet ao serviço de códigos, operado pela desenvolvedora, e chegará ao provedor que entrega a mensagem (veja o item 7 da Política de Privacidade). No modo de demonstração, usado em desenvolvimento, esse serviço roda no próprio computador e os dados do fluxo de códigos são tratados localmente, sem envio ao provedor de e-mail.

## 2. Aceite

Ao criar sua conta no Sino, você marca a opção "Li e aceito os Termos de Uso e a Política de Privacidade". Sem esse aceite, a conta não é criada. O Sino guarda a data em que o aceite foi feito e, nas contas criadas a partir da versão de 06/10/2026, a versão aceita (item 8).

## 3. O que o Sino faz e o que ele não faz

O Sino registra as informações financeiras que **você mesmo digita**: nome da conta, valor, data de vencimento, categoria, descrição, recorrência e se a conta foi paga. Com elas, o app mostra totais, lembretes na tela, listas por situação e gráficos.

O Sino **não** faz pagamentos, **não** acessa contas bancárias, cartões ou qualquer instituição financeira, e **não** confere se as informações registradas estão corretas. Marcar uma conta como "paga" no Sino é apenas um registro seu; não quita nenhuma dívida.

Os lembretes aparecem somente dentro do aplicativo, quando ele está aberto. O Sino não envia lembretes ou avisos por e-mail, mensagem ou notificação; os únicos e-mails são os de código descritos no item 4.

O Sino não oferece orientação financeira, contábil ou jurídica.

## 4. Sua conta de usuário

Para usar o Sino, você informa nome, e-mail e senha. Para entrar, o e-mail e a senha são conferidos no próprio computador, sem consultar a internet.

Ao criar uma conta, o Sino usa um código de 6 dígitos para concluir o cadastro. Com o serviço de envio real, esse código confirma acesso à mensagem enviada ao endereço informado; na demonstração, apenas conclui o fluxo local. O mesmo tipo de código é usado para **alterar o e-mail** em Ajustes (com a senha atual) e para **recuperar uma senha esquecida** pela opção "Esqueci minha senha" na tela de entrada. Cada código vale por 10 minutos, aceita até 5 tentativas e só pode ser usado uma vez; um novo código pode ser pedido depois de 60 segundos e invalida o anterior.

Os códigos são gerados, enviados e conferidos por um **serviço de códigos** (veja o item 7 da Política de Privacidade). Por isso, criar conta, alterar o e-mail e recuperar a senha exigem uma instalação configurada com esse serviço; sem ele, o aplicativo informa que a confirmação por e-mail não está disponível e essas três funções não podem ser concluídas. Entrar com uma conta já existente continua funcionando sem o serviço. Para desenvolvimento e apresentação, existe um **modo de demonstração**, em que o serviço roda no próprio computador e os códigos ficam em arquivos locais em vez de irem para a caixa de e-mail.

**Nesta fase, o serviço de códigos é destinado apenas a testes restritos da desenvolvedora.** Só podem receber códigos os endereços de e-mail autorizados por ela; o Sino ainda não está disponível para uso por outras pessoas. Para um endereço fora dessa lista, o cadastro e a alteração de e-mail mostram "O envio de códigos está restrito nesta fase do Sino." e nenhum código é enviado; na recuperação de senha, a resposta é a mesma de sempre e nenhum e-mail é mandado. Quando houver envio real, os e-mails de código serão enviados por `nao-responda@envios.appsino.com.br`, trarão apenas o código, a finalidade, orientações e um contato para ajuda, não trarão o seu nome e nunca pedirão a sua senha.

Com o envio real de e-mails, informar o código recebido demonstra acesso à mensagem enviada àquele endereço; o Sino não verifica a identidade de ninguém. No modo de demonstração, informar o código gravado localmente apenas conclui o fluxo demonstrativo e não comprova acesso ao e-mail. Contas criadas antes dessa confirmação continuam entrando normalmente, mas só uma conta com e-mail confirmado pode recuperar a senha por código. Por segurança, a resposta ao pedido de recuperação não revela se o endereço corresponde a uma conta que pode recuperar a senha. Outras situações podem gerar mensagens diferentes, como limite de pedidos atingido, serviço indisponível ou falha de conexão.

Toda nova senha precisa ter **pelo menos 8 caracteres** e não pode conter espaços. Senhas criadas antes dessa regra continuam permitindo a entrada no aplicativo.

Em Ajustes, você pode alterar sua senha informando a senha atual e confirmando a nova, que precisa ser diferente da atual. Na recuperação, a nova senha também precisa ser diferente da atual. Guarde sua senha com cuidado.

Em Ajustes, você também pode alterar seu nome, escolher o tema (Claro ou Escuro) e excluir sua conta de usuário (item 6).

## 5. Seus cuidados

Ao usar o Sino, é importante:

* conferir as informações que você registra antes de tomar decisões com base nelas;
* proteger o acesso ao computador e à pasta do Sino;
* manter suas próprias cópias de segurança, se desejar, já que o Sino não as cria de forma periódica.

## 6. Sair da conta e excluir a conta

"Sair da conta" apenas encerra a sessão e volta à tela de entrada. Suas contas, categorias e preferências continuam guardadas e reaparecem quando você entrar novamente.

Excluir uma conta financeira ou uma categoria remove esse item do aplicativo.

Em Ajustes, a opção **Excluir conta** apaga a sua conta de usuário. Antes, o Sino mostra quantas contas, séries recorrentes e categorias serão apagadas, pede a senha atual e uma confirmação final. Confirmada, a exclusão apaga do banco de dados atual do Sino a sua conta de usuário e todos os dados ligados a ela, encerra a sessão e **não pode ser desfeita** pelo aplicativo. Depois disso, o mesmo e-mail só volta a ser usado com um novo cadastro, confirmado por código.

A exclusão **não apaga** as cópias de segurança (backups) já existentes nem informações guardadas fora do banco de dados atual. Veja os itens 6, 8 e 10 da Política de Privacidade.

## 7. Limitações conhecidas

O Sino pode conter erros. Nenhum sistema é totalmente seguro, e o Sino não promete proteção absoluta das informações.

## 8. Alterações destes termos

Estes termos podem mudar em versões futuras do Sino. Cada versão é identificada pela data, que aparece no aplicativo ("Versão de dd/mm/aaaa"), e as alterações são mencionadas nas notas da versão. O Sino registra qual versão destes termos foi aceita no cadastro. Quando uma mudança for relevante, como nos dados tratados, nas finalidades, no compartilhamento ou nos seus direitos, o Sino pede um novo aceite no próximo login, e sem ele não é possível entrar. Ajustes menores, como correções de redação, são informados por um aviso, sem bloquear o acesso. Os registros guardados estão descritos na Política de Privacidade.

## 9. Contato

Dúvidas, sugestões, relatos de problemas e pedidos sobre dados pessoais podem ser enviados para sino.lembrete.contas@gmail.com (veja também o item 12 da Política de Privacidade). Quando houver envio real, as respostas aos e-mails de código também chegarão a esse endereço. Não envie senhas, códigos, arquivos do banco de dados ou informações financeiras pessoais.
"""

POLITICA_DE_PRIVACIDADE = """\
# Política de Privacidade do Sino

Última atualização: 30/10/2026

O Sino é um projeto pessoal de portfólio desenvolvido por Carinne Batista. Esta política descreve como a **versão desktop atual** do Sino trata as informações registradas nele. As afirmações sobre o que o Sino guarda, usa e envia se referem ao próprio aplicativo; o serviço de códigos, os provedores que ele usa e as bibliotecas de terceiros são tratados no item 7.

## 1. Funcionamento local

O Sino é instalado e usado no computador. As informações de cada instalação ficam nesse computador, e o aplicativo não as envia à desenvolvedora nem a terceiros. A desenvolvedora não recebe, por meio do Sino, os dados registrados em instalações de outras pessoas, exceto o que passa pelo serviço de códigos (item 7).

A única função que conversa com um serviço fora do aplicativo é a **confirmação por código** (criar conta, alterar o e-mail e recuperar a senha). Quando o serviço real estiver em uso, o endereço de e-mail e alguns dados técnicos serão enviados pela internet ao serviço de códigos, operado pela desenvolvedora, e o endereço e a mensagem com o código chegarão ao provedor que entrega o e-mail (item 7). No modo de demonstração, o serviço roda no próprio computador e os dados do fluxo de códigos são tratados localmente, sem envio ao provedor de e-mail. Nome, senha e informações financeiras não são enviados em nenhum dos casos.

## 2. Quais informações o Sino guarda

*Dados da sua conta de usuário:* nome, e-mail, se o e-mail foi confirmado por código, senha (guardada de forma protegida, veja o item 5), a data em que você aceitou os Termos de Uso e esta Política, e sua preferência de tema (Claro ou Escuro).

*Registros de aceite e de ciência dos documentos:* nas contas criadas a partir da versão de 06/10/2026, o Sino guarda qual versão dos Termos de Uso e desta Política foi aceita no cadastro, com a data e a hora. Quando um desses documentos receber uma mudança relevante e você aceitar a nova versão, o Sino guarda a versão aceita, com a data e a hora. Quando um documento receber um ajuste menor e você clicar em "Entendi" no aviso, o Sino guarda a versão avisada, com a data e a hora, como **registro de ciência**: esse registro mostra que o aviso foi visto e **não** equivale a um aceite. Nas contas criadas antes da versão de 06/10/2026, o aceite original permanece registrado apenas pela data, sem versão identificada. Novos aceites e registros de ciência passam a ser guardados conforme as regras descritas acima.

*Registro técnico das confirmações por código:* para que a mesma confirmação não seja usada duas vezes, o Sino guarda um identificador aleatório de cada confirmação usada, a finalidade (cadastro, alteração de e-mail ou recuperação de senha) e até quando ela valeria. Esse registro não contém e-mail, nome nem senha, e os itens vencidos são apagados nas confirmações seguintes. Como não está ligado a nenhum usuário, ele não é apagado na exclusão da conta de usuário (item 8).

*Informações financeiras que você registra:* nome, valor, data de vencimento, situação (paga ou pendente), data de pagamento, categoria, descrição (opcional) e recorrência de cada conta; nome, emoji e cor de cada categoria.

*Registros de pagamento:* a partir da versão 6.10, cada pagamento registrado em uma conta fica guardado como um registro próprio, ligado a essa conta, com o valor, a data do pagamento, o tipo (pagamento parcial, pagamento do saldo que faltava ou pagamento integral) e a data e a hora em que foi registrado. Quando um pagamento é desfeito, o registro não é apagado: ele recebe a data em que foi desfeito (**estorno**), continua aparecendo no histórico de pagamentos da conta e deixa de contar no total pago. Corrigir o valor ou a data de um pagamento altera o próprio registro, sem guardar os valores anteriores. A situação da conta (paga ou pendente) e a data de pagamento continuam guardadas na conta e passam a acompanhar os pagamentos registrados. Contas marcadas como pagas antes da versão 6.10 continuam com a situação e a data de pagamento de antes, sem que a atualização crie registros de pagamento para elas.

Além dessas, o Sino não coleta outras informações: não pede a localização do dispositivo nem coleta contatos, dados bancários ou dados do seu computador. A exceção é a confirmação por código: ao usá-la, o serviço de códigos recebe dados técnicos do pedido, como o endereço IP de onde ele parte e identificadores gerados na hora. O endereço IP pode permitir inferir uma localização geográfica aproximada, como a cidade ou a região. O serviço usa o endereço IP apenas para limitar abusos: guarda um resumo calculado a partir dele, não guarda o IP completo em texto no armazenamento do serviço de códigos e não o usa para determinar a localização geográfica. O que é enviado, o que o serviço guarda e por quanto tempo estão descritos no item 7.

## 3. Para que essas informações são usadas

Somente para o funcionamento do aplicativo: permitir que você entre na sua conta, confirmar o e-mail por código (cadastro, alteração de e-mail e recuperação de senha), mostrar e organizar suas contas, mostrar o histórico de pagamentos de cada conta, calcular totais, o total pago e o saldo que falta pagar, indicar vencimentos e atrasos, exibir gráficos e aplicar o tema escolhido. O Sino não usa suas informações para publicidade. Os registros de aceite e de ciência dos documentos servem para saber quais versões dos Termos de Uso e desta Política cada usuário aceitou ou viu, e assim decidir quando pedir um novo aceite ou mostrar um aviso.

## 4. Onde as informações ficam

As informações descritas no item 2 ficam no computador da instalação, em um arquivo de banco de dados (`database/sino.db`) dentro da pasta do Sino. O Sino não envia esse arquivo para servidores ou nuvem e não sincroniza dados entre dispositivos. O que é enviado ao serviço de códigos está descrito no item 7.

Se mais de uma pessoa usar a mesma instalação do Sino, os dados de todas ficam no mesmo arquivo. Dentro do aplicativo, cada usuário vê apenas as próprias informações.

## 5. Como as informações são protegidas

A senha não é guardada como texto: o Sino guarda apenas um resumo protegido dela (PBKDF2-HMAC-SHA256, com um valor aleatório diferente para cada usuário). Senhas cadastradas em um formato antigo são atualizadas para esse formato quando a pessoa entra no aplicativo.

As **demais informações não são criptografadas** no arquivo. Qualquer pessoa ou programa com acesso a esse arquivo pode conseguir lê-las. Por isso, proteja o acesso ao computador e à pasta do Sino.

Nenhum sistema é totalmente seguro, e o Sino não promete proteção absoluta.

## 6. Cópias de segurança (backups)

Quando uma nova versão do Sino precisa atualizar a estrutura do banco de dados, o aplicativo cria **automaticamente** uma cópia completa do arquivo antes da atualização, na pasta `database/backups/`. Cada cópia contém as informações de **todos os usuários** daquela instalação no momento em que foi feita.

As cópias são **arquivos separados** do banco principal e **não são apagadas pelo aplicativo**. Por isso, uma informação que você alterou ou excluiu no Sino pode continuar existindo em uma cópia anterior. Isso vale também para os registros de pagamento: um pagamento corrigido, estornado ou excluído pode continuar, como estava, em uma cópia feita antes dessa mudança. A cópia criada ao atualizar o banco para a versão 6.10 é anterior aos registros de pagamento e não os contém.

## 7. Serviço de códigos, bibliotecas de terceiros e comunicações externas

*Serviço de códigos por e-mail.* Quando você cria uma conta, altera o e-mail ou pede a recuperação da senha, o Sino envia ao serviço de códigos o endereço de e-mail informado, a finalidade do pedido e identificadores técnicos gerados na hora; para conferir o código, envia também o código que você digitou. Fora do próprio computador, a conexão com o serviço usa HTTPS. Como em qualquer conexão pela internet, o serviço recebe o endereço IP de onde o pedido veio. O Sino não envia nome, senha, informações financeiras nem o arquivo do banco.

No envio real, o serviço gera o código e o envia ao endereço informado por meio de um provedor de envio de e-mails, a **Resend**. O pedido de envio à Resend parte do serviço, não diretamente do seu computador. O provedor recebe o endereço e a mensagem com o código de forma legível, porque precisa entregá-la. O serviço não conhece as contas do Sino: na recuperação de senha, quando não há uma conta com e-mail confirmado naquele endereço, o pedido é enviado do mesmo jeito, mas nenhum e-mail é mandado.

O que o serviço guarda, pela implementação atual:

* **e-mail, endereço IP e código:** não são guardados como texto. O serviço guarda resumos de mão única (HMAC-SHA256) calculados com uma chave secreta dele, que permitem comparar valores sem guardá-los. Isso não é criptografia reversível: o serviço não recupera o texto a partir do resumo. Do IP, entra no resumo o endereço IPv4 completo ou o início (/64) do endereço IPv6;
* **identificadores técnicos:** o segredo e as chaves de cada pedido também ficam só como resumo; o identificador de vínculo enviado pelo aplicativo já chega como resumo (SHA-256) e é guardado como recebido; o identificador da confirmação emitida fica legível. Nenhum deles contém o e-mail em texto;
* **legíveis:** a finalidade do pedido, horários, número de tentativas, situação do envio, resultado de cada tentativa e contadores usados para limitar abusos;
* **prazos:** os pedidos encerrados são apagados 24 horas depois do encerramento, os contadores por hora em 2 horas, os contadores diários por e-mail e por conexão em 48 horas, e os totais diários gerais (sem e-mail nem IP) em 35 dias. Veja abaixo o que a plataforma de hospedagem pode manter depois disso;
* **registros de funcionamento:** o serviço não registra códigos, e-mails nem o conteúdo das mensagens.

**O que se segue descreve o funcionamento do serviço real de códigos, planejado para a fase restrita de testes, e vale quando ele estiver em uso.**

*Quem opera o serviço.* O serviço de códigos é operado por Carinne Batista, desenvolvedora do Sino, que define como ele funciona e quais dados ele trata. Dúvidas e pedidos sobre esses dados podem ser enviados ao contato do item 12.

*Fase restrita de testes.* Nesta fase, o serviço real é destinado apenas a testes restritos da desenvolvedora: só poderão receber códigos os endereços de e-mail autorizados por ela (item 4 dos Termos de Uso). A lista de endereços autorizados também é guardada só como resumo (HMAC-SHA256), sem os endereços em texto. Pedidos para outros endereços são recusados ou respondidos de forma neutra, sem envio de e-mail, mas o serviço e a hospedagem recebem e tratam os dados desses pedidos como descrito neste item.

*Hospedagem: Cloudflare.* O serviço roda na plataforma Cloudflare Workers, da empresa norte-americana Cloudflare, e guarda os dados descritos acima no armazenamento da própria plataforma (Durable Objects). Segundo a documentação da Cloudflare, esse armazenamento fica em um centro de dados escolhido pela plataforma, sem garantia de país; por isso, esses dados podem ficar fora do Brasil. A plataforma também oferece um recurso que permite restaurar esse armazenamento a um momento dos últimos 30 dias; por isso, dados que o serviço já apagou nos prazos acima podem continuar recuperáveis pela plataforma dentro dessa janela. Na configuração prevista para o serviço, os registros de funcionamento e de rastreamento da plataforma (Workers Logs e Traces) ficam desligados. Isso não impede que a Cloudflare, como em qualquer conexão que passa pela sua rede, receba o endereço IP e dados técnicos de cada pedido e os trate conforme a própria política de privacidade. Essa política não informa um prazo específico para esses dados e diz que a Cloudflare guarda informações principalmente nos Estados Unidos e na Europa e pode acessá-las de qualquer parte do mundo.

*Envio: Resend.* Os e-mails são enviados pela Resend, empresa norte-americana, a partir do domínio `envios.appsino.com.br`, pelo remetente `nao-responda@envios.appsino.com.br`; as respostas a eles chegam ao contato do item 12. O serviço deve operar sem rastreamento de abertura e de cliques: cada e-mail é só texto, sem links nem imagens, e o rastreamento fica desativado na configuração do domínio de envio, que é conferida novamente antes do primeiro envio real. Os e-mails saem pela região de envio de São Paulo, mas essa escolha define apenas de onde as mensagens partem: segundo a Resend, os dados da conta, inclusive o conteúdo das mensagens e os registros de entrega, ficam guardados nos **Estados Unidos**, qualquer que seja a região de envio. A Resend informa que guarda os dados de cada e-mail enviado (endereço, conteúdo com o código, situação da entrega e registros) por **30 dias** no plano usado e que mantém cópias de segurança por **7 dias**; ela não detalha como esses dois prazos se combinam. A remoção de uma mensagem antes do fim do prazo depende de pedido feito à Resend. Durante esse período, pessoas com acesso autorizado à conta da desenvolvedora na Resend podem ver no painel o endereço, o assunto e o conteúdo dos e-mails enviados, inclusive os códigos. A Resend também informa que uma pequena amostra de e-mails pode ser analisada para segurança e prevenção de abuso. Para prestar o serviço, ela usa outras empresas (suboperadores), cujos nomes, finalidades e localizações constam da lista oficial publicada pela Resend em https://resend.com/legal/subprocessors. O código perde a validade em 10 minutos, bem antes desses prazos.

*Transferência internacional.* Por causa desses provedores, o endereço de e-mail, a mensagem com o código, o endereço IP e os dados técnicos dos pedidos são tratados fora do Brasil, inclusive nos Estados Unidos.

*Modo de demonstração (desenvolvimento).* Nele, o serviço de códigos e uma caixa de mensagens rodam no próprio computador, e os dados do fluxo de códigos são tratados localmente, sem envio ao provedor de e-mail. Cada mensagem (endereço, assunto e código) é gravada como **texto legível** em um arquivo com acesso restrito ao usuário do computador que executa a demonstração, em uma pasta própria fora do aplicativo; as chaves da demonstração ficam na mesma pasta, também com acesso restrito. Esses arquivos ficam lá até serem apagados manualmente. Informar o código gravado localmente apenas conclui o fluxo demonstrativo: a conta aparece como verificada no banco da demonstração, mas isso não comprova acesso ao endereço informado.

*Outras comunicações.* Fora o serviço de códigos, o Sino não envia suas informações a terceiros e não inclui telemetria nem coleta de estatísticas de uso.

Para exibir as telas, o Sino usa a biblioteca Flet. Na primeira execução em um computador, se o componente de interface da Flet ainda não estiver disponível, a própria biblioteca pode baixá-lo da internet, a partir do GitHub, onde a Flet publica suas versões. Esse download é feito pela biblioteca, não pelo Sino.

A verificação técnica feita para esta política abrangeu o código do Sino e esse comportamento da Flet. As demais partes das bibliotecas de terceiros usadas pelo Sino não foram examinadas por completo.

O aviso sonoro de "limite atingido" usa programas de som do próprio computador. Em caso de erro, detalhes técnicos podem aparecer no terminal do computador; o Sino não os envia para fora.

## 8. O que você pode fazer com suas informações

No aplicativo, você pode ver, editar e excluir suas contas financeiras e categorias, alterar seu nome e sua senha e escolher o tema.

*Pagamentos registrados.* Nos Detalhes de uma conta, você pode registrar pagamentos, corrigir o valor e a data de um pagamento e desfazê-lo (estorno). Um registro estornado pode ser excluído definitivamente. Excluir uma conta financeira, ou as ocorrências de uma recorrência, apaga também todos os registros de pagamento dessas contas, inclusive os estornados.

Com o serviço de códigos disponível (item 7), você também pode alterar o e-mail e recuperar uma senha esquecida.

*Excluir a conta de usuário.* Em Ajustes > Excluir conta, depois de informar a senha atual e confirmar, você pode excluir sua conta de usuário. A exclusão apaga do banco de dados atual (`database/sino.db`), em uma única operação, os dados da sua conta de usuário (nome, e-mail e sua confirmação, senha protegida, data do aceite, registros de aceite e de ciência dos documentos e tema), suas contas financeiras, os registros de pagamento delas (inclusive os estornados), séries recorrentes e categorias. Se algo falhar no meio, nada é apagado. Os dados dos outros usuários da mesma instalação não são alterados.

A exclusão da conta de usuário **não alcança**:

* as cópias de segurança já existentes em `database/backups/` (item 6), que continuam contendo seus dados até serem apagadas manualmente;
* o registro técnico das confirmações por código (item 2), que não identifica usuários;
* o que o serviço de códigos e o provedor de envio já receberam ou guardaram (item 7), que segue os prazos e o tratamento de cada um; o Sino não pede a esses serviços que apaguem nada;
* cópias feitas fora do aplicativo, como cópias da pasta do Sino, backups do computador ou arquivos do modo de demonstração.

*Dados do serviço de códigos.* Dúvidas e pedidos sobre os dados tratados pelo serviço de códigos e pelos provedores (item 7) podem ser enviados ao contato do item 12.

*Vestígios técnicos.* Ao excluir um item ou a conta de usuário, os dados deixam de aparecer no aplicativo. Na exclusão da conta de usuário, o Sino pede ao banco de dados que sobrescreva o espaço liberado no arquivo. Essa é uma medida adicional: não garante que a informação não possa ser recuperada por outros meios, como cópias, arquivos temporários do banco de dados ou recursos do sistema e do dispositivo de armazenamento. Nas demais exclusões, o próprio arquivo do banco pode manter vestígios técnicos da informação apagada até que esse espaço seja reutilizado.

## 9. Sair da conta não apaga dados

"Sair da conta" apenas encerra a sessão. Nenhuma informação é removida, e ao entrar novamente tudo continua lá, inclusive o tema escolhido.

## 10. Por quanto tempo as informações ficam guardadas

As informações permanecem no banco de dados enquanto o arquivo `database/sino.db` for mantido, até serem excluídas no aplicativo (item 8). Os registros de pagamento, inclusive os estornados, ficam guardados enquanto a conta financeira a que pertencem existir, até serem excluídos no aplicativo (item 8). Os registros de aceite e de ciência dos documentos ficam guardados enquanto a sua conta de usuário existir e são apagados na exclusão da conta. Eles podem continuar existindo nas cópias de segurança já feitas antes da exclusão (item 6), que o aplicativo não apaga. As cópias de segurança permanecem enquanto os seus próprios arquivos em `database/backups/` forem mantidos. Excluir itens ou a conta de usuário no aplicativo não apaga essas cópias. Os prazos do serviço de códigos e dos provedores estão no item 7.

Desinstalar ou apagar apenas o programa não garante que o banco e os backups sejam removidos. **Atenção:** apagar manualmente `database/sino.db` remove os dados de todos os usuários daquela instalação, não apenas os seus. Os backups são arquivos separados em `database/backups/` e permanecem até serem apagados também. O aplicativo não oferece uma função para desfazer essa remoção.

## 11. Alterações desta política

Esta política pode mudar em versões futuras do Sino. Cada versão é identificada pela data, que aparece no aplicativo ("Versão de dd/mm/aaaa"), e as alterações são mencionadas nas notas da versão. Quando uma mudança for relevante, o Sino pede um novo aceite no próximo login, e sem ele não é possível entrar. Ajustes menores são informados por um aviso, sem bloquear o acesso. Os registros guardados são os do item 2.

## 12. Contato

Dúvidas, sugestões, relatos de problemas e pedidos sobre dados pessoais podem ser enviados para sino.lembrete.contas@gmail.com, endereço acompanhado pela desenvolvedora, que opera o serviço de códigos (item 7). Quando houver envio real, as respostas aos e-mails de código também chegarão a esse endereço. Esse endereço é uma conta do Gmail: as mensagens enviadas a ele são tratadas pelo Google, conforme as políticas do Google. Não envie senhas, códigos, arquivos do banco de dados ou informações financeiras pessoais.
"""

# Chave -> (rótulo exibido nos itens clicáveis, texto em Markdown).
DOCUMENTOS = {
    "termos": ("Termos de Uso", TERMOS_DE_USO),
    "politica": ("Política de Privacidade", POLITICA_DE_PRIVACIDADE),
}

# ------------------------------------------------------------------
#  Versões (ERS v7.0, 5.53)
# ------------------------------------------------------------------
# Nome do arquivo histórico de cada documento em docs/legal/.
ARQUIVOS_HISTORICOS = {"termos": "termos-de-uso", "politica": "politica-de-privacidade"}
PASTA_HISTORICO = Path(__file__).resolve().parent.parent / "docs" / "legal"

# Classificações (5.53): "inicial" (primeira versão registrada: não pede
# novo aceite de quem aceitou antes do versionamento), "relevante" (novo
# aceite obrigatório no próximo login) e "menor" (aviso, sem bloquear).
CLASSIFICACOES = ("inicial", "relevante", "menor")

# Versões de cada documento, da mais antiga para a vigente. "resumo" é o
# texto mostrado no login (obrigatório em "relevante" e "menor"); "motivo"
# registra a classificação feita pela autora.
HISTORICO_VERSOES = {
    "termos": (
        {"versao": "2026-10-04", "classificacao": "inicial", "resumo": None,
         "motivo": "Primeira versão registrada: texto aprovado pela autora em 04/10/2026, "
                   "mantido com a mesma data e o mesmo conteúdo."},
        {"versao": "2026-10-06", "classificacao": "relevante",
         "resumo": "O item 8 passa a explicar que cada versão é identificada pela data, que o Sino "
                   "registra a versão aceita no cadastro e como funcionam o novo aceite e o aviso.",
         "motivo": "Introduz registros de dados antes não descritos (regra 5.53); texto e "
                   "classificação aprovados pela autora em 06/10/2026 (P38)."},
        {"versao": "2026-10-13", "classificacao": "relevante",
         "resumo": "Os itens 1, 2, 4 e 9 passam a descrever o serviço real de códigos por e-mail, "
                   "destinado nesta fase a testes restritos: quem pode receber códigos, o remetente "
                   "dos e-mails, o registro da versão aceita e o contato.",
         "motivo": "Muda o compartilhamento com provedores, a retenção, a localização e a transferência "
                   "internacional dos dados e identifica quem opera o serviço (regra 5.53); texto e "
                   "classificação aprovados pela autora em 13/10/2026 (P41)."},
    ),
    "politica": (
        {"versao": "2026-10-04", "classificacao": "inicial", "resumo": None,
         "motivo": "Primeira versão registrada: texto aprovado pela autora em 04/10/2026, "
                   "mantido com a mesma data e o mesmo conteúdo."},
        {"versao": "2026-10-06", "classificacao": "relevante",
         "resumo": "Os itens 2, 3, 8, 10 e 11 passam a descrever os registros de aceite e de ciência "
                   "dos documentos, para que servem e quando são apagados.",
         "motivo": "Introduz registros de dados antes não descritos (regra 5.53); texto e "
                   "classificação aprovados pela autora em 06/10/2026 (P38)."},
        {"versao": "2026-10-13", "classificacao": "relevante",
         "resumo": "Os itens 1, 2, 7, 8, 10 e 12 passam a descrever o serviço de códigos em fase "
                   "restrita: quem o opera, a hospedagem na Cloudflare, o envio pela Resend (dados nos "
                   "Estados Unidos, guardados por 30 dias), a transferência internacional e o contato "
                   "para pedidos sobre dados.",
         "motivo": "Muda o compartilhamento com provedores, a retenção, a localização e a transferência "
                   "internacional dos dados e identifica quem opera o serviço (regra 5.53); texto e "
                   "classificação aprovados pela autora em 13/10/2026 (P41)."},
        {"versao": "2026-10-30", "classificacao": "relevante",
         "resumo": "Atualizamos a Política de Privacidade para explicar como o Sino registra e armazena "
                   "pagamentos individuais, incluindo pagamentos parciais, correções e estornos, e como "
                   "esses dados são tratados em exclusões e backups.",
         "motivo": "Descreve dados tratados de forma nova pelos pagamentos parciais da Sino 6.10 (registros "
                   "individuais de pagamento, correções e estornos), itens 2, 3, 6, 8 e 10 (regra 5.53); "
                   "texto, resumo e classificação aprovados pela autora em 30/10/2026."},
    ),
}


def versao_atual(chave):
    """Registro da versão vigente do documento (o último do histórico)."""
    return HISTORICO_VERSOES[chave][-1]


def versoes_atuais():
    """{documento: "AAAA-MM-DD"} das versões vigentes, para gravar o aceite."""
    return {chave: versao_atual(chave)["versao"] for chave in HISTORICO_VERSOES}


def rotulo_versao(versao):
    """ "2026-10-04" -> "Versão de 04/10/2026" (5.53)."""
    return f"Versão de {date.fromisoformat(versao).strftime('%d/%m/%Y')}"


def caminho_historico(chave, versao):
    return PASTA_HISTORICO / f"{ARQUIVOS_HISTORICOS[chave]}_{versao}.md"


def _versao_minima_exigida(chave):
    """Última versão "relevante" do documento, ou None se não houver."""
    relevantes = [v["versao"] for v in HISTORICO_VERSOES[chave] if v["classificacao"] == "relevante"]
    return relevantes[-1] if relevantes else None


def _mudancas_desde(chave, base):
    """Versões posteriores a `base` (None = desde a primeira), em ordem."""
    return [v for v in HISTORICO_VERSOES[chave] if base is None or v["versao"] > base]


def pendencias(registros):
    """
    5.53: o que pedir no login, a partir de `registros` (formato de
    database.registros_de_documentos). Devolve {"aceite": [...], "aviso": [...]},
    cada item {"documento", "rotulo", "versao", "mudancas": [registros do
    histórico depois do que o usuário já tinha aceitado ou lido]}.

      * "aceite": existe uma versão relevante posterior ao último aceite do
        usuário. Quem aceitou antes do versionamento (sem registro) tem como
        base a versão inicial: não precisa aceitar de novo só por causa dela;
      * "aviso": sem aceite pendente, a versão vigente é um ajuste menor que o
        usuário ainda não aceitou nem leu.
    """
    resultado = {"aceite": [], "aviso": []}
    for chave, versoes in HISTORICO_VERSOES.items():
        inicial = versoes[0]["versao"]
        aceitas = registros.get(chave, {}).get("aceite", [])
        vistas = aceitas + registros.get(chave, {}).get("ciencia", [])
        ultima_aceita = max(aceitas, default=inicial)
        ultima_vista = max(vistas, default=inicial)
        atual = versoes[-1]
        minima = _versao_minima_exigida(chave)
        item = {"documento": chave, "rotulo": DOCUMENTOS[chave][0], "versao": atual["versao"]}
        if minima is not None and ultima_aceita < minima:
            resultado["aceite"].append({**item, "mudancas": _mudancas_desde(chave, ultima_aceita)})
        elif atual["classificacao"] == "menor" and ultima_vista < atual["versao"]:
            resultado["aviso"].append({**item, "mudancas": _mudancas_desde(chave, ultima_vista)})
    return resultado
