"""测试 job_service 模块。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from job_agent.db.init_db import init_db
from job_agent.db.session import SessionLocal
from job_agent.db.models import Job, JobEvaluation, JobEvaluationDimension
from job_agent.services.job_service import (
    get_jobs,
    get_job_stats,
    get_candidates,
    get_paused_jobs,
    get_job_evaluation,
    update_job_status,
    JobServiceError,
)

init_db()
session = SessionLocal()

# 先插入测试数据
job = Job(
    liepin_job_id="test001",
    title="测试岗位A",
    company="测试公司",
    score=85.0,
    grade="B",
    choice_status="待定",
    apply_status="未投递",
)
session.add(job)
session.flush()

job2 = Job(
    liepin_job_id="test002",
    title="测试岗位B",
    company="测试公司",
    score=92.0,
    grade="A",
    choice_status="待定",
    apply_status="未投递",
)
session.add(job2)
session.flush()

job3 = Job(
    liepin_job_id="test003",
    title="测试岗位C",
    company="测试公司",
    score=60.0,
    grade="D",
    choice_status="暂不投",
    apply_status="未投递",
)
session.add(job3)
session.flush()

job4 = Job(
    liepin_job_id="test004",
    title="已投递岗位",
    company="测试公司",
    score=88.0,
    grade="B",
    choice_status="待定",
    apply_status="已投递",
)
session.add(job4)
session.flush()

# 添加评估记录
ev = JobEvaluation(
    job_id=job.id,
    total_score=85.0,
    grade="B",
    summary="测试评估",
)
session.add(ev)
session.flush()

dims = [
    JobEvaluationDimension(evaluation_id=ev.id, dimension_name="角色匹配", weight=20, score=18, reason="匹配度高"),
    JobEvaluationDimension(evaluation_id=ev.id, dimension_name="地点偏好", weight=10, score=9, reason="地点合适"),
    JobEvaluationDimension(evaluation_id=ev.id, dimension_name="工作生活平衡", weight=15, score=10, reason="一般"),
    JobEvaluationDimension(evaluation_id=ev.id, dimension_name="薪酬竞争力", weight=20, score=16, reason="中等"),
    JobEvaluationDimension(evaluation_id=ev.id, dimension_name="公司口碑/稳定性", weight=10, score=8, reason="较好"),
    JobEvaluationDimension(evaluation_id=ev.id, dimension_name="成长潜力", weight=10, score=8, reason="有空间"),
    JobEvaluationDimension(evaluation_id=ev.id, dimension_name="行业匹配", weight=8, score=6, reason="相关"),
    JobEvaluationDimension(evaluation_id=ev.id, dimension_name="福利完整度", weight=7, score=5, reason="一般"),
]
for d in dims:
    session.add(d)
session.commit()

print("=" * 60)
print("测试 get_jobs")
print("=" * 60)

# 1. 获取全部
result = get_jobs(session, page=1, page_size=10)
print(f"[PASS] 全部岗位: total={result['total']}")
assert result["total"] >= 4

# 2. 按等级筛选
result = get_jobs(session, grade="A/B")
print(f"[PASS] A/B 筛选: total={result['total']}")
assert result["total"] >= 2

# 3. 按关键词
result = get_jobs(session, keyword="测试岗位A")
print(f"[PASS] 关键词筛选: total={result['total']}")
assert result["total"] >= 1

# 4. 按 choice_status
result = get_jobs(session, choice_status="暂不投")
print(f"[PASS] 暂不投筛选: total={result['total']}")
assert result["total"] >= 1

# 5. 按 apply_status
result = get_jobs(session, apply_status="已投递")
print(f"[PASS] 已投递筛选: total={result['total']}")
assert result["total"] >= 1

print()
print("=" * 60)
print("测试 get_job_stats")
print("=" * 60)

stats = get_job_stats(session)
print(f"[PASS] total={stats['total']}, applied={stats['applied']}, pending={stats['pending']}")
print(f"       paused={stats['paused']}, passed={stats['passed']}, ab_candidates={stats['ab_candidates']}")
print(f"       grade_distribution={stats['grade_distribution']}")
assert stats["total"] >= 4
assert stats["applied"] >= 1

print()
print("=" * 60)
print("测试 get_candidates")
print("=" * 60)

candidates = get_candidates(session)
print(f"[PASS] A/B 候选: {len(candidates)} 个")
for c in candidates:
    print(f"       {c.liepin_job_id} | {c.title} | score={c.score} | grade={c.grade}")
assert len(candidates) >= 2

print()
print("=" * 60)
print("测试 get_paused_jobs")
print("=" * 60)

paused = get_paused_jobs(session)
print(f"[PASS] 暂不投/pass: {len(paused)} 个")
assert len(paused) >= 1

print()
print("=" * 60)
print("测试 get_job_evaluation")
print("=" * 60)

ev_result = get_job_evaluation(session, job.id)
print(f"[PASS] 评估: total_score={ev_result['total_score']}, grade={ev_result['grade']}")
print(f"       维度数: {len(ev_result['dimensions'])}")
assert ev_result is not None
assert len(ev_result["dimensions"]) == 8

# 不存在的评估
ev_none = get_job_evaluation(session, 99999)
assert ev_none is None
print("[PASS] 不存在的评估返回 None")

print()
print("=" * 60)
print("测试 update_job_status")
print("=" * 60)

# 正常更新
updated = update_job_status(session, job.id, "暂不投")
print(f"[PASS] 更新状态: {updated.choice_status}")
assert updated.choice_status == "暂不投"

# 恢复
update_job_status(session, job.id, "待定")

# 已投递不可修改
try:
    update_job_status(session, job4.id, "暂不投")
    print("[FAIL] 已投递岗位应抛出异常")
except JobServiceError as e:
    print(f"[PASS] 已投递岗位抛出异常: {e}")

# 非法状态
try:
    update_job_status(session, job.id, "非法状态")
    print("[FAIL] 非法状态应抛出异常")
except JobServiceError as e:
    print(f"[PASS] 非法状态抛出异常: {e}")

# 不存在的岗位
try:
    update_job_status(session, 99999, "待定")
    print("[FAIL] 不存在岗位应抛出异常")
except JobServiceError as e:
    print(f"[PASS] 不存在岗位抛出异常: {e}")

session.close()

print()
print("=" * 60)
print("全部测试通过!")
print("=" * 60)
