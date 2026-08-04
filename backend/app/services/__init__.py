from __future__ import annotations

from os import getenv

from app.providers.openai_categorization import OpenAICategorizationProvider
from app.repositories import (
    categorization_rule_repository,
    category_repository,
    transaction_repository,
)
from app.services.categorization import CategorizationService


provider_mode = getenv("CATEGORIZATION_PROVIDER", "rules").strip().lower()
if provider_mode == "rules":
    categorization_provider = None
elif provider_mode == "openai":
    categorization_provider = OpenAICategorizationProvider(
        api_key=getenv("OPENAI_API_KEY"),
    )
else:
    raise ValueError(
        "CATEGORIZATION_PROVIDER must be either 'rules' or 'openai'",
    )
categorization_service = CategorizationService(
    transaction_repository=transaction_repository,
    rule_repository=categorization_rule_repository,
    category_repository=category_repository,
    provider=categorization_provider,
)


__all__ = ["CategorizationService", "categorization_service"]
