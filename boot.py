"""Inicialização explícita do OFERTA IA."""
import os
import time
import urllib.request
import app as oferta_app
import v106_patch

v106_patch.install(oferta_app.app)

oferta_app.app._get_connection = oferta_app._get_connection
oferta_app.app._save_connection = oferta_app._save_connection

import meli_auto
meli_auto.install(oferta_app.app)

import meli_fast
meli_fast.install(oferta_app.app)

# O enriquecimento V11.11 entra DEPOIS dos instaladores de rota.
_PATCH = "https://raw.githubusercontent.com/Aracni/oferta-ia/92da273dcba371aaa29752a12f87355229bc48b3/ml_enrichment_v3.py"

def _load_patch(url):
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                return response.read().decode("utf-8")
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"Não foi possível carregar o patch V11.11: {last_error}") from last_error

patch = _load_patch(_PATCH)
exec(compile(patch, _PATCH, "exec"), oferta_app.__dict__, oferta_app.__dict__)

import ui_fix
ui_fix.install(oferta_app)

print('[V11.11.3] boot estável; enriquecimento ML instalado após todas as rotas-base', flush=True)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        oferta_app.app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
