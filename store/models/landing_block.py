from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from store.models.landing import HotCategoryBlock
from store.models.landing_comfort import ComfortCategoryRail
from store.models.landing_comfort_editorial import ComfortEditorialBlock


class LandingBlock(models.Model):
    """
    CMS-driven landing page layout block.

    GUARANTEES:
    - ONE row = ONE visible block on landing page
    - CMS controls ORDER + VISIBILITY
    - Each block type binds to EXACTLY ONE payload
    - Invalid combinations are HARD-BLOCKED
    - Validation is ENFORCED at save-time
    """

    # ==================================================
    # BLOCK TYPES (LOCKED ENUM)
    # ==================================================
    class BlockType(models.TextChoices):
        HERO = "hero", _("Hero Banner")
        MENU = "menu", _("Landing Menu")
        FEATURED = "featured", _("Featured Categories")
        HOT = "hot", _("Hot Categories Block")
        COMFORT_BLOCK = "comfort_block", _("Comfort Editorial Block")
        COMFORT_RAIL = "comfort_rail", _("Comfort Rail")

    # ==================================================
    # CORE CMS FIELDS
    # ==================================================
    block_type = models.CharField(
        max_length=32,
        choices=BlockType.choices,
        db_index=True,
        help_text=_("Which block to render on the landing page"),
    )

    ordering = models.PositiveIntegerField(
        default=0,
        help_text=_("Lower numbers appear first"),
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_("Temporarily hide this block without deleting"),
    )

    # ==================================================
    # BLOCK-SPECIFIC PAYLOADS (MUTUALLY EXCLUSIVE)
    # ==================================================

    # 🔥 HOT CATEGORY BLOCK
    hot_category_block = models.ForeignKey(
        HotCategoryBlock,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="landing_blocks",
        help_text=_("Required ONLY when block type is 'hot'"),
    )

    # 🧠 COMFORT EDITORIAL BLOCK
    comfort_editorial_block = models.ForeignKey(
        ComfortEditorialBlock,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="landing_blocks",
        help_text=_("Required ONLY when block type is 'comfort_block'"),
    )

    # 🧵 COMFORT PRODUCT RAIL
    comfort_rail = models.ForeignKey(
        ComfortCategoryRail,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="landing_blocks",
        help_text=_("Required ONLY when block type is 'comfort_rail'"),
    )

    # ==================================================
    # SYSTEM FIELDS
    # ==================================================
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("ordering", "id")
        verbose_name = _("Landing Block")
        verbose_name_plural = _("Landing Blocks")
        indexes = [
            models.Index(fields=["is_active", "ordering"]),
            models.Index(fields=["block_type"]),
        ]

    # ==================================================
    # HARD CMS VALIDATION (ABSOLUTE)
    # ==================================================
    def clean(self):
        """
        Enforces EXACTLY ONE payload FK per block_type.
        This mirrors Django Admin behavior.
        """
        super().clean()

        required_fk_by_type = {
            self.BlockType.HOT: "hot_category_block",
            self.BlockType.COMFORT_BLOCK: "comfort_editorial_block",
            self.BlockType.COMFORT_RAIL: "comfort_rail",
        }

        fk_fields = {
            "hot_category_block",
            "comfort_editorial_block",
            "comfort_rail",
        }

        required_fk = required_fk_by_type.get(self.block_type)

        for field_name in fk_fields:
            value = getattr(self, field_name)

            if field_name == required_fk:
                if not value:
                    raise ValidationError({
                        field_name: _(
                            f"This field is REQUIRED for block type '{self.block_type}'."
                        )
                    })
            else:
                if value:
                    raise ValidationError({
                        field_name: _(
                            f"This field MUST be empty for block type '{self.block_type}'."
                        )
                    })

    # ==================================================
    # SAVE OVERRIDE — ENFORCE VALIDATION
    # ==================================================
    def save(self, *args, **kwargs):
        """
        🔒 CRITICAL:
        Enforces clean() even when created via ORM / API.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    # ==================================================
    # STRING REPRESENTATION
    # ==================================================
    def __str__(self) -> str:
        return f"{self.get_block_type_display()} — order {self.ordering}"
