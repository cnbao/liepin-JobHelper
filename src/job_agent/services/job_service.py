"""岗位服务层。

实现岗位相关的业务逻辑，供 API 路由调用。
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from job_agent.core.rules import calculate_score, determine_grade
from job_agent.core.schemas import (
    BoostFactor as BoostFactorSchema,
    DimensionScore,
    GradeRule as GradeRuleSchema,
    LLMJobEvaluation,
    PenaltyFactor as PenaltyFactorSchema,
)
from job_agent.db.models import (
    BoostFactor,
    GradeRule,
    Job,
    JobEvaluation,
    JobEvaluationDimension,
    PenaltyFactor,
)


class JobServiceError(Exception):
    """岗位服务异常。"""

    pass


def get_jobs(
    db: Session,
    keyword: Optional[str] = None,
    grade: Optional[str] = None,
    choice_status: Optional[str] = None,
    apply_status: Optional[str] = None,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """岗位列表，支持多条件组合筛选、排序、分页。

    Args:
        db: 数据库会话
        keyword: 关键词（模糊匹配 title/company）
        grade: 等级筛选（如 "A", "B", "A/B"）
        choice_status: 用户选择状态
        apply_status: 投递状态
        sort_by: 排序字段（score / salary_min / updated_at）
        sort_order: 排序方向（asc / desc）
        page: 页码
        page_size: 每页数量

    Returns:
        {"items": [...], "total": int, "page": int, "page_size": int, "total_pages": int}
    """
    query = db.query(Job)

    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            Job.title.ilike(like) | Job.company.ilike(like)
        )
    if grade:
        grades = [g.strip() for g in grade.split("/")]
        query = query.filter(Job.grade.in_(grades))
    if choice_status:
        query = query.filter(Job.choice_status == choice_status)
    if apply_status:
        query = query.filter(Job.apply_status == apply_status)

    # 排序
    sort_map = {
        "score": Job.score,
        "salary_min": Job.salary_min,
        "updated_at": Job.updated_at,
    }
    sort_col = sort_map.get(sort_by, Job.updated_at)
    order_fn = desc if sort_order == "desc" else lambda c: c.asc()
    query = query.order_by(order_fn(sort_col), Job.id.desc())

    # 分页
    total = query.count()
    total_pages = max(1, math.ceil(total / page_size))
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_job_stats(db: Session) -> Dict[str, Any]:
    """岗位统计。

    Returns:
        {
            "total": int,
            "applied": int,
            "pending": int,        # 待定
            "paused": int,         # 暂不投
            "passed": int,         # pass
            "ab_candidates": int,  # A/B 未投候选
            "grade_distribution": { "A": int, "B": int, ... }
        }
    """
    total = db.query(Job).count()
    applied = db.query(Job).filter(Job.apply_status == "已投递").count()
    pending = db.query(Job).filter(Job.choice_status == "待定").count()
    paused = db.query(Job).filter(Job.choice_status == "暂不投").count()
    passed = db.query(Job).filter(Job.choice_status == "pass").count()

    # A/B 未投候选：等级 A/B、未投递、choice_status 不为 pass/暂不投
    ab_candidates = (
        db.query(Job)
        .filter(
            Job.grade.in_(["A", "B"]),
            Job.apply_status != "已投递",
            ~Job.choice_status.in_(["pass", "暂不投"]),
        )
        .count()
    )

    # 评分分布
    grade_distribution: Dict[str, int] = {}
    rows = db.query(Job.grade, func.count(Job.id)).group_by(Job.grade).all()
    for g, cnt in rows:
        if g:
            # 取等级首字母（如 "B+" → "B"）
            key = g[0].upper()
            grade_distribution[key] = grade_distribution.get(key, 0) + cnt

    return {
        "total": total,
        "applied": applied,
        "pending": pending,
        "paused": paused,
        "passed": passed,
        "ab_candidates": ab_candidates,
        "grade_distribution": grade_distribution,
    }


def get_candidates(db: Session) -> List[Job]:
    """A/B 未投候选。

    等级 A/B、未投递、choice_status 不为 pass/暂不投，按评分降序。
    """
    return (
        db.query(Job)
        .filter(
            Job.grade.in_(["A", "B"]),
            Job.apply_status != "已投递",
            ~Job.choice_status.in_(["pass", "暂不投"]),
        )
        .order_by(Job.score.desc().nullslast(), Job.id.desc())
        .all()
    )


def get_paused_jobs(db: Session) -> List[Job]:
    """暂不投/pass 且未投递的岗位。"""
    return (
        db.query(Job)
        .filter(
            Job.choice_status.in_(["暂不投", "pass"]),
            Job.apply_status != "已投递",
        )
        .order_by(Job.score.desc().nullslast(), Job.id.desc())
        .all()
    )


def get_job_evaluation(db: Session, job_id: int) -> Optional[Dict[str, Any]]:
    """岗位评估详情（含各维度评分明细）。

    Returns:
        评估字典，包含 total_score, grade, dimensions 等字段；
        如果不存在则返回 None。
    """
    ev = db.query(JobEvaluation).filter(JobEvaluation.job_id == job_id).first()
    if not ev:
        return None

    dims = (
        db.query(JobEvaluationDimension)
        .filter(JobEvaluationDimension.evaluation_id == ev.id)
        .order_by(JobEvaluationDimension.id)
        .all()
    )

    return {
        "id": ev.id,
        "job_id": ev.job_id,
        "total_score": ev.total_score,
        "grade": ev.grade,
        "summary": ev.summary,
        "resume_match": ev.resume_match,
        "level_strategy": ev.level_strategy,
        "salary_analysis": ev.salary_analysis,
        "personal_advice": ev.personal_advice,
        "interview_prep": ev.interview_prep,
        "authenticity": ev.authenticity,
        "evaluator": ev.evaluator,
        "evaluated_at": ev.evaluated_at,
        "dimensions": [
            {
                "id": d.id,
                "dimension_name": d.dimension_name,
                "weight": d.weight,
                "score": d.score,
                "reason": d.reason,
            }
            for d in dims
        ],
    }


def update_job_status(db: Session, job_id: int, choice_status: str) -> Job:
    """修改岗位状态。

    Args:
        db: 数据库会话
        job_id: 岗位 ID
        choice_status: 目标状态（待定/暂不投/pass）

    Returns:
        更新后的 Job 实例

    Raises:
        JobServiceError: 已投递岗位不可修改状态 / choice_status 不合法
    """
    valid_statuses = {"待定", "暂不投", "pass"}
    if choice_status not in valid_statuses:
        raise JobServiceError(
            f"choice_status 不合法: {choice_status}，必须为 {valid_statuses}"
        )

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise JobServiceError(f"岗位 {job_id} 不存在")

    if job.apply_status == "已投递":
        raise JobServiceError(f"岗位 {job_id} 已投递，不可修改状态")

    job.choice_status = choice_status
    db.commit()
    db.refresh(job)
    return job


def reevaluate_batch(db: Session) -> int:
    """批量重评所有已评分岗位。

    读取所有已有评分记录的岗位，调用 rules.calculate_score 重新计算评分。

    Returns:
        重评的岗位数量
    """
    # 读取加分项、降权项、等级规则
    boost_factors = db.query(BoostFactor).all()
    penalty_factors = db.query(PenaltyFactor).all()
    grade_rules = db.query(GradeRule).all()

    # 转换为 rules 模块需要的格式（Pydantic 模型）
    boost_list = [
        BoostFactorSchema(keyword=bf.keyword, category=bf.category)
        for bf in boost_factors
    ]
    penalty_list = [
        PenaltyFactorSchema(keyword=pf.keyword, category=pf.category)
        for pf in penalty_factors
    ]
    grade_list = [
        GradeRuleSchema(grade=gr.grade, score_min=gr.score_min, score_max=gr.score_max)
        for gr in grade_rules
    ]

    # 查找所有有评估记录的岗位
    eval_job_ids = (
        db.query(JobEvaluation.job_id).distinct().subquery()
    )
    jobs = db.query(Job).filter(Job.id.in_(eval_job_ids)).all()

    count = 0
    for job in jobs:
        ev = (
            db.query(JobEvaluation)
            .filter(JobEvaluation.job_id == job.id)
            .first()
        )
        if not ev:
            continue

        # 读取维度评分
        dims = (
            db.query(JobEvaluationDimension)
            .filter(JobEvaluationDimension.evaluation_id == ev.id)
            .all()
        )
        if not dims:
            continue

        # 构建 LLMJobEvaluation
        llm_eval = LLMJobEvaluation(
            dimensions=[
                DimensionScore(
                    name=d.dimension_name,
                    weight=int(d.weight),
                    score=d.score,
                    reason=d.reason or "",
                )
                for d in dims
            ],
            summary=ev.summary or "",
        )

        # 构建 job dict
        job_dict = {
            "title": job.title or "",
            "description": job.description or "",
            "company": job.company or "",
            "industry": job.industry or "",
            "tags": job.tags or "",
        }

        try:
            result = calculate_score(
                job=job_dict,
                llm_evaluation=llm_eval,
                boost_factors=boost_list,
                penalty_factors=penalty_list,
            )
        except ValueError:
            continue

        # 确定等级
        if grade_list:
            grade = determine_grade(result.total, grade_list)
        else:
            grade = ev.grade

        # 更新岗位
        job.score = result.total
        job.grade = grade
        db.add(job)
        count += 1

    db.commit()
    return count
