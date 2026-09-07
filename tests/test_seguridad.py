from pathlib import Path
import re

from lib.notificar_n8n import _validar_url_webhook

RAIZ = Path(__file__).resolve().parents[1]


def test_webhook_vacio_se_rechaza():
    try:
        _validar_url_webhook("")
    except RuntimeError as error:
        assert "N8N_WEBHOOK_URL" in str(error)
    else:
        raise AssertionError("Un webhook vacío debe producir un error.")


def test_no_hay_tokens_de_telegram_en_codigo():
    patron_token = re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b")
    extensiones = {".py", ".json", ".yml", ".yaml", ".md", ".toml"}
    archivos = [
        archivo
        for archivo in RAIZ.rglob("*")
        if archivo.is_file()
        and archivo.suffix in extensiones
        and ".venv" not in archivo.parts
    ]
    contenido = "\n".join(archivo.read_text(encoding="utf-8") for archivo in archivos)

    assert patron_token.search(contenido) is None
    assert re.search(r"https?://[^\s]+/webhook/", contenido) is None
