"""OFERTA IA V12.7 — sinais legítimos de demanda.

Não transforma ranking em vendas. Quando sold_quantity não está disponível,
usa somente sinais documentados do Mercado Livre: /trends e /highlights.
"""
import math
import re
import requests

_V127_PREVIOUS = globals().get("_v119_enrich_ml")
_V127_CACHE = {"trends": None, "highlights": {}}
_V127_TRENDS_BLOCKED_UNTIL = 0.0\n_V127_TRENDS_BLOCK_TTL = 3600


def _v127_norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _v127_token():
    try:
        return _v9_valid_meli_token()
    except Exception:
        return None


def _v127_get(url, token, timeout=6):
    if not token:
        return None, 0
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "OFERTA-IA/12.7"}, timeout=timeout)
        data = r.json() if r.content else None
        return data, int(r.status_code or 0)
    except Exception as exc:
        print(f"[V12.7] HTTP falhou: {type(exc).__name__}", flush=True)
        return None, 0


def _v127_trends(token):
    if _V127_CACHE["trends"] is not None:
        return _V127_CACHE["trends"]
    data, status = _v127_get("https://api.mercadolibre.com/trends/MLB", token)
    if not isinstance(data, list) or not (200 <= status < 300):
        print(f"[V12.7] trends indisponível http={status}", flush=True)
        _V127_CACHE["trends"] = []
        return []
    rows = [x for x in data if isinstance(x, dict) and x.get("keyword")]
    _V127_CACHE["trends"] = rows
    print(f"[V12.7] trends MLB carregadas={len(rows)}", flush=True)
    return rows


def _v127_highlights(category, token):
    category = str(category or "").upper().strip()
    if not re.fullmatch(r"MLB\d+", category):
        return []
    if category in _V127_CACHE["highlights"]:
        return _V127_CACHE["highlights"][category]
    data, status = _v127_get(f"https://api.mercadolibre.com/highlights/MLB/category/{category}", token)
    rows = data.get("content") if isinstance(data, dict) else []
    rows = rows if isinstance(rows, list) and 200 <= status < 300 else []
    _V127_CACHE["highlights"][category] = rows
    return rows


def _v127_demand(item, trends, token):
    title = _v127_norm(item.get("title") or item.get("name") or item.get("product_name"))
    if not title:
        return None, None, None
    words = set(title.split())
    best = None
    for idx, row in enumerate(trends):
        kw = _v127_norm(row.get("keyword"))
        if not kw:
            continue
        kwords = set(kw.split())
        overlap = len(words & kwords)
        if kw in title or title in kw:
            overlap += 3
        if overlap <= 0:
            continue
        # Primeiros 10 = maior crescimento; próximos 20 = mais desejados; últimos 20 = populares.
        if idx < 10:
            base = 100.0
            kind = "crescimento"
        elif idx < 30:
            base = 90.0
            kind = "mais_desejado"
        else:
            base = 80.0
            kind = "popular"
        score = min(100.0, base + min(10.0, overlap * 3.0) - idx * 0.05)
        if best is None or score > best[0]:
            best = (score, kind, row.get("keyword"))

    category = item.get("category") or item.get("category_id")
    catalog = str(item.get("catalog_product_id") or item.get("product_id") or "").upper()
    rank = None
    if category and token:
        for pos, row in enumerate(_v127_highlights(category, token), 1):
            rid = str(row.get("id") or "").upper()
            if catalog and rid == catalog:
                rank = pos
                break
    if rank is not None:
        rank_score = max(70.0, 100.0 - (rank - 1) * 5.0)
        if best is None or rank_score > best[0]:
            best = (rank_score, "mais_vendido_categoria", f"posição {rank}")
    if best is None:
        return None, None, None
    return round(best[0], 2), best[1], best[2]


def _v127_enrich(items):
    enriched = list(_V127_PREVIOUS(items) if callable(_V127_PREVIOUS) else items or [])
    token = _v127_token()
    trends = _v127_trends(token) if token else []
    for item in enriched:
        if not isinstance(item, dict):
            continue
        if item.get("marketplace") and str(item.get("marketplace")).lower() != "mercadolivre":
            continue
        score, kind, source = _v127_demand(item, trends, token)
        if score is None:
            continue
        item["demand_index"] = score
        item["demand_signal"] = kind
        item["demand_source"] = "Mercado Livre /trends" if kind != "mais_vendido_categoria" else "Mercado Livre /highlights"
        item["demand_label"] = {"crescimento":"Em forte crescimento", "mais_desejado":"Muito buscado", "popular":"Tendência popular", "mais_vendido_categoria":"Top mais vendidos da categoria"}.get(kind, "Demanda detectada")
        # Reforça o score apenas quando há um sinal real de demanda; não cria vendas.
        try:
            old = float(item.get("opportunity_score"))
            item["opportunity_score"] = round(old * 0.75 + score * 0.25, 2)
        except Exception:
            item["opportunity_score"] = score
        item["score_provisional"] = True if item.get("sold_quantity") is None else item.get("score_provisional", False)
    print(f"[V12.7] demanda aplicada | trends={len(trends)}", flush=True)
    return enriched

_v119_enrich_ml = _v127_enrich
print("[V12.7] sinais de demanda legítimos ativos; vendas continuam somente quando sold_quantity real", flush=True)
