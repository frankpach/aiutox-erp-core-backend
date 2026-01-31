"""
Servidor ultra-emergencia - sin absolutamente nada de app.
"""

# Solo importar lo esencial
try:
    from fastapi import FastAPI
    print("✅ FastAPI importado")
except Exception as e:
    print(f"❌ Error importando FastAPI: {e}")
    raise

# Crear aplicación sin absolutamente nada más
app = FastAPI(title="Ultra Emergency Server")

@app.get("/")
def root():
    return {"message": "Ultra emergency server", "status": "working"}

@app.get("/test")
def test():
    return {"test": "ok", "timestamp": "now"}

if __name__ == "__main__":
    try:
        import uvicorn
        print("✅ Uvicorn importado")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        print(f"❌ Error importando uvicorn: {e}")
        raise
