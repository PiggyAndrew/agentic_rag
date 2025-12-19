import argparse
import os
import sys

# 将项目根目录加入模块搜索路径，确保可导入顶层包 `kb`
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from kb import read_excel_text


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
        "--excel",
        default=r"test\\testfiles\\excel\\CAT_Sub CAT Code Master List.xlsx",
        help="excel 文件路径",
    )
    parser.add_argument(
        "--out_dir",
        default=r"test\\outputs\\excel",
        help="输出目录（写入读取结果到文件）",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.excel):
        print(f"文件不存在: {args.excel}")
        sys.exit(1)

    text = read_excel_text(args.excel)
    print_summary(text)

    os.makedirs(args.out_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(args.excel))[0]
    out_path = os.path.join(args.out_dir, f"{base_name}.md")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        if text and not text.endswith("\n"):
            f.write("\n")
    print(f"已写入输出文件: {out_path}")


if __name__ == "__main__":
    main()
