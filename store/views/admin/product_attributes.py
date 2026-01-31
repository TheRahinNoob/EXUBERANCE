from django.shortcuts import get_object_or_404
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from rest_framework.exceptions import ValidationError

from store.models import Product, ProductAttributeValue
from store.services.product_attribute_service import (
    create_or_update_attribute_value,
    update_product_attribute_value,
    delete_product_attribute_value,
    reorder_product_attribute_values,
)

# ==================================================
# ADMIN PRODUCT ATTRIBUTE LIST + UPSERT
# ==================================================

class AdminProductAttributeListView(APIView):
    """
    Admin-only product attribute endpoint.

    GET:
    - List all attribute values for a product

    POST:
    - Assign or update an attribute value (UPSERT)
    """

    permission_classes = [IsAdminUser]

    # -----------------------------
    # LIST ATTRIBUTE VALUES
    # -----------------------------
    def get(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)

        values = (
            product.attribute_values
            .select_related("attribute")
            .order_by("ordering", "id")
        )

        return Response(
            {
                "items": [
                    {
                        "id": pav.id,
                        "attribute_id": pav.attribute.id,
                        "attribute_name": pav.attribute.name,
                        "value": pav.value,
                        "ordering": pav.ordering,
                    }
                    for pav in values
                ]
            },
            status=status.HTTP_200_OK,
        )

    # -----------------------------
    # CREATE / UPDATE (UPSERT)
    # -----------------------------
    def post(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)
        data = request.data or {}

        try:
            pav = create_or_update_attribute_value(
                product=product,
                attribute_id=data.get("attribute_id"),
                value=data.get("value"),
                ordering=data.get("ordering", 0),
            )
        except ValidationError:
            raise
        except Exception:
            raise ValidationError(
                {"message": "Failed to assign product attribute."}
            )

        return Response(
            {
                "id": pav.id,
                "attribute_id": pav.attribute.id,
                "attribute_name": pav.attribute.name,
                "value": pav.value,
                "ordering": pav.ordering,
            },
            status=status.HTTP_200_OK,  # UPSERT semantics
        )


# ==================================================
# ADMIN PRODUCT ATTRIBUTE DETAIL (UPDATE / DELETE)
# ==================================================

class AdminProductAttributeDetailView(APIView):
    """
    PATCH:
    - Update attribute value / ordering

    DELETE:
    - Remove attribute from product
    """

    permission_classes = [IsAdminUser]

    # -----------------------------
    # UPDATE ATTRIBUTE VALUE
    # -----------------------------
    def patch(self, request, pav_id: int):
        pav = get_object_or_404(ProductAttributeValue, pk=pav_id)
        data = request.data or {}

        try:
            pav = update_product_attribute_value(
                pav=pav,
                value=data.get("value"),
                ordering=data.get("ordering"),
            )
        except ValidationError:
            raise
        except Exception:
            raise ValidationError(
                {"message": "Failed to update attribute value."}
            )

        return Response(
            {
                "id": pav.id,
                "attribute_id": pav.attribute.id,
                "attribute_name": pav.attribute.name,
                "value": pav.value,
                "ordering": pav.ordering,
            },
            status=status.HTTP_200_OK,
        )

    # -----------------------------
    # DELETE ATTRIBUTE VALUE
    # -----------------------------
    def delete(self, request, pav_id: int):
        pav = get_object_or_404(ProductAttributeValue, pk=pav_id)

        try:
            delete_product_attribute_value(pav=pav)
        except ValidationError:
            raise
        except Exception:
            raise ValidationError(
                {"message": "Failed to delete attribute value."}
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================================================
# ADMIN PRODUCT ATTRIBUTE REORDER (DRAG & DROP)
# ==================================================

class AdminProductAttributeReorderView(APIView):
    """
    POST:
    - Reorder attribute values for a product

    Payload:
    {
        "ordered_ids": [3, 7, 1, 5]
    }
    """

    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)

        ordered_ids = request.data.get("ordered_ids")

        if not isinstance(ordered_ids, list):
            raise ValidationError(
                {"ordered_ids": "Must be a list of attribute value IDs."}
            )

        try:
            reorder_product_attribute_values(
                product=product,
                ordered_pav_ids=ordered_ids,
            )
        except ValidationError:
            raise
        except Exception:
            raise ValidationError(
                {"message": "Failed to reorder product attributes."}
            )

        return Response(status=status.HTTP_200_OK)
