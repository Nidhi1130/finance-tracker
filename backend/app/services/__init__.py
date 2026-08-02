from __future__ import annotations

from os import getenv

from app.providers.openai_categorization import OpenAICategorizationProvider
from app.repositories import (
    categorization_rule_repository,
    category_repository,
    transaction_repository,
)
from app.services.categorization import CategorizationService


openai_api_key = getenv("OPENAI_API_KEY")
categorization_provider = (
    OpenAICategorizationProvider(api_key=openai_api_key) if openai_api_key else None
)
categorization_service = CategorizationService(
    transaction_repository=transaction_repository,
    rule_repository=categorization_rule_repository,
    category_repository=category_repository,
    provider=categorization_provider,
)


__all__ = ["CategorizationService", "categorization_service"]
