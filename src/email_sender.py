"""Envio de e-mail via SMTP (Gmail/Outlook com senha de app) — substitui o
WhatsApp Business Cloud API como canal de notificação do sistema.

Variáveis no .env: EMAIL_REMETENTE, EMAIL_SENHA_APP, EMAIL_SMTP_HOST
(padrão smtp.gmail.com), EMAIL_SMTP_PORT (padrão 587), GESTOR_EMAIL.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from .net_utils import com_retry
from .logging_config import get_logger

logger = get_logger(__name__)
load_dotenv()

_ERROS_TRANSITORIOS = (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected,
                        smtplib.SMTPHeloError, TimeoutError, ConnectionError)


@com_retry(exceptions=_ERROS_TRANSITORIOS)
def enviar(destinatario, assunto, corpo):
    """Envia e-mail. Se `destinatario` estiver vazio (ex: cliente sem e-mail
    cadastrado em Contas_a_Receber), só loga um aviso e não tenta enviar."""
    if not destinatario:
        logger.warning("Sem destinatário pro e-mail '%s' — pulando envio", assunto)
        return None
    remetente = os.getenv("EMAIL_REMETENTE")
    msg = MIMEMultipart()
    msg["From"] = remetente
    msg["To"] = destinatario
    msg["Subject"] = assunto
    msg.attach(MIMEText(corpo, "plain", "utf-8"))

    host = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=15) as servidor:
        servidor.starttls()
        servidor.login(remetente, os.getenv("EMAIL_SENHA_APP"))
        servidor.sendmail(remetente, destinatario, msg.as_string())
    return {"enviado": True}


def enviar_gestor(assunto, corpo):
    return enviar(os.getenv("GESTOR_EMAIL"), assunto, corpo)
