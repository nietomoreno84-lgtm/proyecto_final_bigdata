"""Punto de entrada del pipeline de análisis de datos del videojuego Seed42."""

from __future__ import annotations

import argparse
from pathlib import Path

from lib.carga_mysql import cargar_datos_en_mysql
from lib.cargar_datos import cargar_datos, generar_excel_bruto
from lib.configuracion import CONFIG_BD
from lib.limpieza_datos import estadisticas_descriptivas, limpiar_jugadores, limpiar_partidas
from lib.notificar_n8n import enviar_reporte
from lib.resumen import mostrar_resumen, registrar
from lib.visualizacion import generar_visualizaciones

RAIZ_PROYECTO = Path(__file__).resolve().parent
CARPETA_DATOS = RAIZ_PROYECTO / "data"

RUTA_PARTIDAS = CARPETA_DATOS / "videojuego_seed42.csv"
RUTA_JUGADORES = CARPETA_DATOS / "videojuego_seed42_jugadores.csv"
RUTA_EXCEL_BRUTO = CARPETA_DATOS / "videojuego_datos_brutos.xlsx"
RUTA_PARTIDAS_LIMPIO = CARPETA_DATOS / "partidas_limpio.csv"
RUTA_JUGADORES_LIMPIO = CARPETA_DATOS / "jugadores_limpio.csv"
CARPETA_GRAFICOS = RAIZ_PROYECTO / "graficos"

COLUMNAS_NUMERICAS = [
    "duracion_min",
    "kills",
    "muertes",
    "asistencias",
    "puntos",
    "kd_ratio",
]


def analizar_argumentos() -> argparse.Namespace:
    """Procesa las opciones de ejecución de la línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Ejecuta el pipeline ETL, carga MySQL y genera visualizaciones."
    )
    parser.add_argument(
        "--notificar",
        action="store_true",
        help="Envía el resumen a n8n al finalizar (requiere N8N_WEBHOOK_URL).",
    )
    return parser.parse_args()


def main(notificar: bool = False) -> None:
    """Ejecuta el flujo completo y, opcionalmente, envía la notificación."""
    CARPETA_DATOS.mkdir(exist_ok=True)

    df_partidas, df_jugadores = cargar_datos(RUTA_PARTIDAS, RUTA_JUGADORES)
    generar_excel_bruto(df_partidas, df_jugadores, RUTA_EXCEL_BRUTO)

    df_partidas_limpio = limpiar_partidas(df_partidas)
    df_jugadores_limpio = limpiar_jugadores(df_jugadores)
    df_partidas_limpio.to_csv(RUTA_PARTIDAS_LIMPIO, index=False)
    df_jugadores_limpio.to_csv(RUTA_JUGADORES_LIMPIO, index=False)
    registrar(
        "Paso 2",
        f"CSV limpios generados: {RUTA_PARTIDAS_LIMPIO.name}, "
        f"{RUTA_JUGADORES_LIMPIO.name}",
    )

    print("\nEstadísticas descriptivas — partidas:")
    print(estadisticas_descriptivas(df_partidas_limpio, COLUMNAS_NUMERICAS))

    print("\nCargando datos en MySQL...")
    cargar_datos_en_mysql(df_partidas_limpio, df_jugadores_limpio, CONFIG_BD)

    print("\nGenerando gráficos...")
    generar_visualizaciones(CONFIG_BD, CARPETA_GRAFICOS)

    registrar(
        "Paso 5",
        "Dashboard Power BI: dashboard_videojuego_seed42.pbix "
        "(se edita en Power BI Desktop)",
    )

    if notificar:
        print("\nEnviando resumen a n8n...")
        enviar_reporte(CONFIG_BD)
    else:
        registrar("Paso 6", "Notificación omitida. Usa --notificar para activarla.")

    mostrar_resumen()


if __name__ == "__main__":
    argumentos = analizar_argumentos()
    main(notificar=argumentos.notificar)
