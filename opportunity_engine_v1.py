"""OFERTA IA V12.0 — motor de oportunidade.

Transforma sinais disponíveis em uma decisão de oportunidade sem inventar
comissão, vendas, avaliações ou outros dados ausentes.

Princípio: vende muito != é boa oportunidade.
"""
import math


def _v120_num(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _v120_demand(item):
    sold = _v120_num(item.get("sold_quantity"))
    if sold is not None and sold >= 0:
        return min(100.0, math.log1p(sold) / math.log1p(10000) * 100.0)
    position = _v120_num(item.get("best_seller_position"))
    if position is not None and 1 <= position <= 20:
        # Ranking confirms demand, but is deliberately weaker than real sales.
        return 60.0 + (21.0 - position) / 20.0 * 40.0
    return None


def _v120_discount(item):
    discount = _v120_num(item.get("discount_rate"))
    if discount is None:
        old = _v120_num(item.get("old_price"))
        current = _v120_num(item.get("current_price"))
        if old and current and old > current:
            discount = (old - current) / old * 100.0
    if discount is None:
        return None
    return min(100.0, max(0.0, discount / 60.0 * 100.0))


def _v120_price(item):
    price = _v120_num(item.get("current_price"))
    if price is None:
        return None
    return 100.0 if price <= 50 else 90.0 if price <= 100 else 75.0 if price <= 200 else 60.0


def _v120_rating(item):
    rating = _v120_num(item.get("rating"))
    if rating is None:
        return None
    if not 0 < rating <= 5:
        return None
    return rating / 5.0 * 100.0


def _v120_competition(item):
    pressure = _v120_num(item.get("competition_pressure"))
    if pressure is None:
        return None
    return max(0.0, min(100.0, 100.0 - pressure))


def _v120_winner_quality(item):
    fields = [
        item.get("winner_reputation_level"),
        item.get("winner_free_shipping"),
        item.get("winner_fulfillment"),
        item.get("winner_official_store"),
    ]
    known = 0
    score = 0.0
    if fields[0] not in (None, ""):
        known += 1
        score += 100.0 if str(fields[0]).upper() in {"GREEN", "MERCADO_LIDER"} else 70.0
    for value in fields[1:]:
        if value is not None:
            known += 1
            score += 100.0 if bool(value) else 35.0
    return score / known if known else None


def _v120_decide(item):
    signals = []
    reasons = []

    for name, value, weight in (
        ("demanda", _v120_demand(item), 0.30),
        ("desconto", _v120_discount(item), 0.20),
        ("preço", _v120_price(item), 0.10),
        ("avaliação", _v120_rating(item), 0.15),
        ("competição", _v120_competition(item), 0.15),
        ("qualidade do vencedor", _v120_winner_quality(item), 0.10),
    ):
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
        return None, "dados insuficientes", [], 0.0

    weight = sum(w for _, w in signals)
    score = sum(v * w for v, w in signals) / weight
    coverage = round(weight / 1.0 * 100.0, 1)

    # A ranking de best seller nunca é suficiente para chamar algo de oportunidade.
    has_real_demand = _v120_num(item.get("sold_quantity")) is not None
    has_economics = _v120_discount(item) is not None or _v120_price(item) is not None
    has_quality = _v120_rating(item) is not None or _v120_winner_quality(item) is not None

    if score >= 80 and has_real_demand and has_economics and has_quality:
        classification = "EXCELENTE OPORTUNIDADE"
    elif score >= 70 and (has_real_demand or item.get("best_seller")) and has_economics:
        classification = "BOA OPORTUNIDADE"
    elif score >= 55:
        classification = "OPORTUNIDADE A MONITORAR"
    else:
        classification = "FRACA / DESCARTAR"

    return round(score, 2), classification, reasons, coverage


_original_enrich_v120 = _v119_enrich_ml


def _v120_enrich(items):
    enriched = _original_enrich_v120(items)
    for item in enriched:
        if not isinstance(item, dict):
            continue
        base = _v120_num(item.get("opportunity_score"))
        score, classification, reasons, coverage = _v120_decide(item)
        if base is not None:
            item["base_opportunity_score"] = round(base, 2)
        if score is not None:
            item["opportunity_score"] = score
            item["opportunity_score_v2"] = score
        item["opportunity_class"] = classification
        item["opportunity_reasons"] = reasons
        item["opportunity_data_coverage"] = coverage
        item["opportunity_engine"] = "V12.0"
        item["opportunity_is_provisional"] = not (
            _v120_num(item.get("sold_quantity")) is not None
            and _v120_rating(item) is not None
        )
    print("[V12.0] motor de oportunidade ativo | demanda + economia + qualidade + competição", flush=True)
    return enriched


_v119_enrich_ml = _v120_enrich
