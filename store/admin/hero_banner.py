# store/admin/hero_banner.py

from django.contrib import admin
from django.utils.html import format_html

from store.models.hero_banner import HeroBanner


@admin.register(HeroBanner)
class HeroBannerAdmin(admin.ModelAdmin):
    """
    Django Admin configuration for Hero Banners.

    PURPOSE:
    - Upload responsive hero images (desktop / tablet / mobile)
    - Control visibility and schedule
    - Control ordering
    - Provide clear visual previews
    """

    # ==================================================
    # LIST VIEW
    # ==================================================

    list_display = (
        "id",
        "desktop_preview",
        "is_active",
        "ordering",
        "live_status",
    )

    list_filter = ("is_active",)
    ordering = ("ordering", "id")

    list_editable = (
        "is_active",
        "ordering",
    )

    # ==================================================
    # READONLY PREVIEWS
    # ==================================================

    readonly_fields = (
        "desktop_preview",
        "tablet_preview",
        "mobile_preview",
    )

    # ==================================================
    # FORM LAYOUT
    # ==================================================

    fieldsets = (
        (
            "Images",
            {
                "fields": (
                    "image_desktop",
                    "desktop_preview",
                    "image_tablet",
                    "tablet_preview",
                    "image_mobile",
                    "mobile_preview",
                ),
                "description": (
                    "Upload responsive images. "
                    "Desktop is required. Tablet and mobile are optional but recommended."
                ),
            },
        ),
        (
            "Visibility & Scheduling",
            {
                "fields": (
                    "is_active",
                    "starts_at",
                    "ends_at",
                    "ordering",
                ),
            },
        ),
    )

    # ==================================================
    # INTERNAL IMAGE PREVIEW HELPERS
    # ==================================================

    def _render_image(self, image):
        """
        Safe HTML renderer for image previews.
        """
        if not image:
            return "—"

        return format_html(
            '<img src="{}" style="height:60px;border-radius:6px;object-fit:cover;" />',
            image.url,
        )

    # ==================================================
    # PREVIEW FIELDS
    # ==================================================

    @admin.display(description="Desktop")
    def desktop_preview(self, obj):
        return self._render_image(obj.image_desktop)

    @admin.display(description="Tablet")
    def tablet_preview(self, obj):
        return self._render_image(obj.image_tablet)

    @admin.display(description="Mobile")
    def mobile_preview(self, obj):
        return self._render_image(obj.image_mobile)

    # ==================================================
    # LIVE STATUS INDICATOR
    # ==================================================

    @admin.display(boolean=True, description="Live")
    def live_status(self, obj):
        """
        Reflects real-time visibility state
        based on is_active + scheduling.
        """
        return obj.is_live
