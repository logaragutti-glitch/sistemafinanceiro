"""Agendador principal — substitui o Make (economia R$200/mês).

Rode em VPS/Raspberry: `python main.py`
Ou desative e use cron/GitHub Actions chamando cada cenário.
"""
import time
import schedule
from src import (scenario_1_ingest, scenario_2_alerts, scenario_3_commissions,
                 scenario_4_weekly, scenario_5_analysis, scenario_6_dre,
                 scenario_7_budget)
from src.logging_config import get_logger

logger = get_logger("main")


def seguro(fn, nome):
    def wrapper():
        try:
            fn()
        except Exception as e:
            logger.exception("Falha no %s", nome)
            try:
                from src import notificar
                notificar.enviar_gestor(f"❌ Falha no {nome}", f"❌ Falha no {nome}: {e}")
            except Exception:
                pass
    return wrapper


schedule.every().day.at("06:00").do(seguro(scenario_1_ingest.run, "Cenário 1"))
schedule.every().day.at("08:00").do(seguro(scenario_2_alerts.run, "Cenário 2"))
schedule.every().day.at("08:15").do(seguro(scenario_7_budget.run, "Cenário 7"))
schedule.every().day.at("08:30").do(seguro(scenario_5_analysis.run, "Cenário 5"))
schedule.every().friday.at("17:00").do(seguro(scenario_4_weekly.run, "Cenário 4"))
schedule.every().friday.at("17:30").do(seguro(scenario_6_dre.run, "Cenário 6"))
schedule.every().friday.at("18:00").do(seguro(scenario_3_commissions.run, "Cenário 3"))

if __name__ == "__main__":
    logger.info("Sistema financeiro rodando. Ctrl+C para parar.")
    while True:
        schedule.run_pending()
        time.sleep(30)
