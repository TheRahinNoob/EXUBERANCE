from __future__ import annotations

from django.db import models
from django.db.models import Q
from django.utils.timezone import now
from django.core.exceptions import ValidationError


class Category(models.Model):
    """
    Hierarchical product category (SOFT-DELETABLE).

    GUARANTEES:
    - Infinite depth
    - Strict cycle prevention
    - Soft delete ONLY (never physically deleted)
    - Archived categories are invisible everywhere
    - Campaign-aware (dates OPTIONAL)
    """

    # =============================
    # CORE IDENTITY
    # =============================

    name = models.CharField(
        max_length=100,
        help_text="Display name of the category",
    )

    slug = models.SlugField(
        unique=True,
        help_text="Unique URL slug",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent category for hierarchy",
    )

    # =============================
    # MEDIA
    # =============================

    image = models.ImageField(
        upload_to="categories/",
        null=True,
        blank=True,
        help_text="Used for landing cards & campaign visuals",
    )

    # =============================
    # CAMPAIGN / PROMOTION
    # =============================

    is_campaign = models.BooleanField(
        default=False,
        help_text="Marks this category as a campaign / offer",
    )

    starts_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Campaign start time (optional)",
    )

    ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Campaign end time (optional)",
    )

    show_countdown = models.BooleanField(
        default=False,
        help_text="Frontend may show countdown timer",
    )

    priority = models.PositiveIntegerField(
        default=0,
        help_text="Higher priority appears first",
    )

    # =============================
    # STATE & ORDERING
    # =============================

    is_active = models.BooleanField(
        default=True,
        help_text="SOFT DELETE FLAG — inactive categories do not exist publicly",
    )

    ordering = models.PositiveIntegerField(
        default=0,
        help_text="Sibling ordering (lower comes first)",
    )

    # =============================
    # META
    # =============================

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ("ordering", "-priority", "name")
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_campaign"]),
            models.Index(fields=["starts_at"]),
            models.Index(fields=["ends_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~Q(parent=models.F("id")),
                name="category_cannot_parent_itself",
            ),
            models.UniqueConstraint(
                fields=["parent", "name"],
                condition=Q(is_active=True),
                name="unique_active_category_name_per_parent",
            ),
        ]

    # =============================
    # VALIDATION (FINAL AUTHORITY)
    # =============================

    def clean(self):
        """
        Model-level validation.

        RULES:
        - Campaign dates are OPTIONAL
        - Validation runs even for inactive categories
        """

        # -----------------------------
        # Prevent hierarchy cycles
        # -----------------------------
        if self.parent:
            ancestor = self.parent
            while ancestor:
                if ancestor == self:
                    raise ValidationError(
                        {"parent": "Category hierarchy cannot contain cycles."}
                    )
                ancestor = ancestor.parent

        # -----------------------------
        # Campaign validation
        # -----------------------------
        if self.is_campaign:
            if self.starts_at and self.ends_at:
                if self.starts_at >= self.ends_at:
                    raise ValidationError(
                        "Campaign start time must be before end time."
                    )
        else:
            # Normalize non-campaign categories
            self.starts_at = None
            self.ends_at = None
            self.show_countdown = False

    def save(self, *args, **kwargs):
        """
        Enforce validation everywhere:
        - Django admin
        - Services
        - API
        """
        self.full_clean()
        super().save(*args, **kwargs)

    # =============================
    # VISIBILITY LOGIC (PUBLIC TRUTH)
    # =============================

    @property
    def is_live(self) -> bool:
        """
        Whether category should be visible to customers.
        """
        if not self.is_active:
            return False

        if self.is_campaign:
            current = now()
            if self.starts_at and current < self.starts_at:
                return False
            if self.ends_at and current > self.ends_at:
                return False

        return True

    # =============================
    # SOFT DELETE (CRITICAL)
    # =============================

    def archive(self, *, cascade: bool = True) -> None:
        """
        Soft delete the category.

        - Marks is_active=False
        - Optionally cascades to all descendants
        - NEVER deletes database rows
        """

        if not self.is_active:
            return  # idempotent

        self.is_active = False
        self.save(update_fields=["is_active"])

        if cascade:
            for child in self.children.all():
                child.archive(cascade=True)

    def restore(self, *, cascade: bool = False) -> None:
        """
        Restore a previously archived category.

        ⚠️ Does NOT auto-restore parents.
        """

        if self.is_active:
            return

        self.is_active = True
        self.save(update_fields=["is_active"])

        if cascade:
            for child in self.children.all():
                child.restore(cascade=True)

    # =============================
    # TREE UTILITIES
    # =============================

    def get_descendants(self, include_self: bool = True):
        """
        Iterative, cycle-safe descendant retrieval.
        Includes BOTH active & inactive nodes.
        """
        result = set()
        stack = [self]

        while stack:
            node = stack.pop()
            for child in node.children.all():
                if child not in result:
                    result.add(child)
                    stack.append(child)

        if include_self:
            result.add(self)

        return result

    # =============================
    # STRING
    # =============================

    def __str__(self) -> str:
        return self.name
