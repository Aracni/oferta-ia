"""OFERTA IA V10.6 — otimização segura do Mercado Livre.

Este módulo preserva o app.py existente e aplica a melhoria V10.6 por
monkey-patch: nichos conhecidos passam a priorizar a categoria oficial do
Mercado Livre antes dos fallbacks. A lógica original de validação, score,
tokens e interface permanece intacta.
"""
import unicodedata

CATEGORY_HINTS = {
    "eletronicos": "MLB1000",
    "eletronico": "MLB1000",
    "beleza": "MLB1246",
    "casa": "MLB1574",
    "fitness": "MLB1276",
    "moda": "MLB1430",
}


def _normalize(value):
    value = (value or "").strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(c)
    )


def install(app_module):
    original = app_module.mercadolivre_opportunities

    def optimized(payload: dict):
        payload = dict(payload or {})
        niche = _normalize(payload.get("niche"))
        preferred = CATEGORY_HINTS.get(niche)

        if preferred and not payload.get("category_id"):
            payload["category_id"] = preferred

        result = original(payload)
        if isinstance(result, dict):
            result["engine"] = "OFERTA IA V10.6 ML OTIMIZADO"
            result["optimization"] = (
                "Categoria Mercado Livre priorizada pelo nicho; "
                "enriquecimento progressivo preservado."
            )
        return result

    app_module.mercadolivre_opportunities = optimized

    # A rota já criada pelo FastAPI guarda uma referência direta à função.
    # Trocamos somente essa referência para que chamadas HTTP também usem
    # a versão otimizada.
    target_path = "/api/mercadolivre/opportunities"
    for route in app_module.app.router.routes:
        if getattr(route, "path", None) == target_path:
            route.endpoint = optimized
            if hasattr(route, "dependant"):
                try:
                    from fastapi.dependencies.utils import get_dependant
                    route.dependant = get_dependant(path=route.path, call=optimized)
                except Exception:
                    pass

    return optimized
