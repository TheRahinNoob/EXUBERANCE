from __future__ import annotations

from typing import Iterable

from django.db import transaction
from django.core.exceptions import ValidationError

from store.models import (
    Product,
    ProductAttribute,
    ProductAttributeValue,
)

# ==================================================
# PRODUCT ATTRIBUTE SERVICE
# ==================================================
# DESIGN PRINCIPLES:
# - Service-layer ONLY (no serializers, no views)
# - Atomic & race-safe
# - Single source of truth
# - Explicit validation
# - Admin-safe & idempotent
# - Future-proof ordering
# ==================================================


# ==================================================
# INTERNAL VALIDATORS (PRIVATE)
# ==================================================

def _validate_product(product: Product) -> None:
    if not isinstance(product, Product):
        raise ValidationError({"product": "Invalid product."})


def _validate_value(value: str) -> str:
    if not value or not value.strip():
        raise ValidationError({"value": "Attribute value is required."})
    return value.strip()


def _validate_ordering(ordering: int | None) -> int | None:
    if ordering is None:
        return None
    try:
        return int(ordering)
    except (TypeError, ValueError):
        raise ValidationError({"ordering": "Invalid ordering value."})


def _validate_ordered_ids(ids: Iterable[int]) -> list[int]:
    if not isinstance(ids, (list, tuple)):
        raise ValidationError(
            {"ordered_ids": "ordered_ids must be a list of integers."}
        )

    if not ids:
        raise ValidationError(
            {"ordered_ids": "ordered_ids cannot be empty."}
        )

    try:
        ids = [int(i) for i in ids]
    except (TypeError, ValueError):
        raise ValidationError(
            {"ordered_ids": "ordered_ids must contain only integers."}
        )

    if len(ids) != len(set(ids)):
        raise ValidationError(
            {"ordered_ids": "Duplicate IDs are not allowed."}
        )

    return ids


# ==================================================
# CREATE OR UPDATE ATTRIBUTE VALUE (UPSERT)
# ==================================================

@transaction.atomic
def create_or_update_attribute_value(
    *,
    product: Product,
    attribute_id: int,
    value: str,
    ordering: int = 0,
) -> ProductAttributeValue:
    """
    Assign or update an attribute value for a product.

    GUARANTEES:
    - One attribute per product (DB enforced)
    - Idempotent
    - Atomic & race-safe
    - Normalized value
    """

    _validate_product(product)
    value = _validate_value(value)
    ordering = _validate_ordering(ordering) or 0

    try:
        attribute = (
            ProductAttribute.objects
            .select_for_update()
            .get(pk=attribute_id)
        )
    except ProductAttribute.DoesNotExist:
        raise ValidationError({"attribute": "Invalid attribute."})

    pav, _ = ProductAttributeValue.objects.update_or_create(
        product=product,
        attribute=attribute,
        defaults={
            "value": value,
            "ordering": ordering,
        },
    )

    return pav


# ==================================================
# UPDATE ATTRIBUTE VALUE
# ==================================================

@transaction.atomic
def update_product_attribute_value(
    *,
    pav: ProductAttributeValue,
    value: str,
    ordering: int | None = None,
) -> ProductAttributeValue:
    """
    Update attribute value and/or ordering.

    product & attribute are IMMUTABLE.
    """

    if not isinstance(pav, ProductAttributeValue):
        raise ValidationError(
            {"attribute_value": "Invalid attribute value."}
        )

    value = _validate_value(value)
    ordering = _validate_ordering(ordering)

    updated_fields: list[str] = []

    if pav.value != value:
        pav.value = value
        updated_fields.append("value")

    if ordering is not None and pav.ordering != ordering:
        pav.ordering = ordering
        updated_fields.append("ordering")

    if updated_fields:
        pav.save(update_fields=updated_fields)

    return pav


# ==================================================
# DELETE ATTRIBUTE VALUE
# ==================================================

@transaction.atomic
def delete_product_attribute_value(
    *,
    pav: ProductAttributeValue,
) -> None:
    if not isinstance(pav, ProductAttributeValue):
        raise ValidationError(
            {"attribute_value": "Invalid attribute value."}
        )

    pav.delete()


# ==================================================
# BULK REORDER ATTRIBUTE VALUES (DRAG & DROP)
# ==================================================

@transaction.atomic
def reorder_product_attribute_values(
    *,
    product: Product,
    ordered_pav_ids: Iterable[int],
) -> None:
    """
    Reorder attribute values for a product.

    - IDs must exactly match product attributes
    - Uses gapped ordering (10, 20, 30…)
    - Minimal writes
    """

    _validate_product(product)
    ordered_ids = _validate_ordered_ids(ordered_pav_ids)

    pavs = list(
        ProductAttributeValue.objects
        .select_for_update()
        .filter(product=product)
    )

    pav_map = {pav.id: pav for pav in pavs}

    if set(pav_map.keys()) != set(ordered_ids):
        raise ValidationError(
            {"ordering": "Attribute IDs do not match product attributes."}
        )

    updates: list[ProductAttributeValue] = []

    for index, pav_id in enumerate(ordered_ids):
        pav = pav_map[pav_id]
        new_ordering = index * 10

        if pav.ordering != new_ordering:
            pav.ordering = new_ordering
            updates.append(pav)

    if updates:
        ProductAttributeValue.objects.bulk_update(
            updates,
            fields=["ordering"],
        )
