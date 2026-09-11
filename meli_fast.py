"""V11.10 — Mercado Livre rápido e tolerante a endpoints bloqueados.

O orçamento de chamadas é por requisição, usando contextvars, para que duas
buscas simultâneas não compartilhem nem resetem o orçamento uma da outra.
"""
import contextvars

_INSTALLED = False
_ORIGINAL_GET_ITEM = None
_ORIGINAL_FETCH_JSON = None
_ACTIVE = contextvars.ContextVar("oferta_meli_active", default=False)
_ITEM_CALLS = contextvars.ContextVar("oferta_meli_item_calls", default=0)
MAX_ITEM_DETAIL_CALLS = 8
ITEM_TIMEOUT = 3.0


def _reset_budget(active=False):
    _ACTIVE.set(active)
    _ITEM_CALLS.set(0)


def _reserve_item_call():
    count = int(_ITEM_CALLS.get() or 0)
    if count >= MAX_ITEM_DETAIL_CALLS:
        return False
    _ITEM_CALLS.set(count + 1)
    return True


async def _asgi(scope, receive, send, original):
    if scope.get("type") != "http" or scope.get("path") != "/api/opportunities-central":
        return await original(scope, receive, send)
    token_active = _ACTIVE.set(True)
    token_calls = _ITEM_CALLS.set(0)
    try:
        return await original(scope, receive, send)
    finally:
        _ACTIVE.reset(token_active)
        _ITEM_CALLS.reset(token_calls)


def install(app):
    global _INSTALLED, _ORIGINAL_GET_ITEM, _ORIGINAL_FETCH_JSON
    if _INSTALLED:
        return app

    module = __import__("app")

    if hasattr(module, "_v9_get_item"):
        _ORIGINAL_GET_ITEM = module._v9_get_item

        def guarded_get_item(token, item_id):
            if _ACTIVE.get() and not _reserve_item_call():
                return None
            return _ORIGINAL_GET_ITEM(token, item_id)

        module._v9_get_item = guarded_get_item

    if hasattr(module, "_v9_fetch_json"):
        _ORIGINAL_FETCH_JSON = module._v9_fetch_json

        def guarded_fetch(token, url, params=None, timeout=10, trace=None, stage="HTTP"):
            if _ACTIVE.get() and isinstance(url, str):
                if "/user-products/" in url:
                    return None, 403
                if "/items/" in url:
                    timeout = min(float(timeout), ITEM_TIMEOUT)
            return _ORIGINAL_FETCH_JSON(token, url, params, timeout, trace, stage)

        module._v9_fetch_json = guarded_fetch

    for route in app.routes:
        if getattr(route, "path", None) == "/api/opportunities-central" and hasattr(route, "app"):
            original_route_app = route.app

            async def guarded(scope, receive, send, _original=original_route_app):
                return await _asgi(scope, receive, send, _original)

            route.app = guarded
            break

    _INSTALLED = True
    print(f"[V11.10] Mercado Livre rápido ativo | max_items={MAX_ITEM_DETAIL_CALLS} timeout={ITEM_TIMEOUT}s | orçamento por requisição", flush=True)
    return app
