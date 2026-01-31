from __future__ import annotations

from django.db import transaction
from django.core.exceptions import ValidationError

from store.models import ProductAttribute

# ==================================================
# PRODUCT ATTRIBUTE DEFINITION SERVICE
# ==================================================
# CANONICAL RULES:
# --------------------------------------------------
# - Service layer ONLY (no serializers, no views)
# - Atomic & idempotent
# - Case-insensitive uniqueness
# - Name normalization enforced here
# - NO HARD DELETE (ever)
# - Attributes are ARCHIVED via is_active
# - Existing products must NEVER break
# ==================================================


# ==================================================
# INTERNAL HELPERS
# ==================================================

def _normalize_name(name: str) -> str:
    if not name or not name.strip():
        raise ValidationError({"name": "Attribute name is required."})
    return name.strip().title()


def _validate_ordering(ordering: int | None) -> int:
    if ordering is None:
        return 0
    try:
        return int(ordering)
    except (TypeError, ValueError):
        raise ValidationError({"ordering": "Invalid ordering value."})


def _assert_unique_name(
    name: str,
    *,
    exclude_id: int | None = None,
) -> None:
    """
    Enforce case-insensitive uniqueness.
    Works correctly even with soft-deleted records.
    """
    qs = ProductAttribute.objects.filter(name__iexact=name)
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)

    if qs.exists():
        raise ValidationError(
            {"name": f"Attribute '{name}' already exists."}
        )


# ==================================================
# CREATE ATTRIBUTE DEFINITION
# ==================================================

@transaction.atomic
def create_attribute_definition(
    *,
    name: str,
    ordering: int = 0,
) -> ProductAttribute:
    """
    Create a new global product attribute definition.

    Guarantees:
    - Case-insensitive uniqueness
    - Normalized name
    - Always active on creation
    """

    normalized_name = _normalize_name(name)
    ordering = _validate_ordering(ordering)

    _assert_unique_name(normalized_name)

    attribute = ProductAttribute.objects.create(
        name=normalized_name,
        ordering=ordering,
        is_active=True,
    )

    return attribute


# ==================================================
# UPDATE ATTRIBUTE DEFINITION
# ==================================================

@transaction.atomic
def update_attribute_definition(
    *,
    attribute: ProductAttribute,
    name: str | None = None,
    ordering: int | None = None,
) -> ProductAttribute:
    """
    Update attribute definition.

    Editable:
    - name
    - ordering

    NOT editable:
    - is_active (separate operation)
    """

    if not isinstance(attribute, ProductAttribute):
        raise ValidationError(
            {"attribute": "Invalid product attribute."}
        )

    updated_fields: list[str] = []

    if name is not None:
        normalized_name = _normalize_name(name)

        _assert_unique_name(
            normalized_name,
            exclude_id=attribute.id,
        )

        if attribute.name != normalized_name:
            attribute.name = normalized_name
            updated_fields.append("name")

    if ordering is not None:
        ordering = _validate_ordering(ordering)
        if attribute.ordering != ordering:
            attribute.ordering = ordering
            updated_fields.append("ordering")

    if not updated_fields:
        raise ValidationError(
            {"message": "No fields provided for update."}
        )

    attribute.save(update_fields=updated_fields)
    return attribute


# ==================================================
# ARCHIVE ATTRIBUTE DEFINITION (SOFT DELETE)
# ==================================================

@transaction.atomic
def archive_attribute_definition(
    *,
    attribute: ProductAttribute,
) -> ProductAttribute:
    """
    Soft delete (archive) attribute definition.

    Guarantees:
    - Existing product attribute values remain valid
    - Attribute disappears from admin selection lists
    - Operation is idempotent
    - No historical data loss
    """

    if not isinstance(attribute, ProductAttribute):
        raise ValidationError(
            {"attribute": "Invalid product attribute."}
        )

    # Idempotent safety
    if not attribute.is_active:
        return attribute

    attribute.is_active = False
    attribute.save(update_fields=["is_active"])

    return attribute
