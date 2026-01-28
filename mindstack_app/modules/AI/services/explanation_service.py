"""Background task helpers for generating AI explanations in bulk."""

from __future__ import annotations

import time
from typing import Iterable, Optional

from flask import current_app
from sqlalchemy import or_

from mindstack_app.db_instance import db
from mindstack_app.models import LearningContainer, LearningItem
from .ai_manager import get_ai_service
from ..logics.prompts import get_formatted_prompt


DEFAULT_REQUEST_INTERVAL_SECONDS = 30.0


def _normalize_container_ids(container_ids: Optional[Iterable]) -> Optional[list[int]]:
    if not container_ids:
        return None

    if not isinstance(container_ids, (list, tuple, set)):
        container_ids = [container_ids]

    normalized_ids: list[int] = []
    for raw_id in container_ids:
        try:
            if raw_id is None:
                continue
            normalized_ids.append(int(raw_id))
        except (TypeError, ValueError):
            current_app.logger.warning(
                "[AI_EXPLANATION_TASK] Bỏ qua container_id không hợp lệ: %s", raw_id
            )
            continue

    return normalized_ids or None


def _build_scope_label(container_ids: Optional[list[int]]) -> str:
    if not container_ids:
        return "tất cả học liệu"

    containers = (
        LearningContainer.query.filter(LearningContainer.container_id.in_(container_ids))
        .order_by(LearningContainer.title.asc())
        .all()
    )

    if not containers:
        return "các bộ học liệu đã chọn"

    if len(containers) == 1:
        container = containers[0]
        return f"bộ \"{container.title}\" (ID {container.container_id})"

    joined_titles = ", ".join(
        f"\"{c.title}\" (ID {c.container_id})" for c in containers[:3]
    )
    suffix = "" if len(containers) <= 3 else f" + {len(containers) - 3} bộ khác"
    return f"{len(containers)} bộ đã chọn: {joined_titles}{suffix}"


def generate_ai_explanations(
    task,
    container_ids: Optional[Iterable] = None,
    delay_seconds: float = DEFAULT_REQUEST_INTERVAL_SECONDS,
):
    """Generate AI explanations for items missing cached content.

    Args:
        task: The BackgroundTask instance tracking progress.
        container_ids: Optional list of container IDs to limit the scope.
        delay_seconds: Delay inserted between AI requests to avoid throttling.
    """

    log_prefix = f"[{task.task_name}]"
    normalized_container_ids = _normalize_container_ids(container_ids)
    scope_label = _build_scope_label(normalized_container_ids)

    task.status = "running"
    task.progress = 0
    task.total = 0
    task.message = f"Đang chuẩn bị tạo AI Explain cho {scope_label}..."
    db.session.commit()

    try:
        ai_client = get_ai_service()
        if not ai_client:
            task.status = "error"
            task.message = "Chưa cấu hình dịch vụ AI (thiếu API key)."
            db.session.commit()
            return

        explanation_query = LearningItem.query.filter(
            or_(LearningItem.ai_explanation.is_(None), LearningItem.ai_explanation == "")
        )

        if normalized_container_ids:
            explanation_query = explanation_query.filter(
                LearningItem.container_id.in_(normalized_container_ids)
            )

        items_to_process = explanation_query.order_by(LearningItem.item_id.asc()).all()

        task.total = len(items_to_process)
        db.session.commit()

        if task.total == 0:
            task.status = "completed"
            task.message = f"Không tìm thấy học liệu cần tạo AI Explain trong {scope_label}."
            db.session.commit()
            return

        for idx, item in enumerate(items_to_process, start=1):
            db.session.refresh(task)
            if task.stop_requested:
                task.status = "completed"
                task.message = (
                    f"Đã dừng theo yêu cầu. Hoàn tất {task.progress}/{task.total} học liệu trong {scope_label}."
                )
                db.session.commit()
                return

            prompt = get_formatted_prompt(item, purpose="explanation")
            if not prompt:
                current_app.logger.warning(
                    "%s Bỏ qua item %s vì không tạo được prompt.", log_prefix, item.item_id
                )
                task.progress += 1
                task.message = (
                    f"Bỏ qua item {idx}/{task.total} trong {scope_label} (không có prompt)."
                )
                db.session.commit()
                continue

            item_info = f"{item.item_type} ID {item.item_id}"
            task.message = f"Đang tạo AI Explain cho {item_info} ({idx}/{task.total}) trong {scope_label}"
            db.session.commit()

            success, ai_response = ai_client.generate_content(prompt, item_info)
            if not success:
                task.status = "error"
                task.message = f"Lỗi khi gọi AI cho {item_info}: {ai_response}"
                db.session.commit()
                return

            item.ai_explanation = ai_response
            task.progress += 1
            task.message = (
                f"Đã tạo AI Explain cho {item_info} ({task.progress}/{task.total}) trong {scope_label}"
            )
            db.session.commit()

            if delay_seconds and idx < task.total:
                time.sleep(max(delay_seconds, 0))

        task.status = "completed"
        task.message = (
            f"Hoàn tất! Đã tạo AI Explain cho {task.progress}/{task.total} học liệu trong {scope_label}."
        )
        db.session.commit()

    except Exception as exc:  # pylint: disable=broad-except
        task.status = "error"
        task.message = f"Lỗi không mong muốn: {exc}"
        current_app.logger.error("%s %s", log_prefix, task.message, exc_info=True)
        db.session.commit()

    finally:
        if task.status == "running":
            task.status = "idle"
        task.is_enabled = False
        task.stop_requested = False
        db.session.commit()
