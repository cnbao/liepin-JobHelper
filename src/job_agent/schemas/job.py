from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    """岗位响应"""

    id: int
    liepin_job_id: str
    liepin_job_kind: Optional[str] = None
    title: str
    company: str
    location: Optional[str] = None
    salary_text: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    company_stage: Optional[str] = None
    company_size: Optional[str] = None
    tags: Optional[str] = None
    url: Optional[str] = None
    source: str = "liepin"
    score: Optional[float] = None
    grade: Optional[str] = None
    choice_status: str = "待定"
    apply_status: str = "未投递"
    risk_level: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """岗位列表响应"""

    items: List[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class JobStatsResponse(BaseModel):
    """岗位统计响应"""

    total: int
    applied: int
    pending: int
    paused: int
    passed: int
    ab_candidates: int
    grade_distribution: dict


class JobEvaluationDimensionResponse(BaseModel):
    """评分维度响应"""

    id: int
    dimension_name: str
    weight: float
    score: float
    reason: Optional[str] = None

    model_config = {"from_attributes": True}


class JobEvaluationResponse(BaseModel):
    """岗位评估响应"""

    id: int
    job_id: int
    total_score: float
    grade: str
    summary: Optional[str] = None
    resume_match: Optional[str] = None
    level_strategy: Optional[str] = None
    salary_analysis: Optional[str] = None
    personal_advice: Optional[str] = None
    interview_prep: Optional[str] = None
    authenticity: Optional[str] = None
    evaluator: str = "agent"
    evaluated_at: datetime
    dimensions: List[JobEvaluationDimensionResponse] = []

    model_config = {"from_attributes": True}


class JobStatusUpdate(BaseModel):
    """岗位状态更新请求"""

    choice_status: str = Field(description="状态：待定/暂不投/pass")
