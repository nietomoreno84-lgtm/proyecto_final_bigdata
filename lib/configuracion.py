"""Carga segura de la configuración local desde variables de entorno."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ_PROYECTO / ".env")


def _entero_entorno(nombre: str, predeterminado: int) -> int:
    """Lee una variable entera y devuelve un error claro si no es válida."""
    valor = os.getenv(nombre, str(predeterminado))
    try:
        return int(valor)
    except ValueError as error:
        raise ValueError(f"{nombre} debe contener un número entero.") from error


CONFIG_BD: dict[str, object] = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": _entero_entorno("MYSQL_PORT", 3306),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "videojuego_seed42"),
}

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "").strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
