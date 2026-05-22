from backend.config.llm_config import LLMProviderCreate, LLMProviderType, ModelCategory
from backend.config.llm_config_repository import LLMConfigRepository
from backend.config.config_repository import SqlAlchemyConfigRepository
import os

def seed_providers():
    repo = LLMConfigRepository()
    # for p in repo.list_providers():
    #      repo.delete(p.id)
    providers = repo.list_providers(enabled_only=False)
    isDebug = True
    if not providers:
        # 1. Ollama Embedding
        repo.create(LLMProviderCreate(
            name="Ollama Embedding (Qwen)",
            category=ModelCategory.embedding,
            provider_type=LLMProviderType.ollama,
            base_url="http://localhost:11434",
            api_key="",
            model_name="qwen3-embedding",
            description="Default Ollama Embedding",
            is_default=isDebug
        ))

        # 2. Ollama Reranker
        repo.create(LLMProviderCreate(
            name="Ollama Reranker (Qwen3)",
            category=ModelCategory.reranker,
            provider_type=LLMProviderType.ollama,
            base_url="http://localhost:11434",
            api_key="",
            model_name="dengcao/Qwen3-Reranker-8B:Q3_K_M",
            description="Default Ollama Reranker",
            is_default=isDebug
        ))

        # 3. vLLM LLM
        repo.create(LLMProviderCreate(
            name="Ollama vLLM (qwen3-vl)",
            category=ModelCategory.vll,
            provider_type=LLMProviderType.vllm,
            base_url="http://localhost:8000/v1",
            api_key="",
            model_name="qwen3-vl:latest",
            description="Default vLLM Service",
            is_default=isDebug
        ))

        # 4. DeepSeek
        ds_key ="sk-XXXXXXX" # 请替换为实际的 DeepSeek API Key
        repo.create(LLMProviderCreate(
            name="DeepSeek Chat",
            category=ModelCategory.llm,
            provider_type=LLMProviderType.deepseek,
            base_url="https://api.deepseek.com/v1",
            api_key=ds_key,
            model_name="deepseek-chat",
            description="DeepSeek Official API",
            is_default=True
        ))

        # 5. DashScope Embedding (Aliyun)
        ak = "sk-XXXXXX"    # 请替换为实际的 DashScope API Key
        base =  "https://dashscope.aliyuncs.com/compatible-mode/v1"
        repo.create(LLMProviderCreate(
            name="Aliyun Embedding",
            category=ModelCategory.embedding,
            provider_type=LLMProviderType.dashscope,
            base_url=base,
            api_key=ak,
            model_name= "text-embedding-v4",
            description="Aliyun DashScope Embedding 默认模型",
            is_default=not isDebug
        ))
        # DashScope Reranker
        repo.create(LLMProviderCreate(
            name="Aliyun Reranker",
            category=ModelCategory.reranker,
            provider_type=LLMProviderType.dashscope,
            base_url=base,
            api_key=ak,
            model_name="qwen3-rerank",
            description="Aliyun DashScope Reranker 默认模型",
            is_default=not isDebug
        ))
        # DashScope LLM
        repo.create(LLMProviderCreate(
            name="Aliyun LLM",
            category=ModelCategory.llm,
            provider_type=LLMProviderType.dashscope,
            base_url=base,
            api_key=ak,
            model_name="deepseek-v3.2",
            description="Aliyun DashScope LLM 默认模型",
            is_default=not isDebug
        ))

    # 设置默认激活的 Provider IDs（若未设置）
    providers = repo.list_providers()
    cfg = SqlAlchemyConfigRepository()

    def get_config_value(key: str):
        try:
            row = cfg.get_config(key)
            return row.value if row else None
        except Exception:
            return None

    def set_config_value(key: str, value):
        try:
            cfg.set_config(key, value, description=f"Auto set by seed_providers: {key}")
        except Exception:
            pass

    # 选择规则助手函数
    def find_provider_by_type(ptype: LLMProviderType, model_substr: str | None = None):
        for p in providers:
            if p.provider_type == ptype:
                if model_substr:
                    if (p.model_name or "").lower().find(model_substr.lower()) >= 0:
                        return p
                else:
                    return p
        return None

    # Embedding: 优先 DashScope，其次 Ollama qwen3-embedding
    if get_config_value("active_embedding_provider_id") in (None, "", 0):
        emb = find_provider_by_type(LLMProviderType.dashscope, "embedding") or find_provider_by_type(LLMProviderType.ollama, "qwen3-embedding") or find_provider_by_type(LLMProviderType.ollama)
        if emb:
            set_config_value("active_embedding_provider_id", emb.id)

    # Reranker: 优先 Ollama qllama/bge-reranker-v2-m3，其次包含 reranker 的
    if get_config_value("active_reranker_provider_id") in (None, "", 0):
        rer = None
        for p in providers:
            if p.provider_type == LLMProviderType.ollama and ((p.model_name or "").lower().find("reranker") >= 0 or (p.name or "").lower().find("reranker") >= 0):
                if (p.model_name or "").lower().find("bge-reranker-v2-m3") >= 0:
                    rer = p
                    break
                rer = p
        rer = rer or find_provider_by_type(LLMProviderType.ollama)
        if rer:
            set_config_value("active_reranker_provider_id", rer.id)

    # vLLM: 选择 vllm 类型的第一个
    if get_config_value("active_vll_provider_id") in (None, "", 0):
        vll = find_provider_by_type(LLMProviderType.vllm)
        if vll:
            set_config_value("active_vll_provider_id", vll.id)

    # Chat LLM: 优先 DeepSeek（若有 API Key），否则使用 vLLM
    if get_config_value("active_llm_provider_id") in (None, "", 0):
        # deepseek 有 key 时优先
        ds = find_provider_by_type(LLMProviderType.deepseek)
        if ds and (ds.api_key or "").strip():
            set_config_value("active_llm_provider_id", ds.id)
        else:
            vll = find_provider_by_type(LLMProviderType.vllm)
            if vll:
                set_config_value("active_llm_provider_id", vll.id)
