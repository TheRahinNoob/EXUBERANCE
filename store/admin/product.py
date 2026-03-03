from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin

from store.models import (
    Product,
    ProductImage,
    ProductVariant,
    ProductAttributeValue,
)


# ==================================================
# INLINE: PRODUCT IMAGES (GALLERY)
# ==================================================
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    ordering = ("id",)


# ==================================================
# INLINE: PRODUCT VARIANTS (SIZE / COLOR / STOCK)
# ==================================================
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    ordering = ("id",)
    fields = ("size", "color", "color_hex", "stock")  # ✅ added color_hex


# ==================================================
# INLINE: PRODUCT ATTRIBUTE VALUES (SPEC TABLE)
# ==================================================
class ProductAttributeValueInline(admin.TabularInline):
    """
    Product specification table:
    - Fabric
    - GSM
    - Fit
    - Composition
    """

    model = ProductAttributeValue
    extra = 1
    autocomplete_fields = ("attribute",)
    fields = ("attribute", "value")
    ordering = ("attribute__ordering",)


# ==================================================
# PRODUCT ADMIN (CMS-LEVEL)
# ==================================================
@admin.register(Product)
class ProductAdmin(SummernoteModelAdmin):
    """
    Central CMS for Product management.

    Rules:
    - Variants control availability
    - AttributeValues control specifications
    - Categories control discovery
    """

    # --------------------------------------------------
    # 🔥 RICH TEXT EDITOR
    # --------------------------------------------------
    # Apply Summernote ONLY to full description
    summernote_fields = ("description",)

    # --------------------------------------------------
    # LIST PAGE
    # --------------------------------------------------
    list_display = (
        "name",
        "price",
        "is_active",
        "is_featured",
        "created_at",
    )

    list_filter = (
        "is_active",
        "is_featured",
        "categories",
    )

    search_fields = (
        "name",
        "slug",
    )

    ordering = ("-created_at",)

    # --------------------------------------------------
    # FORM BEHAVIOR
    # --------------------------------------------------
    prepopulated_fields = {
        "slug": ("name",),
    }

    filter_horizontal = ("categories",)

    # --------------------------------------------------
    # INLINE EDITORS
    # --------------------------------------------------
    inlines = (
        ProductImageInline,
        ProductVariantInline,
        ProductAttributeValueInline,
    )