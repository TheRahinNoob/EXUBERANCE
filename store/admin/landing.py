from django.contrib import admin
from django.utils.html import format_html
from django.core.exceptions import ValidationError

from store.models.landing import (
    LandingMenuItem,
    FeaturedCategory,
)


# ==================================================
# BASE ADMIN (SHARED BEHAVIOR)
# ==================================================
class LandingBaseAdmin(admin.ModelAdmin):
    """
    Shared admin behavior for landing-only models.

    WHY:
    - Consistent UX
    - Faster edits
    - Safer content control
    """

    list_filter = ("is_active",)
    list_editable = ("is_active", "ordering")
    ordering = ("ordering", "id")

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    def has_delete_permission(self, request, obj=None):
        """
        Prevent accidental deletions in production mindset.
        Soft-delete via is_active instead.
        """
        return True  # change to False later if needed


# ==================================================
# LANDING PAGE BODY MENU ADMIN
# ==================================================
@admin.register(LandingMenuItem)
class LandingMenuItemAdmin(LandingBaseAdmin):
    """
    Admin control for landing page BODY MENU
    (small menu under hero banner)

    GOALS:
    - Pick categories
    - Control order
    - Enable / disable safely
    - No duplicates
    """

    list_display = (
        "category_name",
        "category_slug",
        "is_active",
        "ordering",
        "created_at",
    )

    search_fields = (
        "category__name",
        "category__slug",
    )

    autocomplete_fields = ("category",)

    fieldsets = (
        ("Category", {
            "fields": ("category",),
            "description": (
                "Select which category appears in the landing page menu. "
                "Each category can appear only once."
            ),
        }),
        ("Visibility & Order", {
            "fields": ("is_active", "ordering"),
        }),
        ("SEO Overrides (Optional)", {
            "fields": ("seo_title", "seo_description"),
            "description": (
                "Optional. Leave empty to auto-generate SEO values "
                "from the category."
            ),
        }),
        ("System", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    # -----------------------------
    # DISPLAY HELPERS
    # -----------------------------
    @admin.display(description="Category")
    def category_name(self, obj):
        return obj.category.name

    @admin.display(description="Slug")
    def category_slug(self, obj):
        return obj.category.slug

    # -----------------------------
    # VALIDATION
    # -----------------------------
    def save_model(self, request, obj, form, change):
        """
        Extra safety: prevent inactive categories
        from being added accidentally.
        """
        if not obj.category.is_active:
            raise ValidationError(
                "This category is inactive and cannot be used in landing menu."
            )
        super().save_model(request, obj, form, change)


# ==================================================
# FEATURED CATEGORY ADMIN (IMAGE GRID)
# ==================================================
@admin.register(FeaturedCategory)
class FeaturedCategoryAdmin(LandingBaseAdmin):
    """
    Admin control for FEATURED CATEGORIES
    (image-based grid under landing menu)
    """

    list_display = (
        "image_preview",
        "category",
        "is_active",
        "ordering",
    )

    autocomplete_fields = ("category",)

    fieldsets = (
        ("Category", {
            "fields": ("category",),
            "description": (
                "Select a category to feature on the landing page."
            ),
        }),
        ("Image", {
            "fields": ("image",),
            "description": (
                "Upload a high-quality image. "
                "Recommended: square or portrait."
            ),
        }),
        ("Visibility & Order", {
            "fields": ("is_active", "ordering"),
        }),
        ("System", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    # -----------------------------
    # IMAGE PREVIEW
    # -----------------------------
    @admin.display(description="Preview")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:8px;" />',
                obj.image.url,
            )
        return "—"

    # -----------------------------
    # VALIDATION
    # -----------------------------
    def save_model(self, request, obj, form, change):
        """
        Prevent featuring inactive categories.
        """
        if not obj.category.is_active:
            raise ValidationError(
                "This category is inactive and cannot be featured."
            )
        super().save_model(request, obj, form, change)
