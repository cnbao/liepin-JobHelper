from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class DimensionScore(BaseModel):
    """单个维度的 LLM 评分结果"""

    name: str = Field(description="维度名称")
    weight: int = Field(description="权重（总和应为 100）", ge=1, le=100)
    score: float = Field(description="LLM 对该维度的评分（0-100）", ge=0.0, le=100.0)
    reason: str = Field(description="评分理由", alias="description")

    model_config = {"populate_by_name": True}


class LLMJobEvaluation(BaseModel):
    """LLM 多维度评分输出的约束模型"""

    dimensions: List[DimensionScore] = Field(
        description="8 维评分列表",
        min_length=8,
        max_length=8,
    )
    summary: str = Field(description="综合评估摘要")
    resume_match: Optional[str] = Field(None, description="简历匹配度分析")
    level_strategy: Optional[str] = Field(None, description="定级策略建议")
    salary_analysis: Optional[str] = Field(None, description="薪酬竞争力分析")
    personal_advice: Optional[str] = Field(None, description="个人建议")
    interview_prep: Optional[str] = Field(None, description="面试准备建议")
    authenticity: Optional[str] = Field(None, description="真实性核查")

    @field_validator("dimensions")
    @classmethod
    def validate_dimension_names(cls, v: List[DimensionScore]) -> List[DimensionScore]:
        """验证 8 维名称是否匹配预期维度"""
        expected_names = {
            "角色匹配",
            "地点偏好",
            "工作生活平衡",
            "薪酬竞争力",
            "公司口碑/稳定性",
            "成长潜力",
            "行业匹配",
            "福利完整度",
        }
        actual_names = {d.name for d in v}
        if actual_names != expected_names:
            missing = expected_names - actual_names
            extra = actual_names - expected_names
            parts = []
            if missing:
                parts.append(f"缺少维度: {missing}")
            if extra:
                parts.append(f"多余维度: {extra}")
            raise ValueError("; ".join(parts))
        return v


class GradeRule(BaseModel):
    """等级规则"""

    grade: str = Field(description="等级标识（A/B/C/D/F）")
    score_min: float = Field(description="最低分数（含）")
    score_max: float = Field(description="最高分数（含）")


class BoostFactor(BaseModel):
    """加分项"""

    keyword: str = Field(description="关键词")
    category: str = Field(default="general", description="分类")


class PenaltyFactor(BaseModel):
    """降权项"""

    keyword: str = Field(description="关键词")
    category: str = Field(default="general", description="分类")


class RiskFactor(BaseModel):
    """风险项"""

    keyword: str = Field(description="关键词")
    description: Optional[str] = Field(None, description="风险描述")


class DimensionResult(BaseModel):
    """规则引擎输出的单维度评分结果"""

    name: str
    weight: int
    score: float = Field(description="调整后的分数（0-100）")
    reason: str
    boost_applied: bool = Field(default=False, description="是否命中了加分项")
    penalty_applied: bool = Field(default=False, description="是否命中了降权项")


class JobScoreResult(BaseModel):
    """规则引擎输出的岗位评分结果"""

    total: float = Field(description="加权总分（0-100）")
    dimensions: List[DimensionResult]
    grade: Optional[str] = Field(None, description="等级")
    risk_items: List[str] = Field(default_factory=list, description="命中的风险项")
