from __future__ import annotations

import os
import unittest

from backend.database.sqlite import SqliteSessionManager, init_sqlite_database
from backend.modules.config.infrastructure import boot_config
from backend.modules.providers.domain.models import LLMProviderCreate, LLMProviderType, ModelCategory, LLMProviderUpdate
from backend.modules.providers.infrastructure.llm_config_repository import LLMConfigRepository
from backend.modules.providers.infrastructure.persistence.models import ProvidersBase
from backend.modules.providers.infrastructure.seed import seed_providers


class ProviderSeedTests(unittest.TestCase):
    def test_seed_defaults_in_development(self) -> None:
        old_app_env = os.environ.get("APP_ENV")
        os.environ["APP_ENV"] = "development"
        boot_config._boot = None
        try:
            manager = SqliteSessionManager.from_url("sqlite:///:memory:")
            init_sqlite_database(manager=manager, metadatas=[ProvidersBase.metadata])
            repo = LLMConfigRepository(manager=manager)

            seed_providers(manager=manager)

            llm = repo.get_default_by_category(ModelCategory.llm.value)
            embedding = repo.get_default_by_category(ModelCategory.embedding.value)
            reranker = repo.get_default_by_category(ModelCategory.reranker.value)
            vll = repo.get_default_by_category(ModelCategory.vll.value)

            self.assertIsNotNone(llm)
            self.assertIsNotNone(embedding)
            self.assertIsNotNone(reranker)
            self.assertIsNotNone(vll)
            self.assertEqual(llm.provider_type, LLMProviderType.deepseek)
            self.assertEqual(embedding.provider_type, LLMProviderType.ollama)
            self.assertEqual(reranker.provider_type, LLMProviderType.ollama)
            self.assertEqual(vll.provider_type, LLMProviderType.dashscope)
        finally:
            if old_app_env is None:
                os.environ.pop("APP_ENV", None)
            else:
                os.environ["APP_ENV"] = old_app_env
            boot_config._boot = None

    def test_seed_enables_dashscope_embedding_in_production(self) -> None:
        old_app_env = os.environ.get("APP_ENV")
        os.environ["APP_ENV"] = "production"
        boot_config._boot = None
        try:
            manager = SqliteSessionManager.from_url("sqlite:///:memory:")
            init_sqlite_database(manager=manager, metadatas=[ProvidersBase.metadata])
            repo = LLMConfigRepository(manager=manager)

            p = repo.create(
                LLMProviderCreate(
                    name="DashScope Embedding",
                    category=ModelCategory.embedding,
                    provider_type=LLMProviderType.dashscope,
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    api_key="k",
                    model_name="text-embedding-v4",
                    is_default=True,
                )
            )
            repo.update(p.id, LLMProviderUpdate(is_enabled=False))

            seed_providers(manager=manager)

            embedding = repo.get_default_by_category(ModelCategory.embedding.value)
            self.assertIsNotNone(embedding)
            self.assertEqual(embedding.provider_type, LLMProviderType.dashscope)
            self.assertEqual(embedding.is_enabled, True)
        finally:
            if old_app_env is None:
                os.environ.pop("APP_ENV", None)
            else:
                os.environ["APP_ENV"] = old_app_env
            boot_config._boot = None


if __name__ == "__main__":
    unittest.main()
