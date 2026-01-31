from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from store.services.search_service import search_products
from store.serializers import ProductSearchSerializer
from store.pagination import StandardResultsSetPagination


class ProductSearchAPIView(APIView):
    """
    Public product listing & search API.
    AUTHORITATIVE source for /shop.

    NON-NEGOTIABLE ARCHITECTURE:
    --------------------------------
    - Categories are the ONLY taxonomy (campaigns included)
    - No `offer`, `campaign`, or hidden params exist
    - search_service is the SINGLE source of truth
    - View layer does ZERO business logic
    - URL params are the ONLY input surface
    """

    pagination_class = StandardResultsSetPagination

    def get(self, request):
        # ==================================================
        # QUERY PARAM PARSING (STRICT, DEFENSIVE, BORING)
        # ==================================================

        # ---- Full-text search ----
        query = request.GET.get("q")
        query = query.strip() if query else None

        # ---- Legacy support (DO NOT REMOVE) ----
        # Allows old URLs like ?category=t-shirt
        category_slug = request.GET.get("category")
        category_slug = category_slug.strip() if category_slug else None

        # ---- Categories (NORMAL + CAMPAIGN) ----
        categories_param = request.GET.get("categories")
        categories: list[str] | None = None

        if categories_param:
            categories = [
                slug.strip()
                for slug in categories_param.split(",")
                if slug.strip()
            ] or None

        # ---- Ordering (explicit allowlist) ----
        ordering = request.GET.get("ordering")
        if ordering not in (None, "price_asc", "price_desc", "newest"):
            ordering = None

        # ---- Price filters ----
        min_price = request.GET.get("min_price")
        max_price = request.GET.get("max_price")

        try:
            min_price = int(min_price) if min_price not in (None, "") else None
            max_price = int(max_price) if max_price not in (None, "") else None
        except (TypeError, ValueError):
            raise ValidationError({
                "price": "min_price and max_price must be valid integers."
            })

        # ==================================================
        # SEARCH SERVICE (SINGLE SOURCE OF TRUTH)
        # ==================================================
        queryset = search_products(
            query=query,
            category_slug=category_slug,
            categories=categories,
            min_price=min_price,
            max_price=max_price,
            ordering=ordering,
        )

        # ==================================================
        # PAGINATION (CONSISTENT RESPONSE SHAPE)
        # ==================================================
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = ProductSearchSerializer(
            page if page is not None else [],
            many=True,
        )

        return paginator.get_paginated_response(serializer.data)
