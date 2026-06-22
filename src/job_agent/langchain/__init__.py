"""LangChain 集成模块。

提供 AI 推荐理由生成和简历匹配分析功能。
"""

from __future__ import annotations

import os
from typing import Optional

from langchain_openai import ChatOpenAI


class LLMNotAvailableError(Exception):
    """LLM 不可用时抛出。"""

    pass


def _get_llm(temperature: float = 0.3) -> ChatOpenAI:
    """获取 LLM 实例。

    从环境变量读取 API key 和模型名称。
    OPENAI_API_KEY 为必填，MODEL_NAME 可选（默认 gpt-4o）。

    Raises:
        LLMNotAvailableError: API key 未配置时抛出
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMNotAvailableError(
            "OPENAI_API_KEY 未配置，请设置环境变量 OPENAI_API_KEY"
        )

    model = os.environ.get("MODEL_NAME", "gpt-4o")
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
    )
