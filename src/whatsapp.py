"""WhatsApp Business Cloud API — envio de mensagens."""
import os, requests
from dotenv import load_dotenv
from .net_utils import HTTP_TIMEOUT, com_retry

load_dotenv()


@com_retry()
def enviar(fone, texto):
    url = f"https://graph.facebook.com/v19.0/{os.getenv('WHATSAPP_PHONE_ID')}/messages"
    r = requests.post(url,
        headers={"Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}"},
        json={"messaging_product": "whatsapp", "to": fone,
              "type": "text", "text": {"body": texto}}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()


def enviar_gestor(texto):
    return enviar(os.getenv("GESTOR_PHONE"), texto)
