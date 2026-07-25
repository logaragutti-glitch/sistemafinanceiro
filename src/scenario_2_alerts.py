"""CENÁRIO 2 (08:00) — Alertas diários + inadimplência + régua de cobrança."""
from datetime import date, datetime, timedelta
import config
from . import sheets, notificar
from .logging_config import get_logger

logger = get_logger(__name__)


def run():
    hoje = date.today()
    ontem = (hoje - timedelta(days=1)).isoformat()
    cr = sheets.ler(config.ABA_CONTAS_RECEBER)

    # 1) marca atrasadas
    for p in cr:
        if p.get("Status") == "Aberto":
            try:
                venc = datetime.strptime(str(p["Vencimento"]), "%Y-%m-%d").date()
            except ValueError:
                continue
            if venc < hoje:
                sheets.atualizar(config.ABA_CONTAS_RECEBER,
                    {"ID Contrato": p["ID Contrato"], "Parcela": p["Parcela"]},
                    {"Status": "Atrasado"})
                p["Status"] = "Atrasado"

    # 2) resumo por empresa
    blocos = []
    for slug, emp in config.EMPRESAS.items():
        recebido = sum(float(str(r["Valor"]).replace(",", "."))
                       for r in sheets.ler(emp["aba_receb"])
                       if str(r.get("Data Receb")) == ontem)
        atrasado = sum(float(str(p["Valor Parcela"]).replace(",", "."))
                       for p in cr if p.get("Empresa") == emp["nome"]
                       and p.get("Status") == "Atrasado")
        blocos.append(f"*{emp['nome']}*\nRecebido ontem: R$ {recebido:,.2f}\n"
                      f"Em atraso: R$ {atrasado:,.2f}")
    notificar.enviar_gestor("📊 Resumo diário", "📊 Resumo diário\n\n" + "\n\n".join(blocos))

    # 3) régua de cobrança (D-3 lembrete, D+1/D+7/D+10 cobrança)
    for p in cr:
        fone = str(p.get("Fone Cliente") or "")
        email = str(p.get("Email Cliente") or "")
        if p.get("Status") not in ("Aberto", "Atrasado") or not (fone or email):
            continue
        try:
            venc = datetime.strptime(str(p["Vencimento"]), "%Y-%m-%d").date()
        except ValueError:
            continue
        delta = (hoje - venc).days
        if -delta == 3:   # 3 dias antes
            notificar.enviar(fone, email, f"Lembrete: parcela vence em {p['Vencimento']}",
                f"Olá {p['Cliente']}! Lembrete: parcela de R$ {p['Valor Parcela']} "
                f"do evento {p['Evento']} vence em {p['Vencimento']}. 😊")
        elif delta in (1, 7, 10):
            notificar.enviar(fone, email, f"Parcela em aberto — evento {p['Evento']}",
                f"Olá {p['Cliente']}, não identificamos o pagamento da parcela de "
                f"R$ {p['Valor Parcela']} ({p['Evento']}), vencida em "
                f"{p['Vencimento']}. Pode verificar? Qualquer dúvida, estamos aqui.")
    logger.info("Cenário 2 concluído")


if __name__ == "__main__":
    run()
