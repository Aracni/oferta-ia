"""OFERTA IA — renovação automática da autorização do Mercado Livre.

Não expõe tokens ao navegador. Aproveita a autorização já salva no Supabase,
renova o access_token pelo refresh_token quando necessário e mantém a interface
indicando conexão real.
"""
import os
from datetime import datetime, timezone, timedelta

import requests


def _log(app, message, **fields):
    try:
        safe = {k: v for k, v in fields.items() if k not in {"access_token", "refresh_token", "client_secret", "token"}}
        suffix = " | " + " ".join(f"{k}={v}" for k, v in safe.items()) if safe else ""
        logger = getattr(app, "_oferta_logger", None)
        if logger:
            logger.info("[MELI_AUTO] %s%s", message, suffix)
        buffer = getattr(app, "_V94_LOG_BUFFER", None)
        if isinstance(buffer, list):
            buffer.append(f"{datetime.now().strftime('%H:%M:%S')} | MELI_AUTO | {message}{suffix}")
    except Exception:
        pass


def _refresh(app, connection):
    refresh_token = connection.get("refresh_token")
    client_id = os.getenv("MELI_CLIENT_ID")
    client_secret = os.getenv("MELI_CLIENT_SECRET")
    if not refresh_token or not client_id or not client_secret:
        return False, "refresh_token ou credenciais do Mercado Livre ausentes"

    response = requests.post(
        "https://api.mercadolibre.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
        timeout=20,
    )
    if not response.ok:
        try:
            body = response.json()
            detail = body.get("error_description") or body.get("message") or body.get("error")
        except Exception:
            detail = response.text[:250]
        return False, f"Mercado Livre recusou a renovação (HTTP {response.status_code}): {detail}"

    token = response.json()
    access_token = token.get("access_token")
    new_refresh = token.get("refresh_token") or refresh_token
    if not access_token:
        return False, "Mercado Livre não retornou novo access_token"

    expires_in = int(token.get("expires_in") or 21600)
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
    app._save_connection("mercadolivre", {
        "status": "connected",
        "access_token": access_token,
        "refresh_token": new_refresh,
        "expires_at": expires_at,
        "user_id": str(token.get("user_id") or connection.get("user_id") or ""),
    })
    _log(app, "Token do Mercado Livre renovado automaticamente", expires_in=expires_in)
    return True, "renovado"


def ensure(app, force=False):
    """Garante um access token utilizável; retorna (ok, motivo)."""
    connection = app._get_connection("mercadolivre")
    if not connection:
        return False, "nenhuma conexão do Mercado Livre salva"
    access_token = connection.get("access_token")
    if not access_token:
        return False, "conexão salva sem access_token"

    expires_at = connection.get("expires_at")
    needs_refresh = force
    if not needs_refresh and expires_at:
        try:
            exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            needs_refresh = exp <= datetime.now(timezone.utc) + timedelta(minutes=2)
        except Exception:
            pass

    if needs_refresh:
        ok, reason = _refresh(app, connection)
        if ok:
            return True, reason
        return False, reason

    # Validação barata: se o token já foi revogado, tenta o refresh automaticamente.
    try:
        r = requests.get(
            "https://api.mercadolibre.com/users/me",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=10,
        )
        if r.status_code == 401:
            ok, reason = _refresh(app, connection)
            if ok:
                return True, reason
            return False, reason
        if r.ok:
            return True, "válido"
    except Exception as exc:
        _log(app, "Falha temporária ao validar token; mantendo conexão salva", error=type(exc).__name__)
        return True, "validação temporariamente indisponível"

    return True, "válido"


def _rebuild(route, endpoint):
    from fastapi.dependencies.utils import get_dependant
    from fastapi.routing import request_response
    route.endpoint = endpoint
    route.dependant = get_dependant(path=route.path, call=endpoint)
    route.app = request_response(route.get_route_handler())


def install(app):
    # Expõe helpers no objeto FastAPI para uso pelos wrappers.
    app._meli_auto_ensure = lambda force=False: ensure(app, force)
    app._meli_auto_refresh = lambda: ensure(app, True)

    # 1) Status: valida/renova antes de informar ao navegador.
    for route in getattr(app, "routes", []):
        if getattr(route, "path", None) == "/api/integrations/status" and not getattr(route.endpoint, "_meli_auto_status", False):
            original = route.endpoint
            def status_wrapper(original=original):
                ok, reason = ensure(app)
                result = dict(original() or {})
                meli = dict(result.get("mercadolivre") or {})
                meli["connected"] = bool(ok)
                meli["automatic"] = True
                meli["message"] = "Conexão automática ativa" if ok else reason
                result["mercadolivre"] = meli
                return result
            status_wrapper._meli_auto_status = True
            _rebuild(route, status_wrapper)
            break

    # 2) Motor central: renova antes da busca. A V10.8 já força include_meli=true.
    for route in getattr(app, "routes", []):
        if getattr(route, "path", None) == "/api/opportunities-central" and not getattr(route.endpoint, "_meli_auto_refresh_wrapper", False):
            original = route.endpoint
            def central_wrapper(payload: dict, original=original):
                ok, reason = ensure(app)
                if not ok:
                    _log(app, "Mercado Livre não pôde ser renovado", reason=reason)
                return original(payload)
            central_wrapper._meli_auto_refresh_wrapper = True
            _rebuild(route, central_wrapper)
            break

    # 3) Interface: esconde o botão de conectar enquanto a autorização estiver válida.
    # Se a autorização for perdida, o próprio painel volta a oferecer a conexão.
    try:
        import app as app_module
        html = getattr(app_module, "HTML", "")
        old = "$('connectedStatus').textContent=ok?'OK':'—';$('meliStatus').textContent=ok?'🟢 Mercado Livre conectado.':'🟡 Mercado Livre não conectado.';"
        new = "$('connectedStatus').textContent=ok?'OK':'—';$('meliStatus').textContent=ok?'🟢 Mercado Livre conectado automaticamente.':'🟡 Mercado Livre não conectado.';$('meliConnectBtn').style.display=ok?'none':'inline-block';"
        if old in html:
            app_module.HTML = html.replace(old, new)
            _log(app, "Interface atualizada: botão Conectar só aparece quando necessário")
        else:
            _log(app, "Não foi possível localizar o trecho visual do botão Conectar")
    except Exception as exc:
        _log(app, "Falha ao ajustar interface", error=type(exc).__name__)

    _log(app, "Renovação automática do Mercado Livre instalada")
