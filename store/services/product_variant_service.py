from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set, TypedDict

from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError

from store.models import Product, ProductVariant


# ==================================================
# PRODUCT VARIANT SERVICE
# ==================================================
# Goals:
# - Business logic only
# - Atomic + race-safe
# - DB is source of truth
# - Admin UX friendly
# - NO dependency on ProductVariant.SIZE_CHOICES
#
# IMPORTANT:
# - ProductVariant.size is now a free-form token (numeric, alpha, mixed)
# - We normalize size/color to reduce duplicates (" blue " vs "Blue")
# ==================================================


# ==================================================
# TYPES
# ==================================================

class VariantDTO(TypedDict):
    id: int
    size: str
    color: str
    stock: int


class BulkCreateResult(TypedDict):
    color: str
    default_stock: int
    created: List[VariantDTO]
    skipped_existing: List[str]


# ==================================================
# NORMALIZATION HELPERS
# ==================================================

def _collapse_ws(value: str) -> str:
    return " ".join(value.split())


def _normalize_size(size: Any) -> str:
    """
    Normalize size tokens:

    - trims whitespace
    - collapses internal whitespace
    - uppercases simple alpha sizes ("m" -> "M", "xl" -> "XL")
    - preserves numeric/mixed sizes ("38", "38R", "One Size")
    """
    token = _collapse_ws(str(size or "").strip())
    if not token:
        return ""
    if token.isalpha():
        return token.upper()
    return token


def _normalize_color(color: Any) -> str:
    """
    Normalize color tokens to reduce duplicates:

    - trims + collapses whitespace
    - title-cases ("deep blue" -> "Deep Blue")
    """
    token = _collapse_ws(str(color or "").strip())
    if not token:
        return ""
    return token.title()


def _coerce_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(
            {field_name: f"{field_name.replace('_', ' ').title()} must be an integer."}
        )


def _validate_size_token(size: str) -> None:
    """
    Size is free-form, BUT we still enforce sanity to prevent garbage data.
    Accept examples:
    - "38", "40", "42"
    - "S", "M", "L", "XL"
    - "One Size"
    - "38R", "W32-L30"

    Reject:
    - empty
    - too long (DB field also limits)
    """
    if not size:
        raise ValidationError({"size": "Size is required."})

    if len(size) > 20:
        # keep this aligned with model max_length for size
        raise ValidationError({"size": "Size is too long."})


def _validate_color_token(color: str) -> None:
    if not color:
        raise ValidationError({"color": "Color is required."})
    if len(color) > 50:
        # keep aligned with model max_length for color
        raise ValidationError({"color": "Color is too long."})


def _validate_stock(stock: int) -> None:
    if stock < 0:
        raise ValidationError({"stock": "Stock cannot be negative."})


# ==================================================
# CREATE VARIANT (SINGLE)
# ==================================================

@transaction.atomic
def create_product_variant(
    *,
    product: Product,
    size: Any,
    color: Any,
    stock: Any,
) -> ProductVariant:
    """
    Create a new product variant.

    Guarantees:
    - normalized size/color
    - sane validation (no SIZE_CHOICES dependency)
    - stock >= 0
    - uniqueness enforced via DB constraints (product, size, color)
    """

    if not isinstance(product, Product):
        raise ValidationError({"product": "Invalid product."})

    normalized_size = _normalize_size(size)
    normalized_color = _normalize_color(color)

    _validate_size_token(normalized_size)
    _validate_color_token(normalized_color)

    stock_int = _coerce_int(stock, "stock")
    _validate_stock(stock_int)

    try:
        return ProductVariant.objects.create(
            product=product,
            size=normalized_size,
            color=normalized_color,
            stock=stock_int,
        )
    except IntegrityError:
        # DB-level safety for race conditions
        raise ValidationError({"detail": "Variant with this size and color already exists."})


# ==================================================
# BULK CREATE VARIANTS (ONE COLOR + MANY SIZES)
# ==================================================

@transaction.atomic
def bulk_create_product_variants(
    *,
    product: Product,
    color: Any,
    sizes: Iterable[Any] | None,
    default_stock: Any = 0,
) -> BulkCreateResult:
    """
    Bulk create variants for a single product + single color.

    Behavior:
    - idempotent: existing variants are skipped
    - validates all inputs before writing
    - de-dupes sizes preserving order
    - returns stable payload for frontend:
      {
        "color": "Blue",
        "default_stock": 0,
        "created": [{id,size,color,stock}, ...],
        "skipped_existing": ["38", "40"]
      }
    """

    if not isinstance(product, Product):
        raise ValidationError({"product": "Invalid product."})

    normalized_color = _normalize_color(color)
    _validate_color_token(normalized_color)

    stock_int = _coerce_int(default_stock, "default_stock")
    if stock_int < 0:
        raise ValidationError({"default_stock": "Default stock cannot be negative."})

    if sizes is None:
        raise ValidationError({"sizes": "Sizes must be provided as a list."})

    # Normalize + de-dupe (preserve order)
    normalized_sizes: List[str] = []
    seen: Set[str] = set()

    for s in sizes:
        token = _normalize_size(s)
        if not token:
            continue
        _validate_size_token(token)

        if token in seen:
            continue
        seen.add(token)
        normalized_sizes.append(token)

    if not normalized_sizes:
        raise ValidationError({"sizes": "Sizes must be a non-empty list."})

    # Pre-check existing (deterministic skipped list + fewer IntegrityErrors)
    existing_sizes = set(
        ProductVariant.objects.filter(
            product=product,
            color=normalized_color,
            size__in=normalized_sizes,
        ).values_list("size", flat=True)
    )

    created: List[VariantDTO] = []
    skipped_existing: List[str] = []

    for size_token in normalized_sizes:
        if size_token in existing_sizes:
            skipped_existing.append(size_token)
            continue

        try:
            v = ProductVariant.objects.create(
                product=product,
                size=size_token,
                color=normalized_color,
                stock=stock_int,
            )
            created.append(
                {
                    "id": v.id,
                    "size": v.size,
                    "color": v.color,
                    "stock": int(v.stock),
                }
            )
        except IntegrityError:
            # if a concurrent request created it, treat as skipped (idempotent)
            skipped_existing.append(size_token)

    return {
        "color": normalized_color,
        "default_stock": stock_int,
        "created": created,
        "skipped_existing": skipped_existing,
    }


# ==================================================
# UPDATE VARIANT STOCK
# ==================================================

@transaction.atomic
def update_product_variant_stock(
    *,
    variant: ProductVariant,
    stock: Any,
) -> ProductVariant:
    """
    Update variant stock safely.

    Rules:
    - Stock must be integer
    - Stock >= 0
    """

    if not isinstance(variant, ProductVariant):
        raise ValidationError({"variant": "Invalid variant."})

    stock_int = _coerce_int(stock, "stock")
    _validate_stock(stock_int)

    variant.stock = stock_int
    variant.save(update_fields=["stock"])

    return variant


# ==================================================
# DELETE VARIANT
# ==================================================

@transaction.atomic
def delete_product_variant(
    *,
    variant: ProductVariant,
) -> None:
    """
    Delete a product variant safely.

    Notes:
    - If referenced by OrderItem (PROTECT), raise a friendly ValidationError.
    """

    if not isinstance(variant, ProductVariant):
        raise ValidationError({"variant": "Invalid variant."})

    try:
        variant.delete()
    except ProtectedError:
        raise ValidationError(
            {"detail": "This variant cannot be deleted because it is used in existing orders."}
        )