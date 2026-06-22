from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PreferenceResponse(BaseModel):
    """偏好配置响应"""

    id: int
    target_roles: List[str] = Field(default_factory=list)
    preferred_cities: List[str] = Field(default_factory=list)
    preferred_districts: List[str] = Field(default_factory=list)
    salary_min: int = 18000
    salary_max: int = 24000
    salary_months: int = 12
    updated_at: datetime

    model_config = {"from_attributes": True}


class PreferenceUpdate(BaseModel):
    """偏好配置更新请求"""

    target_roles: Optional[List[str]] = None
    preferred_cities: Optional[List[str]] = None
    preferred_districts: Optional[List[str]] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_months: Optional[int] = None


class ScoringModelDimensionResponse(BaseModel):
    """评分模型维度响应"""

    id: int
    name: str
    weight: int
    sort_order: int

    model_config = {"from_attributes": True}


class ScoringModelResponse(BaseModel):
    """评分模型响应"""

    dimensions: List[ScoringModelDimensionResponse]


class ScoringModelDimensionUpdate(BaseModel):
    """评分模型维度更新"""

    name: str
    weight: int = Field(ge=1, le=100)
    sort_order: int = 0
