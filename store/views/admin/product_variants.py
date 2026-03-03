from __future__ import annotations

from typing import Any, Dict

from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

# 🔐 JWT AUTH
from rest_framework_simplejwt.authentication import JWTAuthentication

from store.models import Product, ProductVariant
from store.services.product_variant_service import (
    bulk_create_product_variants,
    create_product_variant,
    delete_product_variant,
    update_product_variant_stock,
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
    # Keep contract stable and JSON-safe
    return {
        "id": v.id,
        "size": v.size,
        "color": v.color,
        "color_hex": getattr(v, "color_hex", "") or "",
        "stock": int(v.stock),
    }


def _coerce_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(
            {field: f"{field.replace('_', ' ').title()} must be an integer."}
        )


def _coerce_hex(value: Any) -> str:
    """
    Admin API accepts either:
    - "" / null  -> ""
    - "#RRGGBB"  -> uppercased "#RRGGBB"
    Any other value raises ValidationError.
    """
    s = str(value or "").strip().upper()
    if not s:
        return ""
    if len(s) != 7 or not s.startswith("#"):
        raise ValidationError({"color_hex": "Hex color must be in the format #RRGGBB."})
    allowed = "0123456789ABCDEF"
    if not all(ch in allowed for ch in s[1:]):
        raise ValidationError({"color_hex": "Hex color must be in the format #RRGGBB."})
    return s


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

        size = data.get("size")
        color = data.get("color")
        stock = data.get("stock", 0)

        # Optional
        color_hex = _coerce_hex(data.get("color_hex", ""))

        try:
            # Prefer new service signature that supports color_hex
            variant = create_product_variant(
                product=product,
                size=size,
                color=color,
                color_hex=color_hex,
                stock=stock,
            )
        except TypeError:
            # Backward-compatible fallback if service is not yet updated
            variant = create_product_variant(
                product=product,
                size=size,
                color=color,
                stock=stock,
            )
            # If model has the field, persist it here (best-effort)
            if hasattr(variant, "color_hex"):
                variant.color_hex = color_hex
                variant.save(update_fields=["color_hex"])
        except ValidationError:
            raise
        except Exception:
            raise ValidationError({"detail": "Failed to create product variant."})

        return Response(_variant_to_dict(variant), status=status.HTTP_201_CREATED)


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
#   "color_hex": "#0000FF",      // optional
#   "sizes": ["38", "40", "42"], // list
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

        default_stock = (
            data.get("default_stock")
            if "default_stock" in data
            else data.get("stock", 0)
        )

        color_hex = _coerce_hex(data.get("color_hex", ""))

        try:
            # Prefer new service signature that supports color_hex
            result = bulk_create_product_variants(
                product=product,
                color=data.get("color"),
                color_hex=color_hex,
                sizes=data.get("sizes"),
                default_stock=default_stock,
            )
        except TypeError:
            # Backward-compatible fallback if service is not yet updated
            result = bulk_create_product_variants(
                product=product,
                color=data.get("color"),
                sizes=data.get("sizes"),
                default_stock=default_stock,
            )
            # Best-effort: if model has the field, set on any newly created variants
            created_items = (result or {}).get("created", [])
            if hasattr(ProductVariant, "color_hex") and created_items:
                created_ids = [item.get("id") for item in created_items if isinstance(item, dict)]
                created_ids = [i for i in created_ids if isinstance(i, int)]
                if created_ids:
                    ProductVariant.objects.filter(id__in=created_ids).update(color_hex=color_hex)
                    # keep response consistent
                    for item in created_items:
                        if isinstance(item, dict):
                            item["color_hex"] = color_hex
        except ValidationError:
            raise
        except Exception:
            raise ValidationError({"detail": "Failed to bulk create product variants."})

        # Ensure response is consistent with frontend contract
        if isinstance(result, dict):
            result.setdefault("color_hex", color_hex)
            created_items = result.get("created")
            if isinstance(created_items, list):
                for item in created_items:
                    if isinstance(item, dict):
                        item.setdefault("color_hex", color_hex)

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
    Update stock (and optionally color_hex) or delete a variant.

    NOTE:
    - delete_product_variant() already converts ProtectedError -> ValidationError(detail=...)
      in the service, so we only catch ValidationError here.
    """

    @transaction.atomic
    def patch(self, request, variant_id: int):
        variant = get_object_or_404(ProductVariant, pk=variant_id)
        data = request.data or {}

        # Stock is the primary supported field (used by your admin UI)
        if "stock" not in data and "color_hex" not in data:
            raise ValidationError({"detail": "Nothing to update."})

        updated_fields = []

        if "stock" in data:
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

            variant = updated
            updated_fields.append("stock")

        # Optional: allow updating hex too (won’t break existing frontend)
        if "color_hex" in data and hasattr(variant, "color_hex"):
            variant.color_hex = _coerce_hex(data.get("color_hex"))
            variant.save(update_fields=["color_hex"])
            updated_fields.append("color_hex")

        return Response(
            {
                "id": variant.id,
                "stock": int(variant.stock),
                "color_hex": getattr(variant, "color_hex", "") or "",
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def delete(self, request, variant_id: int):
        variant = get_object_or_404(ProductVariant, pk=variant_id)

        try:
            delete_product_variant(variant=variant)
        except ValidationError:
            raise
        except Exception:
            raise ValidationError({"detail": "Failed to delete product variant."})

        return Response(status=status.HTTP_204_NO_CONTENT)