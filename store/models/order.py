from decimal import Decimal
from typing import Set, Dict

from django.db import models
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError

from .product import Product, ProductVariant


class Order(models.Model):
    """
    Canonical Order model.

    DESIGN PRINCIPLES:
    - Order lifecycle is governed by a strict state machine
    - State transitions are enforced at model + service layer
    - Order is account-agnostic (guest-friendly)
    - OrderItems are immutable snapshots
    """

    # ==================================================
    # STATUS CONSTANTS (SINGLE SOURCE OF TRUTH)
    # ==================================================
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    # ==================================================
    # STATE MACHINE DEFINITION
    # ==================================================
    ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
        STATUS_PENDING: {STATUS_CONFIRMED, STATUS_CANCELLED},
        STATUS_CONFIRMED: {STATUS_SHIPPED, STATUS_CANCELLED},
        STATUS_SHIPPED: {STATUS_DELIVERED},
        STATUS_DELIVERED: set(),
        STATUS_CANCELLED: set(),
    }

    TERMINAL_STATES = {
        STATUS_DELIVERED,
        STATUS_CANCELLED,
    }

    # ==================================================
    # CORE IDENTIFIERS
    # ==================================================
    reference = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        db_index=True,
        help_text="Human-friendly order reference",
    )

    # ==================================================
    # CUSTOMER SNAPSHOT (ACCOUNT-AGNOSTIC)
    # ==================================================
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.TextField()

    # ==================================================
    # FINANCIALS
    # ==================================================
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Final payable amount",
    )

    # ==================================================
    # STATUS / LIFECYCLE
    # ==================================================
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    # ==================================================
    # TIMESTAMPS
    # ==================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ==================================================
    # META
    # ==================================================
    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["reference"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    # ==================================================
    # SAVE OVERRIDE (REFERENCE GENERATION)
    # ==================================================
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_reference()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_reference() -> str:
        """
        Generates a unique, human-friendly order reference.
        Collision-safe.
        """
        while True:
            ref = f"ORD-{get_random_string(10).upper()}"
            if not Order.objects.filter(reference=ref).exists():
                return ref

    # ==================================================
    # STATE MACHINE CORE
    # ==================================================
    def can_transition_to(self, new_status: str) -> bool:
        """
        Checks whether a transition is allowed from current status.
        """
        return new_status in self.ALLOWED_TRANSITIONS.get(
            self.status, set()
        )

    def transition_error(self, new_status: str) -> str:
        return (
            f"Order cannot transition from "
            f"'{self.status}' to '{new_status}'."
        )

    def transition_to(self, new_status: str) -> None:
        """
        Performs a validated state transition.

        IMPORTANT:
        - This method ONLY mutates state
        - Side effects (stock, audit, payments)
          MUST live in service layer
        """
        if not self.can_transition_to(new_status):
            raise ValidationError({
                "status": self.transition_error(new_status)
            })

        self.status = new_status
        self.save(update_fields=["status", "updated_at"])

    # ==================================================
    # SEMANTIC HELPERS (USED EVERYWHERE)
    # ==================================================
    def can_confirm(self) -> bool:
        return self.can_transition_to(self.STATUS_CONFIRMED)

    def can_ship(self) -> bool:
        return self.can_transition_to(self.STATUS_SHIPPED)

    def can_deliver(self) -> bool:
        return self.can_transition_to(self.STATUS_DELIVERED)

    def can_cancel(self) -> bool:
        return self.can_transition_to(self.STATUS_CANCELLED)

    @property
    def is_terminal(self) -> bool:
        """
        Whether the order is in a terminal state.
        """
        return self.status in self.TERMINAL_STATES

    # ==================================================
    # DISPLAY / API HELPERS
    # ==================================================
    @property
    def customer_name(self) -> str:
        return self.name

    @property
    def customer_phone(self) -> str:
        return self.phone

    # ==================================================
    # STRING REPRESENTATION
    # ==================================================
    def __str__(self) -> str:
        return f"{self.reference} ({self.status})"


# ======================================================
# ORDER ITEM (IMMUTABLE SNAPSHOT)
# ======================================================
class OrderItem(models.Model):
    """
    Immutable snapshot of a purchased item.

    DESIGN:
    - Product / variant may change later
    - Snapshot preserves historical accuracy
    """

    order = models.ForeignKey(
        Order,
        related_name="items",
        on_delete=models.CASCADE,
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
    )

    # ------------------------------
    # SNAPSHOT FIELDS
    # ------------------------------
    product_name = models.CharField(max_length=255)
    size = models.CharField(max_length=50)
    color = models.CharField(max_length=50)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ("id",)

    # ------------------------------
    # COMPUTED
    # ------------------------------
    @property
    def line_total(self) -> Decimal:
        return self.price * self.quantity

    def __str__(self) -> str:
        return f"{self.product_name} × {self.quantity}"
