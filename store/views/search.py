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
        # QUERY PARAM PARSING (STRICT, DEFENSIVE)
        # ==================================================

        # ---- Full-text search ----
        query = request.GET.get("q")
        query = query.strip() if isinstance(query, str) and query.strip() else None

        # ---- Legacy support (DO NOT REMOVE) ----
        category_slug = request.GET.get("category")
        category_slug = (
            category_slug.strip()
            if isinstance(category_slug, str) and category_slug.strip()
            else None
        )

        # ---- Categories (NORMAL + CAMPAIGN) ----
        categories_param = request.GET.get("categories")
        categories = None

        if isinstance(categories_param, str):
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

        if min_price is not None and max_price is not None and min_price > max_price:
            raise ValidationError({
                "price": "min_price cannot be greater than max_price."
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
