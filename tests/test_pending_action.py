"""测试 PendingAction 服务和投递状态机。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from job_agent.db.init_db import init_db
from job_agent.db.session import SessionLocal
from job_agent.db.models import PendingAction
from job_agent.services.pending_action_service import (
    create_pending_action,
    confirm_action,
    execute_action,
    cancel_action,
    get_action,
    PendingActionNotFoundError,
    PendingActionAlreadyCancelledError,
    PendingActionAlreadyConfirmedError,
    PendingActionAlreadyExecutedError,
    PendingActionNotConfirmedError,
)
from job_agent.services.apply_state_machine import (
    ApplyStateMachine,
    State,
    InvalidStateTransition,
)

init_db()

# ===== 测试 PendingAction 服务 =====
print("=" * 60)
print("测试 PendingAction 服务")
print("=" * 60)

# 1. 创建
action = create_pending_action(
    action_type="APPLY_JOB",
    payload={"job_id": 123, "job_kind": 2},
    risk_level="medium",
)
print(f"[PASS] 创建 action: id={action.id}, status={action.status}")
assert action.status == "pending"

# 2. 确认
confirmed = confirm_action(action.id)
print(f"[PASS] 确认 action: id={confirmed.id}, status={confirmed.status}")
assert confirmed.status == "confirmed"

# 3. 重复确认 -> 异常
try:
    confirm_action(action.id)
    print("[FAIL] 重复确认应该抛出异常")
except PendingActionAlreadyConfirmedError:
    print("[PASS] 重复确认抛出 PendingActionAlreadyConfirmedError")

# 4. 执行
executed = execute_action(action.id, result="投递成功")
print(f"[PASS] 执行 action: id={executed.id}, status={executed.status}, result={executed.result}")
assert executed.status == "executed"

# 5. 重复执行 -> 异常
try:
    execute_action(action.id)
    print("[FAIL] 重复执行应该抛出异常")
except PendingActionAlreadyExecutedError:
    print("[PASS] 重复执行抛出 PendingActionAlreadyExecutedError")

# 6. 取消 pending 状态的 action
action2 = create_pending_action(action_type="MODIFY_RESUME", payload={"field": "name"})
cancelled = cancel_action(action2.id)
print(f"[PASS] 取消 action: id={cancelled.id}, status={cancelled.status}")
assert cancelled.status == "cancelled"

# 7. 确认已取消的 action -> 异常
try:
    confirm_action(action2.id)
    print("[FAIL] 确认已取消的 action 应该抛出异常")
except PendingActionAlreadyCancelledError:
    print("[PASS] 确认已取消的 action 抛出 PendingActionAlreadyCancelledError")

# 8. 执行未确认的 action -> 异常
action3 = create_pending_action(action_type="APPLY_JOB", payload={"job_id": 456})
try:
    execute_action(action3.id)
    print("[FAIL] 执行未确认的 action 应该抛出异常")
except PendingActionNotConfirmedError:
    print("[PASS] 执行未确认的 action 抛出 PendingActionNotConfirmedError")

# 9. 获取不存在的 action -> 异常
try:
    get_action(99999)
    print("[FAIL] 获取不存在的 action 应该抛出异常")
except PendingActionNotFoundError:
    print("[PASS] 获取不存在的 action 抛出 PendingActionNotFoundError")

# ===== 测试状态机 =====
print()
print("=" * 60)
print("测试投递状态机")
print("=" * 60)

sm = ApplyStateMachine()
assert sm.state == State.IDLE
print(f"[PASS] 初始状态: {sm.state.value}")

# IDLE -> LOADING_CANDIDATES
sm.load_candidates([{"job_id": 1, "title": "岗位A"}, {"job_id": 2, "title": "岗位B"}])
assert sm.state == State.LOADING_CANDIDATES
print(f"[PASS] load_candidates: {sm.state.value}, candidates={len(sm.candidates)}")

# LOADING_CANDIDATES -> PRESENTING
sm.present()
assert sm.state == State.PRESENTING
print(f"[PASS] present: {sm.state.value}")

# PRESENTING -> WAITING_SELECTION
sm.select([{"job_id": 1, "title": "岗位A"}])
assert sm.state == State.WAITING_SELECTION
print(f"[PASS] select: {sm.state.value}, selected={len(sm.selected_jobs)}")

# WAITING_SELECTION -> ASKING_RESUME_STRATEGY
sm.ask_resume_strategy()
assert sm.state == State.ASKING_RESUME_STRATEGY
print(f"[PASS] ask_resume_strategy: {sm.state.value}")

# ASKING_RESUME_STRATEGY -> GENERATING_RESUME
sm.generate_resume({1: "online"})
assert sm.state == State.GENERATING_RESUME
print(f"[PASS] generate_resume: {sm.state.value}")

# GENERATING_RESUME -> WAITING_CONFIRMATION
sm.wait_confirmation()
assert sm.state == State.WAITING_CONFIRMATION
print(f"[PASS] wait_confirmation: {sm.state.value}")

# WAITING_CONFIRMATION -> APPLYING
sm.apply()
assert sm.state == State.APPLYING
print(f"[PASS] apply: {sm.state.value}")

# APPLYING -> COMPLETED
sm.complete([{"job_id": 1, "result": "success"}])
assert sm.state == State.COMPLETED
print(f"[PASS] complete: {sm.state.value}, results={len(sm.results)}")

sm.close()

# ===== 测试状态恢复 =====
print()
print("=" * 60)
print("测试状态恢复")
print("=" * 60)

# 创建新的状态机并保存状态
sm2 = ApplyStateMachine()
sm2.load_candidates([{"job_id": 3, "title": "岗位C"}])
sm2.present()
sm2.select([{"job_id": 3, "title": "岗位C"}])
saved_id = sm2.action_id
print(f"[PASS] 状态机已保存, action_id={saved_id}, state={sm2.state.value}")
sm2.close()

# 从数据库恢复
sm3 = ApplyStateMachine(action_id=saved_id)
assert sm3.state == State.WAITING_SELECTION
assert len(sm3.selected_jobs) == 1
assert sm3.selected_jobs[0]["job_id"] == 3
print(f"[PASS] 状态恢复: state={sm3.state.value}, selected={sm3.selected_jobs}")
sm3.close()

# ===== 测试非法状态转移 =====
print()
print("=" * 60)
print("测试非法状态转移")
print("=" * 60)

sm4 = ApplyStateMachine()
try:
    sm4.apply()  # IDLE 不能直接 APPLYING
    print("[FAIL] 非法转移应该抛出异常")
except InvalidStateTransition as e:
    print(f"[PASS] 非法转移抛出异常: {e}")

try:
    sm4.complete([])  # IDLE 不能直接 COMPLETED
    print("[FAIL] 非法转移应该抛出异常")
except InvalidStateTransition:
    print("[PASS] IDLE -> COMPLETED 非法")

try:
    sm4.cancel()
    # IDLE -> CANCELLED 是合法的
    print(f"[PASS] IDLE -> CANCELLED 合法")
except InvalidStateTransition:
    print("[FAIL] IDLE -> CANCELLED 应该合法")

sm4.close()

print()
print("=" * 60)
print("全部测试通过!")
print("=" * 60)
