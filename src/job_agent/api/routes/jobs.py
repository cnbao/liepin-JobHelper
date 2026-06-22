from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from job_agent.api.deps import get_db
from job_agent.schemas.common import MessageResponse, PaginatedResponse
from job_agent.schemas.job import (
    JobEvaluationResponse,
    JobListResponse,
    JobResponse,
    JobStatsResponse,
    JobStatusUpdate,
)

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    grade: Optional[str] = Query(None),
    choice_status: Optional[str] = Query(None),
    apply_status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """岗位列表（支持筛选、排序、分页）"""
    ...


@router.get("/jobs/stats", response_model=JobStatsResponse)
def job_stats(db: Session = Depends(get_db)):
    """岗位统计"""
    ...


@router.get("/jobs/candidates", response_model=JobListResponse)
def job_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """A/B 未投候选"""
    ...


@router.get("/jobs/paused", response_model=JobListResponse)
def job_paused(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """暂不投/pass 未投岗位"""
    ...


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """岗位详情"""
    ...


@router.get("/jobs/{job_id}/evaluation", response_model=JobEvaluationResponse)
def get_job_evaluation(job_id: int, db: Session = Depends(get_db)):
    """岗位评估详情（含各维度评分）"""
    ...


@router.patch("/jobs/{job_id}/status", response_model=MessageResponse)
def update_job_status(
    job_id: int,
    body: JobStatusUpdate,
    db: Session = Depends(get_db),
):
    """修改岗位状态（待定/暂不投/pass）"""
    ...


@router.post("/jobs/reevaluate-batch", response_model=MessageResponse)
def reevaluate_batch(db: Session = Depends(get_db)):
    """批量重评所有已评分岗位"""
    ...
