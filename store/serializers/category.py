from rest_framework import serializers
from store.models import Category, Product
from .product import ProductListSerializer


# ==================================================
# BASE MIXIN — CAMPAIGN SAFE
# ==================================================

class CampaignSafeMixin(serializers.ModelSerializer):
    """
    Explicitly marks campaign fields as OPTIONAL.
    This prevents DRF from ever enforcing start/end dates.
    """

    starts_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        read_only=True,
    )

    ends_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        read_only=True,
    )

    show_countdown = serializers.BooleanField(
        required=False,
        read_only=True,
    )


# ==================================================
# CATEGORY — TREE (NAVBAR / SIDEBAR)
# ==================================================

class CategoryTreeSerializer(CampaignSafeMixin):
    children = serializers.SerializerMethodField()
    is_live = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "is_campaign",
            "starts_at",
            "ends_at",
            "show_countdown",
            "priority",
            "is_live",
            "children",
        )

    def get_children(self, obj):
        qs = (
            obj.children
            .filter(is_active=True)
            .order_by("ordering", "-priority", "name")
        )
        return CategoryTreeSerializer(
            qs,
            many=True,
            context=self.context,
        ).data

    def get_is_live(self, obj):
        return obj.is_live


# ==================================================
# CATEGORY — CARD (LANDING / DISCOVERY)
# ==================================================

class CategoryCardSerializer(CampaignSafeMixin):
    is_live = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "image",
            "is_campaign",
            "starts_at",
            "ends_at",
            "show_countdown",
            "priority",
            "is_live",
        )

    def get_is_live(self, obj):
        return obj.is_live


# ==================================================
# CATEGORY — DETAIL (CATEGORY / CAMPAIGN PAGE)
# ==================================================

class CategoryDetailSerializer(CampaignSafeMixin):
    children = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()
    is_live = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "is_campaign",
            "starts_at",
            "ends_at",
            "show_countdown",
            "priority",
            "is_live",
            "children",
            "products",
        )

    def get_children(self, obj):
        qs = (
            obj.children
            .filter(is_active=True, image__isnull=False)
            .order_by("ordering", "-priority", "name")
        )
        return CategoryCardSerializer(
            qs,
            many=True,
            context=self.context,
        ).data

    def get_products(self, obj):
        qs = (
            Product.objects
            .filter(categories=obj, is_active=True)
            .distinct()
            .order_by("-created_at")
        )
        return ProductListSerializer(
            qs,
            many=True,
            context=self.context,
        ).data

    def get_is_live(self, obj):
        return obj.is_live
