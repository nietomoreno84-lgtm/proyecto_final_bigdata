"""
Paso 4 — Visualización interactiva (Plotly)
Proyecto de final de curso — Videojuego (seed42)

Consulta los datos ya cargados en MySQL (Paso 3) y genera al menos 3
gráficos interactivos, exportados como HTML:
  1. Evolución temporal / tendencia: partidas jugadas por día
  2. Comparativa entre categorías: puntos medios por mapa
  3. Distribución: reparto del ratio kills/muertes por modo de juego
"""

import os

import pandas as pd
import plotly.express as px

from lib.carga_mysql import obtener_conexion, CONFIG_BD
from lib.resumen import registrar


# ---------------------------------------------------------------------------
# 1. Consulta a MySQL
# ---------------------------------------------------------------------------

def consultar_partidas_completas(conexion) -> pd.DataFrame:
    """
    Trae las partidas junto con los datos del jugador que las jugó
    (JOIN partidas + jugadores), para tener mapa, modo, puntos, kd_ratio,
    región y rango en un único DataFrame.
    """
    sql = """
        SELECT p.fecha, p.mapa, p.modo, p.duracion_min, p.puntos,
               p.kd_ratio, p.resultado, j.region, j.rango
        FROM partidas p
        JOIN jugadores j ON p.id_jugador = j.id_jugador
    """
    cursor = conexion.cursor()
    cursor.execute(sql)
    columnas = [c[0] for c in cursor.description]
    filas = cursor.fetchall()
    cursor.close()

    df = pd.DataFrame(filas, columns=columnas)
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df


def consultar_ranking_jugadores(conexion, limite: int = 10) -> pd.DataFrame:
    """Top jugadores por puntos totales acumulados, con su región, rango y K/D medio."""
    sql = f"""
        SELECT j.nick, j.region, j.rango,
               COUNT(p.id_partida) AS partidas_jugadas,
               SUM(p.puntos)       AS puntos_totales,
               AVG(p.kd_ratio)     AS kd_medio
        FROM jugadores j
        JOIN partidas p ON p.id_jugador = j.id_jugador
        GROUP BY j.id_jugador, j.nick, j.region, j.rango
        ORDER BY puntos_totales DESC
        LIMIT {limite}
    """
    cursor = conexion.cursor()
    cursor.execute(sql)
    columnas = [c[0] for c in cursor.description]
    df = pd.DataFrame(cursor.fetchall(), columns=columnas)
    cursor.close()
    return df


def consultar_victorias_por_rango(conexion) -> pd.DataFrame:
    """Porcentaje de victorias de cada rango de jugador."""
    sql = """
        SELECT j.rango,
               SUM(p.resultado = 'Victoria') AS victorias,
               COUNT(*)                      AS total,
               ROUND(SUM(p.resultado = 'Victoria') / COUNT(*) * 100, 1) AS pct_victorias
        FROM jugadores j
        JOIN partidas p ON p.id_jugador = j.id_jugador
        WHERE p.resultado IS NOT NULL
        GROUP BY j.rango
        ORDER BY pct_victorias DESC
    """
    cursor = conexion.cursor()
    cursor.execute(sql)
    columnas = [c[0] for c in cursor.description]
    df = pd.DataFrame(cursor.fetchall(), columns=columnas)
    cursor.close()
    return df


def consultar_actividad_region_dia(conexion) -> pd.DataFrame:
    """Nº de partidas jugadas, cruzando región del jugador y día de la semana."""
    sql = """
        SELECT j.region, p.dia_semana, COUNT(*) AS total_partidas
        FROM jugadores j
        JOIN partidas p ON p.id_jugador = j.id_jugador
        GROUP BY j.region, p.dia_semana
    """
    cursor = conexion.cursor()
    cursor.execute(sql)
    columnas = [c[0] for c in cursor.description]
    df = pd.DataFrame(cursor.fetchall(), columns=columnas)
    cursor.close()
    return df


def consultar_personajes_usados(conexion) -> pd.Series:
    """Cuenta cuántas veces se ha usado cada personaje. 'personajes_usados' es
    multivalor (separado por ';'), así que se 'explota' en Python con pandas."""
    cursor = conexion.cursor()
    cursor.execute("SELECT personajes_usados FROM partidas WHERE personajes_usados <> ''")
    valores = [fila[0] for fila in cursor.fetchall()]
    cursor.close()

    personajes = pd.Series(valores).str.split(";").explode().str.strip()
    return personajes.value_counts()


# ---------------------------------------------------------------------------
# 2. Gráfico 1 — Evolución temporal / tendencia
# ---------------------------------------------------------------------------

def grafico_evolucion_temporal(df: pd.DataFrame, ruta_salida: str):
    """Partidas jugadas por día, para ver la tendencia de actividad en el tiempo.
    Guarda el HTML y además devuelve el objeto 'fig' (útil para mostrarlo
    inline en el Interactive Window de VS Code con fig.show())."""
    diario = (
        df.groupby(df["fecha"].dt.date)
        .agg(total_partidas=("puntos", "count"), puntos_medios=("puntos", "mean"))
        .reset_index()
        .rename(columns={"fecha": "fecha"})
    )
    fig = px.line(
        diario, x="fecha", y="total_partidas", markers=True,
        title="Evolución de partidas jugadas por día",
    )
    fig.update_layout(xaxis_title="Fecha", yaxis_title="Partidas jugadas")
    fig.write_html(ruta_salida)
    registrar("Paso 4", f"Gráfico generado: {ruta_salida}")
    return fig


# ---------------------------------------------------------------------------
# 3. Gráfico 2 — Comparativa entre categorías
# ---------------------------------------------------------------------------

def grafico_comparativa_mapas(df: pd.DataFrame, ruta_salida: str):
    """Puntos medios por mapa, para comparar qué mapas dan más puntuación."""
    por_mapa = (
        df.groupby("mapa")["puntos"]
        .mean()
        .reset_index()
        .sort_values("puntos", ascending=False)
    )
    fig = px.bar(
        por_mapa, x="mapa", y="puntos", color="mapa",
        title="Puntos medios por mapa",
    )
    fig.update_layout(xaxis_title="Mapa", yaxis_title="Puntos medios", showlegend=False)
    fig.write_html(ruta_salida)
    registrar("Paso 4", f"Gráfico generado: {ruta_salida}")
    return fig


# ---------------------------------------------------------------------------
# 4. Gráfico 3 — Distribución
# ---------------------------------------------------------------------------

def grafico_distribucion_kd(df: pd.DataFrame, ruta_salida: str):
    """
    Distribución del ratio kills/muertes (kd_ratio) por modo de juego, con un
    diagrama de caja: muestra mediana, cuartiles y valores atípicos de cada
    modo uno al lado del otro, más fácil de leer que un histograma superpuesto.
    """
    fig = px.box(
        df, x="modo", y="kd_ratio", color="modo", points="outliers",
        title="Distribución del ratio kills/muertes por modo de juego",
    )
    fig.update_layout(xaxis_title="Modo de juego", yaxis_title="K/D ratio", showlegend=False)
    fig.write_html(ruta_salida)
    registrar("Paso 4", f"Gráfico generado: {ruta_salida}")
    return fig


# ---------------------------------------------------------------------------
# Gráficos extra (para explorar_graficos.ipynb) — no forman parte del
# mínimo del Paso 4 en main.py, son visualizaciones adicionales con otras
# preguntas interesantes sobre los datos.
# ---------------------------------------------------------------------------

def grafico_top_jugadores(df_ranking: pd.DataFrame, ruta_salida: str):
    """Top jugadores por puntos totales acumulados en todas sus partidas."""
    fig = px.bar(
        df_ranking.sort_values("puntos_totales"),
        x="puntos_totales", y="nick", orientation="h", color="rango",
        hover_data=["region", "partidas_jugadas", "kd_medio"],
        title="Top jugadores por puntos totales",
    )
    fig.update_layout(xaxis_title="Puntos totales", yaxis_title="Jugador")
    fig.write_html(ruta_salida)
    registrar("Paso 4 (extra)", f"Gráfico generado: {ruta_salida}")
    return fig


def grafico_victorias_por_rango(df_victorias: pd.DataFrame, ruta_salida: str):
    """Porcentaje de victorias por rango de jugador: ¿los rangos altos ganan más?"""
    fig = px.bar(
        df_victorias, x="rango", y="pct_victorias", color="rango", text="pct_victorias",
        title="Porcentaje de victorias por rango de jugador",
    )
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    fig.update_layout(xaxis_title="Rango", yaxis_title="% de victorias", showlegend=False)
    fig.write_html(ruta_salida)
    registrar("Paso 4 (extra)", f"Gráfico generado: {ruta_salida}")
    return fig


def grafico_actividad_region_dia(df_actividad: pd.DataFrame, ruta_salida: str):
    """Barras agrupadas: partidas jugadas por día de la semana, comparando
    regiones una al lado de la otra (más fácil de comparar alturas exactas
    que un mapa de calor basado en intensidad de color)."""
    orden_dias = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    nombres_es = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", "Thursday": "Jueves",
        "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo",
    }
    df_actividad = df_actividad.copy()
    df_actividad["dia_semana"] = df_actividad["dia_semana"].map(nombres_es)
    orden_dias_es = [nombres_es[d] for d in orden_dias]

    fig = px.bar(
        df_actividad, x="dia_semana", y="total_partidas", color="region", barmode="group",
        category_orders={"dia_semana": orden_dias_es},
        title="Partidas jugadas por día de la semana y región",
    )
    fig.update_layout(xaxis_title="Día de la semana", yaxis_title="Partidas jugadas")
    fig.write_html(ruta_salida)
    registrar("Paso 4 (extra)", f"Gráfico generado: {ruta_salida}")
    return fig


def grafico_personajes_mas_usados(conteo_personajes: pd.Series, ruta_salida: str, top: int = 8):
    """Los personajes más elegidos en las partidas."""
    datos = conteo_personajes.head(top).reset_index()
    datos.columns = ["personaje", "veces_usado"]
    fig = px.bar(
        datos, x="personaje", y="veces_usado", color="personaje",
        title=f"Top {top} personajes más usados",
    )
    fig.update_layout(xaxis_title="Personaje", yaxis_title="Veces usado", showlegend=False)
    fig.write_html(ruta_salida)
    registrar("Paso 4 (extra)", f"Gráfico generado: {ruta_salida}")
    return fig


def grafico_reparto_modos(df: pd.DataFrame, ruta_salida: str):
    """Qué proporción de partidas se juega en cada modo (Casual/Ranked/Torneo)."""
    por_modo = df["modo"].value_counts().reset_index()
    por_modo.columns = ["modo", "total_partidas"]
    fig = px.pie(
        por_modo, names="modo", values="total_partidas", hole=0.4,
        title="Reparto de partidas por modo de juego",
    )
    fig.write_html(ruta_salida)
    registrar("Paso 4 (extra)", f"Gráfico generado: {ruta_salida}")
    return fig


def grafico_duracion_vs_puntos(df: pd.DataFrame, ruta_salida: str):
    """
    Relación entre duración de la partida y puntos conseguidos, en un panel
    separado por modo (cada panel con su propio eje X, para que 'Torneo'
    —con muchas menos partidas— no quede aplastado junto a los otros dos).
    Los puntos van semitransparentes para intuir dónde se concentran más.
    """
    fig = px.scatter(
        df, x="duracion_min", y="puntos", facet_col="modo", color="modo",
        opacity=0.3, category_orders={"modo": ["Ranked", "Casual", "Torneo"]},
        title="Relación entre duración de la partida y puntos, por modo",
    )
    fig.update_xaxes(matches=None, title="Duración (min)")
    fig.update_yaxes(title="Puntos")
    fig.update_layout(showlegend=False)
    fig.for_each_annotation(lambda a: a.update(text=a.text.replace("modo=", "")))
    fig.write_html(ruta_salida)
    registrar("Paso 4 (extra)", f"Gráfico generado: {ruta_salida}")
    return fig


# ---------------------------------------------------------------------------
# Pipeline principal del Paso 4
# ---------------------------------------------------------------------------

def generar_visualizaciones(config: dict = CONFIG_BD, carpeta_salida: str = "graficos") -> list:
    """
    Orquesta el Paso 4 completo: consulta MySQL, y genera los 9 gráficos
    HTML interactivos dentro de 'carpeta_salida' (los 3 mínimos del Paso 4
    más 6 gráficos extra de exploración). Devuelve la lista de objetos
    'fig' generados con éxito (si alguno falla, no bloquea a los demás:
    se registra el error y se continúa con el siguiente).
    """
    os.makedirs(carpeta_salida, exist_ok=True)
    conexion = obtener_conexion(config)
    figuras = []

    # cada gráfico es independiente: (nombre, función que devuelve el fig)
    tareas = [
        ("evolucion_partidas.html", lambda: grafico_evolucion_temporal(
            consultar_partidas_completas(conexion), os.path.join(carpeta_salida, "evolucion_partidas.html"))),
        ("comparativa_mapas.html", lambda: grafico_comparativa_mapas(
            consultar_partidas_completas(conexion), os.path.join(carpeta_salida, "comparativa_mapas.html"))),
        ("distribucion_kd.html", lambda: grafico_distribucion_kd(
            consultar_partidas_completas(conexion), os.path.join(carpeta_salida, "distribucion_kd.html"))),
        ("top_jugadores.html", lambda: grafico_top_jugadores(
            consultar_ranking_jugadores(conexion, limite=10), os.path.join(carpeta_salida, "top_jugadores.html"))),
        ("victorias_por_rango.html", lambda: grafico_victorias_por_rango(
            consultar_victorias_por_rango(conexion), os.path.join(carpeta_salida, "victorias_por_rango.html"))),
        ("actividad_region_dia.html", lambda: grafico_actividad_region_dia(
            consultar_actividad_region_dia(conexion), os.path.join(carpeta_salida, "actividad_region_dia.html"))),
        ("personajes_mas_usados.html", lambda: grafico_personajes_mas_usados(
            consultar_personajes_usados(conexion), os.path.join(carpeta_salida, "personajes_mas_usados.html"))),
        ("reparto_modos.html", lambda: grafico_reparto_modos(
            consultar_partidas_completas(conexion), os.path.join(carpeta_salida, "reparto_modos.html"))),
        ("duracion_vs_puntos.html", lambda: grafico_duracion_vs_puntos(
            consultar_partidas_completas(conexion), os.path.join(carpeta_salida, "duracion_vs_puntos.html"))),
    ]

    for nombre, tarea in tareas:
        try:
            figuras.append(tarea())
        except Exception as error:
            registrar("Paso 4", f"ERROR generando {nombre}: {error}")

    conexion.close()
    return figuras
