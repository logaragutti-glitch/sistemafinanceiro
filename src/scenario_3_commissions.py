"""CENÁRIO 3 (Sex 18:00) — Comissões sobre CONTRATO ASSINADO + estorno.

Regra definida pelo gestor: comissão = valor TOTAL do contrato × %,
gerada na semana da assinatura (Parcela 1/N evita duplicar).
Cancelamento -> lançamento negativo na semana seguinte.
"""
from datetime import date, datetime, timedelta
from collections import defaultdict
import config
from . import sheets, notificar
from .logging_config import get_logger

logger = get_logger(__name__)


def run():
    hoje = date.today()
    seg = hoje - timedelta(days=hoje.weekday())  # segunda desta semana
    cr = sheets.ler(config.ABA_CONTAS_RECEBER)
    por_vendedor = defaultdict(lambda: {"contratos": 0, "base": 0.0})
    estornos = defaultdict(float)

    for p in cr:
        parcela = str(p.get("Parcela", ""))
        if not parcela.startswith("1/"):
            continue  # 1 lançamento por contrato
        try:
            assin = datetime.strptime(str(p["Data Assinatura"]), "%Y-%m-%d").date()
            total = float(str(p["Valor Total"]).replace(",", "."))
        except (ValueError, KeyError):
            continue
        vend = p.get("Vendedor", "")
        if vend not in config.VENDEDORES:
            continue
        if seg <= assin <= hoje and p.get("Status") != "Cancelado":
            por_vendedor[vend]["contratos"] += 1
            por_vendedor[vend]["base"] += total
        # estorno: cancelado nesta semana (campo Data Cancelamento)
        try:
            canc = datetime.strptime(str(p.get("Data Cancelamento", "")),
                                     "%Y-%m-%d").date()
            if seg <= canc <= hoje:
                estornos[vend] += total
        except ValueError:
            pass

    for vend, dados in por_vendedor.items():
        v = config.VENDEDORES[vend]
        emp = config.EMPRESAS[v["empresa"]]
        comissao = dados["base"] * v["pct"]
        estorno = estornos.pop(vend, 0.0) * v["pct"]
        liquido = comissao - estorno
        sheets.inserir(emp["aba_com"], {
            "Vendedor": vend, "Semana": seg.isoformat(),
            "Contratos": dados["contratos"], "Base": dados["base"],
            "Comissão": round(comissao, 2), "Estorno": round(estorno, 2),
            "Líquido": round(liquido, 2), "%": v["pct"], "Status": "A Pagar"})
        msg = (f"💰 {vend}: {dados['contratos']} contrato(s) assinado(s) = "
               f"R$ {dados['base']:,.2f}\nComissão ({v['pct']*100:.0f}%): "
               f"R$ {comissao:,.2f}")
        if estorno:
            msg += f"\nEstorno cancelamentos: -R$ {estorno:,.2f}\nLíquido: R$ {liquido:,.2f}"
        notificar.enviar(v["fone"], v["email"], f"Comissão da semana — {vend}", msg)

    # estornos de quem não vendeu nada na semana
    for vend, base in estornos.items():
        v = config.VENDEDORES[vend]
        emp = config.EMPRESAS[v["empresa"]]
        est = base * v["pct"]
        sheets.inserir(emp["aba_com"], {
            "Vendedor": vend, "Semana": seg.isoformat(), "Contratos": 0,
            "Base": 0, "Comissão": 0, "Estorno": round(est, 2),
            "Líquido": round(-est, 2), "%": v["pct"], "Status": "A Descontar"})
        notificar.enviar(v["fone"], v["email"], f"Estorno de comissão — {vend}",
            f"⚠️ {vend}: estorno de R$ {est:,.2f} por cancelamento de contrato. "
            f"Será descontado da próxima comissão.")
    logger.info("Cenário 3 concluído")


if __name__ == "__main__":
    run()
