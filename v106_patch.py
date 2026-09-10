"""Patch OFERTA IA V10.6 para priorizar Mercado Livre por nicho e ativar consulta automática."""
import math
import unicodedata

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


def install(app):
    original_ml = getattr(app, "mercadolivre_opportunities", None)
    original_central = None
    for route in getattr(app.app, "routes", []):
        if getattr(route, "path", None) == "/api/opportunities-central":
            original_central = getattr(route, "endpoint", None)
            break

    if original_ml is not None and not getattr(original_ml, "_v106_wrapped", False):
        def ml_wrapper(payload):
            payload = dict(payload or {})
            niche = _norm(payload.get("niche"))
            if niche and not payload.get("category_id"):
                for hint, category_id in CATEGORY_HINTS.items():
                    if hint in niche:
                        payload["category_id"] = category_id
                        break
            result = original_ml(payload)
            if isinstance(result, dict):
                result["engine"] = "OFERTA IA V10.6 ML OTIMIZADO"
                result["optimization"] = "Categoria Mercado Livre priorizada pelo nicho; consulta automática habilitada."
            return result
        ml_wrapper._v106_wrapped = True
        app.mercadolivre_opportunities = ml_wrapper

    if original_central is not None and not getattr(original_central, "_v106_auto_meli", False):
        def central_wrapper(payload):
            payload = dict(payload or {})
            # O modo central V10.6 consulta Mercado Livre automaticamente.
            payload["include_meli"] = True
            print("[V10.6] Motor central iniciado | Mercado Livre automático", flush=True)
            try:
                result = original_central(payload)
                result = _json_safe(result)
                if isinstance(result, dict):
                    result["engine"] = "OFERTA IA V10.6 ML OTIMIZADO"
                    result["meli_mode"] = "automatic"
                    result.setdefault("diagnostic", []).append("V10.6: Mercado Livre consultado automaticamente")
                print("[V10.6] Motor central concluído", flush=True)
                return result
            except Exception as exc:
                message = _error_text(exc)
                print(f"[V10.6][ERRO] Motor central: {message}", flush=True)
                # Retorna HTTP 200 com diagnóstico legível para o painel, evitando
                # que o frontend esconda o erro atrás de 'Erro inesperado'.
                return {
                    "status": "error",
                    "engine": "OFERTA IA V10.6 ML OTIMIZADO",
                    "mode": "completo",
                    "items": [],
                    "opportunities": [],
                    "returned": 0,
                    "candidates_found": 0,
                    "diagnostic": [
                        "V10.6 iniciou a consulta automática do Mercado Livre",
                        f"ERRO REAL: {message}",
                    ],
                    "message": f"⚠️ V10.6 encontrou um erro: {message}",
                }
        central_wrapper._v106_auto_meli = True
        for route in getattr(app.app, "routes", []):
            if getattr(route, "path", None) == "/api/opportunities-central":
                route.endpoint = central_wrapper
                try:
                    from fastapi.dependencies.utils import get_dependant
                    route.dependant = get_dependant(path=route.path, call=central_wrapper)
                    # APIRoute já possui um handler ASGI compilado em route.app.
                    # Recrie-o depois de trocar o endpoint para que o wrapper seja realmente executado.
                    route.app = route.get_route_handler()
                except Exception as exc:
                    print(f"[V10.6][ERRO] Não foi possível reconstruir handler: {_error_text(exc)}", flush=True)
                break

    app.V106_PATCH_ACTIVE = True
    print("[V10.6] Patch ativo", flush=True)
