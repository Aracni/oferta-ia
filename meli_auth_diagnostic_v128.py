"""OFERTA IA V12.8.1 — diagnóstico seguro da autorização Mercado Livre.
Nunca registra access_token, refresh_token ou client_secret.
"""
import os
import requests
from fastapi import Query


def _safe_error(response):
    try:
        data = response.json()
        if isinstance(data, dict):
            return {
                "message": str(data.get("message") or data.get("error_description") or data.get("error") or "")[:180],
                "error": str(data.get("error") or "")[:80],
                "cause": str(data.get("cause") or "")[:180],
            }
    except Exception:
        pass
    text = (response.text or "").strip()
    return {"message": text[:180]}


def _connection():
    getter = globals().get("_get_connection")
    if not callable(getter):
        return None
    try:
        return getter("mercadolivre")
    except Exception:
        return None


def _token_from_connection(conn):
    if not isinstance(conn, dict):
        return None
    return conn.get("access_token") or conn.get("token")


def _probe(url, token):
    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "OFERTA-IA/12.8.1"},
            timeout=8,
        )
        return {"status": r.status_code, "ok": bool(r.ok), "error": None if r.ok else _safe_error(r)}
    except Exception as exc:
        return {"status": None, "ok": False, "error": {"type": type(exc).__name__, "message": str(exc)[:180]}}


def _run_probe(item_id=None):
    conn = _connection()
    token = _token_from_connection(conn)
    result = {
        "connection_record": bool(conn),
        "access_token_present": bool(token),
        "refresh_token_present": bool(isinstance(conn, dict) and conn.get("refresh_token")),
        "user": None,
        "application": None,
        "grants": None,
        "item": None,
    }
    if not token:
        return result

    user = _probe("https://api.mercadolibre.com/users/me", token)
    result["user"] = user
    user_id = None
    if user.get("ok"):
        try:
            # Repeats no secret; only the numeric user id is used for the grants probe.
            rr = requests.get(
                "https://api.mercadolibre.com/users/me",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "OFERTA-IA/12.8.1"},
                timeout=8,
            )
            if rr.ok:
                body = rr.json()
                user_id = body.get("id") if isinstance(body, dict) else None
        except Exception:
            user_id = None

    app_id = os.environ.get("MELI_CLIENT_ID") or os.environ.get("MERCADOLIVRE_APP_ID")
    if app_id:
        result["application"] = _probe(f"https://api.mercadolibre.com/applications/{app_id}", token)
    if user_id:
        result["grants"] = _probe(f"https://api.mercadolibre.com/users/{user_id}/applications", token)
    if item_id and isinstance(item_id, str) and item_id.upper().startswith("MLB"):
        item_id = item_id.upper()
        result["item"] = _probe(f"https://api.mercadolibre.com/items/{item_id}?include_attributes=all", token)
    return result


def install(app):
    @app.get("/api/mercadolivre/diagnostico-v128", include_in_schema=False)
    async def _diagnostico_v128(item_id: str | None = Query(default=None, max_length=32)):
        return _run_probe(item_id)

    try:
        r = _run_probe()
        user_status = (r.get("user") or {}).get("status")
        app_status = (r.get("application") or {}).get("status")
        grant_status = (r.get("grants") or {}).get("status")
        print(
            "[V12.8.1] OAuth ML diagnóstico: "
            f"record={r['connection_record']} token={r['access_token_present']} refresh={r['refresh_token_present']} "
            f"users_me={user_status} app={app_status} grants={grant_status}",
            flush=True,
        )
        for name in ("user", "application", "grants"):
            part = r.get(name) or {}
            if part.get("status") and part.get("status") >= 400:
                print(f"[V12.8.1] OAuth ML {name}: status={part.get('status')} error={part.get('error')}", flush=True)
    except Exception as exc:
        print(f"[V12.8.1][WARN] diagnóstico OAuth: {type(exc).__name__}: {str(exc)[:240]}", flush=True)

    print("[V12.8.1] diagnóstico OAuth Mercado Livre instalado", flush=True)
