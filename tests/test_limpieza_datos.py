import pandas as pd

from lib.limpieza_datos import (
    limpiar_partidas,
    separar_nick,
    tratar_nulos_jugadores,
)


def test_separar_nick_no_inventa_datos_ausentes():
    assert separar_nick("cgimenez12") == "C. Gimenez"
    assert separar_nick("pepita22") == "Pepita"
    assert separar_nick(None) == "Desconocido"


def test_region_ausente_queda_etiquetada():
    jugadores = pd.DataFrame({"region": [" eu-oeste ", None]})

    resultado = tratar_nulos_jugadores(jugadores)

    assert resultado["region"].tolist() == ["Eu-Oeste", "Desconocida"]


def test_pipeline_conserva_kd_como_decimal():
    partidas = pd.DataFrame(
        {
            "id_partida": [1, 2, 3, 4],
            "fecha": ["2026-01-01"] * 4,
            "hora": ["10:00"] * 4,
            "id_jugador": ["J0001"] * 4,
            "mapa": ["Arena"] * 4,
            "modo": ["Ranked"] * 4,
            "personajes_usados": ["Vex;Tesla"] * 4,
            "duracion_min": [20, 21, 22, 23],
            "kills": [6, 7, 8, 9],
            "muertes": [7, 2, 0, 3],
            "asistencias": [1, 2, 3, 4],
            "resultado": ["Victoria", "Derrota", "Victoria", "Derrota"],
            "puntos": ["100", "110", "120", "130"],
        }
    )

    resultado = limpiar_partidas(partidas)

    assert resultado.loc[0, "kd_ratio"] == 0.86
    assert pd.isna(resultado.loc[2, "kd_ratio"])
