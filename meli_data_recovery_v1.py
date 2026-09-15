"""OFERTA IA V12.5 — recuperação de dados reais do item Mercado Livre.

Corrige um problema do núcleo V11.8: o índice local podia conter o item vencedor
sem sold_quantity e _v11_synthetic_item convertia essa ausência em 0. Isso fazia
os fallbacks aceitarem um zero sintético como se fosse venda real.

A recuperação tenta primeiro a busca pública do ITEM, que é compatível com o
bloqueio atual de GET /items/{id}. Só depois cai no comportamento legado.
Nunca transforma ausência de vendas em zero.
"""
import re

_V125_ORIGINAL_FETCH_JSON = _v11_fetch_json


def _v125_fetch_json(token, url, params=None, timeout=10, trace=None, stage="HTTP"):
    text = str(url or "")
    match = re.search(r"/items/(ML[A-Z][0-9]+)(?:/|$)", text, re.I)
    is_direct_item = bool(match and "/products/" not in text.lower())
    if is_direct_item:
        item_id = match.group(1).upper()
        try:
            public_search = globals().get("_v11_public_search")
            if callable(public_search):
                data, status = public_search(token, item_id, trace=trace)
                if isinstance(data, dict) and data:
                    with _V11_LOCK:
                        _V11_ITEM_INDEX[item_id] = dict(data)
                    return data, int(status or 200)
        except Exception:
            pass

        try:
            data, status = _V125_ORIGINAL_FETCH_JSON(
                token, url, params=params, timeout=timeout, trace=trace, stage=stage
            )
            # O fallback legado pode devolver um item sintético com sold_quantity=0
            # apenas porque o índice não tinha esse campo. Retiramos esse zero
            # quando ele não veio de uma fonte real.
            if isinstance(data, dict) and int(status or 0) == 200:
                with _V11_LOCK:
                    cached = dict(_V11_ITEM_INDEX.get(item_id, {}))
                if "sold_quantity" not in cached and data.get("sold_quantity") == 0:
                    clean = dict(data)
                    clean.pop("sold_quantity", None)
                    clean.pop("sales", None)
                    clean.pop("sales_count", None)
                    return clean, status
            return data, status
        except Exception:
            return None, None

    return _V125_ORIGINAL_FETCH_JSON(
        token, url, params=params, timeout=timeout, trace=trace, stage=stage
    )


_v11_fetch_json = _v125_fetch_json
print("[V12.5] recuperação ITEM ativa | busca pública antes do índice sintético | zero sintético eliminado", flush=True)
