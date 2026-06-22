"""AI 推荐理由生成。

调用 LLM 为岗位生成推荐理由、风险分析和建议动作。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from job_agent.langchain import LLMNotAvailableError, _get_llm


def generate_recommendation(
    job: Dict[str, Any],
    preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """为岗位生成 AI 推荐理由。

    Args:
        job: 岗位信息字典，应包含 title, company, description, salary_text,
             location, education, experience, industry 等字段
        preferences: 用户偏好字典，可选，用于个性化推荐

    Returns:
        结构化推荐结果：
        {
            "reason": str,          # 推荐理由
            "risks": list[str],     # 风险点列表
            "suggested_action": str # 建议动作（强烈推荐投递/可投递/谨慎投递/不推荐）
        }

    Raises:
        LLMNotAvailableError: LLM 不可用时抛出
    """
    llm = _get_llm(temperature=0.3)

    # 构建岗位信息文本
    job_text = _format_job_for_prompt(job)

    # 构建偏好文本
    pref_text = _format_preferences_for_prompt(preferences or {})

    system_prompt = SystemMessage(
        content="""你是一个专业的求职顾问，负责为求职者分析岗位并提供推荐建议。

请基于岗位信息和用户偏好，输出结构化 JSON：
{
    "reason": "详细的推荐理由（2-4 句话，说明为什么推荐/不推荐该岗位）",
    "risks": ["风险点1", "风险点2", ...],
    "suggested_action": "建议动作（必须为以下之一：强烈推荐投递、可投递、谨慎投递、不推荐）"
}

要求：
- reason 要具体、有针对性，结合岗位和用户背景
- risks 列出 1-3 个主要风险点
- suggested_action 基于岗位匹配度、薪资、公司、风险等因素综合判断
- 只输出 JSON，不要包含其他内容"""
    )

    user_prompt = HumanMessage(
        content=f"""## 岗位信息
{job_text}

## 用户偏好
{pref_text}

请分析该岗位并给出推荐建议。"""
    )

    response = llm.invoke([system_prompt, user_prompt])
    content = response.content.strip()

    # 清理可能的 markdown 代码块标记
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # LLM 返回非 JSON 时的 fallback
        result = {
            "reason": content,
            "risks": [],
            "suggested_action": "可投递",
        }

    # 确保必填字段存在
    result.setdefault("reason", "")
    result.setdefault("risks", [])
    result.setdefault("suggested_action", "可投递")

    return result


def _format_job_for_prompt(job: Dict[str, Any]) -> str:
    """将岗位信息格式化为提示词友好的文本。"""
    lines = [
        f"岗位名称：{job.get('title', '未知')}",
        f"公司：{job.get('company', '未知')}",
        f"地点：{job.get('location', '未知')}",
        f"薪资：{job.get('salary_text', '未知')}",
        f"学历要求：{job.get('education', '未知')}",
        f"经验要求：{job.get('experience', '未知')}",
        f"行业：{job.get('industry', '未知')}",
        f"公司阶段：{job.get('company_stage', '未知')}",
        f"公司规模：{job.get('company_size', '未知')}",
        f"标签：{job.get('tags', '未知')}",
    ]
    if job.get("description"):
        lines.append(f"岗位描述：{job['description'][:500]}")
    return "\n".join(lines)


def _format_preferences_for_prompt(preferences: Dict[str, Any]) -> str:
    """将用户偏好格式化为提示词友好的文本。"""
    parts = []
    if preferences.get("target_roles"):
        roles = preferences["target_roles"]
        if isinstance(roles, list):
            parts.append(f"目标职位：{'、'.join(roles)}")
        else:
            parts.append(f"目标职位：{roles}")
    if preferences.get("salary_min") or preferences.get("salary_max"):
        parts.append(
            f"期望薪资：{preferences.get('salary_min', '不限')}k-{preferences.get('salary_max', '不限')}k"
        )
    if preferences.get("preferred_cities"):
        cities = preferences["preferred_cities"]
        if isinstance(cities, list):
            parts.append(f"偏好城市：{'、'.join(cities)}")
        else:
            parts.append(f"偏好城市：{cities}")
    return "\n".join(parts) if parts else "无特殊偏好"
