"""Camada única de notificação — manda por WhatsApp E e-mail ao mesmo tempo.

Cada canal é tentado independente: se um falhar (ex: token do WhatsApp
expirado), o outro ainda é tentado e a falha só é logada, não interrompe o
cenário. WhatsApp não tem campo de assunto separado — usa só o corpo.
"""
from . import whatsapp, email_sender
from .logging_config import get_logger

logger = get_logger(__name__)


def enviar_gestor(assunto, corpo):
    try:
        whatsapp.enviar_gestor(corpo)
    except Exception:
        logger.exception("Falha ao enviar WhatsApp pro gestor (assunto: %s)", assunto)
    try:
        email_sender.enviar_gestor(assunto, corpo)
    except Exception:
        logger.exception("Falha ao enviar e-mail pro gestor (assunto: %s)", assunto)


def enviar(fone, email_dest, assunto, corpo):
    try:
        whatsapp.enviar(fone, corpo)
    except Exception:
        logger.exception("Falha ao enviar WhatsApp pra %s (assunto: %s)", fone, assunto)
    try:
        email_sender.enviar(email_dest, assunto, corpo)
    except Exception:
        logger.exception("Falha ao enviar e-mail pra %s (assunto: %s)", email_dest, assunto)
