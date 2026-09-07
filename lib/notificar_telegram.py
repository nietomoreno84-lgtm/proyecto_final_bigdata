"""Envío opcional del resumen directamente a Telegram."""

from __future__ import annotations

import requests

from lib.carga_mysql import obtener_conexion
from lib.configuracion import CONFIG_BD, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from lib.notificar_n8n import consultar_resumen_partidas
from lib.resumen import registrar


def construir_mensaje(resumen: dict[str, object]) -> str:
    """Convierte los indicadores en un mensaje breve y legible."""
    return (
        "🎮 Resumen diario — Videojuego Seed42\n"
        f"Total de partidas: {resumen['total_partidas']}\n"
        f"Puntos medios: {resumen['puntos_medios']}\n"
        f"Puntos máximos: {resumen['puntos_maximos']}\n"
        f"K/D medio: {resumen['kd_medio']}"
    )


def enviar_mensaje_telegram(
    texto: str,
    token: str = TELEGRAM_BOT_TOKEN,
    chat_id: str = TELEGRAM_CHAT_ID,
) -> None:
    """Envía un mensaje usando credenciales leídas desde el entorno."""
    if not token or not chat_id:
        raise RuntimeError(
            "Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en el archivo .env."
        )

    respuesta = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": texto},
        timeout=10,
    )
    respuesta.raise_for_status()
    registrar("Paso 6", f"Resumen enviado a Telegram (HTTP {respuesta.status_code}).")


def enviar_resumen_telegram(config: dict = CONFIG_BD) -> None:
    """Consulta MySQL, construye el mensaje y lo envía a Telegram."""
    conexion = obtener_conexion(config)
    try:
        resumen = consultar_resumen_partidas(conexion)
    finally:
        conexion.close()
    enviar_mensaje_telegram(construir_mensaje(resumen))
