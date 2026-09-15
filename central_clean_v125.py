"""OFERTA IA V12.5 — endpoint central limpo, sem cadeia recursiva de wrappers.

O boot V12.5 acumulou wrappers de versões anteriores sobre a mesma rota. Em
runtime isso podia fazer o motor central entrar em RecursionError antes do
enriquecimento. Este patch mantém os núcleos originais como pontos de entrada
e usa somente o enriquecimento final já instalado.
"""
from fastapi import Body


def _v125_clean_central(payload: dict = Body(default={} )):
    body = dict(payload or {})
    selected = str(body.get("marketplaces") or "both").lower().strip()
    if selected not in {"both", "mercadolivre", "shopee"}:
        selected = "both"
    try:
        limit = max(5, min(20, int(body.get("limit") or 10)))
    except Exception:
        limit = 10

    # Mantém a renovação automática, mas sem adicionar outro wrapper à rota.
    try:
        ensure = getattr(app, "_meli_auto_ensure", None)
        if callable(ensure):
            ok, reason = ensure(False)
            if not ok:
                print(f"[V12.5][MELI] conexão indisponível: {reason}", flush=True)
    except Exception:
        pass

    diagnostics = []

    if selected == "mercadolivre":
        ml_result = _V119_ORIGINAL_ML({"niche": body.get("niche") or "", "limit": limit})
        items = list(ml_result.get("items") or ml_result.get("opportunities") or [])[:limit]
        diagnostics.extend(list(ml_result.get("diagnostic") or []))
        diagnostics.append(f"Filtro: somente Mercado Livre · retorno={len(items)}")
    elif selected == "shopee":
        sh_result = _V119_ORIGINAL_OPPORTUNITIES_CENTRAL(body)
        items = list(sh_result.get("items") or sh_result.get("opportunities") or [])
        items = [x for x in items if str(x.get("marketplace") or "").lower() == "shopee"][:limit]
        diagnostics.extend(list(sh_result.get("diagnostic") or []))
        diagnostics.append(f"Filtro: somente Shopee · retorno={len(items)}")
    else:
        base_result = _V119_ORIGINAL_CENTRAL({**body, "include_meli": True})
        items = list(base_result.get("items") or base_result.get("opportunities") or [])[:limit]
        diagnostics.extend(list(base_result.get("diagnostic") or []))
        diagnostics.append(f"Filtro: Ambos · candidatos={len(items)}")

    # Uma única cadeia de enriquecimento: V11.11.6 -> vendas -> sinais -> V12.3.
    final_enrich = globals().get("_v119_enrich_ml")
    if callable(final_enrich):
        items = final_enrich(items)

    items = list(items or [])[:limit]
    ml_count = sum(1 for x in items if str(x.get("marketplace") or "").lower() == "mercadolivre")
    sh_count = sum(1 for x in items if str(x.get("marketplace") or "").lower() == "shopee")
    diagnostics.append(f"V12.5 clean: Mercado Livre={ml_count} · Shopee={sh_count} · retorno={len(items)}")

    return {
        "status": "ok",
        "mode": "mercadolivre" if selected == "mercadolivre" else "shopee" if selected == "shopee" else "completo",
        "engine": "OFERTA IA V12.5",
        "items": items,
        "opportunities": items,
        "returned": len(items),
        "candidates_found": len(items),
        "diagnostic": diagnostics,
        "message": " · ".join(str(x) for x in diagnostics),
    }


_v119_central = _v125_clean_central

for _route in getattr(app, "routes", []):
    if getattr(_route, "path", None) == "/api/opportunities-central" and "POST" in (getattr(_route, "methods", set()) or set()):
        try:
            from fastapi.dependencies.utils import get_dependant
            from fastapi.routing import request_response
            _route.endpoint = _v125_clean_central
            _route.dependant = get_dependant(path=_route.path, call=_v125_clean_central)
            _route.app = request_response(_route.get_route_handler())
            print("[V12.5] rota central limpa | cadeia recursiva removida", flush=True)
        except Exception as exc:
            print(f"[V12.5][ERRO] rota central limpa não instalada: {type(exc).__name__}: {str(exc)[:300]}", flush=True)
        break

print("[V12.5] motor central limpo ativo | sem wrappers recursivos", flush=True)
