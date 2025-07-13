import os
from openai import OpenAI

# 环境变量配置
LLM_API_KEY = None
LLM_BASE_URL = None
CHAT_MODEL_NAME = None


def init_llm(llm_base_url: str, llm_api_key: str, llm_model: str):
    global LLM_BASE_URL, LLM_API_KEY, CHAT_MODEL_NAME
    LLM_BASE_URL = llm_base_url
    LLM_API_KEY = llm_api_key
    CHAT_MODEL_NAME = llm_model


# Learn more about calling the LLM: https://the-pocket.github.io/PocketFlow/utility_function/llm.html
def call_llm(prompt, temperature: float = 0.2) -> str:
    """
    调用LLM（兼容OpenAI API）

    Args:
        prompt: 输入提示

    Returns:
        LLM响应文本
    """
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    r = client.chat.completions.create(
        model=CHAT_MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return r.choices[0].message.content


if __name__ == "__main__":
    # 测试原始调用
    prompt = "What is the meaning of life?"
    print("原始调用结果:", call_llm(prompt))
