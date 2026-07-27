"""
Resumen de ejecución — recoge los mensajes de estado de cada paso del
pipeline (Paso 1 a 6) y los imprime en un único bloque ordenado al final
de main.py, además de mostrarlos en el momento como hasta ahora.
"""

# Lista interna: cada elemento es (paso, mensaje), en el orden en que ocurren
_registro: list[tuple[str, str]] = []


def registrar(paso: str, mensaje: str) -> None:
    """
    Guarda 'mensaje' bajo 'paso' (p.ej. "Paso 1", "Paso 3 — jugadores") para
    el resumen final, y lo imprime igual que antes para ver el progreso
    mientras se ejecuta.
    """
    _registro.append((paso, mensaje))
    print(f"[{paso}] {mensaje}")


def mostrar_resumen() -> None:
    """Imprime, agrupados por paso y en el orden en que se registraron,
    todos los mensajes guardados durante la ejecución."""
    if not _registro:
        print("\n(No se registró ningún cambio.)")
        return

    print("\n" + "=" * 10 + " RESUMEN DE CAMBIOS " + "=" * 10)

    paso_actual = None
    for paso, mensaje in _registro:
        if paso != paso_actual:
            print(f"\n{paso}")
            paso_actual = paso
        print(f"  - {mensaje}")

    print("\n" + "=" * 41)
