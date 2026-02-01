from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware, is_naive
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework import status

# 🔐 JWT AUTH
from rest_framework_simplejwt.authentication import JWTAuthentication

from store.models import Category
from store.services.category_service import (
    create_category,
    update_category,
    delete_category,
    reorder_categories,
)

# ==================================================
# INTERNAL HELPERS
# ==================================================

def parse_datetime_or_none(value: Optional[str]):
    if value in (None, "", "null", "undefined"):
        return None

    dt = parse_datetime(value)
    if not dt:
        raise DRFValidationError({
            "datetime": "Invalid datetime format. Use ISO-8601."
        })

    if is_naive(dt):
        dt = make_aware(dt)

    return dt


# ==================================================
# BASE ADMIN VIEW (JWT ENFORCED)
# ==================================================

class AdminJWTAPIView(APIView):
    """
    Base class for ALL admin views.
    Enforces:
    - JWT Authentication
    - Admin-only access
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]


# ==================================================
# ADMIN CATEGORY LIST + CREATE
# ==================================================

class AdminCategoryListCreateView(AdminJWTAPIView):

    def get(self, request):
        categories = (
            Category.objects
            .all()
            .order_by("ordering", "-priority", "name")
        )

        return Response(
            [
                {
                    "id": c.id,
                    "name": c.name,
                    "slug": c.slug,
                    "parent_id": c.parent_id,
                    "ordering": c.ordering,
                    "priority": c.priority,
                    "is_active": c.is_active,

                    "is_campaign": c.is_campaign,
                    "starts_at": c.starts_at.isoformat() if c.starts_at else None,
                    "ends_at": c.ends_at.isoformat() if c.ends_at else None,
                    "show_countdown": c.show_countdown,
                }
                for c in categories
            ],
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        data = request.data or {}

        name = data.get("name")
        slug = data.get("slug")

        if not name or not str(name).strip():
            raise DRFValidationError({"name": "Category name is required."})

        parent = None
        if data.get("parent_id") is not None:
            parent = get_object_or_404(Category, pk=data["parent_id"])

        try:
            category = create_category(
                name=name.strip(),
                slug=slug,
                parent=parent,
                ordering=data.get("ordering", 0),
                priority=data.get("priority", 0),
                is_active=data.get("is_active", True),

                is_campaign=bool(data.get("is_campaign", False)),
                starts_at=parse_datetime_or_none(data.get("starts_at")),
                ends_at=parse_datetime_or_none(data.get("ends_at")),
                show_countdown=bool(data.get("show_countdown", False)),
            )
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})

        return Response(
            {"id": category.id},
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# ADMIN CATEGORY DETAIL
# ==================================================

class AdminCategoryDetailView(AdminJWTAPIView):

    def patch(self, request, pk: int):
        category = get_object_or_404(Category, pk=pk)
        data = request.data or {}

        parent = None
        if "parent_id" in data:
            parent_id = data.get("parent_id")
            if parent_id is not None:
                parent = get_object_or_404(Category, pk=parent_id)

                if parent == category:
                    raise DRFValidationError({
                        "parent_id": "Category cannot be its own parent."
                    })

                if category in parent.get_descendants(include_self=True):
                    raise DRFValidationError({
                        "parent_id": "Circular category hierarchy is not allowed."
                    })

        try:
            category = update_category(
                category=category,
                name=data.get("name"),
                slug=data.get("slug"),
                parent=parent if "parent_id" in data else None,
                ordering=data.get("ordering"),
                priority=data.get("priority"),
                is_active=data.get("is_active"),

                is_campaign=data.get("is_campaign"),
                starts_at=parse_datetime_or_none(data.get("starts_at"))
                if "starts_at" in data else None,
                ends_at=parse_datetime_or_none(data.get("ends_at"))
                if "ends_at" in data else None,
                show_countdown=data.get("show_countdown"),
            )
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages})

        return Response({"status": "updated"}, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        category = get_object_or_404(Category, pk=pk)

        delete_category(category=category)

        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================================================
# ADMIN CATEGORY TREE
# ==================================================

class AdminCategoryTreeView(AdminJWTAPIView):

    def get(self, request):
        categories = (
            Category.objects
            .all()
            .order_by("ordering", "-priority", "name")
            .only("id", "name", "slug", "parent_id", "is_active", "is_campaign")
        )

        node_map: Dict[int, dict] = {}
        children_map: Dict[int | None, List[dict]] = defaultdict(list)

        for c in categories:
            node = {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "parent_id": c.parent_id,
                "is_active": c.is_active,
                "is_campaign": c.is_campaign,
                "children": [],
            }
            node_map[c.id] = node
            children_map[c.parent_id].append(node)

        for parent_id, children in children_map.items():
            if parent_id in node_map:
                node_map[parent_id]["children"] = children

        return Response(children_map[None], status=status.HTTP_200_OK)


# ==================================================
# ADMIN CATEGORY REORDER
# ==================================================

class AdminCategoryReorderView(AdminJWTAPIView):

    @transaction.atomic
    def post(self, request):
        ids = request.data.get("ids")

        if not isinstance(ids, list) or not ids:
            raise DRFValidationError({
                "ids": "Must be a non-empty list of category IDs."
            })

        reorder_categories(ordered_ids=ids)

        return Response({"status": "ok"}, status=status.HTTP_200_OK)
