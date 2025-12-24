import os
import sys
import json
import argparse

from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from langchain_core.messages import ToolMessage

from api.sql_agent import create_sql_agent


def extract_sql_query_tool_payload(messages):
    tool_payloads = []
    for m in messages:
        if isinstance(m, ToolMessage) and m.name == "sql_db_query":
            try:
                tool_payloads.append(json.loads(m.content))
            except Exception:
                tool_payloads.append({"raw": m.content})
    return tool_payloads


def main():
    parser = argparse.ArgumentParser(description="SQL Agent integration test (sqlite)")
    parser.add_argument("--db", default=os.path.join("data", "sql", "demo.db"), help="sqlite db path")
    parser.add_argument("--thread", default="test-sql-agent-1", help="thread id (optional)")
    args = parser.parse_args()

    load_dotenv()
    if not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")):
        print("缺少 DEEPSEEK_API_KEY / OPENAI_API_KEY，跳过 SQL agent 调用测试。")
        sys.exit(0)

    db_path = args.db
    if not os.path.exists(db_path):
        print(f"数据库文件不存在：{db_path}")
        sys.exit(2)

    os.environ["SQL_DB_PATH"] = db_path

    agent = create_sql_agent()
    question = (
        "谁买的东西最多，并告诉我她花了多少钱，以及她买的东西价值最高的是什么"
    )
    payload = {"messages": [{"role": "user", "content": question}]}
    config = {"configurable": {"thread_id": args.thread}}

    res = agent.invoke(payload, config)
    if not isinstance(res, dict) or "messages" not in res:
        print("Agent 返回格式异常：", type(res), res)
        sys.exit(1)

    tool_payloads = extract_sql_query_tool_payload(res["messages"])
    if not tool_payloads:
        print("未捕获到 sql_db_query 的 ToolMessage，Agent 可能未调用数据库。")
        print("messages=", [type(m).__name__ for m in res["messages"]])
        sys.exit(2)

    payload0 = tool_payloads[-1]
    tool_counts = {}
    for m in res["messages"]:
        if isinstance(m, ToolMessage):
            tool_counts[m.name] = tool_counts.get(m.name, 0) + 1

    last_ai_text = ""
    for m in reversed(res["messages"]):
        if hasattr(m, "content") and isinstance(getattr(m, "content"), str) and getattr(m, "content"):
            last_ai_text = getattr(m, "content")
            break

    print("=== sql_db_query result ===")
    print(json.dumps(payload0, ensure_ascii=False, indent=2))
    print("\n=== tool counts ===")
    print(json.dumps(tool_counts, ensure_ascii=False, indent=2))
    if last_ai_text:
        print("\n=== agent answer ===")
        print(last_ai_text)
    print("\nSQL agent 测试通过。")


if __name__ == "__main__":
    main()
