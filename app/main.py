from fastapi import FastAPI
from app.routers import users
from app.core.config import settings

app = FastAPI(
    title="Meu Projeto",
    version="0.1.0"
)

app.include_router(users.router, prefix="/users", tags=["users"])


@app.get("/", tags=["health"])
def health_check():
    """Endpoint de health check — usado pelo Render para verificar se a app está viva."""
    return {"status": "ok", "env": settings.app_env}