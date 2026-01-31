# store/services/stock_service.py

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from store.models import ProductVariant


# ==================================================
# STOCK REDUCTION (LOCKED + SAFE)
# ==================================================
@transaction.atomic
def reduce_stock(variant_id: int, quantity: int) -> ProductVariant:
    """
    Safely reduces stock for a product variant.

    Guarantees:
    - Row-level locking (prevents overselling)
    - Atomic operation
    - Deterministic, frontend-safe errors
    """

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    try:
        variant = (
            ProductVariant.objects
            .select_for_update()
            .select_related("product")
            .get(id=variant_id)
        )
    except ObjectDoesNotExist:
        raise ValueError("Invalid product variant.")

    if variant.stock < quantity:
        raise ValueError(
            f"Insufficient stock for "
            f"{variant.product.name} "
            f"({variant.size}/{variant.color}). "
            f"Available: {variant.stock}"
        )

    variant.stock -= quantity
    variant.save(update_fields=["stock"])

    return variant


# ==================================================
# STOCK RESTORATION (USED ON CANCELLATION / FAILURES)
# ==================================================
@transaction.atomic
def restore_stock(variant_id: int, quantity: int) -> None:
    """
    Restores stock for a product variant.

    Used when:
    - Order is cancelled
    - Payment fails (future)
    """

    if quantity <= 0:
        return

    try:
        variant = ProductVariant.objects.select_for_update().get(
            id=variant_id
        )
    except ObjectDoesNotExist:
        # Variant might be deleted later; ignore safely
        return

    variant.stock += quantity
    variant.save(update_fields=["stock"])
