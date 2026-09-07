"""Creación, carga y validación del modelo relacional en MySQL."""

from __future__ import annotations

import re
from contextlib import closing
from typing import Mapping

import mysql.connector
import pandas as pd
from mysql.connector import Error

from lib.configuracion import CONFIG_BD
from lib.resumen import registrar

ConfigBD = Mapping[str, object]
PATRON_IDENTIFICADOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _identificador_mysql(valor: object) -> str:
    """Valida y escapa un nombre de base de datos antes de usarlo en SQL."""
    identificador = str(valor)
    if not PATRON_IDENTIFICADOR.fullmatch(identificador):
        raise ValueError(
            "MYSQL_DATABASE solo puede contener letras, números y guiones bajos, "
            "y no puede empezar por un número."
        )
    return "`" + identificador + "`"


def obtener_conexion(config: ConfigBD = CONFIG_BD, incluir_bd: bool = True):
    """Abre una conexión a MySQL usando la configuración indicada."""
    parametros = dict(config)
    if not incluir_bd:
        parametros.pop("database", None)
    return mysql.connector.connect(**parametros)


def crear_base_datos_si_no_existe(config: ConfigBD = CONFIG_BD) -> None:
    """Crea la base configurada si todavía no existe."""
    nombre_bd = _identificador_mysql(config["database"])
    with closing(obtener_conexion(config, incluir_bd=False)) as conexion:
        with closing(conexion.cursor()) as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {nombre_bd}")
    registrar("Paso 3", f"Base de datos '{config['database']}' lista.")


SQL_CREAR_TABLA_JUGADORES = """
CREATE TABLE IF NOT EXISTS jugadores (
    id_jugador       VARCHAR(6)   PRIMARY KEY,
    nick             VARCHAR(100),
    region           VARCHAR(20),
    nivel            INT,
    rango            VARCHAR(20),
    fecha_registro   DATE,
    antiguedad_dias  INT
)
"""

SQL_CREAR_TABLA_PARTIDAS = """
CREATE TABLE IF NOT EXISTS partidas (
    id_partida         INT PRIMARY KEY,
    fecha              DATE,
    hora               VARCHAR(10),
    id_jugador         VARCHAR(6),
    mapa               VARCHAR(50),
    modo               VARCHAR(20),
    personajes_usados  VARCHAR(255),
    duracion_min       INT,
    kills              INT,
    muertes            INT,
    asistencias        INT,
    resultado          VARCHAR(20),
    puntos             INT,
    anio               INT,
    mes                INT,
    dia_semana         VARCHAR(20),
    kd_ratio           DECIMAL(8, 2),
    num_personajes     INT,
    FOREIGN KEY (id_jugador) REFERENCES jugadores(id_jugador)
)
"""

SQL_ASEGURAR_KD_DECIMAL = """
ALTER TABLE partidas
MODIFY COLUMN kd_ratio DECIMAL(8, 2)
"""


def crear_tablas(conexion) -> None:
    """Crea las tablas y migra K/D a decimal si venía de una versión anterior."""
    with closing(conexion.cursor()) as cursor:
        cursor.execute(SQL_CREAR_TABLA_JUGADORES)
        cursor.execute(SQL_CREAR_TABLA_PARTIDAS)
        cursor.execute(SQL_ASEGURAR_KD_DECIMAL)
    conexion.commit()
    registrar("Paso 3", "Tablas 'jugadores' y 'partidas' listas.")


def _filas_para_sql(df: pd.DataFrame) -> list[tuple]:
    """Convierte fechas y valores nulos de pandas a tipos compatibles con SQL."""
    preparado = df.copy()
    for columna in preparado.select_dtypes(include=["datetime64[ns]"]).columns:
        preparado[columna] = preparado[columna].dt.strftime("%Y-%m-%d")
    preparado = preparado.astype(object).where(pd.notnull(preparado), None)
    return list(preparado.itertuples(index=False, name=None))


def _sql_upsert(tabla: str, columnas: list[str], clave_primaria: str) -> str:
    """Construye un UPSERT explícito para todas las columnas no clave."""
    placeholders = ", ".join(["%s"] * len(columnas))
    actualizaciones = ",\n            ".join(
        f"{columna} = VALUES({columna})"
        for columna in columnas
        if columna != clave_primaria
    )
    return f"""
        INSERT INTO {tabla} ({", ".join(columnas)})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE
            {actualizaciones}
    """


def cargar_jugadores(conexion, df_jugadores: pd.DataFrame) -> None:
    """Inserta o actualiza todos los campos de los jugadores."""
    columnas = [
        "id_jugador",
        "nick",
        "region",
        "nivel",
        "rango",
        "fecha_registro",
        "antiguedad_dias",
    ]
    filas = _filas_para_sql(df_jugadores[columnas])
    with closing(conexion.cursor()) as cursor:
        cursor.executemany(_sql_upsert("jugadores", columnas, "id_jugador"), filas)
        filas_afectadas = cursor.rowcount
    conexion.commit()
    registrar("Paso 3", f"Jugadores cargados/actualizados: {filas_afectadas}")


def cargar_partidas(conexion, df_partidas: pd.DataFrame) -> None:
    """Inserta o actualiza todos los campos de las partidas."""
    columnas = [
        "id_partida",
        "fecha",
        "hora",
        "id_jugador",
        "mapa",
        "modo",
        "personajes_usados",
        "duracion_min",
        "kills",
        "muertes",
        "asistencias",
        "resultado",
        "puntos",
        "anio",
        "mes",
        "dia_semana",
        "kd_ratio",
        "num_personajes",
    ]
    filas = _filas_para_sql(df_partidas[columnas])
    with closing(conexion.cursor()) as cursor:
        cursor.executemany(_sql_upsert("partidas", columnas, "id_partida"), filas)
        filas_afectadas = cursor.rowcount
    conexion.commit()
    registrar("Paso 3", f"Partidas cargadas/actualizadas: {filas_afectadas}")


def validar_carga(conexion) -> None:
    """Comprueba recuentos e integridad referencial después de la carga."""
    with closing(conexion.cursor()) as cursor:
        cursor.execute("SELECT COUNT(*) FROM jugadores")
        total_jugadores = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM partidas")
        total_partidas = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM partidas p
            LEFT JOIN jugadores j ON p.id_jugador = j.id_jugador
            WHERE j.id_jugador IS NULL
            """
        )
        huerfanas = cursor.fetchone()[0]

    if huerfanas:
        raise ValueError(f"La validación detectó {huerfanas} partidas sin jugador asociado.")
    registrar(
        "Paso 3",
        f"Validación -> jugadores: {total_jugadores} | partidas: {total_partidas} | "
        "partidas sin jugador asociado: 0",
    )


SQL_CREAR_TABLA_RESUMEN = """
CREATE TABLE IF NOT EXISTS resumen_mapa (
    mapa                VARCHAR(50) PRIMARY KEY,
    total_partidas      INT,
    media_puntos        DECIMAL(10, 2),
    media_kd_ratio      DECIMAL(8, 2),
    media_duracion_min  DECIMAL(8, 2)
)
"""

SQL_POBLAR_TABLA_RESUMEN = """
REPLACE INTO resumen_mapa (
    mapa,
    total_partidas,
    media_puntos,
    media_kd_ratio,
    media_duracion_min
)
SELECT
    mapa,
    COUNT(*),
    AVG(puntos),
    AVG(kd_ratio),
    AVG(duracion_min)
FROM partidas
GROUP BY mapa
"""


def crear_tabla_resumen(conexion) -> None:
    """Crea y actualiza la tabla agregada por mapa."""
    with closing(conexion.cursor()) as cursor:
        cursor.execute(SQL_CREAR_TABLA_RESUMEN)
        cursor.execute(SQL_POBLAR_TABLA_RESUMEN)
        cursor.execute("SELECT COUNT(*) FROM resumen_mapa")
        total = cursor.fetchone()[0]
    conexion.commit()
    registrar("Paso 3", f"Tabla 'resumen_mapa' generada con {total} mapas.")


def cargar_datos_en_mysql(
    df_partidas: pd.DataFrame,
    df_jugadores: pd.DataFrame,
    config: ConfigBD = CONFIG_BD,
) -> None:
    """Orquesta la creación, carga y validación del modelo relacional."""
    conexion = None
    try:
        crear_base_datos_si_no_existe(config)
        conexion = obtener_conexion(config)
        crear_tablas(conexion)
        cargar_jugadores(conexion, df_jugadores)
        cargar_partidas(conexion, df_partidas)
        validar_carga(conexion)
        crear_tabla_resumen(conexion)
    except Error as error:
        registrar("Paso 3", f"Error de MySQL: {error}")
        raise
    finally:
        if conexion is not None and conexion.is_connected():
            conexion.close()
