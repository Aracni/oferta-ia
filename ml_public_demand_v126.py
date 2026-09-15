"""OFERTA IA V12.6 — sinal público de demanda via busca do Mercado Livre."""
import math
import re
import urllib.parse

_V126_PUBLIC_STATS = {"requests": 0, "found": 0, "errors": 0, "matched": 0, "unauth_ok": 0, "token_ok": 0}


def _v126_item_id(obj):
    if not isinstance(obj, dict):
        return None
    for key in ("item_id", "meli_item_id", "id"):
        value = str(obj.get(key) or "").strip().upper()
        if re.fullmatch(r"MLB[0-9]+", value):
            return value
    for key in ("url", "permalink", "link", "product_url"):
        value = str(obj.get(key) or "")
        match = re.search(r"(?:MLB-|MLB)([0-9]+)", value, re.I)
        if match:
            return "MLB" + match.group(1)
    return None


def _v126_catalog_id(obj):
    if not isinstance(obj, dict):
        return None
    for key in ("catalog_product_id", "product_id", "user_product_id"):
        value = str(obj.get(key) or "").strip().upper()
        if re.fullmatch(r"MLB[0-9]+", value):
            return value
    for key in ("url", "permalink", "link", "product_url"):
        value = str(obj.get(key) or "")
        match = re.search(r"/p/(MLB[0-9]+)", value, re.I)
        if match:
            return match.group(1).upper()
    return None


def _v126_norm_title(value):
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    return " ".join(text.split())


def _v126_public_search(title, token):
    if not title:
        return None
    try:
        query = urllib.parse.quote(str(title)[:180])
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={query}&limit=50"

        # O endpoint de busca é público em alguns contextos, enquanto o token
        # atual do OFERTA IA está recebendo 403. Tentar sem Authorization evita
        # transformar uma busca pública em uma chamada privada bloqueada.
        import requests
        response = requests.get(
            url,
            headers={"Accept": "application/json", "User-Agent": "OFERTA-IA/12.6"},
            timeout=4,
        )
        _V126_PUBLIC_STATS["requests"] += 1
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                data = {}
            if isinstance(data, dict):
                _V126_PUBLIC_STATS["unauth_ok"] += 1
                return data.get("results") if isinstance(data.get("results"), list) else []

        # Fallback autenticado somente se a rota pública realmente exigir token.
        if token:
            data, status = _v11_fetch_json(token, url, timeout=4, stage="PUBLIC_DEMAND_V12_6_TOKEN")
            if isinstance(data, dict) and 200 <= int(status or 0) < 300:
                _V126_PUBLIC_STATS["token_ok"] += 1
                return data.get("results") if isinstance(data.get("results"), list) else []

        _V126_PUBLIC_STATS["errors"] += 1
        return None
    except Exception as exc:
        _V126_PUBLIC_STATS["errors"] += 1
        print(f"[V12.6][PUBLIC_SEARCH] falha: {type(exc).__name__}: {str(exc)[:220]}", flush=True)
        return None


# Capture the previous enrichment function BEFORE installing this wrapper.
_V126_PREVIOUS_ENRICH = globals().get("_v119_enrich_ml")


def _v126_enrich(items):
    try:
        token = _v9_valid_meli_token()
    except Exception:
        token = None

    base_enrich = _V126_PREVIOUS_ENRICH
    if callable(base_enrich):
        enriched = base_enrich(items)
    else:
        enriched = items

    if not isinstance(enriched, list):
        return enriched

    for item in enriched:
        if not isinstance(item, dict) or item.get("sold_quantity") is not None:
            continue
        title = str(item.get("title") or item.get("name") or "").strip()
        if not title:
            continue

        item_id = _v126_item_id(item)
        catalog_id = _v126_catalog_id(item)
        results = _v126_public_search(title, token)
        if not results:
            continue

        normalized_item_title = _v126_norm_title(title)
        chosen = None
        # 1) Correspondência segura pelo item_id real.
        if item_id:
            for result in results:
                if isinstance(result, dict) and _v126_item_id(result) == item_id:
                    chosen = result
                    break
        # 2) Para candidatos de catálogo /p/MLB..., casar catalog_product_id.
        if chosen is None and catalog_id:
            for result in results:
                if isinstance(result, dict) and _v126_catalog_id(result) == catalog_id:
                    chosen = result
                    break
        # 3) Último recurso: título normalizado exatamente igual.
        if chosen is None:
            for result in results:
                if isinstance(result, dict) and _v126_norm_title(result.get("title")) == normalized_item_title:
                    chosen = result
                    break

        if not isinstance(chosen, dict):
            continue

        _V126_PUBLIC_STATS["matched"] += 1
        value = chosen.get("sold_quantity")
        try:
            if value in (None, ""):
                continue
            sold = int(float(value))
            if sold < 0:
                continue
        except Exception:
            continue

        item["sold_quantity"] = sold
        item["sales"] = sold
        item["sales_count"] = sold
        item["sales_source"] = "public_search"
        item["demand_source"] = "public_search"
        item["demand_index"] = round(min(100.0, math.log1p(sold) / math.log1p(10000) * 100.0), 2)
        item["data_confidence"] = "média" if item.get("rating") is None else "alta"
        item["confidence"] = item["data_confidence"]
        rescore = globals().get("_v115_rescore")
        if callable(rescore):
            try:
                item["opportunity_score"] = rescore(item)
            except TypeError:
                pass
        item["enrichment_version"] = "V12.6-public-demand"
        _V126_PUBLIC_STATS["found"] += 1

    print(
        f"[V12.6] demanda pública: requests={_V126_PUBLIC_STATS['requests']} "
        f"matched={_V126_PUBLIC_STATS['matched']} found={_V126_PUBLIC_STATS['found']} "
        f"errors={_V126_PUBLIC_STATS['errors']} unauth_ok={_V126_PUBLIC_STATS['unauth_ok']} "
        f"token_ok={_V126_PUBLIC_STATS['token_ok']}",
        flush=True,
    )
    return enriched


_v119_enrich_ml = _v126_enrich
print("[V12.6] sinal público de demanda ativo | busca pública sem token + fallback token", flush=True)
