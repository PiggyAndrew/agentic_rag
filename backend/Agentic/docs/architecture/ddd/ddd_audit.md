# backend DDD 合规性检查记录

## 结论
- 当前 backend 结构总体接近"限界上下文（modules/*）+ 四层（application/domain/infrastructure）"的目标形态
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

### 5) 消除 `backend/kb/` 目录，统一限界上下文结构
- 现象：存在 `backend/kb/` 目录，包含多个转发模块，与 DDD 项目结构规范冲突
- 影响：
  - 项目结构不一致，部分代码在 `backend/kb/`，部分在 `modules/kb/`
  - 存在违规依赖：`modules/kb/application/services/file_ingestion.py` 引用 `backend.kb.splitters`
  - 违反分层依赖规则，应用层不应引用非模块化的代码
- 修复：
  - 删除 `backend/kb/` 目录及其所有文件（`knowledge_base.py`、`knowledge_repository.py`、`knowledge_service.py`、`types.py`、`splitters/`）
  - 修复 `file_ingestion.py` 中的违规依赖，改为引用 `modules/kb/infrastructure/legacy_kb/splitters/splitter_adaptive.py`
  - 更新 `entrypoints/server.spec`，移除 `backend.kb` 的 hiddenimports
  - 所有 KB 相关代码统一在 `modules/kb/` 下，符合 DDD 限界上下文规范
- 验证：
  - 测试通过：`backend/tests/test_kb_legacy_utils.py` 运行成功
  - 导入验证：所有 KB 模块导入正常，无错误

## 2026-02-07 重构（本次）

### 6) KB 模块全面重构
- 问题：
  - `PersistentKnowledgeBaseController` 承担过多职责（控制器+向量存储+嵌入+重排序）
  - `file_ingestion.py` 直接依赖 `legacy_kb/splitters/splitter_adaptive.py`（违反分层规则）
  - 应用层违规依赖：`allow_application_infrastructure_import_files` 包含 `usecase.py`
  - 工具层绕过应用层：`tools/runtime.py` 直接依赖 `kb.controller`
- 修复：
  - **领域层重构**：
    - 定义 `KnowledgeBase` 和 `KnowledgeFile` 聚合根，添加行为方法
    - 新增 `SearchQuery` 和 `SearchResult` 值对象
  - **端口细化**：
    - 新增 `TextSplitterPort`、`VectorStorePort`、`EmbeddingPort`、`RerankPort`、`SearchPort`
    - 将 `PersistentKnowledgeBaseController` 的职责拆分到多个端口
  - **适配器拆分**：
    - `VectorStoreAdapter`：实现 `VectorStorePort`
    - `EmbeddingAdapter`：实现 `EmbeddingPort`
    - `RerankAdapter`：实现 `RerankPort`
    - `SearchAdapter`：实现 `SearchPort`
    - `TextSplitterAdapter`：实现 `TextSplitterPort`
    - `KnowledgeBaseControllerAdapter`：实现 `KnowledgeBaseControllerPort` 和相关端口
    - `ChunkWriterAdapter`：实现 `KnowledgeChunkWriterPort`
  - **应用层重构**：
    - `file_ingestion.py` 移除对 `legacy_kb` 的直接依赖，改为通过端口注入 `TextSplitterPort`
    - `usecase.py` 新增 `search`、`get_files_meta`、`read_file_chunks_dict`、`list_files_paginated` 方法
  - **组合根重构**：
    - `build_kb_usecase` 使用新的适配器替代 `PersistentKnowledgeBaseController`
    - 更新 `rules.json`，移除应用层违规依赖的例外
  - **工具层重构**：
    - `tools/runtime.py` 改为接收 `kb_usecase` 而非 `kb.controller`
    - `rag_agent.py` 更新为传递 `kb` 而非 `kb.controller`
  - **公共逻辑抽取**：
    - 创建 `shared/mappers/kb_mappers.py` 存放 ORM 转换函数
    - 创建 `shared/utils/time_utils.py` 存放时间工具函数
  - **命名规范统一**：
    - 更新 `UBIQUITOUS_LANGUAGE.md`，添加详细的术语表和命名规范

### 7) 资源管理与并发安全
- 问题：
  - 数据库连接未显式关闭
  - ChromaDB 客户端未及时释放
  - 缺少并发控制
  - 线程安全问题
- 修复：
  - 为 `SqliteSessionManager` 添加 `close()` 方法
  - 为 `ChromaVectorStore` 实现上下文管理器协议
  - 为 `PersistentKnowledgeBaseController` 添加文件级别锁
  - 为 `ChromaVectorStore` 添加缓存锁

### 8) 错误处理改进
- 问题：
  - 异常吞没
  - 输入验证不足
  - 事务处理不完整
- 修复：
  - 在 `api/routers/chat.py` 中添加日志记录和异常重新抛出
  - 在 `save_upload` 方法中添加文件名、大小、格式验证
  - 为 `save_chunks` 添加事务补偿机制

### 9) 安全加固
- 问题：
  - SQL 注入风险
  - API Key 泄露风险
- 修复：
  - 审查所有数据库操作，确认使用 SQLAlchemy ORM 和参数化查询，无 SQL 注入风险
  - API Key 脱敏已在 API 层面通过返回 "***" 实现，创建了 `security_utils.py` 工具函数供后续使用

### 10) 架构重构
- 问题：
  - UseCase 层职责过重
  - 向量存储紧耦合 ChromaDB
  - 全局状态管理不规范
- 修复：
  - 创建 `KnowledgeSearchUseCase` 来分担搜索职责
  - 通过端口和适配器解耦向量存储实现
  - 更新组合根使用新的适配器

## 仍建议后续改进（未强制重构）
- `kb` 模块目前仍大量使用 legacy 类型与实现（偏"基础设施/遗留子系统"形态）；建议逐步在 `kb/domain` 中沉淀稳定模型与端口，并在 `kb/application` 内完成映射与编排
'这是一份建筑施工图纸的右下角部分，主要为‘完成面（Finish Schedule）’表格及项目信息栏。图纸右侧为项目基本信息与签署栏，左侧为三个独立的完成面清单表格：\n\n1.  **FLOOR FINISH SCHEDULE（地面完成面表）**：共16行，编号F1-F16，描述各类地面材料，如5mm厚柔性乙烯基地板、重载地毯瓷砖、硬木条纹地板、陶瓷砖（含不同尺寸、颜色、铺装方式）、EPDM预制运动场地表面、回收铺路石、水泥砂浆找平层、高强环氧自流平、白釉陶瓷砖、环氧漆涂层、混凝土保温砖、25mm水泥砂浆等。\n\n2.  **WALL FINISH SCHEDULE（墙面完成面表）**：共11行，编号W1-W11，描述各类墙面系统，包括：12mm胶合板背衬的声学墙板；带矿物木材墙的定制木饰面；12mm胶合板背衬的木饰面；12mm塑料层压板；300×300×5mm陶瓷砖+水泥砂浆抹灰+专用粘结系统；45×195×5mm陶瓷砖+外饰面；150×300×5mm陶瓷砖+内/外水泥砂浆抹灰+水泥基防水系统；2层抗真菌乳胶漆（哑光）；聚氨酯纹理漆+水泥砂浆饰面；可清洗清漆；150×150×10mm白色釉面陶瓷砖+水泥砂浆抹灰+专用粘结系统。\n\n3.  **SKIRTING FINISH SCHEDULE（踢脚线完成面表）**：共8行，编号S1-S8，描述踢脚线材质与构造，如12mm厚硬木踢脚线（合成漆面）、18mm厚硬木（匹配地板）、600×50mm(H)×10mm厚覆边同色均质砖、300×50mm(H)×10mm厚覆边同色均质砖、100×100mm(H)×10mm厚人工花岗岩、50mm(H)×25mm厚水泥砂浆+2道环氧漆、150×150mm(H)×10mm厚白釉陶瓷砖、300×50mm(H)×10mm厚覆边同色均质砖。\n\n4.  **CEILING FINISH SCHEDULE（吊顶完成面表）**：共9行，编号C1-C9，描述吊顶系统，包括：无饰面裸露混凝土；带吸音板的吊挂式吊顶系统（含铝制网格）；同上但为“专有”系统；200mm铝合金条形假顶；1层液态预聚物密封+2层白色丙烯酸树脂亮光漆；2层抗真菌乳胶漆（黑）+10mm内层吊顶板；喷涂纹理漆+20mm外饰面（需SOFFIT & EXPOSED E&M服务）；木饰面假顶系统。\n\n右侧信息栏包含：\n- **NOTES（说明）**：2条，强调所有测量须现场复核，图纸不适用于施工，除非经认证。\n- **公司Logo与顾问团队**：a) Structural Consultant（结构顾问）：alda；b) Building Services Consultant（建筑设备顾问）：aurecon；c) Landscape Consultant（景观顾问）：ATKINS；d) Environmental Engineering Consultant（环境工程顾问）：Mott MacDonald；e) Traffic Consultant（交通顾问）：SYSTRA；f) BIM Consultant（BIM顾问）：isBIM；g) Architect（建筑师）：AD+RG。\n- **项目信息**：Contract No. SS L510；AED project No. 8489；Job No. A1069；Project: CONSTRUCTION OF A 30-CLASSROOM PRIMARY SCHOOL AT SITE 1B-4, KAI TAK（香港启德某小学30间教室建设）；Drawing Title: FINISH SCHEDULE (1)。\n- **签署栏**：含Designated、Drawn、Check、Approved四栏，签名分别为CY、RC、AL、BL/SK；Scale: NTS @A3；Drawing No: AB/8489/CA001；Revision: -。\n- **左下角Logo**：ARCHITECTURAL SERVICES DEPARTMENT（建筑署）。\n\n整体为一份专业建筑施工图中的‘完成面详表’，用于指导各部位装修材料、规格、工艺及系统构成，是施工与验收的重要依据。'