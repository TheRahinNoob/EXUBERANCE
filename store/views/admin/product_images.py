from django.shortcuts import get_object_or_404
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from rest_framework.exceptions import ValidationError

from store.models import Product, ProductImage
from store.services.product_image_service import (
    add_product_image,
    set_primary_image,
)

# ==================================================
# ADMIN PRODUCT IMAGE LIST + CREATE
# ==================================================

class AdminProductImageListCreateView(APIView):
    """
    Admin-only product image gallery endpoint.

    GET:
    - List all images for a product (ordered)

    POST:
    - Upload a new product image
    - Optionally mark as primary
    """

    permission_classes = [IsAdminUser]

    # -----------------------------
    # LIST PRODUCT IMAGES
    # -----------------------------
    def get(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)

        images = product.images.all().order_by("ordering", "id")

        return Response(
            {
                "items": [
                    {
                        "id": image.id,
                        "image": request.build_absolute_uri(
                            image.image.url
                        ),
                        "alt_text": image.alt_text,
                        "is_primary": image.is_primary,
                        "ordering": image.ordering,
                        "created_at": image.created_at.isoformat(),
                    }
                    for image in images
                ]
            },
            status=status.HTTP_200_OK,
        )

    # -----------------------------
    # UPLOAD PRODUCT IMAGE
    # -----------------------------
    @transaction.atomic
    def post(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)

        uploaded_image = request.FILES.get("image")
        if not uploaded_image:
            raise ValidationError(
                {"image": "Image file is required."}
            )

        alt_text = request.data.get("alt_text", "").strip()

        is_primary = (
            str(request.data.get("is_primary", "false"))
            .lower()
            in ("1", "true", "yes")
        )

        product_image = add_product_image(
            product=product,
            image=uploaded_image,
            alt_text=alt_text,
            is_primary=is_primary,
        )

        return Response(
            {
                "id": product_image.id,
                "image": request.build_absolute_uri(
                    product_image.image.url
                ),
                "alt_text": product_image.alt_text,
                "is_primary": product_image.is_primary,
                "ordering": product_image.ordering,
                "created_at": product_image.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# ADMIN PRODUCT IMAGE DETAIL (PATCH / DELETE)
# ==================================================

class AdminProductImageDetailView(APIView):
    """
    Admin-only image mutation endpoint.

    PATCH:
    - Set image as primary (NO BODY REQUIRED)

    DELETE:
    - Permanently delete image
    """

    permission_classes = [IsAdminUser]

    # -----------------------------
    # SET PRIMARY IMAGE
    # -----------------------------
    @transaction.atomic
    def patch(self, request, image_id: int):
        image = get_object_or_404(ProductImage, pk=image_id)

        # 🔥 ACTION-BASED PATCH (NO BODY, NO CONTENT-TYPE)
        if not image.is_primary:
            set_primary_image(image=image)
            image.refresh_from_db()

        return Response(
            {
                "id": image.id,
                "is_primary": image.is_primary,
            },
            status=status.HTTP_200_OK,
        )

    # -----------------------------
    # DELETE IMAGE
    # -----------------------------
    @transaction.atomic
    def delete(self, request, image_id: int):
        image = get_object_or_404(ProductImage, pk=image_id)

        image.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )
