"""
命令行问答测试脚本
直接在终端与智能客服对话

使用方法：
    source ../.venv/bin/activate
    python scripts/ask.py
"""
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保无论从哪运行都能导入 app 包
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.rag_service import query


def main():
    print("智能客服助手已启动，输入 'quit' 或 'exit' 退出\n")

    while True:
        user_input = input("用户：").strip()
        if user_input.lower() in {"quit", "exit", "q"}:
            print("再见！")
            break
        if not user_input:
            continue

        try:
            result = query(user_input)
            answer = result.get("answer", "")
            print(f"\n客服：{answer}\n")
        except Exception as e:
            print(f"\n客服：出错了，{e}\n")


if __name__ == "__main__":
    main()
