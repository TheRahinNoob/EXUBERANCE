from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional, Iterable

from django.db import transaction
from django.utils.text import slugify
from django.core.exceptions import ValidationError

import bleach
from bleach.css_sanitizer import CSSSanitizer

from store.models import Product, Category


# ==================================================
# PRODUCT SERVICE — SINGLE SOURCE OF TRUTH
# ==================================================
# RULES:
# - No request/response objects
# - No serializers
# - No permissions
# - All mutations are deterministic
# ==================================================


# ==================================================
# HTML SANITIZATION (ADMIN-SAFE, TYPOGRAPHY-FRIENDLY)
# ==================================================

ALLOWED_HTML_TAGS = [
    "p", "br",
    "strong", "em", "u", "s",
    "ul", "ol", "li",
    "h1", "h2", "h3", "h4",
    "blockquote",
    "span", "div",
    "a",
]

ALLOWED_HTML_ATTRIBUTES = {
    "*": ["class", "style"],
    "a": ["href", "rel", "target"],
}

ALLOWED_CSS_PROPERTIES = [
    "font-family",
    "font-size",
    "line-height",
    "color",
    "background-color",
    "text-align",
    "font-weight",
    "font-style",
    "text-decoration",
]

_css_sanitizer = CSSSanitizer(
    allowed_css_properties=ALLOWED_CSS_PROPERTIES
)


def sanitize_html(html: str) -> str:
    """
    Sanitizes admin-provided HTML while preserving
    typography-related inline styles.

    SECURITY GUARANTEES:
    - No JS execution
    - No layout breaking CSS
    - No remote resources
    """

    if not html:
        return ""

    cleaned = bleach.clean(
        html,
        tags=ALLOWED_HTML_TAGS,
        attributes=ALLOWED_HTML_ATTRIBUTES,
        css_sanitizer=_css_sanitizer,
        strip=True,
    )

    # Enforce safe anchor defaults
    cleaned = cleaned.replace(
        '<a ',
        '<a rel="noopener noreferrer" target="_blank" ',
    )

    return cleaned


# ==================================================
# PRODUCT CREATION
# ==================================================

@transaction.atomic
def create_product(
    *,
    name: str,
    slug: Optional[str],
    price,
    is_active: bool = True,
) -> Product:

    if not name or not name.strip():
        raise ValidationError({"name": "Product name is required."})

    try:
        price = Decimal(price)
    except (InvalidOperation, TypeError):
        raise ValidationError({"price": "Invalid price value."})

    if price < 0:
        raise ValidationError({"price": "Price cannot be negative."})

    final_slug = slugify(slug or name)

    if not final_slug:
        raise ValidationError({"slug": "Invalid slug."})

    if Product.objects.filter(slug=final_slug).exists():
        raise ValidationError({"slug": "Slug already exists."})

    return Product.objects.create(
        name=name.strip(),
        slug=final_slug,
        price=price,
        is_active=bool(is_active),
    )


# ==================================================
# PRODUCT BASIC INFO
# ==================================================

@transaction.atomic
def update_product_basic_info(
    *,
    product: Product,
    name: str,
    slug: str,
) -> Product:

    if not isinstance(product, Product):
        raise ValidationError("Invalid product instance.")

    if not name or not name.strip():
        raise ValidationError({"name": "Product name is required."})

    final_slug = slugify(slug or "")

    if not final_slug:
        raise ValidationError({"slug": "Invalid slug."})

    if Product.objects.exclude(pk=product.pk).filter(slug=final_slug).exists():
        raise ValidationError({"slug": "Slug already in use."})

    product.name = name.strip()
    product.slug = final_slug
    product.save(update_fields=["name", "slug"])

    return product


# ==================================================
# PRODUCT DEACTIVATION
# ==================================================

@transaction.atomic
def deactivate_product(*, product: Product) -> Product:

    if not isinstance(product, Product):
        raise ValidationError("Invalid product instance.")

    if not product.is_active:
        return product

    product.is_active = False
    product.is_featured = False
    product.save(update_fields=["is_active", "is_featured"])

    return product


# ==================================================
# PRODUCT CATEGORY ASSIGNMENT
# ==================================================

@transaction.atomic
def update_product_categories(
    *,
    product: Product,
    category_ids: Iterable[int],
) -> Product:

    if not isinstance(product, Product):
        raise ValidationError("Invalid product instance.")

    ids = {int(cid) for cid in category_ids}

    categories = list(
        Category.objects.filter(id__in=ids, is_active=True)
    )

    if len(categories) != len(ids):
        raise ValidationError({
            "categories": "Invalid or inactive categories."
        })

    product.categories.set(categories)
    return product


# ==================================================
# PRODUCT PATCH UPDATE (PRICE / FLAGS)
# ==================================================

@transaction.atomic
def update_product(
    *,
    product: Product,
    price: Optional[str | Decimal] = None,
    old_price: Optional[str | Decimal] = None,
    is_featured: Optional[bool] = None,
) -> Product:

    if not isinstance(product, Product):
        raise ValidationError("Invalid product instance.")

    updated_fields: list[str] = []

    if price not in (None, ""):
        try:
            price_val = Decimal(price)
        except (InvalidOperation, TypeError):
            raise ValidationError({"price": "Invalid price."})

        if price_val < 0:
            raise ValidationError({"price": "Price cannot be negative."})

        product.price = price_val
        updated_fields.append("price")

    if old_price in (None, ""):
        if product.old_price is not None:
            product.old_price = None
            updated_fields.append("old_price")
    else:
        try:
            old_price_val = Decimal(old_price)
        except (InvalidOperation, TypeError):
            raise ValidationError({"old_price": "Invalid old price."})

        if old_price_val <= product.price:
            raise ValidationError({
                "old_price": "Old price must be greater than price."
            })

        product.old_price = old_price_val
        updated_fields.append("old_price")

    if is_featured is not None:
        product.is_featured = bool(is_featured)
        updated_fields.append("is_featured")

    if updated_fields:
        product.save(update_fields=updated_fields)

    return product


# ==================================================
# PRODUCT DESCRIPTION
# ==================================================

@transaction.atomic
def update_product_description(
    *,
    product: Product,
    description: str,
) -> Product:

    if not isinstance(product, Product):
        raise ValidationError("Invalid product instance.")

    if description is None:
        raise ValidationError({"description": "Cannot be null."})

    product.description = sanitize_html(description)
    product.save(update_fields=["description"])

    return product
