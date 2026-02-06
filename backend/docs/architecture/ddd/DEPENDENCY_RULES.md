# backend DDD 分层依赖规则

## 分层依赖矩阵
- Domain：不得依赖 UI / Application / Infrastructure；不得依赖框架与 IO
- Application：仅依赖 Domain；通过端口（Protocol/接口）访问外部能力
- UI：依赖 Application；不得直接依赖各上下文 Infrastructure（组合根装配例外）
- Infrastructure：可以依赖 Domain（实现端口）；不得反向依赖 Application/UI

## 限界上下文边界
- 禁止：`backend.modules.A.domain` 直接导入 `backend.modules.B.domain`
- 允许：
  - Application → ACL/适配器 → 外部接口（HTTP/消息/SDK）
  - 通过集成事件/发布语言（published language）传递数据

## 例外与过渡策略
- legacy 子系统（例如 `kb` 当前的 `legacy_kb`）允许在迁移期存在应用层对基础设施的依赖，但必须：
  - 在审查中标注为迁移债务
  - 逐步将稳定的类型与端口沉淀到 `domain/`

