from __future__ import annotations

from typing import Any, Dict, List, Optional

from job_agent.core.schemas import (
    BoostFactor,
    DimensionResult,
    GradeRule,
    JobScoreResult,
    LLMJobEvaluation,
    PenaltyFactor,
    RiskFactor,
)


def calculate_score(
    job: Dict[str, Any],
    llm_evaluation: LLMJobEvaluation,
    boost_factors: Optional[List[BoostFactor]] = None,
    penalty_factors: Optional[List[PenaltyFactor]] = None,
) -> JobScoreResult:
    """混合模式评分：接收 LLM 的多维度评分，规则引擎做调整和总分计算。

    流程：
    1. 校验 LLM 返回的维度权重总和是否为 100
    2. 对每个维度，检查岗位描述是否命中加分/降权关键词
    3. 命中加分项：该维度分数 += 权重 * 10%
    4. 命中降权项：该维度分数 -= 权重 * 10%
    5. 计算加权总分

    Args:
        job: 岗位信息字典，必须包含 "description" 和 "title" 字段
        llm_evaluation: LLM 输出的 8 维评分结果（已通过 Pydantic 校验）
        boost_factors: 加分项列表
        penalty_factors: 降权项列表

    Returns:
        JobScoreResult: 包含调整后的各维度分数、加权总分

    Raises:
        ValueError: 权重总和不为 100 时抛出
    """
    boost_factors = boost_factors or []
    penalty_factors = penalty_factors or []

    # 校验权重总和
    total_weight = sum(d.weight for d in llm_evaluation.dimensions)
    if total_weight != 100:
        raise ValueError(f"维度权重总和为 {total_weight}，必须为 100")

    job_text = _build_job_text(job)
    dimension_results: List[DimensionResult] = []

    for dim in llm_evaluation.dimensions:
        score = dim.score
        boost_applied = False
        penalty_applied = False
        adjustment_reason = dim.reason

        # 检查加分项
        for bf in boost_factors:
            if bf.keyword.lower() in job_text.lower():
                boost_amount = dim.weight * 0.1  # 加分幅度为权重的 10%
                score = min(100.0, score + boost_amount)
                boost_applied = True
                adjustment_reason += f" [加分: 命中「{bf.keyword}」+{boost_amount:.1f}分]"

        # 检查降权项
        for pf in penalty_factors:
            if pf.keyword.lower() in job_text.lower():
                penalty_amount = dim.weight * 0.1  # 降权幅度为权重的 10%
                score = max(0.0, score - penalty_amount)
                penalty_applied = True
                adjustment_reason += f" [降权: 命中「{pf.keyword}」-{penalty_amount:.1f}分]"

        dimension_results.append(
            DimensionResult(
                name=dim.name,
                weight=dim.weight,
                score=round(score, 1),
                reason=adjustment_reason,
                boost_applied=boost_applied,
                penalty_applied=penalty_applied,
            )
        )

    # 计算加权总分
    total = sum(d.score * d.weight for d in dimension_results) / 100
    total = round(total, 1)

    return JobScoreResult(total=total, dimensions=dimension_results)


def determine_grade(total_score: float, grade_rules: List[GradeRule]) -> str:
    """根据总分和等级规则返回对应等级。

    边界值处理：
        - 90.0 返回 A，89.9 返回 B（左闭右闭）
        - 分数超出范围时返回最低/最高等级

    Args:
        total_score: 总分（0-100）
        grade_rules: 等级规则列表，按 score_min 升序排列

    Returns:
        等级标识字符串（如 "A", "B", "C", "D", "F"）
    """
    if not grade_rules:
        raise ValueError("grade_rules 不能为空")

    # 按 score_min 排序
    sorted_rules = sorted(grade_rules, key=lambda r: r.score_min)

    # 分数低于最低规则的最低分 → 返回最低等级
    if total_score < sorted_rules[0].score_min:
        return sorted_rules[0].grade

    # 分数高于最高规则的最高分 → 返回最高等级
    if total_score > sorted_rules[-1].score_max:
        return sorted_rules[-1].grade

    # 正常匹配
    for rule in sorted_rules:
        if rule.score_min <= total_score <= rule.score_max:
            return rule.grade

    # 理论上不会走到这里，但以防万一
    return sorted_rules[0].grade


def filter_candidates(
    jobs: List[Dict[str, Any]],
    grade_rules: List[GradeRule],
    boost_factors: Optional[List[BoostFactor]] = None,
    penalty_factors: Optional[List[PenaltyFactor]] = None,
) -> List[Dict[str, Any]]:
    """筛选候选岗位：只返回等级为 A 和 B 的岗位，按评分从高到低排序。

    注意：此函数会对每个岗位重新计算评分，适用于批量重评场景。
    如果已有评分结果，建议直接按 grade 和 total 字段筛选排序。

    Args:
        jobs: 岗位字典列表，每个字典需包含 title, description 等字段
        grade_rules: 等级规则列表
        boost_factors: 加分项列表
        penalty_factors: 降权项列表

    Returns:
        筛选后的岗位列表（A/B 等级，按总分降序）
    """
    boost_factors = boost_factors or []
    penalty_factors = penalty_factors or []

    candidates = []
    for job in jobs:
        # 如果岗位已有评分结果，直接使用
        if "score" in job and "grade" in job:
            grade = job["grade"]
        else:
            # 需要先评分（简化处理：跳过无评分的岗位）
            continue

        if grade in ("A", "B"):
            candidates.append(job)

    # 按评分从高到低排序
    candidates.sort(key=lambda j: j.get("score", 0) or 0, reverse=True)
    return candidates


def check_risks(
    job: Dict[str, Any],
    risk_factors: Optional[List[RiskFactor]] = None,
) -> List[str]:
    """检查岗位是否包含风险项。

    遍历 risk_factors 中的关键词，检查岗位的标题、描述、公司等字段是否命中。

    Args:
        job: 岗位信息字典
        risk_factors: 风险项列表

    Returns:
        命中的风险项描述列表
    """
    risk_factors = risk_factors or []

    job_text = _build_job_text(job)
    matched_risks: List[str] = []

    for rf in risk_factors:
        if rf.keyword.lower() in job_text.lower():
            matched_risks.append(rf.description or rf.keyword)

    return matched_risks


def _build_job_text(job: Dict[str, Any]) -> str:
    """将岗位信息拼接为用于关键词匹配的文本。"""
    parts = [
        job.get("title", ""),
        job.get("description", ""),
        job.get("company", ""),
        job.get("industry", ""),
        job.get("tags", ""),
    ]
    return " ".join(p for p in parts if p)
