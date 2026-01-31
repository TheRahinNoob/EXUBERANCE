from django.db import models
from django.core.exceptions import ValidationError
import uuid
import os


# ==================================================
# IMAGE PATH — SAFE & COLLISION-PROOF
# ==================================================
def comfort_editorial_image_path(instance, filename):
    """
    Generate a safe, unique file path for comfort editorial images.

    Guarantees:
    - No user-provided filenames
    - No timestamps (Windows-safe)
    - No collisions
    - Predictable folder structure
    """
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    return f"comfort_editorial/{uuid.uuid4().hex}{ext}"


# ==================================================
# MODEL — COMFORT EDITORIAL BLOCK
# ==================================================
class ComfortEditorialBlock(models.Model):
    """
    Landing Page — Comfort Editorial Block (CMS Entity)

    PURPOSE:
    - Editorial-style content block for landing page
    - Fully CMS-controlled
    - Text + image + CTA
    - Appears ONLY via LandingBlock ordering

    DESIGN PRINCIPLES:
    - Lightweight
    - Admin-safe
    - No hard coupling with products or categories
    """

    # ===============================
    # CORE CONTENT
    # ===============================
    title = models.CharField(
        max_length=255,
        help_text="Main headline text for the editorial block",
    )

    subtitle = models.TextField(
        blank=True,
        null=True,
        help_text="Optional supporting text (short paragraph)",
    )

    image = models.ImageField(
        upload_to=comfort_editorial_image_path,
        blank=True,
        null=True,
        help_text="Optional editorial image (recommended high quality)",
    )

    # ===============================
    # CALL TO ACTION (OPTIONAL)
    # ===============================
    cta_text = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="CTA button text (e.g. 'Explore Collection')",
    )

    cta_url = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="CTA destination URL (absolute or relative)",
    )

    # ===============================
    # VISIBILITY & ORDERING
    # ===============================
    is_active = models.BooleanField(
        default=True,
        help_text="Toggle visibility without deleting the block",
    )

    ordering = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear earlier in CMS listings",
    )

    # ===============================
    # SYSTEM META
    # ===============================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ===============================
    # DJANGO META
    # ===============================
    class Meta:
        ordering = ("ordering", "id")
        verbose_name = "Comfort Editorial Block"
        verbose_name_plural = "Comfort Editorial Blocks"
        indexes = [
            models.Index(fields=["is_active", "ordering"]),
        ]

    # ===============================
    # HARD VALIDATION (NO SILENT FAILURES)
    # ===============================
    def clean(self):
        super().clean()

        if not self.title or not self.title.strip():
            raise ValidationError(
                {"title": "Title is required and cannot be empty."}
            )

        # CTA integrity rule
        if bool(self.cta_text) ^ bool(self.cta_url):
            raise ValidationError(
                "CTA text and CTA URL must be provided together."
            )

    # ===============================
    # SAFE DELETE (IMAGE CLEANUP)
    # ===============================
    def delete(self, *args, **kwargs):
        """
        HARD GUARANTEE:
        - Image file cleanup never blocks DB deletion
        - Safe across admin, shell, tests, signals
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
        return f"Comfort Editorial — {self.title} (#{self.id})"
