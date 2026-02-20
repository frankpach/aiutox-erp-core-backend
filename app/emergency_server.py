"""
Servidor de emergencia - mínimo y funcional.
"""

from fastapi import FastAPI

# Crear aplicación FastAPI mínima
app = FastAPI(
    title="AiutoX ERP - Emergency Server",
    version="0.1.0-emergency",
    description="Servidor de emergencia sin imports problemáticos",
)


@app.get("/")
def root():
    return {"message": "Emergency server running"}


@app.get("/healthz")
def healthz():
    return {"status": "ok", "mode": "emergency"}


@app.get("/test")
def test():
    return {"message": "Test endpoint working"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
