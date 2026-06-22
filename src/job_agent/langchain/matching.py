"""简历与岗位匹配分析。

调用 LLM 分析简历与岗位的匹配程度，返回匹配度评分、优势和短板。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from job_agent.langchain import LLMNotAvailableError, _get_llm


def analyze_match(
    resume: Dict[str, Any],
    job: Dict[str, Any],
) -> Dict[str, Any]:
    """分析简历与岗位的匹配度。

    Args:
        resume: 简历信息字典，应包含 skills, experience, education, projects 等字段
        job: 岗位信息字典，应包含 title, description, requirements 等字段

    Returns:
        结构化匹配分析结果：
        {
            "match_score": int,         # 匹配度评分（0-100）
            "strengths": list[str],     # 优势列表
            "weaknesses": list[str],    # 短板列表
        }

    Raises:
        LLMNotAvailableError: LLM 不可用时抛出
    """
    llm = _get_llm(temperature=0.2)

    resume_text = _format_resume_for_prompt(resume)
    job_text = _format_job_for_prompt(job)

    system_prompt = SystemMessage(
        content="""你是一个专业的简历匹配分析师，负责评估简历与岗位的匹配程度。

请基于简历和岗位 JD，输出结构化 JSON：
{
    "match_score": 85,
    "strengths": ["优势1", "优势2", ...],
    "weaknesses": ["短板1", "短板2", ...]
}

要求：
- match_score 为 0-100 的整数
- strengths 列出 2-4 个主要优势（具体、有针对性）
- weaknesses 列出 1-3 个主要短板（具体、可改进）
- 评分要客观，避免虚高或虚低
- 只输出 JSON，不要包含其他内容"""
    )

    user_prompt = HumanMessage(
        content=f"""## 简历信息
{resume_text}

## 岗位 JD
{job_text}

请分析简历与岗位的匹配程度。"""
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
        result = {
            "match_score": 50,
            "strengths": [],
            "weaknesses": [],
        }

    # 确保必填字段存在
    result.setdefault("match_score", 50)
    result.setdefault("strengths", [])
    result.setdefault("weaknesses", [])

    # 校验 match_score 范围
    if not isinstance(result["match_score"], int) or not (0 <= result["match_score"] <= 100):
        result["match_score"] = 50

    return result


def _format_resume_for_prompt(resume: Dict[str, Any]) -> str:
    """将简历信息格式化为提示词友好的文本。"""
    lines = []

    if resume.get("name"):
        lines.append(f"姓名：{resume['name']}")
    if resume.get("title"):
        lines.append(f"当前职位：{resume['title']}")
    if resume.get("years_experience"):
        lines.append(f"工作经验：{resume['years_experience']}年")

    if resume.get("skills"):
        skills = resume["skills"]
        if isinstance(skills, list):
            lines.append(f"技能：{'、'.join(skills)}")
        else:
            lines.append(f"技能：{skills}")

    if resume.get("experience"):
        exp = resume["experience"]
        if isinstance(exp, list):
            for e in exp:
                company = e.get("company", "")
                role = e.get("role", "")
                desc = e.get("description", "")
                lines.append(f"- {company} | {role}：{desc[:200]}")
        else:
            lines.append(f"工作经历：{str(exp)[:500]}")

    if resume.get("education"):
        edu = resume["education"]
        if isinstance(edu, list):
            for e in edu:
                lines.append(f"- {e.get('school', '')} | {e.get('degree', '')} | {e.get('major', '')}")
        else:
            lines.append(f"教育背景：{str(edu)[:200]}")

    if resume.get("projects"):
        projects = resume["projects"]
        if isinstance(projects, list):
            for p in projects:
                lines.append(f"- 项目：{p.get('name', '')}：{str(p.get('description', ''))[:200]}")
        else:
            lines.append(f"项目经历：{str(projects)[:300]}")

    return "\n".join(lines) if lines else "无简历信息"


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
    ]
    if job.get("description"):
        lines.append(f"岗位描述：{job['description'][:1000]}")
    return "\n".join(lines)
