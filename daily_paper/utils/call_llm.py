import os
import asyncio
from openai import OpenAI, AsyncOpenAI

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
def call_llm(prompt, temperature: float = 0.2, return_usage: bool = False):
    """
    调用LLM（兼容OpenAI API）

    Args:
        prompt: 输入提示
        temperature: 温度参数
        return_usage: 是否返回token使用统计

    Returns:
        如果return_usage=False: LLM响应文本
        如果return_usage=True: (LLM响应文本, token使用统计字典)
    """
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    r = client.chat.completions.create(
        model=CHAT_MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    
    response_text = r.choices[0].message.content
    
    if not return_usage:
        return response_text
    
    # 提取token使用信息
    usage_info = {
        "prompt_tokens": r.usage.prompt_tokens if r.usage else 0,
        "completion_tokens": r.usage.completion_tokens if r.usage else 0,
        "total_tokens": r.usage.total_tokens if r.usage else 0,
        "model": CHAT_MODEL_NAME
    }
    
    return response_text, usage_info


def call_llm_with_usage(prompt, temperature: float = 0.2):
    """
    调用LLM并返回token使用统计的便捷函数
    
    Args:
        prompt: 输入提示
        temperature: 温度参数
        
    Returns:
        (LLM响应文本, token使用统计字典)
    """
    return call_llm(prompt, temperature=temperature, return_usage=True)


# 全局AsyncClient实例（线程安全）
_async_client = None

def get_async_client():
    """获取共享的AsyncClient实例"""
    global _async_client
    if _async_client is None:
        _async_client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    return _async_client

async def close_async_client():
    """关闭AsyncClient实例"""
    global _async_client
    if _async_client is not None:
        await _async_client.aclose()
        _async_client = None

async def call_llm_async(prompt, temperature: float = 0.2, return_usage: bool = False):
    """
    异步调用LLM（兼容OpenAI API）
    
    Args:
        prompt: 输入提示
        temperature: 温度参数
        return_usage: 是否返回token使用统计
        
    Returns:
        如果return_usage=False: LLM响应文本
        如果return_usage=True: (LLM响应文本, token使用统计字典)
    """
    client = get_async_client()
    r = await client.chat.completions.create(
        model=CHAT_MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    
    response_text = r.choices[0].message.content
    
    if not return_usage:
        return response_text
    
    # 提取token使用信息
    usage_info = {
        "prompt_tokens": r.usage.prompt_tokens if r.usage else 0,
        "completion_tokens": r.usage.completion_tokens if r.usage else 0,
        "total_tokens": r.usage.total_tokens if r.usage else 0,
        "model": CHAT_MODEL_NAME
    }
    
    return response_text, usage_info


async def call_llm_with_usage_async(prompt, temperature: float = 0.2):
    """
    异步调用LLM并返回token使用统计的便捷函数
    
    Args:
        prompt: 输入提示
        temperature: 温度参数
        
    Returns:
        (LLM响应文本, token使用统计字典)
    """
    return await call_llm_async(prompt, temperature=temperature, return_usage=True)


if __name__ == "__main__":
    # 测试原始调用
    prompt = "What is the meaning of life?"
    print("原始调用结果:", call_llm(prompt))
