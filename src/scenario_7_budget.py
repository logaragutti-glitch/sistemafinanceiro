"""CENÁRIO 7 (08:15) — Real vs Orçado (projeção honesta, correção 6).

Projeção = pago no mês + parcelas assinadas a vencer no mês.
Alerta se desvio > 10% da meta.
"""
from datetime import date
import config
from . import sheets, notificar
from .logging_config import get_logger

logger = get_logger(__name__)


def metas_mensais():
    """Lê a meta mensal de cada empresa da aba Metas_Mensais (linha:
    Empresa | Meta Mensal). Fica na planilha para o gestor poder ajustar
    a meta sem mexer em código."""
    metas = {}
    for r in sheets.ler(config.ABA_METAS):
        slug = next((s for s, e in config.EMPRESAS.items()
                     if e["nome"] == r.get("Empresa")), None)
        if slug is None:
            continue
        try:
            metas[slug] = float(str(r["Meta Mensal"]).replace(",", "."))
        except (ValueError, KeyError):
            continue
    return metas


def run():
    mes = date.today().strftime("%Y-%m")
    cr = sheets.ler(config.ABA_CONTAS_RECEBER)
    metas = metas_mensais()
    alertas = []
    for slug, emp in config.EMPRESAS.items():
        if slug not in metas:
            logger.warning("Meta mensal não configurada para %s na aba %s — "
                            "pulando cálculo de Real vs Orçado", emp["nome"], config.ABA_METAS)
            continue
        pago = sum(float(str(p["Valor Parcela"]).replace(",", "."))
                   for p in cr if p.get("Empresa") == emp["nome"]
                   and p.get("Status") == "Pago"
                   and str(p.get("Data Pagamento", "")).startswith(mes))
        a_vencer = sum(float(str(p["Valor Parcela"]).replace(",", "."))
                       for p in cr if p.get("Empresa") == emp["nome"]
                       and p.get("Status") in ("Aberto", "Atrasado")
                       and str(p.get("Vencimento", "")).startswith(mes))
        projecao = pago + a_vencer * 0.9  # desconta 10% inadimplência esperada
        meta = metas[slug]
        desvio = (projecao - meta) / meta * 100
        sheets.inserir(config.ABA_REAL_ORCADO, {
            "Data": date.today().isoformat(), "Empresa": emp["nome"],
            "Meta": meta, "Pago": round(pago, 2),
            "A Vencer": round(a_vencer, 2), "Projeção": round(projecao, 2),
            "Desvio %": round(desvio, 1)})
        if abs(desvio) > 10:
            alertas.append(f"{'🔴' if desvio < 0 else '🟢'} {emp['nome']}: "
                           f"projeção R$ {projecao:,.0f} vs meta R$ {meta:,.0f} "
                           f"({desvio:+.0f}%)")
    if alertas:
        notificar.enviar_gestor("🎯 Real vs Orçado", "🎯 Real vs Orçado\n\n" + "\n".join(alertas))
    logger.info("Cenário 7 concluído")


if __name__ == "__main__":
    run()
