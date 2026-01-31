from rest_framework import serializers

from store.models import Product


# ==================================================
# PRODUCT MINI (LANDING / RAILS / LIGHTWEIGHT)
# ==================================================
class ProductMiniSerializer(serializers.ModelSerializer):
    """
    Lightweight product serializer for landing blocks
    (Comfort Rail, future curated rails, etc.)

    Design goals:
    - Minimal payload
    - Includes pricing context (price + old_price)
    - Safe for high-traffic landing endpoints
    - Reusable across multiple landing sections
    """

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "price",
            "old_price",
            "main_image",
        )
