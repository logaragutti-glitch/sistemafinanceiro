"""Sincroniza extratos enviados pelo painel para a pasta local do agregador."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from google.oauth2.service_account import Credentials

import config
from src.drive_uploads import ensure_folder, list_files, service, sync_extratos

SCOPES = ["https://www.googleapis.com/auth/drive"]


def credenciais():
    caminho = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    return Credentials.from_service_account_file(caminho, scopes=SCOPES)


def main() -> int:
    destino = Path(os.getenv("EXTRATOS_DIR", "extratos"))
    drive = service(credenciais())
    pasta_id = os.getenv("DRIVE_UPLOADS_FOLDER_ID") or None
    arquivos = list_files(drive, pasta_id)
    baixados = sync_extratos(drive, arquivos, destino, set(config.CONTAS_BANCARIAS))
    print(f"OK: {len(baixados)} extrato(s) sincronizado(s) em {destino}")
    for nome in baixados:
        print(f"- {nome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
