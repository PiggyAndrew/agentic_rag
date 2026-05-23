import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.entrypoints.composition.kb import build_kb_usecase, default_kb_base_dir
from backend.tools.runtime import build_tools

def test_agent_tools():
    """测试 agent 调用 tools"""
    print("=" * 60)
    print("测试: Agent 调用 Tools")
    print("=" * 60)
    
    kb_usecase = build_kb_usecase(base_dir=default_kb_base_dir())
    kb_id = 1
    query = "Industry Standards"
    
    print(f"kb_id: {kb_id}")
    print(f"query: {query}")
    print(f"base_dir: {default_kb_base_dir()}")
    print()
    
    try:
        tools = build_tools(kb_usecase, kb_id)
        print(f"✓ 成功构建 {len(tools)} 个工具")
        print()
        
        for i, tool in enumerate(tools):
            print(f"工具 {i + 1}:")
            print(f"  name: {tool.name}")
            print(f"  description: {tool.description}")
            print(f"  type: {type(tool)}")
            print(f"  callable: {callable(tool)}")
            print()
        
        print("=" * 60)
        print("测试调用 query_knowledge_base 工具")
        print("=" * 60)
        
        query_tool = None
        for tool in tools:
            if tool.name == "query_knowledge_base":
                query_tool = tool
                break
        
        if query_tool is None:
            print("✗ 未找到 query_knowledge_base 工具")
            return
        
        print(f"✓ 找到工具: {query_tool.name}")
        print(f"  类型: {type(query_tool)}")
        print(f"  可调用: {callable(query_tool)}")
        print()
        
        print("尝试调用工具...")
        result = query_tool.func(query)
        print(f"✓ 工具调用成功")
        print(f"  返回结果长度: {len(result)}")
        print(f"  返回结果: {result[:500]}...")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()

if __name__ == "__main__":
    test_agent_tools()
