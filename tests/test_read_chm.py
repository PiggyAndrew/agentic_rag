import argparse
import os
import sys

# 将项目根目录加入模块搜索路径，确保可导入顶层包 `kb`
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from kb import read_chm_text


def print_summary(text: str, preview_len: int = 500) -> None:
    """在控制台打印读取结果摘要与示例片段"""
    total_chars = len(text)
    total_lines = text.count("\n") + (1 if text else 0)
    print("读取结果摘要:")
    print(f"- 字符数: {total_chars}")
    print(f"- 行数: {total_lines}")
    sample = (text[:preview_len] + "...") if len(text) > preview_len else text
    print("示例片段:")
    print(sample)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--chm",
        default=r"test/testfiles/RevitAPI.chm",
        help="CHM 文件路径",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.chm):
        print(f"文件不存在: {args.chm}")
        sys.exit(1)

    text = read_chm_text(args.chm)
    print_summary(text)


if __name__ == "__main__":
    main()