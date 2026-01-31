from django.shortcuts import get_object_or_404
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from rest_framework.exceptions import ValidationError

from store.models import Product, ProductVariant
from store.services.product_variant_service import (
    create_product_variant,
    update_product_variant_stock,
    delete_product_variant,
)

# ==================================================
# ADMIN PRODUCT VARIANT LIST + CREATE
# ==================================================
#
# Rules:
# - Admin only
# - Product is the parent (single source of truth)
# - All mutations go through service layer
# - Atomic writes
#
# Endpoints:
# GET  /api/admin/products/<pk>/variants/
# POST /api/admin/products/<pk>/variants/
# ==================================================

class AdminProductVariantListCreateView(APIView):
    permission_classes = [IsAdminUser]

    # -----------------------------
    # LIST VARIANTS
    # -----------------------------
    def get(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)

        variants = (
            product.variants
            .all()
            .order_by("size", "color", "id")  # deterministic
        )

        return Response(
            {
                "items": [
                    {
                        "id": v.id,
                        "size": v.size,
                        "color": v.color,
                        "stock": v.stock,
                    }
                    for v in variants
                ]
            },
            status=status.HTTP_200_OK,
        )

    # -----------------------------
    # CREATE VARIANT
    # -----------------------------
    @transaction.atomic
    def post(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)
        data = request.data or {}

        try:
            variant = create_product_variant(
                product=product,
                size=(data.get("size") or "").strip(),
                color=(data.get("color") or "").strip(),
                stock=data.get("stock", 0),
            )
        except ValidationError:
            raise
        except Exception:
            # Never leak internal errors to admin UI
            raise ValidationError({
                "message": "Failed to create product variant."
            })

        return Response(
            {
                "id": variant.id,
                "size": variant.size,
                "color": variant.color,
                "stock": variant.stock,
            },
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# ADMIN PRODUCT VARIANT DETAIL (MUTATIONS)
# ==================================================
#
# Endpoints:
# PATCH  /api/admin/product-variants/<variant_id>/
# DELETE /api/admin/product-variants/<variant_id>/
# ==================================================

class AdminProductVariantDetailView(APIView):
    permission_classes = [IsAdminUser]

    # -----------------------------
    # UPDATE STOCK ONLY
    # -----------------------------
    @transaction.atomic
    def patch(self, request, variant_id: int):
        variant = get_object_or_404(ProductVariant, pk=variant_id)
        data = request.data or {}

        try:
            variant = update_product_variant_stock(
                variant=variant,
                stock=data.get("stock"),
            )
        except ValidationError:
            raise
        except Exception:
            raise ValidationError({
                "message": "Failed to update variant stock."
            })

        return Response(
            {
                "id": variant.id,
                "stock": variant.stock,
            },
            status=status.HTTP_200_OK,
        )

    # -----------------------------
    # DELETE VARIANT
    # -----------------------------
    @transaction.atomic
    def delete(self, request, variant_id: int):
        variant = get_object_or_404(ProductVariant, pk=variant_id)

        try:
            delete_product_variant(variant=variant)
        except ValidationError:
            raise
        except Exception:
            raise ValidationError({
                "message": "Failed to delete product variant."
            })

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )
