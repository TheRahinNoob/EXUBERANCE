from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db.models import Max

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status

from store.models.category import Category
from store.models.landing import FeaturedCategory


# ==================================================
# INTERNAL UTILITIES
# ==================================================

def parse_bool(value):
    """
    Safely parse boolean values coming from:
    - FormData (strings)
    - JSON
    - Python bools

    CRITICAL:
    bool("false") == True ❌
    This helper FIXES that forever.
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes", "on")

    if isinstance(value, int):
        return value == 1

    return False


# ==================================================
# ADMIN FEATURED CATEGORY — LIST & CREATE
# ==================================================
class AdminFeaturedCategoryListCreateView(APIView):
    """
    Admin CMS API for Featured Categories.

    GUARANTEES:
    - Only active categories can be featured
    - No duplicate categories
    - Ordering is deterministic
    - Backend is the FINAL authority
    """

    permission_classes = [IsAdminUser]

    # --------------------------------------------------
    # GET — LIST FEATURED CATEGORIES
    # --------------------------------------------------
    def get(self, request):
        items = (
            FeaturedCategory.objects
            .select_related("category")
            .order_by("ordering", "id")
        )

        return Response(
            [
                {
                    "id": item.id,
                    "ordering": item.ordering,
                    "is_active": item.is_active,
                    "image": (
                        request.build_absolute_uri(item.image.url)
                        if item.image else None
                    ),
                    "category": {
                        "id": item.category.id,
                        "name": item.category.name,
                        "slug": item.category.slug,
                        "is_active": item.category.is_active,
                    },
                }
                for item in items
            ]
        )

    # --------------------------------------------------
    # POST — CREATE FEATURED CATEGORY
    # --------------------------------------------------
    @transaction.atomic
    def post(self, request):
        category_id = request.data.get("category_id")
        image = request.FILES.get("image")
        is_active = parse_bool(request.data.get("is_active", True))

        if not category_id:
            return Response(
                {"detail": "category_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not image:
            return Response(
                {"detail": "image file is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category = get_object_or_404(Category, pk=category_id)

        if not category.is_active:
            return Response(
                {"detail": "Inactive categories cannot be featured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if FeaturedCategory.objects.filter(category=category).exists():
            return Response(
                {"detail": "This category is already featured"},
                status=status.HTTP_409_CONFLICT,
            )

        max_ordering = (
            FeaturedCategory.objects.aggregate(
                max_val=Max("ordering")
            )["max_val"]
            or 0
        )

        try:
            featured = FeaturedCategory.objects.create(
                category=category,
                image=image,
                ordering=max_ordering + 1,
                is_active=is_active,
            )
        except ValidationError as e:
            return Response(
                {"detail": e.message_dict or str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "id": featured.id,
                "ordering": featured.ordering,
                "is_active": featured.is_active,
                "image": request.build_absolute_uri(
                    featured.image.url
                ),
                "category": {
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug,
                    "is_active": category.is_active,
                },
            },
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# ADMIN FEATURED CATEGORY — DETAIL
# ==================================================
class AdminFeaturedCategoryDetailView(APIView):
    """
    Admin CMS API for updating / deleting
    a single Featured Category.
    """

    permission_classes = [IsAdminUser]

    # --------------------------------------------------
    # PATCH — UPDATE FEATURED CATEGORY
    # --------------------------------------------------
    @transaction.atomic
    def patch(self, request, pk):
        featured = get_object_or_404(
            FeaturedCategory.objects.select_related("category"),
            pk=pk,
        )

        data = request.data
        updated = False

        # -----------------------------
        # Toggle active (FIXED)
        # -----------------------------
        if "is_active" in data:
            featured.is_active = parse_bool(data["is_active"])
            updated = True

        # -----------------------------
        # Ordering update
        # -----------------------------
        if "ordering" in data:
            try:
                ordering = int(data["ordering"])
                if ordering < 0:
                    raise ValueError
                featured.ordering = ordering
                updated = True
            except (TypeError, ValueError):
                return Response(
                    {"detail": "ordering must be a non-negative integer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # -----------------------------
        # Image replacement
        # -----------------------------
        if "image" in request.FILES:
            featured.image = request.FILES["image"]
            updated = True

        if not updated:
            return Response(
                {"detail": "No valid fields provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------------
        # FINAL SAFETY CHECK
        # -----------------------------
        if not featured.category.is_active:
            return Response(
                {"detail": "Inactive categories cannot be featured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            featured.full_clean()
            featured.save()
        except ValidationError as e:
            return Response(
                {"detail": e.message_dict or str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "id": featured.id,
                "ordering": featured.ordering,
                "is_active": featured.is_active,
                "image": request.build_absolute_uri(
                    featured.image.url
                ),
                "category": {
                    "id": featured.category.id,
                    "name": featured.category.name,
                    "slug": featured.category.slug,
                    "is_active": featured.category.is_active,
                },
            }
        )

    # --------------------------------------------------
    # DELETE — REMOVE FEATURED CATEGORY
    # --------------------------------------------------
    @transaction.atomic
    def delete(self, request, pk):
        featured = get_object_or_404(FeaturedCategory, pk=pk)
        featured.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
