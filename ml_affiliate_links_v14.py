"""OFERTA IA V14 — integração segura com o Gerador de Links de Afiliados do Mercado Livre.

A API pública de sellers/OAuth não expõe um endpoint oficial de criação de links de
afiliado. O Gerador de Links do programa usa uma sessão autenticada do afiliado.
Este módulo aproveita o fluxo técnico observado no APK, mas NÃO coleta senha:
o usuário fornece a própria etiqueta e, se necessário, uma sessão/cookie já
autenticada no Gerador de Links. Segredos nunca são devolvidos nas respostas.
"""
import re
import requests
from fastapi import Body, HTTPException

_CREATE_URL = "https://www.mercadolivre.com.br/affiliate-program/api/v2/affiliates/createLink"
_LINKBUILDER_URL = "https://www.mercadolivre.com.br/afiliados/linkbuilder"
_UA = "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/140 Mobile Safari/537.36 OFERTA-IA/14.0"

def _conn():
    fn = globals().get("_get_connection")
    if callable(fn):
        try:
            return dict(fn("mercadolivre") or {})
        except Exception:
            pass
    return {}

def _save(data):
    fn = globals().get("_save_connection")
    if not callable(fn):
        raise RuntimeError("Persistência de conexão do Mercado Livre indisponível.")
    fn("mercadolivre", data)

def _safe_cookie(raw):
    value = str(raw or "").strip()
    if not value:
        return ""
    # Aceita tanto "a=b; c=d" quanto linhas JSON-like simples; nunca loga o valor.
    value = value.replace("\\n", "; ")
    return value[:12000]

def _csrf(cookie):
    m = re.search(r"(?:^|;\\s*)_csrf=([^;]+)", str(cookie or ""))
    return m.group(1).strip() if m else None

def _extract_short(body):
    if not isinstance(body, dict):
        return None
    rows = body.get("urls")
    if isinstance(rows, list) and rows:
        row = rows[0]
        if isinstance(row, dict):
            return row.get("short_url") or row.get("url")
        if isinstance(row, str):
            return row
    for key in ("short_url", "affiliate_url"):
        if body.get(key):
            return body[key]
    return None

def _create(url, tag, cookie):
    if not url.startswith("http"):
        raise ValueError("A URL do produto precisa começar com http/https.")
    if "mercadolivre.com.br" not in url.lower() and "mercadolibre.com" not in url.lower():
        raise ValueError("A URL precisa ser de um produto do Mercado Livre.")
    headers = {
        "Cookie": cookie,
        "Origin": "https://www.mercadolivre.com.br",
        "Referer": _LINKBUILDER_URL,
        "User-Agent": _UA,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    }
    csrf = _csrf(cookie)
    if csrf:
        headers["x-csrf-token"] = csrf
    response = requests.post(
        _CREATE_URL,
        headers=headers,
        json={"urls": [url], "tag": tag},
        timeout=12,
    )
    try:
        body = response.json()
    except Exception:
        body = {}
    if not response.ok:
        detail = ""
        if isinstance(body, dict):
            detail = str(body.get("message") or body.get("error") or "")[:220]
        raise RuntimeError(f"Gerador de Links respondeu HTTP {response.status_code}" + (f": {detail}" if detail else ""))
    short = _extract_short(body)
    if not short:
        raise RuntimeError("Mercado Livre respondeu sem short_url.")
    return short

def _status():
    c = _conn()
    cookie = c.get("affiliate_cookie") or ""
    tag = c.get("affiliate_tag") or ""
    return {
        "configured": bool(cookie and tag),
        "tag_configured": bool(tag),
        "session_configured": bool(cookie),
        "session_source": "cookie_do_linkbuilder" if cookie else None,
        "note": "A senha do Mercado Livre não é armazenada pelo OFERTA IA."
    }

def install(app):
    if getattr(app, "_oferta_affiliate_v14", False):
        return
    app._oferta_affiliate_v14 = True

    @app.get("/api/mercadolivre/afiliado/status", include_in_schema=False)
    async def affiliate_status():
        return _status()

    @app.post("/api/mercadolivre/afiliado/config", include_in_schema=False)
    async def affiliate_config(payload: dict = Body(default={})):
        body = dict(payload or {})
        tag = str(body.get("tag") or "").strip()
        cookie = _safe_cookie(body.get("cookie") or body.get("cookies"))
        if not tag:
            raise HTTPException(status_code=400, detail="Informe sua etiqueta/tag de afiliado.")
        if not re.match(r"^[A-Za-z0-9_.-]{2,120}$", tag):
            raise HTTPException(status_code=400, detail="Etiqueta de afiliado inválida.")
        if not cookie:
            raise HTTPException(status_code=400, detail="Informe a sessão autenticada do Gerador de Links.")
        merged = _conn()
        merged["affiliate_tag"] = tag
        merged["affiliate_cookie"] = cookie
        merged["affiliate_configured_at"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
        _save(merged)
        return {"status": "ok", "configured": True, "tag_configured": True, "session_configured": True}

    @app.post("/api/mercadolivre/afiliado/link", include_in_schema=False)
    async def affiliate_link(payload: dict = Body(default={})):
        body = dict(payload or {})
        url = str(body.get("url") or body.get("product_url") or "").strip()
        c = _conn()
        tag = str(c.get("affiliate_tag") or "").strip()
        cookie = _safe_cookie(c.get("affiliate_cookie") or "")
        if not tag or not cookie:
            raise HTTPException(status_code=409, detail="Afiliado Mercado Livre ainda não configurado.")
        try:
            short = _create(url, tag, cookie)
            return {"status": "ok", "affiliate_url": short, "source": "mercadolivre_linkbuilder"}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            # Não expõe cookie, token ou resposta sensível.
            raise HTTPException(status_code=502, detail=f"Não foi possível gerar o link de afiliado: {type(exc).__name__}: {str(exc)[:220]}")

    @app.get("/api/mercadolivre/afiliado/mobile", include_in_schema=False)
    async def affiliate_mobile(url: str = "", tag: str = ""):
        from urllib.parse import quote
        clean_url = str(url or "").strip()
        clean_tag = str(tag or "").strip() or str(_conn().get("affiliate_tag") or "").strip()
        if not clean_url or not clean_url.startswith("http"):
            raise HTTPException(status_code=400, detail="URL do produto inválida.")
        if "mercadolivre.com.br" not in clean_url.lower() and "mercadolibre.com" not in clean_url.lower():
            raise HTTPException(status_code=400, detail="A URL precisa ser do Mercado Livre.")
        if not clean_tag:
            raise HTTPException(status_code=409, detail="Configure sua etiqueta de afiliado primeiro.")
        deep = "ofertaia://affiliate?url=" + quote(clean_url, safe="") + "&tag=" + quote(clean_tag, safe="")
        return {"status":"ok","deep_link":deep,"mode":"android_bridge","note":"A sessão permanece no aparelho; senha e cookie não são enviados ao servidor."}

    try:
        html = getattr(app, "HTML", "")
        mobile_ui = '''<section id="oferta-affiliate-bridge" style="margin:14px 0;padding:14px;border:1px solid rgba(255,255,255,.14);border-radius:14px">
<strong>🔗 Afiliado Mercado Livre</strong>
<div id="oferta-affiliate-status" style="margin:6px 0 10px;opacity:.86">Gerador pronto para conexão pelo celular.</div>
<button id="oferta-affiliate-connect" type="button">🟡 Conectar Mercado Livre</button>
</section>
<script>
(function(){
 const portal='https://www.mercadolivre.com.br/afiliados/linkbuilder';
 const connect=document.getElementById('oferta-affiliate-connect');
 const status=document.getElementById('oferta-affiliate-status');
 if(!connect) return;
 const params=new URLSearchParams(location.search); const result=params.get('affiliate_url'); const err=params.get('affiliate_error');
 if(result){ status.textContent='🟢 Link de afiliado recebido da ponte Android.'; const box=document.createElement('div'); box.style='margin-top:10px;word-break:break-all'; box.innerHTML='<strong>Link:</strong> <a target="_blank" rel="noopener" href="'+result.replace(/&/g,'&amp;').replace(/"/g,'&quot;')+'">'+result.replace(/</g,'&lt;')+'</a>'; document.getElementById('oferta-affiliate-bridge').appendChild(box); }
 if(err){ status.textContent='⚠️ A ponte não conseguiu gerar o link. Abra o Portal do Afiliado e tente novamente.'; }
 connect.onclick=function(){ window.open(portal,'_blank'); status.textContent='🟡 Faça login no Mercado Livre e use a ponte Android para gerar o link sem compartilhar sua senha.'; };
})();
</script>'''
        if "id=\"oferta-affiliate-bridge\"" not in html and "</body>" in html:
            app.HTML = html.replace("</body>", mobile_ui + "</body>")
            print("[V14.1] UI de conexão móvel do afiliado instalada", flush=True)
    except Exception as exc:
        print(f"[V14.1][WARN] UI afiliado móvel: {type(exc).__name__}: {str(exc)[:220]}", flush=True)

    print("[V14.1] Gerador de Links ML instalado | senha não coletada | geração sob demanda", flush=True)
