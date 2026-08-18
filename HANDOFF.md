# Relatório de handoff — Sistema Financeiro Casa da Árvore + Casarão

**Data:** 2026-08-18
**Repositório:** https://github.com/logaragutti-glitch/sistemafinanceiro (privado)
**Painel em produção:** https://sistemafinanceiro-noljjkpic5pxfvvwdy2mwx.streamlit.app
**Planilha (fonte de verdade dos dados):** Google Sheets, ID `1l86KZvf7t4qYeMLd736eWH-VZSHsXC-abiUc4FYKyLQ`

Este documento existe pra qualquer programador (interno ou terceirizado) conseguir
pegar o sistema de onde ele está e terminar o que falta, sem precisar reconstruir
o contexto do zero. Leia inteiro antes de mexer em qualquer coisa — tem decisões
de negócio e armadilhas técnicas já resolvidas que não estão óbvias só olhando o código.

---

## 1. O que este sistema faz

Automação financeira em Python para duas empresas de eventos em Cabo Frio/RJ —
**Casa da Árvore** (3 venues: Venue Principal, Park Lagos, Pôr do Sol) e
**Casarão Festas** — substituindo um fluxo que antes rodava no Make (economia de
R$200/mês). Roda 7 "cenários" agendados (`main.py` + lib `schedule`), cada um
um módulo em `src/scenario_N_*.py`:

| Cenário | Horário | O que faz |
|---|---|---|
| 1 — Ingestão | 06:00 diário | Puxa transações bancárias, casa com contratos em `Contas_a_Receber`, dá baixa |
| 2 — Alertas | 08:00 diário | Resumo diário + marca atraso + régua de cobrança (lembrete/cobrança pro cliente) |
| 7 — Real vs Orçado | 08:15 diário | Projeção do mês vs meta, alerta se desvio > 10% |
| 5 — Análise IA | 08:30 diário | Claude gera 2-3 insights do dia |
| 4 — Relatório semanal | Sexta 17:00 | Receita/despesa/margem da semana |
| 6 — DRE | Sexta 17:30 | Demonstrativo de resultado do mês, com impostos |
| 3 — Comissões | Sexta 18:00 | Comissão sobre CONTRATO ASSINADO (não sobre parcela paga), com estorno se cancelar |

**Princípio arquitetural central**: nada é lançado sem um CONTRATO prévio na aba
`Contas_a_Receber`. O banco só dá baixa quando a transação bate com uma parcela
aberta. Isso é proposital — permite saber inadimplência real, não estimada.

---

## 2. Status atual — o que está pronto e testado

✅ **Lógica de negócio dos 7 cenários** — implementada e coberta por
`tests/test_dry_run.py` (58 checagens, roda sem nenhuma credencial real, usa
stubs/banco-de-dados em memória). **Rode isso antes e depois de qualquer
mudança**: `python tests/test_dry_run.py` tem que terminar em
"🎉 TODOS OS TESTES PASSARAM".

✅ **Agregador bancário (`src/aggregator.py`)** — modo `arquivo` (grátis, lê
extrato exportado manualmente, ver seção 4). Todas as 6 contas reais
validadas contra extrato de verdade:
- Sicoob (XLSX) — 238 transações reais, bateu com variação de saldo
- Itaú (XLSX) — 106 transações reais, bateu com variação de saldo
- Caixa (OFX nativo) — 157 transações reais, bateu com variação de saldo

✅ **Google Sheets** — planilha real criada, 11 abas com headers corretos
(script `scripts/criar_planilha.py` recria/completa se precisar).

✅ **Notificações duplo-canal** — `src/notificar.py` manda por WhatsApp E
e-mail em paralelo (decisão do dono: não substituir, manter os dois). E-mail
testado com envio real (Gmail + senha de app). WhatsApp **ainda não
configurado** (falta token).

✅ **Painel web (`painel/app.py`)** — Streamlit, só leitura, deployado em
produção no Streamlit Community Cloud (grátis), confirmado funcionando com
dados reais da planilha.

✅ **Config de negócio confirmada** (`config.py`): CNPJ, chaves Pix, alíquota
do Simples (10% pras duas empresas), metas mensais (Casa da Árvore
R$200.000, Casarão R$100.000).

---

## 3. O que falta — em ordem de prioridade

### 3.1 Credenciais pendentes
- **WhatsApp Business Cloud API**: `WHATSAPP_PHONE_ID`, `WHATSAPP_TOKEN`,
  `GESTOR_PHONE` no `.env` — ainda vazios. Sem isso, `notificar.py` tenta,
  falha rápido (HTTPError 4xx, ~0.4s, não fica travado) e segue só com
  e-mail — **o sistema funciona sem o WhatsApp, só fica sem esse canal**.

### 3.2 Dados de negócio incompletos
- **`config.VENDEDORES`**: só tem 1 vendedora real confirmada (**Cris**,
  Casa da Árvore, 1%, e-mail `comerciargrupocasadaarvore@gmail.com`, telefone
  ainda não confirmado). O resto da equipe de vendas precisa ser cadastrado.
- **`Contas_a_Receber` está vazia** — nenhum contrato real lançado ainda.
  **Sem isso, o sistema não tem nada pra processar.** É o próximo passo mais
  importante antes de considerar o sistema "em produção" de verdade.

### 3.3 Operacional
- **Rotina diária de extrato**: alguém precisa baixar os extratos das 6
  contas todo dia e salvar em `extratos/<CONTA_KEY>.{ofx,xlsx}` antes das
  06:00 (ver seção 4). Isso é manual, não tem como automatizar sem pagar um
  agregador comercial (ver seção 6).
- **Hospedagem do `main.py`**: hoje ninguém está rodando o agendador
  continuamente. Precisa de uma VPS (~R$20-30/mês), Raspberry Pi, ou rodar
  local enquanto o PC estiver ligado (só pra teste).

---

## 4. Decisões de arquitetura — por que é assim, não tente "consertar"

### 4.1 Agregador bancário: `AGGREGATOR=arquivo`, não Pluggy/Belvo pago
Os planos comerciais de Open Finance custam R$1.500–6.000+/mês (Pluggy
"Dados" R$2.500/mês, Belvo US$1.000/mês) — inviável pro porte do negócio. O
"Meu Pluggy" gratuito **não serve**: pelos termos de uso dele, é só pra
pessoa física com dados próprios sem fins comerciais; as contas aqui são PJ
e o uso é comercial — usar violaria os termos.

**Solução**: `AGGREGATOR=arquivo` em `src/aggregator.py` lê extratos
exportados manualmente (`EXTRATOS_DIR`, padrão `extratos/`), um arquivo por
conta, nome = chave da conta (`AZEVEDO_SICOOB.xlsx`, `AZEVEDO_CAIXA.ofx`
etc). Sicoob e Itaú exportam XLSX em layouts **incompatíveis entre si**
(`_xlsx_transacoes_sicoob` vs `_xlsx_transacoes_itau`, despachado por
`config.CONTAS_BANCARIAS[conta_key]["banco"]`); Caixa exporta OFX nativo.

**Gotcha real já corrigido**: a Caixa reaproveita o mesmo FITID (o "ID
único" do padrão OFX) em várias transações diferentes do mesmo lote — extrato
real testado teve 157 transações mas só 97 FITIDs distintos. Deduplicar só
por FITID (comportamento óbvio/ingênuo) descartaria 60 transações reais como
se fossem repetidas. `_ofx_transacoes` dedupilica por
FITID+data+valor+memo — vale pra qualquer banco, não só Caixa.

### 4.2 Chave Pix não identifica a empresa — matching é por valor
A arquitetura original previa usar a chave Pix pra saber se um crédito na
conta compartilhada Azevedo (recebe Casa da Árvore E Casarão) era de qual
empresa. **Testado contra extrato real de dois bancos (Sicoob e Itaú): essa
informação não existe no extrato.** Bancos mostram quem pagou, não qual
chave sua foi usada pra receber. `pix_key_destino` fica sempre vazio nesse
modo.

Na prática o sistema depende 100% do matching por valor+vencimento contra
`Contas_a_Receber`. Isso é seguro porque `scenario_1_ingest.match_parcela()`
tem uma trava de ambiguidade: se mais de uma parcela aberta bate com a
mesma transação (mesmo valor, janela de vencimento coincidente), **não casa
automaticamente** — cai numa fila de revisão manual (WhatsApp/e-mail pro
gestor), em vez de arriscar dar baixa errada silenciosamente. Essa foi uma
decisão explícita do dono (havia duas opções: fila manual vs. desempate por
vencimento mais próximo — ele escolheu fila manual).

### 4.3 Notificação dupla (WhatsApp + e-mail), não substituição
O dono considerou substituir WhatsApp por e-mail, decidiu manter os dois.
`src/notificar.py` é a camada única que os cenários chamam — dispara pros
dois canais, cada um com try/except independente (falha de um não impede o
outro). Não delete `src/whatsapp.py` achando que é código morto.

### 4.4 Comissão sobre contrato assinado, não sobre parcela paga
Decisão explícita do dono, não é bug: `scenario_3_commissions.py` calcula
comissão sobre o **valor total do contrato**, na semana da **assinatura**
(não do pagamento), com estorno automático se cancelado. Um contrato de
R$8.000 assinado gera comissão sobre R$8.000 inteiro, mesmo que só a
primeira parcela tenha sido paga.

---

## 5. Estrutura de arquivos

```
sistema-financeiro-casa-da-arvore/
├── HANDOFF.md            # este arquivo
├── README.md             # guia de setup mais focado em uso, menos em arquitetura
├── PROMPT_CLAUDE_CODE.md # prompt original que iniciou o projeto (histórico)
├── requirements.txt
├── .env.example           # copie pra .env e preencha (nunca commitar o .env)
├── config.py              # TODOS os parâmetros de negócio — editar aqui, não no código dos cenários
├── main.py                # agendador (roda os 7 cenários nos horários certos)
├── scripts/
│   └── criar_planilha.py  # cria/completa as abas da planilha Google Sheets
├── painel/
│   ├── app.py              # painel Streamlit (só leitura)
│   ├── requirements.txt    # deps específicas do painel (Streamlit Cloud usa este)
│   └── .streamlit/secrets.toml  # gitignored — credenciais pro painel local
├── .streamlit/secrets.toml # gitignored — mesmo conteúdo, outro caminho que o Streamlit também checa
├── src/
│   ├── aggregator.py       # extratos OFX/XLSX (grátis) ou Pluggy/Belvo (pago, não usar)
│   ├── sheets.py            # cliente Google Sheets
│   ├── whatsapp.py          # WhatsApp Business Cloud API
│   ├── email_sender.py      # e-mail via SMTP (Gmail/Outlook, senha de app)
│   ├── notificar.py         # camada única: manda pros dois canais
│   ├── claude_ai.py         # análises com Claude API
│   ├── net_utils.py         # timeout + retry compartilhado (com_retry decorator)
│   ├── logging_config.py    # logger rotativo em logs/sistema.log
│   └── scenario_1..7_*.py   # os 7 cenários
├── tests/
│   └── test_dry_run.py      # 58 checagens, sem credenciais, especificação viva do sistema
└── extratos/                 # onde salvar os extratos baixados manualmente (gitignored)
```

---

## 6. Credenciais e onde ficam (`.env`)

| Variável | Status | Onde conseguir |
|---|---|---|
| `AGGREGATOR` | ✅ `arquivo` | fixo, não mudar sem decisão explícita do dono |
| `GOOGLE_CREDENTIALS_FILE` / `SPREADSHEET_ID` | ✅ configurado | Google Cloud Console → service account `sistema-financeiro@sinuous-city-450422-j2.iam.gserviceaccount.com` |
| `ANTHROPIC_API_KEY` | ✅ configurado e testado | console.anthropic.com |
| `EMAIL_REMETENTE` / `EMAIL_SENHA_APP` / `GESTOR_EMAIL` | ✅ configurado e testado (Gmail) | myaccount.google.com/apppasswords |
| `WHATSAPP_PHONE_ID` / `WHATSAPP_TOKEN` / `GESTOR_PHONE` | ❌ pendente | developers.facebook.com → app → WhatsApp → API Setup |
| `PLUGGY_*` / `BELVO_*` / `LINK_*` | não usado | só preencher se decidir pagar um agregador comercial (não recomendado, ver 4.1) |

**Arquivos com segredo real, nunca commitados** (checar `.gitignore` antes de
adicionar qualquer coisa nova que tenha credencial):
- `.env`
- `credentials.json` (chave da service account Google)
- `.streamlit/secrets.toml` e `painel/.streamlit/secrets.toml` (mesmo
  conteúdo do `credentials.json` + `SPREADSHEET_ID`, em formato TOML pro
  Streamlit Cloud)

**Gotcha real do deploy**: colar a `private_key` (formato PEM multi-linha)
direto de uma mensagem de chat/navegador na caixa de Secrets do Streamlit
Cloud corrompe a chave (caracteres especiais podem ser alterados no
caminho). A versão que funciona usa a chave como **string de uma linha só,
com `\n` escapado literalmente** (é o mesmo formato que já vem dentro do
`credentials.json` — não precisa reformatar à mão, só usar o campo
`private_key` do JSON direto). Sempre copiar de um arquivo `.toml` aberto
localmente, nunca copiar/colar via chat pra um campo de produção.

---

## 7. Deploy e ambiente

### 7.1 Painel (já em produção)
- GitHub: `logaragutti-glitch/sistemafinanceiro`, branch `main`
- Streamlit Cloud: main file path `painel/app.py`, secrets configurados
- Deploy automático: todo push na `main` atualiza o painel sozinho

### 7.2 Backend (`main.py`) — ainda não hospedado
Não tem servidor rodando o agendador ainda. Opções, em ordem de custo:
1. Rodar local (`python main.py`) — só serve pra teste, para quando o PC desliga
2. Raspberry Pi na empresa
3. VPS barata (R$20-30/mês) — recomendado pra produção real
4. GitHub Actions com cron — alternativa serverless grátis, um workflow por cenário (ainda não configurado, seria um bom primeiro passo pro programador que pegar isso)

### 7.3 Ambiente Python local
```bash
pip install -r requirements.txt   # painel usa painel/requirements.txt separado
python tests/test_dry_run.py       # confirma que a lógica de negócio está ok
python -m src.aggregator --test    # confirma que os 6 extratos estão acessíveis
```
No Windows, o console usa cp1252 por padrão e quebra nos emojis do output —
rodar com `PYTHONIOENCODING=utf-8` se der erro de encoding.

---

## 8. Risco operacional identificado nesta sessão

A pasta local do projeto **já desapareceu do disco duas vezes** em sessões
anteriores, sem explicação clara (não foi apagada manualmente segundo o
dono, não estava na Lixeira). Cada vez foi recuperada via `git clone` do
GitHub + reconstrução manual das credenciais (que não são versionadas, de
propósito). **Isso é sintoma de depender de uma pasta local/Desktop pra
código de produção.** Recomendação forte: assim que o `main.py` for pra uma
VPS (seção 7.2), o código deve rodar a partir de um `git clone` na própria
VPS, não depender mais dessa pasta local de desenvolvimento no Windows do
dono.

---

## 9. Contato / dono do negócio

Matheus Aragutti (`log.aragutti@gmail.com` / `log.aragutti@hotmail.com`) —
**leigo em termos técnicos**, precisa de instruções bem explicadas passo a
passo (qual botão clicar, onde fica) pra qualquer interação com GitHub,
Streamlit Cloud, Google Cloud Console etc. Não assuma conhecimento prévio de
terminal, git, ou deploy.
