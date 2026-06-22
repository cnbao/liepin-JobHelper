"""Markdown 文件解析模块。

负责解析 job.md、job_detail.md、job_search_archive.md、job_apply_log.md 等文件，
返回结构化的数据字典列表。
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _extract_liepin_job_id(url: str) -> Optional[str]:
    """从猎聘 URL 中提取 liepin_job_id。

    URL 格式示例：
      https://www.liepin.com/job/1983071021.shtml
      https://www.liepin.com/a/75427683.shtml

    优先返回完整 ID（如 1983071021），如果 URL 中没有完整 ID，则返回 Job ID 字段。
    """
    if not url:
        return None
    # 匹配 /job/XXXXX.shtml 或 /a/XXXXX.shtml
    match = re.search(r'/job/(\d+)\.shtml', url)
    if match:
        return match.group(1)
    match = re.search(r'/a/(\d+)\.shtml', url)
    if match:
        return match.group(1)
    return None


def _normalize_job_id(job_id_str: str, url: str = "") -> str:
    """统一 Job ID 格式。

    规则：
    - 如果 URL 中存在完整猎聘 ID（10位，以 19 开头），优先使用 URL 中的 ID
    - 否则使用 job_id_str
    """
    liepin_id = _extract_liepin_job_id(url)
    if liepin_id:
        return liepin_id
    return job_id_str.strip()


def parse_job_md(content: str) -> List[Dict]:
    """解析 job.md 岗位主索引表格。

    返回岗位列表，每条包含：
      job_id, job_type, title, company, score, grade, choice, applied,
      apply_time, pdf_path, detail_path
    """
    jobs: List[Dict] = []
    lines = content.splitlines()

    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("| Job ID |"):
            in_table = True
            continue
        if in_table:
            # 分隔行（|---:|---:|...）是表格的一部分，跳过
            if "---:" in stripped and stripped.startswith("|"):
                continue
            if not stripped.startswith("|"):
                # 遇到非表格行，结束当前表格
                # 但继续检查是否有下一个表格（新一轮搜索摘要）
                if stripped.startswith("| Job ID |"):
                    continue
                in_table = False
                continue
            columns = [col.strip() for col in stripped.strip("|").split("|")]
            if len(columns) < 10:
                continue
            if not columns[0].isdigit():
                continue
            jobs.append({
                "job_id": columns[0],
                "job_type": columns[1],
                "title": columns[2],
                "company": columns[3],
                "score": columns[4],
                "grade": columns[5],
                "choice": columns[6],
                "applied": columns[7],
                "apply_time": columns[8],
                "pdf_path": columns[9],
                "detail_path": columns[10] if len(columns) > 10 else "",
            })
    return jobs


def parse_job_detail_md(content: str) -> List[Dict]:
    """解析 job_detail.md 评估记录。

    支持两种格式：
    1. 完整 A-G 模块评估：以 "## X. 岗位名｜公司名" 开头的区块
    2. 批量初评表格：以 "| Job ID | 岗位 | 公司 | ..." 开头的表格

    返回评估记录列表。
    """
    evaluations: List[Dict] = []
    lines = content.splitlines()

    # --- 方式 1：解析完整 A-G 模块评估 ---
    i = 0
    while i < len(lines):
        line = lines[i]
        # 匹配 "## X. 岗位名｜公司名" 格式
        header_match = re.match(r'^##\s+\d+\.\s+(.+?)\|(.+)$', line.strip())
        if not header_match:
            i += 1
            continue

        title = header_match.group(1).strip()
        company = header_match.group(2).strip()
        i += 1

        # 收集该评估块的所有内容
        block_lines: List[str] = []
        while i < len(lines):
            stripped = lines[i].strip()
            # 新评估块或新的大标题开始
            if re.match(r'^##\s+\d+\.', stripped) or (stripped.startswith("## ") and not stripped.startswith(f"## {len(evaluations) + 1}.")):
                # 检查是否是新的评估标题
                if re.match(r'^##\s+\d+\.\s+.+\|.+', stripped):
                    break
                # 如果是其他 ## 标题但不是评估格式，也停止
                if stripped.startswith("## ") and not re.match(r'^##\s+\d+\.\s+.+\|.+', stripped):
                    break
            block_lines.append(lines[i])
            i += 1

        # 解析 block_lines 中的字段
        eval_record = _parse_evaluation_block(title, company, block_lines)
        if eval_record:
            evaluations.append(eval_record)

    # --- 方式 2：解析批量初评表格 ---
    # 查找所有批量初评表格
    for line in lines:
        if line.strip().startswith("| Job ID |") and "岗位" in line and "公司" in line:
            # 这是批量初评表格的表头
            # 收集表格中的所有行
            table_rows: List[str] = []
            idx = lines.index(line)
            idx += 1
            while idx < len(lines):
                stripped = lines[idx].strip()
                if stripped.startswith("|") and stripped.count("|") >= 8:
                    table_rows.append(stripped)
                    idx += 1
                else:
                    break

            for row in table_rows:
                columns = [col.strip() for col in row.strip("|").split("|")]
                if len(columns) < 8:
                    continue
                try:
                    job_id = columns[0]
                    if not job_id.isdigit():
                        continue
                    evaluations.append({
                        "job_id": job_id,
                        "liepin_job_id": job_id,
                        "title": columns[1],
                        "company": columns[2],
                        "score": columns[3],
                        "grade": columns[4],
                        "choice": columns[5],
                        "risk_points": columns[6] if len(columns) > 6 else "",
                        "work_content": columns[7] if len(columns) > 7 else "",
                        "source": "batch_review",
                    })
                except (ValueError, IndexError):
                    logger.warning(f"跳过无效的批量初评行: {row[:80]}")

    return evaluations


def _parse_evaluation_block(title: str, company: str, block_lines: List[str]) -> Optional[Dict]:
    """从评估块的行中解析字段。"""
    record: Dict = {
        "title": title,
        "company": company,
    }

    job_id = ""
    url = ""
    liepin_job_id = ""
    score = ""
    grade = ""
    choice = ""

    for line in block_lines:
        stripped = line.strip()

        # Job ID
        job_match = re.match(r'^[-\s]*Job ID[：:]\s*(\d+)', stripped)
        if job_match:
            job_id = job_match.group(1)

        # URL
        url_match = re.search(r'(https?://[^\s|]+)', stripped)
        if url_match:
            url = url_match.group(1)

        # 最终评级
        grade_match = re.match(r'^[-\s]*最终评级[：:]\s*(.+)', stripped)
        if grade_match:
            grade_text = grade_match.group(1).strip()
            # 解析 "B / 83" 或 "A / 93"
            score_match = re.search(r'(\d+)\s*/\s*(\d+)', grade_text)
            if score_match:
                grade = score_match.group(1)
                score = score_match.group(2)
            else:
                grade = grade_text

        # 用户选择
        choice_match = re.match(r'^[-\s]*用户选择[：:]\s*(.+)', stripped)
        if choice_match:
            choice = choice_match.group(1).strip()

        # 是否已投递
        applied_match = re.match(r'^[-\s]*是否已投递[：:]\s*(.+)', stripped)
        if applied_match:
            record["applied"] = applied_match.group(1).strip()

        # 投递时间
        time_match = re.match(r'^[-\s]*投递时间[：:]\s*(.+)', stripped)
        if time_match:
            record["apply_time"] = time_match.group(1).strip()

        # PDF路径
        pdf_match = re.match(r'^[-\s]*使用的 PDF 简历路径[：:]\s*(.+)', stripped)
        if pdf_match:
            record["pdf_path"] = pdf_match.group(1).strip()

        # 打招呼语
        greeting_match = re.match(r'^[-\s]*打招呼语[：:]\s*(.+)', stripped)
        if greeting_match:
            record["greeting"] = greeting_match.group(1).strip()

        # 8维评分表格
        if stripped.startswith("| 维度 |") and "权重" in stripped:
            # 收集维度评分
            dimensions = []
            dim_idx = block_lines.index(line) if line in block_lines else -1
            j = dim_idx + 1
            while j < len(block_lines):
                dim_line = block_lines[j].strip()
                if dim_line.startswith("|") and dim_line.endswith("|") and "——" not in dim_line:
                    dim_cols = [c.strip() for c in dim_line.strip("|").split("|")]
                    if len(dim_cols) >= 4 and dim_cols[0] and dim_cols[0] != "维度":
                        dimensions.append({
                            "dimension_name": dim_cols[0],
                            "weight": dim_cols[1],
                            "score": dim_cols[2],
                            "reason": dim_cols[3] if len(dim_cols) > 3 else "",
                        })
                    j += 1
                else:
                    break
            record["dimensions"] = dimensions

    # 统一 job_id
    liepin_job_id = _extract_liepin_job_id(url) or job_id
    record["job_id"] = job_id
    record["liepin_job_id"] = liepin_job_id
    record["url"] = url
    record["score"] = score
    record["grade"] = grade
    record["choice"] = choice

    if not job_id and not liepin_job_id:
        return None

    return record


def parse_search_archive_md(content: str) -> List[Dict]:
    """解析 job_search_archive.md 搜索归档。

    目前返回空列表，搜索归档主要作为参考文件。
    """
    return []


def parse_apply_log_md(content: str) -> List[Dict]:
    """解析 job_apply_log.md 投递日志。

    支持多种投递记录格式：
    1. 段落式：### 公司｜岗位 + 字段列表
    2. 表格式：| 序号 | Job ID | ... |
    """
    applications: List[Dict] = []
    lines = content.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # --- 段落式投递记录 ---
        # 匹配 "### N. 公司｜岗位" 或 "### 公司｜岗位"
        section_match = re.match(r'^###\s+(?:\d+\.\s+)?(.+?)\|(.+)$', stripped)
        if section_match:
            company = section_match.group(1).strip()
            title = section_match.group(2).strip()
            i += 1

            # 收集该投递块的内容
            block_lines: List[str] = []
            while i < len(lines):
                s = lines[i].strip()
                # 新投递块或新的大标题
                if re.match(r'^###\s+(?:\d+\.\s+)?(.+?)\|.+', s):
                    break
                if s.startswith("## ") and not re.match(r'^###\s+', s):
                    break
                if s.startswith("| 序号 |") and "Job ID" in s:
                    # 表格形式的投递记录，稍后单独处理
                    break
                block_lines.append(lines[i])
                i += 1

            app = _parse_apply_section(company, title, block_lines)
            if app:
                applications.append(app)
            continue

        # --- 表格式投递记录 ---
        if stripped.startswith("| 序号 |") and "Job ID" in stripped:
            # 收集表格行
            table_rows: List[str] = []
            while i + 1 < len(lines):
                i += 1
                row = lines[i].strip()
                if row.startswith("|") and row.count("|") >= 5:
                    table_rows.append(row)
                else:
                    break

            for row in table_rows:
                columns = [col.strip() for col in row.strip("|").split("|")]
                if len(columns) < 6:
                    continue
                try:
                    job_id = columns[1]
                    if not job_id.isdigit():
                        continue
                    applications.append({
                        "job_id": job_id,
                        "liepin_job_id": job_id,
                        "title": columns[2],
                        "company": columns[3],
                        "status": columns[4],
                        "pdf_path": columns[5] if len(columns) > 5 else "",
                        "source": "apply_log_table",
                    })
                except (ValueError, IndexError):
                    logger.warning(f"跳过无效的投递日志行: {row[:80]}")
            continue

        i += 1

    return applications


def _parse_apply_section(company: str, title: str, block_lines: List[str]) -> Optional[Dict]:
    """从段落式投递块中解析字段。"""
    record: Dict = {
        "title": title,
        "company": company,
    }

    for line in block_lines:
        stripped = line.strip()

        job_match = re.match(r'^[-\s]*Job ID[：:]\s*(\d+)', stripped)
        if job_match:
            job_id = job_match.group(1)
            record["job_id"] = job_id
            record["liepin_job_id"] = job_id

        kind_match = re.match(r'^[-\s]*Job Type[：:]\s*(\d+)', stripped)
        if kind_match:
            record["job_type"] = kind_match.group(1)

        status_match = re.match(r'^[-\s]*投递结果[：:]\s*(.+)', stripped)
        if status_match:
            record["status"] = status_match.group(1).strip()

        pdf_match = re.match(r'^[-\s]*使用的 PDF 简历路径[：:]\s*(.+)', stripped)
        if pdf_match:
            record["pdf_path"] = pdf_match.group(1).strip()

        greeting_match = re.match(r'^[-\s]*打招呼语[：:]\s*(.+)', stripped)
        if greeting_match:
            record["greeting"] = greeting_match.group(1).strip()

    return record if "job_id" in record else None
