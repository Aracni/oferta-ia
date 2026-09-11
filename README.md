# OFERTA IA

Sistema inteligente de descoberta e análise de oportunidades de venda em marketplaces.

## Arquitetura atual

- `boot.py` é o ponto de entrada do Render.
- `app.py` carrega o núcleo V11.9 e o patch de enriquecimento V11.10.12.
- `v106_patch.py` mantém o endpoint central e o diagnóstico persistente.
- `meli_auto.py` cuida da renovação automática da autorização do Mercado Livre.
- `meli_fast.py` aplica limites de segurança às chamadas de detalhe do Mercado Livre.
- `ml_enrichment_v2.py` enriquece os candidatos do Mercado Livre e monta o seletor de marketplace.

A aplicação não depende de middleware HTTP para montar a interface.

## Deploy no Render

Comando de inicialização:
`python boot.py`

O `boot.py` inicia o Uvicorn usando a variável `PORT` fornecida pelo Render.

## Variáveis de ambiente

Obrigatórias:
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` ou `SUPABASE_SERVICE_ROLE_KEY`

Usadas quando configuradas:
- `MELI_CLIENT_ID`
- `MELI_CLIENT_SECRET`
- `GEMINI_API_KEY` ou `GOOGLE_API_KEY`
- `GEMINI_MODEL`

Nunca publique chaves secretas no código, no HTML ou no GitHub.

## Regra de manutenção

As versões congeladas do núcleo são referenciadas por commit SHA no `app.py` para evitar que uma alteração futura no `main` mude silenciosamente o núcleo em produção. Depois de validar uma nova versão, atualize os SHAs de forma deliberada.
