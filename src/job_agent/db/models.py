from datetime import datetime

from sqlalchemy import Column, Integer, Float, Text, DateTime, create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    liepin_job_id = Column(Text, nullable=False, unique=True)
    liepin_job_kind = Column(Text)
    title = Column(Text, nullable=False)
    company = Column(Text, nullable=False)
    location = Column(Text)
    salary_text = Column(Text)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    education = Column(Text)
    experience = Column(Text)
    description = Column(Text)
    industry = Column(Text)
    company_stage = Column(Text)
    company_size = Column(Text)
    tags = Column(Text)
    url = Column(Text)
    source = Column(Text, default="liepin")
    score = Column(Float)
    grade = Column(Text)
    choice_status = Column(Text, default="待定")
    apply_status = Column(Text, default="未投递")
    risk_level = Column(Text)
    is_agent_explore = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class JobEvaluation(Base):
    __tablename__ = "job_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, nullable=False)
    total_score = Column(Float, nullable=False)
    grade = Column(Text, nullable=False)
    summary = Column(Text)
    resume_match = Column(Text)
    level_strategy = Column(Text)
    salary_analysis = Column(Text)
    personal_advice = Column(Text)
    interview_prep = Column(Text)
    authenticity = Column(Text)
    evaluator = Column(Text, default="agent")
    evaluated_at = Column(DateTime, default=datetime.now)


class JobEvaluationDimension(Base):
    __tablename__ = "job_evaluation_dimensions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evaluation_id = Column(Integer, nullable=False)
    dimension_name = Column(Text, nullable=False)
    weight = Column(Float, nullable=False)
    score = Column(Float, nullable=False)
    reason = Column(Text)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, nullable=False)
    liepin_job_id = Column(Text)
    liepin_job_kind = Column(Text)
    status = Column(Text, default="pending")
    greeting = Column(Text)
    resume_strategy = Column(Text, default="online")
    pdf_path = Column(Text)
    mcp_response = Column(Text)
    mcp_success = Column(Integer)
    applied_at = Column(DateTime, default=datetime.now)


class SearchBatch(Base):
    __tablename__ = "search_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    search_time = Column(DateTime, default=datetime.now)
    keywords = Column(Text)
    address = Column(Text)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    education = Column(Text)
    experience = Column(Text)
    total_results = Column(Integer)
    deduped_count = Column(Integer)
    note = Column(Text)


class SearchResult(Base):
    __tablename__ = "search_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    search_batch_id = Column(Integer, nullable=False)
    job_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class PendingAction(Base):
    __tablename__ = "pending_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_type = Column(Text, nullable=False)
    payload = Column(Text, nullable=False)
    risk_level = Column(Text, default="low")
    status = Column(Text, default="pending")
    created_at = Column(DateTime, default=datetime.now)
    confirmed_at = Column(DateTime)
    executed_at = Column(DateTime)
    result = Column(Text)


class Preference(Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_roles = Column(Text, nullable=False, default="[]")
    preferred_cities = Column(Text, nullable=False, default="[]")
    preferred_districts = Column(Text, nullable=False, default="[]")
    salary_min = Column(Integer, default=18000)
    salary_max = Column(Integer, default=24000)
    salary_months = Column(Integer, default=12)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ScoringModelDimension(Base):
    __tablename__ = "scoring_model_dimensions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    weight = Column(Integer, nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)


class BoostFactor(Base):
    __tablename__ = "boost_factors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(Text, nullable=False, unique=True)
    category = Column(Text, default="general")
    created_at = Column(DateTime, default=datetime.now)


class PenaltyFactor(Base):
    __tablename__ = "penalty_factors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(Text, nullable=False, unique=True)
    category = Column(Text, default="general")
    created_at = Column(DateTime, default=datetime.now)


class RiskFactor(Base):
    __tablename__ = "risk_factors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(Text, nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class GradeRule(Base):
    __tablename__ = "grade_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grade = Column(Text, nullable=False, unique=True)
    score_min = Column(Integer, nullable=False)
    score_max = Column(Integer, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class PreferenceVersion(Base):
    __tablename__ = "preference_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot = Column(Text, nullable=False)
    change_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class ResumeFile(Base):
    __tablename__ = "resume_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, nullable=False)
    file_path = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    file_size = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
