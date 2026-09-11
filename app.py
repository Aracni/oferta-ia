"""OFERTA IA V11.10.11.
Loader simples: núcleo V11.9 + enriquecimento ML V11.10.11.
A interface Marketplace é montada diretamente pelo patch no HTML estrutural.
"""
import urllib.request

_BASE = "https://raw.githubusercontent.com/Aracni/oferta-ia/639b53c7e97152b2756e70eef2940454ae3420d7/app.py"
_PATCH = "https://raw.githubusercontent.com/Aracni/oferta-ia/ab2a580c37c3f8a8c96eadf5b8b2ff243df92f3c/ml_enrichment_v2.py"

try:
    with urllib.request.urlopen(_BASE, timeout=20) as response:
        source = response.read().decode("utf-8")
except Exception as exc:
    raise RuntimeError(f"Não foi possível carregar o núcleo V11.9 do OFERTA IA: {exc}") from exc

exec(compile(source, _BASE, "exec"), globals(), globals())

try:
    with urllib.request.urlopen(_PATCH, timeout=20) as response:
        patch = response.read().decode("utf-8")
except Exception as exc:
    raise RuntimeError(f"Não foi possível carregar o patch V11.10.11 do OFERTA IA: {exc}") from exc

exec(compile(patch, _PATCH, "exec"), globals(), globals())

print('[V11.10.11] loader simples ativo; UI Marketplace vem diretamente do HTML estrutural', flush=True)
