import os
import dspy
from openai import OpenAI

# 环境变量配置
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") 
CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME", "gpt-4o")

# Learn more about calling the LLM: https://the-pocket.github.io/PocketFlow/utility_function/llm.html
def call_llm(prompt):    
    """
    调用LLM（兼容OpenAI API）
    
    Args:
        prompt: 输入提示
        
    Returns:
        LLM响应文本
    """
    client = OpenAI(api_key=LLM_API_KEY or "your-api-key")
    r = client.chat.completions.create(
        model=CHAT_MODEL_NAME,
        messages=[{"role": "user", "content": prompt}]
    )
    return r.choices[0].message.content

def call_llm_with_dspy(lm, prompt):
    """
    使用dspy调用LLM
    
    Args:
        lm: dspy LM对象
        prompt: 输入提示
        
    Returns:
        LLM响应文本
    """
    response = lm(prompt)
    return response[0] if isinstance(response, list) else response

def summarize_paper(lm, paper_text):
    """
    论文摘要生成
    
    Args:
        lm: dspy LM对象
        paper_text: 论文文本
        
    Returns:
        摘要文本
    """
    prompt = f"用中文帮我介绍一下这篇文章: {paper_text}"
    return call_llm_with_dspy(lm, prompt)

def generate_daily_summary(lm, combined_text):
    """
    生成日报摘要
    
    Args:
        lm: dspy LM对象
        combined_text: 组合的论文文本
        
    Returns:
        日报摘要
    """
    prompt = (
        f"请将以下论文汇总信息整理成一份结构清晰的每日简报（使用中文）：\n{combined_text}\n"
        "要求：\n1. 分领域总结研究趋势\n2. 用简洁的bullet points呈现\n3. 推荐3篇最值得阅读的论文并说明理由\n4. 领域相关趋势列出相关论文标题\n5. 论文标题用英文表达\n"
        "6.只输出分领域研究趋势总结和推荐阅读论文，不需要输出其他内容\n7.论文标题输出时不要省略"
    )
    return call_llm_with_dspy(lm, prompt)

def setup_dspy_lm():
    """
    设置dspy LM对象
    
    Returns:
        配置好的dspy LM对象
    """
    if not LLM_API_KEY or not LLM_BASE_URL or not CHAT_MODEL_NAME:
        raise ValueError("请设置环境变量: LLM_API_KEY, LLM_BASE_URL, CHAT_MODEL_NAME")
    
    lm = dspy.LM("openai/" + CHAT_MODEL_NAME, api_base=LLM_BASE_URL, api_key=LLM_API_KEY, temperature=0.2)
    dspy.configure(lm=lm)
    return lm
    
if __name__ == "__main__":
    # 测试原始调用
    prompt = "What is the meaning of life?"
    print("原始调用结果:", call_llm(prompt))
    
    # 测试dspy调用
    try:
        lm = setup_dspy_lm()
        print("dspy调用结果:", call_llm_with_dspy(lm, prompt))
    except Exception as e:
        print(f"dspy调用失败: {e}")
