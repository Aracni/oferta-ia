"""Inicialização explícita do OFERTA IA — boot resiliente."""
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

_PATCH = "https://raw.githubusercontent.com/Aracni/oferta-ia/081d99d469525f6b4248783fdeac99fd9f33073c/ml_enrichment_v3.py"
_PATCH_SALES = "https://raw.githubusercontent.com/Aracni/oferta-ia/4b17048fcca94eba2d3c6da548ae60108950a518/ml_sales_fallback_v4.py"


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
    raise RuntimeError(f"Não foi possível carregar patch do OFERTA IA: {last_error}") from last_error


# O enriquecimento é importante, mas não pode derrubar o serviço inteiro.
try:
    patch = _load_patch(_PATCH)
    exec(compile(patch, _PATCH, "exec"), oferta_app.__dict__, oferta_app.__dict__)
    print("[BOOT] V11.11.6 carregado", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] V11.11.6 não instalado: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

# Fallback de vendas: opcional. Se falhar, o núcleo continua disponível.
try:
    sales_patch = _load_patch(_PATCH_SALES)
    exec(compile(sales_patch, _PATCH_SALES, "exec"), oferta_app.__dict__, oferta_app.__dict__)
    print("[BOOT] fallback de vendas V11.11.4 carregado", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] fallback de vendas não instalado: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

# UI também não pode impedir o servidor de subir.
try:
    import ui_fix
    ui_fix.install(oferta_app)
    print("[BOOT] UI V11.11.5 instalada", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] UI não instalada: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

print('[V11.11.7] boot resiliente; falhas de patches não derrubam o servidor', flush=True)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        oferta_app.app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
