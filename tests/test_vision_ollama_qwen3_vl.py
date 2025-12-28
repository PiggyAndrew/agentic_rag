import os
import sys
import json

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.agents.vision_ollama_qwen3_vl import create_vision_agent, OllamaVisionAgent

def test_ollama_qwen3_vl_image():
    agent = create_vision_agent()
    img = os.path.join(
        ROOT_DIR,
        "tests",
        "testfiles",
        "Attachment-E---BIM-Guide-for-Facilities-Upkeep_Ver2.0_Jun21-20211007-113450.pdf-48-0.png",
    )
    prompt = "请用中文描述这张图片的主要内容和结构。"
    result = agent.analyze_image(img, prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    assert isinstance(result, dict)

def main():
    test_ollama_qwen3_vl_image()


if __name__ == "__main__":
    main()

