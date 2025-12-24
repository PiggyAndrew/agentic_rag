import os
import sys
import json
import argparse
from dotenv import load_dotenv

# 保证可导入顶层包
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from api.agent import create_agentic_rag_system


def to_dict(obj):
    """兼容 Pydantic v2/v1 或字典/对象的转换"""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, (dict, list, str, int, float, bool)):
        return obj
    try:
        return json.loads(json.dumps(obj, default=lambda o: getattr(o, "__dict__", str(o))))
    except Exception:
        return {"value": str(obj)}


def main():
    parser = argparse.ArgumentParser(description="运行 Agent 并打印结构化输出")
    parser.add_argument("--kb", type=int, default=1, help="知识库ID")
    parser.add_argument(
        "--question",
        default="请直接输出一个简短回答，并返回空引用；不要调用任何工具。",
        help="测试问题",
    )
    parser.add_argument("--thread", default="test-agent-1", help="线程ID（可选）")
    args = parser.parse_args()

    load_dotenv()
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("缺少 DEEPSEEK_API_KEY，请在 .env 中配置或导出环境变量。")
        sys.exit(1)

    try:
        agent = create_agentic_rag_system(args.kb)
    except Exception as e:
        print("Agent 初始化失败:", e)
        sys.exit(1)

    # 调用：提示不使用工具，验证结构化输出是否正常
    payload = {"messages": [{"role": "user", "content": args.question}]}
    config = {"configurable": {"thread_id": args.thread}}
    try:
        res = agent.invoke(payload, config)
    except Exception as e:
        print("Agent 调用失败:", e)
        sys.exit(1)

    sr = None
    if isinstance(res, dict):
        sr = res.get("structured_response")

    sr_dict = to_dict(sr)
    print("=== 结构化输出 ===")
    print(json.dumps(sr_dict, ensure_ascii=False, indent=2))

    # 基本断言
    ok = bool(sr_dict) and "answer" in sr_dict and "citations" in sr_dict
    if not ok:
        print("结构化响应缺失或字段不完整。原始返回:")
        print(json.dumps(res if isinstance(res, dict) else {"value": str(res)}, ensure_ascii=False, indent=2))
        sys.exit(2)

    print("\n校验通过：answer 与 citations 字段存在。")


if __name__ == "__main__":
    main()