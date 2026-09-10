"""Patch OFERTA IA V10.6 para priorizar Mercado Livre por nicho e ativar consulta automática."""
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
            if "include_meli" not in payload:
                payload["include_meli"] = True
            result = original_central(payload)
            if isinstance(result, dict):
                result["engine"] = "OFERTA IA V10.6 ML OTIMIZADO"
            return result
        central_wrapper._v106_auto_meli = True
        for route in getattr(app.app, "routes", []):
            if getattr(route, "path", None) == "/api/opportunities-central":
                route.endpoint = central_wrapper
                try:
                    from fastapi.dependencies.utils import get_dependant
                    route.dependant = get_dependant(path=route.path, call=central_wrapper)
                except Exception:
                    pass
                break

    app.V106_PATCH_ACTIVE = True
