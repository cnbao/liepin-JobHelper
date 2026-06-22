from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from job_agent.api.deps import get_db
from job_agent.schemas.common import MessageResponse
from job_agent.schemas.job import (
    JobEvaluationResponse,
    JobListResponse,
    JobResponse,
    JobStatsResponse,
    JobStatusUpdate,
)
from job_agent.services.job_service import (
    JobServiceError,
    get_candidates,
    get_job_evaluation,
    get_job_stats,
    get_jobs,
    get_paused_jobs,
    reevaluate_batch,
    update_job_status,
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
    sort_by: str = Query("updated_at", regex="^(score|salary_min|updated_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """岗位列表（支持筛选、排序、分页）"""
    result = get_jobs(
        db=db,
        keyword=keyword,
        grade=grade,
        choice_status=choice_status,
        apply_status=apply_status,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return JobListResponse(**result)


@router.get("/jobs/stats", response_model=JobStatsResponse)
def job_stats(db: Session = Depends(get_db)):
    """岗位统计"""
    stats = get_job_stats(db)
    return JobStatsResponse(**stats)


@router.get("/jobs/candidates", response_model=JobListResponse)
def job_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """A/B 未投候选"""
    items = get_candidates(db)
    total = len(items)
    page_items = items[(page - 1) * page_size : page * page_size]
    return JobListResponse(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/jobs/paused", response_model=JobListResponse)
def job_paused(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """暂不投/pass 未投岗位"""
    items = get_paused_jobs(db)
    total = len(items)
    page_items = items[(page - 1) * page_size : page * page_size]
    return JobListResponse(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """岗位详情"""
    from job_agent.db.models import Job

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"岗位 {job_id} 不存在")
    return job


@router.get("/jobs/{job_id}/evaluation", response_model=JobEvaluationResponse)
def get_job_evaluation_route(job_id: int, db: Session = Depends(get_db)):
    """岗位评估详情（含各维度评分）"""
    ev = get_job_evaluation(db, job_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"岗位 {job_id} 暂无评估记录")
    return JobEvaluationResponse(**ev)


@router.patch("/jobs/{job_id}/status", response_model=MessageResponse)
def update_job_status_route(
    job_id: int,
    body: JobStatusUpdate,
    db: Session = Depends(get_db),
):
    """修改岗位状态（待定/暂不投/pass）"""
    try:
        update_job_status(db, job_id, body.choice_status)
        return MessageResponse(
            message="状态已更新",
            detail=f"岗位 {job_id} 状态已更新为 {body.choice_status}",
        )
    except JobServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/reevaluate-batch", response_model=MessageResponse)
def reevaluate_batch_route(db: Session = Depends(get_db)):
    """批量重评所有已评分岗位"""
    count = reevaluate_batch(db)
    return MessageResponse(
        message="批量重评完成",
        detail=f"已重新评分 {count} 个岗位",
    )
