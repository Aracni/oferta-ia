"""Patch OFERTA IA V10.7 — Mercado Livre automático + diagnóstico persistente."""
import math
import unicodedata
from datetime import datetime

CATEGORY_HINTS = {
    "eletronicos": "MLB1000",
    "eletronico": "MLB1000",
    "beleza": "MLB1246",
    "casa": "MLB1574",
    "fitness": "MLB1276",
    "moda": "MLB1430",
}


def _norm(text):
    text = str(text or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _json_safe(value):
    """Remove NaN/Infinity e outros valores que podem quebrar a resposta JSON."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _error_text(exc):
    return f"{type(exc).__name__}: {str(exc)[:500]}"


def _append_log(app, stage, message, **fields):
    """Escreve no mesmo buffer global usado pelos endpoints V9.8."""
    try:
        safe = {
            k: v for k, v in fields.items()
            if k not in {"token", "access_token", "refresh_token", "client_secret", "app_secret"}
        }
        suffix = " | " + " ".join(f"{k}={v}" for k, v in safe.items()) if safe else ""
        line = f"{datetime.now().strftime('%H:%M:%S')} | {stage} | {message}{suffix}"
        buffer = getattr(app, "_V94_LOG_BUFFER", None)
        if isinstance(buffer, list):
            buffer.append(line)
            max_lines = int(getattr(app, "_V94_LOG_MAX_LINES", 500) or 500)
            if len(buffer) > max_lines:
                del buffer[:-max_lines]
        logger = getattr(app, "_oferta_logger", None)
        if logger:
            logger.info("[%s] %s%s", stage, message, suffix)
    except Exception:
        pass


def _install_log_bridge(app):
    """Faz o objeto FastAPI e o módulo app.py usarem a mesma lista de log."""
    try:
        import app as app_module
        if not isinstance(getattr(app_module, "_V94_LOG_BUFFER", None), list):
            app_module._V94_LOG_BUFFER = []
        app._V94_LOG_BUFFER = app_module._V94_LOG_BUFFER
        app._V94_LOG_MAX_LINES = int(getattr(app_module, "_V94_LOG_MAX_LINES", 500) or 500)
        app._oferta_logger = getattr(app_module, "logger", None)
    except Exception:
        if not hasattr(app, "_V94_LOG_BUFFER"):
            app._V94_LOG_BUFFER = []
        if not hasattr(app, "_V94_LOG_MAX_LINES"):
            app._V94_LOG_MAX_LINES = 500


def install(app):
    _install_log_bridge(app)

    original_ml = getattr(app, "mercadolivre_opportunities", None)
    original_central = None
    for route in getattr(app.app, "routes", []):
        if getattr(route, "path", None) == "/api/opportunities-central":
            original_central = getattr(route, "endpoint", None)
            break

    if original_ml is not None and not getattr(original_ml, "_v107_wrapped", False):
        def ml_wrapper(payload: dict):
            payload = dict(payload or {})
            niche = _norm(payload.get("niche"))
            if niche and not payload.get("category_id"):
                for hint, category_id in CATEGORY_HINTS.items():
                    if hint in niche:
                        payload["category_id"] = category_id
                        break
            _append_log(app, "MELI", "Mercado Livre solicitado pelo motor central", niche=niche or "todos")
            try:
                result = original_ml(payload)
                if isinstance(result, dict):
                    result["engine"] = "OFERTA IA V10.7 ML OTIMIZADO"
                    result["optimization"] = "Categoria Mercado Livre priorizada pelo nicho; consulta automática habilitada."
                _append_log(app, "MELI", "Mercado Livre concluído", returned=(result or {}).get("returned", 0) if isinstance(result, dict) else 0)
                return result
            except Exception as exc:
                _append_log(app, "MELI_ERROR", "Mercado Livre falhou", error=_error_text(exc))
                raise
        ml_wrapper._v107_wrapped = True
        app.mercadolivre_opportunities = ml_wrapper

    if original_central is not None and not getattr(original_central, "_v107_auto_meli", False):
        def central_wrapper(payload: dict):
            payload = dict(payload or {})
            payload["include_meli"] = True
            niche = str(payload.get("niche") or "").strip()
            _append_log(app, "START", "Motor central V10.7 iniciado", niche=niche or "todos", limit=payload.get("limit", 10), include_meli=True)
            print("[V10.7] Motor central iniciado | Mercado Livre automático", flush=True)
            try:
                result = original_central(payload)
                result = _json_safe(result)
                if isinstance(result, dict):
                    result["engine"] = "OFERTA IA V10.7 ML OTIMIZADO"
                    result["meli_mode"] = "automatic"
                    diagnostic = result.get("diagnostic")
                    if not isinstance(diagnostic, list):
                        diagnostic = []
                        result["diagnostic"] = diagnostic
                    diagnostic.append("V10.7: Mercado Livre consultado automaticamente")
                    _append_log(app, "RESULT", "Motor central concluído", returned=result.get("returned", 0), candidates=result.get("candidates_found", 0))
                    _append_log(app, "DIAGNOSTIC", " · ".join(str(x) for x in diagnostic))
                print("[V10.7] Motor central concluído", flush=True)
                return result
            except Exception as exc:
                message = _error_text(exc)
                _append_log(app, "ERROR", "Motor central falhou", error=message)
                print(f"[V10.7][ERRO] Motor central: {message}", flush=True)
                return {
                    "status": "error",
                    "engine": "OFERTA IA V10.7 ML OTIMIZADO",
                    "mode": "completo",
                    "items": [],
                    "opportunities": [],
                    "returned": 0,
                    "candidates_found": 0,
                    "diagnostic": [
                        "V10.7 iniciou a consulta automática do Mercado Livre",
                        f"ERRO REAL: {message}",
                    ],
                    "message": f"⚠️ V10.7 encontrou um erro: {message}",
                }
        central_wrapper._v107_auto_meli = True
        for route in getattr(app.app, "routes", []):
            if getattr(route, "path", None) == "/api/opportunities-central":
                route.endpoint = central_wrapper
                try:
                    from fastapi.dependencies.utils import get_dependant
                    route.dependant = get_dependant(path=route.path, call=central_wrapper)
                    route.app = route.get_route_handler()
                except Exception as exc:
                    _append_log(app, "PATCH_ERROR", "Não foi possível reconstruir handler", error=_error_text(exc))
                    print(f"[V10.7][ERRO] Não foi possível reconstruir handler: {_error_text(exc)}", flush=True)
                break

    app.V107_PATCH_ACTIVE = True
    _append_log(app, "BOOT", "Patch V10.7 ativo — diagnóstico persistente habilitado")
    print("[V10.7] Patch ativo — diagnóstico persistente habilitado", flush=True)
