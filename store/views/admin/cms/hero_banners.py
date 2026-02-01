# ==================================================
# ADMIN CMS — HERO BANNERS
# ==================================================
#
# PURPOSE:
# - Mirror Django Admin hero banner capabilities
# - Serve Next.js admin panel as a thin client
#
# DESIGN PRINCIPLES:
# - Django Admin is the source of truth
# - No inferred state, no silent coercion
# - Multipart-safe (file uploads)
# - Transactional writes
# - Explicit, stable response shape
#
# GUARANTEES:
# - No invalid banner states
# - No partial uploads
# - Ordering consistency
#
# ==================================================

from typing import Any, Dict

from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from rest_framework_simplejwt.authentication import JWTAuthentication

from store.models.hero_banner import HeroBanner


# ==================================================
# JWT BASE ADMIN VIEW (NO CSRF, NO COOKIES)
# ==================================================
class AdminJWTAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]


# ==================================================
# INTERNAL CASTING HELPERS
# ==================================================

def _bool(value) -> bool:
    """
    Robust boolean coercion for admin input.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes", "on")
    return bool(value)


def _int(value, default: int = 0) -> int:
    """
    Safe integer coercion.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ==================================================
# SERIALIZATION (ADMIN CONTRACT)
# ==================================================

def _serialize_hero_banner(banner: HeroBanner) -> Dict[str, Any]:
    """
    Canonical admin serializer.

    ⚠️ THIS IS A HARD CONTRACT.
    Frontend depends on this shape.
    """

    return {
        "id": banner.id,

        # Images (frontend resolves absolute URLs)
        "image_desktop": banner.image_desktop.url if banner.image_desktop else None,
        "image_tablet": banner.image_tablet.url if banner.image_tablet else None,
        "image_mobile": banner.image_mobile.url if banner.image_mobile else None,

        # Visibility
        "is_active": banner.is_active,
        "starts_at": banner.starts_at,
        "ends_at": banner.ends_at,
        "is_live": banner.is_live,

        # Ordering
        "ordering": banner.ordering,

        # Metadata
        "created_at": banner.created_at,
    }


# ==================================================
# LIST + CREATE
# ==================================================

class AdminHeroBannerListCreateView(AdminJWTAPIView):
    """
    GET:
    - List ALL hero banners (active + inactive)
    - Ordered exactly like Django Admin

    POST:
    - Create a new hero banner
    - Multipart upload (images)
    """

    parser_classes = [MultiPartParser, FormParser]

    # --------------------------------------------------
    # GET — LIST
    # --------------------------------------------------

    def get(self, request):
        banners = (
            HeroBanner.objects
            .all()
            .order_by("ordering", "id")
        )

        return Response(
            [_serialize_hero_banner(b) for b in banners],
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------
    # POST — CREATE
    # --------------------------------------------------

    @transaction.atomic
    def post(self, request):
        data = request.data

        # --------------------------------------------------
        # REQUIRED IMAGES
        # --------------------------------------------------

        if "image_desktop" not in data:
            return Response(
                {"detail": "image_desktop is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "image_tablet" not in data:
            return Response(
                {"detail": "image_tablet is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "image_mobile" not in data:
            return Response(
                {"detail": "image_mobile is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --------------------------------------------------
        # CREATE (ATOMIC)
        # --------------------------------------------------

        banner = HeroBanner.objects.create(
            image_desktop=data.get("image_desktop"),
            image_tablet=data.get("image_tablet"),
            image_mobile=data.get("image_mobile"),

            is_active=_bool(data.get("is_active", True)),
            ordering=_int(data.get("ordering", 0)),

            starts_at=data.get("starts_at") or None,
            ends_at=data.get("ends_at") or None,
        )

        return Response(
            _serialize_hero_banner(banner),
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# DETAIL — UPDATE / DELETE
# ==================================================

class AdminHeroBannerDetailView(AdminJWTAPIView):
    """
    PATCH:
    - Update images (replace)
    - Update visibility / schedule
    - Update ordering

    DELETE:
    - Hard delete (explicit)
    """

    parser_classes = [MultiPartParser, FormParser]

    # --------------------------------------------------
    # PATCH — UPDATE
    # --------------------------------------------------

    @transaction.atomic
    def patch(self, request, pk: int):
        banner = get_object_or_404(HeroBanner, pk=pk)
        data = request.data

        # --------------------------------------------------
        # IMAGE UPDATES (OPTIONAL)
        # --------------------------------------------------

        if "image_desktop" in data:
            banner.image_desktop = data.get("image_desktop")

        if "image_tablet" in data:
            banner.image_tablet = data.get("image_tablet")

        if "image_mobile" in data:
            banner.image_mobile = data.get("image_mobile")

        # --------------------------------------------------
        # VISIBILITY / SCHEDULING
        # --------------------------------------------------

        if "is_active" in data:
            banner.is_active = _bool(data.get("is_active"))

        if "starts_at" in data:
            banner.starts_at = data.get("starts_at") or None

        if "ends_at" in data:
            banner.ends_at = data.get("ends_at") or None

        # --------------------------------------------------
        # ORDERING
        # --------------------------------------------------

        if "ordering" in data:
            banner.ordering = _int(data.get("ordering"))

        banner.save()

        return Response(
            _serialize_hero_banner(banner),
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------
    # DELETE — HARD REMOVE
    # --------------------------------------------------

    @transaction.atomic
    def delete(self, request, pk: int):
        banner = get_object_or_404(HeroBanner, pk=pk)
        banner.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
