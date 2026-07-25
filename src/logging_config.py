"""Logging estruturado — arquivo rotativo em logs/sistema.log + console."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

_configurado = False


def configurar():
    global _configurado
    if _configurado:
        return
    LOG_DIR.mkdir(exist_ok=True)
    raiz = logging.getLogger("sistema_financeiro")
    raiz.setLevel(logging.INFO)
    formato = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    arquivo = RotatingFileHandler(LOG_DIR / "sistema.log", maxBytes=5 * 1024 * 1024,
                                   backupCount=5, encoding="utf-8")
    arquivo.setFormatter(formato)
    raiz.addHandler(arquivo)

    console = logging.StreamHandler()
    console.setFormatter(formato)
    raiz.addHandler(console)

    _configurado = True


def get_logger(nome):
    configurar()
    return logging.getLogger(f"sistema_financeiro.{nome}")
