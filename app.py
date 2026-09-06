import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
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
button.offer-btn{margin-top:12px;width:100%;background:#e85d04}
.form{display:grid;gap:10px}
input{width:100%;padding:13px;border:1px solid #d7dce5;border-radius:12px;font-size:15px}
.products{display:grid;gap:10px}
.product{background:white;border-radius:16px;padding:17px;box-shadow:0 3px 14px #00000009}
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
@media(min-width:700px){.grid{grid-template-columns:repeat(4,1fr)}}
@media(max-width:480px){.offer-data{grid-template-columns:1fr 1fr 1fr}.metric{font-size:12px}.metric b{font-size:15px}}
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
<input name="url" placeholder="Link do produto">
<input name="affiliate_url" placeholder="Link de afiliado">
<input name="old_price" type="number" step="0.01" placeholder="Preço antigo">
<input name="current_price" type="number" step="0.01" placeholder="Preço atual">
<button type="submit">Cadastrar produto</button>
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

    let score = 0;
    if(discount >= 50) score += 70;
    else if(discount >= 40) score += 60;
    else if(discount >= 30) score += 50;
    else if(discount >= 20) score += 35;
    else if(discount >= 10) score += 20;
    else score += 5;

    if(p.affiliate_url) score += 15;
    if(p.url) score += 5;
    if(p.store) score += 5;
    if(p.category) score += 5;

    score = Math.min(100, score);

    return {
        savings: savings,
        discount: discount,
        score: score
    };
}

function scoreClass(score){
    if(score >= 70) return 'good';
    if(score >= 40) return 'medium';
    return 'low';
}

function generateOffer(p, analysis){
    const store = p.store ? ' na ' + p.store : '';
    return `
        <div class="offer-box">
            <strong>🔥 ${p.name}</strong><br>
            De <s>${money(p.old_price)}</s><br>
            <strong>Por ${money(p.current_price)}</strong><br>
            <strong>${analysis.discount.toFixed(2).replace('.', ',')}% OFF</strong>
            ${store}.<br><br>
            💰 Você economiza ${money(analysis.savings)}.
        </div>
    `;
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

            if(!analysis){
                return `
                <div class="product low">
                    <strong>${p.name || ''}</strong>
                    <div>${store}${category ? ' · ' + category : ''}</div>
                    ${price ? '<div class="price">' + price + '</div>' : ''}
                    <div class="offer-box">⚠️ Preços insuficientes para calcular uma oferta.</div>
                </div>`;
            }

            return `
            <div class="product ${scoreClass(analysis.score)}" id="product-${index}">
                <strong>${p.name || ''}</strong>
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

                <button class="offer-btn" onclick="showOffer(${index})">
                    🔥 Gerar oferta
                </button>

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

function showOffer(index){
    const p = window.currentProducts[index];
    const analysis = calculateOffer(p);

    if(!analysis) return;

    document.getElementById('offer-' + index).innerHTML =
        generateOffer(p, analysis);
}

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
        current_price: form.get('current_price') ? Number(form.get('current_price')) : null
    };

    const response = await fetch('/api/products', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
    });

    if(!response.ok){
        alert('Não foi possível cadastrar o produto.');
        return;
    }

    event.target.reset();
    await loadProducts();
    alert('Produto cadastrado com sucesso! 🎉');
});

loadProducts();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "OFERTA IA"}


@app.get("/api/products")
def products():
    return (
        supabase.table("products")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
    )


@app.post("/api/products")
def create_product(product: Product):
    result = supabase.table("products").insert(product.model_dump()).execute()
    if not result.data:
        raise HTTPException(400, "Não foi possível cadastrar o produto.")
    return result.data[0]
