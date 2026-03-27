from fastapi import FastAPI

app = FastAPI(
    title="Mandaca Backend API",
    description="API do Mandaca com documentação Swagger automática.",
    version="0.1.0",
    docs_url="/api-docs",
    redoc_url=None,
    openapi_url="/api-docs/openapi.json",
)
# uvicorn app.main:app --reload


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.get("/items")
def list_items(category: str | None = None, limit: int = 10) -> dict[str, str | int | None]:
    return {"category": category, "limit": limit}
