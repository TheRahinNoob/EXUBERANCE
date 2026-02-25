from __future__ import annotations

from decimal import Decimal
from typing import Dict, Set

from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError

from .product import Product, ProductVariant


class Order(models.Model):
    """
    Canonical Order model.

    IMPORTANT DESIGN DECISION (production-safe):
    - `total_price` is treated as a persisted snapshot set by the service layer.
    - The model does NOT auto-recalculate totals inside `save()`.
      (Auto-recalc can accidentally overwrite totals during status-only updates.)
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

    TERMINAL_STATES = {STATUS_DELIVERED, STATUS_CANCELLED}

    # ==================================================
    # CORE IDENTIFIER
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
    city = models.CharField(max_length=120)
    delivery_area = models.CharField(
        max_length=20,
        choices=DELIVERY_AREA_CHOICES,
    )

    # ==================================================
    # FINANCIAL SNAPSHOT
    # ==================================================
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Final payable amount snapshot (items subtotal + delivery charge)",
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
            models.Index(fields=["phone"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(total_price__gte=0),
                name="order_total_price_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(delivery_charge__gte=0),
                name="order_delivery_charge_non_negative",
            ),
        ]

    # ==================================================
    # VALIDATION
    # ==================================================
    def clean(self) -> None:
        # Basic sanitation
        if not self.name or not self.name.strip():
            raise ValidationError({"name": "Customer name is required."})
        self.name = " ".join(self.name.strip().split())

        if not self.phone or not self.phone.strip():
            raise ValidationError({"phone": "Phone number is required."})
        self.phone = " ".join(self.phone.strip().split())

        if not self.address or not self.address.strip():
            raise ValidationError({"address": "Address is required."})
        self.address = self.address.strip()

        if not self.city or not self.city.strip():
            raise ValidationError({"city": "City is required."})
        self.city = " ".join(self.city.strip().split())

        # Ensure delivery_area is valid choice
        allowed_areas = {c[0] for c in self.DELIVERY_AREA_CHOICES}
        if self.delivery_area not in allowed_areas:
            raise ValidationError({"delivery_area": "Invalid delivery area."})

        # Financial sanity (DB constraints also protect)
        if self.delivery_charge is None or self.delivery_charge < 0:
            raise ValidationError({"delivery_charge": "Delivery charge cannot be negative."})

        if self.total_price is None or self.total_price < 0:
            raise ValidationError({"total_price": "Total price cannot be negative."})

    # ==================================================
    # SAVE
    # ==================================================
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_reference()

        # DO NOT auto-recompute total_price here.
        # Service layer is the single source of truth for financial snapshots.
        self.full_clean()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_reference() -> str:
        # Fast, collision-resistant enough for typical ecommerce scale.
        # Uniqueness is enforced by DB + retry loop.
        while True:
            ref = f"ORD-{get_random_string(10).upper()}"
            if not Order.objects.filter(reference=ref).exists():
                return ref

    # ==================================================
    # COMPUTED HELPERS (READ-ONLY)
    # ==================================================
    @property
    def subtotal(self) -> Decimal:
        """
        Live computed subtotal from OrderItem snapshots.
        (Use with care: it hits DB unless items are prefetched.)
        """
        return sum((item.line_total for item in self.items.all()), Decimal("0.00"))

    @property
    def computed_total(self) -> Decimal:
        """
        Live computed total = subtotal + delivery_charge.
        This is NOT persisted automatically.
        """
        return self.subtotal + (self.delivery_charge or Decimal("0.00"))

    # ==================================================
    # STATE MACHINE
    # ==================================================
    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status: str) -> None:
        if not self.can_transition_to(new_status):
            raise ValidationError(
                {
                    "status": (
                        f"Order cannot transition from '{self.status}' "
                        f"to '{new_status}'."
                    )
                }
            )

        # This is safe now because save() does not mutate totals.
        self.status = new_status
        self.updated_at = timezone.now()
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
    """
    Immutable snapshot of what was purchased.

    Notes:
    - Product/Variant are PROTECT so history stays intact.
    - Snapshot fields (product_name, size, color, price) ensure
      old orders remain readable even if catalog changes.
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
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["variant"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=1),
                name="order_item_quantity_gte_1",
            ),
            models.CheckConstraint(
                check=models.Q(price__gte=0),
                name="order_item_price_non_negative",
            ),
            # Prevent accidental duplicate lines for same variant in same order
            models.UniqueConstraint(
                fields=["order", "variant"],
                name="uniq_order_variant_line",
            ),
        ]

    def clean(self) -> None:
        if not self.product_name or not self.product_name.strip():
            raise ValidationError({"product_name": "Product name snapshot is required."})
        self.product_name = " ".join(self.product_name.strip().split())

        if not self.size or not str(self.size).strip():
            raise ValidationError({"size": "Size snapshot is required."})
        self.size = " ".join(str(self.size).strip().split())

        if not self.color or not str(self.color).strip():
            raise ValidationError({"color": "Color snapshot is required."})
        self.color = " ".join(str(self.color).strip().split())

        if self.quantity is None or self.quantity < 1:
            raise ValidationError({"quantity": "Quantity must be at least 1."})

        if self.price is None or self.price < 0:
            raise ValidationError({"price": "Price cannot be negative."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def line_total(self) -> Decimal:
        return self.price * self.quantity

    def __str__(self) -> str:
        return f"{self.product_name} × {self.quantity}"