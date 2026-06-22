"""从数据库导出 Markdown 文件。

生成与原始格式兼容的 Markdown 文件：
  - job.md：岗位主索引表格
  - job_detail.md：评估记录
  - job_apply_log.md：投递日志

用法：
    python scripts/export_to_md.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from job_agent.db.models import (
    Application,
    Job,
    JobEvaluation,
    JobEvaluationDimension,
)
from job_agent.db.session import SessionLocal


def _fmt(v):
    """格式化值，None 返回空字符串"""
    if v is None:
        return ""
    return str(v)


def export_job_md(session, path: Path):
    """导出 job.md 岗位主索引表格。"""
    jobs = session.query(Job).order_by(Job.id).all()

    lines = [
        "# 岗位主索引",
        "",
        "> 由 export_to_md.py 自动生成",
        "",
        "## 岗位主表",
        "",
        "| Job ID | Job Type | 岗位名称 | 公司 | 评分 | 等级 | 用户选择 | 是否已投递 | 投递时间 | PDF路径 |",
        "|---:|---:|---|---|---:|---|---|---|---|---|",
    ]

    for job in jobs:
        lines.append(
            f"| {_fmt(job.liepin_job_id)}"
            f" | {_fmt(job.liepin_job_kind)}"
            f" | {_fmt(job.title)}"
            f" | {_fmt(job.company)}"
            f" | {_fmt(job.score)}"
            f" | {_fmt(job.grade)}"
            f" | {_fmt(job.choice_status)}"
            f" | {'是' if job.apply_status == '已投递' else '否'}"
            f" | {_fmt(job.updated_at.strftime('%Y-%m-%d %H:%M:%S') if job.updated_at else '')}"
            f" | |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")
    return len(jobs)


def export_job_detail_md(session, path: Path):
    """导出 job_detail.md 评估记录。"""
    evals = session.query(JobEvaluation).order_by(JobEvaluation.id).all()

    lines = [
        "# 岗位详情归档",
        "",
        "> 由 export_to_md.py 自动生成",
        "",
        "# 岗位评估记录",
        "",
    ]

    for i, ev in enumerate(evals, 1):
        job = session.query(Job).filter_by(id=ev.job_id).first()
        if not job:
            continue

        lines.append(f"## {i}. {_fmt(job.title)}｜{_fmt(job.company)}")
        lines.append("")
        lines.append(f"- Job ID：{_fmt(job.liepin_job_id)}")
        lines.append(f"- 最终评级：{_fmt(ev.grade)} / {_fmt(ev.total_score)}")
        lines.append("")

        # 8维评分
        dims = (
            session.query(JobEvaluationDimension)
            .filter_by(evaluation_id=ev.id)
            .order_by(JobEvaluationDimension.id)
            .all()
        )
        if dims:
            lines.append("### 8维评分")
            lines.append("| 维度 | 权重 | 分数 | 说明 |")
            lines.append("|---|---:|---:|---|")
            for d in dims:
                lines.append(
                    f"| {_fmt(d.dimension_name)}"
                    f" | {_fmt(d.weight)}"
                    f" | {_fmt(d.score)}"
                    f" | {_fmt(d.reason)} |"
                )
            lines.append("")

        lines.append("---")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return len(evals)


def export_apply_log_md(session, path: Path):
    """导出 job_apply_log.md 投递日志。"""
    apps = session.query(Application).order_by(Application.id).all()

    lines = [
        "# 岗位投递日志",
        "",
        "> 由 export_to_md.py 自动生成",
        "",
        "## 投递记录",
        "",
        "| 序号 | Job ID | 岗位 | 公司 | 投递结果 | PDF路径 |",
        "|---:|---:|---|---|---|---|",
    ]

    for i, app in enumerate(apps, 1):
        job = session.query(Job).filter_by(id=app.job_id).first()
        title = _fmt(job.title) if job else ""
        company = _fmt(job.company) if job else ""

        status_map = {
            "success": "应聘成功",
            "failed": "投递失败",
            "pending": "待确认",
        }
        status = status_map.get(app.status, app.status)

        lines.append(
            f"| {i}"
            f" | {_fmt(app.liepin_job_id)}"
            f" | {title}"
            f" | {company}"
            f" | {status}"
            f" | {_fmt(app.pdf_path)} |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")
    return len(apps)


def main():
    session = SessionLocal()
    export_dir = PROJECT_ROOT

    try:
        n_jobs = export_job_md(session, export_dir / "job.md")
        print(f"导出 job.md: {n_jobs} 条岗位记录")

        n_evals = export_job_detail_md(session, export_dir / "job_detail.md")
        print(f"导出 job_detail.md: {n_evals} 条评估记录")

        n_apps = export_apply_log_md(session, export_dir / "job_apply_log.md")
        print(f"导出 job_apply_log.md: {n_apps} 条投递记录")

        print(f"\n导出完成，文件已保存到 {export_dir}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
