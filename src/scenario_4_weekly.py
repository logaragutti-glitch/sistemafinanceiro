"""CENÁRIO 4 (Sex 17:00) — Relatório executivo semanal."""
from datetime import date, timedelta
import config
from . import sheets, notificar
from .logging_config import get_logger

logger = get_logger(__name__)


def _soma_semana(aba, col_data, col_valor, seg, hoje):
    total = 0.0
    for r in sheets.ler(aba):
        d = str(r.get(col_data, ""))
        if seg.isoformat() <= d <= hoje.isoformat():
            try:
                total += float(str(r[col_valor]).replace(",", "."))
            except (ValueError, KeyError):
                pass
    return total


def run():
    hoje = date.today()
    seg = hoje - timedelta(days=hoje.weekday())
    blocos = []
    total_geral = 0.0
    for slug, emp in config.EMPRESAS.items():
        rec = _soma_semana(emp["aba_receb"], "Data Receb", "Valor", seg, hoje)
        desp = _soma_semana(emp["aba_desp"], "Data", "Valor", seg, hoje)
        margem = (rec - desp) / rec * 100 if rec else 0
        total_geral += rec
        blocos.append(f"*{emp['nome']}*\nReceita: R$ {rec:,.2f}\n"
                      f"Despesas: R$ {desp:,.2f}\nMargem: {margem:.1f}%")
    notificar.enviar_gestor(
        f"📈 Relatório semanal ({seg.strftime('%d/%m')}–{hoje.strftime('%d/%m')})",
        f"📈 RELATÓRIO SEMANAL ({seg.strftime('%d/%m')}–{hoje.strftime('%d/%m')})\n\n"
        + "\n\n".join(blocos) + f"\n\nTOTAL: R$ {total_geral:,.2f}")
    logger.info("Cenário 4 concluído")


if __name__ == "__main__":
    run()
