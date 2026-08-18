"""Executa um cenário individual uma única vez.

Uso:
    python -m scripts.run_once --cenario 1
    python -m scripts.run_once --cenario 7

O comando não altera a agenda do ``main.py``. Ele é destinado a validação,
operação assistida e diagnóstico em produção.
"""
from __future__ import annotations

import argparse
import importlib
import logging
import sys
from pathlib import Path

# Permite executar o módulo a partir da raiz ou de qualquer diretório.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CENARIOS = {
    1: ("Ingestão bancária", "src.scenario_1_ingest"),
    2: ("Alertas e cobrança", "src.scenario_2_alerts"),
    3: ("Comissões", "src.scenario_3_commissions"),
    4: ("Relatório semanal", "src.scenario_4_weekly"),
    5: ("Análise diária", "src.scenario_5_analysis"),
    6: ("DRE", "src.scenario_6_dre"),
    7: ("Real vs Orçado", "src.scenario_7_budget"),
}


def executar(numero: int) -> None:
    nome, modulo_nome = CENARIOS[numero]
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("run_once")
    logger.info("Iniciando Cenário %d — %s", numero, nome)

    modulo = importlib.import_module(modulo_nome)
    modulo.run()
    logger.info("Cenário %d concluído", numero)


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa um cenário financeiro uma vez.")
    parser.add_argument(
        "--cenario",
        type=int,
        required=True,
        choices=sorted(CENARIOS),
        help="Número do cenário (1 a 7).",
    )
    args = parser.parse_args()
    executar(args.cenario)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["CENARIOS", "executar", "main"]
