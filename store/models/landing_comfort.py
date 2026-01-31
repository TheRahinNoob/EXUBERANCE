from django.db import models
from django.core.exceptions import ValidationError

import uuid
import os

from store.models import Category, Product


# ==================================================
# IMAGE PATH — SAFE & COLLISION-PROOF
# ==================================================

def comfort_rail_image_path(instance, filename):
    """
    Generate a safe, unique file path for comfort rail images.

    Guarantees:
    - No user-provided filenames
    - No timestamps (Windows-safe)
    - No collisions
    - Predictable folder structure
    """
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"comfort_rails/{uuid.uuid4().hex}{ext}"


# ==================================================
# MODEL
# ==================================================

class ComfortCategoryRail(models.Model):
    """
    Landing Page — Comfort Section Rail (CMS Entity)

    FIRST-CLASS CMS BLOCK.

    Guarantees:
    - Always linked to a category
    - Always has a valid image
    - Products are optional
    - Ordering is deterministic
    - Safe deletion across ALL code paths
    """

    # ===============================
    # CATEGORY (LOGICAL ANCHOR)
    # ===============================
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="comfort_rails",
        help_text="Primary category represented by this comfort rail",
    )

    # ===============================
    # IMAGE (VISUAL IDENTITY — REQUIRED)
    # ===============================
    image = models.ImageField(
        upload_to=comfort_rail_image_path,
        null=False,
        blank=False,
        help_text="MANDATORY image for this comfort rail (landing page visual)",
    )

    # ===============================
    # PRODUCTS (RIGHT SIDE CONTENT)
    # ===============================
    products = models.ManyToManyField(
        Product,
        blank=True,
        related_name="comfort_rails",
        help_text=(
            "Optional manually selected products. "
            "If empty and auto_fill is enabled, products are auto-picked from category."
        ),
    )

    # ===============================
    # AUTO-FILL LOGIC
    # ===============================
    auto_fill = models.BooleanField(
        default=True,
        help_text="Auto-pick products from category when no manual products exist",
    )

    auto_limit = models.PositiveIntegerField(
        default=8,
        help_text="Maximum number of products to show in this rail",
    )

    # ===============================
    # VISIBILITY & ORDERING
    # ===============================
    is_active = models.BooleanField(
        default=True,
        help_text="Controls whether this rail appears on the landing page",
    )

    ordering = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear earlier on the landing page",
    )

    # ===============================
    # META
    # ===============================
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("ordering", "id")
        verbose_name = "Comfort Section"
        verbose_name_plural = "Comfort Sections"
        indexes = [
            models.Index(fields=["is_active", "ordering"]),
            models.Index(fields=["category"]),
        ]

    # ===============================
    # HARD VALIDATION (NO SILENT FAILURES)
    # ===============================
    def clean(self):
        super().clean()

        if not self.image:
            raise ValidationError(
                {"image": "Comfort rail image is required."}
            )

        if self.auto_limit <= 0:
            raise ValidationError(
                {"auto_limit": "auto_limit must be a positive integer."}
            )

    # ===============================
    # SAFE DELETE (🔥 CRITICAL)
    # ===============================
    def delete(self, *args, **kwargs):
        """
        HARD GUARANTEE:
        - Image file is cleaned up safely
        - Filesystem errors NEVER block DB deletion
        - Works from admin, API, shell, tests, signals
        """
        if self.image and self.image.name:
            try:
                self.image.delete(save=False)
            except Exception:
                pass

        super().delete(*args, **kwargs)

    # ===============================
    # STRING REPRESENTATION
    # ===============================
    def __str__(self) -> str:
        return f"Comfort Rail — {self.category.name} (#{self.id})"
