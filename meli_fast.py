"""V10.9 — Mercado Livre rápido e tolerante a endpoints bloqueados.

Este patch não altera OAuth nem os resultados da Shopee. Durante o motor central,
limita chamadas de enriquecimento do Mercado Livre e aplica timeouts curtos.
Chamadas que sabemos que podem retornar 403 são encerradas imediatamente, sem
ficar aguardando dezenas de requisições desnecessárias.
"""
from contextvars import ContextVar
from urllib.parse import urlparse
import requests

_ACTIVE = ContextVar("oferta_meli_fast_active", default=False)
_COUNT = ContextVar("oferta_meli_fast_count", default=0)
_INSTALLED = False
_ORIGINAL_REQUEST = None

# Limites conservadores: preservam alguns detalhes sem permitir que o ML trave o garimpo.
MAX_ITEM_DETAIL_CALLS = 10
ITEM_TIMEOUT = 2.5
PRODUCT_TIMEOUT = 3.5
SEARCH_TIMEOUT = 4.0


def _blocked_response(url: str):
    response = requests.Response()
    response.status_code = 403
    response.url = url
    response.reason = "Fast guard: endpoint ignorado"
    response._content = b'{"message":"Mercado Livre endpoint skipped by performance guard"}'
    response.headers["content-type"] = "application/json"
    return response


def _request(self, method, url, **kwargs):
    if _ACTIVE.get() and isinstance(url, str) and "api.mercadolibre.com" in url:
        path = urlparse(url).path or ""

        # Este endpoint não é necessário para o ranking público e estava gerando 403.
        if "/user-products/" in path:
            return _blocked_response(url)

        # Enriquecimento individual é o principal causador de lentidão/403.
        if "/items/" in path:
            count = _COUNT.get()
            if count >= MAX_ITEM_DETAIL_CALLS:
                return _blocked_response(url)
            _COUNT.set(count + 1)
            kwargs["timeout"] = min(float(kwargs.get("timeout", ITEM_TIMEOUT)), ITEM_TIMEOUT)

        elif "/products/" in path:
            kwargs["timeout"] = min(float(kwargs.get("timeout", PRODUCT_TIMEOUT)), PRODUCT_TIMEOUT)
        else:
            kwargs["timeout"] = min(float(kwargs.get("timeout", SEARCH_TIMEOUT)), SEARCH_TIMEOUT)

    return _ORIGINAL_REQUEST(self, method, url, **kwargs)


async def _asgi(scope, receive, send, original):
    if scope.get("type") != "http" or scope.get("path") != "/api/opportunities-central":
        return await original(scope, receive, send)

    token_active = _ACTIVE.set(True)
    token_count = _COUNT.set(0)
    try:
        return await original(scope, receive, send)
    finally:
        _COUNT.reset(token_count)
        _ACTIVE.reset(token_active)


def install(app):
    global _INSTALLED, _ORIGINAL_REQUEST
    if _INSTALLED:
        return app

    _ORIGINAL_REQUEST = requests.sessions.Session.request
    requests.sessions.Session.request = _request

    for route in app.routes:
        if getattr(route, "path", None) == "/api/opportunities-central" and hasattr(route, "app"):
            original = route.app

            async def guarded(scope, receive, send, _original=original):
                return await _asgi(scope, receive, send, _original)

            route.app = guarded
            break

    _INSTALLED = True
    print(
        f"[V10.9] Mercado Livre rápido ativo | itens={MAX_ITEM_DETAIL_CALLS} "
        f"timeout_item={ITEM_TIMEOUT}s timeout_produto={PRODUCT_TIMEOUT}s"
    )
    return app
