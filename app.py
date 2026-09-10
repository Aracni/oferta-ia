import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Configure SUPABASE_URL e SUPABASE_SECRET_KEY (ou SUPABASE_SERVICE_ROLE_KEY).")
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

HTML = '''<!doctype html><html lang="pt-BR"><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>OFERTA IA</title><style>
*{box-sizing:border-box}body{margin:0;background:#f5f7fb;color:#172033;font-family:Arial,sans-serif}header{background:#111827;color:white;padding:18px 20px;position:sticky;top:0;z-index:5}.brand{font-size:22px;font-weight:800}.sub{font-size:12px;opacity:.7;margin-top:4px}main{max-width:900px;margin:auto;padding:20px}.hero{background:white;border-radius:20px;padding:22px;box-shadow:0 4px 18px #0000000b;margin-bottom:18px}.hero h1{margin:0 0 8px;font-size:25px}.hero p{margin:0;color:#667085}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.card{background:white;border-radius:18px;padding:18px;box-shadow:0 4px 18px #0000000b}.number{font-size:30px;font-weight:800;margin-top:7px}.label{font-size:13px;color:#667085}.section{margin-top:22px}.section h2{font-size:19px;margin:0 0 12px}button{border:0;border-radius:12px;padding:13px 16px;background:#111827;color:white;font-weight:700;cursor:pointer}.form{display:grid;gap:10px}input{width:100%;padding:13px;border:1px solid #d7dce5;border-radius:12px;font-size:15px}.products{display:grid;gap:10px}.product{background:white;border-radius:16px;padding:15px;box-shadow:0 3px 14px #00000009}.product strong{display:block;margin-bottom:5px}.price{font-weight:800}.empty{color:#667085;text-align:center;padding:20px}nav{display:flex;gap:8px;overflow:auto;margin:18px 0}nav span{background:white;border-radius:999px;padding:9px 13px;font-size:13px;white-space:nowrap}@media(min-width:700px){.grid{grid-template-columns:repeat(4,1fr)}}
</style></head><body><header><div class="brand">🚀 OFERTA IA</div><div class="sub">Central inteligente de ofertas</div></header><main><div class="hero"><h1>Olá! 👋</h1><p>Vamos encontrar, analisar e transformar produtos em boas ofertas.</p></div><nav><span>🏠 Início</span><span>🛍️ Produtos</span><span>🔥 Ofertas</span><span>🤖 IA</span><span>📊 Métricas</span></nav><div class="grid"><div class="card"><div class="label">Produtos</div><div class="number" id="products">0</div></div><div class="card"><div class="label">Ofertas</div><div class="number" id="offers">0</div></div><div class="card"><div class="label">Cliques</div><div class="number" id="clicks">0</div></div><div class="card"><div class="label">Publicações</div><div class="number" id="publications">0</div></div></div><div class="section"><h2>➕ Cadastrar produto</h2><div class="card"><form class="form" id="productForm"><input name="name" placeholder="Nome do produto" required><input name="store" placeholder="Loja"><input name="category" placeholder="Categoria"><input name="url" placeholder="Link do produto"><input name="affiliate_url" placeholder="Link de afiliado"><input name="old_price" type="number" step="0.01" placeholder="Preço antigo"><input name="current_price" type="number" step="0.01" placeholder="Preço atual"><button type="submit">Cadastrar produto</button></form></div></div><div class="section"><h2>🛍️ Produtos cadastrados</h2><div id="productList" class="products"></div></div></main><script>
async function load(){try{const r=await fetch('/api/products');const data=await r.json();document.getElementById('products').textContent=data.length;const list=document.getElementById('productList');if(!data.length){list.innerHTML='<div class="card empty">Nenhum produto cadastrado ainda.</div>';return}list.innerHTML=data.map(p=>{let price=p.current_price!=null?'R$ '+Number(p.current_price).toFixed(2).replace('.',','):'';return `<div class="product"><strong>${escapeHtml(p.name)}</strong><div>${escapeHtml(p.store||'')}${p.category?' · '+escapeHtml(p.category):''}</div>${price?'<div class="price">'+price+'</div>':''}</div>`}).join('')}catch(e){document.getElementById('productList').innerHTML='<div class="card empty">Não foi possível carregar os produtos.</div>'}}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}
document.getElementById('productForm').addEventListener('submit',async e=>{e.preventDefault();const f=new FormData(e.target);const body={name:f.get('name'),store:f.get('store')||null,category:f.get('category')||null,url:f.get('url')||null,affiliate_url:f.get('affiliate_url')||null,old_price:f.get('old_price')?Number(f.get('old_price')):null,current_price:f.get('current_price')?Number(f.get('current_price')):null};const r=await fetch('/api/products',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok){alert('Não foi possível cadastrar o produto.');return}e.target.reset();await load();alert('Produto cadastrado com sucesso! 🎉')});load();
</script></body></html>'''

@app.get("/", response_class=HTMLResponse)
def home(): return HTML
@app.get("/api/health")
def health(): return {"status":"ok","app":"OFERTA IA"}
@app.get("/api/products")
def products(): return supabase.table("products").select("*").order("created_at", desc=True).execute().data
@app.post("/api/products")
def create_product(product: Product):
    result=supabase.table("products").insert(product.model_dump()).execute()
    if not result.data: raise HTTPException(400,"Não foi possível cadastrar o produto.")
    return result.data[0]
