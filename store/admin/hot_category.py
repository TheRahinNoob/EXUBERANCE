from django.contrib import admin
from django.utils.html import format_html

from store.models.landing import HotCategory


@admin.register(HotCategory)
class HotCategoryAdmin(admin.ModelAdmin):
    """
    Landing Page — Hot Categories
    """

    list_display = (
        "preview",
        "category",
        "is_active",
        "ordering",
    )

    list_editable = (
        "is_active",
        "ordering",
    )

    ordering = ("ordering", "id")

    autocomplete_fields = ("category",)

    # 🔥 REQUIRED FOR AUTOCOMPLETE USAGE
    search_fields = (
        "category__name",
        "category__slug",
    )

    fieldsets = (
        ("Category", {
            "fields": ("category",),
        }),
        ("Image", {
            "fields": ("image",),
        }),
        ("Visibility & Order", {
            "fields": ("is_active", "ordering"),
        }),
    )

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:80px;border-radius:8px;" />',
                obj.image.url,
            )
        return "—"

    preview.short_description = "Preview"
