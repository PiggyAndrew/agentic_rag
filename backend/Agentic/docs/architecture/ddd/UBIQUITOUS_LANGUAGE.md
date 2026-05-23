# 统一语言（Ubiquitous Language）实践

## 原则
- 领域术语优先：类/方法/事件命名来自业务语言，而非技术语言
- 一词一义：同一限界上下文内一个词只表达一个概念
- 边界映射：跨上下文的同名概念必须在边界处显式映射

## 命名约定
- 聚合根：名词（如 `Order`、`ChatSession`、`KnowledgeBase`）
- 值对象：名词且不可变（如 `Email`、`Money`、`ChunkMetadata`）
- 领域事件：过去式（如 `OrderPlaced`、`KnowledgeBaseCreated`）
- 用例/命令：动宾（如 `CreateChatSession`、`IngestKnowledgeFile`）
- 端口：`Port` 后缀（如 `KnowledgeRepositoryPort`、`SearchPort`）
- 适配器：`Adapter` 后缀（如 `VectorStoreAdapter`、`EmbeddingAdapter`）
- 应用层服务：`Service` 后缀（如 `FileIngestionService`、`ProviderService`）
- 应用层用例：`UseCase` 后缀（如 `KnowledgeBaseUseCase`、`ChatUseCase`）

## 术语表
| 术语 | 代码名 | 定义 | 反例 | 备注 |
|---|---|---|---|---|
| 知识库 | `KnowledgeBase` | 存储文档和知识片段的容器 | `KB`, `KnowledgeBaseEntity` | 聚合根 |
| 知识库文件 | `KnowledgeFile` | 知识库中的文档文件 | `File`, `Document` | 实体 |
| 知识块 | `KnowledgeChunk` | 文档切分后的文本片段 | `Chunk`, `TextChunk` | 实体 |
| 文件状态 | `FileStatus` | 文件处理状态（uploaded/chunked/done） | `Status`, `FileState` | 值对象 |
| 块元数据 | `ChunkMetadata` | 知识块的元数据（页码、标题等） | `Metadata`, `ChunkMeta` | 值对象 |
| 搜索查询 | `SearchQuery` | 知识库搜索请求 | `Query`, `SearchRequest` | 值对象 |
| 搜索结果 | `SearchResult` | 知识库搜索结果 | `Result`, `SearchItem` | 值对象 |
| 聊天会话 | `ChatSession` | 用户与 AI 的对话会话 | `Session`, `Conversation` | 聚合根 |
| 聊天消息 | `ChatMessage` | 会话中的单条消息 | `Message`, `ChatItem` | 实体 |
| LLM 提供商 | `LLMProvider` | 大语言模型服务提供商 | `Provider`, `LLMService` | 实体 |
| 配置服务 | `ConfigService` | 系统配置管理服务 | `ConfigManager`, `SettingsService` | 应用层服务 |
| 文件摄取服务 | `FileIngestionService` | 文件解析和切分服务 | `IngestionService`, `FileParser` | 应用层服务 |
| 向量存储 | `VectorStorePort` | 向量数据库接口 | `VectorDB`, `EmbeddingStore` | 端口 |
| 嵌入服务 | `EmbeddingPort` | 文本向量化接口 | `Embedder`, `TextEmbedding` | 端口 |
| 重排序服务 | `RerankPort` | 搜索结果重排序接口 | `Reranker`, `ReRanking` | 端口 |
| 搜索服务 | `SearchPort` | 知识库搜索接口 | `SearchService`, `QueryService` | 端口 |
| 文本分割器 | `TextSplitterPort` | 文本切分接口 | `Splitter`, `TextChunker` | 端口 |

## 模块命名规范
- 限界上下文：小写 + 下划线（如 `kb`、`chat`、`agents`）
- 领域层：`domain/models.py`、`domain/ports.py`、`domain/services/`
- 应用层：`application/usecase.py`、`application/services/`
- 基础设施层：`infrastructure/adapters/`、`infrastructure/persistence/`
- 共享模块：`shared/`（如 `shared/utils/`、`shared/mappers/`）

## 方法命名规范
- 查询方法：`get_*`（如 `get_kb`、`get_file`）
- 列表方法：`list_*`（如 `list_kbs`、`list_files`）
- 创建方法：`create_*`（如 `create_kb`、`create_file`）
- 更新方法：`update_*`（如 `update_kb`、`update_file`）
- 删除方法：`delete_*`（如 `delete_kb`、`delete_file`）
- 搜索方法：`search`（如 `search`、`search_knowledge_base`）
- 摄取方法：`ingest_*`（如 `ingest_pdf`、`ingest_excel`）

## 变量命名规范
- 环境变量：大写 + 下划线（如 `LLM_API_KEY`、`KB_BASE_DIR`）
- 枚举值：小写 + 下划线（如 `uploaded`、`chunked`、`done`）
- 配置键：小写 + 点分隔（如 `llm.api_key`、`kb.base_dir`）
