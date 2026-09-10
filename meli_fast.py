"""V10.10 — Mercado Livre rápido e tolerante a endpoints bloqueados.

O motor V9.8 resolve dezenas de candidatos em ThreadPoolExecutor. O patch
anterior dependia de ContextVar, que não limita chamadas feitas em threads.
Aqui o limite é aplicado diretamente aos helpers do app, de forma global e
thread-safe durante cada garimpo.
"""
import threading
from contextvars import ContextVar
import requests

_ACTIVE = ContextVar("oferta_meli_fast_active", default=False)
_INSTALLED = False
_ORIGINAL_GET_ITEM = None
_ORIGINAL_CATALOG_TO_ITEM = None
_LOCK = threading.Lock()
_ITEM_CALLS = 0

MAX_ITEM_DETAIL_CALLS = 8
ITEM_TIMEOUT = 3.0


def _reset_budget():
    global _ITEM_CALLS
    with _LOCK:
        _ITEM_CALLS = 0


def _reserve_item_call():
    global _ITEM_CALLS
    with _LOCK:
        if _ITEM_CALLS >= MAX_ITEM_DETAIL_CALLS:
            return False
        _ITEM_CALLS += 1
        return True


def _fast_get_item(app_module, token, item_id):
    if _ACTIVE.get():
        if not _reserve_item_call():
            return None
    return _ORIGINAL_GET_ITEM(token, item_id)


async def _asgi(scope, receive, send, original):
    if scope.get("type") != "http" or scope.get("path") != "/api/opportunities-central":
        return await original(scope, receive, send)

    _reset_budget()
    token_active = _ACTIVE.set(True)
    try:
        return await original(scope, receive, send)
    finally:
        _ACTIVE.reset(token_active)
        _reset_budget()


def install(app):
    global _INSTALLED, _ORIGINAL_GET_ITEM, _ORIGINAL_CATALOG_TO_ITEM
    if _INSTALLED:
        return app

    module = __import__(app.title and "app" or "app")
    if hasattr(module, "_v9_get_item"):
        _ORIGINAL_GET_ITEM = module._v9_get_item

        def guarded_get_item(token, item_id):
            if _ACTIVE.get() and not _reserve_item_call():
                return None
            return _ORIGINAL_GET_ITEM(token, item_id)

        module._v9_get_item = guarded_get_item

    # Evita o endpoint user-products, que está retornando 403 e não é necessário
    # para o ranking rápido. O fluxo de PRODUCT continua usando catálogo.
    if hasattr(module, "_v9_fetch_json"):
        original_fetch = module._v9_fetch_json

        def guarded_fetch(token, url, params=None, timeout=10, trace=None, stage="HTTP"):
            if _ACTIVE.get() and isinstance(url, str) and "/user-products/" in url:
                return None, 403
            if _ACTIVE.get() and isinstance(url, str) and "/items/" in url:
                timeout = min(float(timeout), ITEM_TIMEOUT)
            return original_fetch(token, url, params, timeout, trace, stage)

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
