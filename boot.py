"""Boot resiliente do OFERTA IA."""
import os
import time
import urllib.request
from fastapi.responses import JSONResponse
from starlette.requests import Request
import app as oferta_app
import v106_patch

v106_patch.install(oferta_app.app)
try:
    import supabase_secret_compat_v1
    supabase_secret_compat_v1.install(oferta_app)
    print("[BOOT] compatibilidade Supabase sb_secret_* carregada", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] compatibilidade Supabase: {type(exc).__name__}: {str(exc)[:300]}", flush=True)

setattr(oferta_app.app, "_get_connection", oferta_app._get_connection)
setattr(oferta_app.app, "_save_connection", oferta_app._save_connection)

import meli_auto
meli_auto.install(oferta_app.app)
import meli_fast
meli_fast.install(oferta_app.app)

_PATCH_ITEM_RECOVERY = "https://raw.githubusercontent.com/Aracni/oferta-ia/a63f187d1bc6c2aa9b68abb6f749fab97c35472c/meli_data_recovery_v1.py"
_PATCH = "https://raw.githubusercontent.com/Aracni/oferta-ia/081d99d469525f6b4248783fdeac99fd9f33073c/ml_enrichment_v3.py"
_PATCH_ITEM_SALES = "https://raw.githubusercontent.com/Aracni/oferta-ia/32a0cf2937e6c8759a9f0a0bdfc7933ae6a62977/ml_item_sales_v1.py"
_PATCH_DIRECT_ITEM_SALES = "https://raw.githubusercontent.com/Aracni/oferta-ia/2884d6f5a4d41b647b2d8048d4aa642a96f58516/ml_direct_item_sales_v125.py"
_PATCH_REVIEWS = "https://raw.githubusercontent.com/Aracni/oferta-ia/fe4a64fee34bb79f6eeef72ef4c4d860b464e21f/ml_reviews_fallback_v2.py"
_PATCH_MARKET = "https://raw.githubusercontent.com/Aracni/oferta-ia/7a4115c7f7484eeda23d19a73ab80cacbd43fb54/ml_market_signals_v16.py"
_PATCH_OPPORTUNITY = "https://raw.githubusercontent.com/Aracni/oferta-ia/a3192bae80c4b89a45347677af54a9e231b74bb6/opportunity_engine_v12_3.py"
_PATCH_DIAGNOSTIC = "https://raw.githubusercontent.com/Aracni/oferta-ia/909141fe8445b6b089f433467b3a538f55023337/opportunity_diagnostic_v1.py"
_PATCH_PUBLIC_DEMAND = "https://raw.githubusercontent.com/Aracni/oferta-ia/main/ml_public_demand_v126.py"
_PATCH_DEMAND_SIGNALS = "https://raw.githubusercontent.com/Aracni/oferta-ia/main/ml_demand_signals_v127.py"
_PATCH_CLEAN_CENTRAL = "https://raw.githubusercontent.com/Aracni/oferta-ia/fea1802a31c9528de79085e50d021073314e2c5c/central_clean_v125.py"


def _load_patch(url):
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                return response.read().decode("utf-8")
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(f"Não foi possível carregar patch do OFERTA IA: {last_error}") from last_error


def _exec_patch(url, label):
    try:
        source = _load_patch(url)
        exec(compile(source, url, "exec"), oferta_app.__dict__, oferta_app.__dict__)
        print(f"[BOOT] {label} carregado", flush=True)
    except Exception as exc:
        print(f"[BOOT][WARN] {label}: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

_exec_patch(_PATCH_ITEM_RECOVERY, "recuperação de dados ITEM V12.5")
_exec_patch(_PATCH, "V11.11.6")

try:
    import ml_sales_fallback_v5
    oferta_app._v119_enrich_ml = ml_sales_fallback_v5._v115_enrich_ml
    print("[BOOT] fallback de vendas V11.11.10 local instalado no app", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] fallback de vendas: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

_exec_patch(_PATCH_ITEM_SALES, "fallback item winner V11.11.16")
_exec_patch(_PATCH_DIRECT_ITEM_SALES, "vendas diretas por ITEM V12.5")
_exec_patch(_PATCH_REVIEWS, "fallback de avaliações V11.11.13")
_exec_patch(_PATCH_MARKET, "sinais de mercado V12.5 isolados")
_exec_patch(_PATCH_OPPORTUNITY, "motor de oportunidade V12.3")

try:
    diagnostic_source = _load_patch(_PATCH_DIAGNOSTIC)
    exec(compile(diagnostic_source, _PATCH_DIAGNOSTIC, "exec"), oferta_app.__dict__, oferta_app.__dict__)
    installer = oferta_app.__dict__.get("_v124_install")
    if callable(installer):
        installer(oferta_app)
    print("[BOOT] diagnóstico V12.4 carregado", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] diagnóstico V12.4: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

_exec_patch(_PATCH_PUBLIC_DEMAND, "vendas/demanda V12.6 catálogo + fallback público")
_exec_patch(_PATCH_DEMAND_SIGNALS, "demanda V12.7 tendências + mais vendidos")
_exec_patch(_PATCH_CLEAN_CENTRAL, "rota central limpa V12.5")

try:
    import ui_fix
    ui_fix.install(oferta_app)
    print("[BOOT] UI V11.11.5 instalada", flush=True)
except Exception as exc:
    print(f"[BOOT][WARN] UI: {type(exc).__name__}: {str(exc)[:400]}", flush=True)

try:
    if not any(getattr(route, "path", None) == "/healthz" for route in oferta_app.app.routes):
        @oferta_app.app.get("/healthz", include_in_schema=False)
        async def _oferta_healthz():
            return JSONResponse({"status": "ok", "app": "OFERTA IA", "boot": "V12.7"})
    print("[HEALTH] /healthz registrado", flush=True)
except Exception as exc:
    print(f"[HEALTH][WARN] {type(exc).__name__}: {str(exc)[:300]}", flush=True)

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
            print(f"[EDGE_TRACE] {request.method} {request.url.path} status={response.status_code} host={host} cf_ray={cf_ray} rndr_id={rndr_id} elapsed_ms={elapsed_ms}", flush=True)
            return response
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            print(f"[EDGE_TRACE][ERROR] {request.method} {request.url.path} status=exception host={host} cf_ray={cf_ray} rndr_id={rndr_id} elapsed_ms={elapsed_ms} error={type(exc).__name__}: {str(exc)[:300]}", flush=True)
            raise
    print("[EDGE_TRACE] rastreamento CF-Ray/Rndr-Id ativo", flush=True)
except Exception as exc:
    print(f"[EDGE_TRACE][WARN] rastreamento: {type(exc).__name__}: {str(exc)[:300]}", flush=True)

print("[V12.7] boot resiliente ativo", flush=True)

import uvicorn
if __name__ == "__main__":
    uvicorn.run(oferta_app.app, host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
