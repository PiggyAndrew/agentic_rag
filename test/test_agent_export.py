import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import api.agent as agent_mod


def main():
    obj = getattr(agent_mod, "agent", None)
    if obj is None:
        print("agent 变量不存在或为 None")
        sys.exit(1)
    if not hasattr(obj, "invoke"):
        print("agent 不具有 invoke 方法，可能不是可调用的 Agent/Graph")
        sys.exit(2)
    print("agent 导出存在且具备 invoke 能力。")


if __name__ == "__main__":
    main()