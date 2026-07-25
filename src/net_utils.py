"""Utilidades de rede compartilhadas: timeout padrão e retry simples.

HTTP_TIMEOUT deve ser passado em toda chamada requests.* do projeto.
com_retry() cobre timeout/erro de conexão e HTTP 5xx (não repete 4xx,
que é erro do próprio request, não vai se resolver tentando de novo).
"""
import time
import requests

HTTP_TIMEOUT = 15  # segundos


def _status_5xx(exc):
    resp = getattr(exc, "response", None)
    status = getattr(resp, "status_code", None)
    return status is not None and 500 <= status < 600


def com_retry(tentativas=2, backoff=2, exceptions=()):
    """Repete a função em caso de timeout, erro de conexão ou HTTP 5xx.
    Não repete erros 4xx (client error) nem outras exceções — essas
    provavelmente não se resolvem tentando de novo.

    `exceptions`: tupla extra de tipos sempre considerados transitórios
    (ex: erros de SMTP/socket em envio de e-mail, que não têm `.response`
    HTTP pra checar 5xx)."""
    def decorator(fn):
        def wrapper(*args, **kwargs):
            ultimo_erro = None
            for tentativa in range(1, tentativas + 1):
                try:
                    return fn(*args, **kwargs)
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    ultimo_erro = e
                except requests.exceptions.HTTPError as e:
                    if not _status_5xx(e):
                        raise
                    ultimo_erro = e
                except exceptions as e:
                    ultimo_erro = e
                except Exception as e:
                    # cobre erros de bibliotecas de terceiros (ex: gspread.exceptions.APIError)
                    # que carregam um `.response` com status HTTP, sem depender delas diretamente
                    if not _status_5xx(e):
                        raise
                    ultimo_erro = e
                if tentativa < tentativas:
                    time.sleep(backoff)
            raise ultimo_erro
        return wrapper
    return decorator
