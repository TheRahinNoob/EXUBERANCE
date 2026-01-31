print("🔥🔥🔥 CATEGORY ADMIN LOADED 🔥🔥🔥")

from django.contrib import admin
from django import forms
from django.utils.html import format_html

from store.models import Category


# ==================================================
# ADMIN FORM (ONLY RELAXES REQUIRED FLAGS)
# ==================================================

class CategoryAdminForm(forms.ModelForm):
    """
    Admin form override.

    PURPOSE:
    - Prevent Django Admin from forcing campaign dates
    - Do NOT duplicate business validation
    """

    class Meta:
        model = Category
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔥 THIS IS THE ACTUAL FIX
        self.fields["starts_at"].required = False
        self.fields["ends_at"].required = False


# ==================================================
# ADMIN CONFIG
# ==================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryAdminForm  # ✅ REQUIRED

    list_display = (
        "name",
        "parent",
        "is_campaign",
        "campaign_status",
        "is_active",
        "ordering",
        "image_preview",
    )

    list_filter = (
        "is_campaign",
        "is_active",
        "parent",
    )

    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("ordering", "name")

    readonly_fields = ("image_preview",)

    fieldsets = (
        (None, {
            "fields": (
                "name",
                "slug",
                "parent",
                "ordering",
            )
        }),
        ("Campaign Controls", {
            "fields": (
                "is_campaign",
                "starts_at",
                "ends_at",
                "priority",
                "show_countdown",
            ),
        }),
        ("Visibility", {
            "fields": ("is_active",),
        }),
        ("Visual", {
            "fields": ("image", "image_preview"),
        }),
    )

    # =============================
    # UI HELPERS
    # =============================

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:50px;border-radius:6px;" />',
                obj.image.url,
            )
        return "—"

    image_preview.short_description = "Preview"

    def campaign_status(self, obj):
        if not obj.is_campaign:
            return "—"

        if obj.is_live:
            return format_html(
                '<span style="background:#22c55e;color:white;'
                'padding:3px 10px;border-radius:999px;font-size:11px;">LIVE</span>'
            )

        return format_html(
            '<span style="background:#6b7280;color:white;'
            'padding:3px 10px;border-radius:999px;font-size:11px;">INACTIVE</span>'
        )

    campaign_status.short_description = "Campaign"
