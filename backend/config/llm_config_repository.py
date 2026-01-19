from __future__ import annotations

from typing import List, Optional
import time

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.database.sqlite import SqliteSessionManager, get_default_sqlite_manager
from backend.config.config_models import LLMProviderORM
from backend.config.llm_config import (
    LLMProvider,
    LLMProviderCreate,
    LLMProviderUpdate,
    ModelCategory,
)


class LLMConfigRepositoryError(RuntimeError):
    """LLM配置仓储层错误基类"""


class LLMConfigNotFoundError(LLMConfigRepositoryError):
    """LLM配置不存在"""


class LLMConfigRepository:
    """LLM配置数据访问层"""

    def __init__(self, manager: Optional[SqliteSessionManager] = None):
        self._manager = manager or get_default_sqlite_manager()

    @staticmethod
    def _orm_to_model(row: LLMProviderORM) -> LLMProvider:
        """ORM转数据模型"""
        return LLMProvider(
            id=row.id,
            name=row.name,
            category=ModelCategory(row.category) if row.category else None,
            provider_type=row.provider_type,
            base_url=row.base_url,
            api_key=row.api_key,
            model_name=row.model_name,
            config=row.config,
            is_default=bool(row.is_default),
            is_enabled=bool(row.is_enabled),
            description=row.description,
            created_at_ms=row.created_at_ms,
            updated_at_ms=row.updated_at_ms,
        )

    def create(self, provider: LLMProviderCreate) -> LLMProvider:
        """创建LLM配置"""
        now_ms = int(time.time() * 1000)
        is_default = 1 if provider.is_default else 0

        with self._manager.session_scope() as session:
            if provider.is_default:
                session.execute(
                    update(LLMProviderORM)
                    .values(is_default=0)
                    .where(
                        LLMProviderORM.category == provider.category.value,
                    )
                )

            orm = LLMProviderORM(
                name=provider.name,
                category=provider.category.value,
                provider_type=provider.provider_type,
                base_url=provider.base_url,
                api_key=provider.api_key,
                model_name=provider.model_name,
                config=provider.config,
                is_default=is_default,
                is_enabled=1,
                description=provider.description,
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
            )
            session.add(orm)
            session.flush()
            return self._orm_to_model(orm)

    def get_by_id(self, provider_id: int) -> Optional[LLMProvider]:
        """根据ID获取配置"""
        with self._manager.session_scope() as session:
            row = session.get(LLMProviderORM, provider_id)
            return self._orm_to_model(row) if row else None

    def get_default(self, provider_type: str) -> Optional[LLMProvider]:
        """获取指定类型的默认配置"""
        with self._manager.session_scope() as session:
            row = session.execute(
                select(LLMProviderORM)
                .where(
                    LLMProviderORM.provider_type == provider_type,
                    LLMProviderORM.is_default == 1,
                    LLMProviderORM.is_enabled == 1,
                )
                .order_by(LLMProviderORM.id.desc())
            ).scalar_one_or_none()
            return self._orm_to_model(row) if row else None

    def get_default_by_category(self, category: str) -> Optional[LLMProvider]:
        """按模型类别获取默认配置"""
        with self._manager.session_scope() as session:
            row = (
                session.execute(
                    select(LLMProviderORM)
                    .where(
                        LLMProviderORM.category == category,
                        LLMProviderORM.is_default == 1,
                        LLMProviderORM.is_enabled == 1,
                    )
                    .order_by(LLMProviderORM.id.desc())
                )
                .scalars()
                .first()
            )
            return self._orm_to_model(row) if row else None

    def list_providers(
        self, provider_type: Optional[str] = None, enabled_only: bool = True, category: Optional[str] = None
    ) -> List[LLMProvider]:
        """列出LLM配置"""
        with self._manager.session_scope() as session:
            query = select(LLMProviderORM)
            if provider_type:
                query = query.where(LLMProviderORM.provider_type == provider_type)
            if category:
                query = query.where(LLMProviderORM.category == category)
            if enabled_only:
                query = query.where(LLMProviderORM.is_enabled == 1)
            rows = (
                session.execute(query.order_by(LLMProviderORM.id.desc()))
                .scalars()
                .all()
            )
            return [self._orm_to_model(r) for r in rows]

    def update(self, provider_id: int, update_data: LLMProviderUpdate) -> LLMProvider:
        """更新LLM配置"""
        now_ms = int(time.time() * 1000)

        with self._manager.session_scope() as session:
            orm = session.get(LLMProviderORM, provider_id)
            if not orm:
                raise LLMConfigNotFoundError(f"LLM配置不存在: {provider_id}")

            if update_data.name is not None:
                orm.name = update_data.name
            if update_data.category is not None:
                orm.category = update_data.category.value
            if update_data.base_url is not None:
                orm.base_url = update_data.base_url
            if update_data.api_key is not None:
                orm.api_key = update_data.api_key
            if update_data.model_name is not None:
                orm.model_name = update_data.model_name
            if update_data.config is not None:
                orm.config = update_data.config
            if update_data.is_default is not None:
                if update_data.is_default:
                    session.execute(
                        update(LLMProviderORM)
                        .values(is_default=0)
                        .where(
                            LLMProviderORM.category == orm.category,
                            LLMProviderORM.id != provider_id,
                        )
                    )
                orm.is_default = 1 if update_data.is_default else 0
            if update_data.is_enabled is not None:
                orm.is_enabled = 1 if update_data.is_enabled else 0
            if update_data.description is not None:
                orm.description = update_data.description

            orm.updated_at_ms = now_ms
            session.flush()
            return self._orm_to_model(orm)

    def delete(self, provider_id: int) -> None:
        """删除LLM配置"""
        with self._manager.session_scope() as session:
            orm = session.get(LLMProviderORM, provider_id)
            if orm:
                session.delete(orm)

    def set_default(self, provider_id: int) -> LLMProvider:
        """设置为默认配置"""
        with self._manager.session_scope() as session:
            orm = session.get(LLMProviderORM, provider_id)
            if not orm:
                raise LLMConfigNotFoundError(f"LLM配置不存在: {provider_id}")

            session.execute(
                update(LLMProviderORM)
                .values(is_default=0)
                .where(
                    LLMProviderORM.category == orm.category,
                    LLMProviderORM.id != provider_id,
                )
            )

            orm.is_default = 1
            orm.updated_at_ms = int(time.time() * 1000)
            session.flush()
            return self._orm_to_model(orm)
