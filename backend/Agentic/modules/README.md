## Modules（Bounded Contexts）

目标：把后端组织成“可拆微服务的模块化单体”。每个上下文在 `modules/<context>/` 下自洽，外部只能通过 `application` 暴露的用例接口交互。

### 分层约束（依赖方向）
- `presentation`（API/适配） → `application`（用例编排） → `domain`（实体/策略/ports）
- `application` 只能通过 `domain/ports` 依赖 `infrastructure`（适配器实现）
- `domain` 禁止依赖：`fastapi/sqlalchemy/httpx/langchain/*`

### 现有上下文
- `kb`：知识库

### 规划上下文
- `config`：Boot/Runtime 配置与特性开关
- `providers`：LLM/Embedding/Reranker/VLL 提供商目录与按类别激活
- `chat`：会话与消息
- `docx`：文档重写
- `agents`：智能体编排（只依赖用例/ports）

