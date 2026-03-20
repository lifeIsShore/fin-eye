import asyncio
import httpx
from app.config import settings

async def main():
    print(f"Settings OLLAMA_BASE_URL: {settings.ollama_base_url}")
    print(f"Settings OLLAMA_MODEL: {settings.ollama_model}")
    
    async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=180.0) as client:
        try:
            resp = await client.get("/api/tags")
            print(f"Ollama tags status: {resp.status_code}")
            print(f"Ollama tags response: {resp.json()}")
            
            # Test simple generation
            payload = {
                "model": settings.ollama_model,
                "prompt": "Hello",
                "stream": False
            }
            resp = await client.post("/api/generate", json=payload)
            print(f"Ollama generate status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"Ollama generate success!")
            else:
                print(f"Ollama generate fail: {resp.text}")
                
        except Exception as e:
            print(f"Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
