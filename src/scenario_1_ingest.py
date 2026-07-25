"""CENÁRIO 1 (06:00) — Ingestão + match com Contas_a_Receber.

Fluxo V2:
1. Puxa transações 24h das 3 contas
2. CRÉDITO: identifica empresa pela CHAVE PIX (correção 1);
   fallback: match por valor+janela em Contas_a_Receber
3. Match parcela aberta (±R$1, vencimento ±7d) -> baixa (Pago)
4. Sem match -> transação órfã -> WhatsApp gestor
5. DÉBITO: categoriza por keywords -> aba Despesas
"""
from datetime import date, datetime
import config
from . import aggregator, sheets, notificar
from .logging_config import get_logger

logger = get_logger(__name__)

CATEGORIAS = {
    "Decoração": ["FLOR", "BEXIGA", "BALAO", "DECOR"],
    "Utilidades": ["LUZ", "ENEL", "AGUA", "PROLAGOS", "GAS", "INTERNET"],
    "Fornecedores": ["SUPERMERCADO", "ATACAD", "BEBIDA", "BUFFET"],
    "Limpeza": ["LIMP", "HIGIENE"],
}


def empresa_por_pix(tx):
    for slug, emp in config.EMPRESAS.items():
        if tx["pix_key_destino"] and tx["pix_key_destino"] in emp["pix_keys"]:
            return slug
    return None


def candidatos_parcela(tx, abertas):
    """Todas as parcelas abertas com valor ±tolerância e vencimento dentro da janela."""
    dt_tx = datetime.strptime(tx["data"], "%Y-%m-%d").date()
    candidatos = []
    for p in abertas:
        try:
            valor = float(str(p["Valor Parcela"]).replace(",", "."))
            venc = datetime.strptime(str(p["Vencimento"]), "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue
        if (abs(valor - tx["valor"]) <= config.MATCH_TOLERANCIA_VALOR
                and abs((venc - dt_tx).days) <= config.MATCH_JANELA_DIAS):
            candidatos.append(p)
    return candidatos


def match_parcela(tx, abertas):
    """Retorna (parcela, ambigua). `parcela` é None se não achou nenhuma ou se
    houver mais de uma candidata válida — nesse caso não casamos automaticamente
    (decisão do gestor: evitar baixa errada silenciosa) e `ambigua` vem True,
    para a transação cair na fila de revisão manual via WhatsApp."""
    candidatos = candidatos_parcela(tx, abertas)
    if len(candidatos) == 1:
        return candidatos[0], False
    if len(candidatos) > 1:
        return None, True
    return None, False


def categorizar(descricao):
    d = descricao.upper()
    for cat, kws in CATEGORIAS.items():
        if any(k in d for k in kws):
            return cat
    return "Outros"


def run():
    txs = aggregator.transacoes_ultimas_24h()
    cr = sheets.ler(config.ABA_CONTAS_RECEBER)
    abertas = [p for p in cr if p.get("Status") in ("Aberto", "Atrasado")]
    orfas = []
    ambiguas = []

    for tx in txs:
        if tx["tipo"] == "CREDITO":
            if tx["valor"] < config.VALOR_MINIMO_RECEBIMENTO:
                continue
            slug = empresa_por_pix(tx)
            if not slug:
                # unidade exclusiva (Park Lagos / Pôr do Sol) -> só 1 empresa possível,
                # não depende de chave Pix
                possiveis = config.UNIDADE_EMPRESAS.get(tx["unidade"], list(config.EMPRESAS))
                if len(possiveis) == 1:
                    slug = possiveis[0]
            candidatas = ([p for p in abertas if p.get("Empresa") ==
                           config.EMPRESAS[slug]["nome"]] if slug else abertas)
            p, ambigua = match_parcela(tx, candidatas)
            if p:
                slug = slug or next(s for s, e in config.EMPRESAS.items()
                                    if e["nome"] == p["Empresa"])
                sheets.atualizar(config.ABA_CONTAS_RECEBER,
                    {"ID Contrato": p["ID Contrato"], "Parcela": p["Parcela"]},
                    {"Status": "Pago", "Data Pagamento": tx["data"],
                     "ID Transação Banco": tx["id"]})
                sheets.inserir(config.EMPRESAS[slug]["aba_receb"], {
                    "Data": tx["data"], "Venue": p.get("Venue", ""),
                    "Evento": p.get("Evento", ""), "Cliente": p.get("Cliente", ""),
                    "Valor": tx["valor"], "Forma Pagto": "Pix",
                    "Status": "Pago", "Data Receb": tx["data"],
                    "Banco": tx["conta_key"]})
                abertas.remove(p)
            elif ambigua:
                ambiguas.append(tx)
            else:
                orfas.append(tx)
        else:  # DEBITO
            # unidade Park Lagos / Pôr do Sol -> venue único, sempre Casa da Árvore
            # unidade Azevedo (Casa + Casarão) -> por padrão vai para Casa;
            #   revise manualmente despesas que sejam do Casarão (não dá p/ saber
            #   pela conta, já que Azevedo é compartilhada entre as 2 empresas)
            slug = "casa_arvore"
            venue = config.UNIDADE_VENUE.get(
                tx["unidade"], config.UNIDADE_VENUE_PRINCIPAL_AZEVEDO)
            sheets.inserir(config.EMPRESAS[slug]["aba_desp"], {
                "Data": tx["data"], "Venue": venue,
                "Descrição": tx["descricao"],
                "Categoria": categorizar(tx["descricao"]),
                "Valor": tx["valor"], "Banco": tx["conta_key"]})

    if orfas:
        linhas = "\n".join(f"• R$ {t['valor']:.2f} — {t['descricao'][:40]} "
                           f"({t['conta_key']}, {t['data']})" for t in orfas)
        notificar.enviar_gestor(
            f"⚠️ {len(orfas)} transação(ões) sem contrato correspondente",
            f"⚠️ {len(orfas)} transação(ões) sem contrato correspondente:\n"
            f"{linhas}\n\nVincule manualmente em Contas_a_Receber.")
    if ambiguas:
        linhas = "\n".join(f"• R$ {t['valor']:.2f} — {t['descricao'][:40]} "
                           f"({t['conta_key']}, {t['data']})" for t in ambiguas)
        notificar.enviar_gestor(
            f"❓ {len(ambiguas)} transação(ões) ambígua(s) — revisar",
            f"❓ {len(ambiguas)} transação(ões) com mais de uma parcela candidata "
            f"(mesmo valor e janela de vencimento) — não casamos automaticamente "
            f"para evitar baixa errada:\n{linhas}\n\n"
            f"Revise manualmente em Contas_a_Receber.")
    logger.info("Cenário 1: %d transações, %d órfãs, %d ambíguas",
                len(txs), len(orfas), len(ambiguas))


if __name__ == "__main__":
    run()
