from rest_framework import generics
from django.db.models import Q

from store.models import Product, Category
from store.serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
)


# ==================================================
# 🔧 SHARED CATEGORY TREE RESOLVER (DRY)
# ==================================================
def get_category_tree_ids(category: Category) -> list[int]:
    """
    Returns category IDs including:
    - the category itself
    - all descendant categories
    """

    ids: list[int] = []

    def collect(node):
        ids.append(node.id)
        for child in node.children.all():
            collect(child)

    collect(category)
    return ids


# ==================================================
# PRODUCT LIST (HOME / CATEGORY / FEATURED)
# ==================================================
class ProductListAPIView(generics.ListAPIView):
    """
    Product listing endpoint.

    Supports:
    - ?category=<slug>   (tree-aware)
    - ?featured=1
    - ?exclude=<product_id>   🔥 (for related products)
    - ?limit=<number>
    """

    serializer_class = ProductListSerializer

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)

        category_slug = self.request.query_params.get("category")
        featured = self.request.query_params.get("featured")
        exclude_id = self.request.query_params.get("exclude")
        limit = self.request.query_params.get("limit")

        # -----------------------------
        # CATEGORY FILTER (TREE-AWARE)
        # -----------------------------
        if category_slug:
            try:
                category = Category.objects.get(slug=category_slug)
            except Category.DoesNotExist:
                return Product.objects.none()

            category_ids = get_category_tree_ids(category)
            queryset = queryset.filter(categories__in=category_ids)

        # -----------------------------
        # FEATURED FILTER
        # -----------------------------
        if featured == "1":
            queryset = queryset.filter(is_featured=True)

        # -----------------------------
        # EXCLUDE PRODUCT (RELATED USE)
        # -----------------------------
        if exclude_id and exclude_id.isdigit():
            queryset = queryset.exclude(id=int(exclude_id))

        queryset = queryset.distinct().order_by("-created_at")

        # -----------------------------
        # LIMIT
        # -----------------------------
        if limit and limit.isdigit():
            queryset = queryset[: int(limit)]

        return queryset


# ==================================================
# PRODUCT DETAIL (PDP)
# ==================================================
class ProductDetailAPIView(generics.RetrieveAPIView):
    """
    Single product detail page.
    """

    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"


# ==================================================
# 🔥 RELATED PRODUCTS (YOU MAY ALSO LIKE)
# ==================================================
class RelatedProductAPIView(generics.ListAPIView):
    """
    Returns products related to a given product.

    Rules:
    - Same or closest category first
    - Excludes current product
    - Active products only
    - Limit configurable
    """

    serializer_class = ProductListSerializer

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        limit = self.request.query_params.get("limit", "8")

        try:
            limit = int(limit)
        except ValueError:
            limit = 8

        try:
            product = Product.objects.prefetch_related(
                "categories__children"
            ).get(slug=slug, is_active=True)
        except Product.DoesNotExist:
            return Product.objects.none()

        categories = product.categories.all()

        if not categories.exists():
            return Product.objects.none()

        # Collect all relevant category IDs (closest match)
        category_ids: set[int] = set()

        for category in categories:
            category_ids.update(get_category_tree_ids(category))

        queryset = (
            Product.objects.filter(
                is_active=True,
                categories__in=category_ids,
            )
            .exclude(id=product.id)
            .distinct()
            .order_by("-created_at")[:limit]
        )

        return queryset
