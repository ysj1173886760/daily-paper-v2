import os
from openai import OpenAI

# 环境变量配置
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME", "gpt-4o")

# Learn more about calling the LLM: https://the-pocket.github.io/PocketFlow/utility_function/llm.html
def call_llm(prompt) -> str:
    """
    调用LLM（兼容OpenAI API）

    Args:
        prompt: 输入提示

    Returns:
        LLM响应文本
    """
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    r = client.chat.completions.create(
        model=CHAT_MODEL_NAME, messages=[{"role": "user", "content": prompt}]
    )
    return r.choices[0].message.content


if __name__ == "__main__":
    # 测试原始调用
    prompt = "What is the meaning of life?"
    print("原始调用结果:", call_llm(prompt))
