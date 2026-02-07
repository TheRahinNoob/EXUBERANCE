from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django.utils.timezone import now
from django.db.models import Prefetch

from store.models.landing import HotCategory, HotCategoryBlock, HotCategoryBlockItem


class LandingHotCategoriesAPIView(APIView):
    """
    Landing Page — Hot Categories (BLOCKED & NESTED API)

    PURPOSE:
    - Serve hot categories data grouped by CMS-defined blocks
    - Frontend receives blocks with nested hot categories
    - Fully supports multiple blocks, ordering, and active flags
    - Optional filtering by block IDs (?block_id=1,2,3)
    """

    permission_classes = [AllowAny]

    def get(self, request):
        # --------------------------------------------------
        # Parse optional block filter
        # --------------------------------------------------
        block_ids_param = request.query_params.get("block_id")
        block_filter = None
        if block_ids_param:
            try:
                block_filter = [int(pk) for pk in block_ids_param.split(",")]
            except ValueError:
                return Response(
                    {"detail": "Invalid block_id parameter"},
                    status=400,
                )

        # --------------------------------------------------
        # Prefetch hot category items safely
        # Only active items and blocks
        # --------------------------------------------------
        hot_category_items_prefetch = Prefetch(
            "items",
            queryset=HotCategoryBlockItem.objects.filter(
                is_active=True,
                hot_category__is_active=True,
                block__is_active=True,
            ).select_related("hot_category__category").order_by("ordering", "id"),
            to_attr="prefetched_items",
        )

        # --------------------------------------------------
        # Fetch blocks with prefetch
        # --------------------------------------------------
        blocks_qs = HotCategoryBlock.objects.filter(is_active=True)
        if block_filter:
            blocks_qs = blocks_qs.filter(id__in=block_filter)

        blocks_qs = blocks_qs.prefetch_related(hot_category_items_prefetch).order_by("ordering", "id")

        # --------------------------------------------------
        # Serialize blocks with nested items
        # --------------------------------------------------
        response_blocks = []
        for block in blocks_qs:
            items = []
            for item in getattr(block, "prefetched_items", []):
                hot_category = item.hot_category
                items.append({
                    "id": hot_category.id,
                    "ordering": item.ordering,
                    "name": hot_category.category.name,
                    "slug": hot_category.category.slug,
                    "image": (
                        request.build_absolute_uri(hot_category.image.url)
                        if hot_category.image else None
                    ),
                })

            response_blocks.append({
                "id": block.id,
                "title": block.title or f"Hot Category Block #{block.id}",
                "ordering": block.ordering,
                "is_active": block.is_active,
                "items": items,
            })

        # --------------------------------------------------
        # Return structured response
        # --------------------------------------------------
        return Response({
            "meta": {
                "page": "landing",
                "section": "hot",
                "generated_at": now().isoformat(),
                "block_count": len(response_blocks),
            },
            "blocks": response_blocks,
        })
