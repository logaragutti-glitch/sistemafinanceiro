"""CENÁRIO 5 (08:30) — Análise diária com Claude (insights acionáveis)."""
from datetime import date, timedelta
import config
from . import sheets, notificar, claude_ai
from .logging_config import get_logger

logger = get_logger(__name__)


def run():
    hoje = date.today()
    ontem = (hoje - timedelta(days=1)).isoformat()
    dados = []
    cr = sheets.ler(config.ABA_CONTAS_RECEBER)
    for slug, emp in config.EMPRESAS.items():
        rec_ontem = sum(float(str(r["Valor"]).replace(",", "."))
                        for r in sheets.ler(emp["aba_receb"])
                        if str(r.get("Data Receb")) == ontem)
        a_vencer_mes = sum(float(str(p["Valor Parcela"]).replace(",", "."))
                           for p in cr if p.get("Empresa") == emp["nome"]
                           and p.get("Status") == "Aberto"
                           and str(p.get("Vencimento", "")).startswith(hoje.strftime("%Y-%m")))
        atrasado = sum(float(str(p["Valor Parcela"]).replace(",", "."))
                       for p in cr if p.get("Empresa") == emp["nome"]
                       and p.get("Status") == "Atrasado")
        dados.append(f"{emp['nome']}: recebido ontem R${rec_ontem:.0f}; "
                     f"a vencer no mês R${a_vencer_mes:.0f}; em atraso R${atrasado:.0f}")

    insight = claude_ai.analisar(
        "Você é analista financeiro de duas empresas de eventos em Cabo Frio.\n"
        f"Dados de hoje:\n" + "\n".join(dados) +
        "\n\nGere no máximo 3 insights acionáveis e 1 recomendação prática "
        "para os próximos 3 dias. Seja direto, formato WhatsApp, sem introdução.")
    notificar.enviar_gestor("🤖 Análise do dia", f"🤖 Análise do dia\n\n{insight}")
    logger.info("Cenário 5 concluído")


if __name__ == "__main__":
    run()
