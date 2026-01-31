from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django.utils.timezone import now
from django.db.models import OuterRef, Subquery

from store.models.landing import HotCategory, HotCategoryBlockItem


class LandingHotCategoriesAPIView(APIView):
    """
    Landing Page — Hot Categories (ATOMIC API)

    PURPOSE:
    - Serve hot categories data
    - Support CMS-driven placement via block IDs
    - Reusable across homepage & future layouts

    FEATURES:
    - Optional filtering by IDs (?id=1,2,3)
    - Annotates hot_category_block_id
    - Safe, predictable response shape
    - NEVER breaks frontend
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """
        Optional query params:
        - id=1
        - id=1,2,3
        """

        # --------------------------------------------------
        # BASE QUERYSET (ATOMIC & SAFE)
        # --------------------------------------------------
        qs = (
            HotCategory.objects
            .filter(is_active=True)
            .select_related("category")
            .only(
                "id",
                "ordering",
                "image",
                "category__name",
                "category__slug",
            )
            .order_by("ordering", "id")
        )

        # --------------------------------------------------
        # OPTIONAL CMS FILTERING BY HOT CATEGORY IDs
        # --------------------------------------------------
        ids_param = request.query_params.get("id")

        if ids_param:
            try:
                ids = [int(pk) for pk in ids_param.split(",")]
                qs = qs.filter(id__in=ids)
            except ValueError:
                qs = qs.none()

        # --------------------------------------------------
        # 🔥 ANNOTATE BLOCK ID (COLLECTIVE SUPPORT)
        # --------------------------------------------------
        block_id_subquery = (
            HotCategoryBlockItem.objects
            .filter(
                hot_category=OuterRef("pk"),
                is_active=True,
                block__is_active=True,
            )
            .order_by("ordering")
            .values("block_id")[:1]
        )

        qs = qs.annotate(
            hot_category_block_id=Subquery(block_id_subquery)
        )

        # --------------------------------------------------
        # RESPONSE SERIALIZATION (SAFE)
        # --------------------------------------------------
        items = [
    {
        "id": item.id,
        "hot_category_block_id": item.hot_category_block_id,
        "name": item.category.name,
        "slug": item.category.slug,
        "image": (
            request.build_absolute_uri(item.image.url)
            if item.image else None
        ),
    }
    for item in qs
    if item.hot_category_block_id is not None
]



        return Response(
            {
                "meta": {
                    "page": "landing",
                    "section": "hot",
                    "generated_at": now().isoformat(),
                    "count": len(items),
                },
                "items": items,
            }
        )
