# store/admin/comfort.py

from django.contrib import admin
from store.models.landing_comfort import ComfortCategoryRail


@admin.register(ComfortCategoryRail)
class ComfortCategoryRailAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "is_active",
        "auto_fill",
        "auto_limit",
        "ordering",
    )

    list_filter = ("is_active", "auto_fill")
    ordering = ("ordering",)

    filter_horizontal = ("products",)

    fieldsets = (
        ("Category", {
            "fields": ("category",)
        }),
        ("Products", {
            "fields": ("products",),
            "description": "Optional. If empty, auto-fill will be used."
        }),
        ("Behavior", {
            "fields": ("auto_fill", "auto_limit")
        }),
        ("Visibility", {
            "fields": ("is_active", "ordering")
        }),
    )
