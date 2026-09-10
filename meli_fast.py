"""V10.10 — Mercado Livre rápido e tolerante a endpoints bloqueados."""
import threading

_INSTALLED = False
_ORIGINAL_GET_ITEM = None
_ORIGINAL_FETCH_JSON = None
_LOCK = threading.Lock()
_ITEM_CALLS = 0
_GLOBAL_ACTIVE = False
MAX_ITEM_DETAIL_CALLS = 8
ITEM_TIMEOUT = 3.0


def _reset_budget(active=False):
    global _ITEM_CALLS, _GLOBAL_ACTIVE
    with _LOCK:
        _ITEM_CALLS = 0
        _GLOBAL_ACTIVE = active


def _reserve_item_call():
    global _ITEM_CALLS
    with _LOCK:
        if _ITEM_CALLS >= MAX_ITEM_DETAIL_CALLS:
            return False
        _ITEM_CALLS += 1
        return True


async def _asgi(scope, receive, send, original):
    if scope.get("type") != "http" or scope.get("path") != "/api/opportunities-central":
        return await original(scope, receive, send)
    _reset_budget(True)
    try:
        return await original(scope, receive, send)
    finally:
        _reset_budget(False)


def install(app):
    global _INSTALLED, _ORIGINAL_GET_ITEM, _ORIGINAL_FETCH_JSON
    if _INSTALLED:
        return app

    module = __import__("app")

    if hasattr(module, "_v9_get_item"):
        _ORIGINAL_GET_ITEM = module._v9_get_item

        def guarded_get_item(token, item_id):
            with _LOCK:
                active = _GLOBAL_ACTIVE
            if active and not _reserve_item_call():
                return None
            return _ORIGINAL_GET_ITEM(token, item_id)

        module._v9_get_item = guarded_get_item

    if hasattr(module, "_v9_fetch_json"):
        _ORIGINAL_FETCH_JSON = module._v9_fetch_json

        def guarded_fetch(token, url, params=None, timeout=10, trace=None, stage="HTTP"):
            with _LOCK:
                active = _GLOBAL_ACTIVE
            if active and isinstance(url, str):
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
    print(f"[V10.10] Mercado Livre rápido ativo | max_items={MAX_ITEM_DETAIL_CALLS} timeout={ITEM_TIMEOUT}s")
    return app
