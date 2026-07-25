# Sistema Financeiro — Casa da Árvore + Casarão (V2)

Automação financeira completa em Python, substituindo o Make (economia de R$200/mês).
Implementa a ARQUITETURA V2: chaves Pix por empresa, Contas_a_Receber como espinha
dorsal, comissão sobre contrato assinado com estorno, DRE com impostos.

## Estrutura
```
sistema-financeiro/
├── README.md
├── requirements.txt
├── .env.example          # copie para .env e preencha
├── config.py             # parâmetros do negócio (empresas, chaves Pix, comissões, impostos)
├── main.py               # agendador: roda os 7 cenários nos horários certos
├── scripts/
│   └── criar_planilha.py # cria/completa as abas da planilha Google Sheets
└── src/
    ├── aggregator.py     # extratos OFX (grátis) ou Pluggy/Belvo (Open Finance pago)
    ├── sheets.py         # cliente Google Sheets (11 abas)
    ├── whatsapp.py       # WhatsApp Business Cloud API
    ├── email_sender.py   # e-mail via SMTP (Gmail/Outlook, senha de app)
    ├── notificar.py      # manda por WhatsApp E e-mail ao mesmo tempo
    ├── claude_ai.py      # análises com Claude API
    ├── scenario_1_ingest.py        # 06:00 puxar transações + match Contas_a_Receber
    ├── scenario_2_alerts.py        # 08:00 alertas diários + inadimplência + régua cobrança
    ├── scenario_3_commissions.py   # Sex 18:00 comissões (contrato assinado + estorno)
    ├── scenario_4_weekly.py        # Sex 17:00 relatório semanal
    ├── scenario_5_analysis.py      # 08:30 análise diária com Claude
    ├── scenario_6_dre.py           # Sex 17:30 DRE com impostos
    └── scenario_7_budget.py        # 08:15 Real vs Orçado
```

## Teste AGORA, sem credenciais (dry-run)
Antes de mexer em banco, planilha, WhatsApp ou e-mail reais, valide a lógica de negócio:
```
python tests/test_dry_run.py
```
Isso roda os Cenários 1, 2, 3 e 6 de verdade contra dados simulados em memória
(6 contas bancárias, contratos, matching, comissão sobre contrato assinado, DRE),
sem precisar instalar gspread/anthropic nem preencher o `.env`. Imprime um
relatório PASSOU/FALHOU de cada regra e mostra as mensagens que teriam ido
pro WhatsApp e pro e-mail. Rode de novo sempre que editar `config.py` ou os cenários.

## Notificações: WhatsApp E e-mail ao mesmo tempo
Toda notificação do sistema (pro gestor, pros clientes na régua de cobrança,
pros vendedores na comissão) sai pelos dois canais — `src/notificar.py` chama
`whatsapp.py` e `email_sender.py` de forma independente; se um canal falhar
(ex: token do WhatsApp expirado), o outro ainda tenta, e só loga o erro.

Pra clientes, `Contas_a_Receber` tem as colunas `Fone Cliente` e
`Email Cliente` — a régua de cobrança usa qualquer uma que estiver
preenchida (não precisa das duas). Pros vendedores, `config.VENDEDORES` tem
`fone` e `email` de cada um — **os e-mails ali são placeholder, confirmar os
reais antes de produção**.

O e-mail sai via SMTP com uma "senha de app" do Gmail/Outlook (ver
`.env.example`, seção E-mail) — não precisa de conta paga em serviço de
e-mail transacional.

## Agregador bancário: modo "arquivo" (grátis) em vez de Pluggy/Belvo pago
Os planos comerciais de Open Finance são caros pro porte deste negócio: Pluggy
"Dados" a partir de **R$ 2.500/mês**, Belvo a partir de **US$ 1.000/mês** — 12x
e mais o custo do Make que este projeto substitui. O "Meu Pluggy" gratuito
**não serve aqui**: por termos de uso, é só pra pessoa física acessando dados
próprios sem fins comerciais — as 6 contas são PJ (CNPJ) e o uso é claramente
comercial (automação financeira de duas empresas).

Por isso o modo recomendado é `AGGREGATOR=arquivo`: `aggregator.py` lê
extratos exportados manualmente do internet banking de cada conta, salvos em
`EXTRATOS_DIR` (padrão: `extratos/`), um arquivo por conta nomeado com a
chave da conta — ex: `extratos/AZEVEDO_SICOOB.ofx` ou `extratos/AZEVEDO_SICOOB.xlsx`
(suporta os dois formatos; se os dois existirem pra mesma conta, o `.ofx` tem
prioridade). Zero custo, mas alguém precisa baixar e salvar os 6 extratos todo
dia antes das 06:00 (horário do Cenário 1). Transações já processadas ficam
registradas em `extratos/.processados.json` — no OFX por FITID+data+valor+memo
(**não só FITID**: confirmado com extrato real da Caixa que o mesmo FITID se
repete em várias transações distintas do mesmo lote — 157 transações reais,
só 97 FITIDs únicos; usar só o FITID faria perder 60 transações de verdade),
no XLSX por hash de data+valor+detalhes. Isso evita contar duas vezes se o
extrato baixado de novo ainda incluir dias antigos.

**Cada banco exporta XLSX num layout diferente** — `_xlsx_transacoes`
despacha pro parser certo (`_xlsx_transacoes_sicoob` ou `_xlsx_transacoes_itau`)
conforme `config.CONTAS_BANCARIAS[conta_key]["banco"]`. Status por banco (todas
as 6 contas confirmadas):
- **Sicoob** (XLSX): validado contra extrato real (238 transações, soma bateu com a variação de saldo do período)
- **Itaú** (XLSX): validado contra extrato real (106 transações, soma bateu com a variação de saldo do período)
- **Caixa** (OFX nativo): validado contra extrato real (157 transações, incluindo o caso de FITID repetido acima)

**Confirmado com extrato real (Sicoob e Itaú): a chave Pix NÃO aparece em
nenhum campo do extrato.** O Sicoob mascara o CPF/CNPJ de quem paga e de quem
recebe; o Itaú mostra Nome/Razão Social e CPF/CNPJ completos, mas nenhum dos
dois expõe "recebido pela chave X". Isso significa que a identificação
automática de empresa (Casa da Árvore vs Casarão) na conta compartilhada
Azevedo **não é possível a partir do extrato bancário** — o sistema depende
inteiramente do matching por valor+vencimento contra `Contas_a_Receber`,
protegido pela trava de ambiguidade do Cenário 1 (mais de um candidato → fila
de revisão manual, não casa às cegas). `pix_key_destino` fica sempre vazio
nesse modo; o código tenta extrair a chave do texto mesmo assim
(`_pix_key_no_texto`), por segurança, caso algum banco inclua isso no futuro
ou em outro formato — mas não conte com isso.

## Setup (Semana 0-1) — quando for para produção
1. `pip install -r requirements.txt`
2. Copie `.env.example` → `.env` e preencha as credenciais
3. Baixe os 6 extratos OFX do internet banking e salve em `extratos/<CONTA>.ofx`,
   depois valide: `python -m src.aggregator --test`
4. Compartilhe uma planilha (nova ou existente) com o e-mail da service
   account (`client_email` do `credentials.json`), permissão Editor. Depois
   rode `python -m scripts.criar_planilha` — cria (ou completa) todas as 11
   abas com os headers exatos que os cenários esperam, incluindo
   `Metas_Mensais` (é de lá que o Cenário 7 lê a meta de cada empresa; antes
   ficava hardcoded no código). Se criar uma planilha nova, o script imprime
   o `SPREADSHEET_ID` pra você colar no `.env`.
   Metas já definidas pelo gestor: `Casa da Árvore | 200000` e
   `Casarão Festas | 100000` — insira essas duas linhas na aba `Metas_Mensais`
   depois que o script criar
5. Preencha `EMAIL_REMETENTE`/`EMAIL_SENHA_APP`/`GESTOR_EMAIL` no `.env` (ver
   seção "Notificações" acima) e `WHATSAPP_PHONE_ID`/`WHATSAPP_TOKEN`/`GESTOR_PHONE`
6. Rode manualmente cada cenário: `python -m src.scenario_1_ingest`
7. Produção: `python main.py` (mantém agendador rodando) ou use cron/systemd

## Deploy sugerido
- VPS barata (R$20-30/mês) ou Raspberry Pi na empresa
- Alternativa serverless: GitHub Actions com cron (grátis) — um workflow por cenário

## Claude Code
Abra esta pasta no Claude Code e peça, por exemplo:
"implemente o TODO do matching por chave Pix no scenario_1" — os TODOs marcam os
pontos que dependem das suas credenciais reais.
