from django.db import models
from .order import Order


class OrderStatusAuditLog(models.Model):
    class ActorType(models.TextChoices):
        SYSTEM = "system", "System"
        ADMIN = "admin", "Admin"
        CUSTOMER = "customer", "Customer"

    order = models.ForeignKey(
        Order,
        related_name="status_logs",
        on_delete=models.CASCADE,
    )

    from_status = models.CharField(
        max_length=20,
        choices=Order.STATUS_CHOICES,
    )
    to_status = models.CharField(
        max_length=20,
        choices=Order.STATUS_CHOICES,
    )

    actor_type = models.CharField(
        max_length=20,
        choices=ActorType.choices,
    )
    actor_identifier = models.CharField(
        max_length=255,
        help_text="admin:5 | system | customer:+8801XXXXXXXXX",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.order.reference}: {self.from_status} → {self.to_status}"
