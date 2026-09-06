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
<h2>🛒 Mercado Livre</h2>
<div class="card">
<div id="meliStatus" class="muted">Verificando conexão...</div>
<button type="button" id="meliConnectBtn" style="margin-top:10px;background:#2563eb">🔐 Conectar Mercado Livre</button>
<button type="button" id="meliDiagnosticBtn" style="margin-top:10px;background:#475467">🩺 Diagnosticar Mercado Livre</button>
<button type="button" id="meliSearchBtn" style="margin-top:10px">🔎 Pesquisar produtos</button>
<div id="meliDiagnostic" class="muted" style="margin-top:12px;line-height:1.55"></div>
<div id="meliSearchBox" style="display:none;margin-top:12px">
<input id="meliQuery" placeholder="Ex.: celular, air fryer, fone bluetooth">
<input id="meliLimit" type="number" min="1" max="20" value="10" placeholder="Quantidade">
<button type="button" id="meliSearchAction" style="margin-top:8px;background:#12b76a">🔎 Buscar produtos no catálogo</button>
<div id="meliCatalogHint" class="muted" style="margin-top:8px">Teste oficial do catálogo de produtos, usando sua autorização do Mercado Livre.</div>
<div id="meliResults" style="margin-top:12px"></div>
</div>
</div>
</div>

<div class="section">
<h2>🎯 Descoberta inteligente de oportunidades</h2>
<div class="card">
<p class="muted">O sistema analisa os produtos disponíveis e prioriza oportunidades pelo potencial de oferta.</p>
<input id="discoveryCategory" placeholder="Categoria (opcional)">
<input id="discoveryMinDiscount" type="number" min="0" max="100" value="10" placeholder="Desconto mínimo (%)">
<input id="discoveryLimit" type="number" min="1" max="50" value="10" placeholder="Quantidade de oportunidades">
<button type="button" id="discoverBtn" style="margin-top:8px;background:#e85d04">🔎 Buscar oportunidades</button>
<div id="discoveryStatus" class="muted" style="margin-top:10px"></div>
<div id="opportunityList" style="margin-top:12px"></div>
</div>
</div>

<div class="section">
<h2>📢 Canais de publicação</h2>
<div class="card">
<div id="channelOptions" class="channel-grid">
<label><input type="checkbox" value="whatsapp" checked> 💬 WhatsApp</label>
<label><input type="checkbox" value="instagram"> 📸 Instagram</label>
<label><input type="checkbox" value="telegram"> ✈️ Telegram</label>
</div>
</div>
</div>

<div class="section">
<h2>🛍️ Amazon</h2>
<div class="card">
<div id="amazonStatus" class="muted">Nenhuma identificação Amazon salva ainda.</div>
<input id="amazonTag" placeholder="Sua identificação de associado Amazon">
<button type="button" id="amazonSaveBtn" style="margin-top:8px;background:#2563eb">💾 Salvar identificação Amazon</button>
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
}

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

/* Inicialização segura da interface.
   Todos os eventos são registrados somente depois que o HTML estiver pronto.
   Um elemento ausente ou uma falha de uma API não pode mais desativar os demais botões. */
function bindClick(id, handler){
    const el = document.getElementById(id);
    if(el) el.addEventListener('click', handler);
    return el;
}

function setText(id, text){
    const el = document.getElementById(id);
    if(el) el.textContent = text;
}

async function loadIntegrations(){
    const status = document.getElementById('meliStatus');
    if(status) status.textContent = '🔄 Verificando conexão...';

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);

    try{
        const r = await fetch('/api/integrations/status', {
            method: 'GET',
            cache: 'no-store',
            signal: controller.signal
        });
        if(!r.ok) throw new Error('HTTP ' + r.status);
        const d = await r.json();

        const meliConnected = !!(d.mercadolivre && d.mercadolivre.connected);
        const amazonTag = (d.amazon && d.amazon.tag) || '';

        setText(
            'meliStatus',
            meliConnected
                ? '🟢 Mercado Livre conectado.'
                : '🟡 Mercado Livre ainda não conectado. Clique para autorizar.'
        );

        setText(
            'amazonStatus',
            amazonTag
                ? '🟢 Identificação salva: ' + amazonTag
                : '⚪ Nenhuma identificação Amazon salva ainda.'
        );

        const amazonInput = document.getElementById('amazonTag');
        if(amazonInput) amazonInput.value = amazonTag;
    }catch(e){
        setText(
            'meliStatus',
            e && e.name === 'AbortError'
                ? '⚠️ Verificação demorou demais. Os botões continuam disponíveis.'
                : '⚠️ Não foi possível verificar agora. Os botões continuam disponíveis.'
        );
    }finally{
        clearTimeout(timer);
    }
}

async function diagnoseMercadoLivre(){
    const out = document.getElementById('meliDiagnostic');
    const btn = document.getElementById('meliDiagnosticBtn');
    if(!out) return;

    if(btn){
        btn.disabled = true;
        btn.textContent = '🩺 Diagnosticando...';
    }
    out.innerHTML = '🔄 Consultando o token salvo e a API do Mercado Livre...';

    try{
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 15000);
        let r;
        try{
            r = await fetch('/api/mercadolivre/diagnostico', {
                method:'GET',
                cache:'no-store',
                signal:controller.signal
            });
        }finally{
            clearTimeout(timer);
        }

        const d = await r.json().catch(() => ({}));
        if(!r.ok){
            throw new Error(d.detail || 'Falha no diagnóstico.');
        }

        const esc = window.escapeHtml || function(v){
            return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
        };

        const rows = d.tests || [];
        out.innerHTML = '<div style="margin-bottom:8px"><strong>Resultado do diagnóstico</strong></div>' +
            rows.map(t => {
                const icon = t.ok ? '✅' : '❌';
                return '<div style="margin-top:6px">' + icon + ' <strong>' + esc(t.name) + '</strong>: HTTP ' + esc(t.http_status ?? '—') + '<br><span class="muted">' + esc(t.message || '') + '</span></div>';
            }).join('') +
            (d.summary ? '<div style="margin-top:10px"><strong>Resumo:</strong> ' + esc(d.summary) + '</div>' : '') +
            (d.app ? '<div style="margin-top:10px"><strong>Aplicação:</strong> ' + esc(d.app.certification_status || '—') + ' · ativa=' + esc(d.app.active) + ' · sandbox=' + esc(d.app.sandbox_mode) + '</div>' : '');
    }catch(e){
        out.innerHTML = '⚠️ ' + (e && e.name === 'AbortError' ? 'O diagnóstico demorou demais.' : (e.message || 'Falha no diagnóstico.'));
    }finally{
        if(btn){
            btn.disabled = false;
            btn.textContent = '🩺 Diagnosticar Mercado Livre';
        }
    }
}

async function searchMercadoLivre(){
    const queryEl = document.getElementById('meliQuery');
    const limitEl = document.getElementById('meliLimit');
    const out = document.getElementById('meliResults');

    if(!queryEl || !out) return;

    const q = queryEl.value.trim();
    if(!q){
        alert('Digite o produto que deseja pesquisar.');
        queryEl.focus();
        return;
    }

    out.innerHTML = '<div class="empty">🔎 Pesquisando...</div>';

    try{
        const limit = Math.max(1, Math.min(20, Number(limitEl?.value || 10)));

        const r = await fetch('/api/mercadolivre/search', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({query:q, limit:limit})
        });

        const d = await r.json().catch(() => ({}));
        if(!r.ok) throw new Error(d.detail || 'Falha na busca.');

        out.innerHTML = (d.items || []).map(item => `
            <div class="opportunity">
                <h3>${escapeHtml(item.name || 'Produto')}</h3>
                <div class="muted">${escapeHtml(item.store || 'Mercado Livre')} · ${escapeHtml(item.category || '')}</div>
                <div class="price">${item.current_price != null ? money(item.current_price) : 'Preço não informado'}</div>
                ${item.image_url ? '<img class="product-image" src="' + escapeHtml(item.image_url) + '" alt="">' : ''}
                <a class="buy-btn" href="${escapeHtml(item.url || '#')}" target="_blank" rel="noopener">Ver produto</a>
                <button class="approve-btn add-discovered-btn" type="button">➕ Adicionar ao OFERTA IA</button>
            </div>
        `).join('') || '<div class="empty">Nenhum produto encontrado.</div>';

        // Evita onclick inline com JSON e funciona melhor em navegadores móveis.
        Array.from(out.querySelectorAll('.add-discovered-btn')).forEach((btn, index) => {
            btn.addEventListener('click', () => importDiscovered((d.items || [])[index]));
        });
    }catch(e){
        out.innerHTML = '<div class="empty">⚠️ ' + escapeHtml(e.message || 'Falha na busca.') + '</div>';
    }
}

async function importDiscovered(item){
    if(!item) return;

    try{
        const r = await fetch('/api/products',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({
                name:item.name,
                store:'Mercado Livre',
                url:item.url,
                category:item.category,
                current_price:item.current_price,
                image_url:item.image_url,
                marketplace:'mercadolivre',
                item_id:item.item_id
            })
        });

        const d = await r.json().catch(() => ({}));
        if(!r.ok) throw new Error(d.detail || 'Não foi possível salvar.');

        alert('Produto adicionado ao OFERTA IA.');
        if(typeof loadProducts === 'function') await loadProducts();
    }catch(e){
        alert(e.message || 'Não foi possível adicionar o produto.');
    }
}

document.addEventListener('DOMContentLoaded', function(){
    // Um erro em uma integração não impede o restante da interface.
    try{
        bindClick('importBtn', importProductFromUrl);
        bindClick('discoverBtn', discoverOpportunities);

        const productForm = document.getElementById('productForm');
        if(productForm){
            productForm.addEventListener('submit', async function(event){
                event.preventDefault();

                try{
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
                        throw new Error(err.detail || 'Não foi possível salvar o produto.');
                    }

                    event.target.reset();
                    delete event.target.dataset.editId;

                    const submitBtn = document.getElementById('submitProductBtn');
                    if(submitBtn) submitBtn.textContent = 'Cadastrar produto';

                    await loadProducts();
                    alert(editId ? 'Produto atualizado com sucesso! 🎉' : 'Produto cadastrado com sucesso! 🎉');
                }catch(error){
                    alert(error.message || 'Não foi possível salvar o produto.');
                }
            });
        }

        bindClick('meliConnectBtn', function(){
            window.location.href = '/oauth/mercadolivre';
        });

        bindClick('meliDiagnosticBtn', diagnoseMercadoLivre);

        bindClick('meliSearchBtn', function(){
            const box = document.getElementById('meliSearchBox');
            if(!box) return;
            box.style.display = box.style.display === 'none' ? 'block' : 'none';

            if(box.style.display === 'block'){
                const input = document.getElementById('meliQuery');
                if(input) input.focus();
            }
        });

        bindClick('meliSearchAction', searchMercadoLivre);

        const meliQuery = document.getElementById('meliQuery');
        if(meliQuery){
            meliQuery.addEventListener('keydown', function(e){
                if(e.key === 'Enter'){
                    e.preventDefault();
                    searchMercadoLivre();
                }
            });
        }

        bindClick('amazonSaveBtn', async function(){
            try{
                const input = document.getElementById('amazonTag');
                const tag = input ? input.value.trim() : '';
                if(!tag){
                    alert('Informe sua identificação de associado.');
                    if(input) input.focus();
                    return;
                }

                const r = await fetch('/api/amazon/settings',{
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({tag})
                });

                const d = await r.json().catch(() => ({}));
                if(!r.ok) throw new Error(d.detail || 'Erro ao salvar.');

                setText(
                    'amazonStatus',
                    d.ok ? '🟢 Identificação Amazon salva.' : '❌ ' + (d.detail || 'Erro')
                );
            }catch(e){
                setText('amazonStatus', '❌ ' + (e.message || 'Erro ao salvar identificação.'));
            }
        });

        // Carregamentos iniciais independentes.
        if(typeof loadProducts === 'function') loadProducts();
        loadIntegrations();

    }catch(error){
        // Último mecanismo de segurança: a página continua utilizável.
        setText('meliStatus', '⚠️ Interface carregada. Algumas funções precisam ser recarregadas.');
        console.error('OFERTA IA inicialização:', error);
    }
});
window.addEventListener('error', function(event){
    try{
        const status = document.getElementById('meliStatus');
        if(status && event && event.message){
            status.textContent = '⚠️ Interface: ' + event.message;
        }
    }catch(_){}
});
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

@app.post("/api/mercadolivre/search")
def mercadolivre_search(payload: dict):
    """Busca somente oportunidades de catálogo que tenham anúncio comprável agora.

    Fluxo:
    1) /products/search com status=active
    2) /products/{product_id} para obter buy_box_winner
    3) /items/{item_id} para validar o anúncio real
    4) descarta catálogo sem anúncio, anúncio inativo ou sem estoque/preço
    """
    query = (payload.get("query") or "").strip()
    try:
        limit = max(1, min(20, int(payload.get("limit") or 10)))
    except (TypeError, ValueError):
        limit = 10

    if not query:
        raise HTTPException(400, "Informe um termo de busca.")

    connection = _get_connection("mercadolivre")
    access_token = (connection or {}).get("access_token")
    if not access_token:
        raise HTTPException(401, "Mercado Livre não está conectado. Clique em Conectar Mercado Livre.")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "OFERTA-IA/1.0",
        "Accept": "application/json",
    }

    def get_json(url, params=None, timeout=15, allow_404=False):
        r = requests.get(url, params=params, timeout=timeout, headers=headers)
        if r.status_code in (401, 403):
            detail = r.text[:500]
            raise HTTPException(502, f"Mercado Livre recusou uma consulta ({r.status_code}). Detalhe: {detail}")
        if r.status_code == 404 and allow_404:
            return None
        r.raise_for_status()
        return r.json()

    def number(value):
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def discount_percent(current, old):
        current = number(current)
        old = number(old)
        if current is not None and old is not None and old > current > 0:
            return round(((old - current) / old) * 100, 2)
        return None

    try:
        # O catálogo agora é filtrado como ativo desde a origem.
        search = get_json(
            "https://api.mercadolibre.com/products/search",
            params={
                "status": "active",
                "site_id": "MLB",
                "q": query,
                "limit": min(50, max(limit * 3, limit)),
            },
            timeout=20,
        )

        items = []
        discarded = {
            "no_product_id": 0,
            "inactive_catalog": 0,
            "no_buy_box": 0,
            "no_item_id": 0,
            "item_unavailable": 0,
            "no_price": 0,
            "errors": 0,
        }

        # Buscamos mais candidatos que o limite final porque vários produtos
        # de catálogo podem não ter anúncio comprável atualmente.
        raw_results = (search.get("results") or [])[: max(limit * 3, limit)]

        for x in raw_results:
            if len(items) >= limit:
                break

            product_id = x.get("id") or x.get("catalog_product_id")
            if not product_id:
                discarded["no_product_id"] += 1
                continue

            try:
                # Detalhe do catálogo: é aqui que o ML informa buy_box_winner.
                detail = get_json(
                    f"https://api.mercadolibre.com/products/{product_id}",
                    timeout=15,
                    allow_404=True,
                ) or {}
            except requests.RequestException:
                discarded["errors"] += 1
                continue

            catalog_status = str(detail.get("status") or x.get("status") or "").lower()
            if catalog_status != "active":
                discarded["inactive_catalog"] += 1
                continue

            winner = detail.get("buy_box_winner") or {}
            if not winner:
                discarded["no_buy_box"] += 1
                continue

            item_id = winner.get("item_id")
            if not item_id:
                discarded["no_item_id"] += 1
                continue

            # Agora validamos o anúncio real. Isso elimina anúncios antigos,
            # pausados, encerrados ou sem estoque.
            try:
                item_detail = get_json(
                    f"https://api.mercadolibre.com/items/{item_id}",
                    timeout=15,
                    allow_404=True,
                ) or {}
            except requests.RequestException:
                discarded["errors"] += 1
                continue

            item_status = str(item_detail.get("status") or "").lower()
            available_quantity = number(
                item_detail.get("available_quantity")
                if item_detail.get("available_quantity") is not None
                else winner.get("available_quantity")
            )

            # Para uma oferta real precisamos de uma publicação ativa.
            if item_status and item_status != "active":
                discarded["item_unavailable"] += 1
                continue

            # Se o ML informou explicitamente quantidade zero, não mostramos.
            if available_quantity is not None and available_quantity <= 0:
                discarded["item_unavailable"] += 1
                continue

            current_price = number(item_detail.get("price"))
            if current_price is None:
                current_price = number(winner.get("price"))

            original_price = number(item_detail.get("original_price"))
            if original_price is None:
                original_price = number(winner.get("original_price"))

            # Último fallback: preços do anúncio.
            if current_price is None:
                try:
                    prices = get_json(
                        f"https://api.mercadolibre.com/items/{item_id}/prices",
                        timeout=15,
                    ) or {}
                    price_rows = prices.get("prices") or []
                    eligible = [
                        pr for pr in price_rows
                        if pr.get("conditions", {}).get("context_restrictions", [])
                        in ([], ["channel_marketplace"])
                    ]
                    candidates = eligible or price_rows
                    if candidates:
                        promo = next((pr for pr in candidates if pr.get("type") == "promotion"), None)
                        chosen = promo or next(
                            (pr for pr in candidates if pr.get("type") == "standard"),
                            candidates[0],
                        )
                        current_price = number(chosen.get("amount"))
                        if original_price is None:
                            original_price = number(chosen.get("regular_amount"))
                except requests.RequestException:
                    pass

            if current_price is None or current_price <= 0:
                discarded["no_price"] += 1
                continue

            seller_id = item_detail.get("seller_id") or winner.get("seller_id")
            seller_reputation = (item_detail.get("seller") or {}).get("reputation_level_id")
            shipping = item_detail.get("shipping") or winner.get("shipping") or {}

            pictures = detail.get("pictures") or x.get("pictures") or []
            image_url = None
            if pictures and isinstance(pictures[0], dict):
                image_url = pictures[0].get("secure_url") or pictures[0].get("url")
            if not image_url:
                image_url = item_detail.get("thumbnail") or item_detail.get("secure_thumbnail")
            if not image_url:
                image_url = x.get("thumbnail") or x.get("picture")

            url = (
                item_detail.get("permalink")
                or winner.get("permalink")
                or detail.get("permalink")
                or x.get("permalink")
                or f"https://www.mercadolivre.com.br/p/{product_id}"
            )

            discount_rate = discount_percent(current_price, original_price)
            sold_quantity = number(item_detail.get("sold_quantity"))

            items.append({
                "name": item_detail.get("title") or detail.get("name") or x.get("name") or "Produto Mercado Livre",
                "product_id": product_id,
                "catalog_product_id": product_id,
                "status": item_status or catalog_status,
                "catalog_status": catalog_status,
                "domain_id": detail.get("domain_id") or x.get("domain_id"),
                "url": url,
                "image_url": image_url,
                "current_price": current_price,
                "old_price": original_price,
                "discount_rate": discount_rate,
                "item_id": item_id,
                "seller_id": seller_id,
                "seller_reputation": seller_reputation,
                "shipping": shipping,
                "buy_box_winner": True,
                "available_quantity": available_quantity,
                "sold_quantity": sold_quantity,
                "condition": item_detail.get("item_condition") or item_detail.get("condition") or winner.get("condition"),
                "data_confidence": "alta",
            })

        return {
            "query": query,
            "source": "mercadolivre_catalog_active_buybox",
            "total_catalog_candidates": (search.get("paging") or {}).get("total", len(raw_results)),
            "returned": len(items),
            "discarded": discarded,
            "items": items,
            "message": (
                "Foram exibidos somente anúncios ativos, com publicação real e preço informado."
                if items else
                "Nenhum anúncio comprável foi encontrado entre os produtos retornados."
            ),
        }

    except HTTPException:
        raise
    except requests.RequestException as exc:
        raise HTTPException(502, f"Falha de comunicação com o Mercado Livre: {exc}")
    except ValueError:
        raise HTTPException(502, "O Mercado Livre retornou uma resposta inválida.")

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
