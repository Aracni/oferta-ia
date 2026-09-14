"""Inicialização explícita do OFERTA IA — boot resiliente."""
import os
import time
import urllib.request
from fastapi.responses import JSONResponse
from starlette.requests import Request
import app as oferta_app
import v106_patch

v106_patch.install(oferta_app.app)

# Supabase new sb_secret_* keys are opaque API keys, not JWTs.
# Remove any Authorization: Bearer header injected by supabase-py so
# PostgREST validates the secret through the apikey header instead.
try:
    import supabase_secret_compat_v1
    supabase_secret_compat_v1.install(oferta_app)
    print("[BOOT] compatibilidade Supabase sb_secret_* carregada", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] compatibilidade Supabase não instalada: {type(exc).__name__}: {str(exc)[:300]}", flush=True)

oferta_app.app._get_connection = oferta_app._get_connection
oferta_app.app._save_connection = oferta_app._save_connection

import meli_auto
meli_auto.install(oferta_app.app)

import meli_fast
meli_fast.install(oferta_app.app)

_PATCH = "https://raw.githubusercontent.com/Aracni/oferta-ia/081d99d469525f6b4248783fdeac99fd9f33073c/ml_enrichment_v3.py"
_PATCH_SALES = "https://raw.githubusercontent.com/Aracni/oferta-ia/c20e1e4ef421868d1e341e5830d9033ff5baf6ca/ml_sales_fallback_v5.py"
_PATCH_ITEM_SALES = "https://raw.githubusercontent.com/Aracni/oferta-ia/32a0cf2937e6c8759a9f0a0bdfc7933ae6a62977/ml_item_sales_v1.py"
_PATCH_REVIEWS = "https://raw.githubusercontent.com/Aracni/oferta-ia/fe4a64fee34bb79f6eeef72ef4c4d860b464e21f/ml_reviews_fallback_v2.py"
_PATCH_MARKET = "https://raw.githubusercontent.com/Aracni/oferta-ia/6f0ab9636ce9586a205606c2c58da6304b3b83ec/ml_market_signals_v14.py"
_PATCH_OPPORTUNITY = "https://raw.githubusercontent.com/Aracni/oferta-ia/4fc607d2f9043e1351072058a0cb0c74da5e8404/opportunity_engine_v12_2.py"


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
    item_sales_patch = _load_patch(_PATCH_ITEM_SALES)
    exec(compile(item_sales_patch, _PATCH_ITEM_SALES, "exec"), oferta_app.__dict__, oferta_app.__dict__)
    print("[BOOT] fallback de vendas V11.11.16 carregado", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] fallback item winner não instalado: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

try:
    reviews_patch = _load_patch(_PATCH_REVIEWS)
    exec(compile(reviews_patch, _PATCH_REVIEWS, "exec"), oferta_app.__dict__, oferta_app.__dict__)
    print("[BOOT] fallback de avaliações V11.11.13 carregado", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] fallback de avaliações não instalado: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

try:
    market_patch = _load_patch(_PATCH_MARKET)
    exec(compile(market_patch, _PATCH_MARKET, "exec"), oferta_app.__dict__, oferta_app.__dict__)
    print("[BOOT] sinais de mercado V11.11.14 carregados", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] sinais de mercado não instalados: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

try:
    opportunity_patch = _load_patch(_PATCH_OPPORTUNITY)
    exec(compile(opportunity_patch, _PATCH_OPPORTUNITY, "exec"), oferta_app.__dict__, oferta_app.__dict__)
    print("[BOOT] motor de oportunidade V12.2 carregado", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] motor de oportunidade não instalado: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

try:
    import ui_fix
    ui_fix.install(oferta_app)
    print("[BOOT] UI V11.11.5 instalada", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] UI não instalada: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

try:
    if not any(getattr(route, "path", None) == "/healthz" for route in oferta_app.app.routes):
        @oferta_app.app.get("/healthz", include_in_schema=False)
        async def _oferta_healthz():
            return JSONResponse({"status": "ok", "app": "OFERTA IA", "boot": "V12.2"})
    print("[HEALTH] /healthz registrado", flush=True)
except Exception as exc:
    print(f"[HEALTH][WARN] /healthz não registrado: {type(exc).__name__}: {str(exc)[:300]}", flush=True)

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
                f"status=exception host={host} cf_ray={cf_ray} rndr_id={rndr_id} "
                f"elapsed_ms={elapsed_ms} error={type(exc).__name__}: {str(exc)[:300]}",
                flush=True,
            )
            raise
    print("[EDGE_TRACE] rastreamento CF-Ray/Rndr-Id ativo", flush=True)
except Exception as exc:
    print(f"[EDGE_TRACE][WARN] rastreamento não instalado: {type(exc).__name__}: {str(exc)[:300]}", flush=True)

print('[V12.2] boot resiliente; motor de oportunidade + sinais de mercado + vendas e avaliações ativos', flush=True)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        oferta_app.app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
