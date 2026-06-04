from fastapi import FastAPI
from datetime import datetime
from dennis.server.routers.artifacts import router as artifacts_router
from dennis.server.routers import federation


app = FastAPI(
    title="Dennis Forge API",
    description="Deterministic Codemod Infrastructure",
    version="0.3.0"
)
from dennis.server.routers import registry

app.include_router(registry.router)
app.include_router(artifacts_router)
app.include_router(federation.router)

@app.get("/api/health")
def health():
    return {
        "service": "dennis-forge",
        "status": "ok",
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }
