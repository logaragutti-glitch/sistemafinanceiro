# Validação da área de Importações

O painel local respondeu HTTP 200 na porta 8505. A primeira abertura visual voltou para `about:blank` durante a inicialização do Streamlit, sem erro de aplicação; será repetida após o servidor estabilizar.

Os validadores de CSV e extratos passaram nos testes isolados, e a suíte financeira existente continua passando.

Após a segunda abertura, o painel local carregou sem erro. O menu lateral mostra `Importações`, `Agendamentos` e `Fluxo de caixa`. O Resumo continua exibindo os cards e o bloco de planejamento. A tela de Importações ainda não foi aberta nesta validação visual.

A área de Importações abriu com aviso explícito de que selecionar arquivo não grava nada. A aba Contratos mostra o upload CSV e as regras de validação. A aba Agendamentos mostra o upload CSV e informa que os registros entram no caixa projetado, não no realizado.

Foi enviado localmente um CSV de teste para a aba Agendamentos. O painel validou 1 linha, mostrou a prévia tabular, identificou 1 linha nova e manteve o botão de importação desabilitado até a confirmação. O botão não foi acionado; nenhum dado foi gravado na planilha.
