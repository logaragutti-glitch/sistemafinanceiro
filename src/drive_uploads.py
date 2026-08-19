"""Persistência de arquivos enviados pelo painel em uma pasta do Google Drive."""
from __future__ import annotations

import io
import os
from typing import Iterable

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

FOLDER_NAME = "Financeiro Uploads"
FOLDER_MIME = "application/vnd.google-apps.folder"


def service(credentials):
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def ensure_folder(drive, folder_id: str | None = None) -> str:
    if folder_id:
        return folder_id
    query = (
        f"name = '{FOLDER_NAME}' and mimeType = '{FOLDER_MIME}' "
        "and trashed = false"
    )
    encontrados = drive.files().list(q=query, spaces="drive", fields="files(id,name)", pageSize=10).execute().get("files", [])
    if encontrados:
        return encontrados[0]["id"]
    pasta = drive.files().create(
        body={"name": FOLDER_NAME, "mimeType": FOLDER_MIME},
        fields="id,name",
    ).execute()
    return pasta["id"]


def upload_bytes(drive, filename: str, content: bytes, mime_type: str, folder_id: str | None = None) -> dict:
    nome = os.path.basename(filename)
    pasta = ensure_folder(drive, folder_id)
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=False)
    query = f"name = '{nome.replace(chr(39), chr(92) + chr(39))}' and '{pasta}' in parents and trashed = false"
    existentes = drive.files().list(q=query, spaces="drive", fields="files(id,name)", pageSize=10).execute().get("files", [])
    if existentes:
        return drive.files().update(
            fileId=existentes[0]["id"], media_body=media,
            fields="id,name,size,modifiedTime,webViewLink",
        ).execute()
    return drive.files().create(
        body={"name": nome, "parents": [pasta]},
        media_body=media,
        fields="id,name,size,modifiedTime,webViewLink",
    ).execute()


def list_files(drive, folder_id: str | None = None) -> list[dict]:
    pasta = ensure_folder(drive, folder_id)
    query = f"'{pasta}' in parents and trashed = false"
    resposta = drive.files().list(
        q=query, spaces="drive", fields="files(id,name,size,modifiedTime,mimeType)",
        pageSize=100, orderBy="modifiedTime desc",
    ).execute()
    return resposta.get("files", [])


def download_file(drive, file_id: str) -> bytes:
    buffer = io.BytesIO()
    pedido = drive.files().get_media(fileId=file_id)
    downloader = MediaIoBaseDownload(buffer, pedido)
    concluido = False
    while not concluido:
        _, concluido = downloader.next_chunk()
    return buffer.getvalue()


def sync_extratos(drive, arquivos: Iterable[dict], destino, contas_validas: set[str]) -> list[str]:
    """Baixa apenas OFX/XLSX com nome de conta conhecido para `destino`."""
    destino.mkdir(parents=True, exist_ok=True)
    baixados = []
    for arquivo in arquivos:
        nome = str(arquivo.get("name") or "")
        base, extensao = os.path.splitext(nome)
        if base.upper() not in contas_validas or extensao.lower() not in (".ofx", ".xlsx"):
            continue
        (destino / f"{base.upper()}{extensao.lower()}").write_bytes(download_file(drive, arquivo["id"]))
        baixados.append(nome)
    return baixados


__all__ = ["service", "ensure_folder", "upload_bytes", "list_files", "download_file", "sync_extratos"]
