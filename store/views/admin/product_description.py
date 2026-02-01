from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import JSONParser
from rest_framework import status

# 🔐 JWT AUTH
from rest_framework_simplejwt.authentication import JWTAuthentication

from store.models import Product
from store.services.product_service import update_product_description


# ==================================================
# BASE ADMIN VIEW (JWT ENFORCED)
# ==================================================

class AdminJWTAPIView(APIView):
    """
    Base class for ALL admin product mutation views.

    Enforces:
    - JWT Authentication
    - Admin-only access
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]


# ==================================================
# ADMIN PRODUCT DESCRIPTION UPDATE
# ==================================================
# PATCH /api/admin/products/<pk>/description/
# ==================================================

class AdminProductDescriptionUpdateView(AdminJWTAPIView):
    """
    Admin-only endpoint for updating product description (HTML).

    Contract:
    - Accepts JSON body: { "description": "<html>" }
    - description is REQUIRED
    - empty string is ALLOWED
    - HTML sanitization happens in service layer
    """

    parser_classes = [JSONParser]

    def patch(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)

        data = request.data

        if not isinstance(data, dict):
            raise DRFValidationError({
                "detail": "Invalid JSON payload."
            })

        if "description" not in data:
            raise DRFValidationError({
                "description": "This field is required."
            })

        description = data["description"]

        if not isinstance(description, str):
            raise DRFValidationError({
                "description": "Must be a string."
            })

        try:
            product = update_product_description(
                product=product,
                description=description,
            )
        except DjangoValidationError as e:
            raise DRFValidationError({
                "detail": e.messages
            })

        return Response(
            {
                "id": product.id,
                "updated_at": product.updated_at.isoformat(),
            },
            status=status.HTTP_200_OK,
        )
