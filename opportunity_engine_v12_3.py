"""OFERTA IA V12.3 — motor de oportunidade com pressão competitiva explícita.

Objetivo: separar demanda, economia, qualidade e dificuldade de entrada.
A pressão competitiva do vencedor é tratada como sinal de dificuldade, não
como contagem real de concorrentes.

Regras:
- não inventa comissão, avaliações ou vendas;
- best-seller confirma demanda, mas não transforma sozinho um produto em oportunidade;
- falta de dados reduz a confiança/cobertura;
- comissão continua opcional para o cálculo, mas sua ausência mantém o resultado provisório;
- pressão competitiva entra com peso pequeno e transparente.
"""
import math


def _v123_num(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _v123_sales(item):
    for key in ("sold_quantity", "sales_count", "sales"):
        value = _v123_num(item.get(key))
        if value is not None and value >= 0:
            return int(value)
    return None


def _v123_demand(item):
    sold = _v123_sales(item)
    if sold is not None:
        return min(100.0, math.log1p(sold) / math.log1p(10000) * 100.0)
    position = _v123_num(item.get("best_seller_position"))
    if position is not None and 1 <= position <= 20:
        return 60.0 + (21.0 - position) / 20.0 * 40.0
    return None


def _v123_discount(item):
    discount = _v123_num(item.get("discount_rate"))
    if discount is None:
        old = _v123_num(item.get("old_price"))
        current = _v123_num(item.get("current_price"))
        if old and current and old > current:
            discount = (old - current) / old * 100.0
    if discount is None:
        return None
    return min(100.0, max(0.0, discount / 60.0 * 100.0))


def _v123_price_accessibility(item):
    price = _v123_num(item.get("current_price"))
    if price is None:
        return None
    if price <= 50:
        return 100.0
    if price <= 100:
        return 90.0
    if price <= 200:
        return 75.0
    if price <= 500:
        return 60.0
    return 45.0


def _v123_rating(item):
    rating = None
    for key in ("rating", "rating_average", "stars"):
        value = _v123_num(item.get(key))
        if value is not None and 0 < value <= 5:
            rating = value
            break
    if rating is None:
        return None
    reviews = None
    for key in ("reviews_total", "review_count", "reviews_count"):
        value = _v123_num(item.get(key))
        if value is not None and value >= 0:
            reviews = value
            break
    base = rating / 5.0 * 100.0
    if reviews is None:
        return base
    confidence = min(1.0, math.log1p(reviews) / math.log1p(200))
    return round(55.0 + (base - 55.0) * confidence, 2)


def _v123_winner_quality(item):
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


def _v123_commission(item):
    for key in ("commission_rate", "affiliate_commission_rate", "commission"):
        value = _v123_num(item.get(key))
        if value is not None and value >= 0:
            return min(100.0, value / 16.0 * 100.0)
    return None


def _v123_trend(item):
    for key in ("trend_score", "trend_signal", "trend_index"):
        value = _v123_num(item.get(key))
        if value is not None:
            return max(0.0, min(100.0, value))
    return None


def _v123_competition(item):
    pressure = _v123_num(item.get("competition_pressure"))
    if pressure is None:
        return None
    # V11.11.14 mede a força do vencedor atual. Não é contagem de concorrentes.
    # Quanto maior a força do vencedor, maior a dificuldade de entrada.
    return max(0.0, min(100.0, 100.0 - pressure))


def _v123_decide(item):
    definitions = (
        ("demanda", _v123_demand(item), 0.25),
        ("tendência", _v123_trend(item), 0.05),
        ("desconto", _v123_discount(item), 0.15),
        ("preço", _v123_price_accessibility(item), 0.05),
        ("avaliação", _v123_rating(item), 0.15),
        ("qualidade do vencedor", _v123_winner_quality(item), 0.10),
        ("entrada competitiva", _v123_competition(item), 0.10),
        ("comissão", _v123_commission(item), 0.15),
    )
    available = [(name, value, weight) for name, value, weight in definitions if value is not None]
    if not available:
        return None, "DADOS INSUFICIENTES", [], 0.0, False

    coverage = round(sum(weight for _, _, weight in available) * 100.0, 1)
    raw = sum(value * weight for _, value, weight in available) / sum(weight for _, _, weight in available)
    completeness = coverage / 100.0
    score = raw * (0.55 + 0.45 * completeness)

    sales = _v123_sales(item)
    best_seller = bool(item.get("best_seller"))
    rating = _v123_rating(item)
    commission = _v123_commission(item)
    discount = _v123_discount(item)
    competition = _v123_competition(item)
    reasons = []

    if sales is not None and sales > 0:
        reasons.append("vendas confirmadas")
    elif best_seller:
        reasons.append("presença no ranking de mais vendidos")
    if _v123_trend(item) is not None:
        reasons.append("tendência disponível")
    if discount is not None and discount >= 55:
        reasons.append("desconto relevante")
    if rating is not None and rating >= 80:
        reasons.append("boa avaliação")
    if commission is not None:
        reasons.append("comissão disponível")
    if competition is not None:
        if competition >= 70:
            reasons.append("entrada competitiva favorável")
        elif competition < 40:
            reasons.append("entrada competitiva difícil")

    has_real_demand = sales is not None and sales > 0
    has_economics = discount is not None or commission is not None
    has_quality = rating is not None or _v123_winner_quality(item) is not None

    if score >= 82 and coverage >= 85 and has_real_demand and has_economics and has_quality:
        classification = "EXCELENTE OPORTUNIDADE"
    elif score >= 70 and coverage >= 70 and (has_real_demand or best_seller) and has_economics:
        classification = "BOA OPORTUNIDADE"
    elif score >= 55 and coverage >= 45:
        classification = "OPORTUNIDADE A MONITORAR"
    else:
        classification = "DADOS INSUFICIENTES / DESCARTAR"

    provisional = coverage < 85 or rating is None or commission is None
    return round(score, 2), classification, reasons, coverage, provisional


_original_enrich_v123 = _v119_enrich_ml


def _v123_enrich(items):
    enriched = _original_enrich_v123(items)
    counts = {"excellent": 0, "good": 0, "monitor": 0, "discard": 0}

    for item in enriched:
        if not isinstance(item, dict):
            continue
        sales = _v123_sales(item)
        if sales is not None:
            item["sold_quantity"] = sales
            item["sales"] = sales
            item["sales_count"] = sales
            item["sales_source"] = item.get("sales_source") or "Mercado Livre API"

        score, classification, reasons, coverage, provisional = _v123_decide(item)
        base = _v123_num(item.get("opportunity_score"))
        if base is not None:
            item["base_opportunity_score"] = round(base, 2)
        if score is not None:
            item["opportunity_score"] = score
            item["opportunity_score_v2"] = score
            item["score"] = score
            item["score_provisional"] = provisional

        item["opportunity_class"] = classification
        item["opportunity_reasons"] = reasons
        item["opportunity_data_coverage"] = coverage
        item["opportunity_engine"] = "V12.3"
        item["opportunity_is_provisional"] = provisional
        item["competition_signal"] = _v123_competition(item)

        if classification == "EXCELENTE OPORTUNIDADE":
            counts["excellent"] += 1
        elif classification == "BOA OPORTUNIDADE":
            counts["good"] += 1
        elif classification == "OPORTUNIDADE A MONITORAR":
            counts["monitor"] += 1
        else:
            counts["discard"] += 1

    print(
        "[V12.3] oportunidade: "
        f"excellent={counts['excellent']} good={counts['good']} "
        f"monitor={counts['monitor']} discard={counts['discard']}",
        flush=True,
    )
    return enriched


_v119_enrich_ml = _v123_enrich
