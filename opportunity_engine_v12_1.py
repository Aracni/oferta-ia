"""OFERTA IA V12.1 — motor de oportunidade corrigido.

Garante que os sinais de vendas descobertos pelos fallbacks cheguem também
às chaves legadas usadas pela interface e calcula a oportunidade a partir
dos sinais realmente disponíveis.

Princípio: vende muito != é boa oportunidade.
"""
import math


def _v121_num(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _v121_sales(item):
    # Unifica os nomes usados pelas diferentes versões do núcleo.
    for key in ("sold_quantity", "sales_count", "sales"):
        value = _v121_num(item.get(key))
        if value is not None and value >= 0:
            return int(value)
    return None


def _v121_demand(item):
    sold = _v121_sales(item)
    if sold is not None:
        return min(100.0, math.log1p(sold) / math.log1p(10000) * 100.0)
    position = _v121_num(item.get("best_seller_position"))
    if position is not None and 1 <= position <= 20:
        return 60.0 + (21.0 - position) / 20.0 * 40.0
    return None


def _v121_discount(item):
    discount = _v121_num(item.get("discount_rate"))
    if discount is None:
        old = _v121_num(item.get("old_price"))
        current = _v121_num(item.get("current_price"))
        if old and current and old > current:
            discount = (old - current) / old * 100.0
    if discount is None:
        return None
    return min(100.0, max(0.0, discount / 60.0 * 100.0))


def _v121_price(item):
    price = _v121_num(item.get("current_price"))
    if price is None:
        return None
    return 100.0 if price <= 50 else 90.0 if price <= 100 else 75.0 if price <= 200 else 60.0


def _v121_rating(item):
    for key in ("rating", "rating_average", "stars"):
        rating = _v121_num(item.get(key))
        if rating is not None and 0 < rating <= 5:
            return rating / 5.0 * 100.0
    return None


def _v121_competition(item):
    pressure = _v121_num(item.get("competition_pressure"))
    if pressure is None:
        return None
    return max(0.0, min(100.0, 100.0 - pressure))


def _v121_winner_quality(item):
    known = 0
    score = 0.0
    reputation = item.get("winner_reputation_level")
    if reputation not in (None, ""):
        known += 1
        score += 100.0 if str(reputation).upper() in {"GREEN", "MERCADO_LIDER"} else 70.0
    for key in ("winner_free_shipping", "winner_fulfillment", "winner_official_store"):
        value = item.get(key)
        if value is not None:
            known += 1
            score += 100.0 if bool(value) else 35.0
    return score / known if known else None


def _v121_decide(item):
    signals = []
    reasons = []
    definitions = (
        ("demanda", _v121_demand(item), 0.35),
        ("desconto", _v121_discount(item), 0.20),
        ("preço", _v121_price(item), 0.10),
        ("avaliação", _v121_rating(item), 0.10),
        ("competição", _v121_competition(item), 0.15),
        ("qualidade do vencedor", _v121_winner_quality(item), 0.10),
    )
    for name, value, weight in definitions:
        if value is not None:
            signals.append((value, weight))
            if name == "demanda" and value >= 70:
                reasons.append("demanda forte")
            elif name == "desconto" and value >= 55:
                reasons.append("desconto relevante")
            elif name == "avaliação" and value >= 80:
                reasons.append("boa avaliação")
            elif name == "competição" and value >= 65:
                reasons.append("pressão competitiva controlada")
            elif name == "qualidade do vencedor" and value >= 80:
                reasons.append("vencedor bem posicionado")

    if not signals:
        return None, "DADOS INSUFICIENTES", [], 0.0

    total_weight = sum(weight for _, weight in signals)
    score = sum(value * weight for value, weight in signals) / total_weight
    coverage = round(total_weight * 100.0, 1)

    sales = _v121_sales(item)
    has_real_demand = sales is not None and sales > 0
    has_economics = _v121_discount(item) is not None or _v121_price(item) is not None
    has_quality = _v121_rating(item) is not None or _v121_winner_quality(item) is not None

    if score >= 80 and has_real_demand and has_economics and has_quality:
        classification = "EXCELENTE OPORTUNIDADE"
    elif score >= 70 and (has_real_demand or bool(item.get("best_seller"))) and has_economics:
        classification = "BOA OPORTUNIDADE"
    elif score >= 55:
        classification = "OPORTUNIDADE A MONITORAR"
    else:
        classification = "FRACA / DESCARTAR"

    return round(score, 2), classification, reasons, coverage


_original_enrich_v121 = _v119_enrich_ml


def _v121_enrich(items):
    enriched = _original_enrich_v121(items)
    for item in enriched:
        if not isinstance(item, dict):
            continue

        sales = _v121_sales(item)
        if sales is not None:
            # Sincroniza explicitamente as chaves que a UI histórica utiliza.
            item["sold_quantity"] = sales
            item["sales"] = sales
            item["sales_count"] = sales
            item["sales_source"] = item.get("sales_source") or "Mercado Livre API"

        score, classification, reasons, coverage = _v121_decide(item)
        base = _v121_num(item.get("opportunity_score"))
        if base is not None:
            item["base_opportunity_score"] = round(base, 2)
        if score is not None:
            item["opportunity_score"] = score
            item["opportunity_score_v2"] = score
            # Mantém também os campos legados usados por versões antigas da UI.
            item["score"] = score
            item["score_provisional"] = _v121_rating(item) is None
        item["opportunity_class"] = classification
        item["opportunity_reasons"] = reasons
        item["opportunity_data_coverage"] = coverage
        item["opportunity_engine"] = "V12.1"
        item["opportunity_is_provisional"] = not (_v121_sales(item) is not None and _v121_rating(item) is not None)

    print("[V12.1] motor corrigido | vendas sincronizadas + score de oportunidade", flush=True)
    return enriched


_v119_enrich_ml = _v121_enrich
