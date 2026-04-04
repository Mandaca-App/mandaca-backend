from fastapi import FastAPI

import app.models
from app.core.config import settings
from app.routers import enterprises, photos, users

app = FastAPI(title="Meu Projeto", version="0.1.0")

app.include_router(users.router)
app.include_router(enterprises.router)
app.include_router(photos.router)


@app.get("/", tags=["health"])
def health_check():
    """Endpoint de health check — usado pelo Render para verificar se a app está viva."""
    return {"status": "ok", "env": settings.app_env}
