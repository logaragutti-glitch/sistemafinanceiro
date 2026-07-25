# Prompt para Claude Code — Sistema Financeiro Casa da Árvore + Casarão

Cole o texto abaixo no Claude Code, dentro da pasta `codigo/` descompactada do zip.

---

## PROMPT

Você está no repositório de um sistema de automação financeira para duas
empresas de eventos em Cabo Frio/RJ: Casa da Árvore (3 venues: Venue
Principal, Park Lagos, Pôr do Sol) e Casarão Festas. Leia primeiro o
`README.md` e o `config.py` inteiros para entender a arquitetura antes de
mexer em qualquer coisa.

### Contexto que você precisa saber
- O sistema substitui o Make (economiza R$200/mês) rodando 7 cenários em
  Python, agendados via `main.py`.
- Existem 6 contas bancárias reais em 3 bancos (Sicoob, Caixa, Itaú),
  agrupadas em 3 unidades: Azevedo (recebe Casa da Árvore E Casarão na
  mesma conta — por isso precisa de chave Pix separada por empresa),
  Park Lagos e Pôr do Sol (cada uma exclusiva da Casa da Árvore).
- A "espinha dorsal" do sistema é a aba `Contas_a_Receber`: todo registro
  financeiro nasce de um CONTRATO (com vendedor, valor, parcelas,
  vencimento), e o banco só dá baixa quando o Pix/TED correspondente chega.
  Não existe lançamento sem contrato prévio — isso é proposital (permite
  saber inadimplência real e projeção real, não estimativa).
- Comissão é sobre CONTRATO ASSINADO (não sobre parcela paga), com estorno
  automático se o contrato for cancelado — decisão explícita do gestor.
- Já existe `tests/test_dry_run.py`, um teste offline com dados simulados
  em memória que valida a lógica de negócio sem precisar de credenciais.
  RODE ESSE TESTE ANTES E DEPOIS DE QUALQUER MUDANÇA:
  `python tests/test_dry_run.py` — ele tem que continuar em
  "🎉 TODOS OS TESTES PASSARAM" no final. Se você alterar regra de negócio,
  atualize também as asserções do teste (elas são a especificação viva do
  sistema).

### O que fazer, nesta ordem

**1. Auditoria inicial**
Rode `python tests/test_dry_run.py` e confirme que passa. Leia os 7
arquivos `src/scenario_*.py` e liste, em texto corrido (não precisa
implementar ainda), todos os `TODO` que encontrar no código — eles marcam
decisões que dependem de mim (dono do negócio) ou de testes reais com o
agregador bancário.

**2. Ampliar a cobertura de testes**
O `test_dry_run.py` atual cobre os Cenários 1, 2, 3 e 6. Adicione testes
equivalentes para os Cenários 4 (relatório semanal), 5 (análise Claude —
pode usar o stub) e 7 (Real vs Orçado), seguindo o mesmo padrão de
banco-de-dados-em-memória já estabelecido no arquivo. Cubra pelo menos um
caso de borda por cenário (ex: Cenário 7 com desvio > 10% deve gerar
alerta; Cenário 7 com desvio pequeno não deve).

**3. Robustez do matching (Cenário 1)**
Hoje, se duas parcelas abertas da MESMA empresa tiverem valor e janela de
vencimento coincidentes, `match_parcela` pega a primeira que encontrar —
isso pode causar um match errado silencioso. Implemente um destes dois
comportamentos (me pergunte qual eu prefiro antes de escolher):
  (a) se houver mais de um candidato válido, não casa automaticamente —
      vira "ambígua" e cai na fila de revisão manual via WhatsApp; ou
  (b) desempata pelo vencimento mais próximo da data da transação.
Adicione teste cobrindo esse caso.

**4. Tratamento de erros de rede**
`aggregator.py`, `sheets.py` e `whatsapp.py` fazem chamadas HTTP sem retry
nem timeout explícito. Adicione timeout (ex: 15s) em todas as chamadas
`requests.*` e um retry simples (2 tentativas, backoff de 2s) para erros
5xx/timeout. Não precisa de biblioteca nova — pode ser um decorator simples.

**5. Logging estruturado**
Troque os `print()` espalhados pelos cenários por um logger Python padrão
(`logging`), com um arquivo de log rotativo em `logs/sistema.log`. Mantenha
os `print()` do `test_dry_run.py` como estão (é output de teste, não de
produção).

**6. Validar `.env.example` × `config.py`**
Confira se toda variável referenciada em `config.py` e nos módulos `src/`
está documentada no `.env.example` com um comentário explicando de onde
vem o valor (ex: qual tela do Pluggy/Belvo). Se faltar alguma, adicione.

### Não faça (ainda)
- Não troque Google Sheets por outro banco de dados — está fora de escopo
  até a Fase 3.
- Não implemente de fato a chamada ao Pluggy/Belvo além do que já existe —
  isso depende de credenciais reais que ainda não tenho (Semana 0).
- Não mude a regra de comissão (contrato assinado) nem a estrutura das 6
  contas sem eu confirmar antes.

### Ao terminar cada item
Rode `python tests/test_dry_run.py` de novo e me mostre o resultado antes
de passar para o próximo item da lista.
