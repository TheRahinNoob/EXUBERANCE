from __future__ import annotations

from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

from store.models import Product, ProductVariant


# ==================================================
# PRODUCT VARIANT SERVICE
# ==================================================
# Rules:
# - Business logic ONLY
# - Atomic
# - DB is the final source of truth
# - Safe against race conditions
# ==================================================


@transaction.atomic
def create_product_variant(
    *,
    product: Product,
    size: str,
    color: str,
    stock: int,
) -> ProductVariant:
    """
    Create a new product variant.

    Rules:
    - (product, size, color) must be unique
    - Stock >= 0
    """

    if not isinstance(product, Product):
        raise ValidationError({"product": "Invalid product."})

    if not size:
        raise ValidationError({"size": "Size is required."})

    if not color or not color.strip():
        raise ValidationError({"color": "Color is required."})

    try:
        stock = int(stock)
    except (TypeError, ValueError):
        raise ValidationError({"stock": "Stock must be an integer."})

    if stock < 0:
        raise ValidationError({"stock": "Stock cannot be negative."})

    try:
        return ProductVariant.objects.create(
            product=product,
            size=size,
            color=color.strip(),
            stock=stock,
        )
    except IntegrityError:
        # 🔒 DB-level safety for race conditions
        raise ValidationError(
            "Variant with this size and color already exists."
        )


@transaction.atomic
def update_product_variant_stock(
    *,
    variant: ProductVariant,
    stock: int,
) -> ProductVariant:
    """
    Update variant stock.

    Rules:
    - Stock >= 0
    """

    if not isinstance(variant, ProductVariant):
        raise ValidationError({"variant": "Invalid variant."})

    try:
        stock = int(stock)
    except (TypeError, ValueError):
        raise ValidationError({"stock": "Stock must be an integer."})

    if stock < 0:
        raise ValidationError({"stock": "Stock cannot be negative."})

    variant.stock = stock
    variant.save(update_fields=["stock"])

    return variant


@transaction.atomic
def delete_product_variant(
    *,
    variant: ProductVariant,
) -> None:
    """
    Delete a product variant.

    Rules:
    - Safe delete
    """

    if not isinstance(variant, ProductVariant):
        raise ValidationError({"variant": "Invalid variant."})

    variant.delete()
