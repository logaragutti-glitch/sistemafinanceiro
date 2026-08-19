# Checklist final de ativação

Este checklist parte de um sistema já validado, com painel publicado, CI aprovado e planilha configurada. Ele evita ativar o agendador antes de haver contratos e extratos reais.

## 1. Preparar a máquina que ficará ligada

Use uma VPS, Raspberry Pi ou computador da empresa que permaneça ligado. No diretório do usuário `ubuntu`, execute:

```bash
git clone https://github.com/logaragutti-glitch/sistemafinanceiro.git ~/sistema-financeiro
cd ~/sistema-financeiro
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Coloque `credentials.json` na raiz e preencha `.env`. O valor de `AGGREGATOR` deve permanecer `arquivo`, e `SPREADSHEET_ID` deve apontar para a planilha já configurada. O WhatsApp pode ficar vazio na primeira ativação, pois o e-mail é um canal independente.

## 2. Configurar os contratos

Preencha `templates/contas_a_receber.csv` exclusivamente com contratos reais. Cada parcela deve ter uma combinação única de `ID Contrato` e `Parcela`, empresa válida, valor, vencimento e data de assinatura.

Valide antes de escrever:

```bash
.venv/bin/python -m scripts.importar_contas_receber --csv contratos.csv --dry-run
```

Depois importe:

```bash
.venv/bin/python -m scripts.importar_contas_receber --csv contratos.csv
```

## 3. Configurar os seis extratos

Baixe diariamente os extratos antes das 06:00 e salve um arquivo por conta em `extratos/`, usando exatamente estes nomes:

```text
AZEVEDO_SICOOB.xlsx ou .ofx
AZEVEDO_CAIXA.xlsx ou .ofx
AZEVEDO_ITAU.xlsx ou .ofx
PARKLAGOS_CAIXA.xlsx ou .ofx
PARKLAGOS_ITAU.xlsx ou .ofx
PORDOSOL_CAIXA.xlsx ou .ofx
```

Valide o acesso local:

```bash
.venv/bin/python -m src.aggregator --test
```

## 4. Executar o diagnóstico antes da ativação

```bash
.venv/bin/python -m scripts.verificar_producao --online
```

Não ative o serviço enquanto houver erro de credencial, planilha inacessível ou `Contas_a_Receber` vazia.

## 5. Testar um cenário manualmente

Depois de confirmar os contratos e extratos, execute primeiro a ingestão:

```bash
.venv/bin/python -m scripts.run_once --cenario 1
```

Verifique a baixa correta das parcelas, a aba de recebimentos e os avisos enviados. Em caso de transação órfã ou ambígua, corrija a planilha manualmente antes de seguir.

## 6. Ativar o agendador

```bash
sudo cp deploy/systemd/sistema-financeiro.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sistema-financeiro
sudo systemctl status sistema-financeiro
journalctl -u sistema-financeiro -f
```

O serviço está configurado para o fuso `America/Sao_Paulo` e executa `main.py` com os horários definidos no projeto. Não rode o agendador simultaneamente em duas máquinas.

## 7. Primeira semana de acompanhamento

Confira diariamente se os seis extratos foram baixados, se o Cenário 1 registrou transações órfãs ou ambíguas e se os e-mails chegaram ao gestor. Na primeira sexta-feira, confira DRE, relatório semanal e comissões antes de considerar a rotina estabilizada.

## 2A. Configurar agendamentos e fluxo projetado

A planilha deve conter a aba `Agendamentos` com os headers criados pelo sistema. No painel publicado, abra **Agendamentos** e registre somente compromissos futuros reais, escolhendo `RECEITA` ou `DESPESA`, empresa, valor, data prevista, recorrência e status `Agendado` ou `Pendente`.

Depois abra **Fluxo de caixa** e confira as quatro métricas: entradas realizadas, entradas previstas, saídas previstas e saldo projetado. O cadastro não deve ser usado para simular pagamentos já feitos. Quando um compromisso for realizado e conciliado, atualize o status para `Concluído` ou `Baixado` e preencha a referência da transação, para que ele deixe de aparecer como previsto.

A DRE e as comissões continuam usando somente o realizado. Não é necessário alterar os cenários 1, 3 ou 6 para cadastrar uma previsão.

## 1A. Usar a Central de entrada do painel

Depois de abrir o painel, entre em **Importações**. Siga a ordem apresentada na tela: **1. Contratos**, **2. Extratos bancários**, **3. Agendamentos**. A própria página mostra o status atual, permite baixar os modelos e exige pré-visualização e confirmação antes de gravar.

Não envie `credentials.json`, senhas, tokens ou chaves por essa tela. Esses itens continuam configurados nos Secrets do Streamlit ou no `.env` protegido do servidor.
