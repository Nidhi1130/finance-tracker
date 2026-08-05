import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.accounts import router as accounts_router
from app.routers.categories import router as categories_router
from app.routers.categorization_rules import router as categorization_rules_router
from app.routers.dashboard import router as dashboard_router
from app.routers.transactions import router as transactions_router

_DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3100",
    "http://127.0.0.1:3100",
]


def _allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS")
    if not raw:
        return _DEFAULT_ALLOWED_ORIGINS
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or _DEFAULT_ALLOWED_ORIGINS


app = FastAPI(
    title="Finance Flow API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(transactions_router)
app.include_router(categories_router)
app.include_router(categorization_rules_router)
app.include_router(accounts_router)
app.include_router(dashboard_router)
