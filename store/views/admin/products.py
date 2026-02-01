from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.db.models.functions import Coalesce

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from rest_framework.exceptions import ValidationError

# 🔐 JWT AUTH
from rest_framework_simplejwt.authentication import JWTAuthentication

from store.models import Product
from store.services.product_service import (
    create_product,
    update_product,
    deactivate_product,
    update_product_basic_info,
    update_product_categories,
)

# ==================================================
# BASE ADMIN VIEW (JWT ENFORCED)
# ==================================================

class AdminJWTAPIView(APIView):
    """
    Base class for ALL admin product views.

    Enforces:
    - JWT authentication
    - Admin-only access
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]


# ==================================================
# CONSTANTS
# ==================================================

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ==================================================
# ADMIN PRODUCT LIST + CREATE
# ==================================================

class AdminProductListView(AdminJWTAPIView):

    def get(self, request):
        qs = (
            Product.objects
            .annotate(total_stock=Coalesce(Sum("variants__stock"), 0))
            .order_by("-created_at")
        )

        status_filter = request.query_params.get("status")
        if status_filter == "active":
            qs = qs.filter(is_active=True)
        elif status_filter == "inactive":
            qs = qs.filter(is_active=False)

        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(
                request.query_params.get("page_size", DEFAULT_PAGE_SIZE)
            )
        except (TypeError, ValueError):
            raise ValidationError({
                "message": "Invalid pagination parameters."
            })

        page = max(page, 1)
        page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size

        products = qs[start:end]

        return Response(
            {
                "meta": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "has_next": end < total,
                    "has_prev": start > 0,
                },
                "items": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "price": str(p.price),
                        "is_active": p.is_active,
                        "total_stock": int(p.total_stock),
                        "created_at": p.created_at.isoformat(),
                    }
                    for p in products
                ],
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        data = request.data or {}

        try:
            product = create_product(
                name=data.get("name"),
                slug=data.get("slug"),
                price=data.get("price"),
                is_active=data.get("is_active", True),
            )
        except ValidationError:
            raise
        except Exception:
            raise ValidationError({
                "message": "Failed to create product."
            })

        return Response(
            {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "price": str(product.price),
                "is_active": product.is_active,
                "created_at": product.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# ADMIN PRODUCT DETAIL + PATCH
# ==================================================

class AdminProductDetailView(AdminJWTAPIView):

    def get(self, request, pk: int):
        product = get_object_or_404(
            Product.objects.prefetch_related(
                "variants",
                "attribute_values__attribute",
                "images",
                "categories",
            ),
            pk=pk,
        )

        primary_image = (
            product.images
            .filter(is_primary=True)
            .order_by("ordering", "id")
            .first()
        )

        return Response(
            {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "description": product.description,
                "price": str(product.price),
                "old_price": (
                    str(product.old_price)
                    if product.old_price is not None
                    else None
                ),
                "is_active": product.is_active,
                "is_featured": product.is_featured,
                "categories": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "slug": c.slug,
                        "parent_id": c.parent_id,
                    }
                    for c in product.categories.all()
                ],
                "created_at": product.created_at.isoformat(),
                "updated_at": product.updated_at.isoformat(),
                "main_image": (
                    request.build_absolute_uri(primary_image.image.url)
                    if primary_image
                    else None
                ),
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)
        data = request.data or {}

        if "is_active" in data:
            raise ValidationError({
                "is_active": "Use the deactivate endpoint."
            })

        try:
            product = update_product(
                product=product,
                price=data.get("price"),
                old_price=data.get("old_price"),
                is_featured=data.get("is_featured"),
            )

            if "category_ids" in data:
                update_product_categories(
                    product=product,
                    category_ids=data.get("category_ids"),
                )

        except ValidationError:
            raise
        except Exception:
            raise ValidationError({
                "message": "Failed to update product."
            })

        product.refresh_from_db()

        return Response(
            {
                "id": product.id,
                "price": str(product.price),
                "old_price": (
                    str(product.old_price)
                    if product.old_price is not None
                    else None
                ),
                "is_featured": product.is_featured,
                "updated_at": product.updated_at.isoformat(),
            },
            status=status.HTTP_200_OK,
        )


# ==================================================
# ADMIN PRODUCT BASIC INFO
# ==================================================

class AdminProductBasicInfoUpdateView(AdminJWTAPIView):

    def patch(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)
        data = request.data or {}

        try:
            product = update_product_basic_info(
                product=product,
                name=data.get("name"),
                slug=data.get("slug"),
            )
        except ValidationError:
            raise
        except Exception:
            raise ValidationError({
                "message": "Failed to update product info."
            })

        return Response(
            {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "updated_at": product.updated_at.isoformat(),
            },
            status=status.HTTP_200_OK,
        )


# ==================================================
# ADMIN PRODUCT DEACTIVATION
# ==================================================

class AdminProductDeactivateView(AdminJWTAPIView):

    def post(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)

        try:
            product = deactivate_product(product=product)
        except ValidationError:
            raise
        except Exception:
            raise ValidationError({
                "message": "Failed to deactivate product."
            })

        return Response(
            {
                "id": product.id,
                "is_active": product.is_active,
            },
            status=status.HTTP_200_OK,
        )
