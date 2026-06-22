"""PendingAction 服务层。

管理待确认操作的生命周期：
  pending → confirmed → executed
  pending → cancelled
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from job_agent.db.models import PendingAction
from job_agent.db.session import SessionLocal


class PendingActionError(Exception):
    """PendingAction 操作异常。"""

    pass


class PendingActionNotFoundError(PendingActionError):
    """PendingAction 不存在。"""

    pass


class PendingActionAlreadyConfirmedError(PendingActionError):
    """PendingAction 已被确认，无法重复确认。"""

    pass


class PendingActionAlreadyCancelledError(PendingActionError):
    """PendingAction 已被取消，无法操作。"""

    pass


class PendingActionAlreadyExecutedError(PendingActionError):
    """PendingAction 已被执行，无法重复执行。"""

    pass


class PendingActionNotConfirmedError(PendingActionError):
    """PendingAction 尚未确认，无法执行。"""

    pass


def create_pending_action(
    action_type: str,
    payload: Dict[str, Any],
    risk_level: str = "low",
    session=None,
) -> PendingAction:
    """创建待确认操作。

    Args:
        action_type: 操作类型（APPLY_JOB / MODIFY_RESUME）
        payload: 操作参数字典
        risk_level: 风险等级（low / medium / high）
        session: 数据库会话，不传则自动创建

    Returns:
        PendingAction 实例
    """
    own_session = False
    if session is None:
        session = SessionLocal()
        own_session = True

    try:
        action = PendingAction(
            action_type=action_type,
            payload=json.dumps(payload, ensure_ascii=False),
            risk_level=risk_level,
            status="pending",
        )
        session.add(action)
        session.commit()
        session.refresh(action)
        return action
    finally:
        if own_session:
            session.close()


def get_action(action_id: int, session=None) -> Optional[PendingAction]:
    """获取指定 ID 的 PendingAction。

    Raises:
        PendingActionNotFoundError: 不存在时抛出
    """
    own_session = False
    if session is None:
        session = SessionLocal()
        own_session = True

    try:
        action = session.query(PendingAction).filter_by(id=action_id).first()
        if not action:
            raise PendingActionNotFoundError(f"PendingAction {action_id} 不存在")
        return action
    finally:
        if own_session:
            session.close()


def list_pending_actions(
    status: Optional[str] = None,
    action_type: Optional[str] = None,
    session=None,
) -> List[PendingAction]:
    """列出待确认操作，可按状态和类型筛选。"""
    own_session = False
    if session is None:
        session = SessionLocal()
        own_session = True

    try:
        query = session.query(PendingAction)
        if status:
            query = query.filter_by(status=status)
        if action_type:
            query = query.filter_by(action_type=action_type)
        return query.order_by(PendingAction.created_at.desc()).all()
    finally:
        if own_session:
            session.close()


def confirm_action(action_id: int, session=None) -> PendingAction:
    """确认待确认操作。

    Raises:
        PendingActionNotFoundError: 不存在
        PendingActionAlreadyCancelledError: 已取消
        PendingActionAlreadyConfirmedError: 已确认
        PendingActionAlreadyExecutedError: 已执行
    """
    own_session = False
    if session is None:
        session = SessionLocal()
        own_session = True

    try:
        action = get_action(action_id, session=session)

        if action.status == "cancelled":
            raise PendingActionAlreadyCancelledError(
                f"PendingAction {action_id} 已被取消，无法确认"
            )
        if action.status == "confirmed":
            raise PendingActionAlreadyConfirmedError(
                f"PendingAction {action_id} 已被确认，无法重复确认"
            )
        if action.status == "executed":
            raise PendingActionAlreadyExecutedError(
                f"PendingAction {action_id} 已被执行，无法确认"
            )

        action.status = "confirmed"
        action.confirmed_at = datetime.now()
        session.commit()
        session.refresh(action)
        return action
    finally:
        if own_session:
            session.close()


def execute_action(action_id: int, result: Optional[str] = None, session=None) -> PendingAction:
    """执行已确认的操作。

    Args:
        action_id: PendingAction ID
        result: 执行结果描述
        session: 数据库会话

    Raises:
        PendingActionNotFoundError: 不存在
        PendingActionNotConfirmedError: 未确认
        PendingActionAlreadyExecutedError: 已执行
        PendingActionAlreadyCancelledError: 已取消
    """
    own_session = False
    if session is None:
        session = SessionLocal()
        own_session = True

    try:
        action = get_action(action_id, session=session)

        if action.status == "cancelled":
            raise PendingActionAlreadyCancelledError(
                f"PendingAction {action_id} 已被取消，无法执行"
            )
        if action.status == "pending":
            raise PendingActionNotConfirmedError(
                f"PendingAction {action_id} 尚未确认，无法执行"
            )
        if action.status == "executed":
            raise PendingActionAlreadyExecutedError(
                f"PendingAction {action_id} 已被执行，无法重复执行"
            )

        action.status = "executed"
        action.executed_at = datetime.now()
        action.result = result
        session.commit()
        session.refresh(action)
        return action
    finally:
        if own_session:
            session.close()


def cancel_action(action_id: int, session=None) -> PendingAction:
    """取消待确认操作。

    Raises:
        PendingActionNotFoundError: 不存在
        PendingActionAlreadyExecutedError: 已执行
        PendingActionAlreadyCancelledError: 已取消
    """
    own_session = False
    if session is None:
        session = SessionLocal()
        own_session = True

    try:
        action = get_action(action_id, session=session)

        if action.status == "executed":
            raise PendingActionAlreadyExecutedError(
                f"PendingAction {action_id} 已被执行，无法取消"
            )
        if action.status == "cancelled":
            raise PendingActionAlreadyCancelledError(
                f"PendingAction {action_id} 已被取消，无法重复取消"
            )

        action.status = "cancelled"
        session.commit()
        session.refresh(action)
        return action
    finally:
        if own_session:
            session.close()
