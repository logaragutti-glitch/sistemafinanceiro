"""Parâmetros do negócio — edite aqui, não no código dos cenários.

ESTRUTURA REAL (corrigida): 6 contas bancárias em 3 bancos, agrupadas em
3 unidades. "Azevedo" é a unidade que recebe Casa da Árvore E Casarão
(por isso precisa das chaves Pix separadas — correção 1 da Arquitetura V2).
"""

CONTAS_BANCARIAS = {
    # unidade "Azevedo": 3 contas, recebe Casa da Árvore + Casarão
    "AZEVEDO_SICOOB": {"banco": "Sicoob", "agencia": "3003",
                        "conta": "224.754-8", "unidade": "azevedo"},
    "AZEVEDO_CAIXA":  {"banco": "Caixa", "agencia": "0179",
                        "conta": "578544606-1", "unidade": "azevedo"},
    "AZEVEDO_ITAU":   {"banco": "Itaú", "agencia": "8595",
                        "conta": "0043484-9", "unidade": "azevedo"},
    # unidade Park Lagos: 2 contas
    "PARKLAGOS_CAIXA": {"banco": "Caixa", "agencia": "0179",
                         "conta": "578544626-6", "unidade": "park_lagos"},
    "PARKLAGOS_ITAU":  {"banco": "Itaú", "agencia": "8595",
                         "conta": "0044452-5", "unidade": "park_lagos"},
    # unidade Pôr do Sol: 1 conta
    "PORDOSOL_CAIXA": {"banco": "Caixa", "agencia": "0179",
                        "conta": "579343304-6", "unidade": "por_do_sol"},
}

# TODO Semana 0: para cada conta acima, criar o "link"/"item" no agregador
# (Pluggy/Belvo) e colar o link_id no .env. Bancos com mesma agência entre
# unidades (ex: Caixa 0179 em Azevedo/Park Lagos/Pôr do Sol) podem ou não
# usar o MESMO login — confirme no teste se 1 conexão já retorna as 3 contas
# ou se são necessárias 3 autorizações distintas.
LINK_ID_ENV_VAR = {
    "AZEVEDO_SICOOB": "LINK_AZEVEDO_SICOOB",
    "AZEVEDO_CAIXA": "LINK_AZEVEDO_CAIXA",
    "AZEVEDO_ITAU": "LINK_AZEVEDO_ITAU",
    "PARKLAGOS_CAIXA": "LINK_PARKLAGOS_CAIXA",
    "PARKLAGOS_ITAU": "LINK_PARKLAGOS_ITAU",
    "PORDOSOL_CAIXA": "LINK_PORDOSOL_CAIXA",
}

EMPRESAS = {
    "casa_arvore": {
        "nome": "Casa da Árvore",
        "pix_keys": ["19431800000195"],  # CNPJ 19.431.800/0001-95 (recebe via contas Azevedo)
        "unidades": ["azevedo", "park_lagos", "por_do_sol"],
        "aba_receb": "Recebimentos_CasaArvore",
        "aba_desp": "Despesas_CasaArvore",
        "aba_com": "Comissoes_CasaArvore",
        "aliquota_simples": 0.10,
    },
    "casarao": {
        "nome": "Casarão Festas",
        "pix_keys": ["formaturacasadaarvore@gmail.com"],  # chave e-mail, recebe via AZEVEDO_ITAU
        "unidades": ["azevedo"],
        "aba_receb": "Recebimentos_Casarao",
        "aba_desp": "Despesas_Casarao",
        "aba_com": "Comissoes_Casarao",
        "aliquota_simples": 0.10,
    },
}

# unidade -> venue (para contas exclusivas de um venue, identifica sem precisar de tag)
UNIDADE_VENUE = {
    "park_lagos": "Park Lagos",
    "por_do_sol": "Pôr do Sol",
    # "azevedo" NÃO tem venue único: pode ser Venue Principal (Casa) ou Casarão
    # -> ali sim depende da chave Pix (correção 1) ou match em Contas_a_Receber
}
UNIDADE_VENUE_PRINCIPAL_AZEVEDO = "Venue Principal"  # default p/ despesas em Azevedo

# unidade -> lista de empresas que podem receber ali. Quando a lista tem 1 item,
# o Cenário 1 identifica a empresa direto pela conta, sem precisar de chave Pix.
UNIDADE_EMPRESAS = {
    "azevedo": ["casa_arvore", "casarao"],   # ambíguo -> precisa da chave Pix
    "park_lagos": ["casa_arvore"],           # não ambíguo
    "por_do_sol": ["casa_arvore"],           # não ambíguo
}

VENDEDORES = {
    # nome: {telefone, e-mail, percentual, empresa} — comissão avisada por
    # WhatsApp E e-mail. TODO: e-mails abaixo são placeholder, confirmar os reais.
    "João":  {"fone": "5522988880001", "email": "joao@example.com", "pct": 0.10, "empresa": "casa_arvore"},
    "Maria": {"fone": "5522988880002", "email": "maria@example.com", "pct": 0.10, "empresa": "casa_arvore"},
    "Pedro": {"fone": "5522988880003", "email": "pedro@example.com", "pct": 0.10, "empresa": "casa_arvore"},
    "Ana":   {"fone": "5522988880004", "email": "ana@example.com", "pct": 0.06, "empresa": "casarao"},
    "Bruno": {"fone": "5522988880005", "email": "bruno@example.com", "pct": 0.06, "empresa": "casarao"},
}

# Regra de comissão: contrato ASSINADO (decisão do gestor) com estorno se cancelar
COMISSAO_SOBRE = "assinatura"

# Matching transação x parcela
MATCH_TOLERANCIA_VALOR = 1.00     # ±R$1
MATCH_JANELA_DIAS = 7             # vencimento ±7 dias
VALOR_MINIMO_RECEBIMENTO = 500    # ignora créditos menores

# Régua de cobrança (dias relativos ao vencimento)
REGUA_COBRANCA = [-3, 1, 7, 10]

ABA_CONTAS_RECEBER = "Contas_a_Receber"
ABA_CUSTOS_FIXOS = "Custos_Fixos"
ABA_DRE = "DRE_Automatico"
ABA_REAL_ORCADO = "RealVsOrcado"
# Meta mensal por empresa: colunas "Empresa" | "Meta Mensal". Antes vivia
# hardcoded em scenario_7_budget.py; mudar a meta agora é editar a planilha,
# não o código.
ABA_METAS = "Metas_Mensais"
