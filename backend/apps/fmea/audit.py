import logging

from .models import AuditLog

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "password",
    "password1",
    "password2",
    "token",
    "access",
    "refresh",
    "secret",
    "authorization",
    "api_key",
}


def get_client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def _sanitize(value):
    if isinstance(value, dict):
        return {
            key: "***" if str(key).lower() in SENSITIVE_KEYS else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


def log_action(*, user, action, entity, payload=None, request=None):
    if isinstance(entity, str):
        entity_type, entity_id = entity, ""
    else:
        entity_type = entity.__class__.__name__
        entity_id = str(getattr(entity, "pk", "") or "")

    actor = user if getattr(user, "is_authenticated", False) else None
    try:
        return AuditLog.objects.create(
            user=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=_sanitize(payload or {}),
            ip_address=get_client_ip(request),
        )
    except Exception:
        logger.exception("Не удалось записать действие аудита")
        return None
