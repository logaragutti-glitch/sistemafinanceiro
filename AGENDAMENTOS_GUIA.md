# Agendamentos e fluxo de caixa

> Os agendamentos representam compromissos futuros. Eles ajudam a projetar o caixa, mas não substituem o lançamento realizado e não alteram a DRE, as comissões ou as baixas bancárias.

## Como funciona

O sistema separa quatro grupos de movimento:

| Grupo | Fonte | Entra no realizado? | Entra no projetado? |
|---|---|---:|---:|
| Entrada realizada | `Recebimentos_CasaArvore` e `Recebimentos_Casarao` | Sim | Sim, como histórico |
| Saída realizada | `Despesas_CasaArvore` e `Despesas_Casarao` | Sim | Sim, como histórico |
| Entrada prevista | `Contas_a_Receber` com status `Aberto` ou `Atrasado`, ou receita em `Agendamentos` | Não | Sim |
| Saída prevista | `Agendamentos` com tipo `DESPESA` e status `Agendado` ou `Pendente` | Não | Sim |

Uma parcela com status `Pago` não volta a ser prevista. Um agendamento com status `Concluído`, `Baixado` ou `Cancelado` também não entra novamente na projeção.

## Como cadastrar

Abra o painel e acesse **Agendamentos**. Preencha o tipo, a empresa, a descrição, o valor, a data prevista e a recorrência. O campo `RECEITA` pode ser usado para entradas futuras que não são parcelas de um contrato. Para despesas, informe também a categoria e o favorecido quando possível.

As recorrências disponíveis são `Única`, `Mensal`, `Semanal` e `Anual`. O sistema expande a ocorrência apenas dentro do mês filtrado; não duplica linhas na planilha. A linha original permanece na aba `Agendamentos` e o cálculo gera as ocorrências somente para a visualização do fluxo.

## Como acompanhar

A página **Fluxo de caixa** mostra quatro indicadores: entradas realizadas, entradas previstas, saídas previstas e saldo projetado. O saldo projetado é calculado assim:

```text
saldo projetado = entradas realizadas + entradas previstas
                  - saídas realizadas - saídas previstas
```

A página **Resumo** também apresenta o bloco Planejamento do caixa. A DRE continua sendo uma demonstração do realizado e não usa agendamentos como receita ou despesa contabilizada.

## Estrutura da aba `Agendamentos`

| Coluna | Uso |
|---|---|
| `ID Agendamento` | Identificador único criado pelo painel. |
| `Tipo` | `RECEITA` ou `DESPESA`. |
| `Empresa` | `Casa da Árvore` ou `Casarão Festas`. |
| `Venue` | Unidade, salão ou local relacionado. |
| `Descrição` | O que será recebido ou pago. |
| `Categoria` | Categoria gerencial do movimento. |
| `Favorecido` | Fornecedor, cliente ou origem da receita. |
| `Valor` | Valor da ocorrência. |
| `Data Prevista` | Primeira data do compromisso. |
| `Recorrência` | `Única`, `Mensal`, `Semanal` ou `Anual`. |
| `Status` | `Agendado`, `Pendente`, `Concluído`, `Baixado` ou `Cancelado`. |
| `Data Baixa` | Preenchida quando a saída ou receita for realizada. |
| `ID Transação Banco` | Vínculo opcional com a transação conciliada. |
| `Observações` | Condições, centro de custo ou referência. |

A atualização do status para `Concluído` ou `Baixado` deve ocorrer somente depois que o movimento tiver sido efetivamente realizado e conciliado. Isso evita que o caixa projetado seja confundido com o caixa realizado.
