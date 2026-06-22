"""投递编排状态机。

状态流转：
  IDLE → LOADING_CANDIDATES → PRESENTING → WAITING_SELECTION
    → ASKING_RESUME_STRATEGY → GENERATING_RESUME
    → WAITING_CONFIRMATION → APPLYING → COMPLETED / FAILED

每个状态对应一个方法，关键节点（WAITING_SELECTION, WAITING_CONFIRMATION）
返回前端等待用户输入。所有状态持久化到 pending_actions 表。
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from job_agent.db.models import PendingAction
from job_agent.db.session import SessionLocal


class State(Enum):
    IDLE = "IDLE"
    LOADING_CANDIDATES = "LOADING_CANDIDATES"
    PRESENTING = "PRESENTING"
    WAITING_SELECTION = "WAITING_SELECTION"
    ASKING_RESUME_STRATEGY = "ASKING_RESUME_STRATEGY"
    GENERATING_RESUME = "GENERATING_RESUME"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    APPLYING = "APPLYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# 合法状态转移表
_TRANSITIONS: Dict[State, List[State]] = {
    State.IDLE: [State.LOADING_CANDIDATES, State.CANCELLED],
    State.LOADING_CANDIDATES: [State.PRESENTING, State.FAILED, State.CANCELLED],
    State.PRESENTING: [State.WAITING_SELECTION, State.FAILED, State.CANCELLED],
    State.WAITING_SELECTION: [
        State.ASKING_RESUME_STRATEGY,
        State.CANCELLED,
        State.FAILED,
    ],
    State.ASKING_RESUME_STRATEGY: [
        State.GENERATING_RESUME,
        State.WAITING_CONFIRMATION,
        State.CANCELLED,
        State.FAILED,
    ],
    State.GENERATING_RESUME: [
        State.WAITING_CONFIRMATION,
        State.ASKING_RESUME_STRATEGY,
        State.FAILED,
        State.CANCELLED,
    ],
    State.WAITING_CONFIRMATION: [
        State.APPLYING,
        State.CANCELLED,
        State.FAILED,
    ],
    State.APPLYING: [State.COMPLETED, State.FAILED, State.CANCELLED],
    State.COMPLETED: [],
    State.FAILED: [State.IDLE],
    State.CANCELLED: [],
}


class InvalidStateTransition(Exception):
    """非法状态转移异常。"""

    def __init__(self, current: State, target: State):
        self.current = current
        self.target = target
        super().__init__(f"非法状态转移: {current.value} → {target.value}")


class ApplyStateMachine:
    """投递编排状态机。

    用法：
        sm = ApplyStateMachine()
        sm.load_candidates()
        sm.present()
        # ... 按状态流转调用
    """

    def __init__(self, session=None, action_id: Optional[int] = None):
        self._session = session or SessionLocal()
        self._own_session = session is None

        if action_id is not None:
            self._restore(action_id)
        else:
            self._action: Optional[PendingAction] = None
            self._state: State = State.IDLE
            self._candidates: List[Dict[str, Any]] = []
            self._selected_jobs: List[Dict[str, Any]] = []
            self._resume_strategies: Dict[int, str] = {}
            self._results: List[Dict[str, Any]] = []

    def _transition(self, target: State):
        """执行状态转移，校验合法性。"""
        if target not in _TRANSITIONS.get(self._state, []):
            raise InvalidStateTransition(self._state, target)
        self._state = target
        self._persist()

    def _persist(self):
        """将当前状态持久化到 pending_actions 表。"""
        if self._action is None:
            self._action = PendingAction(
                action_type="APPLY_FLOW",
                payload=json.dumps(
                    {
                        "state": self._state.value,
                        "candidates": self._candidates,
                        "selected_jobs": self._selected_jobs,
                        "resume_strategies": self._resume_strategies,
                        "results": self._results,
                    },
                    ensure_ascii=False,
                ),
                risk_level="low",
                status="pending",
            )
            self._session.add(self._action)
        else:
            self._action.payload = json.dumps(
                {
                    "state": self._state.value,
                    "candidates": self._candidates,
                    "selected_jobs": self._selected_jobs,
                    "resume_strategies": self._resume_strategies,
                    "results": self._results,
                },
                ensure_ascii=False,
            )
        self._session.commit()
        self._session.refresh(self._action)

    def _restore(self, action_id: int):
        """从数据库恢复状态。"""
        action = self._session.query(PendingAction).filter_by(id=action_id).first()
        if not action:
            raise ValueError(f"PendingAction {action_id} 不存在")

        payload = json.loads(action.payload)
        self._action = action
        self._state = State(payload.get("state", "IDLE"))
        self._candidates = payload.get("candidates", [])
        self._selected_jobs = payload.get("selected_jobs", [])
        self._resume_strategies = payload.get("resume_strategies", {})
        self._results = payload.get("results", [])

    # ---- 公开方法 ----

    @property
    def state(self) -> State:
        return self._state

    @property
    def action_id(self) -> Optional[int]:
        return self._action.id if self._action else None

    @property
    def candidates(self) -> List[Dict[str, Any]]:
        return self._candidates

    @property
    def selected_jobs(self) -> List[Dict[str, Any]]:
        return self._selected_jobs

    @property
    def resume_strategies(self) -> Dict[int, str]:
        return self._resume_strategies

    @property
    def results(self) -> List[Dict[str, Any]]:
        return self._results

    def load_candidates(self, candidates: List[Dict[str, Any]]):
        """加载候选岗位列表。"""
        self._transition(State.LOADING_CANDIDATES)
        self._candidates = candidates
        self._persist()

    def present(self):
        """展示候选列表（进入等待用户选择状态）。"""
        self._transition(State.PRESENTING)
        self._persist()

    def select(self, selected: List[Dict[str, Any]]):
        """用户选择岗位。"""
        self._transition(State.WAITING_SELECTION)
        self._selected_jobs = selected
        self._persist()

    def ask_resume_strategy(self):
        """询问简历策略（进入等待用户选择策略状态）。"""
        self._transition(State.ASKING_RESUME_STRATEGY)
        self._persist()

    def generate_resume(self, strategies: Dict[int, str]):
        """用户指定简历策略。

        Args:
            strategies: {job_id: "online" | "pdf"}
        """
        self._transition(State.GENERATING_RESUME)
        self._resume_strategies = strategies
        self._persist()

    def wait_confirmation(self):
        """等待用户最终确认。"""
        self._transition(State.WAITING_CONFIRMATION)
        self._persist()

    def apply(self):
        """执行投递。"""
        self._transition(State.APPLYING)
        self._persist()

    def complete(self, results: List[Dict[str, Any]]):
        """投递完成。"""
        self._transition(State.COMPLETED)
        self._results = results
        self._persist()

    def fail(self, error: str):
        """投递失败。"""
        self._transition(State.FAILED)
        self._results.append({"error": error})
        self._persist()

    def cancel(self):
        """取消投递流程。"""
        self._transition(State.CANCELLED)
        self._persist()

    def close(self):
        """关闭数据库会话。"""
        if self._own_session:
            self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
