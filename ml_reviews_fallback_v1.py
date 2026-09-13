"""V11.11.12 — fallback seguro para avaliações do Mercado Livre.

A documentação oficial aceita catalog_product_id como parâmetro opcional.
Se a chamada filtrada retornar 401/403, tenta uma única vez a consulta do item
sem o filtro de catálogo antes de considerar a API de avaliações bloqueada.
"""

_original_reviews_v112 = _v111_reviews


def _v112_reviews(item_id, product_id, token):
    global _V111_REVIEWS_BLOCKED
    if not item_id or not token:
        return None

    # Primeiro preserva o comportamento já validado da V11.11.
    result = _original_reviews_v112(item_id, product_id, token)
    if result is not None:
        return result

    # Se a primeira tentativa foi bloqueada, libera apenas esta segunda tentativa.
    # O fallback não faz loop: no máximo duas chamadas para o mesmo item.
    if not _V111_REVIEWS_BLOCKED:
        return None

    _V111_REVIEWS_BLOCKED = False
    url = f"https://api.mercadolibre.com/reviews/item/{item_id}"
    try:
        data, status = _v11_fetch_json(
            token,
            url,
            timeout=5,
            stage="REVIEWS_V11_12_FALLBACK",
        )
        status = int(status or 0)
        if isinstance(data, dict) and 200 <= status < 300:
            _V111_REVIEWS_CACHE[f"{item_id}|{product_id}"] = (time.time(), data)
            _V111_STATS["reviews_ok"] += 1
            print(
                f"[V11.11.12] reviews fallback sem catalog_product_id: "
                f"item={item_id} ok=1",
                flush=True,
            )
            return data
        if status in (401, 403):
            _V111_REVIEWS_BLOCKED = True
            print(
                f"[V11.11.12] reviews fallback bloqueado: item={item_id} http={status}",
                flush=True,
            )
    except Exception as exc:
        _V111_REVIEWS_BLOCKED = True
        print(
            f"[V11.11.12] reviews fallback erro: item={item_id} "
            f"error={type(exc).__name__}: {str(exc)[:250]}",
            flush=True,
        )
    return None


_v111_reviews = _v112_reviews
print("[V11.11.12] fallback de avaliações sem catalog_product_id ativo", flush=True)
