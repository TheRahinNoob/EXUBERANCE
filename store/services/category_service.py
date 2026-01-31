from __future__ import annotations

from typing import Optional, Iterable
from django.db import transaction
from django.utils.text import slugify
from django.core.exceptions import ValidationError

from store.models import Category


# ==================================================
# CATEGORY SERVICE — SINGLE SOURCE OF TRUTH
# ==================================================
# HARD RULES:
# - NO hard deletes (EVER)
# - Delete == archive (soft delete)
# - Products do NOT block category deletion
# - Descendants are archived automatically
# - Idempotent & safe
# ==================================================


# ==================================================
# INTERNAL — CASCADE ARCHIVE
# ==================================================

def _archive_category(category: Category) -> None:
    """
    Archive a category and all descendants.

    - Safe to call multiple times
    - Clears campaign state
    - Preserves hierarchy
    """

    if not category.is_active:
        return  # already archived → idempotent

    category.is_active = False
    category.is_campaign = False
    category.starts_at = None
    category.ends_at = None
    category.show_countdown = False

    category.save(
        update_fields=[
            "is_active",
            "is_campaign",
            "starts_at",
            "ends_at",
            "show_countdown",
        ]
    )

    for child in category.children.all():
        _archive_category(child)


# ==================================================
# CREATE CATEGORY
# ==================================================

@transaction.atomic
def create_category(
    *,
    name: str,
    slug: Optional[str] = None,
    parent: Optional[Category] = None,
    ordering: int = 0,
    priority: int = 0,
    is_active: bool = True,

    # 🔥 CAMPAIGN (OPTIONAL)
    is_campaign: bool = False,
    starts_at=None,
    ends_at=None,
    show_countdown: bool = False,
) -> Category:
    if not name or not name.strip():
        raise ValidationError({"name": "Category name is required."})

    name = name.strip()
    final_slug = slugify(slug.strip() if slug else name)

    if not final_slug:
        raise ValidationError({"slug": "Invalid slug."})

    if Category.objects.filter(slug=final_slug).exists():
        raise ValidationError({"slug": "Slug already exists."})

    if parent and not isinstance(parent, Category):
        raise ValidationError({"parent": "Invalid parent category."})

    if is_campaign and starts_at and ends_at and starts_at >= ends_at:
        raise ValidationError(
            "Campaign start time must be before end time."
        )

    category = Category(
        name=name,
        slug=final_slug,
        parent=parent,
        ordering=max(0, int(ordering)),
        priority=max(0, int(priority)),
        is_active=bool(is_active),

        is_campaign=bool(is_campaign),
        starts_at=starts_at if is_campaign else None,
        ends_at=ends_at if is_campaign else None,
        show_countdown=bool(show_countdown) if is_campaign else False,
    )

    category.full_clean()
    category.save()

    return category


# ==================================================
# UPDATE CATEGORY (PATCH SAFE)
# ==================================================

@transaction.atomic
def update_category(
    *,
    category: Category,
    name: Optional[str] = None,
    slug: Optional[str] = None,
    parent: Optional[Category | None] = None,
    ordering: Optional[int] = None,
    priority: Optional[int] = None,
    is_active: Optional[bool] = None,

    # 🔥 CAMPAIGN
    is_campaign: Optional[bool] = None,
    starts_at=None,
    ends_at=None,
    show_countdown: Optional[bool] = None,
) -> Category:
    if not isinstance(category, Category):
        raise ValidationError("Invalid category instance.")

    updated_fields: list[str] = []

    if name is not None:
        if not name.strip():
            raise ValidationError({"name": "Category name cannot be empty."})
        category.name = name.strip()
        updated_fields.append("name")

    if slug is not None:
        final_slug = slugify(slug.strip())
        if not final_slug:
            raise ValidationError({"slug": "Invalid slug."})

        if (
            Category.objects
            .exclude(pk=category.pk)
            .filter(slug=final_slug)
            .exists()
        ):
            raise ValidationError({"slug": "Slug already in use."})

        category.slug = final_slug
        updated_fields.append("slug")

    if parent is not None:
        if parent == category:
            raise ValidationError({"parent": "Category cannot be its own parent."})

        if parent and category in parent.get_descendants(include_self=True):
            raise ValidationError(
                {"parent": "Circular category hierarchy is not allowed."}
            )

        category.parent = parent
        updated_fields.append("parent")

    if ordering is not None:
        category.ordering = max(0, int(ordering))
        updated_fields.append("ordering")

    if priority is not None:
        category.priority = max(0, int(priority))
        updated_fields.append("priority")

    if is_active is not None:
        category.is_active = bool(is_active)
        updated_fields.append("is_active")

    if is_campaign is not None:
        category.is_campaign = bool(is_campaign)
        updated_fields.append("is_campaign")

        if is_campaign:
            if starts_at and ends_at and starts_at >= ends_at:
                raise ValidationError(
                    "Campaign start time must be before end time."
                )

            if starts_at is not None:
                category.starts_at = starts_at
                updated_fields.append("starts_at")

            if ends_at is not None:
                category.ends_at = ends_at
                updated_fields.append("ends_at")

            if show_countdown is not None:
                category.show_countdown = bool(show_countdown)
                updated_fields.append("show_countdown")
        else:
            category.starts_at = None
            category.ends_at = None
            category.show_countdown = False
            updated_fields += ["starts_at", "ends_at", "show_countdown"]

    if updated_fields:
        category.save(update_fields=updated_fields)

    return category


# ==================================================
# DELETE CATEGORY (SOFT DELETE ONLY)
# ==================================================

@transaction.atomic
def delete_category(*, category: Category) -> None:
    """
    Soft-delete category.

    - Products DO NOT block deletion
    - Children are archived automatically
    - Safe & idempotent
    """

    if not isinstance(category, Category):
        raise ValidationError("Invalid category instance.")

    _archive_category(category)


# ==================================================
# REORDER CATEGORIES
# ==================================================

@transaction.atomic
def reorder_categories(*, ordered_ids: Iterable[int]) -> None:
    ids = list(ordered_ids)
    if not ids:
        return

    categories = list(
        Category.objects.filter(id__in=ids, is_active=True)
    )

    if len(categories) != len(ids):
        raise ValidationError(
            "Invalid or inactive category IDs."
        )

    parent_ids = {c.parent_id for c in categories}
    if len(parent_ids) > 1:
        raise ValidationError(
            "Categories must share the same parent."
        )

    order_map = {cid: idx for idx, cid in enumerate(ids)}
    for cat in categories:
        cat.ordering = order_map[cat.id]

    Category.objects.bulk_update(categories, ["ordering"])
