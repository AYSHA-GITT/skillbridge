"""Append-only audit log for security-relevant / administrative operations."""
import json
import logging

from extensions import db
from models import AuditLog

logger = logging.getLogger("skillbridge.audit")


def audit(action: str, actor_id=None, target: str = None, details=None) -> None:
    """Record an audit event. Never raises - auditing must not break the request."""
    try:
        db.session.add(AuditLog(actor_id=actor_id, action=action[:80], target=(target or "")[:200] or None,
                                details=json.dumps(details, default=str) if details is not None else None))
        db.session.commit()
    except Exception as e:  # pragma: no cover
        db.session.rollback()
        logger.error("Failed to write audit log for %s: %s", action, e)
