# ==================================================
# ADMIN CMS — LANDING MENU ITEMS
# ==================================================
#
# PURPOSE:
# - Manage landing page BODY MENU items
# - Mirror Django Admin behavior exactly
#
# PRINCIPLES:
# - Backend is the source of truth
# - No silent coercion
# - Explicit validation
# - Stable response contract
#
# GUARANTEES:
# - No duplicate categories
# - No inactive categories
# - Ordering always consistent
# - Transaction-safe writes
#
# ==================================================

from typing import Dict, Any

from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status

from store.models.landing import LandingMenuItem
from store.models.category import Category


# ==================================================
# SERIALIZER (ADMIN CONTRACT)
# ==================================================

def serialize_landing_menu_item(
    item: LandingMenuItem,
) -> Dict[str, Any]:
    """
    Canonical admin response shape.
    This is a HARD CONTRACT for frontend.
    """

    return {
        "id": item.id,

        # Category (embedded snapshot)
        "category": {
            "id": item.category.id,
            "name": item.category.name,
            "slug": item.category.slug,
        },

        # SEO overrides
        "seo_title": item.seo_title,
        "seo_description": item.seo_description,

        # Visibility & ordering
        "is_active": item.is_active,
        "ordering": item.ordering,

        # System fields
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


# ==================================================
# LIST + CREATE
# ==================================================

class AdminLandingMenuItemListCreateView(APIView):
    """
    GET:
    - List ALL landing menu items (active + inactive)
    - Ordered exactly like Django Admin

    POST:
    - Create a landing menu item
    - Enforces:
        • category exists
        • category is active
        • category is unique
    """

    permission_classes = [IsAdminUser]

    # --------------------------------------------------
    # GET — LIST
    # --------------------------------------------------

    def get(self, request):
        items = (
            LandingMenuItem.objects
            .select_related("category")
            .order_by("ordering", "id")
        )

        return Response(
            [serialize_landing_menu_item(item) for item in items],
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------
    # POST — CREATE
    # --------------------------------------------------

    @transaction.atomic
    def post(self, request):
        data = request.data

        category_id = data.get("category_id")
        if not category_id:
            return Response(
                {"detail": "category_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category = get_object_or_404(Category, pk=category_id)

        # --------------------------------------------------
        # HARD RULES (DJANGO ADMIN PARITY)
        # --------------------------------------------------

        if not category.is_active:
            return Response(
                {"detail": "This category is inactive and cannot be used."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            item = LandingMenuItem.objects.create(
                category=category,
                seo_title=data.get("seo_title", ""),
                seo_description=data.get("seo_description", ""),
                is_active=_bool(data.get("is_active", True)),
                ordering=_int(data.get("ordering", 0)),
            )
        except IntegrityError:
            # DB-level uniqueness guard
            return Response(
                {"detail": "This category already exists in landing menu."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            serialize_landing_menu_item(item),
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# DETAIL — UPDATE / DELETE
# ==================================================

class AdminLandingMenuItemDetailView(APIView):
    """
    PATCH:
    - Update visibility, ordering, SEO
    - Category CANNOT be changed

    DELETE:
    - Hard delete (explicit & intentional)
    """

    permission_classes = [IsAdminUser]

    # --------------------------------------------------
    # PATCH — UPDATE
    # --------------------------------------------------

    @transaction.atomic
    def patch(self, request, pk: int):
        item = get_object_or_404(
            LandingMenuItem.objects.select_related("category"),
            pk=pk,
        )

        data = request.data

        # --------------------------------------------------
        # CATEGORY CHANGE IS FORBIDDEN
        # --------------------------------------------------
        if "category_id" in data:
            return Response(
                {"detail": "Category cannot be changed once created."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --------------------------------------------------
        # CATEGORY MUST REMAIN ACTIVE
        # --------------------------------------------------
        if not item.category.is_active:
            return Response(
                {
                    "detail": (
                        "This category is inactive and "
                        "cannot be used in landing menu."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --------------------------------------------------
        # APPLY UPDATES
        # --------------------------------------------------
        if "seo_title" in data:
            item.seo_title = data.get("seo_title", "")

        if "seo_description" in data:
            item.seo_description = data.get("seo_description", "")

        if "is_active" in data:
            item.is_active = _bool(data.get("is_active"))

        if "ordering" in data:
            item.ordering = _int(data.get("ordering"))

        item.save()

        return Response(
            serialize_landing_menu_item(item),
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------
    # DELETE — HARD REMOVE
    # --------------------------------------------------

    @transaction.atomic
    def delete(self, request, pk: int):
        item = get_object_or_404(LandingMenuItem, pk=pk)
        item.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


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
