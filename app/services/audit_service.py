"""Audit log yozish helperi."""
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log_action(
    db: AsyncSession,
    *,
    admin_telegram_id: int | None,
    action: str,
    entity: str | None = None,
    entity_id: str | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            admin_telegram_id=admin_telegram_id,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=json.dumps(details, ensure_ascii=False) if details else None,
        )
    )
    await db.flush()
