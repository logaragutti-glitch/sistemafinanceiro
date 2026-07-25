"""CENÁRIO 6 (Sex 17:30) — DRE do mês com impostos (correção 5)."""
from datetime import date
import config
from . import sheets, notificar
from .logging_config import get_logger

logger = get_logger(__name__)


def run():
    mes = date.today().strftime("%Y-%m")
    for slug, emp in config.EMPRESAS.items():
        receita = sum(float(str(r["Valor"]).replace(",", "."))
                      for r in sheets.ler(emp["aba_receb"])
                      if str(r.get("Data Receb", "")).startswith(mes))
        despesas = sum(float(str(r["Valor"]).replace(",", "."))
                       for r in sheets.ler(emp["aba_desp"])
                       if str(r.get("Data", "")).startswith(mes))
        comissoes = sum(float(str(r.get("Líquido", 0)).replace(",", "."))
                        for r in sheets.ler(emp["aba_com"])
                        if str(r.get("Semana", "")).startswith(mes))
        fixos = sum(float(str(r["Valor"]).replace(",", "."))
                    for r in sheets.ler(config.ABA_CUSTOS_FIXOS)
                    if r.get("Empresa") == emp["nome"])
        impostos = receita * emp["aliquota_simples"]
        liquida = receita - impostos
        contrib = liquida - despesas - comissoes
        lucro = contrib - fixos
        margem = lucro / receita * 100 if receita else 0
        sheets.inserir(config.ABA_DRE, {
            "Mês": mes, "Empresa": emp["nome"],
            "Receita Bruta": round(receita, 2),
            "Impostos": round(impostos, 2),
            "Receita Líquida": round(liquida, 2),
            "Custos Variáveis": round(despesas, 2),
            "Comissões": round(comissoes, 2),
            "Margem Contribuição": round(contrib, 2),
            "Custos Fixos": round(fixos, 2),
            "Lucro Operacional": round(lucro, 2),
            "Margem %": round(margem, 1)})
        notificar.enviar_gestor(
            f"📋 DRE {mes} — {emp['nome']}",
            f"📋 DRE {mes} — {emp['nome']}\n"
            f"Receita bruta: R$ {receita:,.2f}\n"
            f"(-) Impostos ({emp['aliquota_simples']*100:.1f}%): R$ {impostos:,.2f}\n"
            f"(-) Variáveis: R$ {despesas:,.2f}\n"
            f"(-) Comissões: R$ {comissoes:,.2f}\n"
            f"(-) Fixos: R$ {fixos:,.2f}\n"
            f"Lucro: R$ {lucro:,.2f} ({margem:.1f}%)")
    logger.info("Cenário 6 concluído")


if __name__ == "__main__":
    run()
