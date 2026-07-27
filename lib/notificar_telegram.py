"""
Paso 6 (versión directa) — Automatización con Telegram
Proyecto de final de curso — Videojuego (seed42)

En vez de depender de n8n (webhook, credenciales, formato de los datos...),
Python consulta MySQL y le manda el mensaje directamente a Telegram usando
su API HTTP (https://api.telegram.org/bot<TOKEN>/sendMessage). Menos piezas
que puedan fallar, y se integra directamente en main.py.
"""

import requests

from lib.carga_mysql import obtener_conexion, CONFIG_BD
from lib.resumen import registrar


# Credenciales de tu bot de Telegram (@piratavk_bot)
TELEGRAM_BOT_TOKEN = "8847018663:AAHSbQVC2ebkbagyGxEwGC-AUyQwDmmzE4g"
TELEGRAM_CHAT_ID = "7036048095"


def consultar_resumen_partidas(conexion) -> dict:
    """Total de registros, media y máximo de la métrica principal (puntos)."""
    sql = """
        SELECT
            COUNT(*)    AS total_partidas,
            AVG(puntos) AS puntos_medios,
            MAX(puntos) AS puntos_maximos
        FROM partidas
    """
    cursor = conexion.cursor()
    cursor.execute(sql)
    columnas = [c[0] for c in cursor.description]
    fila = cursor.fetchone()
    cursor.close()

    resumen = dict(zip(columnas, fila))
    if resumen.get("puntos_medios") is not None:
        resumen["puntos_medios"] = round(float(resumen["puntos_medios"]), 1)
    return resumen


def construir_mensaje(resumen: dict) -> str:
    """Da formato de texto legible al resumen, para el mensaje de Telegram."""
    return (
        "🎮 Resumen diario — Videojuego seed42\n"
        f"Total de partidas: {resumen['total_partidas']}\n"
        f"Puntos medios: {resumen['puntos_medios']}\n"
        f"Puntos máximos: {resumen['puntos_maximos']}"
    )


def enviar_mensaje_telegram(texto: str, token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID) -> None:
    """Envía 'texto' como mensaje de Telegram, usando la API HTTP del bot."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    respuesta = requests.post(url, json={"chat_id": chat_id, "text": texto}, timeout=10)
    respuesta.raise_for_status()
    registrar("Paso 6", "Resumen enviado a Telegram correctamente.")


def enviar_resumen_telegram(config: dict = CONFIG_BD) -> None:
    """Orquesta el Paso 6: consulta MySQL, arma el mensaje y lo envía a Telegram."""
    if TELEGRAM_BOT_TOKEN == "PON_AQUI_TU_TOKEN" or TELEGRAM_CHAT_ID == "PON_AQUI_TU_CHAT_ID":
        registrar("Paso 6", "Sin enviar: falta configurar TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID "
                  "en lib/notificar_telegram.py")
        return

    conexion = obtener_conexion(config)
    resumen = consultar_resumen_partidas(conexion)
    conexion.close()

    mensaje = construir_mensaje(resumen)
    enviar_mensaje_telegram(mensaje, token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID)
