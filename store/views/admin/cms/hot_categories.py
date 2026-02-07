from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db.models import Max

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status

from rest_framework_simplejwt.authentication import JWTAuthentication

from store.models.category import Category
from store.models.landing import HotCategory


# ==================================================
# JWT BASE ADMIN VIEW (NO CSRF, NO COOKIES)
# ==================================================
class AdminJWTAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]


# ==================================================
# ADMIN HOT CATEGORY — LIST & CREATE (ATOMIC)
# ==================================================
class AdminHotCategoryListCreateView(AdminJWTAPIView):
    """
    Admin CMS API for Hot Categories (ATOMIC).

    Guarantees:
    - Only active categories can be used
    - One HotCategory per Category (no duplicates)
    - Explicit, deterministic ordering
    - Image upload required on creation
    - Backend is final authority
    """

    # --------------------------------------------------
    # GET — LIST HOT CATEGORIES
    # --------------------------------------------------
    def get(self, request):
        items = (
            HotCategory.objects
            .select_related("category")
            .order_by("ordering", "id")
        )

        response = [
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
                },
            }
            for item in items
        ]

        return Response(response)

    # --------------------------------------------------
    # POST — CREATE HOT CATEGORY
    # --------------------------------------------------
    @transaction.atomic
    def post(self, request):
        category_id = request.data.get("category_id")
        image = request.FILES.get("image")
        is_active = request.data.get("is_active", True)

        if not category_id:
            return Response(
                {"detail": "category_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not image:
            return Response(
                {"detail": "image file is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        category = get_object_or_404(Category, pk=category_id)

        if not category.is_active:
            return Response(
                {"detail": "Inactive categories cannot be used"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if HotCategory.objects.filter(category=category).exists():
            return Response(
                {"detail": "This category already has a Hot Category"},
                status=status.HTTP_409_CONFLICT
            )

        # Ensure deterministic ordering
        max_ordering = HotCategory.objects.aggregate(max_val=Max("ordering"))["max_val"] or 0

        try:
            hot_category = HotCategory.objects.create(
                category=category,
                image=image,
                ordering=max_ordering + 1,
                is_active=bool(is_active)
            )
        except ValidationError as e:
            return Response(
                {"detail": e.message_dict or str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "id": hot_category.id,
                "ordering": hot_category.ordering,
                "is_active": hot_category.is_active,
                "image": request.build_absolute_uri(hot_category.image.url),
                "category": {
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug
                },
            },
            status=status.HTTP_201_CREATED
        )


# ==================================================
# ADMIN HOT CATEGORY — DETAIL / UPDATE / DELETE
# ==================================================
class AdminHotCategoryDetailView(AdminJWTAPIView):
    """
    Admin CMS API for updating / deleting a single Hot Category.
    """

    # --------------------------------------------------
    # PATCH — UPDATE HOT CATEGORY
    # --------------------------------------------------
    @transaction.atomic
    def patch(self, request, pk):
        hot_category = get_object_or_404(
            HotCategory.objects.select_related("category"),
            pk=pk
        )

        updated = False
        data = request.data

        # Toggle active
        if "is_active" in data:
            hot_category.is_active = bool(data["is_active"])
            updated = True

        # Update ordering
        if "ordering" in data:
            try:
                ordering = int(data["ordering"])
                if ordering < 0:
                    raise ValueError
                hot_category.ordering = ordering
                updated = True
            except (TypeError, ValueError):
                return Response(
                    {"detail": "ordering must be a non-negative integer"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Replace image if provided
        if "image" in request.FILES:
            hot_category.image = request.FILES["image"]
            updated = True

        if not updated:
            return Response(
                {"detail": "No valid fields provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure category remains active
        if not hot_category.category.is_active:
            return Response(
                {"detail": "Inactive categories cannot be used"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            hot_category.full_clean()
            hot_category.save()
        except ValidationError as e:
            return Response(
                {"detail": e.message_dict or str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "id": hot_category.id,
            "ordering": hot_category.ordering,
            "is_active": hot_category.is_active,
            "image": request.build_absolute_uri(hot_category.image.url),
            "category": {
                "id": hot_category.category.id,
                "name": hot_category.category.name,
                "slug": hot_category.category.slug,
            },
        })

    # --------------------------------------------------
    # DELETE — REMOVE HOT CATEGORY
    # --------------------------------------------------
    @transaction.atomic
    def delete(self, request, pk):
        hot_category = get_object_or_404(HotCategory, pk=pk)
        hot_category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
