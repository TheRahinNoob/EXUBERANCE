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
    # DELIVERY CONFIGURATION (SINGLE SOURCE OF TRUTH)
    # ==================================================
    DELIVERY_INSIDE_DHAKA = "inside_dhaka"
    DELIVERY_OUTSIDE_DHAKA = "outside_dhaka"

    DELIVERY_AREA_CHOICES = (
        (DELIVERY_INSIDE_DHAKA, "Inside Dhaka"),
        (DELIVERY_OUTSIDE_DHAKA, "Outside Dhaka"),
    )

    DELIVERY_CHARGE_MAP = {
        DELIVERY_INSIDE_DHAKA: Decimal("80.00"),
        DELIVERY_OUTSIDE_DHAKA: Decimal("150.00"),
    }

    # ==================================================
    # STATUS CONSTANTS
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
    # STATE MACHINE
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
    )

    # ==================================================
    # CUSTOMER SNAPSHOT
    # ==================================================
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=120)  # ✅ Added city field
    delivery_area = models.CharField(
        max_length=20,
        choices=DELIVERY_AREA_CHOICES,
    )

    # ==================================================
    # FINANCIALS
    # ==================================================
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Final payable amount (items subtotal + delivery charge)",
    )

    delivery_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # ==================================================
    # STATUS
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
    # SAVE OVERRIDE
    # ==================================================
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_reference()

        # Ensure total_price integrity
        if self.pk:  # only recalc on updates
            self.total_price = self.subtotal + self.delivery_charge

        super().save(*args, **kwargs)

    @staticmethod
    def _generate_reference() -> str:
        while True:
            ref = f"ORD-{get_random_string(10).upper()}"
            if not Order.objects.filter(reference=ref).exists():
                return ref

    # ==================================================
    # COMPUTED HELPERS
    # ==================================================
    @property
    def subtotal(self) -> Decimal:
        """
        Sum of all order items.
        """
        return sum(
            (item.line_total for item in self.items.all()),
            Decimal("0.00"),
        )

    # ==================================================
    # STATE MACHINE
    # ==================================================
    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.ALLOWED_TRANSITIONS.get(
            self.status, set()
        )

    def transition_to(self, new_status: str) -> None:
        if not self.can_transition_to(new_status):
            raise ValidationError({
                "status": (
                    f"Order cannot transition from "
                    f"'{self.status}' to '{new_status}'."
                )
            })

        self.status = new_status
        self.save(update_fields=["status", "updated_at"])

    @property
    def is_terminal(self) -> bool:
        return self.status in self.TERMINAL_STATES

    def __str__(self) -> str:
        return f"{self.reference} ({self.status})"


# ======================================================
# ORDER ITEM
# ======================================================
class OrderItem(models.Model):
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

    @property
    def line_total(self) -> Decimal:
        return self.price * self.quantity

    def __str__(self) -> str:
        return f"{self.product_name} × {self.quantity}"
