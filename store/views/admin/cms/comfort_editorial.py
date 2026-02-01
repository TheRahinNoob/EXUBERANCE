from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status

# 🔐 JWT AUTH
from rest_framework_simplejwt.authentication import JWTAuthentication

from store.models.landing_comfort_editorial import (
    ComfortEditorialBlock,
)


# ==================================================
# BASE ADMIN VIEW (JWT ENFORCED)
# ==================================================

class AdminJWTAPIView(APIView):
    """
    Base class for ALL admin CMS views.

    Enforces:
    - JWT authentication
    - Admin-only access
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]


# ==================================================
# 🧠 ADMIN — COMFORT EDITORIAL (LIST + CREATE)
# ==================================================

class AdminComfortEditorialBlockListCreateView(AdminJWTAPIView):
    """
    Admin CMS endpoint for Comfort Editorial blocks.

    RESPONSIBILITIES:
    - List all editorial blocks (ordered)
    - Create new editorial block

    GUARANTEES:
    - Admin-only
    - Stable ordering
    - RAW ARRAY response (NO { items })
    """

    def get(self, request):
        blocks = (
            ComfortEditorialBlock.objects
            .all()
            .order_by("ordering", "id")
        )

        return Response(
            [
                {
                    "id": block.id,
                    "title": block.title,
                    "subtitle": block.subtitle,
                    "image": (
                        request.build_absolute_uri(block.image.url)
                        if block.image
                        else None
                    ),
                    "cta_text": block.cta_text,
                    "cta_url": block.cta_url,
                    "ordering": block.ordering,
                    "is_active": block.is_active,
                    "created_at": block.created_at.isoformat(),
                }
                for block in blocks
            ],
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        data = request.data or {}

        title = (data.get("title") or "").strip()
        if not title:
            return Response(
                {"error": "Title is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        block = ComfortEditorialBlock.objects.create(
            title=title,
            subtitle=data.get("subtitle") or None,
            cta_text=data.get("cta_text") or None,
            cta_url=data.get("cta_url") or None,
            image=data.get("image"),
            is_active=bool(data.get("is_active", True)),
            ordering=ComfortEditorialBlock.objects.count(),
        )

        return Response(
            {
                "id": block.id,
                "message": "Comfort editorial block created",
            },
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# 🧠 ADMIN — COMFORT EDITORIAL (DETAIL)
# ==================================================

class AdminComfortEditorialBlockDetailView(AdminJWTAPIView):
    """
    Retrieve / Update / Delete a Comfort Editorial block.
    """

    def get_object(self, pk: int):
        return get_object_or_404(
            ComfortEditorialBlock,
            pk=pk,
        )

    def get(self, request, pk: int):
        block = self.get_object(pk)

        return Response(
            {
                "id": block.id,
                "title": block.title,
                "subtitle": block.subtitle,
                "image": (
                    request.build_absolute_uri(block.image.url)
                    if block.image
                    else None
                ),
                "cta_text": block.cta_text,
                "cta_url": block.cta_url,
                "ordering": block.ordering,
                "is_active": block.is_active,
                "created_at": block.created_at.isoformat(),
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, pk: int):
        block = self.get_object(pk)
        data = request.data or {}

        fields_updated = []

        if "title" in data:
            block.title = (data.get("title") or "").strip()
            fields_updated.append("title")

        if "subtitle" in data:
            block.subtitle = data.get("subtitle") or None
            fields_updated.append("subtitle")

        if "cta_text" in data:
            block.cta_text = data.get("cta_text") or None
            fields_updated.append("cta_text")

        if "cta_url" in data:
            block.cta_url = data.get("cta_url") or None
            fields_updated.append("cta_url")

        if "image" in data:
            block.image = data.get("image")
            fields_updated.append("image")

        if "is_active" in data:
            block.is_active = bool(data.get("is_active"))
            fields_updated.append("is_active")

        if fields_updated:
            block.save(update_fields=fields_updated)

        return Response(
            {"message": "Comfort editorial block updated"},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        block = self.get_object(pk)
        block.delete()

        return Response(
            {"message": "Comfort editorial block deleted"},
            status=status.HTTP_204_NO_CONTENT,
        )


# ==================================================
# 🔁 ADMIN — COMFORT EDITORIAL (REORDER)
# ==================================================

class AdminComfortEditorialBlockReorderView(AdminJWTAPIView):
    """
    Reorder Comfort Editorial blocks.

    Payload:
    {
      "order": [3, 1, 2]
    }
    """

    def post(self, request):
        order = request.data.get("order")

        if not isinstance(order, list):
            return Response(
                {"error": "Invalid order payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            for index, block_id in enumerate(order):
                ComfortEditorialBlock.objects.filter(
                    id=block_id
                ).update(ordering=index)

        return Response(
            {"message": "Order updated"},
            status=status.HTTP_200_OK,
        )
