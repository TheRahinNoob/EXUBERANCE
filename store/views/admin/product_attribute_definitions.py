from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework import status

# 🔐 JWT AUTH
from rest_framework_simplejwt.authentication import JWTAuthentication

from store.models import ProductAttribute
from store.services.product_attribute_definition_service import (
    create_attribute_definition,
    update_attribute_definition,
    archive_attribute_definition,  # ✅ SOFT DELETE
)

# ==================================================
# BASE ADMIN VIEW (JWT ENFORCED)
# ==================================================

class AdminJWTAPIView(APIView):
    """
    Base class for ALL admin attribute definition views.

    Enforces:
    - JWT Authentication
    - Admin-only access
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]


# ==================================================
# ADMIN ATTRIBUTE DEFINITIONS — LIST & CREATE
# ==================================================
# GET  /api/admin/attribute-definitions/
# POST /api/admin/attribute-definitions/
# ==================================================

class AdminProductAttributeDefinitionListView(AdminJWTAPIView):
    """
    Global product attribute definitions (ADMIN).

    Guarantees:
    - Shows active + archived attributes
    - No destructive operations
    """

    def get(self, request):
        attributes = (
            ProductAttribute.objects
            .all()  # 🔥 admin sees archived too
            .order_by("ordering", "name")
        )

        return Response(
            {
                "items": [
                    {
                        "id": attr.id,
                        "name": attr.name,
                        "ordering": attr.ordering,
                        "is_active": attr.is_active,
                    }
                    for attr in attributes
                ]
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        data = request.data or {}

        try:
            attribute = create_attribute_definition(
                name=data.get("name"),
                ordering=data.get("ordering", 0),
            )
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})

        return Response(
            {
                "id": attribute.id,
                "name": attribute.name,
                "ordering": attribute.ordering,
                "is_active": attribute.is_active,
            },
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# ADMIN ATTRIBUTE DEFINITIONS — UPDATE & ARCHIVE
# ==================================================
# PATCH  /api/admin/attribute-definitions/<id>/
# DELETE /api/admin/attribute-definitions/<id>/
# ==================================================

class AdminProductAttributeDefinitionDetailView(AdminJWTAPIView):
    """
    Attribute definition mutation (ADMIN).

    PATCH:
    - Rename
    - Reorder

    DELETE:
    - 🔥 SOFT DELETE (archive)
    """

    def patch(self, request, pk: int):
        attribute = get_object_or_404(ProductAttribute, pk=pk)
        data = request.data or {}

        try:
            attribute = update_attribute_definition(
                attribute=attribute,
                name=data.get("name"),
                ordering=data.get("ordering"),
            )
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})

        return Response(
            {
                "id": attribute.id,
                "name": attribute.name,
                "ordering": attribute.ordering,
                "is_active": attribute.is_active,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        """
        🔥 SOFT DELETE (ARCHIVE)

        - Never breaks products
        - Idempotent
        - Safe for real orders
        """

        attribute = get_object_or_404(ProductAttribute, pk=pk)

        try:
            attribute = archive_attribute_definition(
                attribute=attribute
            )
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})

        return Response(
            {
                "id": attribute.id,
                "is_active": attribute.is_active,
            },
            status=status.HTTP_200_OK,
        )
