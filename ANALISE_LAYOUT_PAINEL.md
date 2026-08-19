# Análise do layout do painel financeiro

## Diagnóstico executivo

O painel atual funciona tecnicamente, mas ainda tem aparência de uma página de teste de Streamlit, não de um produto financeiro pronto para uso diário por um gestor. O problema principal não é a cor ou um componente isolado: é a **hierarquia de informação**. A tela apresenta muitas seções em sequência, mas não orienta o usuário sobre o que exige atenção agora, qual empresa está melhor, quanto falta para a meta ou qual risco financeiro precisa ser tratado.

A solução recomendada é reorganizar a experiência em torno de uma página inicial de decisão rápida, com filtros claros, cartões de indicadores mais fortes, estados vazios bem desenhados, gráficos simples e páginas separadas para operação detalhada. A lógica financeira e a planilha podem permanecer como estão; a mudança deve se concentrar na apresentação e na navegação.

## O que está bom

A separação visual entre Casa da Árvore e Casarão é um bom ponto de partida. O azul e o laranja também permitem distinguir as empresas com facilidade. O painel apresenta os blocos financeiros relevantes — receita, despesas, atraso, DRE, orçamento, comissões e contratos — e o botão de atualização manual é útil.

O painel também já trata a ausência de dados sem quebrar a aplicação. Isso deve ser preservado, mas os estados vazios precisam parecer uma orientação operacional, e não uma sequência de alertas azuis.

## Problemas observados

| Prioridade | Problema | Efeito para o usuário | Recomendação |
|---|---|---|---|
| Alta | Página única muito vertical | O gestor precisa rolar para encontrar informação importante | Criar navegação lateral com Resumo, Recebimentos, Despesas, Contratos, DRE e Comissões |
| Alta | Não existe um resumo executivo global | Não há resposta imediata para “como estamos hoje?” | Criar uma faixa superior com receita, despesas, resultado, atraso e atingimento da meta |
| Alta | Indicadores sem cartões ou contexto | Os números parecem soltos | Usar cartões com valor principal, comparação com meta/período anterior e status visual |
| Alta | Não há seletor de período ou empresa | A tela fica presa ao mês atual e às duas empresas | Adicionar filtros de mês, empresa e venue/unidade |
| Alta | Estados vazios repetidos em caixas azuis | A interface parece quebrada ou incompleta quando não há registros | Substituir por empty states com ícone discreto, explicação curta e próximo passo |
| Média | DRE, orçamento e comissões aparecem apenas como tabelas | O usuário precisa interpretar números brutos | Adicionar gráfico de evolução, barra de progresso da meta e margem destacada |
| Média | Tabelas sem tratamento financeiro suficiente | Valores, percentuais e datas têm pouca legibilidade | Formatar moeda, percentual, datas, totais e destacar atrasos/cancelamentos |
| Média | Cabeçalho genérico e emoji como marca | Aparência de protótipo, pouca identidade | Criar cabeçalho limpo com nome do sistema, período selecionado, última atualização e status de conexão |
| Média | Muitos divisores horizontais | A página fica fragmentada e comprida | Usar cards, blocos com fundo sutil e espaçamento consistente |
| Baixa | Elementos padrões do Streamlit ficam visíveis | Reduz sensação de produto próprio | Ocultar ou reduzir elementos secundários do framework quando possível |
| Baixa | Não há legenda explicando os indicadores | Termos como “A Vencer” ou “Desvio %” podem gerar dúvida | Adicionar tooltips e pequenas descrições em indicadores críticos |

## Layout recomendado

### Cabeçalho

O topo deveria conter o nome do sistema, a empresa ou grupo analisado, o período selecionado, a data da última atualização e um botão discreto de atualização. A informação de conexão deve aparecer como um pequeno status: “Planilha conectada”, “Última leitura às 08:12” ou “Atenção: dados desatualizados”.

### Barra de filtros

Logo abaixo do cabeçalho, incluir filtros para `Período`, `Empresa`, `Venue/Unidade` e, quando aplicável, `Status`. Esses filtros devem controlar todos os blocos da tela. O usuário não deveria precisar interpretar que cada seção está automaticamente limitada ao mês atual.

### Resumo executivo

A primeira tela deveria começar com cinco cartões:

1. Receita recebida no período.
2. Despesas pagas no período.
3. Resultado operacional ou margem.
4. Valor em atraso.
5. Percentual da meta mensal atingido.

Cada cartão deveria mostrar o valor principal, uma comparação curta e uma cor semântica. Verde deve significar situação favorável, vermelho atraso ou risco, e azul informação neutra. O laranja pode permanecer como cor da marca do Casarão, mas não deve ser usado como cor genérica de alerta.

### Comparação entre empresas

Em seguida, apresentar Casa da Árvore e Casarão em dois cards de mesmo tamanho. Cada card deve mostrar receita, despesa, resultado, atraso e progresso da meta. Assim o gestor consegue comparar as duas operações sem precisar olhar seis métricas soltas.

### Gráficos de decisão

Abaixo da comparação, incluir dois gráficos simples: evolução de recebimentos e despesas no período e progresso Real vs Orçado. O gráfico de orçamento deve responder visualmente quanto já foi pago, quanto ainda está a vencer e qual é a projeção. Não é necessário criar gráficos decorativos; cada visual deve apoiar uma decisão.

### Alertas prioritários

Uma seção “Requer atenção” deve aparecer antes das tabelas. Ela deve listar contratos atrasados, transações órfãs, transações ambíguas, desvio orçamentário acima de 10% e falhas de integração. Se não houver alertas, mostrar uma mensagem positiva compacta, sem ocupar um grande bloco azul.

### Detalhes operacionais

Os dados detalhados devem ficar em páginas ou abas separadas:

| Página | Conteúdo |
|---|---|
| Resumo | KPIs, comparação, gráficos e alertas |
| Recebimentos | Parcelas, baixas, recebimentos por empresa e banco |
| Despesas | Despesas por categoria, venue e período |
| Contratos | Contas a receber, vencimentos, atraso e contatos |
| DRE | Receita, impostos, custos, comissões, lucro e margem |
| Comissões | Vendedores, base, percentual, líquido e estornos |
| Operação | Última execução, extratos presentes, falhas e data da última sincronização |

## Direção visual recomendada

A direção visual deve ser **executiva, limpa e acolhedora**, evitando tanto o aspecto genérico de planilha quanto uma aparência excessivamente chamativa. Recomendo fundo neutro claro, cards brancos com borda muito sutil, tipografia maior nos valores, títulos mais compactos e uma única cor de destaque por empresa.

A paleta atual azul/laranja pode ser preservada como identificação das empresas, mas deve ser complementada por tons neutros: grafite para textos, cinza claro para superfícies e verde/vermelho apenas para estados financeiros. O uso de emoji deve ser reduzido a zero ou mantido somente quando tiver função clara; o ícone de gráfico no título pode ser substituído por uma marca textual mais profissional.

## Alterações que eu faria primeiro

### Fase 1 — maior impacto

Eu começaria pela nova estrutura da página inicial: cabeçalho, filtros, cinco KPIs executivos, comparação entre empresas e seção de alertas. Também substituiria os quatro grandes `st.divider()` por blocos visuais mais compactos e criaria empty states orientados à ação.

### Fase 2 — tornar o painel realmente útil

Depois, separaria os detalhes em páginas laterais e adicionaria gráficos de evolução e orçamento. Nessa etapa também padronizaria moeda, percentuais, datas, títulos de colunas e cores de status.

### Fase 3 — acabamento de produto

Por fim, aplicaria identidade visual mais própria, ajustaria responsividade para celular, adicionaria tooltips e criaria uma página de operação com conectividade da planilha, horário da última execução e situação dos seis extratos.

## O que eu não alteraria

Eu não mudaria a regra de negócio do matching, a planilha como fonte de verdade, a separação entre Casa da Árvore e Casarão, a dupla notificação por e-mail e WhatsApp, nem a comissão sobre o contrato assinado. O redesign deve melhorar a leitura e a operação sem tocar nas decisões financeiras já validadas.

## Conclusão

Minha avaliação é que o painel atual está funcional, mas visualmente ainda é um **MVP operacional**. Eu faria um redesign da interface antes de considerá-lo a versão definitiva para o gestor. A prioridade não seria “embelezar” a tela; seria transformá-la em um painel que responde em poucos segundos: **quanto entrou, quanto saiu, quanto falta para a meta, o que está atrasado e qual ação precisa ser tomada hoje**.
