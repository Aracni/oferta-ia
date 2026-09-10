"""Patch OFERTA IA V10.8 — diagnóstico persistente e wrapper FastAPI corrigido."""
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
    try:
        safe = {k: v for k, v in fields.items() if k not in {"token", "access_token", "refresh_token", "client_secret", "app_secret"}}
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

    # Localiza o endpoint já registrado pelo app.py.
    central_route = None
    original_central = None
    for route in getattr(app, "routes", []):
        if getattr(route, "path", None) == "/api/opportunities-central":
            central_route = route
            original_central = getattr(route, "endpoint", None)
            break

    if central_route is None or original_central is None:
        _append_log(app, "PATCH_ERROR", "Endpoint /api/opportunities-central não encontrado")
        print("[V10.8][ERRO] Endpoint central não encontrado", flush=True)
        app.V107_PATCH_ACTIVE = True
        return

    if getattr(original_central, "_v108_auto_meli", False):
        app.V107_PATCH_ACTIVE = True
        _append_log(app, "BOOT", "Patch V10.8 já estava ativo")
        return

    def central_wrapper(payload: dict):
        payload = dict(payload or {})
        payload["include_meli"] = True
        niche = str(payload.get("niche") or "").strip()
        _append_log(
            app,
            "START",
            "Motor central V10.8 iniciado",
            niche=niche or "todos",
            limit=payload.get("limit", 10),
            include_meli=True,
        )
        print("[V10.8] Motor central iniciado | Mercado Livre automático", flush=True)
        try:
            result = original_central(payload)
            result = _json_safe(result)
            if not isinstance(result, dict):
                raise RuntimeError("O motor central retornou uma resposta inválida.")

            result["engine"] = "OFERTA IA V10.8"
            result["meli_mode"] = "automatic"
            diagnostic = result.get("diagnostic")
            if not isinstance(diagnostic, list):
                diagnostic = []
                result["diagnostic"] = diagnostic
            diagnostic.append("V10.8: Mercado Livre consultado automaticamente")

            _append_log(
                app,
                "RESULT",
                "Motor central concluído",
                returned=result.get("returned", 0),
                candidates=result.get("candidates_found", 0),
            )
            _append_log(app, "DIAGNOSTIC", " · ".join(str(x) for x in diagnostic))
            print("[V10.8] Motor central concluído", flush=True)
            return result
        except Exception as exc:
            message = _error_text(exc)
            _append_log(app, "ERROR", "Motor central falhou", error=message)
            print(f"[V10.8][ERRO] Motor central: {message}", flush=True)
            return {
                "status": "error",
                "engine": "OFERTA IA V10.8",
                "mode": "completo",
                "items": [],
                "opportunities": [],
                "returned": 0,
                "candidates_found": 0,
                "diagnostic": [
                    "V10.8 iniciou a consulta automática do Mercado Livre",
                    f"ERRO REAL: {message}",
                ],
                "message": f"⚠️ V10.8 encontrou um erro: {message}",
            }

    central_wrapper._v108_auto_meli = True
    central_route.endpoint = central_wrapper

    # IMPORTANTE: APIRoute.app precisa ser o wrapper ASGI request_response,
    # não o handler cru retornado por get_route_handler().
    try:
        from fastapi.dependencies.utils import get_dependant
        from fastapi.routing import request_response
        central_route.dependant = get_dependant(path=central_route.path, call=central_wrapper)
        central_route.app = request_response(central_route.get_route_handler())
        _append_log(app, "PATCH", "Handler central reconstruído corretamente")
    except Exception as exc:
        _append_log(app, "PATCH_ERROR", "Falha ao reconstruir handler central", error=_error_text(exc))
        print(f"[V10.8][ERRO] Handler: {_error_text(exc)}", flush=True)

    app.V107_PATCH_ACTIVE = True
    _append_log(app, "BOOT", "Patch V10.8 ativo — diagnóstico persistente habilitado")
    print("[V10.8] Patch ativo — diagnóstico persistente habilitado", flush=True)
