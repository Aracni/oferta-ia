import os
from urllib.parse import quote
import json
import re
import math
import base64
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from html import unescape
from urllib.parse import urljoin, urlparse
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Configure SUPABASE_URL e SUPABASE_SECRET_KEY (ou SUPABASE_SERVICE_ROLE_KEY)."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI(title="OFERTA IA")


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


HTML = """<!doctype html>
<html lang="pt-BR">
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OFERTA IA</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f5f7fb;color:#172033;font-family:Arial,sans-serif}header{background:#111827;color:white;padding:18px 20px;position:sticky;top:0;z-index:5}.brand{font-size:22px;font-weight:800}.sub{font-size:12px;opacity:.7;margin-top:4px}main{max-width:900px;margin:auto;padding:20px}.hero{background:white;border-radius:20px;padding:22px;box-shadow:0 4px 18px #0000000b;margin-bottom:18px}.hero h1{margin:0 0 8px;font-size:25px}.hero p{margin:0;color:#667085}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.card{background:white;border-radius:18px;padding:18px;box-shadow:0 4px 18px #0000000b}.number{font-size:30px;font-weight:800;margin-top:7px}.label{font-size:13px;color:#667085}.section{margin-top:22px}.section h2{font-size:19px;margin:0 0 12px}button{border:0;border-radius:12px;padding:13px 16px;background:#111827;color:white;font-weight:700;cursor:pointer}button:disabled{opacity:.6;cursor:wait}.mode-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.mode-btn{min-height:120px;text-align:left;padding:18px;border-radius:18px}.mode-btn strong{display:block;font-size:18px;margin-bottom:8px}.mode-btn span{display:block;font-size:13px;line-height:1.45;opacity:.8}.mode-op{background:#e85d04}.mode-prod{background:#2563eb}.form{display:grid;gap:10px}input{width:100%;padding:13px;border:1px solid #d7dce5;border-radius:12px;font-size:15px}.products{display:grid;gap:10px}.product,.opportunity{background:white;border-radius:16px;padding:17px;box-shadow:0 3px 14px #00000009}.product-image{width:100%;max-height:240px;object-fit:contain;border-radius:12px;margin-bottom:12px;background:#f8fafc}.product strong,.opportunity h3{display:block;margin-bottom:5px;font-size:17px}.price{font-weight:800;font-size:20px;margin-top:7px}.old-price{text-decoration:line-through;color:#667085;font-size:14px}.offer-data{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}.metric{background:#f5f7fb;border-radius:12px;padding:10px;text-align:center;font-size:12px}.metric b{display:block;font-size:16px;margin-top:4px}.score{background:#ecfdf3;color:#067647}.good{border-left:5px solid #16a34a}.medium{border-left:5px solid #f59e0b}.low{border-left:5px solid #94a3b8}.offer-box{margin-top:12px;padding:14px;background:#fff7ed;border-radius:14px;line-height:1.5}.empty{color:#667085;text-align:center;padding:20px}.muted{color:#667085;font-size:13px;line-height:1.5}.hidden{display:none}.buy-btn{display:block;text-align:center;margin-top:12px;background:#111827;color:white;text-decoration:none;padding:12px;border-radius:12px;font-weight:700}.approve-btn{width:100%;margin-top:10px;background:#12b76a}.reject-btn{width:100%;margin-top:8px;background:#667085}.channel-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.channel-grid label{padding:12px;border:1px solid #e4e7ec;border-radius:12px;background:#fff}.badge{display:inline-block;padding:5px 9px;border-radius:999px;font-size:12px;font-weight:700;background:#ecfdf3;color:#027a48}.search-head{display:flex;justify-content:space-between;align-items:center;gap:10px}.close-btn{background:#667085;padding:9px 12px;font-size:12px}@media(max-width:520px){.mode-grid{grid-template-columns:1fr}.offer-data{grid-template-columns:repeat(3,1fr)}.grid{grid-template-columns:1fr 1fr}}
</style></head>
<body><header><div class="brand">🚀 OFERTA IA</div><div class="sub">Central inteligente de ofertas</div></header>
<main>
<div class="hero"><h1>Encontre oportunidades de venda</h1><p>Escolha o que deseja fazer. <b>Oportunidades</b> e <b>Produtos</b> são funções independentes.</p></div>
<div class="grid"><div class="card"><div class="label">Produtos cadastrados</div><div class="number" id="products">0</div></div><div class="card"><div class="label">Ofertas geradas</div><div class="number" id="offers">0</div></div></div>
<div class="section"><h2>O que você quer fazer?</h2><div class="mode-grid">
<button class="mode-btn mode-op" id="openOpportunities"><strong>🔥 OPORTUNIDADES</strong><span>O sistema procura automaticamente produtos com maior potencial comercial. Não precisa informar produto.</span></button>
<button class="mode-btn mode-prod" id="openProducts"><strong>📦 PRODUTOS</strong><span>Pesquise um produto ou nicho específico. A pesquisa não mistura o ranking de oportunidades.</span></button>
</div></div>

<section id="opportunitySection" class="section hidden"><div class="search-head"><h2>🔥 Oportunidades</h2><button class="close-btn" id="closeOpportunities">Fechar</button></div><div class="card"><p class="muted">Modo automático: o OFERTA IA consulta sinais de produtos populares e ranqueia as melhores oportunidades disponíveis.</p><input id="opportunityNiche" placeholder="Opcional: informe um nicho, ex.: beleza, fitness, eletrônicos"><input id="opportunityLimit" type="number" min="5" max="30" value="10" placeholder="Quantidade"><button id="runOpportunities" style="margin-top:8px;background:#e85d04;width:100%">🔥 Encontrar oportunidades</button><div id="opportunityStatus" class="muted" style="margin-top:10px"></div><div id="opportunityList" style="margin-top:12px"></div></div></section>

<section id="productSection" class="section hidden"><div class="search-head"><h2>📦 Produtos</h2><button class="close-btn" id="closeProducts">Fechar</button></div><div class="card"><p class="muted">Pesquisa específica. Digite o produto ou nicho desejado. Resultados irrelevantes são filtrados antes de aparecer.</p><input id="productSearch" placeholder="Ex.: smartwatch, celular, air fryer"><input id="productLimit" type="number" min="1" max="20" value="10"><button id="runProductSearch" style="margin-top:8px;background:#2563eb;width:100%">🔎 Pesquisar produtos</button><div id="productSearchStatus" class="muted" style="margin-top:10px"></div><div id="productResults" style="margin-top:12px"></div></div></section>

<div class="section"><h2>📢 Canais de publicação</h2><div class="card"><div id="channelOptions" class="channel-grid"><label><input type="checkbox" value="whatsapp" checked> 💬 WhatsApp</label><label><input type="checkbox" value="instagram"> 📸 Instagram</label><label><input type="checkbox" value="telegram"> ✈️ Telegram</label></div></div></div>
<div class="section"><h2>🛒 Integração Mercado Livre</h2><div class="card"><div id="meliStatus" class="muted">Verificando conexão...</div><button id="meliConnectBtn" style="margin-top:10px;background:#2563eb">🔐 Conectar Mercado Livre</button><button id="meliDiagnosticBtn" style="margin-top:10px;background:#475467">🩺 Diagnosticar</button><div id="meliDiagnostic" class="muted" style="margin-top:10px"></div></div></div>
<div class="section"><h2>🛍️ Amazon</h2><div class="card"><div id="amazonStatus" class="muted">Nenhuma identificação salva.</div><input id="amazonTag" placeholder="Sua identificação de associado Amazon"><button id="amazonSaveBtn" style="margin-top:8px;background:#2563eb">💾 Salvar identificação</button></div></div>
<div class="section"><h2>➕ Cadastro manual</h2><div class="card"><form class="form" id="productForm"><input name="name" placeholder="Nome do produto" required><input name="store" placeholder="Loja"><input name="category" placeholder="Categoria"><input name="url" placeholder="Link do produto" id="productUrl"><button type="button" id="importBtn" style="background:#475467">🔎 Buscar dados pelo link</button><div id="importStatus" class="muted"></div><input name="affiliate_url" placeholder="Link de afiliado"><input name="old_price" type="number" step="0.01" placeholder="Preço antigo"><input name="current_price" type="number" step="0.01" placeholder="Preço atual"><input name="image_url" placeholder="URL da imagem"><button type="submit" id="submitProductBtn">Cadastrar produto</button></form></div></div>
<div class="section"><h2>📚 Meus produtos</h2><div id="productList" class="products"></div></div>
</main>
<script>
function money(v){return v==null?'—':'R$ '+Number(v).toFixed(2).replace('.',',')}function esc(t){return String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function channels(){return [...document.querySelectorAll('#channelOptions input:checked')].map(x=>x.value)}
function toggle(id,on){document.getElementById(id).classList.toggle('hidden',!on)}
function opportunityCard(p,i){let s=Number(p.opportunity_score||0);let label=s>=90?'EXCELENTE OPORTUNIDADE':s>=80?'BOA OPORTUNIDADE':s>=70?'OPORTUNIDADE MODERADA':'ANALISAR';return `<div class="opportunity" id="opp-${i}"><span class="badge">⭐ ${s.toFixed(0)}/100 · ${label}</span><h3>${esc(p.name)}</h3><div class="muted">${esc(p.store||'Mercado Livre')} · ${esc(p.category||'')}</div><div class="price">${money(p.current_price)}</div>${p.old_price?`<div class="old-price">de ${money(p.old_price)}</div>`:''}<div class="offer-data"><div class="metric">Desconto<b>${p.discount_rate!=null?Number(p.discount_rate).toFixed(1).replace('.',',')+'%':'—'}</b></div><div class="metric">Ranking<b>${p.rank_position?('#'+p.rank_position):'—'}</b></div><div class="metric">Confiança<b>${esc(p.data_confidence||'estimada')}</b></div></div>${p.image_url?`<img class="product-image" src="${esc(p.image_url)}" alt="">`:''}${p.url?`<a class="buy-btn" href="${esc(p.url)}" target="_blank" rel="noopener">🛒 Ver produto</a>`:''}<button class="approve-btn" onclick="approveOpportunity(${i})">✅ Aprovar e preparar oferta</button><button class="reject-btn" onclick="document.getElementById('opp-${i}').remove()">❌ Descartar</button></div>`}
async function loadOpportunities(){let status=document.getElementById('opportunityStatus'),list=document.getElementById('opportunityList'),btn=document.getElementById('runOpportunities');btn.disabled=true;btn.textContent='⏳ Analisando oportunidades...';status.textContent='Consultando dados e ranqueando produtos...';try{let r=await fetch('/api/mercadolivre/opportunities',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({niche:document.getElementById('opportunityNiche').value.trim(),limit:Number(document.getElementById('opportunityLimit').value||10)})});let d=await r.json();if(!r.ok)throw Error(d.detail||'Falha na descoberta.');window.currentOpportunities=d.items||[];list.innerHTML=window.currentOpportunities.length?window.currentOpportunities.map(opportunityCard).join(''):'<div class="empty">Nenhuma oportunidade encontrada com dados atuais suficientes.</div>';status.textContent=d.message||'Concluído.'}catch(e){status.textContent='⚠️ '+e.message}finally{btn.disabled=false;btn.textContent='🔥 Encontrar oportunidades'}}
async function searchProducts(){let q=document.getElementById('productSearch').value.trim(),out=document.getElementById('productResults'),status=document.getElementById('productSearchStatus');if(!q){status.textContent='Digite um produto ou nicho.';return}status.textContent='🔎 Pesquisando...';out.innerHTML='';try{let r=await fetch('/api/mercadolivre/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q,limit:Number(document.getElementById('productLimit').value||10)})});let d=await r.json();if(!r.ok)throw Error(d.detail||'Falha na pesquisa.');let items=d.items||[];out.innerHTML=items.length?items.map((p,i)=>`<div class="product"><strong>${esc(p.name)}</strong><div class="muted">${esc(p.store||'Mercado Livre')} · ${esc(p.category||'')}</div><div class="price">${money(p.current_price)}</div>${p.old_price?`<div class="old-price">de ${money(p.old_price)}</div>`:''}${p.image_url?`<img class="product-image" src="${esc(p.image_url)}" alt="">`:''}${p.url?`<a class="buy-btn" href="${esc(p.url)}" target="_blank" rel="noopener">Ver produto</a>`:''}<button class="approve-btn" onclick="addProduct(${i})">➕ Adicionar ao OFERTA IA</button></div>`).join(''):'<div class="empty">Nenhum produto relevante encontrado.</div>';window.currentSearchProducts=items;status.textContent=`✅ ${items.length} produto(s) relevante(s) encontrado(s).`}catch(e){status.textContent='⚠️ '+e.message}}
async function addProduct(i){let p=window.currentSearchProducts?.[i];if(!p)return;try{let r=await fetch('/api/products',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:p.name,store:p.store||'Mercado Livre',url:p.url,category:p.category,current_price:p.current_price,old_price:p.old_price,image_url:p.image_url,marketplace:p.marketplace||'mercadolivre',item_id:p.item_id})});let d=await r.json();if(!r.ok)throw Error(d.detail||'Falha ao salvar.');alert('Produto adicionado ao OFERTA IA.');loadProducts()}catch(e){alert(e.message)}}
async function approveOpportunity(i){let p=window.currentOpportunities?.[i];if(!p)return;let ch=channels();if(!ch.length){alert('Selecione pelo menos um canal.');return}let box=document.getElementById('opp-'+i);box.insertAdjacentHTML('beforeend','<div class="offer-box">🤖 Gerando oferta com IA...</div>');try{let r=await fetch('/api/approve-and-publish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product:p,channels:ch})});let d=await r.json();if(!r.ok)throw Error(d.detail||'Falha.');box.insertAdjacentHTML('beforeend','<div class="offer-box">✅ '+esc(d.message||'Oferta preparada.')+'</div>')}catch(e){box.insertAdjacentHTML('beforeend','<div class="offer-box">⚠️ '+esc(e.message)+'</div>')}}
async function loadProducts(){try{let r=await fetch('/api/products');let d=await r.json();document.getElementById('products').textContent=d.length;document.getElementById('productList').innerHTML=d.length?d.map(p=>`<div class="product"><strong>${esc(p.name)}</strong><div class="muted">${esc(p.store||'')} · ${esc(p.category||'')}</div><div class="price">${money(p.current_price)}</div></div>`).join(''):'<div class="empty">Nenhum produto cadastrado ainda.</div>'}catch(e){}}
async function importProduct(){let u=document.getElementById('productUrl').value.trim(),st=document.getElementById('importStatus');if(!u){st.textContent='Cole primeiro o link.';return}st.textContent='⏳ Buscando dados...';try{let r=await fetch('/api/import-product',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:u})});let d=await r.json();if(!r.ok)throw Error(d.detail||'Falha.');let f=document.getElementById('productForm');for(let k of ['name','store','category','url','image_url','old_price','current_price'])if(d[k]!=null&&f[k])f[k].value=d[k];st.textContent='✅ Dados encontrados.'}catch(e){st.textContent='⚠️ '+e.message}}
async function integrations(){try{let r=await fetch('/api/integrations/status');let d=await r.json();document.getElementById('meliStatus').textContent=d.mercadolivre?.connected?'🟢 Mercado Livre conectado.':'🟡 Mercado Livre não conectado.';document.getElementById('amazonStatus').textContent=d.amazon?.tag?'🟢 Identificação salva: '+d.amazon.tag:'Nenhuma identificação salva.';document.getElementById('amazonTag').value=d.amazon?.tag||''}catch(e){}}
async function diagnostic(){let o=document.getElementById('meliDiagnostic');o.textContent='🔄 Diagnosticando...';try{let r=await fetch('/api/mercadolivre/diagnostico');let d=await r.json();o.innerHTML=(d.tests||[]).map(x=>(x.ok?'✅ ':'❌ ')+esc(x.name)+': HTTP '+esc(x.http_status)+'<br>'+esc(x.message)).join('<br>')}catch(e){o.textContent='⚠️ '+e.message}}
document.addEventListener('DOMContentLoaded',()=>{document.getElementById('openOpportunities').onclick=()=>toggle('opportunitySection',true);document.getElementById('closeOpportunities').onclick=()=>toggle('opportunitySection',false);document.getElementById('openProducts').onclick=()=>toggle('productSection',true);document.getElementById('closeProducts').onclick=()=>toggle('productSection',false);document.getElementById('runOpportunities').onclick=loadOpportunities;document.getElementById('runProductSearch').onclick=searchProducts;document.getElementById('importBtn').onclick=importProduct;document.getElementById('meliConnectBtn').onclick=()=>location.href='/oauth/mercadolivre';document.getElementById('meliDiagnosticBtn').onclick=diagnostic;document.getElementById('amazonSaveBtn').onclick=async()=>{let tag=document.getElementById('amazonTag').value.trim();if(!tag)return;let r=await fetch('/api/amazon/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag})});let d=await r.json();document.getElementById('amazonStatus').textContent=r.ok?'🟢 Identificação salva.':'⚠️ '+(d.detail||'Erro')};document.getElementById('productForm').onsubmit=async e=>{e.preventDefault();let f=new FormData(e.target),body={name:f.get('name'),store:f.get('store')||null,category:f.get('category')||null,url:f.get('url')||null,affiliate_url:f.get('affiliate_url')||null,old_price:f.get('old_price')?Number(f.get('old_price')):null,current_price:f.get('current_price')?Number(f.get('current_price')):null,image_url:f.get('image_url')||null};let id=e.target.dataset.editId;let r=await fetch(id?'/api/products/'+id:'/api/products',{method:id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});let d=await r.json();if(!r.ok){alert(d.detail||'Erro');return}e.target.reset();delete e.target.dataset.editId;loadProducts();alert('Produto salvo com sucesso.')};loadProducts();integrations()})
</script></body></html>"""


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


def generate_ai_offer(product: dict, analysis: dict) -> dict:
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY não configurada no Render.")

    prompt = f"""Você é um especialista em copywriting para ofertas de e-commerce no Brasil.
Crie três versões da mesma oferta, usando SOMENTE os dados fornecidos.
Não invente características, avaliações, frete, garantia, estoque, prazo ou benefícios.
Use português do Brasil.

Retorne EXATAMENTE neste formato, mantendo os marcadores:
[WHATSAPP]
texto curto, direto e com emojis
[/WHATSAPP]
[INSTAGRAM]
texto para legenda do Instagram, com chamada para ação
[/INSTAGRAM]
[TELEGRAM]
texto curto para Telegram, com chamada para ação
[/TELEGRAM]
[HASHTAGS]
até 8 hashtags relacionadas ao produto/categoria
[/HASHTAGS]

Produto: {product.get('name')}
Loja: {product.get('store') or 'não informada'}
Categoria: {product.get('category') or 'não informada'}
Preço anterior: R$ {float(product.get('old_price') or 0):.2f}
Preço atual: R$ {float(product.get('current_price') or 0):.2f}
Desconto calculado: {analysis.get('discount', 0):.2f}%
Economia calculada: R$ {analysis.get('savings', 0):.2f}
"""

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        text = (response.text or "").strip()
        if not text:
            raise HTTPException(502, "O Gemini respondeu sem texto.")

        def section(tag: str) -> str:
            import re
            m = re.search(rf"\[{tag}\](.*?)\[/{tag}\]", text, re.S | re.I)
            return m.group(1).strip() if m else ""

        result = {
            "whatsapp": section("WHATSAPP"),
            "instagram": section("INSTAGRAM"),
            "telegram": section("TELEGRAM"),
            "hashtags": section("HASHTAGS"),
            "raw": text,
        }
        if not result["whatsapp"]:
            result["whatsapp"] = text
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Gemini: {exc}")


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "OFERTA IA"}



def _clean_text(value):
    if value is None:
        return None
    value = unescape(str(value))
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def _price_number(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    s = re.sub(r"[^\d,.\-]", "", s)

    if not s:
        return None

    # Trata formatos brasileiros e internacionais.
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        # "199.90" continua 199.90; "1.999" pode ser mil novecentos e noventa e nove.
        parts = s.split(".")
        if len(parts) == 2 and len(parts[1]) == 3:
            s = "".join(parts)
    try:
        return float(s)
    except Exception:
        return None


def _walk_jsonld(obj, found):
    if isinstance(obj, dict):
        found.append(obj)
        for value in obj.values():
            _walk_jsonld(value, found)
    elif isinstance(obj, list):
        for value in obj:
            _walk_jsonld(value, found)


def _extract_product_from_page(html, page_url):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    metas = {}

    for tag in soup.find_all("meta"):
        key = tag.get("property") or tag.get("name")
        value = tag.get("content")
        if key and value:
            metas[key.lower()] = _clean_text(value)

    title = metas.get("og:title") or metas.get("twitter:title")
    image = metas.get("og:image") or metas.get("twitter:image")
    description = metas.get("og:description") or metas.get("description")

    if image:
        image = urljoin(page_url, image)

    json_objects = []
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            _walk_jsonld(json.loads(raw), json_objects)
        except Exception:
            continue

    product_obj = None
    for obj in json_objects:
        types = obj.get("@type") if isinstance(obj, dict) else None
        types = types if isinstance(types, list) else [types]
        if any(str(t).lower() == "product" for t in types if t):
            product_obj = obj
            break

    if product_obj:
        title = title or _clean_text(product_obj.get("name"))
        image_value = product_obj.get("image")
        if isinstance(image_value, list):
            image_value = image_value[0] if image_value else None
        image = image or (urljoin(page_url, image_value) if image_value else None)

    offers = product_obj.get("offers") if product_obj else None
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    if not isinstance(offers, dict):
        offers = {}

    current_price = (
        _price_number(offers.get("price"))
        or _price_number(product_obj.get("price")) if product_obj else None
    )

    # Alguns sites expõem lowPrice/highPrice, mas não necessariamente o preço real.
    if current_price is None:
        current_price = _price_number(metas.get("product:price:amount"))

    store = None
    host = urlparse(page_url).netloc.lower()
    host = host.split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    if host:
        store = host.split(".")[0].replace("-", " ").title()

    category = None
    if product_obj:
        category = _clean_text(product_obj.get("category"))

    if not title and soup.title:
        title = _clean_text(soup.title.get_text())

    # Fallback simples para preço em páginas que não usam JSON-LD.
    if current_price is None:
        candidates = re.findall(
            r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*(?:,\d{2})|\d+(?:,\d{2})|\d+(?:\.\d{2}))",
            soup.get_text(" ", strip=True)
        )
        parsed = [_price_number(x) for x in candidates]
        parsed = [x for x in parsed if x is not None and 1 <= x <= 1000000]
        if parsed:
            current_price = min(parsed)

    # "Preço anterior" é propositalmente conservador: só usa dados estruturados
    # quando o site realmente fornece um preço anterior.
    old_price = None
    if product_obj:
        old_price = _price_number(product_obj.get("priceBefore"))
    if old_price is None:
        old_price = _price_number(metas.get("product:price:old"))

    return {
        "name": title,
        "store": store,
        "category": category,
        "url": page_url,
        "image_url": image,
        "old_price": old_price,
        "current_price": current_price,
        "description": description,
    }



def _opportunity_score_from_product(p: dict) -> float:
    """Transparent MVP score. Real marketplace signals replace these heuristics as connectors are enabled."""
    sales = float(p.get("sales") or 0)
    commission = float(p.get("commission_rate") or 0)
    discount = float(p.get("discount_rate") or 0)
    rating = float(p.get("rating") or 0)
    competition = p.get("competition_index")

    sales_score = min(30.0, math.log10(max(sales, 1) + 1) * 10.0)
    commission_score = min(20.0, commission * 2.0)
    discount_score = min(20.0, discount * 0.6)
    rating_score = min(10.0, rating * 2.0)
    competition_score = 10.0 if competition is None else max(0.0, 10.0 - float(competition) / 10.0)
    data_score = 10.0 if p.get("data_confidence") == "alta" else 6.0
    return round(min(100.0, sales_score + commission_score + discount_score + rating_score + competition_score + data_score), 2)


def _normalize_discovered_product(p: dict) -> dict:
    p = dict(p or {})
    if p.get("old_price") and p.get("current_price") and not p.get("discount_rate"):
        try:
            old = float(p["old_price"])
            cur = float(p["current_price"])
            if old > 0 and cur >= 0:
                p["discount_rate"] = round(max(0.0, (old-cur)/old*100), 2)
        except Exception:
            pass
    p["opportunity_score"] = _opportunity_score_from_product(p)
    return p


@app.post("/api/discover-opportunities")
def discover_opportunities(payload: dict):
    """
    Discovery-first MVP:
    - Reads existing marketplace/affiliate data already available in Supabase.
    - Ranks products by opportunity.
    - If no products exist, returns an explicit empty state instead of inventing products.
    Real Shopee/Amazon/other marketplace collectors plug into this endpoint next.
    """
    category = (payload.get("category") or "").strip().lower()
    min_discount = float(payload.get("min_discount") or 0)
    limit = max(1, min(50, int(payload.get("limit") or 10)))

    result = supabase.table("products").select("*").order("opportunity_score", desc=True).limit(200).execute()
    products = result.data or []

    filtered = []
    for p in products:
        if category and category not in str(p.get("category") or "").lower():
            continue
        discount = float(p.get("discount_rate") or 0)
        if not discount:
            old = p.get("old_price")
            cur = p.get("current_price")
            try:
                if old and cur and float(old) > 0:
                    discount = (float(old)-float(cur))/float(old)*100
            except Exception:
                discount = 0
        if discount < min_discount:
            continue
        filtered.append(_normalize_discovered_product(p))

    filtered.sort(key=lambda x: float(x.get("opportunity_score") or 0), reverse=True)
    return {
        "items": filtered[:limit],
        "source": "supabase_products",
        "automatic_collectors_ready": bool(os.getenv("SHOPEE_APP_ID") and os.getenv("SHOPEE_APP_SECRET"))
    }


@app.post("/api/approve-and-publish")
def approve_and_publish(payload: dict):
    product = payload.get("product") or {}
    channels = payload.get("channels") or []
    if not product.get("name"):
        raise HTTPException(400, "Produto inválido.")
    if not channels:
        raise HTTPException(400, "Selecione pelo menos um canal.")

    analysis = {
        "discount": float(product.get("discount_rate") or 0),
        "score": float(product.get("opportunity_score") or _opportunity_score_from_product(product)),
        "savings": max(0.0, float(product.get("old_price") or 0) - float(product.get("current_price") or 0))
    }
    generated = generate_ai_offer(product, analysis)

    # Persist the approved offer.
    offer_id = None
    try:
        offer_data = {
            "product_id": product.get("id"),
            "title": generated.get("whatsapp", product.get("name"))[:180],
            "description": generated.get("raw", ""),
            "discount": analysis["discount"],
            "score": analysis["score"],
            "status": "approved"
        }
        saved = supabase.table("offers").insert(offer_data).execute()
        if saved.data:
            offer_id = saved.data[0].get("id")
    except Exception:
        pass

    published = []
    for channel in channels:
        try:
            if offer_id:
                row = {
                    "offer_id": offer_id,
                    "channel": channel,
                    "status": "pending"
                }
                supabase.table("publications").insert(row).execute()
            published.append(channel)
        except Exception:
            # Keep the workflow alive; actual channel connector will handle the final send.
            published.append(channel)

    return {
        "ok": True,
        "offer_id": offer_id,
        "channels": published,
        "message": "Oferta aprovada. O sistema registrou os canais selecionados e está pronta para a publicação automática quando as conexões oficiais estiverem ativas.",
        "generated": generated
    }


@app.post("/api/import-product")
def import_product(payload: dict):
    url = (payload.get("url") or "").strip()

    if not url or not re.match(r"^https?://", url, re.I):
        raise HTTPException(400, "Informe uma URL completa começando com http:// ou https://.")

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 10) "
                    "AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"
                ),
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            },
            timeout=15,
            allow_redirects=True,
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type:
            raise HTTPException(400, "O link não parece ser uma página de produto.")

        data = _extract_product_from_page(response.text, response.url)

        if not data.get("name"):
            raise HTTPException(
                422,
                "A página abriu, mas não foi possível identificar o nome do produto."
            )

        data["source_url"] = response.url
        return data

    except HTTPException:
        raise
    except requests.RequestException as exc:
        raise HTTPException(502, f"Não consegui acessar a página: {exc}")
    except Exception as exc:
        raise HTTPException(502, f"Falha ao interpretar a página: {exc}")


@app.post("/api/generate-offer")
def generate_offer(payload: dict):
    product = payload.get("product") or {}
    analysis = payload.get("analysis") or {}
    if not product.get("name"):
        raise HTTPException(400, "Produto inválido.")

    generated = generate_ai_offer(product, analysis)

    try:
        offer_data = {
            "product_id": product.get("id"),
            "title": generated.get("whatsapp", product.get("name"))[:180],
            "description": generated.get("raw", ""),
            "discount": analysis.get("discount"),
            "score": analysis.get("score"),
            "status": "generated"
        }
        supabase.table("offers").insert(offer_data).execute()
    except Exception:
        pass

    return {**generated, "model": GEMINI_MODEL}




def _meli_credentials():
    return os.getenv("MELI_CLIENT_ID"), os.getenv("MELI_CLIENT_SECRET")

def _save_connection(provider, data):
    try:
        existing = supabase.table("affiliate_connections").select("id").eq("provider", provider).limit(1).execute().data
        payload = {"provider": provider, **data, "updated_at": datetime.now(timezone.utc).isoformat()}
        if existing:
            supabase.table("affiliate_connections").update(payload).eq("id", existing[0]["id"]).execute()
        else:
            supabase.table("affiliate_connections").insert(payload).execute()
    except Exception as exc:
        raise HTTPException(500, f"Não foi possível salvar a conexão: {exc}")

def _get_connection(provider):
    try:
        rows = supabase.table("affiliate_connections").select("*").eq("provider", provider).limit(1).execute().data or []
        return rows[0] if rows else None
    except Exception:
        return None

@app.get("/api/integrations/status")
def integrations_status():
    meli = _get_connection("mercadolivre")
    amazon = _get_connection("amazon")
    return {
        "mercadolivre": {"connected": bool(meli and meli.get("access_token"))},
        "amazon": {"tag": (amazon or {}).get("affiliate_tag", "")}
    }

@app.get("/oauth/mercadolivre")
def mercadolivre_oauth():
    client_id, client_secret = _meli_credentials()
    if not client_id or not client_secret:
        raise HTTPException(500, "Configure MELI_CLIENT_ID e MELI_CLIENT_SECRET no Render antes de conectar o Mercado Livre.")
    redirect_uri = "https://oferta-ia.onrender.com/oauth/mercadolivre/callback"
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(32)
    from urllib.parse import urlencode
    params = {"response_type":"code","client_id":client_id,"redirect_uri":redirect_uri,"state":state,"code_challenge":challenge,"code_challenge_method":"S256"}
    response = RedirectResponse("https://auth.mercadolivre.com.br/authorization?" + urlencode(params))
    response.set_cookie("meli_oauth_state", state, httponly=True, secure=True, samesite="lax", max_age=600)
    response.set_cookie("meli_code_verifier", verifier, httponly=True, secure=True, samesite="lax", max_age=600)
    return response

@app.get("/oauth/mercadolivre/callback")
def mercadolivre_callback(request: Request, code: str | None = None, state: str | None = None):
    if not code:
        raise HTTPException(400, "Mercado Livre não retornou o código de autorização.")

    saved_state = request.cookies.get("meli_oauth_state")
    verifier = request.cookies.get("meli_code_verifier")

    if not state or not saved_state or state != saved_state:
        raise HTTPException(400, "Sessão OAuth inválida ou expirada. Tente conectar novamente.")
    if not verifier:
        raise HTTPException(400, "Verificador PKCE não encontrado. Tente conectar novamente.")

    client_id, client_secret = _meli_credentials()
    if not client_id or not client_secret:
        raise HTTPException(500, "Configure MELI_CLIENT_ID e MELI_CLIENT_SECRET no Render.")

    redirect_uri = "https://oferta-ia.onrender.com/oauth/mercadolivre/callback"

    try:
        token_response = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": verifier,
            },
            timeout=20,
        )
        if not token_response.ok:
            detail = token_response.text[:500]
            raise HTTPException(502, f"Mercado Livre recusou a autorização: {detail}")

        token = token_response.json()
        access_token = token.get("access_token")
        refresh_token = token.get("refresh_token")

        if not access_token:
            raise HTTPException(502, "Mercado Livre não retornou access_token.")

        expires_in = int(token.get("expires_in") or 0)
        expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        ).isoformat() if expires_in else None

        _save_connection("mercadolivre", {
            "status": "connected",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "user_id": str(token.get("user_id") or ""),
        })

        response = RedirectResponse("/")
        response.delete_cookie("meli_oauth_state")
        response.delete_cookie("meli_code_verifier")
        return response

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Falha ao concluir conexão com Mercado Livre: {exc}")

@app.get("/api/mercadolivre/diagnostico")
def mercadolivre_diagnostico():
    """Diagnóstico seguro da autorização do Mercado Livre.

    Nunca devolve access_token, refresh_token ou client_secret ao navegador.
    """
    connection = _get_connection("mercadolivre")
    if not connection:
        raise HTTPException(400, "Nenhuma conexão do Mercado Livre foi encontrada no Supabase.")

    access_token = connection.get("access_token")
    if not access_token:
        raise HTTPException(400, "A conexão existe, mas não há access_token salvo.")

    app_id = os.getenv("MELI_CLIENT_ID") or "2432620888529017"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "OFERTA-IA/1.0",
    }

    tests = []
    app_info = {}

    def safe_json(response):
        try:
            data = response.json()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    # 1) Testa o token com o endpoint oficial de usuário.
    try:
        r = requests.get(
            "https://api.mercadolibre.com/users/me",
            headers=headers,
            timeout=15,
        )
        data = safe_json(r)
        tests.append({
            "name": "Token / users/me",
            "ok": r.ok,
            "http_status": r.status_code,
            "message": (
                f"Usuário autorizado: {data.get('nickname') or data.get('id') or 'sim'}"
                if r.ok else
                f"{data.get('message') or data.get('error') or r.text[:300]}"
            ),
        })
    except requests.RequestException as exc:
        tests.append({
            "name": "Token / users/me",
            "ok": False,
            "http_status": None,
            "message": f"Falha de comunicação: {exc}",
        })

    # 2) Consulta os dados da aplicação.
    try:
        r = requests.get(
            f"https://api.mercadolibre.com/applications/{app_id}",
            headers=headers,
            timeout=15,
        )
        data = safe_json(r)
        app_info = {
            "active": data.get("active"),
            "sandbox_mode": data.get("sandbox_mode"),
            "certification_status": data.get("certification_status"),
        }
        scopes = data.get("scopes")
        if isinstance(scopes, list):
            app_info["scopes"] = [str(x) for x in scopes[:20]]
        tests.append({
            "name": "Aplicação / applications/{APP_ID}",
            "ok": r.ok,
            "http_status": r.status_code,
            "message": (
                "Dados da aplicação consultados."
                if r.ok else
                f"{data.get('message') or data.get('error') or r.text[:300]}"
            ),
        })
    except requests.RequestException as exc:
        tests.append({
            "name": "Aplicação / applications/{APP_ID}",
            "ok": False,
            "http_status": None,
            "message": f"Falha de comunicação: {exc}",
        })

    # 3) Consulta os grants, quando permitido.
    try:
        r = requests.get(
            f"https://api.mercadolibre.com/applications/{app_id}/grants",
            headers=headers,
            timeout=15,
        )
        data = safe_json(r)
        if r.ok:
            grants = data.get("grants") if isinstance(data.get("grants"), list) else data.get("results")
            count = len(grants) if isinstance(grants, list) else None
            msg = f"Grants consultados{': ' + str(count) + ' registro(s)' if count is not None else '.'}"
        else:
            msg = data.get("message") or data.get("error") or r.text[:300]
        tests.append({
            "name": "Grants / applications/{APP_ID}/grants",
            "ok": r.ok,
            "http_status": r.status_code,
            "message": msg,
        })
    except requests.RequestException as exc:
        tests.append({
            "name": "Grants / applications/{APP_ID}/grants",
            "ok": False,
            "http_status": None,
            "message": f"Falha de comunicação: {exc}",
        })

    ok_count = sum(1 for x in tests if x.get("ok"))
    if tests and ok_count == len(tests):
        summary = "A autorização e a aplicação responderam normalmente nos testes realizados."
    elif tests and tests[0].get("ok"):
        summary = "O token está válido para users/me, mas pelo menos uma consulta adicional foi recusada."
    else:
        summary = "O token não foi aceito em users/me; isso aponta para autorização/token antes de qualquer busca de produto."

    return {
        "tests": tests,
        "app": app_info,
        "token_saved": True,
        "summary": summary,
    }

@app.get("/api/mercadolivre/search-diagnostic")
def mercadolivre_search_diagnostic(q: str = "relogio"):
    """Diagnóstico isolado dos endpoints de busca, sem gravar nada."""
    connection = _get_connection("mercadolivre")
    access_token = (connection or {}).get("access_token")
    if not access_token:
        raise HTTPException(401, "Mercado Livre não está conectado.")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "OFERTA-IA/1.0",
        "Accept": "application/json",
    }
    tests = []
    def run(name, url, params=None):
        try:
            r = requests.get(url, params=params, timeout=15, headers=headers)
            body = safe_json(r)
            tests.append({
                "name": name,
                "url": r.url,
                "http_status": r.status_code,
                "ok": r.ok,
                "response_keys": list(body.keys())[:20] if isinstance(body, dict) else [],
                "message": (body.get("message") or body.get("error") or "") if isinstance(body, dict) else "",
                "code": body.get("code") if isinstance(body, dict) else None,
                "blocked_by": body.get("blocked_by") if isinstance(body, dict) else None,
                "results_count": len(body.get("results") or []) if isinstance(body, dict) else None,
                "paging": body.get("paging") if isinstance(body, dict) else None,
            })
        except Exception as exc:
            tests.append({"name": name, "http_status": None, "ok": False, "message": str(exc)})
    run("products/search", "https://api.mercadolibre.com/products/search", {"status":"active","site_id":"MLB","q":q,"limit":10})
    # O endpoint tradicional é mantido apenas como diagnóstico; não é usado como fallback automático.
    run("sites/MLB/search", "https://api.mercadolibre.com/sites/MLB/search", {"q":q,"limit":5})
    return {"query": q, "tests": tests}


def _norm_text(value):
    import unicodedata
    text = str(value or '').lower()
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-z0-9 ]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _tokens(value):
    stop = {'de','da','do','das','dos','para','com','e','ou','mais','vendido','vendidos','promocao','oferta'}
    return [x for x in _norm_text(value).split() if len(x) > 2 and x not in stop]


def _relevance_score(query, title, category=''):
    q = _tokens(query)
    text = _norm_text(f'{title} {category}')
    if not q:
        return 0.0
    hits = sum(1 for t in q if t in text)
    score = hits / len(q)
    # Correção simples para erros comuns como smartwach -> smartwatch.
    if score == 0 and 'smartwach' in q and 'smartwatch' in text:
        score = 0.85
    return score


ACCESSORY_TERMS = {'capa','case','pelicula','capinha','cabo','carregador','fonte','adaptador','suporte','pulseira','bracelete','bateria','dock'}

def _looks_like_accessory(title):
    return bool(set(_tokens(title)) & ACCESSORY_TERMS)


def _opportunity_score(p):
    def n(v):
        try: return None if v in (None,'') else float(v)
        except Exception: return None
    rank=n(p.get('rank_position'))
    discount=n(p.get('discount_rate')) or 0
    rating=n(p.get('rating')) or 0
    competition=n(p.get('competition_index'))
    rank_score = max(0, 100 - (rank-1)*5) if rank else 45
    discount_score = min(100, discount*2.2)
    rating_score = min(100, max(0,(rating-3)*25)) if rating else 60
    competition_score = 100-min(100,max(0,competition)) if competition is not None else 50
    data_score = 100 if p.get('data_confidence') == 'alta' else 70
    completeness = sum(bool(p.get(k)) for k in ('current_price','url','image_url','item_id'))/4*100
    return round(max(0,min(100,rank_score*.35 + competition_score*.20 + discount_score*.15 + rating_score*.10 + data_score*.10 + completeness*.10)),2)


def _opportunity_label(score):
    if score >= 90: return 'EXCELENTE OPORTUNIDADE'
    if score >= 80: return 'BOA OPORTUNIDADE'
    if score >= 70: return 'OPORTUNIDADE MODERADA'
    return 'ANALISAR'


def _meli_headers(token):
    return {'Authorization': f'Bearer {token}', 'User-Agent':'OFERTA-IA/6.0', 'Accept':'application/json'}


def _meli_get(token, url, params=None, timeout=15):
    r=requests.get(url,params=params,headers=_meli_headers(token),timeout=timeout)
    if r.status_code in (401,403): return None,r.status_code
    r.raise_for_status()
    return r.json(),r.status_code


def _product_from_catalog(token, catalog_item, rank_position=None, query=''):
    pid=catalog_item.get('id') or catalog_item.get('catalog_product_id')
    if not pid: return None
    try:
        detail,status=_meli_get(token,f'https://api.mercadolibre.com/products/{pid}',timeout=12)
        if not detail: return None
        winner=detail.get('buy_box_winner') if isinstance(detail,dict) else None
        candidates=[winner] if isinstance(winner,dict) else []
        if not candidates:
            data,_=_meli_get(token,f'https://api.mercadolibre.com/products/{pid}/items',{'limit':10},timeout=12)
            if isinstance(data,dict): candidates=data.get('results') or data.get('items') or data.get('publications') or []
            elif isinstance(data,list): candidates=data
        best=None
        for c in candidates:
            if not isinstance(c,dict): continue
            iid=c.get('item_id') or c.get('id'); price=c.get('price')
            try: price=float(price)
            except Exception: price=None
            title=c.get('title') or detail.get('name') or catalog_item.get('name')
            if iid and price and price>0 and not _looks_like_accessory(title):
                if best is None or price < float(best.get('price') or 10**12): best=c
        if not best: return None
        old=best.get('original_price')
        try: old=float(old) if old not in (None,'') else None
        except Exception: old=None
        cur=float(best.get('price'))
        image=best.get('secure_thumbnail') or best.get('thumbnail')
        if not image:
            pics=detail.get('pictures') or catalog_item.get('pictures') or []
            if pics and isinstance(pics[0],dict): image=pics[0].get('secure_url') or pics[0].get('url')
        p={'name':best.get('title') or detail.get('name') or catalog_item.get('name') or 'Produto Mercado Livre','store':str((best.get('seller') or {}).get('nickname') or 'Mercado Livre'),'marketplace':'mercadolivre','product_id':pid,'catalog_product_id':pid,'item_id':best.get('item_id') or best.get('id'),'seller_id':best.get('seller_id') or (best.get('seller') or {}).get('id'),'url':best.get('permalink') or detail.get('permalink') or catalog_item.get('permalink'),'image_url':image,'current_price':cur,'old_price':old,'discount_rate':round((old-cur)/old*100,2) if old and old>cur else None,'category':detail.get('domain_id') or catalog_item.get('domain_id'),'rating':best.get('rating'),'condition':best.get('condition') or best.get('item_condition'),'rank_position':rank_position,'discovery_query':query,'data_confidence':'alta'}
        p['opportunity_score']=_opportunity_score(p);p['opportunity_label']=_opportunity_label(p['opportunity_score'])
        return p
    except Exception:
        return None


@app.post('/api/mercadolivre/opportunities')
def mercadolivre_opportunities(payload: dict):
    """Modo OPORTUNIDADES: usa o ranking oficial /highlights e não exige produto."""
    token=(_get_connection('mercadolivre') or {}).get('access_token')
    if not token: raise HTTPException(401,'Mercado Livre não está conectado.')
    niche=(payload.get('niche') or '').strip()
    try: limit=max(5,min(30,int(payload.get('limit') or 10)))
    except Exception: limit=10
    catalog=[]; seen=set(); diagnostics={'highlights':0,'catalog_details':0,'products':0}
    # Primeiro: rankings oficiais de mais vendidos. Quando há nicho, usamos tendências como ponte para localizar categorias/produtos do nicho.
    categories=['MLB1000','MLB1055','MLB1246','MLB1430','MLB1574','MLB1276','MLB1144','MLB1132']
    # IDs são apenas candidatos; se uma categoria não tiver highlights, seguimos sem erro.
    for cat in categories:
        try:
            data,status=_meli_get(token,f'https://api.mercadolibre.com/highlights/MLB/category/{cat}',timeout=10)
            if not data: continue
            diagnostics['highlights']+=1
            for x in data.get('content') or []:
                if x.get('type') not in ('PRODUCT','ITEM','USER_PRODUCT'): continue
                iid=x.get('id'); pos=x.get('position')
                key=(iid,pos)
                if iid and key not in seen: seen.add(key); catalog.append(({'id':iid},pos,'highlights'))
        except Exception: continue
    # Fallback/expansão por tendências + catálogo, principalmente para nichos.
    if niche or len(catalog)<10:
        queries=[niche] if niche else ['smartphone','smartwatch','fone bluetooth','air fryer','notebook','televisao','beleza','fitness','casa']
        try:
            trends,status=_meli_get(token,'https://api.mercadolibre.com/trends/MLB',timeout=12)
            if isinstance(trends,list): queries += [str(x.get('keyword')) for x in trends[:20] if isinstance(x,dict) and x.get('keyword')]
        except Exception: pass
        for q in list(dict.fromkeys([x for x in queries if x]))[:30]:
            try:
                data,status=_meli_get(token,'https://api.mercadolibre.com/products/search',{'status':'active','site_id':'MLB','q':q,'limit':12},timeout=12)
                for x in (data or {}).get('results') or []:
                    pid=x.get('id')
                    if pid and pid not in seen: seen.add(pid); catalog.append((x,None,q))
            except Exception: continue
    from concurrent.futures import ThreadPoolExecutor,as_completed
    products=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs=[pool.submit(_product_from_catalog,token,x,pos,q) for x,pos,q in catalog[:100]]
        for f in as_completed(futs):
            try:
                p=f.result()
                if p: products.append(p); diagnostics['products']+=1
            except Exception: pass
    if niche:
        products=[p for p in products if _relevance_score(niche,p.get('name',''),p.get('category',''))>=0.5]
    uniq={p.get('item_id') or p.get('product_id'):p for p in products if p.get('item_id') or p.get('product_id')}
    products=list(uniq.values()); products.sort(key=lambda p:(-float(p.get('opportunity_score') or 0), float(p.get('rank_position') or 999), -float(p.get('discount_rate') or 0)))
    selected=products[:limit]
    return {'mode':'opportunities','niche':niche or 'todos','items':selected,'returned':len(selected),'diagnostic':diagnostics,'message':f'Foram analisados {len(products)} produtos e selecionadas {len(selected)} oportunidades.' if selected else 'Não foram encontradas oportunidades com dados atuais suficientes.'}


@app.post('/api/mercadolivre/search')
def mercadolivre_search(payload: dict):
    """Modo PRODUTOS: pesquisa específica, sem score/ranking de oportunidades."""
    token=(_get_connection('mercadolivre') or {}).get('access_token')
    if not token: raise HTTPException(401,'Mercado Livre não está conectado.')
    query=(payload.get('query') or '').strip()
    if not query: raise HTTPException(400,'Informe um produto ou nicho.')
    try: limit=max(1,min(20,int(payload.get('limit') or 10)))
    except Exception: limit=10
    try:
        data,status=_meli_get(token,'https://api.mercadolibre.com/products/search',{'status':'active','site_id':'MLB','q':query,'limit':30},timeout=18)
    except Exception as exc: raise HTTPException(502,f'Falha na pesquisa do catálogo: {exc}')
    raw=(data or {}).get('results') or []; candidates=[]
    for x in raw:
        rel=_relevance_score(query,x.get('name') or x.get('title') or '',x.get('domain_id') or '')
        if rel<0.5: continue
        p=_product_from_catalog(token,x,None,query)
        if p:
            rel2=_relevance_score(query,p.get('name',''),p.get('category',''))
            if rel2>=0.5: p.pop('opportunity_score',None);p.pop('opportunity_label',None);p['relevance_score']=round(rel2,2);candidates.append(p)
    candidates.sort(key=lambda p:-float(p.get('relevance_score') or 0))
    return {'mode':'products','query':query,'items':candidates[:limit],'returned':min(limit,len(candidates)),'message':f'{min(limit,len(candidates))} produto(s) relevante(s) encontrado(s).'}


@app.get("/api/products")
def products():
    return (
        supabase.table("products")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
    )


@app.put("/api/products/{product_id}")
def update_product(product_id: int, product: Product):
    result = (
        supabase.table("products")
        .update(product.model_dump())
        .eq("id", product_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Produto não encontrado.")
    return result.data[0]


@app.post("/api/products")
def create_product(product: Product):
    result = supabase.table("products").insert(product.model_dump()).execute()
    if not result.data:
        raise HTTPException(400, "Não foi possível cadastrar o produto.")
    return result.data[0]
