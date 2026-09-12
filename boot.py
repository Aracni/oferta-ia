"""Inicialização explícita do OFERTA IA — boot resiliente."""
import os
import time
import urllib.request
from fastapi.responses import JSONResponse
from starlette.requests import Request
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
_PATCH_SALES = "https://raw.githubusercontent.com/Aracni/oferta-ia/c20e1e4ef421868d1e341e5830d9033ff5baf6ca/ml_sales_fallback_v5.py"


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


try:
    patch = _load_patch(_PATCH)
    exec(compile(patch, _PATCH, "exec"), oferta_app.__dict__, oferta_app.__dict__)
    print("[BOOT] V11.11.6 carregado", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] V11.11.6 não instalado: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

try:
    sales_patch = _load_patch(_PATCH_SALES)
    exec(compile(sales_patch, _PATCH_SALES, "exec"), oferta_app.__dict__, oferta_app.__dict__)
    print("[BOOT] fallback de vendas V11.11.10 carregado", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] fallback de vendas não instalado: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

try:
    import ui_fix
    ui_fix.install(oferta_app)
    print("[BOOT] UI V11.11.5 instalada", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] UI não instalada: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

# Health check mínimo: não toca em Supabase, Mercado Livre, Shopee ou no núcleo.
# Serve para distinguir processo vivo de aplicação sem instância saudável.
try:
    if not any(getattr(route, "path", None) == "/healthz" for route in oferta_app.app.routes):
        @oferta_app.app.get("/healthz", include_in_schema=False)
        async def _oferta_healthz():
            return JSONResponse({"status": "ok", "app": "OFERTA IA", "boot": "V11.11.10"})
    print("[HEALTH] /healthz registrado", flush=True)
except Exception as exc:
    print(f"[HEALTH][WARN] /healthz não registrado: {type(exc).__name__}: {str(exc)[:300]}", flush=True)

# Diagnóstico de borda: Render recomenda registrar CF-Ray e Rndr-Id
# para distinguir requisições que chegaram ao FastAPI das que falharam antes dele.
# Não altera respostas nem lógica de negócio.
try:
    @oferta_app.app.middleware("http")
    async def _oferta_edge_trace(request: Request, call_next):
        cf_ray = request.headers.get("cf-ray", "-")
        rndr_id = request.headers.get("rndr-id", "-")
        host = request.headers.get("host", "-")
        started = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            print(
                f"[EDGE_TRACE] {request.method} {request.url.path} "
                f"status={response.status_code} host={host} cf_ray={cf_ray} "
                f"rndr_id={rndr_id} elapsed_ms={elapsed_ms}",
                flush=True,
            )
            return response
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            print(
                f"[EDGE_TRACE][ERROR] {request.method} {request.url.path} "
                f"host={host} cf_ray={cf_ray} rndr_id={rndr_id} "
                f"elapsed_ms={elapsed_ms} error={type(exc).__name__}: {str(exc)[:300]}",
                flush=True,
            )
            raise
    print("[EDGE_TRACE] rastreamento CF-Ray/Rndr-Id ativo", flush=True)
except Exception as exc:
    print(f"[EDGE_TRACE][WARN] rastreamento não instalado: {type(exc).__name__}: {str(exc)[:300]}", flush=True)

print('[V11.11.10] boot resiliente; fallback de vendas otimizado', flush=True)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        oferta_app.app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
