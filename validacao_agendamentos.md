# Validação de agendamentos e fluxo de caixa

O núcleo de cálculo foi validado com testes isolados e a suíte financeira existente continua passando. A aba `Agendamentos` foi criada na planilha real somente com headers.

O painel local respondeu HTTP 200 na porta 8504. A primeira navegação visual voltou para `about:blank` durante a inicialização, sem erro de aplicação; será repetida após o servidor estabilizar.

Após recarregar, o menu exibiu `Agendamentos` e `Fluxo de caixa`. O Resumo mostrou o bloco `Planejamento do caixa` com Entradas previstas, Saídas agendadas e Saldo projetado. A tela Agendamentos abriu com formulário para tipo, empresa, descrição, categoria, favorecido/origem, valor, data prevista, recorrência, venue, status e observações; a planilha real permanece sem lançamentos.

A tela Fluxo de caixa abriu corretamente com quatro cartões — Entradas realizadas, Entradas previstas, Saídas previstas e Saldo projetado — e explicou que o previsto não altera DRE, comissões ou baixas bancárias. Com a aba vazia, exibiu o empty state esperado e nenhum gráfico foi criado artificialmente.

A planilha real foi verificada via Google Sheets: `Agendamentos!A1:N1` contém os 14 headers oficiais e nenhuma linha de lançamento. A suíte final passou, incluindo `tests/test_cashflow.py`, `tests/test_dry_run.py`, compilação do painel e `git diff --check`.
