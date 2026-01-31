from django.db import models

from store.models.order import Order


class OrderStatusAuditLog(models.Model):
    """
    Immutable audit log for order status transitions.

    This table is append-only and records:
    - Every status change
    - Who/what caused it (admin, system, automation)
    - When it happened

    This model is the single source of truth
    for order lifecycle history.
    """

    # ==================================================
    # RELATIONS
    # ==================================================
    order = models.ForeignKey(
        Order,
        related_name="status_audit_logs",
        on_delete=models.CASCADE,
        db_index=True,
    )

    # ==================================================
    # ACTOR METADATA (FUTURE-PROOF)
    # ==================================================
    actor_type = models.CharField(
        max_length=20,
        help_text="Who performed the action (admin, system, courier, etc.)",
    )

    actor_identifier = models.CharField(
        max_length=100,
        help_text="Identifier of the actor (e.g. admin:1, system, pathao:webhook)",
    )

    # ==================================================
    # STATUS TRANSITION
    # ==================================================
    previous_status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Previous order status (null for creation)",
    )

    new_status = models.CharField(
        max_length=20,
        help_text="New order status after transition",
    )

    # ==================================================
    # TIMESTAMP
    # ==================================================
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    # ==================================================
    # META
    # ==================================================
    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Order Status Audit Log"
        verbose_name_plural = "Order Status Audit Logs"
        indexes = [
            models.Index(fields=["order", "created_at"]),
        ]

    # ==================================================
    # STRING REPRESENTATION
    # ==================================================
    def __str__(self) -> str:
        return (
            f"Order {self.order.reference}: "
            f"{self.previous_status or 'created'} → {self.new_status}"
        )
