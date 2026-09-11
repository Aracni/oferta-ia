"""OFERTA IA V11.10.2.
Preserva o seletor seguro e aplica patch de enriquecimento do Mercado Livre.
"""
import urllib.request

_BASE = "https://raw.githubusercontent.com/Aracni/oferta-ia/639b53c7e97152b2756e70eef2940454ae3420d7/app.py"
_PATCH = "https://raw.githubusercontent.com/Aracni/oferta-ia/c18c26a11794b66e037b8c78cbdc207ab83c9559/ml_enrichment_v2.py"

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
    raise RuntimeError(f"Não foi possível carregar o patch V11.10.2 do OFERTA IA: {exc}") from exc

exec(compile(patch, _PATCH, "exec"), globals(), globals())
