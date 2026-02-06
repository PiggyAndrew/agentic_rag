# backend DDD 合规性检查记录

## 结论
- 当前 backend 结构总体接近“限界上下文（modules/*）+ 四层（application/domain/infrastructure）”的目标形态
- 已修复 UI 层（api）直接依赖基础设施层（infrastructure）的问题，使路由层只依赖应用层对象（UseCase/Service）

## 已修复问题（本次变更）
### 1) UI 层直接导入基础设施层
- 现象：`backend/api/routers/*.py` 与 `backend/api/deps.py` 直接导入 `backend.modules.*.infrastructure.*`
- 影响：UI 层绕过应用层编排，导致分层边界失效，后续演进困难
- 修复：将路由依赖调整为应用层对象（UseCase/Service），基础设施对象仅在组合根（`backend/api/main.py`）进行装配

### 2) Chat 模块应用层依赖基础设施（并向 UI 暴露 ORM）
- 现象：`ChatUseCase` 依赖 `ChatService`（SQLAlchemy）且返回 ORM 对象；UI 再做 citations JSON 解析
- 修复：
  - 增加 `chat/domain/models.py` 与 `chat/domain/ports.py`
  - `ChatUseCase` 依赖 `ChatRepositoryPort` 并返回领域模型
  - `ChatService` 作为基础设施实现，负责 ORM ↔ 领域模型映射（含 citations JSON 解析）

### 3) Config 列表接口依赖基础设施仓储
- 现象：`/api/config` 路由直接使用 `SqlAlchemyConfigRepository`
- 修复：
  - 扩展 `ConfigRepositoryPort` 暴露 `list_configs()`（返回领域模型 `SystemConfig`）
  - `ConfigService` 提供 `list_configs()`，UI 只依赖应用层服务

### 4) LLM 配置接口依赖基础设施仓储
- 现象：`/api/llm/*` 路由直接使用 `LLMConfigRepository`
- 修复：路由改为依赖 `ProviderService`，由应用层统一编排仓储访问；连通性测试也由应用层方法封装

## 仍建议后续改进（未强制重构）
- `kb` 模块目前仍大量使用 legacy 类型与实现（偏“基础设施/遗留子系统”形态）；建议逐步在 `kb/domain` 中沉淀稳定模型与端口，并在 `kb/application` 内完成映射与编排

