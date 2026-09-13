"""V11.11.13 — fallback de avaliações com tentativa única global.

A V11.11.12 confirmou que a chamada sem catalog_product_id também retorna 403.
O problema restante era o fallback limpar o bloqueio e repetir a tentativa para
cada candidato. Esta versão permite somente uma tentativa de fallback por boot.
"""

_original_reviews_v113 = _v111_reviews
_V113_FALLBACK_ATTEMPTED = False


def _v113_reviews(item_id, product_id, token):
    global _V111_REVIEWS_BLOCKED, _V113_FALLBACK_ATTEMPTED
    if not item_id or not token:
        return None

    result = _original_reviews_v113(item_id, product_id, token)
    if result is not None:
        return result

    # O núcleo já marcou 401/403 como bloqueio. Fazemos apenas uma tentativa
    # adicional, sem catalog_product_id, para validar se o bloqueio depende do filtro.
    if _V113_FALLBACK_ATTEMPTED or not _V111_REVIEWS_BLOCKED:
        return None

    _V113_FALLBACK_ATTEMPTED = True
    url = f"https://api.mercadolibre.com/reviews/item/{item_id}"
    try:
        data, status = _v11_fetch_json(
            token,
            url,
            timeout=5,
            stage="REVIEWS_V11_13_FALLBACK",
        )
        status = int(status or 0)
        if isinstance(data, dict) and 200 <= status < 300:
            _V111_REVIEWS_CACHE[f"{item_id}|{product_id}"] = (time.time(), data)
            _V111_STATS["reviews_ok"] += 1
            _V111_REVIEWS_BLOCKED = False
            print(
                f"[V11.11.13] reviews fallback sem catalog_product_id: "
                f"item={item_id} ok=1",
                flush=True,
            )
            return data
        if status in (401, 403):
            _V111_REVIEWS_BLOCKED = True
            print(
                f"[V11.11.13] reviews fallback bloqueado definitivamente: "
                f"item={item_id} http={status}",
                flush=True,
            )
        else:
            print(
                f"[V11.11.13] reviews fallback sem dados: "
                f"item={item_id} http={status}",
                flush=True,
            )
    except Exception as exc:
        _V111_REVIEWS_BLOCKED = True
        print(
            f"[V11.11.13] reviews fallback erro: item={item_id} "
            f"error={type(exc).__name__}: {str(exc)[:250]}",
            flush=True,
        )
    return None


_v111_reviews = _v113_reviews
print("[V11.11.13] fallback de avaliações com tentativa única ativo", flush=True)
