from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ApplicationResponse(BaseModel):
    """投递记录响应"""

    id: int
    job_id: int
    liepin_job_id: Optional[str] = None
    liepin_job_kind: Optional[str] = None
    status: str = "pending"
    greeting: Optional[str] = None
    resume_strategy: str = "online"
    pdf_path: Optional[str] = None
    mcp_response: Optional[str] = None
    mcp_success: Optional[int] = None
    applied_at: datetime

    model_config = {"from_attributes": True}


class ApplicationListResponse(BaseModel):
    """投递记录列表响应"""

    items: List[ApplicationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ApplyPreviewRequest(BaseModel):
    """投递预览请求"""

    job_ids: List[int]
    resume_strategy: str = "online"  # online 或 pdf


class ApplyPreviewItem(BaseModel):
    """投递预览项"""

    job_id: int
    title: str
    company: str
    salary_text: Optional[str] = None
    grade: Optional[str] = None
    resume_strategy: str


class ApplyPreviewResponse(BaseModel):
    """投递预览响应"""

    items: List[ApplyPreviewItem]


class ApplyConfirmRequest(BaseModel):
    """投递确认请求"""

    items: List[ApplyPreviewItem]
    greeting: Optional[str] = None
