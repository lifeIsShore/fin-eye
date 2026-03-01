from fastapi import FastAPI


app = FastAPI(title="Fin-Eye Backend", version="0.1.0")


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


