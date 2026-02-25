from __future__ import annotations

from typing import Any, Dict, List

from django.shortcuts import get_object_or_404
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from rest_framework.exceptions import ValidationError

# 🔐 JWT AUTH
from rest_framework_simplejwt.authentication import JWTAuthentication

from store.models import Product, ProductVariant
from store.services.product_variant_service import (
    create_product_variant,
    bulk_create_product_variants,
    update_product_variant_stock,
    delete_product_variant,
)


# ==================================================
# BASE ADMIN VIEW (JWT ENFORCED)
# ==================================================

class AdminJWTAPIView(APIView):
    """
    Base class for ALL admin product variant views.

    Enforces:
    - JWT Authentication
    - Admin-only access
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]


# ==================================================
# RESPONSE SHAPE HELPERS (STRICT, STABLE CONTRACT)
# ==================================================

def _variant_to_dict(v: ProductVariant) -> Dict[str, Any]:
    return {
        "id": v.id,
        "size": v.size,
        "color": v.color,
        "stock": int(v.stock),
    }


def _coerce_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({field: f"{field.replace('_', ' ').title()} must be an integer."})


# ==================================================
# ADMIN PRODUCT VARIANT LIST + CREATE (SINGLE)
# ==================================================
#
# Endpoints:
# GET  /api/admin/products/<pk>/variants/
# POST /api/admin/products/<pk>/variants/
# ==================================================

class AdminProductVariantListCreateView(AdminJWTAPIView):
    """
    List variants for a product, and create a single variant.
    """

    def get(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)

        variants = (
            product.variants.all()
            .order_by("color", "size", "id")  # stable UX: group by color first
        )

        return Response(
            {"items": [_variant_to_dict(v) for v in variants]},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def post(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)
        data = request.data or {}

        # Minimal input sanity before hitting service
        size = data.get("size")
        color = data.get("color")
        stock = data.get("stock", 0)

        try:
            variant = create_product_variant(
                product=product,
                size=size,
                color=color,
                stock=stock,
            )
        except ValidationError:
            raise
        except Exception:
            # Don’t leak internals to admin UI
            raise ValidationError({"detail": "Failed to create product variant."})

        return Response(
            _variant_to_dict(variant),
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# ADMIN PRODUCT VARIANT BULK CREATE ✅
# ==================================================
#
# Endpoint:
# POST /api/admin/products/<pk>/variants/bulk/
#
# Body:
# {
#   "color": "Blue",
#   "sizes": ["38", "40", "42"],  // or any iterable list from frontend
#   "default_stock": 0
# }
# ==================================================

class AdminProductVariantBulkCreateView(AdminJWTAPIView):
    """
    Bulk create variants for ONE product + ONE color + MANY sizes.
    Idempotent: existing ones are skipped, not errors.
    """

    @transaction.atomic
    def post(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)
        data = request.data or {}

        # Accept both "default_stock" and "stock" as alias (frontend flexibility)
        default_stock = (
            data.get("default_stock")
            if "default_stock" in data
            else data.get("stock", 0)
        )

        try:
            result = bulk_create_product_variants(
                product=product,
                color=data.get("color"),
                sizes=data.get("sizes"),
                default_stock=default_stock,
            )
        except ValidationError:
            raise
        except Exception:
            raise ValidationError({"detail": "Failed to bulk create product variants."})

        # 201: created something (maybe 0 created but request accepted)
        return Response(result, status=status.HTTP_201_CREATED)


# ==================================================
# ADMIN PRODUCT VARIANT DETAIL (UPDATE / DELETE)
# ==================================================
#
# Endpoints:
# PATCH  /api/admin/product-variants/<variant_id>/
# DELETE /api/admin/product-variants/<variant_id>/
# ==================================================

class AdminProductVariantDetailView(AdminJWTAPIView):
    """
    Update stock or delete a variant.

    NOTE:
    - delete_product_variant() already converts ProtectedError -> ValidationError(detail=...)
      in the service, so we only catch ValidationError here.
    """

    @transaction.atomic
    def patch(self, request, variant_id: int):
        variant = get_object_or_404(ProductVariant, pk=variant_id)
        data = request.data or {}

        if "stock" not in data:
            raise ValidationError({"stock": "Stock is required."})

        # quick coercion for cleaner error messages
        stock = _coerce_int(data.get("stock"), "stock")

        try:
            updated = update_product_variant_stock(
                variant=variant,
                stock=stock,
            )
        except ValidationError:
            raise
        except Exception:
            raise ValidationError({"detail": "Failed to update variant stock."})

        return Response(
            {"id": updated.id, "stock": int(updated.stock)},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def delete(self, request, variant_id: int):
        variant = get_object_or_404(ProductVariant, pk=variant_id)

        try:
            delete_product_variant(variant=variant)
        except ValidationError:
            # Includes the protected-order message from the service
            raise
        except Exception:
            raise ValidationError({"detail": "Failed to delete product variant."})

        return Response(status=status.HTTP_204_NO_CONTENT)