"""OFERTA IA V13 — vendas reais somente pela conta Mercado Livre autorizada.

Fonte: /orders/search filtrada pelo seller do usuário OAuth.
Nunca usa sold_quantity de anúncios de terceiros e nunca transforma ranking/demanda em vendas.
"""
from datetime import datetime, timedelta, timezone
import re
import requests
from fastapi import Query

_V13_STATS = {"orders_requests": 0, "orders_ok": 0, "orders_errors": 0, "units_found": 0, "items_matched": 0}


def _token():
    fn = globals().get("_v9_valid_meli_token")
    if callable(fn):
        try:
            return fn()
        except Exception:
            pass
    conn_fn = globals().get("_get_connection")
    if callable(conn_fn):
        try:
            conn = conn_fn("mercadolivre") or {}
            return conn.get("access_token") or conn.get("token")
        except Exception:
            pass
    return None


def _item_id(value):
    if value is None:
        return None
    m = re.search(r"\bMLB\d+\b", str(value).upper())
    return m.group(0) if m else None


def _seller_id(token):
    try:
        r = requests.get("https://api.mercadolibre.com/users/me", headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "OFERTA-IA/13.0"}, timeout=8)
        if r.ok:
            body = r.json()
            return body.get("id") if isinstance(body, dict) else None
    except Exception:
        pass
    return None


def _load_authorized_sales():
    token = _token()
    if not token:
        return {}, {"status": None, "error": "token_missing"}
    seller = _seller_id(token)
    if not seller:
        return {}, {"status": None, "error": "seller_id_unavailable"}
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)
    params = {
        "seller": str(seller),
        "order.status": "paid",
        "order.date_closed.from": start.isoformat().replace("+00:00", "Z"),
        "order.date_closed.to": now.isoformat().replace("+00:00", "Z"),
        "sort": "date_desc",
        "limit": "50",
        "offset": "0",
    }
    _V13_STATS["orders_requests"] += 1
    try:
        r = requests.get("https://api.mercadolibre.com/orders/search", params=params, headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "OFERTA-IA/13.0"}, timeout=12)
        if not r.ok:
            _V13_STATS["orders_errors"] += 1
            return {}, {"status": r.status_code, "error": "orders_search_forbidden_or_failed"}
        body = r.json()
        totals = {}
        for order in (body.get("results") or []):
            if not isinstance(order, dict):
                continue
            for oi in (order.get("order_items") or []):
                if not isinstance(oi, dict):
                    continue
                item = oi.get("item") or {}
                iid = _item_id(item.get("id") or oi.get("item_id"))
                qty = oi.get("quantity")
                if iid and isinstance(qty, (int, float)) and qty >= 0:
                    totals[iid] = totals.get(iid, 0) + qty
        _V13_STATS["orders_ok"] += 1
        _V13_STATS["units_found"] += int(sum(totals.values()))
        return totals, {"status": 200, "seller_id": seller, "orders": len(body.get("results") or []), "paging_total": (body.get("paging") or {}).get("total")}
    except Exception as exc:
        _V13_STATS["orders_errors"] += 1
        return {}, {"status": None, "error": type(exc).__name__}


def _v13_enrich(items):
    original = globals().get("_v119_enrich_ml")
    if callable(original) and not getattr(original, "_v13_wrapped", False):
        try:
            items = original(items)
        except Exception as exc:
            print(f"[V13][WARN] enriquecimento anterior: {type(exc).__name__}: {str(exc)[:180]}", flush=True)
    try:
        sales, meta = _load_authorized_sales()
        matched = 0
        for item in items or []:
            iid = _item_id((item or {}).get("id") or (item or {}).get("item_id") or (item or {}).get("url"))
            if iid in sales:
                qty = sales[iid]
                item["sold_quantity"] = int(qty)
                item["sales"] = int(qty)
                item["sales_count"] = int(qty)
                item["sales_source"] = "orders_authorized_30d"
                item["sales_period_days"] = 30
                item["sales_authorized"] = True
                matched += 1
            elif not item.get("sales_authorized"):
                # Third-party candidates must not inherit guessed sales.
                item["sales_authorized"] = False
        _V13_STATS["items_matched"] += matched
        print(f"[V13] vendas autorizadas: orders_status={meta.get('status')} orders={meta.get('orders', 0)} matched_items={matched} units_30d={sum(sales.values()) if sales else 0}", flush=True)
    except Exception as exc:
        print(f"[V13][WARN] vendas autorizadas: {type(exc).__name__}: {str(exc)[:220]}", flush=True)
    return items

_v13_enrich._v13_wrapped = True


def install(app):
    app.state.oferta_v13_sales = _load_authorized_sales
    @app.get("/api/mercadolivre/vendas-autorizadas", include_in_schema=False)
    async def _sales_diagnostic():
        sales, meta = _load_authorized_sales()
        return {"source": "orders/search", "period_days": 30, "authorized_seller": bool(meta.get("seller_id")), "meta": meta, "items_with_sales": len(sales), "total_units": int(sum(sales.values())) if sales else 0, "stats": dict(_V13_STATS)}
    base = globals().get("_v119_enrich_ml")
    if callable(base) and not getattr(base, "_v13_base", False):
        def wrapped(items):
            return _v13_enrich(items)
        wrapped._v13_base = base
        globals()["_v119_enrich_ml"] = wrapped
    print("[V13] fonte autorizada de vendas /orders/search instalada", flush=True)
