from django.contrib import admin
from django.utils.html import format_html
from django.core.exceptions import ValidationError

from store.models.landing_comfort_editorial import ComfortEditorialBlock


@admin.register(ComfortEditorialBlock)
class ComfortEditorialBlockAdmin(admin.ModelAdmin):
    """
    Admin for Landing — Comfort Editorial Block

    GOALS:
    - Fully CMS-controlled
    - Zero silent failures
    - Visual confidence for editors
    """

    # ==================================================
    # LIST VIEW
    # ==================================================
    list_display = (
        "title",
        "is_active",
        "ordering",
        "created_at",
    )

    list_filter = ("is_active",)
    ordering = ("ordering", "id")
    list_editable = ("is_active", "ordering")

    # ==================================================
    # READ-ONLY FIELDS
    # ==================================================
    readonly_fields = (
        "image_preview",
        "created_at",
        "updated_at",
    )

    # ==================================================
    # FORM LAYOUT
    # ==================================================
    fieldsets = (
        ("Content", {
            "fields": (
                "title",
                "subtitle",
                "image",
                "image_preview",   # ✅ allowed here because it's READONLY
            ),
        }),
        ("Call To Action (Optional)", {
            "fields": (
                "cta_text",
                "cta_url",
            ),
        }),
        ("Visibility & Order", {
            "fields": (
                "is_active",
                "ordering",
            ),
        }),
        ("System", {
            "fields": (
                "created_at",
                "updated_at",
            ),
        }),
    )

    # ==================================================
    # IMAGE PREVIEW (SAFE)
    # ==================================================
    @admin.display(description="Image Preview")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:160px;border-radius:10px;" />',
                obj.image.url,
            )
        return "—"

    # ==================================================
    # HARD VALIDATION
    # ==================================================
    def save_model(self, request, obj, form, change):
        """
        Absolute guarantees:
        - Title is mandatory
        - Image must exist
        """
        if not obj.title:
            raise ValidationError("Title is required.")

        if not obj.image:
            raise ValidationError("Image is required.")

        super().save_model(request, obj, form, change)
