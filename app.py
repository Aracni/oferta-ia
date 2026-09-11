"""OFERTA IA V11.11.
Loader simples e determinístico: núcleo V11.9 + enriquecimento ML V11.11.
"""
import time
import urllib.request

_BASE = "https://raw.githubusercontent.com/Aracni/oferta-ia/639b53c7e97152b2756e70eef2940454ae3420d7/app.py"
_PATCH = "https://raw.githubusercontent.com/Aracni/oferta-ia/e2573b00c684cca600cfc05c2590b8e83e0ded8e/ml_enrichment_v3.py"


def _load_remote(url, label):
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                return response.read().decode("utf-8")
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"Não foi possível carregar {label} do OFERTA IA: {last_error}") from last_error


source = _load_remote(_BASE, "o núcleo V11.9")
exec(compile(source, _BASE, "exec"), globals(), globals())

patch = _load_remote(_PATCH, "o patch V11.11")
exec(compile(patch, _PATCH, "exec"), globals(), globals())

print('[V11.11] loader ativo; núcleo V11.9 + enriquecimento ML V11.11', flush=True)
