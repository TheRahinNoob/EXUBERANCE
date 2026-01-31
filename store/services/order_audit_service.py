from store.models import Order
from store.models.order_status_audit import OrderStatusAuditLog


def log_order_status_change(
    *,
    order: Order,
    previous_status: str | None,
    new_status: str,
    actor_type: str,
    actor_identifier: str,
) -> None:
    """
    Immutable audit log for order status transitions.

    DESIGN PRINCIPLES:
    - Append-only (never update/delete)
    - Schema-safe (matches OrderStatusAuditLog exactly)
    - Never mutates Order
    - Never validates transitions
    - Failures MUST NOT break core business flow
    """

    try:
        OrderStatusAuditLog.objects.create(
            order=order,
            previous_status=previous_status,
            new_status=new_status,
            actor_type=actor_type,
            actor_identifier=actor_identifier,
        )
    except Exception:
        # ⚠️ Audit logging must NEVER break order flow.
        # Errors should be captured by logging / Sentry in production.
        pass
