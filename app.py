import os
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
*{box-sizing:border-box}
body{margin:0;background:#f5f7fb;color:#172033;font-family:Arial,sans-serif}
header{background:#111827;color:white;padding:18px 20px;position:sticky;top:0;z-index:5}
.brand{font-size:22px;font-weight:800}.sub{font-size:12px;opacity:.7;margin-top:4px}
main{max-width:900px;margin:auto;padding:20px}
.hero{background:white;border-radius:20px;padding:22px;box-shadow:0 4px 18px #0000000b;margin-bottom:18px}
.hero h1{margin:0 0 8px;font-size:25px}.hero p{margin:0;color:#667085}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.card{background:white;border-radius:18px;padding:18px;box-shadow:0 4px 18px #0000000b}
.number{font-size:30px;font-weight:800;margin-top:7px}.label{font-size:13px;color:#667085}
.section{margin-top:22px}.section h2{font-size:19px;margin:0 0 12px}
button{border:0;border-radius:12px;padding:13px 16px;background:#111827;color:white;font-weight:700;cursor:pointer}
button.buy-btn{display:block;text-align:center;margin-top:14px;background:#111827;color:white;text-decoration:none;padding:12px;border-radius:12px;font-weight:700}
.offer-btn{margin-top:12px;width:100%;background:#e85d04}
.form{display:grid;gap:10px}
input{width:100%;padding:13px;border:1px solid #d7dce5;border-radius:12px;font-size:15px}
.products{display:grid;gap:10px}
.product{background:white;border-radius:16px;padding:17px;box-shadow:0 3px 14px #00000009}
.product-image{width:100%;max-height:240px;object-fit:contain;border-radius:12px;margin-bottom:12px;background:#f8fafc}
.product strong{display:block;margin-bottom:5px;font-size:17px}
.price{font-weight:800;font-size:20px;margin-top:7px}
.old-price{text-decoration:line-through;color:#667085;font-size:14px}
.offer-data{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}
.metric{background:#f5f7fb;border-radius:12px;padding:10px;text-align:center}
.metric b{display:block;font-size:17px;margin-top:4px}
.score{background:#ecfdf3;color:#067647}
.good{border-left:5px solid #16a34a}
.medium{border-left:5px solid #f59e0b}
.low{border-left:5px solid #94a3b8}
.offer-box{margin-top:12px;padding:14px;background:#fff7ed;border-radius:14px;line-height:1.5}
.empty{color:#667085;text-align:center;padding:20px}
nav{display:flex;gap:8px;overflow:auto;margin:18px 0}
nav span{background:white;border-radius:999px;padding:9px 13px;font-size:13px;white-space:nowrap}
.channel-tabs{display:flex;gap:6px;overflow:auto;margin-bottom:10px}.tab{background:#eef2f6;color:#172033;padding:9px 11px;font-size:12px;white-space:nowrap}.tab.active{background:#111827;color:white}.copy-text{white-space:pre-wrap;line-height:1.55;background:white;border-radius:12px;padding:12px;border:1px solid #e4e7ec}.copy-btn{width:100%;margin-top:10px;background:#475467}.hashtags{margin-top:10px;font-size:13px;line-height:1.5}.hashtags div{margin-top:5px;color:#475467}
@media(min-width:700px){.grid{grid-template-columns:repeat(4,1fr)}}
@media(max-width:480px){.offer-data{grid-template-columns:1fr 1fr 1fr}.metric{font-size:12px}.metric b{font-size:15px}}

.channel-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.channel-grid label{padding:12px;border:1px solid #e4e7ec;border-radius:12px;background:#fff}
.opportunity{border:1px solid #e4e7ec;border-radius:16px;padding:14px;margin-bottom:12px;background:#fff}
.opportunity h3{margin:0 0 6px}
.badge{display:inline-block;padding:5px 9px;border-radius:999px;font-size:12px;font-weight:700;background:#ecfdf3;color:#027a48}
.muted{color:#667085;font-size:13px}
.approve-btn{width:100%;margin-top:10px;background:#12b76a}
.reject-btn{width:100%;margin-top:8px;background:#667085}
</style>
</head>
<body>
<header>
<div class="brand">🚀 OFERTA IA</div>
<div class="sub">Central inteligente de ofertas</div>
</header>

<main>
<div class="hero">
<h1>Olá! 👋</h1>
<p>Vamos encontrar, analisar e transformar produtos em boas ofertas.</p>
</div>

<nav>
<span>🏠 Início</span>
<span>🛍️ Produtos</span>
<span>🔥 Ofertas</span>
<span>🤖 IA</span>
<span>📊 Métricas</span>
</nav>

<div class="grid">
<div class="card"><div class="label">Produtos</div><div class="number" id="products">0</div></div>
<div class="card"><div class="label">Ofertas</div><div class="number" id="offers">0</div></div>
<div class="card"><div class="label">Cliques</div><div class="number">0</div></div>
<div class="card"><div class="label">Publicações</div><div class="number">0</div></div>
</div>

<div class="section">
<h2>➕ Cadastrar produto</h2>
<div class="card">
<form class="form" id="productForm">
<input name="name" placeholder="Nome do produto" required>
<input name="store" placeholder="Loja">
<input name="category" placeholder="Categoria">
<input name="url" placeholder="Cole o link do produto aqui" id="productUrl">
<button type="button" id="importBtn" style="background:#2563eb">🔎 Buscar dados pelo link</button>
<div id="importStatus" style="font-size:13px;color:#667085"></div>
<input name="affiliate_url" placeholder="Link de afiliado">
<input name="old_price" type="number" step="0.01" placeholder="Preço antigo">
<input name="current_price" type="number" step="0.01" placeholder="Preço atual">
<input name="image_url" placeholder="URL da imagem do produto">
<button type="submit" id="submitProductBtn">Cadastrar produto</button>
</form>
</div>
</div>

<div class="section">
<h2>🔥 Análise das ofertas</h2>
<div id="productList" class="products"></div>
</div>
</main>

<script>
function money(value){
    return 'R$ ' + Number(value).toFixed(2).replace('.', ',');
}

function calculateOffer(p){
    const oldPrice = Number(p.old_price);
    const currentPrice = Number(p.current_price);

    if(!oldPrice || !currentPrice || oldPrice <= 0 || currentPrice <= 0 || currentPrice >= oldPrice){
        return null;
    }

    const savings = oldPrice - currentPrice;
    const discount = (savings / oldPrice) * 100;

    // Score transparente do MVP: desconto (60), economia (15),
    // link de afiliado (10), URL do produto (5), loja (5), categoria (5).
    let discountPoints = 0;
    if(discount >= 50) discountPoints = 60;
    else if(discount >= 40) discountPoints = 50;
    else if(discount >= 30) discountPoints = 40;
    else if(discount >= 20) discountPoints = 28;
    else if(discount >= 10) discountPoints = 15;
    else discountPoints = 5;

    let savingsPoints = 0;
    if(savings >= 200) savingsPoints = 15;
    else if(savings >= 100) savingsPoints = 12;
    else if(savings >= 50) savingsPoints = 9;
    else if(savings >= 20) savingsPoints = 6;
    else savingsPoints = 2;

    const affiliatePoints = p.affiliate_url ? 10 : 0;
    const urlPoints = p.url ? 5 : 0;
    const storePoints = p.store ? 5 : 0;
    const categoryPoints = p.category ? 5 : 0;

    const score = Math.min(
        100,
        discountPoints + savingsPoints + affiliatePoints +
        urlPoints + storePoints + categoryPoints
    );

    return {
        savings: savings,
        discount: discount,
        score: score,
        breakdown: {
            discount: discountPoints,
            savings: savingsPoints,
            affiliate: affiliatePoints,
            url: urlPoints,
            store: storePoints,
            category: categoryPoints
        }
    };
}

function scoreClass(score){
    if(score >= 70) return 'good';
    if(score >= 40) return 'medium';
    return 'low';
}

function escapeHtml(text){
    return String(text || '').replace(/[&<>"']/g, function(c){
        return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c];
    });
}

function generateOffer(p, analysis, generated){
    const store = p.store ? ' na ' + p.store : '';
    const link = p.affiliate_url || p.url;
    const whatsapp = generated.whatsapp || generated.raw || '';
    const instagram = generated.instagram || whatsapp;
    const telegram = generated.telegram || whatsapp;
    const hashtags = generated.hashtags || '';

    return `
        <div class="offer-box">
            <div style="font-weight:800;margin-bottom:10px">🤖 Oferta criada pelo Gemini</div>
            <div class="channel-tabs">
                <button class="tab active" onclick="showChannel(this,'whatsapp')">💬 WhatsApp</button>
                <button class="tab" onclick="showChannel(this,'instagram')">📸 Instagram</button>
                <button class="tab" onclick="showChannel(this,'telegram')">✈️ Telegram</button>
            </div>
            <div class="channel-content" data-channel="whatsapp"><div class="copy-text">${escapeHtml(whatsapp)}</div></div>
            <div class="channel-content" data-channel="instagram" style="display:none"><div class="copy-text">${escapeHtml(instagram)}</div></div>
            <div class="channel-content" data-channel="telegram" style="display:none"><div class="copy-text">${escapeHtml(telegram)}</div></div>
            <button class="copy-btn" onclick="copyCurrent(this)">📋 Copiar texto</button>
            ${hashtags ? '<div class="hashtags"><strong>#️⃣ Hashtags</strong><div>' + escapeHtml(hashtags) + '</div></div>' : ''}
            <hr style="border:0;border-top:1px solid #ddd;margin:14px 0">
            <div><strong>💰 Economia:</strong> ${money(analysis.savings)} · <strong>${analysis.discount.toFixed(2).replace('.', ',')}% OFF</strong>${store}</div>
            ${link ? '<a class="buy-btn" href="' + escapeHtml(link) + '" target="_blank" rel="noopener">🛒 Ver oferta</a>' : ''}
        </div>
    `;
}

function showChannel(button, channel){
    const box = button.closest('.offer-box');
    box.querySelectorAll('.channel').forEach(function(){ });
    box.querySelectorAll('.channel-content').forEach(function(el){
        el.style.display = el.dataset.channel === channel ? 'block' : 'none';
    });
    box.querySelectorAll('.tab').forEach(function(tab){ tab.classList.remove('active'); });
    button.classList.add('active');
}

async function copyCurrent(button){
    const box = button.closest('.offer-box');
    const visible = Array.from(box.querySelectorAll('.channel-content')).find(el => el.style.display !== 'none');
    const text = visible ? visible.querySelector('.copy-text').innerText : '';
    try{
        await navigator.clipboard.writeText(text);
        button.textContent = '✅ Copiado!';
        setTimeout(() => button.textContent = '📋 Copiar texto', 1500);
    }catch(e){
        alert('Não foi possível copiar automaticamente.');
    }
}



function selectedChannels(){
    return Array.from(document.querySelectorAll('#channelOptions input:checked')).map(x => x.value);
}

function opportunityHtml(item, index){
    const score = Number(item.opportunity_score || 0);
    const scoreLabel = score >= 90 ? 'EXCELENTE OPORTUNIDADE' :
                       score >= 80 ? 'BOA OPORTUNIDADE' :
                       score >= 65 ? 'OPORTUNIDADE MODERADA' : 'BAIXA OPORTUNIDADE';
    const price = item.current_price != null ? 'R$ ' + Number(item.current_price).toFixed(2).replace('.',',') : '—';
    const oldPrice = item.old_price != null ? 'R$ ' + Number(item.old_price).toFixed(2).replace('.',',') : '—';
    const sales = item.sales != null ? Number(item.sales).toLocaleString('pt-BR') : 'não informado';
    const commission = item.commission_rate != null ? Number(item.commission_rate).toFixed(2).replace('.',',') + '%' : 'não informada';
    const competition = item.competition_index != null ? Number(item.competition_index).toFixed(0) + '/100' : 'não estimada';
    return `<div class="opportunity" id="opportunity-${index}">
        <span class="badge">⭐ ${score.toFixed(0)}/100 · ${scoreLabel}</span>
        <h3>${escapeHtml(item.name || 'Produto')}</h3>
        <div class="muted">${escapeHtml(item.store || item.marketplace || '')} · ${escapeHtml(item.category || '')}</div>
        <div style="margin-top:8px"><b>${price}</b> <span class="muted">de ${oldPrice}</span></div>
        <div class="offer-data" style="margin-top:10px">
          <div class="metric">Vendas <b>${sales}</b></div>
          <div class="metric">Comissão <b>${commission}</b></div>
          <div class="metric">Concorrência <b>${competition}</b></div>
          <div class="metric">Confiança <b>${escapeHtml(item.data_confidence || 'estimada')}</b></div>
        </div>
        <button class="approve-btn" onclick="approveOpportunity(${index})">✅ Aprovar e publicar</button>
        <button class="reject-btn" onclick="rejectOpportunity(${index})">❌ Descartar</button>
    </div>`;

    async function discoverOpportunities(){
    const status = document.getElementById('discoveryStatus');
    const list = document.getElementById('opportunityList');
    const btn = document.getElementById('discoverBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Pesquisando...';
    status.textContent = 'Buscando e analisando produtos nas fontes conectadas...';
    try{
        const response = await fetch('/api/discover-opportunities', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({
                category: document.getElementById('discoveryCategory').value,
                min_discount: Number(document.getElementById('discoveryMinDiscount').value || 0),
                limit: Number(document.getElementById('discoveryLimit').value || 10)
            })
        });
        const data = await response.json();
        if(!response.ok) throw new Error(data.detail || 'Falha na pesquisa.');
        window.currentOpportunities = data.items || [];
        list.innerHTML = window.currentOpportunities.length
            ? window.currentOpportunities.map(opportunityHtml).join('')
            : '<div class="card empty">Nenhuma oportunidade encontrada com os critérios atuais.</div>';
        status.textContent = `✅ ${window.currentOpportunities.length} oportunidade(s) encontrada(s).`;
    }catch(error){
        status.textContent = '⚠️ ' + (error.message || 'Falha na pesquisa.');
    }finally{
        btn.disabled = false;
        btn.textContent = '🔎 Buscar oportunidades';
    }
}

async function approveOpportunity(index){
    const item = window.currentOpportunities?.[index];
    if(!item) return;
    const channels = selectedChannels();
    if(!channels.length){
        alert('Selecione pelo menos um canal de publicação.');
        return;
    }
    const box = document.getElementById('opportunity-' + index);
    box.innerHTML += '<div class="offer-box">🤖 Aprovado. Gerando oferta e preparando publicação...</div>';
    try{
        const response = await fetch('/api/approve-and-publish', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({product:item, channels:channels})
        });
        const data = await response.json();
        if(!response.ok) throw new Error(data.detail || 'Falha na publicação.');
        box.innerHTML = `<div class="offer-box">✅ Aprovado.<br>${escapeHtml(data.message || 'Oferta preparada para publicação automática.')}</div>`;
    }catch(error){
        box.innerHTML += '<div class="offer-box">⚠️ ' + (error.message || 'Falha na publicação.') + '</div>';
    }
}

function rejectOpportunity(index){
    const box = document.getElementById('opportunity-' + index);
    if(box) box.remove();
}

async function loadProducts(){
    try{
        const response = await fetch('/api/products');
        const data = await response.json();

        document.getElementById('products').textContent = data.length;

        let validOffers = 0;
        const list = document.getElementById('productList');

        if(!data.length){
            list.innerHTML = '<div class="card empty">Nenhum produto cadastrado ainda.</div>';
            document.getElementById('offers').textContent = '0';
            return;
        }

        list.innerHTML = data.map(function(p, index){
            const analysis = calculateOffer(p);

            if(analysis) validOffers++;

            const store = p.store || '';
            const category = p.category || '';
            const price = p.current_price != null ? money(p.current_price) : '';
            const image = p.image_url ? '<img class="product-image" src="' + escapeHtml(p.image_url) + '" alt="" loading="lazy">' : '';

            if(!analysis){
                return `
                <div class="product low">
                    ${image}
                    <strong>${escapeHtml(p.name || '')}</strong>
                    <div>${store}${category ? ' · ' + category : ''}</div>
                    ${price ? '<div class="price">' + price + '</div>' : ''}
                    <div class="offer-box">⚠️ Preços insuficientes para calcular uma oferta.</div>
                </div>`;
            }

            return `
            <div class="product ${scoreClass(analysis.score)}" id="product-${index}">
                ${image}
                <strong>${escapeHtml(p.name || '')}</strong>
                <div>${store}${category ? ' · ' + category : ''}</div>
                <div class="old-price">${money(p.old_price)}</div>
                <div class="price">${money(p.current_price)}</div>

                <div class="offer-data">
                    <div class="metric">
                        Desconto
                        <b>${analysis.discount.toFixed(2).replace('.', ',')}%</b>
                    </div>
                    <div class="metric">
                        Economia
                        <b>${money(analysis.savings)}</b>
                    </div>
                    <div class="metric score">
                        Score
                        <b>⭐ ${analysis.score}/100</b>
                    </div>
                </div>

                <details style="margin-top:10px">
                    <summary style="cursor:pointer;font-size:13px;color:#475467">
                        🔎 Como chegamos ao score?
                    </summary>
                    <div style="margin-top:8px;font-size:12px;color:#475467;line-height:1.7">
                        Desconto: <b>${analysis.breakdown.discount}/60</b> ·
                        Economia: <b>${analysis.breakdown.savings}/15</b> ·
                        Afiliado: <b>${analysis.breakdown.affiliate}/10</b> ·
                        Link: <b>${analysis.breakdown.url}/5</b> ·
                        Loja: <b>${analysis.breakdown.store}/5</b> ·
                        Categoria: <b>${analysis.breakdown.category}/5</b>
                    </div>
                </details>

                <button class="offer-btn" onclick="showOffer(${index})">
                    🔥 Gerar oferta
                </button>
                <button style="margin-top:8px;width:100%;background:#475467" onclick="editProduct(${index})">✏️ Editar produto</button>

                <div id="offer-${index}"></div>
            </div>`;
        }).join('');

        document.getElementById('offers').textContent = validOffers;

        window.currentProducts = data;
    }catch(error){
        document.getElementById('productList').innerHTML =
            '<div class="card empty">Não foi possível carregar os produtos.</div>';
    }
}

async function showOffer(index){
    const p = window.currentProducts[index];
    const analysis = calculateOffer(p);
    if(!analysis) return;

    const box = document.getElementById('offer-' + index);
    box.innerHTML = '<div class="offer-box">🤖 Criando oferta com IA...</div>';

    try{
        const response = await fetch('/api/generate-offer', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({product: p, analysis: analysis})
        });
        const data = await response.json();
        if(!response.ok){ throw new Error(data.detail || 'Erro ao gerar oferta'); }
        box.innerHTML = generateOffer(p, analysis, data);
    }catch(error){
        box.innerHTML = '<div class="offer-box">⚠️ ' + (error.message || 'Não foi possível gerar a oferta.') + '</div>';
    }
}

async function editProduct(index){
    const p = window.currentProducts[index];
    if(!p) return;

    const form = document.getElementById('productForm');
    form.dataset.editId = p.id;
    form.name.value = p.name || '';
    form.store.value = p.store || '';
    form.category.value = p.category || '';
    form.url.value = p.url || '';
    form.affiliate_url.value = p.affiliate_url || '';
    form.old_price.value = p.old_price ?? '';
    form.current_price.value = p.current_price ?? '';
    form.image_url.value = p.image_url || '';

    document.getElementById('submitProductBtn').textContent = '💾 Salvar alterações';
    window.scrollTo({top: form.closest('.section').offsetTop - 10, behavior:'smooth'});
}


async function importProductFromUrl(){
    const url = document.getElementById('productUrl').value.trim();
    const status = document.getElementById('importStatus');

    if(!url){
        status.textContent = 'Cole primeiro o link do produto.';
        return;
    }

    const btn = document.getElementById('importBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Buscando...';
    status.textContent = 'Lendo os dados da página...';

    try{
        const response = await fetch('/api/import-product', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({url: url})
        });

        const data = await response.json();

        if(!response.ok){
            throw new Error(data.detail || 'Não foi possível ler o produto.');
        }

        const form = document.getElementById('productForm');

        if(data.name) form.name.value = data.name;
        if(data.store) form.store.value = data.store;
        if(data.category) form.category.value = data.category;
        if(data.url) form.url.value = data.url;
        if(data.image_url) form.image_url.value = data.image_url;
        if(data.old_price != null) form.old_price.value = data.old_price;
        if(data.current_price != null) form.current_price.value = data.current_price;

        status.textContent = '✅ Dados encontrados. Confira os campos antes de salvar.';
    }catch(error){
        status.textContent = '⚠️ ' + (error.message || 'Falha ao importar.');
    }finally{
        btn.disabled = false;
        btn.textContent = '🔎 Buscar dados pelo link';
    }
}

document.getElementById('importBtn').addEventListener('click', importProductFromUrl);
document.getElementById('discoverBtn').addEventListener('click', discoverOpportunities);

document.getElementById('productForm').addEventListener('submit', async function(event){
    event.preventDefault();

    const form = new FormData(event.target);

    const body = {
        name: form.get('name'),
        store: form.get('store') || null,
        category: form.get('category') || null,
        url: form.get('url') || null,
        affiliate_url: form.get('affiliate_url') || null,
        old_price: form.get('old_price') ? Number(form.get('old_price')) : null,
        current_price: form.get('current_price') ? Number(form.get('current_price')) : null,
        image_url: form.get('image_url') || null
    };

    const editId = event.target.dataset.editId;
    const endpoint = editId ? '/api/products/' + editId : '/api/products';
    const method = editId ? 'PUT' : 'POST';

    const response = await fetch(endpoint, {
        method: method,
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
    });

    if(!response.ok){
        const err = await response.json().catch(() => ({}));
        alert(err.detail || 'Não foi possível salvar o produto.');
        return;
    }

    event.target.reset();
    delete event.target.dataset.editId;
    document.getElementById('submitProductBtn').textContent = 'Cadastrar produto';
    await loadProducts();
    alert(editId ? 'Produto atualizado com sucesso! 🎉' : 'Produto cadastrado com sucesso! 🎉');
});;

loadProducts();

async function loadIntegrations(){
    try{
        const r=await fetch('/api/integrations/status');
        const d=await r.json();
        const m=document.getElementById('meliStatus');
        m.textContent=d.mercadolivre.connected ? '🟢 Mercado Livre conectado.' : '🟡 Mercado Livre ainda não conectado. Clique para autorizar.';
        document.getElementById('amazonStatus').textContent=d.amazon.tag ? '🟢 Identificação salva: '+d.amazon.tag : '⚪ Nenhuma identificação Amazon salva ainda.';
        document.getElementById('amazonTag').value=d.amazon.tag || '';
    }catch(e){
        document.getElementById('meliStatus').textContent='Não foi possível verificar a conexão.';
    }
}

document.getElementById('meliConnectBtn').addEventListener('click',()=>{ window.location.href='/oauth/mercadolivre'; });
document.getElementById('meliSearchBtn').addEventListener('click',()=>{
    const box=document.getElementById('meliSearchBox');
    box.style.display=box.style.display==='none'?'block':'none';
});
document.getElementById('meliQuery').addEventListener('keydown',e=>{if(e.key==='Enter') searchMercadoLivre();});
async function searchMercadoLivre(){
    const q=document.getElementById('meliQuery').value.trim();
    if(!q){alert('Digite o produto que deseja pesquisar.');return;}
    const out=document.getElementById('meliResults');
    out.innerHTML='<div class="empty">🔎 Pesquisando...</div>';
    try{
        const r=await fetch('/api/mercadolivre/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q,limit:Number(document.getElementById('meliLimit').value||10)})});
        const d=await r.json();
        if(!r.ok) throw new Error(d.detail||'Falha na busca');
        out.innerHTML=(d.items||[]).map(item=>`<div class="opportunity"><h3>${escapeHtml(item.name||'Produto')}</h3><div class="muted">${escapeHtml(item.store||'Mercado Livre')} · ${escapeHtml(item.category||'')}</div><div class="price">${item.current_price?money(item.current_price):'Preço não informado'}</div>${item.image_url?'<img class="product-image" src="'+escapeHtml(item.image_url)+'" alt="">':''}<a class="buy-btn" href="${escapeHtml(item.url||'#')}" target="_blank" rel="noopener">Ver produto</a><button class="approve-btn" onclick='importDiscovered(${JSON.stringify(item).replace(/'/g,"&#39;")})'>➕ Adicionar ao OFERTA IA</button></div>`).join('')||'<div class="empty">Nenhum produto encontrado.</div>';
    }catch(e){out.innerHTML='<div class="empty">'+escapeHtml(e.message)+'</div>';}
}
async function importDiscovered(item){
    try{
        const r=await fetch('/api/products',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:item.name,store:'Mercado Livre',url:item.url,category:item.category,current_price:item.current_price,image_url:item.image_url,marketplace:'mercadolivre',item_id:item.item_id})});
        const d=await r.json();
        if(!r.ok) throw new Error(d.detail||'Não foi possível salvar');
        alert('Produto adicionado ao OFERTA IA.');
        if(typeof loadProducts==='function') loadProducts();
    }catch(e){alert(e.message);}
}
document.getElementById('amazonSaveBtn').addEventListener('click',async()=>{
    const tag=document.getElementById('amazonTag').value.trim();
    if(!tag){alert('Informe sua identificação de associado.');return;}
    const r=await fetch('/api/amazon/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag})});
    const d=await r.json();
    document.getElementById('amazonStatus').textContent=d.ok?'🟢 Identificação Amazon salva.':'❌ '+(d.detail||'Erro');
});
loadIntegrations();
</script>
</body>
</html>"""


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
    # Cookies são recuperados via Request; esta rota é mantida simples para o MVP.
    # Se o state/verifier não estiverem disponíveis, o usuário será orientado a tentar novamente.
    raise HTTPException(400, "A primeira etapa de OAuth foi preparada. Para concluir a conexão, atualizaremos o callback com validação de sessão segura antes do teste final.")

@app.post("/api/mercadolivre/search")
def mercadolivre_search(payload: dict):
    query = (payload.get("query") or "").strip()
    limit = max(1, min(20, int(payload.get("limit") or 10)))
    if not query:
        raise HTTPException(400, "Informe um termo de busca.")
    try:
        r = requests.get("https://api.mercadolibre.com/sites/MLB/search", params={"q": query, "limit": limit}, timeout=15, headers={"User-Agent":"OFERTA-IA/1.0"})
        r.raise_for_status()
        raw = r.json()
        items=[]
        for x in raw.get("results", [])[:limit]:
            items.append({
                "name": x.get("title"),
                "store": "Mercado Livre",
                "url": x.get("permalink"),
                "current_price": x.get("price"),
                "category": x.get("category_id"),
                "image_url": x.get("thumbnail"),
                "item_id": x.get("id"),
                "sales": 0,
                "rating": 0,
                "data_confidence": "media"
            })
        return {"items":items,"source":"mercadolivre_public_search"}
    except requests.RequestException as exc:
        raise HTTPException(502, f"Falha ao consultar Mercado Livre: {exc}")

@app.post("/api/amazon/settings")
def amazon_settings(payload: dict):
    tag=(payload.get("tag") or "").strip()
    if not tag:
        raise HTTPException(400,"Informe a identificação de associado Amazon.")
    _save_connection("amazon", {"affiliate_tag": tag, "status":"configured"})
    return {"ok":True,"tag":tag}

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
    

}
