"""
Paso 6 — Automatización (n8n)
Proyecto de final de curso — Videojuego (seed42)

En vez de que n8n (alojado en la nube) intente conectarse a tu MySQL local
(que no puede alcanzar), es Python quien consulta MySQL y le envía el
resumen ya calculado a n8n mediante una petición HTTP a un Webhook.

Flujo: Python (MySQL) --POST--> Webhook n8n --> Edit Fields --> Telegram/Email
"""

from datetime import datetime
from urllib.parse import quote

import requests

from lib.carga_mysql import obtener_conexion, CONFIG_BD
from lib.resumen import registrar


# Production URL del nodo Webhook en n8n (con /webhook/, no /webhook-test/).
URL_WEBHOOK_N8N = "https://david.n8ncamp.com/webhook/Resumen_diario_videojuegoSeed42"


def _url_codificada(url: str) -> str:
    """
    Codifica de forma segura la última parte de la URL (el 'Path' del
    webhook), por si contiene espacios u otros caracteres especiales, como
    en 'Resumen diario - videojuego Seed42'. El dominio no se toca.
    """
    base, _, ruta = url.partition("/webhook/")
    if not ruta:
        return url
    return f"{base}/webhook/{quote(ruta)}"


def consultar_resumen_partidas(conexion) -> dict:
    """
    Calcula el resumen diario: total de registros, media y máximo de la
    métrica principal (puntos), y datos adicionales para enriquecer el
    informe (mapa más jugado, K/D medio, % de victorias, jugador top).
    Devuelve un diccionario listo para enviar como JSON.
    """
    cursor = conexion.cursor()

    # --- Datos generales de partidas ---
    cursor.execute("""
        SELECT
            COUNT(*)      AS total_partidas,
            AVG(puntos)   AS puntos_medios,
            MAX(puntos)   AS puntos_maximos,
            AVG(kd_ratio) AS kd_medio
        FROM partidas
    """)
    columnas = [c[0] for c in cursor.description]
    generales = dict(zip(columnas, cursor.fetchone()))

    # --- Mapa más jugado ---
    cursor.execute("""
        SELECT mapa, COUNT(*) AS total
        FROM partidas
        GROUP BY mapa
        ORDER BY total DESC
        LIMIT 1
    """)
    mapa_favorito, partidas_mapa_favorito = cursor.fetchone()

    # --- % de victorias (sobre partidas con resultado registrado) ---
    cursor.execute("""
        SELECT
            ROUND(SUM(resultado = 'Victoria') / COUNT(*) * 100, 1) AS pct_victorias
        FROM partidas
        WHERE resultado IS NOT NULL
    """)
    (pct_victorias,) = cursor.fetchone()

    # --- Jugador con más puntos totales acumulados ---
    cursor.execute("""
        SELECT j.nick, SUM(p.puntos) AS puntos_totales
        FROM jugadores j
        JOIN partidas p ON p.id_jugador = j.id_jugador
        GROUP BY j.id_jugador, j.nick
        ORDER BY puntos_totales DESC
        LIMIT 1
    """)
    jugador_top, puntos_jugador_top = cursor.fetchone()

    cursor.close()

    resumen = {
        "fecha": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "total_partidas": generales["total_partidas"],
        "puntos_medios": round(float(generales["puntos_medios"]), 1),
        "puntos_maximos": generales["puntos_maximos"],
        "kd_medio": round(float(generales["kd_medio"]), 2),
        "mapa_favorito": mapa_favorito,
        "partidas_mapa_favorito": partidas_mapa_favorito,
        "pct_victorias": float(pct_victorias),
        "jugador_top": jugador_top,
        "puntos_jugador_top": int(puntos_jugador_top),
    }
    resumen["conclusiones"] = generar_conclusiones(resumen)
    return resumen


def generar_conclusiones(resumen: dict) -> list:
    """
    Genera 3-4 frases de conclusión a partir del resumen, con reglas simples
    (sin inventar nada que no esté en los propios datos).
    """
    conclusiones = [
        f"El mapa más jugado es {resumen['mapa_favorito']}, con "
        f"{resumen['partidas_mapa_favorito']} partidas de {resumen['total_partidas']} totales.",
        f"El ratio de victorias global es del {resumen['pct_victorias']}%.",
        f"El jugador con más puntos acumulados es {resumen['jugador_top']}, "
        f"con {resumen['puntos_jugador_top']} puntos en total.",
    ]
    if resumen["kd_medio"] >= 1:
        conclusiones.append(
            f"El K/D medio general es de {resumen['kd_medio']}, por encima del empate "
            "(se consiguen más bajas que muertes de media)."
        )
    else:
        conclusiones.append(
            f"El K/D medio general es de {resumen['kd_medio']}, por debajo del empate "
            "(se reciben más muertes que bajas conseguidas de media)."
        )
    return conclusiones


def enviar_resumen_a_n8n(resumen: dict, url_webhook: str = URL_WEBHOOK_N8N) -> None:
    """Envía el resumen a n8n como JSON, mediante POST al webhook."""
    respuesta = requests.post(_url_codificada(url_webhook), json=resumen, timeout=10)
    respuesta.raise_for_status()
    registrar("Paso 6", f"Resumen enviado a n8n correctamente (status {respuesta.status_code})")


def enviar_reporte(config: dict = CONFIG_BD, url_webhook: str = URL_WEBHOOK_N8N) -> None:
    """Orquesta el Paso 6: consulta MySQL, calcula el resumen y lo envía a n8n."""
    conexion = obtener_conexion(config)
    resumen = consultar_resumen_partidas(conexion)
    conexion.close()

    print("Resumen calculado:", resumen)
    enviar_resumen_a_n8n(resumen, url_webhook)
