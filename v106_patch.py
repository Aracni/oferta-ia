"""OFERTA IA V10.6 — otimização segura do Mercado Livre.

Preserva o app.py existente e aplica melhorias por monkey-patch:
- prioriza categoria oficial do Mercado Livre quando o nicho é conhecido;
- ativa o Mercado Livre no motor central, evitando o modo rápido por padrão;
- mantém score, autenticação, Shopee e interface existentes.
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
    original_ml = app_module.mercadolivre_opportunities
    original_central = app_module.opportunities_central

    def optimized_ml(payload: dict):
        payload = dict(payload or {})
        niche = _normalize(payload.get("niche"))
        preferred = CATEGORY_HINTS.get(niche)

        if preferred and not payload.get("category_id"):
            payload["category_id"] = preferred

        result = original_ml(payload)
        if isinstance(result, dict):
            result["engine"] = "OFERTA IA V10.6 ML OTIMIZADO"
            result["optimization"] = (
                "Categoria Mercado Livre priorizada pelo nicho; "
                "enriquecimento progressivo preservado."
            )
        return result

    def optimized_central(payload: dict):
        # O painel usa o motor central. No V10.6, Mercado Livre deixa de ser
        # opcional no modo rápido e passa a participar automaticamente.
        payload = dict(payload or {})
        payload["include_meli"] = True
        result = original_central(payload)
        if isinstance(result, dict):
            result["engine"] = "OFERTA IA V10.6 CENTRAL"
            result["mode"] = "completo"
            result["optimization"] = "Shopee + Mercado Livre consultados automaticamente."
        return result

    app_module.mercadolivre_opportunities = optimized_ml
    app_module.opportunities_central = optimized_central

    # As rotas FastAPI guardam referências diretas às funções. Atualizamos
    # somente os dois endpoints envolvidos, sem substituir o app.py inteiro.
    targets = {
        "/api/mercadolivre/opportunities": optimized_ml,
        "/api/opportunities-central": optimized_central,
    }
    for route in app_module.app.router.routes:
        endpoint = targets.get(getattr(route, "path", None))
        if endpoint is None:
            continue
        route.endpoint = endpoint
        if hasattr(route, "dependant"):
            try:
                from fastapi.dependencies.utils import get_dependant
                route.dependant = get_dependant(path=route.path, call=endpoint)
            except Exception:
                pass

    return optimized_central
