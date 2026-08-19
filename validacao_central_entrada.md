# Validação da central de entrada

O painel local respondeu HTTP 200 na porta 8506. A primeira navegação visual voltou para `about:blank` durante a inicialização do Streamlit, sem erro de aplicação; será repetida após o servidor estabilizar.

A central foi compilada e os testes de upload, fluxo de caixa e dry-run financeiro passaram.

Após a segunda abertura, o painel local carregou sem erro e mostrou no menu o caminho `Importações → Agendamentos → Fluxo de caixa`, além do bloco Planejamento do caixa no Resumo. A página Importações ainda será aberta para validar o checklist e os modelos para download.

A central Importações abriu com o título `Central de entrada`, instrução de ordem 1) contratos, 2) extratos, 3) compromissos futuros, quatro cards de checklist, expander com modelos para download e abas numeradas `1. Contratos`, `2. Extratos bancários` e `3. Agendamentos`. A visualização está coerente com o caminho único solicitado.
