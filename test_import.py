
import os
import sys

# Mock API KEY to avoid immediate error if it's just checking for existence
os.environ["DEEPSEEK_API_KEY"] = "sk-mock-key"

try:
    from app.agent import agent
    print(f"Successfully imported agent. Type: {type(agent)}")
    if agent is None:
        print("Agent is None!")
    else:
        print("Agent is ready.")
except Exception as e:
    print(f"Error importing agent: {e}")
