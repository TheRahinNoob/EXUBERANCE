from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status

from store.models.landing import (
    HotCategory,
    HotCategoryBlock,
    HotCategoryBlockItem,
)


# ==================================================
# HOT CATEGORY BLOCK — LIST + CREATE
# ==================================================

class AdminHotCategoryBlockListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        blocks = (
            HotCategoryBlock.objects
            .prefetch_related("items__hot_category__category")
            .order_by("ordering", "id")
        )

        return Response([
            {
                "id": block.id,
                "title": block.title,
                "is_active": block.is_active,
                "ordering": block.ordering,
                "created_at": block.created_at,
                "items": [
                    {
                        "id": item.id,
                        "ordering": item.ordering,
                        "is_active": item.is_active,
                        "hot_category": {
                            "id": item.hot_category.id,
                            "image": (
                                request.build_absolute_uri(
                                    item.hot_category.image.url
                                )
                                if item.hot_category.image
                                else None
                            ),
                            "category": {
                                "id": item.hot_category.category.id,
                                "name": item.hot_category.category.name,
                                "slug": item.hot_category.category.slug,
                            },
                        },
                    }
                    for item in block.items.all().order_by("ordering", "id")
                ],
            }
            for block in blocks
        ])

    @transaction.atomic
    def post(self, request):
        title = str(request.data.get("title", "")).strip()

        max_ordering = (
            HotCategoryBlock.objects
            .aggregate(max_val=Max("ordering"))["max_val"]
        )

        next_order = 0 if max_ordering is None else max_ordering + 1

        block = HotCategoryBlock(
            title=title or "Untitled Block",
            ordering=next_order,
            is_active=True,
        )

        block.full_clean()
        block.save()

        return Response(
            {
                "id": block.id,
                "title": block.title,
                "is_active": block.is_active,
                "ordering": block.ordering,
                "created_at": block.created_at,
                "items": [],
            },
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# HOT CATEGORY BLOCK — DETAIL / UPDATE / DELETE
# ==================================================

class AdminHotCategoryBlockDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        block = get_object_or_404(
            HotCategoryBlock.objects.prefetch_related(
                "items__hot_category__category"
            ),
            pk=pk,
        )

        return Response(
            {
                "id": block.id,
                "title": block.title,
                "is_active": block.is_active,
                "ordering": block.ordering,
                "created_at": block.created_at,
                "items": [
                    {
                        "id": item.id,
                        "ordering": item.ordering,
                        "is_active": item.is_active,
                        "hot_category": {
                            "id": item.hot_category.id,
                            "image": (
                                request.build_absolute_uri(
                                    item.hot_category.image.url
                                )
                                if item.hot_category.image
                                else None
                            ),
                            "category": {
                                "id": item.hot_category.category.id,
                                "name": item.hot_category.category.name,
                                "slug": item.hot_category.category.slug,
                            },
                        },
                    }
                    for item in block.items.all().order_by("ordering", "id")
                ],
            }
        )

    @transaction.atomic
    def patch(self, request, pk):
        block = get_object_or_404(HotCategoryBlock, pk=pk)
        updated = False

        if "title" in request.data:
            value = str(request.data["title"]).strip()
            if value:
                block.title = value
                updated = True

        if "is_active" in request.data:
            block.is_active = bool(request.data["is_active"])
            updated = True

        if "ordering" in request.data:
            try:
                ordering = int(request.data["ordering"])
                if ordering < 0:
                    raise ValueError
                block.ordering = ordering
                updated = True
            except (TypeError, ValueError):
                return Response(
                    {"detail": "ordering must be a non-negative integer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not updated:
            return Response(
                {"detail": "No valid fields provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        block.full_clean()
        block.save()

        return Response(
            {
                "id": block.id,
                "title": block.title,
                "is_active": block.is_active,
                "ordering": block.ordering,
                "created_at": block.created_at,
            }
        )

    @transaction.atomic
    def delete(self, request, pk):
        block = get_object_or_404(HotCategoryBlock, pk=pk)
        block.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================================================
# HOT CATEGORY BLOCK ITEM — CREATE
# ==================================================

class AdminHotCategoryBlockItemCreateView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, pk):
        block = get_object_or_404(HotCategoryBlock, pk=pk)

        hot_category_id = request.data.get("hot_category_id")
        if not hot_category_id:
            return Response(
                {"detail": "hot_category_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        hot_category = get_object_or_404(HotCategory, pk=hot_category_id)

        if HotCategoryBlockItem.objects.filter(
            block=block,
            hot_category=hot_category,
        ).exists():
            return Response(
                {"detail": "Hot category already exists in this block"},
                status=status.HTTP_409_CONFLICT,
            )

        max_ordering = (
            HotCategoryBlockItem.objects
            .filter(block=block)
            .aggregate(max_val=Max("ordering"))["max_val"]
        )

        next_order = 0 if max_ordering is None else max_ordering + 1

        item = HotCategoryBlockItem(
            block=block,
            hot_category=hot_category,
            ordering=next_order,
            is_active=True,
        )

        item.full_clean()
        item.save()

        return Response(
            {
                "id": item.id,
                "ordering": item.ordering,
                "is_active": item.is_active,
                "hot_category": {
                    "id": hot_category.id,
                    "image": (
                        request.build_absolute_uri(
                            hot_category.image.url
                        )
                        if hot_category.image
                        else None
                    ),
                    "category": {
                        "id": hot_category.category.id,
                        "name": hot_category.category.name,
                        "slug": hot_category.category.slug,
                    },
                },
            },
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# HOT CATEGORY BLOCK ITEM — DELETE  🔥🔥🔥
# ==================================================

class AdminHotCategoryBlockItemDeleteView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def delete(self, request, pk, item_id):
        item = get_object_or_404(
            HotCategoryBlockItem,
            pk=item_id,
            block_id=pk,
        )

        item.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================================================
# HOT CATEGORY BLOCK ITEM — REORDER / TOGGLE
# ==================================================

class AdminHotCategoryBlockItemReorderView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, pk):
        block = get_object_or_404(HotCategoryBlock, pk=pk)

        payload_items = request.data.get("items")
        if not isinstance(payload_items, list):
            return Response(
                {"detail": "items must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        block_items = list(
            HotCategoryBlockItem.objects
            .filter(block=block)
            .order_by("ordering", "id")
        )

        if len(payload_items) != len(block_items):
            return Response(
                {"detail": "Item count mismatch"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item_map = {item.id: item for item in block_items}
        seen_ids = set()

        for index, payload in enumerate(payload_items):
            item_id = payload.get("id")

            if item_id in seen_ids:
                return Response(
                    {"detail": f"Duplicate item id {item_id}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            item = item_map.get(item_id)
            if not item:
                return Response(
                    {"detail": f"Invalid block item id {item_id}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            seen_ids.add(item_id)

            item.ordering = index
            item.is_active = bool(
                payload.get("is_active", item.is_active)
            )

            item.full_clean()
            item.save()

        return Response({"detail": "Order updated successfully"})
