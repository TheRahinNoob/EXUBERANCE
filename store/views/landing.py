from django.utils.timezone import now
from django.db.models import Prefetch

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from store.models import HeroBanner
from store.models.landing import FeaturedCategory, HotCategory
from store.models.landing_comfort import ComfortCategoryRail
from store.models.landing_comfort_editorial import ComfortEditorialBlock

from store.serializers import (
    HeroBannerSerializer,
    ProductMiniSerializer,
)

from store.services.landing_menu_service import get_landing_menu_items


# ==================================================
# LANDING — HERO BANNERS (ATOMIC)
# ==================================================
class LandingHeroBannerAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        banners = (
            HeroBanner.objects
            .filter(is_active=True)
            .only(
                "id",
                "image_desktop",
                "image_tablet",
                "image_mobile",
                "ordering",
            )
            .order_by("ordering", "-created_at")
        )

        serializer = HeroBannerSerializer(
            banners,
            many=True,
            context={"request": request},
        )

        return Response({
            "meta": {
                "page": "landing",
                "section": "hero",
                "generated_at": now().isoformat(),
            },
            "items": serializer.data,
        })


# ==================================================
# LANDING — BODY MENU (ATOMIC)
# ==================================================
class LandingMenuAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        items = get_landing_menu_items()

        return Response({
            "meta": {
                "page": "landing",
                "section": "menu",
                "generated_at": now().isoformat(),
            },
            "items": [
                {
                    "name": item.category.name,
                    "slug": item.category.slug,
                    "seo_title": item.effective_seo_title,
                    "seo_description": item.effective_seo_description,
                }
                for item in items
            ],
        })


# ==================================================
# LANDING — FEATURED CATEGORIES (ATOMIC)
# ==================================================
class LandingFeaturedCategoriesAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        items = (
            FeaturedCategory.objects
            .filter(is_active=True)
            .select_related("category")
            .only(
                "ordering",
                "image",
                "category__name",
                "category__slug",
            )
            .order_by("ordering", "id")
        )

        return Response({
            "meta": {
                "page": "landing",
                "section": "featured",
                "generated_at": now().isoformat(),
            },
            "items": [
                {
                    "name": item.category.name,
                    "slug": item.category.slug,
                    "image": request.build_absolute_uri(item.image.url),
                }
                for item in items
            ],
        })


# ==================================================
# LANDING — HOT CATEGORIES (ATOMIC)
# ==================================================
class LandingHotCategoriesAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        items = (
            HotCategory.objects
            .filter(is_active=True)
            .select_related("category")
            .only(
                "ordering",
                "image",
                "category__name",
                "category__slug",
            )
            .order_by("ordering", "id")
        )

        return Response({
            "meta": {
                "page": "landing",
                "section": "hot",
                "generated_at": now().isoformat(),
            },
            "items": [
                {
                    "name": item.category.name,
                    "slug": item.category.slug,
                    "image": request.build_absolute_uri(item.image.url),
                }
                for item in items
            ],
        })


# ==================================================
# 🧠 LANDING — COMFORT EDITORIAL BLOCK (ATOMIC)
# ==================================================
class LandingComfortEditorialAPIView(APIView):
    """
    Atomic Comfort Editorial Block endpoint.

    - ONE editorial block per CMS entry
    - Text + Image + CTA only
    - NO product logic here
    """

    permission_classes = [AllowAny]

    def get(self, request):
        blocks = (
            ComfortEditorialBlock.objects
            .filter(is_active=True)
            .order_by("ordering", "id")
        )

        items = []

        for block in blocks:
            items.append({
                "id": block.id,
                "title": block.title,
                "subtitle": block.subtitle,
                "image": (
                    request.build_absolute_uri(block.image.url)
                    if block.image
                    else None
                ),
                "cta_text": block.cta_text,
                "cta_url": block.cta_url,
            })

        return Response({
            "meta": {
                "page": "landing",
                "section": "comfort_editorial",
                "generated_at": now().isoformat(),
            },
            "items": items,
        })


# ==================================================
# 🔥 LANDING — COMFORT RAILS (CMS-CRITICAL)
# ==================================================
class LandingComfortAPIView(APIView):
    """
    Atomic comfort rail endpoint.

    - Uses ComfortCategoryRail.image
    - Products are resolved here
    - Frontend receives FINAL render-ready data
    """

    permission_classes = [AllowAny]

    def get(self, request):
        rails = (
            ComfortCategoryRail.objects
            .filter(is_active=True)
            .select_related("category")
            .prefetch_related(
                Prefetch(
                    "products",
                    queryset=(
                        ComfortCategoryRail.products.rel.model.objects
                        .filter(is_active=True)
                        .only(
                            "id",
                            "name",
                            "slug",
                            "price",
                            "old_price",
                            "main_image",
                        )
                    ),
                )
            )
            .order_by("ordering", "id")
        )

        items = []

        for rail in rails:
            if rail.products.exists():
                products = rail.products.all()[: rail.auto_limit]

            elif rail.auto_fill:
                products = (
                    rail.category.products
                    .filter(is_active=True)
                    .only(
                        "id",
                        "name",
                        "slug",
                        "price",
                        "old_price",
                        "main_image",
                    )
                    .order_by("?")[: rail.auto_limit]
                )

            else:
                products = []

            items.append({
                "id": rail.id,
                "category": {
                    "name": rail.category.name,
                    "slug": rail.category.slug,
                    "image": (
                        request.build_absolute_uri(rail.image.url)
                        if rail.image
                        else None
                    ),
                },
                "products": ProductMiniSerializer(
                    products,
                    many=True,
                    context={"request": request},
                ).data,
            })

        return Response({
            "meta": {
                "page": "landing",
                "section": "comfort_rail",
                "generated_at": now().isoformat(),
            },
            "items": items,
        })
