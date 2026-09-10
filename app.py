import os
from urllib.parse import quote
import json
import re
import math
import base64
import hashlib
import secrets
import time
import logging
import uuid
from collections import Counter
from datetime import datetime, timezone, timedelta
from html import unescape
from urllib.parse import urljoin, urlparse
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from supabase import create_client

# V9.8 — log estruturado para rastrear todo o caminho da descoberta.
logger = logging.getLogger("oferta_ia.v9")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | V9.8 | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False
_V93_LAST_DIAGNOSTIC = {}
_V94_LOG_BUFFER = []
_V94_LOG_MAX_LINES = 500

def _v93_log(stage, message, **fields):
    global _V94_LOG_BUFFER
    safe = {k: v for k, v in fields.items() if k not in {"token", "access_token", "refresh_token", "client_secret"}}
    suffix = " | " + " ".join(f"{k}={v}" for k, v in safe.items()) if safe else ""
    line = f"{datetime.now().strftime('%H:%M:%S')} | {stage} | {message}{suffix}"
    _V94_LOG_BUFFER.append(line)
    if len(_V94_LOG_BUFFER) > _V94_LOG_MAX_LINES:
        del _V94_LOG_BUFFER[:-_V94_LOG_MAX_LINES]
    logger.info("[%s] %s%s", stage, message, suffix)

def _v94_log_text():
    return "\n".join(_V94_LOG_BUFFER)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Configure SUPABASE_URL e SUPABASE_SECRET_KEY (ou SUPABASE_SERVICE_ROLE_KEY).")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI(title="OFERTA IA")

_CACHE = {}
_CACHE_TTL = 300

def _cache_get(key):
    item = _CACHE.get(key)
    if not item:
        return None
    if time.time() - item[0] > _CACHE_TTL:
        _CACHE.pop(key, None)
        return None
    return item[1]

def _cache_set(key, value):
    _CACHE[key] = (time.time(), value)
    if len(_CACHE) > 250:
        oldest = sorted(_CACHE.items(), key=lambda kv: kv[1][0])[:50]
        for k, _ in oldest:
            _CACHE.pop(k, None)
    return value

class Product(BaseModel):
    name: str
    store: str | None = None
    url: str | None = None
    affiliate_url: str | None = None
    old_price: float | None = None
    current_price: float | None = None
    category: str | None = None
    image_url: str | None = None
    marketplace: str | None = None
    item_id: str | None = None
    shop_id: str | None = None
    sales: float | None = None
    rating: float | None = None
    discount_rate: float | None = None
    commission_rate: float | None = None
    seller_commission_rate: float | None = None
    shopee_commission_rate: float | None = None
    commission_value: float | None = None
    opportunity_score: float | None = None
    competition_index: float | None = None
    data_confidence: str | None = None

# O HTML original do aplicativo permanece inalterado nesta versão.
# Para preservar a interface atual, ele é carregado do bloco existente no arquivo.
