from rest_framework import serializers

from store.models import (
    Product,
    ProductImage,
    ProductVariant,
    ProductAttributeValue,
)


# ==================================================
# PRODUCT IMAGE (GALLERY)
# ==================================================
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = (
            "id",
            "image",
        )


# ==================================================
# PRODUCT VARIANT (SIZE / COLOR / STOCK)
# ==================================================
class ProductVariantSerializer(serializers.ModelSerializer):
    """
    Stock intentionally exposed for UX.
    """

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "size",
            "color",
            "stock",
        )


# ==================================================
# PRODUCT ATTRIBUTE VALUE (SPECIFICATIONS)
# ==================================================
class ProductAttributeValueSerializer(serializers.ModelSerializer):
    """
    Structured product specifications:
    - Fabric: Cotton
    - GSM: 180
    - Fit: Regular
    """

    name = serializers.CharField(
        source="attribute.name",
        read_only=True,
    )

    class Meta:
        model = ProductAttributeValue
        fields = (
            "name",
            "value",
        )


# ==================================================
# PRODUCT LIST (GRID / SHOP / CAMPAIGNS)
# ==================================================
class ProductListSerializer(serializers.ModelSerializer):
    categories = serializers.StringRelatedField(many=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "price",
            "old_price",
            "main_image",
            "is_featured",
            "categories",
        )


# ==================================================
# PRODUCT DETAIL
# ==================================================
class ProductDetailSerializer(serializers.ModelSerializer):
    categories = serializers.StringRelatedField(many=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    attributes = ProductAttributeValueSerializer(
        source="attribute_values",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "short_description",
            "description",
            "price",
            "old_price",
            "main_image",
            "categories",
            "images",
            "variants",
            "attributes",
        )


# ==================================================
# 🔥 PRODUCT SEARCH (FAST & MINIMAL — FIXED)
# ==================================================
class ProductSearchSerializer(serializers.ModelSerializer):
    categories = serializers.StringRelatedField(many=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",

            "price",
            "old_price",        # ✅ 🔥 THIS WAS MISSING

            "main_image",
            "categories",
        )
