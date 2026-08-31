# -*- coding: utf-8 -*-
"""复制数据转CSV工具（剪贴板模式）：制表符分隔转逗号分隔

用法：
1. 从股票软件/Excel 复制数据（制表符分隔）
2. 运行本脚本
3. 转换结果自动写回剪贴板，直接粘贴即可

示例输入：
代码\t名称(55)
000712\t锦龙股份

示例输出：
代码,名称(55)
000712,锦龙股份
"""
import sys

try:
    import pyperclip
except ImportError:
    print("缺少依赖：pip install pyperclip")
    sys.exit(1)


def convert(text: str) -> str:
    """将制表符分隔文本转为逗号分隔，跳过空行，压缩连续制表符"""
    lines = []
    for line in text.splitlines():
        line = line.rstrip("\t")
        if not line.strip():
            continue
        cols = [c.strip() for c in line.split("\t") if c.strip()]
        lines.append(",".join(cols))
    return "\n".join(lines)


def main():
    text = pyperclip.paste()
    if not text or not text.strip():
        print("剪贴板为空，请先复制数据再运行。")
        sys.exit(1)

    if "\t" not in text:
        print("剪贴板内容中没有制表符，无需转换。")
        sys.exit(0)

    result = convert(text)
    pyperclip.copy(result)
    print("转换完成，结果已写回剪贴板：\n")
    print(result)


if __name__ == "__main__":
    main()
