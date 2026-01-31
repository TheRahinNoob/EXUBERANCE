from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from store.models import LandingBlock


@admin.register(LandingBlock)
class LandingBlockAdmin(admin.ModelAdmin):
    """
    CMS controller for landing page layout.

    RESPONSIBILITY:
    - Control WHICH blocks appear
    - Control ORDER
    - Enforce block-specific configuration
    - NEVER crash admin
    """

    # ===============================
    # LIST VIEW
    # ===============================
    list_display = (
        "ordering",
        "block_type",
        "is_active",
        "created_at",
    )

    list_display_links = ("block_type",)
    list_editable = ("ordering", "is_active")
    list_filter = ("block_type", "is_active")
    ordering = ("ordering", "id")

    readonly_fields = ("created_at",)

    # ===============================
    # FORM LAYOUT
    # ===============================
    fieldsets = (
        (
            _("Block Configuration"),
            {
                "fields": (
                    "block_type",
                    "ordering",
                    "is_active",
                ),
            },
        ),
        (
            _("Hot Categories Block"),
            {
                "fields": ("hot_category_block",),
                "description": _(
                    "Required ONLY when block type is 'hot'."
                ),
            },
        ),
        (
            _("Comfort Editorial Block"),
            {
                "fields": ("comfort_editorial_block",),
                "description": _(
                    "Required ONLY when block type is 'comfort_block'."
                ),
            },
        ),
        (
            _("Comfort Rail"),
            {
                "fields": ("comfort_rail",),
                "description": _(
                    "Required ONLY when block type is 'comfort_rail'."
                ),
            },
        ),
        (
            _("System"),
            {
                "fields": ("created_at",),
            },
        ),
    )

    # ===============================
    # HARD CMS SAFETY (ADMIN-SAFE)
    # ===============================
    def save_model(self, request, obj, form, change):
        """
        Enforce block-specific relationships safely.

        IMPORTANT:
        - Use ValidationError (NOT ValueError)
        - Let Django Admin attach errors to fields
        """

        errors = {}

        if obj.block_type == LandingBlock.BlockType.HOT:
            if not obj.hot_category_block:
                errors["hot_category_block"] = _(
                    "Hot Category Block is required for this block type."
                )
            obj.comfort_editorial_block = None
            obj.comfort_rail = None

        elif obj.block_type == LandingBlock.BlockType.COMFORT_BLOCK:
            if not obj.comfort_editorial_block:
                errors["comfort_editorial_block"] = _(
                    "Comfort Editorial Block is required for this block type."
                )
            obj.hot_category_block = None
            obj.comfort_rail = None

        elif obj.block_type == LandingBlock.BlockType.COMFORT_RAIL:
            if not obj.comfort_rail:
                errors["comfort_rail"] = _(
                    "Comfort Rail is required for this block type."
                )
            obj.hot_category_block = None
            obj.comfort_editorial_block = None

        else:
            # HERO / MENU / FEATURED
            obj.hot_category_block = None
            obj.comfort_editorial_block = None
            obj.comfort_rail = None

        if errors:
            raise ValidationError(errors)

        super().save_model(request, obj, form, change)
