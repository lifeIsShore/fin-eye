import asyncio
import time
import os
import json
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

async def check_db():
    start = time.time()
    try:
        engine = create_async_engine(os.environ.get("ASYNC_DATABASE_URL"))
        async with engine.connect() as conn:
            pass
        return {"status": "connected", "latency_ms": (time.time() - start) * 1000}
    except Exception as e:
        return {"status": "failed", "error": str(e), "latency_ms": (time.time() - start) * 1000}

async def check_redis():
    start = time.time()
    try:
        r = aioredis.from_url(os.environ.get("REDIS_URL"))
        await r.ping()
        await r.close()
        return {"status": "connected", "latency_ms": (time.time() - start) * 1000}
    except Exception as e:
        return {"status": "failed", "error": str(e), "latency_ms": (time.time() - start) * 1000}

async def check_ollama():
    start = time.time()
    try:
        async with AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{os.environ.get('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')}/api/tags")
            return {"status": "connected" if resp.status_code == 200 else "error", "status_code": resp.status_code, "latency_ms": (time.time() - start) * 1000}
    except Exception as e:
        return {"status": "failed", "error": "Connection Refused / Failed", "latency_ms": (time.time() - start) * 1000}

async def run_audit():
    print("Starting Performance & Connection Audit...")
    results = {
        "connections": {},
        "integrations": {}
    }
    
    results["connections"]['database'] = await check_db()
    results["connections"]['redis'] = await check_redis()
    results["connections"]['ml_ollama_local'] = await check_ollama()
    
    # Audit configurations for mock vs real
    integrations = {
        "Authentication": "REQUIRE_AUTH",
        "OpenAI": "OPENAI_API_KEY",
        "Anthropic": "ANTHROPIC_API_KEY",
        "Reddit": "REDDIT_CLIENT_ID",
        "Stripe": "STRIPE_SECRET_KEY",
        "Pinecone (Vector DB)": "PINECONE_API_KEY",
        "Twitter/X": "TWITTER_BEARER_TOKEN",
        "Finnhub": "FINNHUB_API_KEY",
        "AlphaVantage": "ALPHA_VANTAGE_API_KEY",
        "Polygon": "POLYGON_API_KEY",
    }
    
    for name, env_var in integrations.items():
        val = os.environ.get(env_var, "").strip()
        if val.lower() == 'false':
            status = "MOCKED / DISABLED"
        elif not val:
            status = "MOCKED / PLACEHOLDER (Missing Key)"
        else:
            status = "LIVE (Dynamic)"
        results["integrations"][name] = status

    with open('audit_results.json', 'w') as f:
        json.dump(results, f, indent=4)
        
    print("Audit Complete. Saved to audit_results.json")

if __name__ == "__main__":
    asyncio.run(run_audit())
