from rest_framework import generics
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from store.models import Category, Product
from store.serializers import (
    CategoryTreeSerializer,
    CategoryCardSerializer,
    ProductListSerializer,
)


# ==================================================
# CATEGORY TREE (NAVBAR / MENUS / FILTERS)
# ==================================================
class CategoryListAPIView(generics.ListAPIView):
    """
    Hierarchical category tree (NO image).

    Frontend RULES:
    - Only ACTIVE categories
    - Campaign visibility respected
    - Archived categories behave as non-existent
    """

    serializer_class = CategoryTreeSerializer

    queryset = (
        Category.objects
        .filter(
            parent__isnull=True,
            is_active=True,
        )
        .prefetch_related(
            "children__children"
        )
    )

    def get_queryset(self):
        """
        Extra safety:
        filters children in serializer depth
        """
        return (
            Category.objects
            .filter(
                parent__isnull=True,
                is_active=True,
            )
        )


# ==================================================
# CATEGORY DETAIL (CATEGORY PAGE)
# ==================================================
class CategoryDetailAPIView(generics.RetrieveAPIView):
    """
    Category detail endpoint.

    HARD RULES:
    - Archived category → 404
    - Campaign date rules enforced
    - Children must be active
    """

    lookup_field = "slug"

    def get_queryset(self):
        # Only categories visible to users
        return Category.objects.filter(is_active=True)

    def retrieve(self, request, *args, **kwargs):
        category = self.get_object()

        # 🔒 Campaign visibility check
        if not category.is_live:
            raise NotFound("Category not found.")

        # -----------------------------
        # Child categories (cards)
        # -----------------------------
        child_categories = (
            Category.objects
            .filter(
                parent=category,
                is_active=True,
                image__isnull=False,
            )
        )

        # -----------------------------
        # Products directly in category
        # -----------------------------
        products = (
            Product.objects
            .filter(
                categories=category,
                is_active=True,
            )
            .distinct()
        )

        return Response({
            "category": {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
            },
            "children": CategoryCardSerializer(
                child_categories,
                many=True,
                context={"request": request},
            ).data,
            "products": ProductListSerializer(
                products,
                many=True,
                context={"request": request},
            ).data,
        })


# ==================================================
# CATEGORY CARDS (LANDING PAGE ONLY)
# ==================================================
class CategoryCardListAPIView(generics.ListAPIView):
    """
    Flat category list WITH image.

    Landing page RULES:
    - Only ACTIVE categories
    - Only LIVE campaigns
    - Archived categories are invisible
    """

    serializer_class = CategoryCardSerializer

    queryset = (
        Category.objects
        .filter(
            parent__isnull=True,
            is_active=True,
            image__isnull=False,
        )
    )

    def get_queryset(self):
        """
        Enforce campaign visibility window
        """
        return [
            c for c in self.queryset
            if c.is_live
        ]
