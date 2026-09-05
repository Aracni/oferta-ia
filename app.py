import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    raise RuntimeError("Configure SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY.")

supabase = create_client(url, key)
app = FastAPI(title="OFERTA IA")

class Product(BaseModel):
    name: str
    store: str | None = None
    url: str | None = None
    affiliate_url: str | None = None
    old_price: float | None = None
    current_price: float | None = None
    category: str | None = None

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html><html lang="pt-BR"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OFERTA IA</title><body style="font-family:Arial;max-width:700px;margin:40px auto;padding:20px">
<h1>🚀 OFERTA IA</h1><p>O sistema está online e conectado ao Supabase.</p>
<p>Próximo passo: cadastrar e analisar ofertas com IA.</p></body></html>"""

@app.get("/api/health")
def health():
    return {"status":"ok","app":"OFERTA IA"}

@app.get("/api/products")
def products():
    result = supabase.table("products").select("*").order("created_at", desc=True).execute()
    return result.data

@app.post("/api/products")
def create_product(product: Product):
    result = supabase.table("products").insert(product.model_dump()).execute()
    if not result.data:
        raise HTTPException(400, "Não foi possível cadastrar o produto.")
    return result.data[0]
