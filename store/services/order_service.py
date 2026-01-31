from django.db import transaction
from rest_framework.exceptions import ValidationError

from store.models import (
    Order,
    OrderItem,
    ProductVariant,
)
from store.services.order_audit_service import (
    log_order_status_change,
)

# ✅ NEW: Meta Conversions API (isolated side effect)
from store.services.meta_capi_service import (
    send_meta_purchase_event,
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
    items: list[dict],
) -> Order:
    """
    Canonical order creation entry point.

    Guarantees:
    - Full validation before mutation
    - Row-level locking on stock
    - Atomic behavior
    - Immutable order item snapshot
    - Audit-safe
    """

    if not items:
        raise ValidationError({
            "items": "Order must contain at least one item."
        })

    # -----------------------------
    # 1. NORMALIZE & VALIDATE INPUT
    # -----------------------------
    normalized_items: list[dict] = []

    for item in items:
        try:
            variant_id = int(item["variant_id"])
            quantity = int(item["quantity"])
        except (KeyError, TypeError, ValueError):
            raise ValidationError({
                "items": "Invalid item format."
            })

        if quantity <= 0:
            raise ValidationError({
                "quantity": "Quantity must be greater than zero."
            })

        normalized_items.append({
            "variant_id": variant_id,
            "quantity": quantity,
        })

    # -----------------------------
    # 2. LOCK PRODUCT VARIANTS
    # -----------------------------
    variant_ids = [i["variant_id"] for i in normalized_items]

    variants = (
        ProductVariant.objects
        .select_for_update()
        .select_related("product")
        .filter(id__in=variant_ids)
    )

    if variants.count() != len(variant_ids):
        raise ValidationError({
            "items": "One or more product variants do not exist."
        })

    variant_map = {v.id: v for v in variants}

    for item in normalized_items:
        variant = variant_map[item["variant_id"]]
        if variant.stock < item["quantity"]:
            raise ValidationError({
                "stock": (
                    f"{variant.product.name} "
                    f"({variant.size}/{variant.color}) "
                    "has insufficient stock."
                )
            })

    # -----------------------------
    # 3. CREATE ORDER (PENDING)
    # -----------------------------
    order = Order.objects.create(
        name=name,
        phone=phone,
        address=address,
        total_price=0,
    )

    total_price = 0

    # -----------------------------
    # 4. SNAPSHOT ITEMS + DEDUCT STOCK
    # -----------------------------
    for item in normalized_items:
        variant = variant_map[item["variant_id"]]
        quantity = item["quantity"]

        # Deduct stock safely
        variant.stock -= quantity
        variant.save(update_fields=["stock"])

        price = variant.product.price
        line_total = price * quantity
        total_price += line_total

        OrderItem.objects.create(
            order=order,
            product=variant.product,
            variant=variant,
            product_name=variant.product.name,
            size=variant.size,
            color=variant.color,
            price=price,
            quantity=quantity,
        )

    order.total_price = total_price
    order.save(update_fields=["total_price"])

    # -----------------------------
    # 5. INITIAL AUDIT LOG
    # -----------------------------
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
    Single authoritative transition handler.

    Responsibilities:
    - Row-level lock
    - Transition validation
    - State persistence
    - Audit logging
    """

    order = Order.objects.select_for_update().get(pk=order.pk)
    from_status = order.status

    if not order.can_transition_to(to_status):
        return False

    order.transition_to(to_status)

    log_order_status_change(
        order=order,
        previous_status=from_status,
        new_status=to_status,
        actor_type=actor_type,
        actor_identifier=actor_identifier,
    )

    return True


# ==================================================
# CONFIRM ORDER  ✅ META PURCHASE LIVES HERE
# ==================================================
def confirm_order(
    *,
    order: Order,
    actor_type: str,
    actor_identifier: str,
) -> bool:
    """
    Confirms an order.

    This is the ONLY place where:
    - Payment is considered successful
    - Purchase becomes real
    - Meta Purchase event is fired

    Guaranteed:
    - Fires once
    - Never fires on retries
    - Never fires on invalid transitions
    """

    transitioned = _transition_order(
        order=order,
        to_status=Order.STATUS_CONFIRMED,
        actor_type=actor_type,
        actor_identifier=actor_identifier,
    )

    if transitioned:
        # 🔥 SIDE EFFECT (SAFE, POST-COMMIT INTENT)
        send_meta_purchase_event(order)

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
    order = (
        Order.objects
        .select_for_update()
        .prefetch_related("items__variant")
        .get(pk=order.pk)
    )

    if order.status == Order.STATUS_CANCELLED:
        return False

    if not order.can_transition_to(Order.STATUS_CANCELLED):
        return False

    # Restore stock safely
    for item in order.items.all():
        variant = item.variant
        variant.stock += item.quantity
        variant.save(update_fields=["stock"])

    old_status = order.status
    order.transition_to(Order.STATUS_CANCELLED)

    log_order_status_change(
        order=order,
        previous_status=old_status,
        new_status=Order.STATUS_CANCELLED,
        actor_type=actor_type,
        actor_identifier=actor_identifier,
    )

    return True
