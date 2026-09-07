"""Consulta los indicadores de MySQL y los envía de forma segura a n8n."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote, urlparse

import requests

from lib.carga_mysql import obtener_conexion
from lib.configuracion import CONFIG_BD, N8N_WEBHOOK_URL
from lib.resumen import registrar


def _url_codificada(url: str) -> str:
    """Codifica únicamente la ruta del webhook, sin modificar el dominio."""
    base, separador, ruta = url.partition("/webhook/")
    if not separador:
        return url
    return f"{base}/webhook/{quote(ruta)}"


def _validar_url_webhook(url: str) -> str:
    """Impide envíos accidentales cuando el webhook no está configurado."""
    if not url:
        raise RuntimeError(
            "Falta N8N_WEBHOOK_URL. Copia .env.example a .env y configura el webhook."
        )
    url_validada = _url_codificada(url)
    partes = urlparse(url_validada)
    if partes.scheme not in {"http", "https"} or not partes.netloc:
        raise ValueError("N8N_WEBHOOK_URL no contiene una URL HTTP válida.")
    return url_validada


def consultar_resumen_partidas(conexion) -> dict[str, object]:
    """Calcula indicadores descriptivos sin inventar valores."""
    cursor = conexion.cursor()
    try:
        cursor.execute(
            """
            SELECT
                COUNT(*)      AS total_partidas,
                AVG(puntos)   AS puntos_medios,
                MAX(puntos)   AS puntos_maximos,
                AVG(kd_ratio) AS kd_medio
            FROM partidas
            """
        )
        columnas = [columna[0] for columna in cursor.description]
        generales = dict(zip(columnas, cursor.fetchone()))

        cursor.execute(
            """
            SELECT mapa, COUNT(*) AS total
            FROM partidas
            GROUP BY mapa
            ORDER BY total DESC
            LIMIT 1
            """
        )
        fila_mapa = cursor.fetchone()

        cursor.execute(
            """
            SELECT ROUND(SUM(resultado = 'Victoria') / COUNT(*) * 100, 1)
            FROM partidas
            WHERE resultado IS NOT NULL
            """
        )
        fila_victorias = cursor.fetchone()

        cursor.execute(
            """
            SELECT j.nick, SUM(p.puntos) AS puntos_totales
            FROM jugadores j
            JOIN partidas p ON p.id_jugador = j.id_jugador
            GROUP BY j.id_jugador, j.nick
            ORDER BY puntos_totales DESC
            LIMIT 1
            """
        )
        fila_jugador = cursor.fetchone()
    finally:
        cursor.close()

    if not generales["total_partidas"] or fila_mapa is None or fila_jugador is None:
        raise ValueError("No hay suficientes datos cargados para generar el resumen.")

    mapa_favorito, partidas_mapa_favorito = fila_mapa
    pct_victorias = fila_victorias[0] if fila_victorias else None
    jugador_top, puntos_jugador_top = fila_jugador

    resumen: dict[str, object] = {
        "fecha": datetime.now().astimezone().strftime("%d-%m-%Y %H:%M %Z"),
        "total_partidas": generales["total_partidas"],
        "puntos_medios": round(float(generales["puntos_medios"]), 1),
        "puntos_maximos": generales["puntos_maximos"],
        "kd_medio": round(float(generales["kd_medio"]), 2),
        "mapa_favorito": mapa_favorito,
        "partidas_mapa_favorito": partidas_mapa_favorito,
        "pct_victorias": float(pct_victorias) if pct_victorias is not None else None,
        "jugador_top": jugador_top,
        "puntos_jugador_top": int(puntos_jugador_top),
    }
    resumen["conclusiones"] = generar_conclusiones(resumen)
    return resumen


def generar_conclusiones(resumen: dict[str, object]) -> list[str]:
    """Genera conclusiones descriptivas basadas únicamente en los indicadores."""
    conclusiones = [
        f"El mapa más jugado es {resumen['mapa_favorito']}, con "
        f"{resumen['partidas_mapa_favorito']} partidas de "
        f"{resumen['total_partidas']} totales.",
        f"El ratio de victorias global es del {resumen['pct_victorias']}%.",
        f"El jugador con más puntos acumulados es {resumen['jugador_top']}, "
        f"con {resumen['puntos_jugador_top']} puntos.",
    ]
    comparacion = "por encima" if float(resumen["kd_medio"]) >= 1 else "por debajo"
    conclusiones.append(
        f"El K/D medio general es de {resumen['kd_medio']}, {comparacion} de 1."
    )
    return conclusiones


def enviar_resumen_a_n8n(
    resumen: dict[str, object],
    url_webhook: str = N8N_WEBHOOK_URL,
) -> None:
    """Envía el resumen como JSON sin mostrar ni registrar la URL privada."""
    respuesta = requests.post(
        _validar_url_webhook(url_webhook),
        json=resumen,
        timeout=10,
    )
    respuesta.raise_for_status()
    registrar("Paso 6", f"Resumen enviado a n8n (HTTP {respuesta.status_code}).")


def enviar_reporte(config: dict = CONFIG_BD, url_webhook: str = N8N_WEBHOOK_URL) -> None:
    """Consulta MySQL y envía el resumen a n8n."""
    conexion = obtener_conexion(config)
    try:
        resumen = consultar_resumen_partidas(conexion)
    finally:
        conexion.close()
    enviar_resumen_a_n8n(resumen, url_webhook)
