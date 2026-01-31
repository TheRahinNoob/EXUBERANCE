# ==================================================
# ADMIN CMS — LANDING BLOCKS (CANONICAL)
# ==================================================
#
# RESPONSIBILITY:
# - Orchestrate landing page layout
# - Enforce CMS invariants strictly
# - Mirror Django Admin behavior exactly
#
# GUARANTEES:
# - Backend is the single source of truth
# - No invalid block states can ever exist
# - Safe for concurrent admin edits
# - Order + visibility always consistent
#
# ==================================================

from typing import Any, Dict, List

from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status

from store.models.landing_block import LandingBlock
from store.models.landing import HotCategoryBlock
from store.models.landing_comfort import ComfortCategoryRail
from store.models.landing_comfort_editorial import ComfortEditorialBlock


# ==================================================
# INTERNAL HELPERS
# ==================================================

def _serialize_landing_block(block: LandingBlock) -> Dict[str, Any]:
    """
    Canonical serializer for admin CMS usage.
    Frontend depends on this shape EXACTLY.
    """
    return {
        "id": block.id,
        "block_type": block.block_type,
        "ordering": block.ordering,
        "is_active": block.is_active,

        "hot_category_block_id": block.hot_category_block_id,
        "comfort_rail_id": block.comfort_rail_id,
        "comfort_editorial_block_id": block.comfort_editorial_block_id,

        "created_at": block.created_at,
    }


def _apply_block_type_rules(
    *,
    block_type: str,
    hot_category_block_id: int | None,
    comfort_rail_id: int | None,
    comfort_editorial_block_id: int | None,
) -> Dict[str, Any]:
    """
    🔒 HARD CMS GUARD (DJANGO ADMIN PARITY)

    Guarantees:
    - EXACTLY ONE relation per block type
    - Impossible states are rejected
    """

    relations: Dict[str, Any] = {
        "hot_category_block": None,
        "comfort_rail": None,
        "comfort_editorial_block": None,
    }

    # ---------- HOT ----------
    if block_type == LandingBlock.BlockType.HOT:
        if not hot_category_block_id:
            raise ValueError(
                "hot_category_block_id is required when block_type is 'hot'."
            )

        relations["hot_category_block"] = get_object_or_404(
            HotCategoryBlock,
            pk=hot_category_block_id,
        )
        return relations

    # ---------- COMFORT RAIL ----------
    if block_type == LandingBlock.BlockType.COMFORT_RAIL:
        if not comfort_rail_id:
            raise ValueError(
                "comfort_rail_id is required when block_type is 'comfort_rail'."
            )

        relations["comfort_rail"] = get_object_or_404(
            ComfortCategoryRail,
            pk=comfort_rail_id,
        )
        return relations

    # ---------- COMFORT EDITORIAL ----------
    if block_type == LandingBlock.BlockType.COMFORT_BLOCK:
        if not comfort_editorial_block_id:
            raise ValueError(
                "comfort_editorial_block_id is required when block_type is 'comfort_block'."
            )

        relations["comfort_editorial_block"] = get_object_or_404(
            ComfortEditorialBlock,
            pk=comfort_editorial_block_id,
        )
        return relations

    # ---------- SIMPLE BLOCKS ----------
    if (
        hot_category_block_id
        or comfort_rail_id
        or comfort_editorial_block_id
    ):
        raise ValueError(
            "This block type must not reference hot, comfort rail, or comfort editorial."
        )

    return relations


# ==================================================
# LIST + CREATE
# ==================================================

class AdminLandingBlockListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        blocks = (
            LandingBlock.objects
            .select_related(
                "hot_category_block",
                "comfort_rail",
                "comfort_editorial_block",
            )
            .order_by("ordering", "id")
        )

        return Response(
            [_serialize_landing_block(b) for b in blocks],
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def post(self, request):
        payload = request.data

        try:
            block_type = payload.get("block_type")
            ordering = int(payload.get("ordering", 0))
            is_active = bool(payload.get("is_active", True))

            if not block_type:
                return Response(
                    {"detail": "block_type is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            valid_types = {c.value for c in LandingBlock.BlockType}
            if block_type not in valid_types:
                return Response(
                    {
                        "detail": (
                            f"Invalid block_type '{block_type}'. "
                            f"Valid types: {sorted(valid_types)}"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            relations = _apply_block_type_rules(
                block_type=block_type,
                hot_category_block_id=payload.get("hot_category_block_id"),
                comfort_rail_id=payload.get("comfort_rail_id"),
                comfort_editorial_block_id=payload.get(
                    "comfort_editorial_block_id"
                ),
            )

            block = LandingBlock.objects.create(
                block_type=block_type,
                ordering=ordering,
                is_active=is_active,
                **relations,
            )

            return Response(
                _serialize_landing_block(block),
                status=status.HTTP_201_CREATED,
            )

        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==================================================
# DETAIL — UPDATE / DELETE
# ==================================================

class AdminLandingBlockDetailView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request, pk: int):
        block = get_object_or_404(LandingBlock, pk=pk)
        payload = request.data

        try:
            if "ordering" in payload:
                block.ordering = int(payload["ordering"])

            if "is_active" in payload:
                block.is_active = bool(payload["is_active"])

            relations = _apply_block_type_rules(
                block_type=block.block_type,
                hot_category_block_id=payload.get(
                    "hot_category_block_id",
                    block.hot_category_block_id,
                ),
                comfort_rail_id=payload.get(
                    "comfort_rail_id",
                    block.comfort_rail_id,
                ),
                comfort_editorial_block_id=payload.get(
                    "comfort_editorial_block_id",
                    block.comfort_editorial_block_id,
                ),
            )

            block.hot_category_block = relations["hot_category_block"]
            block.comfort_rail = relations["comfort_rail"]
            block.comfort_editorial_block = relations[
                "comfort_editorial_block"
            ]

            block.save()

            return Response(
                _serialize_landing_block(block),
                status=status.HTTP_200_OK,
            )

        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @transaction.atomic
    def delete(self, request, pk: int):
        block = get_object_or_404(LandingBlock, pk=pk)
        block.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================================================
# 🔥 REORDER — DRAG & DROP (ATOMIC)
# ==================================================

class AdminLandingBlockReorderView(APIView):
    """
    POST:
    - Accepts list of {id, ordering}
    - Atomic reorder
    """

    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request):
        payload: List[Dict[str, Any]] = request.data

        if not isinstance(payload, list):
            return Response(
                {"detail": "Expected a list of {id, ordering} objects."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not payload:
            return Response(
                {"detail": "Reorder payload cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updates = {}

        for item in payload:
            try:
                block_id = int(item["id"])
                ordering = int(item["ordering"])
            except (KeyError, TypeError, ValueError):
                return Response(
                    {"detail": "Each item must contain id and ordering."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if block_id in updates:
                return Response(
                    {"detail": "Duplicate block id in reorder payload."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            updates[block_id] = ordering

        blocks = list(
            LandingBlock.objects
            .select_for_update()
            .filter(id__in=updates.keys())
        )

        if len(blocks) != len(updates):
            return Response(
                {"detail": "One or more landing blocks do not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for block in blocks:
            block.ordering = updates[block.id]

        LandingBlock.objects.bulk_update(blocks, ["ordering"])

        return Response(status=status.HTTP_204_NO_CONTENT)
