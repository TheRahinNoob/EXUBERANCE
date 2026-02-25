from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Tuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from store.models import Order, OrderItem, ProductVariant
from store.services.order_audit_service import log_order_status_change
from store.services.meta_capi_service import send_meta_purchase_event


# ==================================================
# DELIVERY CHARGE RULES (SINGLE SOURCE OF TRUTH)
# ==================================================
DELIVERY_CHARGE_MAP: Dict[str, Decimal] = {
    Order.DELIVERY_INSIDE_DHAKA: Decimal("80.00"),
    Order.DELIVERY_OUTSIDE_DHAKA: Decimal("150.00"),
}


# ==================================================
# INTERNAL HELPERS
# ==================================================

def _coerce_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({field_name: f"{field_name.replace('_', ' ').title()} must be an integer."})


def _normalize_customer_str(value: Any, field: str, *, max_len: int | None = None) -> str:
    token = str(value or "").strip()
    token = " ".join(token.split())
    if not token:
        raise ValidationError({field: f"{field.replace('_', ' ').title()} is required."})
    if max_len is not None and len(token) > max_len:
        raise ValidationError({field: f"{field.replace('_', ' ').title()} is too long."})
    return token


def _normalize_items(items: Any) -> List[Dict[str, int]]:
    """
    Normalizes input items and aggregates duplicates by variant_id.
    Input shape expected:
      [{"variant_id": 1, "quantity": 2}, ...]
    """
    if not isinstance(items, list) or not items:
        raise ValidationError({"items": "Order must contain at least one item."})

    aggregated: Dict[int, int] = {}

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValidationError({"items": f"Invalid item at index {idx}."})

        if "variant_id" not in item or "quantity" not in item:
            raise ValidationError({"items": f"Each item must contain variant_id and quantity (index {idx})."})

        variant_id = _coerce_int(item.get("variant_id"), "variant_id")
        quantity = _coerce_int(item.get("quantity"), "quantity")

        if variant_id <= 0:
            raise ValidationError({"variant_id": "variant_id must be a positive integer."})
        if quantity <= 0:
            raise ValidationError({"quantity": "Quantity must be greater than zero."})

        aggregated[variant_id] = aggregated.get(variant_id, 0) + quantity

    return [{"variant_id": vid, "quantity": qty} for vid, qty in aggregated.items()]


def _compute_delivery_charge(delivery_area: str) -> Decimal:
    if delivery_area not in DELIVERY_CHARGE_MAP:
        raise ValidationError({"delivery_area": "Invalid delivery area."})
    return DELIVERY_CHARGE_MAP[delivery_area]


def _lock_variants(variant_ids: List[int]) -> Dict[int, ProductVariant]:
    """
    Lock all variants referenced by the order to prevent race conditions.
    Returns a map: variant_id -> ProductVariant (with product selected).
    """
    variants = (
        ProductVariant.objects.select_for_update()
        .select_related("product")
        .filter(id__in=variant_ids)
    )

    found_ids = set(variants.values_list("id", flat=True))
    missing = [vid for vid in variant_ids if vid not in found_ids]
    if missing:
        raise ValidationError({"items": f"One or more product variants do not exist: {missing}"})

    return {v.id: v for v in variants}


def _validate_stock(variant_map: Dict[int, ProductVariant], normalized_items: List[Dict[str, int]]) -> None:
    for item in normalized_items:
        variant = variant_map[item["variant_id"]]
        qty = item["quantity"]
        if variant.stock < qty:
            raise ValidationError(
                {
                    "stock": (
                        f"{variant.product.name} "
                        f"({variant.size}/{variant.color}) has insufficient stock."
                    )
                }
            )


# ==================================================
# CREATE ORDER (CANONICAL ENTRY POINT)
# ==================================================
@transaction.atomic
def create_order(
    *,
    name: str,
    phone: str,
    address: str,
    city: str,
    delivery_area: str,
    items: list[dict],
) -> Order:
    """
    Canonical order creation entry point.

    Guarantees:
    - Full validation before mutation
    - Aggregates duplicate variant lines
    - Row-level locking on stock
    - Atomic behavior
    - Immutable order item snapshot
    - Delivery charge auto-calculated
    - total_price persisted as snapshot (service is source of truth)
    - Audit log appended
    """

    # 1) Normalize input
    customer_name = _normalize_customer_str(name, "name", max_len=200)
    customer_phone = _normalize_customer_str(phone, "phone", max_len=20)
    customer_address = _normalize_customer_str(address, "address")
    customer_city = _normalize_customer_str(city, "city", max_len=120)

    normalized_items = _normalize_items(items)
    delivery_charge = _compute_delivery_charge(delivery_area)

    # 2) Lock variants + validate stock
    variant_ids = [i["variant_id"] for i in normalized_items]
    variant_map = _lock_variants(variant_ids)
    _validate_stock(variant_map, normalized_items)

    # 3) Create order (pending)
    order = Order.objects.create(
        name=customer_name,
        phone=customer_phone,
        address=customer_address,
        city=customer_city,
        delivery_area=delivery_area,
        delivery_charge=delivery_charge,
        total_price=Decimal("0.00"),  # set properly after items snapshot
    )

    items_total = Decimal("0.00")

    # 4) Snapshot items + deduct stock
    for item in normalized_items:
        variant = variant_map[item["variant_id"]]
        qty = item["quantity"]

        # Deduct stock safely
        variant.stock -= qty
        variant.save(update_fields=["stock"])

        price = variant.product.price
        line_total = price * qty
        items_total += line_total

        OrderItem.objects.create(
            order=order,
            product=variant.product,
            variant=variant,
            product_name=variant.product.name,
            size=variant.size,
            color=variant.color,
            price=price,
            quantity=qty,
        )

    # 5) Persist total snapshot
    order.total_price = items_total + delivery_charge
    order.save(update_fields=["total_price"])

    # 6) Audit log
    log_order_status_change(
        order=order,
        previous_status=None,
        new_status=order.status,
        actor_type="system",
        actor_identifier="checkout",
    )

    return order


# ==================================================
# INTERNAL STATE TRANSITION HELPER
# ==================================================
@transaction.atomic
def _transition_order(
    *,
    order: Order,
    to_status: str,
    actor_type: str,
    actor_identifier: str,
) -> bool:
    """
    Enforces:
    - row locking on the order
    - state machine validation
    - audit log append
    """
    locked = Order.objects.select_for_update().get(pk=order.pk)
    from_status = locked.status

    if not locked.can_transition_to(to_status):
        return False

    # transition_to() is safe because Order.save() won't touch totals anymore
    locked.transition_to(to_status)

    log_order_status_change(
        order=locked,
        previous_status=from_status,
        new_status=to_status,
        actor_type=actor_type,
        actor_identifier=actor_identifier,
    )

    return True


# ==================================================
# CONFIRM ORDER ✅ META PURCHASE (AFTER COMMIT)
# ==================================================
@transaction.atomic
def confirm_order(
    *,
    order: Order,
    actor_type: str,
    actor_identifier: str,
) -> bool:
    """
    Confirm order and emit Meta Purchase event.

    IMPORTANT:
    - Meta call is a side effect.
    - It runs ONLY AFTER the DB transaction successfully commits,
      preventing "sent event but DB rolled back" inconsistency.
    """
    transitioned = _transition_order(
        order=order,
        to_status=Order.STATUS_CONFIRMED,
        actor_type=actor_type,
        actor_identifier=actor_identifier,
    )

    if transitioned:
        # Side effect AFTER commit
        transaction.on_commit(lambda: send_meta_purchase_event(order))

    return transitioned


# ==================================================
# SHIP ORDER
# ==================================================
def ship_order(
    *,
    order: Order,
    actor_type: str,
    actor_identifier: str,
) -> bool:
    return _transition_order(
        order=order,
        to_status=Order.STATUS_SHIPPED,
        actor_type=actor_type,
        actor_identifier=actor_identifier,
    )


# ==================================================
# DELIVER ORDER
# ==================================================
def deliver_order(
    *,
    order: Order,
    actor_type: str,
    actor_identifier: str,
) -> bool:
    return _transition_order(
        order=order,
        to_status=Order.STATUS_DELIVERED,
        actor_type=actor_type,
        actor_identifier=actor_identifier,
    )


# ==================================================
# CANCEL ORDER (STOCK-SAFE)
# ==================================================
@transaction.atomic
def cancel_order(
    *,
    order: Order,
    actor_type: str,
    actor_identifier: str,
) -> bool:
    """
    Cancel order safely:
    - lock order + related variants
    - restore stock
    - enforce state machine
    - audit log append
    """

    locked = (
        Order.objects.select_for_update()
        .prefetch_related("items__variant")
        .get(pk=order.pk)
    )

    if locked.status == Order.STATUS_CANCELLED:
        return False

    if not locked.can_transition_to(Order.STATUS_CANCELLED):
        return False

    # Restore stock safely
    for item in locked.items.all():
        variant = item.variant
        variant.stock += item.quantity
        variant.save(update_fields=["stock"])

    old_status = locked.status
    locked.transition_to(Order.STATUS_CANCELLED)

    log_order_status_change(
        order=locked,
        previous_status=old_status,
        new_status=Order.STATUS_CANCELLED,
        actor_type=actor_type,
        actor_identifier=actor_identifier,
    )

    return True