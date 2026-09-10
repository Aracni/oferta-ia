"""V10.19 — resolução de PRODUCT sem depender de GET /items/{id}.

O Mercado Livre permite consultar /products/{product_id}/items, mas a
aplicação pode receber 403 ao consultar /items/{item_id}. Para o garimpo,
usamos diretamente os dados autorizados do catálogo e da lista PDP.
"""
import time


def install(app_module):
    def _num(value):
        try:
            if value in (None, ""):
                return None
            return float(value)
        except Exception:
            return None

    def _catalog_to_item(token, product_id, rank_position=None, query=""):
        try:
            detail, status = app_module._v9_fetch_json(
                token,
                f"https://api.mercadolibre.com/products/{product_id}",
                timeout=8,
                stage="CATALOG",
            )
            if not isinstance(detail, dict):
                app_module._v93_log("CATALOG", "Produto sem payload utilizável", product_id=product_id, http=status)
                return None

            winner = detail.get("buy_box_winner")
            rows = []
            if isinstance(winner, dict):
                rows.append(winner)

            # A lista PDP traz item_id + preço e evita a chamada /items/{id},
            # que para esta aplicação pode responder 403.
            if not rows:
                data, items_status = app_module._v9_fetch_json(
                    token,
                    f"https://api.mercadolibre.com/products/{product_id}/items",
                    {"limit": 20},
                    timeout=8,
                    stage="CATALOG",
                )
                if isinstance(data, dict):
                    rows = data.get("results") or data.get("items") or data.get("publications") or []
                elif isinstance(data, list):
                    rows = data
                if not isinstance(rows, list):
                    rows = []
                app_module._v93_log("CATALOG", "Publicações PDP carregadas", product_id=product_id, http=items_status, results=len(rows))

            best = None
            for row in rows:
                if not isinstance(row, dict):
                    continue
                iid = row.get("item_id") or row.get("id")
                price = _num(row.get("price") or row.get("current_price"))
                title = row.get("title") or detail.get("name") or ""
                if not iid or price is None or price <= 0:
                    continue
                if app_module._looks_like_accessory(title):
                    continue
                if best is None or price < (_num(best.get("price")) or 10**18):
                    best = row

            # Se não houver uma publicação disponível, o próprio produto de
            # catálogo ainda pode fornecer nome, permalink e faixa de preço.
            # Nesse caso retornamos um registro de confiança média, sem
            # inventar um item_id.
            if best is None:
                price_range = detail.get("buy_box_winner_price_range") or {}
                minimum = price_range.get("min") if isinstance(price_range, dict) else None
                price = _num((minimum or {}).get("price")) if isinstance(minimum, dict) else None
                if price is None:
                    app_module._v93_log("CATALOG", "Produto sem publicação e sem preço", product_id=product_id)
                    return None
                title = detail.get("name") or "Produto Mercado Livre"
                if app_module._looks_like_accessory(title):
                    return None
                image = None
                pictures = detail.get("pictures") or []
                if pictures and isinstance(pictures[0], dict):
                    image = pictures[0].get("secure_url") or pictures[0].get("url")
                p = {
                    "name": title,
                    "store": "Mercado Livre",
                    "marketplace": "mercadolivre",
                    "product_id": product_id,
                    "catalog_product_id": product_id,
                    "item_id": None,
                    "seller_id": None,
                    "url": detail.get("permalink") or f"https://www.mercadolivre.com.br/p/{product_id}",
                    "image_url": image,
                    "current_price": price,
                    "old_price": None,
                    "discount_rate": None,
                    "category": detail.get("domain_id"),
                    "rating": None,
                    "sales": detail.get("sold_quantity"),
                    "rank_position": rank_position,
                    "discovery_query": query,
                    "data_confidence": "média",
                }
                p["opportunity_score"] = app_module._opportunity_score(p)
                p["opportunity_label"] = app_module._opportunity_label(p["opportunity_score"])
                app_module._v93_log("CATALOG", "Produto resolvido via faixa de preço", product_id=product_id, price=price)
                return p

            title = best.get("title") or detail.get("name") or "Produto Mercado Livre"
            current = _num(best.get("price") or best.get("current_price"))
            old = _num(best.get("original_price"))
            image = best.get("secure_thumbnail") or best.get("thumbnail")
            if not image:
                pictures = detail.get("pictures") or []
                if pictures and isinstance(pictures[0], dict):
                    image = pictures[0].get("secure_url") or pictures[0].get("url")

            iid = best.get("item_id") or best.get("id")
            permalink = best.get("permalink")
            if not permalink and iid:
                permalink = f"https://produto.mercadolivre.com.br/{iid}"
            if not permalink:
                permalink = detail.get("permalink") or f"https://www.mercadolivre.com.br/p/{product_id}"

            discount = round((old - current) / old * 100, 2) if old and current and old > current else None
            seller = best.get("seller") if isinstance(best.get("seller"), dict) else {}
            p = {
                "name": title,
                "store": str(seller.get("nickname") or "Mercado Livre"),
                "marketplace": "mercadolivre",
                "product_id": product_id,
                "catalog_product_id": product_id,
                "item_id": str(iid) if iid else None,
                "seller_id": best.get("seller_id") or seller.get("id"),
                "url": permalink,
                "image_url": image,
                "current_price": current,
                "old_price": old,
                "discount_rate": discount,
                "category": best.get("category_id") or detail.get("domain_id"),
                "rating": best.get("rating"),
                "sales": best.get("sold_quantity") or detail.get("sold_quantity"),
                "condition": best.get("condition") or best.get("item_condition"),
                "rank_position": rank_position,
                "discovery_query": query,
                "data_confidence": "alta",
            }
            p["opportunity_score"] = app_module._opportunity_score(p)
            p["opportunity_label"] = app_module._opportunity_label(p["opportunity_score"])
            app_module._v93_log("CATALOG", "Produto resolvido sem /items/{id}", product_id=product_id, item_id=iid, price=current)
            return p
        except Exception as exc:
            app_module._v93_log("CATALOG", "Falha ao resolver produto", product_id=product_id, error=str(exc)[:220])
            return None

    app_module._v9_catalog_to_item = _catalog_to_item
    app_module._meli_catalog_patch_version = "V10.19"
    print("[CATALOG_PATCH] V10.19 ativo: PRODUCT usa /products/{id}/items sem depender de /items/{id}", flush=True)
