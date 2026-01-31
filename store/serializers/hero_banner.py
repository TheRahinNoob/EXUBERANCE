from rest_framework import serializers
from store.models import HeroBanner


class HeroBannerSerializer(serializers.ModelSerializer):
    """
    Landing page hero banners.
    Image only. No text.
    """

    class Meta:
        model = HeroBanner
        fields = (
            "id",
            "image_desktop",
            "image_tablet",
            "image_mobile",
            "ordering",
        )
