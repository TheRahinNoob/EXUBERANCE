from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status

# 🔐 JWT AUTH
from rest_framework_simplejwt.authentication import JWTAuthentication

from store.models import Category, Product
from store.models.landing_comfort import ComfortCategoryRail


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
# HELPERS
# ==================================================

def build_absolute_image_url(request, image_field):
    if not image_field:
        return None
    try:
        return request.build_absolute_uri(image_field.url)
    except Exception:
        return None


def safe_delete_image(image_field):
    """
    Delete image file safely.
    NEVER let filesystem errors block DB operations.
    """
    if image_field and image_field.name:
        try:
            image_field.delete(save=False)
        except Exception:
            pass


# ==================================================
# COMFORT RAIL — LIST + CREATE
# ==================================================

class AdminComfortCategoryRailListCreateView(AdminJWTAPIView):

    def get(self, request):
        rails = (
            ComfortCategoryRail.objects
            .select_related("category")
            .prefetch_related("products")
            .order_by("ordering", "id")
        )

        return Response(
            [
                {
                    "id": rail.id,
                    "category": {
                        "id": rail.category.id,
                        "name": rail.category.name,
                        "slug": rail.category.slug,
                    },
                    "image": build_absolute_image_url(request, rail.image),
                    "auto_fill": rail.auto_fill,
                    "auto_limit": rail.auto_limit,
                    "is_active": rail.is_active,
                    "ordering": rail.ordering,
                    "products": [
                        {
                            "id": p.id,
                            "name": p.name,
                            "slug": p.slug,
                        }
                        for p in rail.products.all()
                    ],
                    "created_at": rail.created_at,
                }
                for rail in rails
            ],
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def post(self, request):
        """
        CREATE comfort rail

        multipart/form-data REQUIRED:
        - category_id
        - image
        """

        category_id = request.data.get("category_id")
        image = request.FILES.get("image")

        if not category_id:
            return Response(
                {"detail": "category_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not image:
            return Response(
                {"detail": "image is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category = get_object_or_404(Category, pk=category_id)

        max_ordering = (
            ComfortCategoryRail.objects
            .aggregate(max_val=Max("ordering"))
            .get("max_val")
        )
        next_order = 0 if max_ordering is None else max_ordering + 1

        rail = ComfortCategoryRail(
            category=category,
            image=image,
            ordering=next_order,
            is_active=True,
        )

        rail.full_clean()
        rail.save()

        return Response(
            {
                "id": rail.id,
                "image": build_absolute_image_url(request, rail.image),
                "ordering": rail.ordering,
            },
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# COMFORT RAIL — DETAIL / METADATA UPDATE / DELETE
# ==================================================

class AdminComfortCategoryRailDetailView(AdminJWTAPIView):

    def get(self, request, pk):
        rail = get_object_or_404(
            ComfortCategoryRail.objects
            .select_related("category")
            .prefetch_related("products"),
            pk=pk,
        )

        return Response(
            {
                "id": rail.id,
                "category": {
                    "id": rail.category.id,
                    "name": rail.category.name,
                    "slug": rail.category.slug,
                },
                "image": build_absolute_image_url(request, rail.image),
                "auto_fill": rail.auto_fill,
                "auto_limit": rail.auto_limit,
                "is_active": rail.is_active,
                "ordering": rail.ordering,
                "products": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "slug": p.slug,
                    }
                    for p in rail.products.all()
                ],
                "created_at": rail.created_at,
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def patch(self, request, pk):
        """
        PATCH — metadata ONLY
        Image mutation is forbidden here.
        """
        rail = get_object_or_404(ComfortCategoryRail, pk=pk)
        updated = False

        if "auto_fill" in request.data:
            rail.auto_fill = bool(request.data["auto_fill"])
            updated = True

        if "auto_limit" in request.data:
            try:
                limit = int(request.data["auto_limit"])
                if limit <= 0:
                    raise ValueError
                rail.auto_limit = limit
                updated = True
            except (TypeError, ValueError):
                return Response(
                    {"detail": "auto_limit must be a positive integer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if "is_active" in request.data:
            rail.is_active = bool(request.data["is_active"])
            updated = True

        if not updated:
            return Response(
                {"detail": "No valid fields provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rail.full_clean()
        rail.save()

        return Response(
            {"detail": "Updated successfully"},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def delete(self, request, pk):
        """
        DELETE — SAFE, NON-BLOCKING
        """
        rail = get_object_or_404(ComfortCategoryRail, pk=pk)

        safe_delete_image(rail.image)
        rail.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================================================
# COMFORT RAIL — IMAGE PATCH (DEDICATED)
# ==================================================

class AdminComfortCategoryRailImageUpdateView(AdminJWTAPIView):

    @transaction.atomic
    def patch(self, request, pk):
        """
        PATCH image ONLY

        multipart/form-data:
        - image (required)
        """

        rail = get_object_or_404(ComfortCategoryRail, pk=pk)
        image = request.FILES.get("image")

        if not image:
            return Response(
                {"detail": "image is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        safe_delete_image(rail.image)

        rail.image = image
        rail.full_clean()
        rail.save()

        return Response(
            {
                "id": rail.id,
                "image": build_absolute_image_url(request, rail.image),
            },
            status=status.HTTP_200_OK,
        )


# ==================================================
# COMFORT RAIL — PRODUCT ATTACH / DETACH
# ==================================================

class AdminComfortCategoryRailProductView(AdminJWTAPIView):

    @transaction.atomic
    def post(self, request, pk):
        rail = get_object_or_404(ComfortCategoryRail, pk=pk)

        product_id = request.data.get("product_id")
        if not product_id:
            return Response(
                {"detail": "product_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = get_object_or_404(Product, pk=product_id)

        if rail.products.filter(pk=product.id).exists():
            return Response(
                {"detail": "Product already added"},
                status=status.HTTP_409_CONFLICT,
            )

        rail.products.add(product)
        return Response(status=status.HTTP_201_CREATED)

    @transaction.atomic
    def delete(self, request, pk, product_id):
        rail = get_object_or_404(ComfortCategoryRail, pk=pk)
        product = get_object_or_404(Product, pk=product_id)

        rail.products.remove(product)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================================================
# COMFORT RAIL — REORDER
# ==================================================

class AdminComfortCategoryRailReorderView(AdminJWTAPIView):

    @transaction.atomic
    def post(self, request):
        items = request.data.get("items")

        if not isinstance(items, list):
            return Response(
                {"detail": "items must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rails = list(
            ComfortCategoryRail.objects.all().order_by("ordering", "id")
        )

        if len(items) != len(rails):
            return Response(
                {"detail": "Item count mismatch"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rail_map = {r.id: r for r in rails}
        seen = set()

        for index, payload in enumerate(items):
            rail_id = payload.get("id")

            if rail_id in seen:
                return Response(
                    {"detail": f"Duplicate id {rail_id}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            rail = rail_map.get(rail_id)
            if not rail:
                return Response(
                    {"detail": f"Invalid rail id {rail_id}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            seen.add(rail_id)
            rail.ordering = index
            rail.full_clean()
            rail.save(update_fields=["ordering"])

        return Response(
            {"detail": "Reordered successfully"},
            status=status.HTTP_200_OK,
        )
