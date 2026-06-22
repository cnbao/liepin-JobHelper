"""从 Markdown 文件导入数据到数据库。

用法：
    python -m scripts.import_from_md              # 执行导入
    python -m scripts.import_from_md --dry-run     # 预览导入结果
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.job_agent.db.models import Application, Job, JobEvaluation, JobEvaluationDimension
from src.job_agent.db.session import SessionLocal, ensure_db_dir
from src.job_agent.services.markdown_loader import (
    parse_apply_log_md,
    parse_job_detail_md,
    parse_job_md,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

WORKSPACE = Path(os.environ.get("WORKSPACE_DIR", str(PROJECT_ROOT)))


def _ensure_unique_key(session, model_class, liepin_job_id: str, id_field="liepin_job_id"):
    """查找已存在的记录，返回 (existing_id, is_update)；不存在则返回 (None, False)。"""
    existing = session.query(model_class).filter_by(**{id_field: liepin_job_id}).first()
    return (existing.id, True) if existing else (None, False)


def import_jobs(session, jobs_data: List[Dict]):
    """导入 job.md 岗位主索引。"""
    imported = 0
    skipped = 0
    for job in jobs_data:
        job_id = job["job_id"]
        # 检查是否已存在
        existing = session.query(Job).filter_by(liepin_job_id=job_id).first()
        if existing:
            skipped += 1
            continue

        score_val = None
        try:
            score_val = float(job["score"]) if job["score"] else None
        except (ValueError, TypeError):
            pass

        applied = job.get("applied", "否") == "是"
        apply_status = "已投递" if applied else "未投递"
        choice_status = job.get("choice", "待定")
        if choice_status in ("暂不投", "pass"):
            choice_status = choice_status

        new_job = Job(
            liepin_job_id=job_id,
            liepin_job_kind=job.get("job_type"),
            title=job.get("title", ""),
            company=job.get("company", ""),
            score=score_val,
            grade=job.get("grade", ""),
            choice_status=choice_status,
            apply_status=apply_status,
            url="",  # job.md 中没有 URL
        )
        session.add(new_job)
        imported += 1

    session.commit()
    return imported, skipped


def import_evaluations(session, eval_data: List[Dict]):
    """导入 job_detail.md 评估记录。"""
    imported = 0
    skipped = 0
    for ev in eval_data:
        liepin_job_id = ev.get("liepin_job_id") or ev.get("job_id")
        if not liepin_job_id:
            continue

        # 查找对应的 job 记录
        job = session.query(Job).filter_by(liepin_job_id=liepin_job_id).first()
        if not job:
            logger.warning(f"评估记录 {liepin_job_id} 找不到对应岗位，跳过")
            skipped += 1
            continue

        score_val = None
        try:
            score_val = float(ev.get("score", 0)) if ev.get("score") else None
        except (ValueError, TypeError):
            pass

        grade = ev.get("grade", "")

        # 检查评估是否已存在
        existing_eval = session.query(JobEvaluation).filter_by(job_id=job.id).first()
        if existing_eval:
            skipped += 1
            continue

        new_eval = JobEvaluation(
            job_id=job.id,
            total_score=score_val or 0,
            grade=grade,
            summary=ev.get("title"),
            evaluator="agent",
        )
        session.add(new_eval)
        session.flush()  # 获取 evaluation_id

        # 导入维度评分
        dimensions = ev.get("dimensions", [])
        for dim in dimensions:
            weight = dim.get("weight", "0")
            score = dim.get("score", "0")
            try:
                new_dim = JobEvaluationDimension(
                    evaluation_id=new_eval.id,
                    dimension_name=dim.get("dimension_name", ""),
                    weight=float(weight) if weight else 0,
                    score=float(score) if score else 0,
                    reason=dim.get("reason", ""),
                )
                session.add(new_dim)
            except (ValueError, TypeError):
                pass

        imported += 1

    session.commit()
    return imported, skipped


def import_applications(session, apps_data: List[Dict]):
    """导入投递记录。"""
    imported = 0
    skipped = 0
    for app in apps_data:
        liepin_job_id = app.get("liepin_job_id") or app.get("job_id")
        if not liepin_job_id:
            continue

        # 查找对应的 job 记录
        job = session.query(Job).filter_by(liepin_job_id=liepin_job_id).first()
        if not job:
            logger.warning(f"投递记录 {liepin_job_id} 找不到对应岗位，跳过")
            skipped += 1
            continue

        # 检查是否已存在
        existing = session.query(Application).filter_by(job_id=job.id).first()
        if existing:
            skipped += 1
            continue

        # 解析投递结果
        status_text = app.get("status", "")
        if "成功" in status_text:
            status = "success"
        elif "失败" in status_text or "待确认" in status_text:
            status = "failed"
        else:
            status = "pending"

        new_app = Application(
            job_id=job.id,
            liepin_job_id=liepin_job_id,
            status=status,
            greeting=app.get("greeting"),
            pdf_path=app.get("pdf_path"),
            applied_at=datetime.now(),
        )
        session.add(new_app)
        imported += 1

    session.commit()
    return imported, skipped


def dry_run_preview(jobs_data, eval_data, apps_data):
    """预览导入结果，不写入数据库。"""
    print("\n=== 导入预览 (DRY RUN) ===\n")

    print(f"[job.md] 岗位记录: {len(jobs_data)} 条")
    for job in jobs_data[:5]:
        print(f"  - Job ID: {job['job_id']}, {job.get('title', '')[:30]}, {job.get('company', '')}")
    if len(jobs_data) > 5:
        print(f"  ... 还有 {len(jobs_data) - 5} 条")

    print(f"\n[job_detail.md] 评估记录: {len(eval_data)} 条")
    for ev in eval_data[:5]:
        liepin_id = ev.get('liepin_job_id') or ev.get('job_id', '')
        print(f"  - liepin_job_id: {liepin_id}, {ev.get('title', '')[:30]}, {ev.get('company', '')}")
    if len(eval_data) > 5:
        print(f"  ... 还有 {len(eval_data) - 5} 条")

    print(f"\n[job_apply_log.md] 投递记录: {len(apps_data)} 条")
    for app in apps_data[:5]:
        liepin_id = app.get('liepin_job_id') or app.get('job_id', '')
        print(f"  - liepin_job_id: {liepin_id}, {app.get('title', '')[:30]}, {app.get('company', '')}")
    if len(apps_data) > 5:
        print(f"  ... 还有 {len(apps_data) - 5} 条")

    print("\n=== 预览结束 ===\n")


def main():
    parser = argparse.ArgumentParser(description="从 Markdown 文件导入数据到数据库")
    parser.add_argument("--dry-run", action="store_true", help="预览导入结果，不写入数据库")
    args = parser.parse_args()

    ensure_db_dir()
    session = SessionLocal()

    try:
        # 解析 Markdown 文件
        job_md = WORKSPACE / "job.md"
        detail_md = WORKSPACE / "job_detail.md"
        apply_md = WORKSPACE / "job_apply_log.md"

        jobs_data = []
        eval_data = []
        apps_data = []

        if job_md.exists():
            jobs_data = parse_job_md(job_md.read_text(encoding="utf-8"))
            logger.info(f"解析 job.md: {len(jobs_data)} 条岗位记录")
        else:
            logger.warning(f"未找到文件: {job_md}")

        if detail_md.exists():
            eval_data = parse_job_detail_md(detail_md.read_text(encoding="utf-8"))
            logger.info(f"解析 job_detail.md: {len(eval_data)} 条评估记录")
        else:
            logger.warning(f"未找到文件: {detail_md}")

        if apply_md.exists():
            apps_data = parse_apply_log_md(apply_md.read_text(encoding="utf-8"))
            logger.info(f"解析 job_apply_log.md: {len(apps_data)} 条投递记录")
        else:
            logger.warning(f"未找到文件: {apply_md}")

        if args.dry_run:
            dry_run_preview(jobs_data, eval_data, apps_data)
            return

        # 执行导入
        jobs_imported, jobs_skipped = import_jobs(session, jobs_data)
        logger.info(f"导入岗位: {jobs_imported} 条新增, {jobs_skipped} 条跳过")

        eval_imported, eval_skipped = import_evaluations(session, eval_data)
        logger.info(f"导入评估: {eval_imported} 条新增, {eval_skipped} 条跳过")

        apps_imported, apps_skipped = import_applications(session, apps_data)
        logger.info(f"导入投递: {apps_imported} 条新增, {apps_skipped} 条跳过")

        print(f"\n导入完成: 岗位 {jobs_imported} 条, 评估 {eval_imported} 条, 投递 {apps_imported} 条")

    finally:
        session.close()


if __name__ == "__main__":
    main()
