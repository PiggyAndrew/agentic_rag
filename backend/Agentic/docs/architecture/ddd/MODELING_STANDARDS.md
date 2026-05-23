# 领域建模标准

## 聚合（Aggregate）
- 聚合根是唯一对外写入口；对外写操作通过聚合根行为表达
- 聚合根维护一致性不变量（invariants）
- 聚合边界内实体/值对象不得被外部直接修改或持久化

## 实体（Entity）
- 具有稳定标识（ID），生命周期内身份不变
- 行为优先，不做纯数据容器

## 值对象（Value Object）
- 不可变（immutable），以值相等为主
- 构造时完成校验，确保合法状态

## 领域服务（Domain Service）
- 表达跨多个实体/值对象/聚合的领域规则
- 无持久状态；依赖通过参数传入

## 领域事件（Domain Event）
- 表达“已发生的领域事实”，命名用过去式
- 载荷只包含必要领域数据，避免 ORM/HTTP DTO 泄漏
- Application 负责事务一致性的发布策略（出站箱等）

## 仓储（Repository）
- 面向聚合根；接口定义在 Domain，技术实现放在 Infrastructure
- Application 只依赖接口，通过装配/注入获得实现

