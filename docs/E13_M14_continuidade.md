# E13/M14 — Avaliação das plataformas: registro de continuidade

**Situação:** **E13/M14 — Suspensa temporariamente em 24/10/2026, por decisão da responsável pelo projeto.**
**Referência:** Sino 6.9, commit `0b7739c61c6d235627776d60f70931a210ce7b38` (`main` = `origin/main` na data do registro).
**Documentos relacionados:** [ERS v7.0](ERS_Controle_de_Contas_v7.0.md) (2.2, 2.3, 5.49, 11.2, 11.3, 13.4, 15.1, 15.3) e [propostas, M14](ERS_v7.0_propostas.md#m14--disponibilização-para-outras-pessoas-desktop-eou-mobile-06102026).

A suspensão **não** é cancelamento nem conclusão técnica da etapa. Este documento preserva os diagnósticos feitos em 24/10/2026, as decisões tomadas, as alternativas, os riscos e as pendências, para que a E13 possa ser retomada sem repetir toda a investigação. A retomada depende de **nova autorização** da autora.

---

## 1. Estado na data da suspensão

* Diagnósticos realizados (somente leitura): estado do projeto, compatibilidade com Android, segurança da biblioteca `cryptography` e planejamento do ambiente de compilação.
* Decisões parciais preservadas (seção 4).
* **Nenhum APK gerado.**
* **Nenhuma implementação Android** realizada; nenhum código, teste, banco, backup ou texto legal alterado.
* **Nenhuma ferramenta instalada** (Flutter, JDK, Android SDK, `flet-cli`) e nenhum comando do Flet executado.
* **Nenhuma alteração nas dependências do Sino** (`requirements.txt` inalterado).
* **Nenhum gasto autorizado** ou realizado.
* Serviço de códigos inalterado: produção restrita, com a lista de destinatários atual; nenhuma ampliação autorizada.

## 2. Escopo: experimento pessoal × piloto com terceiros

* **Foco escolhido em 24/10/2026:** avaliar a instalação do Sino num celular Android **pessoal da autora**, por arquivo APK, **sem** publicação na Google Play Store.
* **D1:** o APK pessoal é um **experimento separado** do futuro piloto com terceiros. Ele **não** antecipa a E15 nem substitui as condições da seção 11.3 da ERS (decisões da M14, textos revistos com novo aceite, lista de destinatários ampliada explicitamente).
* O funcionamento atual do Sino no Ubuntu deve ser **preservado**.
* A sincronização entre computador e celular é um **objetivo futuro** (seção 9), fora da implementação inicial.

## 3. Legenda das conclusões

* **[P] Comprovado no projeto:** conferido no código, no ambiente virtual (`.venv`) ou no sistema, por leitura.
* **[F] Documentação oficial:** fonte oficial consultada em 24/10/2026 (links na seção 11). Pode mudar; reconferir na retomada.
* **[T] Hipótese:** depende de teste ou de confirmação ainda não feita.

## 4. Decisões

### 4.1 Aprovadas (24/10/2026)

| Decisão | Conteúdo |
|---|---|
| **D1** | APK Android pessoal como experimento separado do piloto com terceiros |
| **D2** | Consultas de **leitura** às fontes oficiais do Flet, do Android Developers e dos repositórios oficiais das dependências |
| **D3** | Ambiente de compilação **local isolado no Ubuntu** (alternativa A), aprovado **somente para planejamento**; nenhuma instalação autorizada |

Comparação que fundamentou a D3:

| | A. Local isolado no Ubuntu (aprovada) | B. CI na nuvem (GitHub Actions) | C. Local em contêiner |
|---|---|---|---|
| Custo | Nenhum | Gratuito em repositório público com executores padrão [F] | Nenhum |
| Efeito no sistema | Vários GB em `$HOME` (Flutter, JDK, Android SDK, caches do Gradle e do pip) | Nada local | Imagens e volumes do Docker |
| Git | Sem mudança | Exige commit e push de um workflow | Sem mudança |
| Keystore | Só na máquina | Segredo no GitHub (serviço externo) | Na máquina |
| Exposição do APK | Nenhuma | Artefatos acessíveis em repositório público | Nenhuma |
| Motivo | Mais simples e documentada | Rejeitada: push, exposição dos artefatos e segredo externo | Sem guia oficial do Flet; mais complexa |

### 4.2 Pendentes (não aprovadas)

Ordem sugerida para a retomada:

1. **D5 — `cryptography` 48.0.0 exclusivamente no APK**, mantendo a 50.0.2 no desktop (recomendação técnica; seção 5.4).
2. **Python 3.14 embarcado** (consequência da D5) e **listas de dependências separadas** para desktop e Android, com `regex` 2026.5.9 no APK.
3. **Isolamento do serviço de produção** no experimento (opções i, ii e iii, seção 5.8).
4. **APK mínimo experimental** antes de adaptar o Sino.
5. **Armazenamento do SQLite no Android** (`FLET_APP_STORAGE_DATA`; Ubuntu inalterado).
6. **Política de Auto Backup** (desligar ou não; regras de transferência entre aparelhos).
7. **Assinatura e preservação da keystore** (quando criar, onde guardar, cópia de recuperação).
8. **Compatibilidade de interface, gráficos e acessibilidade** (adaptações B e C, seção 6).
9. **Revisão dos documentos legais** para o Android (Termos e Política descrevem o computador).
10. **Critérios para uso futuro com dados reais.**
11. Autorização específica para executar a suíte de testes em Python 3.14, num ambiente virtual separado.

Continuam abertas também as decisões da M14 para o piloto com terceiros (tabela da M14 nas propostas: público, plataformas, empacotamento, instalação, atualizações, dados, backup, lojas, custos, segurança, privacidade, revisão jurídica, suporte, serviço de códigos, avisos de terceiros) e os pontos de consistência da seção 8.

## 5. Diagnósticos técnicos

### 5.1 Viabilidade do APK com Flet 0.86.5

* **Conclusão:** viável em princípio, **não comprovado** por build.
* [P] Versões do projeto: Python 3.11.0 (pyenv), `flet`, `flet-desktop` e `flet-charts` 0.86.5, `regex` 2026.9.10, `httpx` 0.28.1, `cryptography` 50.0.2, `cffi` 2.1.1, `certifi` 2026.7.22.
* [F] `flet-cli` 0.86.5 existe no PyPI (publicado em 01/08/2026). A 0.86.0 (14/07/2026) redesenhou o empacotamento Android. A versão estável mais recente do `flet-cli` no PyPI em 24/10/2026 é a 1.0.5; não é preciso migrar para gerar APK.
* [P] O Flet 0.86.5 instalado fixa o **Flutter 3.44.8** (`flet/version.py`).
* [P] **Atenção:** o comando `flet` instalado é só um intermediário que **instala automaticamente o `flet-cli` via pip** no ambiente em uso (`flet/cli.py`, `flet/utils/pip.py`). Nenhum comando `flet …` deve rodar no `.venv` do desktop.
* [F] A documentação publicada é a da versão atual, sem separação por versão; as notas da 0.86 confirmam o que vale para a 0.86.5.
* [T] Número de versão do APK (`versionCode`) não encontrado na documentação.

### 5.2 Requisitos do ambiente de compilação

* [F] JDK 17 e Android SDK **instalados automaticamente** na primeira execução de `flet build` (JDK em `$HOME/java/<versão>`; SDK do Android Studio reaproveitado, se houver; `ANDROID_HOME` e `ANDROID_SDK_ROOT` respeitados).
* [F] Flutter baixado automaticamente para `$HOME/flutter/<versão>` se não estiver no `PATH`. O Flet 0.86 usa Java 17 e Gradle 8.14.
* [F] O exemplo oficial de CI gera APK em `ubuntu-latest` (host Linux serve).
* [P] Situação da máquina em 24/10/2026: Java do sistema é o OpenJDK 8 (insuficiente, mas o Flet instala o 17 à parte); Flutter, Android SDK, `adb`, `sdkmanager`, `javac` e Rust ausentes; Docker presente.
* [T] Se o `adb` vem com o SDK instalado pelo Flet; quais pacotes e licenças do SDK são aceitos.
* **Consequência:** a alternativa A não fica contida numa pasta: deixa vários GB em `$HOME`, a planejar e a limpar depois. O `.venv` do desktop não é afetado se o build usar um ambiente virtual próprio.

### 5.3 Compatibilidade de Python e dependências

* [F] O APK embarca **somente Python 3.12, 3.13 ou 3.14** (padrão 3.14), escolhido por `requires-python` no `pyproject.toml`, `--python-version` ou `SERIOUS_PYTHON_VERSION`. Com `pyproject.toml` e `requirements.txt` juntos, o build ignora o `requirements.txt`. **Python 3.11 é incompatível.**
* [T] O código e a suíte (1264 testes) nunca rodaram em 3.12 ou superior.

| Pacote | Versão do Sino | Wheels Android disponíveis (24/10/2026) | Classificação |
|---|---|---|---|
| `cryptography` | 50.0.2 | PyPI: **nenhuma** wheel Android. Índice do Flet (`pypi.flet.dev`): **43.0.1** (cp312, cp313) e **48.0.0** (**só cp314**); ABIs arm64-v8a, armeabi-v7a, x86_64 | [F] incompatível na versão fixada |
| `regex` | 2026.9.10 | PyPI: nenhuma wheel Android. Índice do Flet: **2026.5.9** (cp312, cp313, cp314) e 2024.11.6 (cp312) | [F] incompatível na versão fixada; 2026.5.9 disponível |
| `cffi` | 2.1.1 | Índice do Flet: 2.1.1 (cp312, cp313, cp314) | [F] compatível |
| `flet-charts` | 0.86.5 | Wheel em Python puro (`py3-none-any`), exige `flet==0.86.5` | [F] compatível na parte Python; [T] inclusão da parte Flutter no build |
| `httpx`, `httpcore`, `h11`, `anyio`, `certifi`, `idna` | — | Python puro | [T] não conferido pacote a pacote; risco baixo |

* **Combinação viável sem trocar código:** Python **3.14** + `cryptography` **48.0.0** + `regex` **2026.5.9** + `cffi` **2.1.1**.
* [F] A receita oficial do Flet usa a 48.0.0 para Python ≥3.14 e a 43.0.1 para as demais versões ("43.0.1 pins pyo3 0.22.2 which hard-stops at Python 3.13"). **Não existe versão Android mais recente** compatível com o Flet 0.86.5 nas fontes oficiais.
* [F] ABIs suportadas: arm64-v8a, armeabi-v7a e x86_64 (x86 de 32 bits removida na 0.86). O carregador exige minSdk 23+, e as wheels são `android_24`; na prática, **Android 7.0 ou mais novo** (dedução).

### 5.4 Vulnerabilidades da `cryptography` e uso do Ed25519

**Uso no Sino [P]** (`backend/autorizacao_servico.py`, único módulo que importa a biblioteca):

* importa só `Ed25519PublicKey` e `InvalidSignature` (API pública);
* `Ed25519PublicKey.from_public_bytes()` com 32 bytes crus (sem ASN.1, PEM ou DER), vindos da constante `CHAVES_PUBLICAS_PRODUCAO` (`servico_codigos.py`) ou de `SINO_SERVICO_CHAVES`;
* `verify(assinatura, PREFIXO + payload)` com `bytes` contíguos;
* validação estrita **antes** da biblioteca: token de até 1024 caracteres, conteúdo de até 512 bytes, assinatura de exatamente 64 bytes, base64url canônico, JSON estrito com chaves e tipos exatos, `kid` conhecido.

**Avisos oficiais [F]:**

| Aviso | CVE | Gravidade | Afetadas → corrigida | Afeta 48.0.0 | Aplica-se ao Sino |
|---|---|---|---|---|---|
| GHSA-537c-gmf6-5ccf — OpenSSL vulnerável nas wheels | CVE-2026-34180 | Moderada | ≥0.5 → 48.0.1 | Sim, só nas wheels do PyPI | **Não no APK** (a wheel do Flet usa outro OpenSSL, 5.5); desktop já corrigido |
| GHSA-jwv3-5hgf-82ww — cadeia X.509 com crescimento exponencial | CVE-2026-69249 | Baixa | ≤48.0.0 → 49.0.0 | Sim | **Não** (sem verificação X.509 pela biblioteca) |
| GHSA-m2h6-j472-rp4c — curinga DNS fora das restrições de nome | CVE-2026-69248 | Baixa | ≤48.0.0 → 49.0.0 | Sim | **Não** |
| GHSA-g6cj-pr64-35w5 — PKCS#7: oráculo de Bleichenbacher | CVE-2026-69247 | Moderada | ≥44.0.0 → 50.0.0 | Sim | **Não** (sem `pkcs7_decrypt_*`) |
| GHSA-p423-j2cm-9vmq — buffers não contíguos | CVE-2026-39892 | Moderada | ≥45.0.0 → 46.0.7 | Não | Não (só `bytes`) |
| GHSA-m959-cc7f-wv43 — restrições de nome X.509 | CVE-2026-34073 | Baixa | ≤46.0.5 → 46.0.6 | Não | Não |
| GHSA-r6ph-v2qm-q3c2 — curvas SECT sem validação de subgrupo | CVE-2026-26007 | Alta | ≤46.0.4 → 46.0.5 | Não | Não (só curvas SECT) |

* [F] O changelog da 48.0.0 à 50.0.2 não traz nenhuma mudança em Ed25519, `from_public_bytes`, `verify` ou `InvalidSignature`; as mudanças incompatíveis do intervalo (ChaCha20, X.509, DH, fim do macOS x86_64) não tocam o código do Sino.
* [T] A segunda página da lista de avisos (avisos anteriores a 2024) não foi aberta.
* **Conclusão:** nenhuma vulnerabilidade corrigida entre a 48.0.0 e a 50.0.2 atinge o uso do Sino. O motivo registrado no `requirements.txt` para a 50.0.2 (OpenSSL embutido corrigido a partir da 48.0.1) vale para as wheels do PyPI, **não** para a wheel Android do Flet.

**Alternativas avaliadas:**

| Alternativa | Avaliação |
|---|---|
| **A. 48.0.0 só no APK (Python 3.14); 50.0.2 no desktop** | **Recomendada** (D5, pendente) |
| B. Aguardar versão Android mais nova | Sem prazo nem receita em andamento; sem ganho real de segurança |
| C. 43.0.1 com Python 3.12 ou 3.13 | Mais antiga; não recomendada |
| D. Ed25519 em Python puro | Substituição desnecessária; perde implementação auditada; exige nova revisão |
| E. PyNaCl/libsodium | Troca de biblioteca desnecessária; disponibilidade Android não verificada |
| F. Compilar wheel própria (mobile-forge) | Complexidade desproporcional ao experimento |

### 5.5 OpenSSL embarcado no Android

* [F] A receita do Flet compila a `cryptography` contra o OpenSSL do Python Android (`openssl ^3.0.12`, `OPENSSL_DIR: '{platlib}/opt'`), não contra o OpenSSL embutido das wheels do PyPI.
* [F] O python-build do Flet usa, para Python 3.13+, o fluxo oficial `Android/android.py` do CPython. Esse arquivo fixa `openssl-3.5.7-0` na tag **v3.14.6** e `openssl-3.5.9-0` no branch 3.14 atual.
* [F] Avisos do OpenSSL corrigidos depois da 3.5.7 (3.5.8 em 25/08/2026 e 3.5.9 em 29/09/2026): DTLS, QUIC, CMS, CMP, X.509, TLS 1.2 com AEAD (CVE-2026-75806, baixa), `EVP_Cipher` AEAD (CVE-2026-75803, baixa), temporização de ECDSA/SM2. **Nenhum trata de EdDSA/Ed25519.**
* **Consequência:** no Android, o risco relevante é a versão do OpenSSL embarcado, que também atende o **HTTPS** (`httpx` → `ssl`), qualquer que seja a versão da `cryptography`. Para o Sino, importam os avisos de TLS 1.2 e X.509 (classificados como baixos).
* [T] Qual patch do Python 3.14 o Flet 0.86.5 embarca (3.14.6, 3.14.7 ou 3.14.8) e, portanto, qual OpenSSL (3.5.7, 3.5.8 ou 3.5.9); se o python-build do Flet usa exatamente as dependências do CPython. Conferir no pacote gerado, depois do primeiro build autorizado (`ssl.OPENSSL_VERSION`).

### 5.6 Risco de empacotar o banco real e os backups

* [F] O build empacota a pasta do app e, por padrão, só exclui `build`, itens ocultos, ambientes virtuais (detectados por `pyvenv.cfg`) e `__pycache__`; `.env` não é empacotado.
* [P] O banco (`database/sino.db`) e os backups (`database/backups/`) ficam dentro da pasta do projeto, assim como `servidor/` (com `node_modules`), `tests/` e `docs/`.
* **Risco:** um build a partir da pasta de trabalho atual colocaria o **banco real e os backups dentro do APK**.
* **Medida proposta:** gerar o pacote a partir de uma **cópia limpa do repositório Git** (o `.gitignore` já exclui `sino.db` e `database/backups/`), com exclusões explícitas de `servidor/`, `tests/` e de `docs/` exceto `docs/legal`; conferir o conteúdo do APK antes de instalá-lo.

### 5.7 Persistência e atualização dos dados no Android

* [P] `database/db.py:26-27` grava o banco e os backups pelo caminho de `__file__`, ao lado do código.
* [F] Os arquivos do app ficam num pacote **somente leitura**; `FLET_APP_STORAGE_DATA` aponta para a pasta de suporte da aplicação e é a pasta de trabalho do app. No Android, a biblioteca padrão e o site-packages vão compactados (`stdlib.zip`, `sitepackages.zip`); pacotes que leem arquivos por `__file__` precisam de `extract_packages`. Para ler arquivos do próprio app, a recomendação é `__file__` ou `importlib.resources`.
* [F] O armazenamento interno do app é privado (outros apps não acessam), criptografado no Android 10+ e **removido na desinstalação**.
* [F] **Auto Backup** ligado por padrão (target ≥23): inclui `filesDir` e a pasta de bancos, até 25 MB, numa pasta privada do Google Drive, com criptografia de ponta a ponta no Android 9+ quando há bloqueio de tela. O Flet permite `allowBackup="false"`; em alguns fabricantes isso não impede a transferência entre aparelhos no Android 12+ (seriam necessárias `data-extraction-rules`).
* [F] Atualizações só são aceitas com o **mesmo certificado** de assinatura; com outro certificado, é preciso desinstalar, o que apaga os dados.
* [P] A Política atual diz que o banco não vai para servidores ou nuvem (`backend/documentos.py:146`) e que desinstalar não garante a remoção do banco e dos backups (`documentos.py:227`). Os dois trechos descrevem o desktop e não valem para o Android sem revisão.
* [P] `docs/legal` é lido pelo caminho do código-fonte (`documentos.py:249`) e precisa ir no pacote.
* [T] `sqlite3` no CPython embarcado (provável, biblioteca padrão); se o código do próprio app vai compactado ou extraído; suporte do Flet a `data-extraction-rules`.
* **Testes iniciais propostos:** só bancos fictícios criados no próprio aparelho (`pessoa1@demonstracao.invalid` e semelhantes); **nenhuma cópia do banco real** para o celular.

### 5.8 Acesso ao serviço de códigos em produção

* [P] Sem variáveis de ambiente, o app usa `URL_PRODUCAO` e `CHAVES_PUBLICAS_PRODUCAO` (`servico_codigos.py`, `configuracao_do_ambiente`). No Android não há como passar `SINO_SERVICO_URL` como no terminal.
* [P] O app não carrega segredos: só a URL e a chave **pública** do serviço; redirecionamentos desligados (`follow_redirects=False`, `trust_env=False`).
* [P] O cadastro exige código por e-mail; sem serviço, o experimento não passa do cadastro, e a verificação Ed25519 não é exercitada no aparelho.
* [P] HTTP só é aceito para hosts locais (`servico_codigos.py`, `validar_url_base`); o modo de demonstração exige `http://127.0.0.1:<porta>` (`fluxos_codigo.py`).
* **Opções de isolamento (pendentes):** (i) APK mínimo, com uma tela de teste que verifica uma assinatura fictícia; (ii) serviço local de desenvolvimento no PC, acessível pelo celular em `127.0.0.1` via `adb reverse` [T]; (iii) configuração do serviço no build (exige mudança de código).
* O serviço permanece em **produção restrita**; nenhuma ampliação de destinatários está autorizada.

### 5.9 Assinatura e instalação fora da Play Store

* [F] Todo APK precisa ser assinado. Sem keystore própria, o Flet assina com a **chave de depuração**, adequada só para teste local; ela muda a cada máquina ou execução de CI.
* [F] Perder a chave impede atualizar o app, e ela não pode ser recuperada. A senha da keystore não é lida do `pyproject.toml` (só por parâmetro ou variável de ambiente). Recomendação oficial de validade: 25 anos ou mais.
* **Consequência:** para atualizar sem perder dados, é preciso uma **keystore própria e estável** desde o primeiro APK com dados que importem, guardada fora do Git e com cópia de recuperação.
* [F] Permissão padrão: só `INTERNET`, que é o que o Sino precisa.
* [F] **Verificação de desenvolvedores do Android:** em vigor desde **30/09/2026 no Brasil** (e na Indonésia, em Singapura e na Tailândia), **só para instalações vindas das lojas participantes** (Google Play, Galaxy Store, HONOR, OPPO, vivo, Xiaomi, Transsion). Instalação direta do APK: ainda não afetada. **Instalação por ADB não exige verificação** e não sofre a espera do fluxo avançado. **Em 2027:** expansão global para todos os apps em aparelhos certificados; apps não verificados exigirão o "fluxo avançado" (modo de desenvolvedor, reinício, espera única de um dia, biometria ou PIN). Existe uma **conta de distribuição limitada**, gratuita e sem documento de identidade, para até **20 aparelhos**, útil para um futuro piloto.
* Riscos da instalação direta: permitir fontes desconhecidas, alertas do Play Protect, ausência de atualização automática, necessidade de conferir a integridade do arquivo (SHA-256) e de não transmiti-lo por canais não confiáveis.

### 5.10 Módulos e funcionalidades afetados

| Item | Situação |
|---|---|
| `backend/aviso_sonoro.py` (`canberra-gtk-play`/`paplay` via `subprocess`) | [P] Silencioso no Android (já é melhor esforço). [F] Alternativa: `HapticFeedback` |
| `backend/main.py:15` (ajuste de `sys.path`) | [T] Deve funcionar se a estrutura de pastas for preservada |
| `backend/main.py:1242-1243` (tamanho da janela) e `1329-1364` (fechamento seguro com `prevent_close`) | [P] Sem efeito no Android; o sistema pode encerrar o app em segundo plano. [F] Substituto: `page.on_app_lifecycle_state_change` |
| Botão ou gesto "voltar" | [P] Sem tratamento (nenhum `on_view_pop`/`page.views`); [T] pode fechar o app |
| Teclado virtual e `SafeArea` | [T] Campos podem ficar cobertos; sem `SafeArea` |
| Senhas (PBKDF2, 200.000 iterações, `db.py:1692`) | [T] Tempo no celular a medir |
| Gráficos (`flet-charts`) | [T] Dicas por toque longo; inclusão da parte Flutter |
| Temas claro e escuro | [P] Compatíveis (escolha manual no app) |
| Acessibilidade | [T] `Semantics` com TalkBack. Pendências anteriores mantidas: setas de mês sem nome acessível, leitor de tela não validado |
| Tamanhos de tela | [P] Favorável (janela de 380 px, layouts por `page.width` da E10/E12); [T] aparelhos de 320–360 dp e orientação horizontal |

### 5.11 Verificações ainda pendentes [T]

1. Suíte completa em Python 3.14, com `cryptography` 48.0.0 e `regex` 2026.5.9, no Ubuntu e em ambiente virtual separado (exige autorização específica).
2. Carga da wheel `cryptography-48.0.0` no aparelho; `from_public_bytes` e `verify` aceitando a assinatura válida e recusando a alterada.
3. Versão real do OpenSSL embarcado e do Python 3.14 no APK.
4. HTTPS do `httpx` com os certificados do `certifi` no Android.
5. Inclusão da parte Flutter do `flet-charts`.
6. `sqlite3` embarcado; gravação em `FLET_APP_STORAGE_DATA`; persistência ao fechar, reabrir e atualizar.
7. Suporte a `data-extraction-rules`; número de versão (`versionCode`); disponibilidade do `adb`.
8. Botão "voltar", teclado virtual, `SafeArea`, ciclo de vida, custo do PBKDF2, TalkBack.
9. Isolamento da produção pela opção escolhida (5.8).

## 6. Adaptações identificadas (não implementadas)

* **Alta (bloqueia o APK ou põe dados em risco):** A1 local do banco e dos backups configurável (`FLET_APP_STORAGE_DATA` no Android, caminho atual no Ubuntu); A2 `docs/legal` incluído no pacote; A3 dependências do build sem `flet-desktop`; A4 versões Android de `cryptography` e `regex` (5.3).
* **Média:** B1 botão ou gesto "voltar"; B2 ciclo de vida no lugar de `prevent_close`; B3 teclado virtual e `SafeArea`; B4 medição do PBKDF2; B5 política de Auto Backup.
* **Baixa:** C1 vibração no lugar do som; C2 dicas por toque nos gráficos; C3 revisão dos textos legais para o celular (necessária antes do uso com dados reais).

## 7. Roteiro proposto para a retomada

Cada fase depende de autorização própria.

| Fase | Conteúdo |
|---|---|
| F0 | Reconferir só o que pode ter mudado: versões no índice do Flet, avisos novos da `cryptography` e do OpenSSL, regras de verificação do Android em 2027 |
| F1 | Ambiente de build isolado (D3): pasta e ambiente virtual próprios fora do repositório, Python 3.14, `flet-cli` 0.86.5; `.venv` do desktop intocado |
| F2 | APK mínimo (tela de teste com `cryptography`, `regex`, `sqlite3` e `flet_charts`), instalado no celular pessoal |
| F3 | Adaptações A1–A3 numa branch, com a suíte completa no Ubuntu para provar que o desktop não mudou |
| F4 | APK do Sino com chave de depuração e só dados fictícios, sem fluxo de e-mail real |
| F5 | Keystore definitiva fora do Git; teste de atualização v1 → v2 sem perda de dados fictícios |
| F6 | Adaptações B1–B5 e validação manual curta no aparelho |
| F7 | Decisão sobre uso com dados reais: textos legais revistos, novo aceite, e-mail pela lista atual |

**O que não precisa ser refeito:** os diagnósticos das seções 5.1 a 5.10, salvo a reconferência da F0.

## 8. Pontos de consistência registrados no diagnóstico inicial

* A seção 11.3 da ERS lista 11 temas da M14; a tabela das propostas tem 15 (faltam lojas, revisão jurídica, serviço de códigos e avisos de terceiros).
* O risco de CPU (P43) foi aceito "só para a produção restrita", e a proteção adicional por dispositivo deve ser reavaliada "antes da disponibilização a terceiros" (13.4); a seção 11.3 só exige reavaliar o abuso para a liberação ampla. Não está definido se o piloto conta como produção restrita.
* O esboço do "Documento 2 — Condições da Distribuição Oficial" (propostas) proíbe redistribuir os pacotes oficiais "pela mesma regra do item 3" da licença própria, que não foi adotada; a licença vigente (MIT + Commons Clause, P36) permite redistribuição não comercial.
* Os Termos e a Política descrevem o computador e a pasta do Sino; mudar o local dos dados ou incluir o Android exige novos textos e novo aceite.
* O título "Situação atual (v6.0)" da M14 nas propostas está defasado; o conteúdo técnico continua correto.

## 9. Objetivo futuro: sincronização entre desktop e Android

Registro de interesse da autora: **sincronização segura entre desktop e Android por meio de um provedor de nuvem**, com arquitetura **offline-first** (cada aparelho funciona sem conexão e sincroniza quando possível).

* **Nenhum provedor escolhido ou contratado; nada implementado; arquitetura atual inalterada.**
* Características atuais que pesam nessa decisão [P]: identificadores `INTEGER AUTOINCREMENT` em todas as tabelas; datas locais (`date.today()`, `datetime.now()`), sem fuso horário; exclusões físicas (com `secure_delete` na exclusão de conta); várias pessoas usuárias por instalação.
* Decisões arquiteturais a preservar até lá:
  1. manter o acesso ao banco concentrado em `database/db.py`, sem SQL na interface;
  2. não fechar o caminho para identificadores globais (por exemplo, UUID) numa migração futura;
  3. registrar o horário das mudanças em UTC numa migração futura;
  4. decidir se exclusões precisarão de marca (tombstone), o que conflita com a promessa atual de apagar de fato;
  5. manter o local do banco configurável, sem caminho fixo no código;
  6. não acoplar a verificação de e-mail a uma identidade de nuvem por enquanto;
  7. qualquer sincronização exige novos textos legais, novo aceite e revisão do modelo atual, em que o banco não vai para a nuvem.

## 10. Restrições vigentes na suspensão

* Nenhuma instalação de ferramentas, build, geração de APK, execução de comandos do Flet ou de testes sem autorização específica.
* Nenhuma alteração de código, dependências, banco real, backups, segredos, infraestrutura ou textos legais.
* Nenhum gasto; nenhuma ampliação de destinatários do serviço de códigos.
* O banco real não deve ser copiado, migrado nem acessado para o experimento.

## 11. Referências

### 11.1 Projeto (leitura em 24/10/2026, commit `0b7739c`)

* `requirements.txt`; `.venv/pyvenv.cfg`; pacotes instalados em `.venv/lib/python3.11/site-packages/` (`flet/cli.py`, `flet/utils/pip.py`, `flet/version.py`, `flet/controls/services/storage_paths.py`, `flet/controls/page.py`).
* `backend/autorizacao_servico.py`; `backend/servico_codigos.py` (constantes de produção, `validar_url_base`, `configuracao_do_ambiente`, `TransporteHttpx`); `backend/fluxos_codigo.py` (modo de demonstração); `backend/main.py:15, 1242-1243, 1329-1364`; `backend/aviso_sonoro.py`; `backend/documentos.py:146-227, 249`; `database/db.py:26-32, 179-190, 1691-1724, 2505-2512`; `.gitignore`.
* ERS v7.0: 1, 2.1–2.3, 5.49, 11.1–11.3, 13.3, 13.4, 15.1–15.3. Propostas: M14; licença e lojas (Documento 2).

### 11.2 Fontes oficiais (consultadas em 24/10/2026)

* Flet: [Publicação Android](https://flet.dev/docs/publish/android/) · [Publicação (geral)](https://flet.dev/docs/publish/) · [Pacotes binários Android/iOS](https://flet.dev/docs/reference/binary-packages-android-ios) · [Anúncio da 0.86](https://flet.dev/blog/flet-v-0-86-release-announcement/) · [Python 3.14 padrão](https://flet.dev/docs/updates/breaking-changes/v0-86-0/default-bundled-python-3-14/) · [extract_packages](https://flet.dev/docs/updates/breaking-changes/v0-86-0/android-extract-packages/)
* Índice e receitas do Flet: [pypi.flet.dev/cryptography](https://pypi.flet.dev/cryptography/) · [pypi.flet.dev/regex](https://pypi.flet.dev/regex/) · [pypi.flet.dev/cffi](https://pypi.flet.dev/cffi/) · [mobile-forge: receita da cryptography](https://raw.githubusercontent.com/flet-dev/mobile-forge/main/recipes/cryptography/meta.yaml) · [python-build: Android](https://github.com/flet-dev/python-build/blob/main/android/README.md)
* PyPI: [flet-cli](https://pypi.org/project/flet-cli/) · [cryptography 50.0.2](https://pypi.org/project/cryptography/50.0.2/) · [regex 2026.9.10](https://pypi.org/project/regex/2026.9.10/) · [flet-charts 0.86.5](https://pypi.org/project/flet-charts/0.86.5/)
* cryptography: [Changelog](https://cryptography.io/en/latest/changelog/) · [Avisos de segurança](https://github.com/pyca/cryptography/security/advisories) (GHSA-537c-gmf6-5ccf, GHSA-jwv3-5hgf-82ww, GHSA-m2h6-j472-rp4c, GHSA-g6cj-pr64-35w5, GHSA-p423-j2cm-9vmq, GHSA-m959-cc7f-wv43, GHSA-r6ph-v2qm-q3c2)
* CPython: [Android/android.py, tag v3.14.6](https://github.com/python/cpython/blob/v3.14.6/Android/android.py) · [Android/android.py, branch 3.14](https://github.com/python/cpython/blob/3.14/Android/android.py)
* OpenSSL: [Vulnerabilidades](https://openssl-library.org/news/vulnerabilities/)
* Android Developers: [Armazenamento do app](https://developer.android.com/training/data-storage/app-specific) · [Auto Backup](https://developer.android.com/identity/data/autobackup) · [Assinatura de apps](https://developer.android.com/studio/publish/app-signing) · [Verificação de desenvolvedores](https://developer.android.com/developer-verification) · [Guias](https://developer.android.com/developer-verification/guides) · [FAQ](https://developer.android.com/developer-verification/guides/faq)
* GitHub: [Cobrança do GitHub Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
