# backend DDD 项目结构规范

## 结构总览
- UI 层：`backend/api/`（FastAPI 路由与请求/响应 DTO 映射）
- 限界上下文（BC）：`backend/modules/<context>/`
- 共享基础设施：`backend/infrastructure/`（跨上下文的通用技术能力）
- 共享通用能力：`backend/domain/`、`backend/shared/`（尽量保持贫血与无框架依赖）

## 单个限界上下文目录（推荐）
```
backend/modules/<context>/
  application/
  domain/
  infrastructure/
```

## 各层职责
- UI（`backend/api`）：只做协议适配（HTTP/headers/鉴权/序列化），不实现业务规则；依赖应用层用例或服务
- Application：用例编排与事务边界（权限、调用顺序、跨聚合/跨上下文协调）；只依赖 Domain
- Domain：聚合根/实体/值对象/领域服务/领域事件；不得依赖 FastAPI/SQLAlchemy/HTTP/文件系统等
- Infrastructure：DB/ORM、消息、外部 API、文件系统、向量库等技术实现；实现 Domain 端口

## 对本仓库的落地约定
- 路由层（`backend/api/routers/*`）不得直接导入 `backend.modules.*.infrastructure.*`
- 基础设施装配集中在组合根（`backend/api/main.py` 的 lifespan）
- 每个上下文应逐步补齐：`domain/models.py`、`domain/ports.py`，应用层通过端口注入基础设施实现

