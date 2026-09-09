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

# V9.3 — log estruturado para rastrear todo o caminho da descoberta.
# O Render captura stdout/stderr automaticamente. Nenhum token é registrado.
logger = logging.getLogger("oferta_ia.v9")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | V9.3 | %(levelname)s | %(message)s"))
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
    line = f"{datetime.now().strftime("%H:%M:%S")} | {stage} | {message}{suffix}"
    _V94_LOG_BUFFER.append(line)
    if len(_V94_LOG_BUFFER) > _V94_LOG_MAX_LINES:
        del _V94_LOG_BUFFER[:-_V94_LOG_MAX_LINES]
    logger.info("[%s] %s%s", stage, message, suffix)

def _v94_log_text():
    return "\n".join(_V94_LOG_BUFFER)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Configure SUPABASE_URL e SUPABASE_SECRET_KEY (ou SUPABASE_SERVICE_ROLE_KEY)."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI(title="OFERTA IA")

# Cache curto para evitar chamadas repetidas ao Mercado Livre e acelerar o painel.
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


HTML = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0b1220"><title>OFERTA IA</title>
<style>
:root{--bg:#f4f7fb;--card:#fff;--ink:#101828;--muted:#667085;--line:#e4e7ec;--orange:#f97316;--blue:#2563eb;--green:#12b76a;--dark:#0b1220;--red:#ef4444;--shadow:0 10px 30px rgba(16,24,40,.07)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}button,input{font:inherit}button{border:0;cursor:pointer}a{text-decoration:none;color:inherit}
.top{position:sticky;top:0;z-index:20;background:rgba(11,18,32,.96);color:#fff;padding:14px 16px;box-shadow:0 4px 20px rgba(0,0,0,.12)}.top-in{max-width:1100px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:12px}.brand{font-weight:900;font-size:20px}.brand small{display:block;font-size:11px;font-weight:500;color:#98a2b3;margin-top:2px}.status-dot{font-size:12px;color:#a7f3d0}
main{max-width:1100px;margin:auto;padding:18px 14px 70px}.hero{background:linear-gradient(135deg,#111827,#1d2939);color:#fff;border-radius:24px;padding:24px;margin-bottom:14px;box-shadow:var(--shadow)}.hero h1{margin:0;font-size:28px;line-height:1.12}.hero p{margin:9px 0 0;color:#cbd5e1;line-height:1.5}.hero-badge{display:inline-flex;background:#243244;border:1px solid #344054;border-radius:999px;padding:6px 10px;font-size:12px;margin-bottom:12px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px}.stat{background:var(--card);border:1px solid var(--line);border-radius:17px;padding:15px;box-shadow:var(--shadow)}.stat b{font-size:25px;display:block}.stat span{font-size:12px;color:var(--muted)}
.modes{display:grid;grid-template-columns:1fr 1fr;gap:12px}.mode{min-height:145px;border-radius:22px;padding:20px;color:#fff;text-align:left;box-shadow:var(--shadow);transition:.15s}.mode:hover{transform:translateY(-1px)}.mode.op{background:linear-gradient(135deg,#ea580c,#f97316)}.mode.prod{background:linear-gradient(135deg,#1d4ed8,#2563eb)}.mode .ico{font-size:28px}.mode strong{display:block;font-size:20px;margin:7px 0}.mode span{display:block;font-size:13px;line-height:1.45;opacity:.92}
.panel{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:18px;margin-top:16px;box-shadow:var(--shadow)}.panel-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}.panel-head h2{margin:0;font-size:19px}.close{background:#f2f4f7;color:#475467;border-radius:10px;padding:8px 11px;font-size:12px}.hidden{display:none!important}.muted{color:var(--muted);font-size:13px;line-height:1.5}.hint{background:#f8fafc;border:1px solid var(--line);padding:11px 12px;border-radius:13px;font-size:12px;color:#475467;margin:0 0 12px}
.form{display:grid;gap:9px}.input-row{display:grid;grid-template-columns:1fr 120px;gap:9px}input{width:100%;padding:13px 14px;border:1px solid #d0d5dd;border-radius:12px;background:#fff;color:var(--ink);outline:none}input:focus{border-color:#98a2b3;box-shadow:0 0 0 3px rgba(37,99,235,.08)}.primary{width:100%;padding:13px 15px;border-radius:12px;color:#fff;font-weight:800}.orange{background:var(--orange)}.blue{background:var(--blue)}.dark{background:#111827}.green{background:var(--green)}.ghost{background:#f2f4f7;color:#344054}.danger{background:#f2f4f7;color:#b42318}.loading{display:flex;align-items:center;gap:8px;padding:14px;border-radius:13px;background:#f8fafc;color:#475467;font-size:13px}.spinner{width:15px;height:15px;border:2px solid #d0d5dd;border-top-color:#344054;border-radius:50%;animation:spin .7s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
.results{display:grid;gap:12px;margin-top:13px}.card{border:1px solid var(--line);border-radius:18px;padding:14px;background:#fff;overflow:hidden}.product-card{display:grid;grid-template-columns:130px 1fr;gap:14px}.thumb{width:130px;height:130px;object-fit:contain;border-radius:14px;background:#f8fafc;border:1px solid #eef2f6}.title{font-weight:800;font-size:16px;line-height:1.35}.store{font-size:12px;color:var(--muted);margin-top:5px}.price{font-size:21px;font-weight:900;margin-top:8px}.old{text-decoration:line-through;color:#98a2b3;font-size:12px}.actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:11px}.action{padding:11px;border-radius:11px;text-align:center;font-size:13px;font-weight:800}.score-row{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-top:8px}.badge{display:inline-flex;padding:5px 9px;border-radius:999px;background:#ecfdf3;color:#027a48;font-size:11px;font-weight:900}.badge.blue-b{background:#eff6ff;color:#1d4ed8}.badge.orange-b{background:#fff7ed;color:#c2410c}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:10px}.metric{background:#f8fafc;border-radius:11px;padding:9px;text-align:center;font-size:10px;color:#667085}.metric b{display:block;font-size:14px;color:#101828;margin-top:3px}.op-card{border-left:5px solid #16a34a}.section-note{margin:14px 0 0;color:#98a2b3;font-size:11px}.empty{text-align:center;padding:25px;color:#667085;background:#f8fafc;border-radius:15px}.channels{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.channel{padding:12px;border:1px solid var(--line);border-radius:12px;font-size:13px;background:#fff}.channel input{width:auto;padding:0;margin-right:5px}.integration-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.integration{border:1px solid var(--line);border-radius:15px;padding:14px}.integration h3{margin:0 0 6px;font-size:14px}.small-btn{padding:10px 12px;border-radius:10px;font-size:12px;font-weight:800;margin-top:8px}.footer-note{margin-top:20px;text-align:center;color:#98a2b3;font-size:11px}
@media(max-width:700px){main{padding:12px 10px 55px}.hero{padding:20px;border-radius:20px}.hero h1{font-size:24px}.modes{grid-template-columns:1fr}.mode{min-height:125px}.stats{grid-template-columns:repeat(3,1fr)}.stat{padding:12px 9px}.stat b{font-size:21px}.product-card{grid-template-columns:92px 1fr;gap:11px}.thumb{width:92px;height:92px}.title{font-size:14px}.price{font-size:18px}.metrics{grid-template-columns:repeat(2,1fr)}.actions{grid-template-columns:1fr}.integration-grid{grid-template-columns:1fr}.input-row{grid-template-columns:1fr 95px}.channels{grid-template-columns:1fr}}
</style></head>
<body>
<header class="top"><div class="top-in"><div class="brand">🚀 OFERTA IA<small>Central inteligente de oportunidades</small></div><div id="connectionMini" class="status-dot">● sistema online</div></div></header>
<main>
<section class="hero"><span class="hero-badge">IA + Marketplace + Afiliados</span><h1>Encontre o que vale a pena vender.</h1><p>O OFERTA IA procura oportunidades automaticamente. A pesquisa de produtos é uma função separada para quando você já sabe o que procura.</p></section>
<section class="stats"><div class="stat"><b id="products">0</b><span>Produtos salvos</span></div><div class="stat"><b id="offers">0</b><span>Ofertas geradas</span></div><div class="stat"><b id="connectedStatus">—</b><span>Mercado Livre</span></div></section>
<section class="modes"><button class="mode op" id="openOpportunities"><span class="ico">🔥</span><strong>OPORTUNIDADES</strong><span>Deixe o sistema procurar sozinho os produtos com maior potencial comercial.</span></button><button class="mode prod" id="openProducts"><span class="ico">📦</span><strong>PRODUTOS</strong><span>Pesquise um produto ou nicho específico, sem misturar com o ranking de oportunidades.</span></button></section>

<section id="opportunitySection" class="panel hidden"><div class="panel-head"><h2>🔥 Oportunidades</h2><button class="close" id="closeOpportunities">Fechar</button></div><p class="hint">Você não precisa informar um produto. Deixe o nicho vazio para procurar oportunidades em várias categorias. O resultado aparece primeiro; o aprofundamento acontece somente nos melhores candidatos.</p><div class="form"><div class="input-row"><input id="opportunityNiche" placeholder="Opcional: beleza, eletrônicos, fitness..."><input id="opportunityLimit" type="number" min="5" max="20" value="10"></div><button id="runOpportunities" class="primary orange">🔥 Encontrar oportunidades</button></div><div id="opportunityStatus" class="muted" style="margin-top:10px"></div><div id="opportunityList" class="results"></div></section>

<section id="productSection" class="panel hidden"><div class="panel-head"><h2>📦 Pesquisar produtos</h2><button class="close" id="closeProducts">Fechar</button></div><p class="hint">Use para procurar algo específico. A busca filtra acessórios e resultados que não correspondem ao produto principal.</p><div class="form"><div class="input-row"><input id="productSearch" placeholder="Ex.: iPhone 16, smartwatch, air fryer"><input id="productLimit" type="number" min="1" max="20" value="10"></div><button id="runProductSearch" class="primary blue">🔎 Pesquisar produtos</button></div><div id="productSearchStatus" class="muted" style="margin-top:10px"></div><div id="productResults" class="results"></div></section>

<section id="diagnosticSection" class="panel">
<div class="panel-head"><h2>🛠️ Diagnóstico / Log</h2></div>
<p class="hint">Use esta área depois de testar o garimpo. O log mostra onde a busca encontrou ou perdeu candidatos, sem exibir tokens ou segredos.</p>
<div class="actions">
<button id="refreshLogBtn" class="action dark">🔄 Atualizar log</button>
<button id="copyLogBtn" class="action" style="background:#ecfdf3;color:#027a48">📋 Copiar log</button>
</div>
<div class="actions">
<a class="action" href="/api/v9/log.txt" target="_blank" rel="noopener">📄 Abrir log .txt</a>
<button id="clearLogBtn" class="action" style="background:#f2f4f7;color:#344054">🧹 Limpar tela</button>
</div>
<pre id="v94Log" style="margin-top:10px;white-space:pre-wrap;word-break:break-word;background:#0b1220;color:#e5e7eb;border-radius:14px;padding:12px;font-size:11px;line-height:1.55;max-height:420px;overflow:auto">Nenhum log disponível. Execute uma busca de oportunidades primeiro.</pre>
<div id="v94LogStatus" class="muted" style="margin-top:8px"></div>
</section>

<section class="panel"><div class="panel-head"><h2>📢 Canais</h2></div><div id="channelOptions" class="channels"><label class="channel"><input type="checkbox" value="whatsapp" checked>💬 WhatsApp</label><label class="channel"><input type="checkbox" value="instagram">📸 Instagram</label><label class="channel"><input type="checkbox" value="telegram">✈️ Telegram</label></div></section>
<section class="panel"><div class="panel-head"><h2>🔌 Conexões</h2></div><div class="integration-grid"><div class="integration"><h3>🛒 Mercado Livre</h3><div id="meliStatus" class="muted">Verificando...</div><button id="meliConnectBtn" class="small-btn blue">🔐 Conectar</button><button id="meliDiagnosticBtn" class="small-btn ghost">🩺 Diagnóstico</button><div id="meliDiagnostic" class="muted" style="margin-top:8px"></div></div><div class="integration"><h3>🛍️ Amazon</h3><div id="amazonStatus" class="muted">Nenhuma identificação salva.</div><input id="amazonTag" placeholder="Identificação de associado" style="margin-top:8px"><button id="amazonSaveBtn" class="small-btn blue">💾 Salvar</button></div></div></section>
<section class="panel"><div class="panel-head"><h2>➕ Cadastro manual</h2></div><p class="hint">Use apenas quando quiser cadastrar uma oferta que não veio da descoberta automática.</p><form class="form" id="productForm"><input name="name" placeholder="Nome do produto" required><div class="input-row"><input name="store" placeholder="Loja"><input name="category" placeholder="Categoria"></div><input name="url" placeholder="Link do produto" id="productUrl"><button type="button" id="importBtn" class="small-btn ghost">🔎 Buscar dados pelo link</button><div id="importStatus" class="muted"></div><input name="affiliate_url" placeholder="Link de afiliado (quando disponível)"><div class="input-row"><input name="old_price" type="number" step="0.01" placeholder="Preço antigo"><input name="current_price" type="number" step="0.01" placeholder="Preço atual"></div><input name="image_url" placeholder="URL da imagem"><button type="submit" id="submitProductBtn" class="primary dark">Cadastrar produto</button></form></section>
<section class="panel"><div class="panel-head"><h2>📚 Meus produtos</h2></div><div id="productList" class="results"></div></section>
<div class="footer-note">OFERTA IA • descoberta primeiro, decisão depois, automação por etapas.</div>
</main>
<script>
const $=id=>document.getElementById(id);const esc=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=v=>v==null||v===''?'—':'R$ '+Number(v).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});
const channels=()=>[...document.querySelectorAll('#channelOptions input:checked')].map(x=>x.value);
function toggle(id,on){$(id).classList.toggle('hidden',!on);if(on)$(id).scrollIntoView({behavior:'smooth',block:'start'})}
function loading(el,text){el.innerHTML='<div class="loading"><span class="spinner"></span>'+esc(text)+'</div>'}
function productCard(p,i,mode){const img=p.image_url?`<img class="thumb" src="${esc(p.image_url)}" alt="" loading="lazy">`:'<div class="thumb"></div>';const score=p.relevance_score!=null?`<span class="badge blue-b">Relevância ${Math.round(Number(p.relevance_score)*100)}%</span>`:'';const save=mode==='products'?`<button class="action" style="background:#ecfdf3;color:#027a48" onclick="addProduct(${i})">➕ Salvar</button>`:'';return `<article class="card product-card">${img}<div><div class="title">${esc(p.name)}</div><div class="store">${esc(p.store||'Mercado Livre')} ${p.category?'· '+esc(p.category):''}</div>${p.current_price!=null?`<div class="price">${money(p.current_price)}</div>`:''}${p.old_price?`<div class="old">de ${money(p.old_price)}</div>`:''}<div class="score-row">${score}<span class="badge orange-b">${esc(p.data_confidence||'catálogo')}</span></div><div class="actions">${p.url?`<a class="action dark" href="${esc(p.url)}" target="_blank" rel="noopener">🛒 Ver produto</a>`:''}${save}</div></div></article>`}
function opportunityCard(p,i){const s=Number(p.opportunity_score||0);const label=s>=90?'EXCELENTE':s>=80?'BOA':s>=70?'MODERADA':'ANALISAR';return `<article class="card op-card"><div class="score-row"><span class="badge">🔥 ${s.toFixed(0)}/100 · ${label}</span><span class="badge blue-b">${esc(p.data_confidence||'dados parciais')}</span></div><div style="margin-top:9px" class="title">${esc(p.name)}</div><div class="store">${esc(p.store||'Mercado Livre')} ${p.category?'· '+esc(p.category):''}</div>${p.image_url?`<img class="thumb" style="width:100%;height:190px;margin-top:10px" src="${esc(p.image_url)}" alt="" loading="lazy">`:''}<div class="price">${money(p.current_price)}</div>${p.old_price?`<div class="old">de ${money(p.old_price)}</div>`:''}<div class="metrics"><div class="metric">Desconto<b>${p.discount_rate!=null?Number(p.discount_rate).toFixed(1).replace('.',',')+'%':'—'}</b></div><div class="metric">Ranking<b>${p.rank_position?'#'+p.rank_position:'—'}</b></div><div class="metric">Avaliação<b>${p.rating?Number(p.rating).toFixed(1):'—'}</b></div><div class="metric">Concorrência<b>${p.competition_index!=null?Number(p.competition_index).toFixed(0):'—'}</b></div></div><div class="actions"><a class="action dark" href="${esc(p.url||'#')}" target="_blank" rel="noopener">🛒 Ver produto</a><button class="action" style="background:#ecfdf3;color:#027a48" onclick="approveOpportunity(${i})">✅ Aprovar</button></div><button class="action" style="width:100%;margin-top:8px;background:#f2f4f7" onclick="this.closest('article').remove()">Descartar</button></article>`}
async function jsonFetch(url,opts={}){const r=await fetch(url,opts);let d={};try{d=await r.json()}catch{}if(!r.ok)throw Error(d.detail||'Erro inesperado.');return d}
async function loadDashboard(){try{const p=await jsonFetch('/api/products');$('products').textContent=(p||[]).length;const s=await jsonFetch('/api/integrations/status');const ok=!!s.mercadolivre?.connected;$('connectedStatus').textContent=ok?'OK':'—';$('meliStatus').textContent=ok?'🟢 Mercado Livre conectado.':'🟡 Mercado Livre não conectado.';$('amazonStatus').textContent=s.amazon?.tag?'🟢 Identificação salva: '+s.amazon.tag:'Nenhuma identificação salva.';$('amazonTag').value=s.amazon?.tag||''}catch(e){}}
async function loadOffersCount(){try{const d=await jsonFetch('/api/dashboard');$('offers').textContent=d.offers??0}catch(e){}}
async function refreshV94Log(){
 const out=$('v94Log'),status=$('v94LogStatus');
 if(!out) return;
 try{
   const d=await jsonFetch('/api/v9/diagnostic',{cache:'no-store'});
   out.textContent=d.log||'Nenhum log disponível. Execute uma busca de oportunidades primeiro.';
   status.textContent=d.diagnostic?.trace_id?('Rastreamento: '+d.diagnostic.trace_id):'Log atualizado.';
   out.scrollTop=out.scrollHeight;
 }catch(e){status.textContent='⚠️ '+e.message}
}
async function copyV94Log(){
 const out=$('v94Log'),status=$('v94LogStatus');
 const txt=out?.textContent||'';
 if(!txt || txt.startsWith('Nenhum log disponível')){
   await refreshV94Log();
 }
 const finalTxt=$('v94Log')?.textContent||'';
 try{
   await navigator.clipboard.writeText(finalTxt);
   status.textContent='✅ Log copiado. Agora é só colar aqui no ChatGPT.';
 }catch(e){
   status.textContent='⚠️ Não foi possível copiar automaticamente. Abra o log .txt e copie o conteúdo.';
 }
}
$('refreshLogBtn')?.addEventListener('click',refreshV94Log);
$('copyLogBtn')?.addEventListener('click',copyV94Log);
$('clearLogBtn')?.addEventListener('click',()=>{ $('v94Log').textContent='Tela limpa. Execute ou atualize o log.'; $('v94LogStatus').textContent=''; });

async function loadOpportunities(){const list=$('opportunityList'),status=$('opportunityStatus'),btn=$('runOpportunities');btn.disabled=true;btn.textContent='⏳ Procurando...';loading(list,'Buscando candidatos e priorizando os melhores...');status.textContent='Primeiro o ranking; depois o aprofundamento dos melhores produtos.';try{const d=await jsonFetch('/api/v9/opportunities',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({niche:$('opportunityNiche').value.trim(),limit:Number($('opportunityLimit').value||10)})});window.currentOpportunities=d.items||d.opportunities||[];list.innerHTML=window.currentOpportunities.length?window.currentOpportunities.map(opportunityCard).join(''):'<div class="empty">Nenhuma oportunidade com dados atuais suficientes.</div>';status.textContent=d.message||'Concluído.';await refreshV94Log()}catch(e){list.innerHTML='';status.textContent='⚠️ '+e.message;await refreshV94Log()}finally{btn.disabled=false;btn.textContent='🔥 Encontrar oportunidades'}}
async function searchProducts(){const q=$('productSearch').value.trim(),out=$('productResults'),status=$('productSearchStatus');if(!q){status.textContent='Digite um produto ou nicho.';return}loading(out,'Pesquisando e filtrando resultados...');status.textContent='Buscando apenas produtos compatíveis com sua pesquisa.';try{const d=await jsonFetch('/api/mercadolivre/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q,limit:Number($('productLimit').value||10)})});window.currentSearchProducts=d.items||[];out.innerHTML=window.currentSearchProducts.length?window.currentSearchProducts.map((p,i)=>productCard(p,i,'products')).join(''):'<div class="empty">Nenhum produto principal relevante encontrado.</div>';status.textContent=`✅ ${window.currentSearchProducts.length} produto(s) relevante(s).`}catch(e){out.innerHTML='';status.textContent='⚠️ '+e.message}}
async function addProduct(i){const p=window.currentSearchProducts?.[i];if(!p)return;try{await jsonFetch('/api/products',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:p.name,store:p.store||'Mercado Livre',url:p.url,category:p.category,current_price:p.current_price,old_price:p.old_price,image_url:p.image_url,marketplace:p.marketplace||'mercadolivre',item_id:p.item_id})});alert('Produto salvo no OFERTA IA.');loadDashboard()}catch(e){alert(e.message)}}
async function approveOpportunity(i){const p=window.currentOpportunities?.[i];if(!p)return;const btns=document.querySelectorAll('#opportunityList button');btns.forEach(b=>b.disabled=true);try{const d=await jsonFetch('/api/approve-and-publish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product:p,channels:channels()})});alert(d.message||'Oferta aprovada.');loadOffersCount()}catch(e){alert(e.message)}finally{btns.forEach(b=>b.disabled=false)}}
async function diagnostic(){const o=$('meliDiagnostic');o.textContent='🔄 Diagnosticando...';try{const d=await jsonFetch('/api/mercadolivre/diagnostico');o.innerHTML=(d.tests||[]).map(x=>(x.ok?'✅ ':'❌ ')+esc(x.name)+': HTTP '+esc(x.http_status)+'<br>'+esc(x.message)).join('<br><br>')}catch(e){o.textContent='⚠️ '+e.message}}
async function loadProducts(){const out=$('productList');try{const items=await jsonFetch('/api/products');if(!items.length){out.innerHTML='<div class="empty">Nenhum produto salvo ainda.</div>';return}out.innerHTML=items.slice(0,20).map((p,i)=>productCard(p,i,'saved')).join('')}catch(e){out.innerHTML='<div class="empty">Não foi possível carregar os produtos.</div>'}}
async function importProduct(){const url=$('productUrl').value.trim(),st=$('importStatus');if(!url){st.textContent='Informe o link primeiro.';return}st.textContent='🔎 Lendo página...';try{const d=await jsonFetch('/api/import-product',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});const f=$('productForm');f.elements.name.value=d.name||'';f.elements.store.value=d.store||'';f.elements.category.value=d.category||'';f.elements.old_price.value=d.old_price??'';f.elements.current_price.value=d.current_price??'';f.elements.image_url.value=d.image_url||'';f.elements.url.value=d.source_url||url;st.textContent='✅ Dados encontrados. Confira antes de salvar.'}catch(e){st.textContent='⚠️ '+e.message}}
document.addEventListener('DOMContentLoaded',()=>{$('openOpportunities').onclick=()=>toggle('opportunitySection',true);$('closeOpportunities').onclick=()=>toggle('opportunitySection',false);$('openProducts').onclick=()=>toggle('productSection',true);$('closeProducts').onclick=()=>toggle('productSection',false);$('runOpportunities').onclick=loadOpportunities;$('runProductSearch').onclick=searchProducts;$('importBtn').onclick=importProduct;$('meliConnectBtn').onclick=()=>location.href='/oauth/mercadolivre';$('meliDiagnosticBtn').onclick=diagnostic;$('amazonSaveBtn').onclick=async()=>{const tag=$('amazonTag').value.trim();if(!tag)return;try{await jsonFetch('/api/amazon/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag})});$('amazonStatus').textContent='🟢 Identificação salva.'}catch(e){$('amazonStatus').textContent='⚠️ '+e.message}};$('productForm').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target),body={name:f.get('name'),store:f.get('store')||null,category:f.get('category')||null,url:f.get('url')||null,affiliate_url:f.get('affiliate_url')||null,old_price:f.get('old_price')?Number(f.get('old_price')):null,current_price:f.get('current_price')?Number(f.get('current_price')):null,image_url:f.get('image_url')||null};try{await jsonFetch('/api/products',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});e.target.reset();$('importStatus').textContent='';alert('Produto salvo com sucesso.');loadDashboard();loadProducts()}catch(e){alert(e.message)}};loadDashboard();loadOffersCount();loadProducts()})
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


def _canonical_query(query):
    q = _norm_text(query)
    aliases = {
        'smartwach': 'smartwatch',
        'smart watch': 'smartwatch',
        'iphon': 'iphone',
        'airfrayer': 'air fryer',
        'airfryer': 'air fryer',
    }
    return aliases.get(q, q)

def _relevance_score(query, title, category=''):
    query = _canonical_query(query)
    q = _tokens(query)
    text = _norm_text(f'{title} {category}')
    if not q:
        return 0.0
    hits = sum(1 for t in q if t in text)
    score = hits / len(q)
    if len(q) == 1 and q[0] in text:
        score = 1.0
    return score


ACCESSORY_TERMS = {'capa','case','pelicula','película','capinha','cabo','carregador','fonte','adaptador','suporte','pulseira','bracelete','bateria','dock','microfone','microphone','teclado','mouse','hub','pelicula','tripé','tripe','bolsa','suporte','controle','controle remoto','relogio','relógio'}

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
    """Descoberta rápida: coleta rankings em paralelo e aprofunda apenas os melhores candidatos."""
    token = (_get_connection('mercadolivre') or {}).get('access_token')
    if not token:
        raise HTTPException(401, 'Mercado Livre não está conectado.')
    niche = _canonical_query((payload.get('niche') or '').strip())
    try:
        limit = max(5, min(20, int(payload.get('limit') or 10)))
    except Exception:
        limit = 10

    cache_key = f"opp:{niche}:{limit}"
    cached = _cache_get(cache_key)
    if cached:
        return {**cached, 'cached': True}

    from concurrent.futures import ThreadPoolExecutor, as_completed
    categories = ['MLB1000','MLB1055','MLB1246','MLB1430','MLB1574','MLB1276','MLB1144','MLB1132']
    candidates = []
    seen = set()

    def fetch_highlight(cat):
        return cat, _meli_get(token, f'https://api.mercadolibre.com/highlights/MLB/category/{cat}', timeout=8)[0]

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch_highlight, cat) for cat in categories]
        for f in as_completed(futures):
            try:
                cat, data = f.result()
                for x in (data or {}).get('content') or []:
                    if x.get('type') not in ('PRODUCT','ITEM','USER_PRODUCT'):
                        continue
                    pid = x.get('id')
                    if pid and pid not in seen:
                        seen.add(pid)
                        candidates.append(({'id': pid}, x.get('position'), cat))
            except Exception:
                pass

    # Nicho é opcional. Quando informado, usamos poucas buscas de catálogo em paralelo.
    if niche:
        queries = [niche]
        try:
            words = _tokens(niche)
            if len(words) > 1:
                queries += words[:2]
        except Exception:
            pass
        def search_catalog(q):
            try:
                data, _ = _meli_get(token, 'https://api.mercadolibre.com/products/search',
                                    {'status':'active','site_id':'MLB','q':q,'limit':15}, timeout=8)
                return q, (data or {}).get('results') or []
            except Exception:
                return q, []
        with ThreadPoolExecutor(max_workers=min(3, len(queries))) as pool:
            for q, rows in pool.map(search_catalog, list(dict.fromkeys(queries))):
                for x in rows:
                    pid = x.get('id')
                    title = x.get('name') or x.get('title') or ''
                    if pid and pid not in seen and not _looks_like_accessory(title) and _relevance_score(niche, title, x.get('domain_id','')) >= 0.5:
                        seen.add(pid)
                        candidates.append((x, None, q))

    if not candidates:
        return {'mode':'opportunities','niche':niche or 'todos','items':[],'returned':0,'message':'Nenhum candidato foi retornado pelo Mercado Livre agora.','cached':False}

    # A posição do ranking é suficiente para selecionar os candidatos antes do enriquecimento.
    candidates.sort(key=lambda x: (999 if x[1] is None else int(x[1])))
    enrich_limit = min(len(candidates), max(limit * 2, 16), 28)
    selected_candidates = candidates[:enrich_limit]
    products = []

    def enrich(row):
        x, pos, q = row
        return _product_from_catalog(token, x, pos, q)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(enrich, row) for row in selected_candidates]
        for f in as_completed(futures):
            try:
                p = f.result()
                if p and not _looks_like_accessory(p.get('name','')):
                    if niche and _relevance_score(niche, p.get('name',''), p.get('category','')) < 0.5:
                        continue
                    products.append(p)
            except Exception:
                pass

    uniq = {}
    for p in products:
        key = p.get('item_id') or p.get('product_id') or p.get('catalog_product_id') or p.get('name')
        if key and (key not in uniq or float(p.get('opportunity_score') or 0) > float(uniq[key].get('opportunity_score') or 0)):
            uniq[key] = p
    products = list(uniq.values())
    products.sort(key=lambda p: (-float(p.get('opportunity_score') or 0), float(p.get('rank_position') or 999), -float(p.get('discount_rate') or 0)))
    selected = products[:limit]
    result = {'mode':'opportunities','niche':niche or 'todos','items':selected,'returned':len(selected),
              'message':f'{len(selected)} oportunidade(s) encontrada(s) após analisar {len(selected_candidates)} candidatos.','cached':False}
    return _cache_set(cache_key, result)


@app.post('/api/mercadolivre/search')
def mercadolivre_search(payload: dict):
    """Busca específica com filtro forte para produto principal e resposta rápida."""
    token = (_get_connection('mercadolivre') or {}).get('access_token')
    if not token:
        raise HTTPException(401, 'Mercado Livre não está conectado.')
    query = _canonical_query((payload.get('query') or '').strip())
    if not query:
        raise HTTPException(400, 'Informe um produto ou nicho.')
    try:
        limit = max(1, min(20, int(payload.get('limit') or 10)))
    except Exception:
        limit = 10

    cache_key = f"search:{query}:{limit}"
    cached = _cache_get(cache_key)
    if cached:
        return {**cached, 'cached': True}

    try:
        data, _ = _meli_get(token, 'https://api.mercadolibre.com/products/search',
                            {'status':'active','site_id':'MLB','q':query,'limit':40}, timeout=8)
    except Exception as exc:
        raise HTTPException(502, f'Falha na pesquisa do catálogo: {exc}')

    raw = (data or {}).get('results') or []
    relevant = []
    for x in raw:
        title = x.get('name') or x.get('title') or ''
        if _looks_like_accessory(title):
            continue
        rel = _relevance_score(query, title, x.get('domain_id') or '')
        if rel >= 0.5:
            relevant.append((x, rel))
    relevant.sort(key=lambda z: (-z[1], z[0].get('name') or z[0].get('title') or ''))

    # Só os melhores candidatos recebem chamadas adicionais ao catálogo.
    candidates = []
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_product_from_catalog, token, x, None, query): (x, rel) for x, rel in relevant[:max(limit * 2, 12)]}
        for f in as_completed(futures):
            x, rel = futures[f]
            catalog_title = x.get('name') or x.get('title') or 'Produto'
            try:
                p = f.result()
            except Exception:
                p = None
            # Se a publicação vencedora virou um acessório (ex.: microfone para iPhone), descartamos o enriquecimento e usamos o produto do catálogo.
            if p and (_looks_like_accessory(p.get('name','')) or _relevance_score(query, p.get('name',''), p.get('category','')) < 0.5):
                p = None
            if not p:
                pid = x.get('id')
                if pid:
                    pictures = x.get('pictures') or []
                    image = pictures[0].get('url') if pictures and isinstance(pictures[0], dict) else None
                    p = {'name':catalog_title,'store':'Mercado Livre','marketplace':'mercadolivre','catalog_product_id':pid,
                         'url':f'https://www.mercadolivre.com.br/p/{pid}','image_url':image,'category':x.get('domain_id'),
                         'current_price':None,'relevance_score':round(rel,2),'data_confidence':'catalogo'}
            if p:
                p.pop('opportunity_score', None); p.pop('opportunity_label', None)
                p['relevance_score'] = round(max(rel, _relevance_score(query, p.get('name',''), p.get('category',''))), 2)
                candidates.append(p)

    uniq = {}
    for p in candidates:
        key = p.get('item_id') or p.get('product_id') or p.get('catalog_product_id') or p.get('name')
        if key not in uniq or p['relevance_score'] > uniq[key]['relevance_score']:
            uniq[key] = p
    selected = list(uniq.values())
    selected.sort(key=lambda p: (-float(p.get('relevance_score') or 0), p.get('name','')))
    result = {'mode':'products','query':query,'items':selected[:limit],'returned':min(len(selected),limit),
              'message':f'{min(len(selected),limit)} produto(s) relevante(s) encontrado(s).','cached':False}
    return _cache_set(cache_key, result)


@app.post("/api/amazon/settings")
def amazon_settings(payload: dict):
    tag = (payload.get("tag") or "").strip()
    if not tag:
        raise HTTPException(400, "Informe a identificação da Amazon.")
    _save_connection("amazon", {"status": "configured", "affiliate_tag": tag})
    return {"ok": True, "tag": tag}


@app.get("/api/dashboard")
def dashboard():
    try:
        products_count = len(supabase.table("products").select("id").execute().data or [])
    except Exception:
        products_count = 0
    try:
        offers_count = len(supabase.table("offers").select("id").execute().data or [])
    except Exception:
        offers_count = 0
    return {"products": products_count, "offers": offers_count}


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


# ============================================================
# OFERTA IA V9 — MOTOR DE OPORTUNIDADES INTEGRADO
# ============================================================
from concurrent.futures import ThreadPoolExecutor, as_completed

V9_WEIGHTS = {
    "demand": 0.25,
    "commission": 0.20,
    "low_competition": 0.20,
    "discount": 0.10,
    "price": 0.10,
    "rating": 0.05,
    "trend": 0.05,
    "potential": 0.05,
}

def _v9_num(v, default=None):
    try:
        if v in (None, ""):
            return default
        return float(v)
    except Exception:
        return default

def _v9_demand_score(position, trend_strength=0):
    if not position:
        base = 50.0
    elif position == 1: base = 100.0
    elif position == 2: base = 98.0
    elif position == 3: base = 96.0
    elif position == 4: base = 94.0
    elif position == 5: base = 92.0
    elif position <= 10: base = 91.0 - (position - 6) * 1.5
    elif position <= 15: base = 84.0 - (position - 11) * 2
    elif position <= 20: base = 74.0 - (position - 16) * 2
    else: base = 55.0
    return round(min(100, base * .75 + trend_strength * .25), 2)

def _v9_commission_score(rate):
    r = _v9_num(rate)
    if r is None: return 0.0
    if r <= 0: return 0.0
    if r <= 2: return 15.0
    if r <= 4: return 30.0
    if r <= 6: return 45.0
    if r <= 8: return 60.0
    if r <= 10: return 75.0
    if r <= 12: return 85.0
    if r <= 14: return 92.0
    if r <= 15: return 97.0
    return 100.0

def _v9_discount_score(discount):
    d = _v9_num(discount)
    if d is None: return 0.0
    if d <= 0: return 0.0
    if d <= 4: return 15.0
    if d <= 9: return 35.0
    if d <= 14: return 55.0
    if d <= 19: return 70.0
    if d <= 24: return 80.0
    if d <= 29: return 87.0
    if d <= 39: return 94.0
    if d <= 49: return 98.0
    return 100.0

def _v9_rating_score(rating):
    r = _v9_num(rating)
    if r is None: return 0.0
    if r < 3: return 0.0
    if r < 3.5: return 30.0
    if r < 4: return 50.0
    if r < 4.3: return 65.0
    if r < 4.5: return 75.0
    if r < 4.7: return 85.0
    if r < 4.9: return 93.0
    if r < 5: return 98.0
    return 100.0

def _v9_trend_score(rank):
    if not rank: return 0.0
    if rank <= 10: return 100.0
    if rank <= 20: return 90.0
    if rank <= 30: return 75.0
    if rank <= 40: return 60.0
    return 45.0

def _v9_price_score(price):
    p = _v9_num(price)
    if p is None or p <= 0: return 0.0
    if p <= 80: return 92.0
    if p <= 150: return 100.0
    if p <= 300: return 94.0
    if p <= 600: return 82.0
    if p <= 1200: return 65.0
    return 45.0

def _v9_potential_score(demand, commission, discount, price, rating, trend):
    return round(
        demand*.30 + commission*.20 + discount*.15 +
        price*.10 + rating*.10 + trend*.15, 2
    )

def _v9_classification(score):
    if score >= 90: return "🟢 OPORTUNIDADE EXCEPCIONAL", "excepcional"
    if score >= 80: return "🟢 EXCELENTE OPORTUNIDADE", "excelente"
    if score >= 70: return "🟡 BOA OPORTUNIDADE", "boa"
    if score >= 60: return "🟠 OPORTUNIDADE MODERADA", "moderada"
    return "🔴 DESCARTAR", "descartar"

def _v9_confidence(item):
    checks = [
        bool(item.get("item_id")),
        bool(item.get("url")),
        item.get("current_price") is not None,
        item.get("rank_position") is not None,
        item.get("marketplace") == "mercadolivre",
    ]
    score = sum(checks) / len(checks) * 100
    if item.get("competition_estimated"): score -= 10
    if item.get("commission_rate") is None: score -= 8
    return round(max(0, min(100, score)), 2)



def _v9_valid_meli_token():
    """
    Retorna um access_token válido.
    O token do Mercado Livre expira; quando estiver próximo do vencimento,
    troca automaticamente usando o refresh_token salvo no Supabase.
    """
    conn = _get_connection("mercadolivre") or {}
    access = conn.get("access_token")
    refresh = conn.get("refresh_token")
    expires_at = conn.get("expires_at")

    def expired_or_near(value):
        if not value:
            return True
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt <= datetime.now(timezone.utc) + timedelta(minutes=5)
        except Exception:
            return True

    if access and not expired_or_near(expires_at):
        return access

    client_id, client_secret = _meli_credentials()
    if not client_id or not client_secret or not refresh:
        return None

    try:
        response = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh,
            },
            timeout=15,
        )
        if not response.ok:
            return None

        token = response.json()
        new_access = token.get("access_token")
        new_refresh = token.get("refresh_token") or refresh
        expires_in = int(token.get("expires_in") or 0)
        new_expires = (
            datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        ).isoformat() if expires_in else None

        if not new_access:
            return None

        _save_connection("mercadolivre", {
            "status": "connected",
            "access_token": new_access,
            "refresh_token": new_refresh,
            "expires_at": new_expires,
            "user_id": str(token.get("user_id") or conn.get("user_id") or ""),
        })
        return new_access
    except Exception:
        return None


def _v9_fetch_json(token, url, params=None, timeout=10):
    """GET seguro para o Mercado Livre, com uma tentativa de renovação."""
    for attempt in range(2):
        r = requests.get(
            url,
            params=params or {},
            headers=_meli_headers(token),
            timeout=timeout,
        )
        if r.status_code == 401 and attempt == 0:
            fresh = _v9_valid_meli_token()
            if fresh and fresh != token:
                token = fresh
                continue
        if r.status_code in (401, 403):
            return None, r.status_code
        if not r.ok:
            return None, r.status_code
        try:
            return r.json(), r.status_code
        except Exception:
            return None, r.status_code
    return None, 401


def _v9_get_item(token, item_id):
    """Obtém uma publicação real e ativa, registrando exatamente por que foi rejeitada."""
    data, status = _v9_fetch_json(
        token, f"https://api.mercadolibre.com/items/{item_id}", timeout=8
    )
    if not isinstance(data, dict):
        logger.warning("[VALIDATE] item_rejected reason=no_item_data item_id=%s http=%s", item_id, status)
        return None

    if data.get("status") != "active":
        logger.info("[VALIDATE] item_rejected reason=inactive item_id=%s item_status=%s", item_id, data.get("status"))
        return None

    permalink = data.get("permalink")
    if not permalink or not str(permalink).startswith("http"):
        logger.info("[VALIDATE] item_rejected reason=no_permalink item_id=%s", item_id)
        return None

    price = _v9_num(data.get("price"))
    if price is None or price <= 0:
        logger.info("[VALIDATE] item_rejected reason=no_valid_price item_id=%s raw_price=%s", item_id, data.get("price"))
        return None

    old = _v9_num(data.get("original_price"))
    return {
        "item_id": data.get("id"),
        "name": data.get("title") or "Produto Mercado Livre",
        "url": permalink,
        "current_price": price,
        "old_price": old,
        "discount_rate": round((old-price)/old*100, 2) if old and old > price else None,
        "category": data.get("category_id"),
        "image_url": data.get("secure_thumbnail") or data.get("thumbnail"),
        "seller_id": data.get("seller_id"),
        "rating": None,
        "marketplace": "mercadolivre",
    }


def _v9_catalog_to_item(token, product_id, rank_position=None, query=""):
    """
    Converte PRODUCT/USER_PRODUCT do ranking em uma publicação ITEM real.
    Primeiro tenta o buy_box_winner; depois lista publicações do produto;
    por fim valida cada item diretamente em /items/{id}.
    """
    detail, _ = _v9_fetch_json(
        token, f"https://api.mercadolibre.com/products/{product_id}", timeout=8
    )
    if not isinstance(detail, dict):
        return None

    item_ids = []

    winner = detail.get("buy_box_winner")
    if isinstance(winner, dict):
        iid = winner.get("item_id") or winner.get("id")
        if iid:
            item_ids.append(iid)

    data, _ = _v9_fetch_json(
        token,
        f"https://api.mercadolibre.com/products/{product_id}/items",
        {"limit": 20},
        timeout=8,
    )
    if isinstance(data, dict):
        for row in (data.get("results") or data.get("items") or data.get("publications") or []):
            if isinstance(row, dict):
                iid = row.get("item_id") or row.get("id")
            else:
                iid = row
            if iid:
                item_ids.append(iid)

    # Alguns formatos de catálogo podem devolver o item dentro do winner.
    for iid in item_ids:
        item = _v9_get_item(token, str(iid))
        if not item:
            continue
        if _looks_like_accessory(item.get("name", "")):
            continue
        item["rank_position"] = rank_position
        item["discovery_query"] = query
        item["catalog_product_id"] = product_id
        return item

    return None


def _v9_search_listings(token, query, limit=20, sort=None, category_id=None):
    """Busca publicações reais no marketplace."""
    params = {"q": query, "limit": max(1, min(50, int(limit or 20)))}
    if sort:
        params["sort"] = sort
    if category_id:
        params["category"] = category_id

    # IMPORTANTE: domínio correto é mercadolibre.com.
    data, _ = _v9_fetch_json(
        token,
        "https://api.mercadolibre.com/sites/MLB/search",
        params,
        timeout=8,
    )
    return data.get("results", []) if isinstance(data, dict) else []


def _v9_trends(token, category_id=None):
    path = "https://api.mercadolibre.com/trends/MLB"
    if category_id:
        path += f"/{category_id}"
    data, _ = _v9_fetch_json(token, path, timeout=8)
    return data if isinstance(data, list) else []


def _v9_trend_rank_for_name(name, trends):
    nt = _norm_text(name)
    if not nt:
        return None
    tokens = set(_tokens(name))
    best = None
    for idx, row in enumerate(trends[:50], start=1):
        kw = _norm_text((row or {}).get("keyword"))
        if not kw:
            continue
        kt = set(_tokens(kw))
        if not kt:
            continue
        overlap = len(tokens & kt) / max(1, len(kt))
        if kw in nt or overlap >= 0.6:
            if best is None or overlap > best[1]:
                best = (idx, overlap)
    return best[0] if best else None


def _v9_seed_queries(niche, trends, max_queries=8):
    """
    Gera consultas de descoberta sem depender de categorias-pai.
    Tendências são uma fonte oficial de demanda/popularidade.
    """
    queries = []
    if niche:
        queries.append(niche)
        parts = _tokens(niche)
        queries.extend(parts[:3])
    else:
        # /trends retorna até 50 termos populares; usamos uma amostra curta
        # para manter o tempo de resposta adequado.
        for row in trends[:max_queries]:
            kw = (row or {}).get("keyword")
            if kw:
                queries.append(str(kw))

        # Fallback caso a API de trends esteja temporariamente indisponível.
        if not queries:
            queries = [
                "celular",
                "air fryer",
                "smartwatch",
                "fone bluetooth",
                "notebook",
                "aspirador",
                "beleza",
                "casa",
            ]

    clean = []
    seen = set()
    for q in queries:
        q = str(q).strip()
        key = _norm_text(q)
        if q and key and key not in seen:
            seen.add(key)
            clean.append(q)
    return clean[:max_queries]


def _v9_analyze(item, rank_position=None, trend_rank=None, commission_rate=None):
    p = dict(item)
    price = _v9_num(p.get("current_price"))
    old = _v9_num(p.get("old_price"))
    discount = _v9_num(p.get("discount_rate"))
    if discount is None and old and price and old > price:
        discount = round((old-price)/old*100, 2)

    demand = _v9_demand_score(rank_position, _v9_trend_score(trend_rank))
    commission = _v9_commission_score(commission_rate)

    # Não inventamos concorrência. Até existir uma fonte real de
    # concorrência de afiliados, o índice permanece estimado/neutro.
    competition_index = 50.0
    low_competition = 100.0 - competition_index

    dscore = _v9_discount_score(discount)
    pscore = _v9_price_score(price)
    rscore = _v9_rating_score(p.get("rating"))
    tscore = _v9_trend_score(trend_rank)
    potential = _v9_potential_score(
        demand, commission, dscore, pscore, rscore, tscore
    )

    score = (
        demand*.25 + commission*.20 + low_competition*.20 +
        dscore*.10 + pscore*.10 + rscore*.05 +
        tscore*.05 + potential*.05
    )

    p.update({
        "commission_rate": commission_rate,
        "commission_value": (
            round(price*float(commission_rate)/100, 2)
            if price and commission_rate is not None else None
        ),
        "discount_rate": discount,
        "rank_position": rank_position,
        "trend_rank": trend_rank,
        "demand_score": round(demand, 2),
        "commission_score": round(commission, 2),
        "competition_index": competition_index,
        "competition_score": round(low_competition, 2),
        "competition_estimated": True,
        "discount_score": round(dscore, 2),
        "price_score": round(pscore, 2),
        "rating_score": round(rscore, 2),
        "trend_score": round(tscore, 2),
        "potential_score": round(potential, 2),
        "opportunity_score": round(score, 2),
        "marketplace": "mercadolivre",
    })
    p["data_confidence"] = _v9_confidence(p)
    p["classification"], p["classification_key"] = _v9_classification(
        p["opportunity_score"]
    )
    return p

@app.post("/api/v9/opportunities")
def v9_opportunities(payload: dict):
    """V9.3: garimpo com diagnóstico por etapa e erros visíveis no log do Render."""
    global _V93_LAST_DIAGNOSTIC, _V94_LOG_BUFFER
    _V94_LOG_BUFFER = []
    trace = uuid.uuid4().hex[:8]
    started = time.time()
    diag = {"trace_id": trace, "token_valid": False, "trends_requests": 0, "trend_terms": 0,
            "queries": 0, "search_requests_ok": 0, "search_requests_error": 0,
            "raw_candidates": 0, "filtered_candidates": 0, "item_requests": 0,
            "item_active": 0, "with_price": 0, "with_url": 0, "validated_products": 0,
            "final": 0, "errors": []}

    def err(stage, message, **fields):
        if len(diag["errors"]) < 20:
            diag["errors"].append({"stage": stage, "message": message, **fields})
        _v93_log(stage, message, trace=trace, **fields)

    _v93_log("START", "Início do garimpo", trace=trace)
    token = _v9_valid_meli_token()
    if not token:
        err("AUTH", "Não foi possível obter token válido")
        diag["elapsed_ms"] = round((time.time()-started)*1000)
        _V93_LAST_DIAGNOSTIC = diag
        raise HTTPException(401, "Mercado Livre sem sessão válida. Conecte novamente o Mercado Livre.")
    diag["token_valid"] = True
    _v93_log("AUTH", "Token válido", trace=trace)

    niche = _canonical_query((payload.get("niche") or "").strip())
    try: limit = max(5, min(20, int(payload.get("limit") or payload.get("quantity") or 10)))
    except Exception: limit = 10
    category_id = (payload.get("category_id") or "").strip() or None

    trends = []
    try:
        diag["trends_requests"] += 1
        trends = _v9_trends(token, category_id) or []
        diag["trend_terms"] = len(trends)
        _v93_log("TRENDS", "Tendências carregadas", trace=trace, terms=len(trends))
    except Exception as exc:
        err("TRENDS", "Falha ao carregar tendências", error=type(exc).__name__)

    try: queries = _v9_seed_queries(niche, trends, max_queries=8)
    except Exception as exc:
        queries = [niche] if niche else ["smartphone", "air fryer", "fone bluetooth", "notebook", "smartwatch"]
        err("QUERIES", "Falha ao montar consultas; usando fallback", error=type(exc).__name__)
    queries = list(dict.fromkeys([q for q in queries if q]))[:8]
    diag["queries"] = len(queries)
    _v93_log("QUERIES", "Consultas definidas", trace=trace, count=len(queries), queries=" || ".join(queries))

    raw_candidates, seen_items = [], set()
    def collect_query(q):
        try:
            rows = _v9_search_listings(token, q, limit=max(12, min(25, limit*2)), sort=None, category_id=category_id)
            return q, rows, None
        except Exception as exc: return q, [], exc

    with ThreadPoolExecutor(max_workers=min(8, len(queries) or 1)) as pool:
        futures = [pool.submit(collect_query, q) for q in queries]
        for future in as_completed(futures):
            q, rows, exc = future.result()
            if exc:
                diag["search_requests_error"] += 1
                err("SEARCH", "Exceção na busca", query=q, error=type(exc).__name__)
                continue
            diag["search_requests_ok"] += 1
            _v93_log("SEARCH", "Busca concluída", trace=trace, query=q, rows=len(rows))
            for row in rows:
                if not isinstance(row, dict): continue
                diag["raw_candidates"] += 1
                iid, title = row.get("id"), row.get("title") or ""
                if not iid or iid in seen_items or _looks_like_accessory(title): continue
                if niche and _relevance_score(niche, title, row.get("category_id") or "") < 0.35: continue
                seen_items.add(iid)
                raw_candidates.append({"item_id": iid, "query": q,
                    "trend_rank": _v9_trend_rank_for_name(title, trends), "search_row": row})

    diag["filtered_candidates"] = len(raw_candidates)
    _v93_log("CANDIDATES", "Candidatos após filtros", trace=trace, raw=diag["raw_candidates"], kept=len(raw_candidates))

    enrich = raw_candidates[:max(limit*4, 40)]
    products, errors_counter = [], Counter()
    def enrich_one(candidate):
        iid, pos, q = candidate.get("item_id"), candidate.get("rank_position"), candidate.get("query") or ""
        try:
            diag["item_requests"] += 1
            item = _v9_get_item(token, iid)
            if not item:
                errors_counter["item_invalid"] += 1
                return None
            diag["item_active"] += 1
            if item.get("current_price") is not None: diag["with_price"] += 1
            if item.get("url"): diag["with_url"] += 1
            item["rank_position"], item["discovery_query"] = pos, q
            tr = candidate.get("trend_rank")
            if tr is None: tr = _v9_trend_rank_for_name(item.get("name", ""), trends)
            return _v9_analyze(item, pos, tr, None)
        except Exception as exc:
            errors_counter[type(exc).__name__] += 1
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(enrich_one, c) for c in enrich]
        for future in as_completed(futures):
            item = future.result()
            if item: products.append(item)

    diag["validated_products"] = len(products)
    for k,v in errors_counter.items():
        if k != "item_invalid": diag["errors"].append({"stage":"VALIDATE","message":"Erro em candidato","error":k,"count":v})
    _v93_log("VALIDATE", "Validação concluída", trace=trace, requested=len(enrich), active=diag["item_active"], price=diag["with_price"], url=diag["with_url"], valid=len(products), invalid=errors_counter.get("item_invalid",0))

    unique = {}
    for p in products:
        key = p.get("item_id") or p.get("name")
        if key and (key not in unique or float(p.get("opportunity_score") or 0) > float(unique[key].get("opportunity_score") or 0)): unique[key] = p
    products = list(unique.values())
    products.sort(key=lambda p:(-float(p.get("opportunity_score") or 0), 999 if p.get("trend_rank") is None else int(p.get("trend_rank")), float(p.get("current_price") or 10**12)))
    selected = products[:limit]
    diag["final"] = len(selected); diag["elapsed_ms"] = round((time.time()-started)*1000)
    _V93_LAST_DIAGNOSTIC = diag
    _v93_log("END", "Garimpo encerrado", trace=trace, final=len(selected), elapsed_ms=diag["elapsed_ms"])
    message = f"{len(selected)} oportunidade(s) encontrada(s). Rastreamento {trace}." if selected else f"Nenhuma oportunidade passou. Rastreamento {trace}."
    return {"status":"ok","engine":"OFERTA IA V9.4","mode":"opportunities","niche":niche or "todos","items":selected,"opportunities":selected,"returned":len(selected),"candidates_found":len(raw_candidates),"validated":len(products),"diagnostic":diag,"message":message,"cached":False}

@app.get("/api/v9/diagnostic")
def v9_diagnostic():
    return {
        "status": "ok",
        "engine": "OFERTA IA V9.4",
        "diagnostic": _V93_LAST_DIAGNOSTIC,
        "log": _v94_log_text(),
    }

@app.get("/api/v9/log.txt")
def v9_log_txt():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        _v94_log_text() or "Nenhum log disponível. Execute uma busca de oportunidades primeiro.",
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'inline; filename="oferta-ia-ultimo-log.txt"'},
    )

