"""OFERTA IA V12.4 — diagnóstico interno do motor de oportunidade.

Endpoint GET para testar o pipeline real sem depender do clique do usuário.
Não cria dados e não altera resultados; apenas executa o mesmo central usado pela UI.
"""
from fastapi import Query
from fastapi.responses import JSONResponse


def _v124_install(app_module):
    app = app_module.app
    if any(getattr(route, "path", None) == "/api/diagnostic/opportunity" for route in app.routes):
        return

    @app.get("/api/diagnostic/opportunity", include_in_schema=False)
    async def _v124_diagnostic(marketplaces: str = Query(default="mercadolivre")):
        try:
            market = str(marketplaces or "mercadolivre").strip().lower()
            if market not in {"both", "mercadolivre", "shopee"}:
                market = "mercadolivre"
            central = getattr(app_module, "_v119_central", None)
            if not callable(central):
                raise RuntimeError("motor central V11/V12 não disponível")
            result = central({"marketplaces": market})
            if not isinstance(result, dict):
                raise RuntimeError("motor central retornou resposta inválida")
            items = result.get("items") or result.get("opportunities") or []
            summary = []
            for item in items[:10]:
                if not isinstance(item, dict):
                    continue
                summary.append({
                    "name": item.get("name") or item.get("title"),
                    "marketplace": item.get("marketplace"),
                    "score": item.get("opportunity_score"),
                    "class": item.get("opportunity_class"),
                    "coverage": item.get("opportunity_data_coverage"),
                    "provisional": item.get("opportunity_is_provisional"),
                    "reasons": item.get("opportunity_reasons") or [],
                    "sales": item.get("sold_quantity"),
                    "discount": item.get("discount_rate"),
                    "rating": item.get("rating"),
                    "competition": item.get("competition_signal"),
                })
            return JSONResponse({
                "status": result.get("status", "ok"),
                "marketplaces": market,
                "returned": result.get("returned", len(summary)),
                "diagnostic": result.get("diagnostic") or [],
                "items": summary,
            })
        except Exception as exc:
            return JSONResponse({
                "status": "error",
                "error": f"{type(exc).__name__}: {str(exc)[:500]}",
            }, status_code=500)

    print("[V12.4] diagnóstico real do motor de oportunidade disponível", flush=True)
