from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError

from django.db import DatabaseError

from .models import Category, Product, Order
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    OrderCreateSerializer,
    OrderTrackingSerializer,
)


# ==================================================
# CATEGORY LIST (NAVBAR / MENU)
# ==================================================
class CategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.filter(parent__isnull=True)
    serializer_class = CategorySerializer


# ==================================================
# CATEGORY DETAIL
# ==================================================
class CategoryDetailAPIView(generics.RetrieveAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "slug"


# ==================================================
# PRODUCT LIST (GRID / CATEGORY / FEATURED)
# ==================================================
class ProductListAPIView(generics.ListAPIView):
    serializer_class = ProductListSerializer

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)

        category_slug = self.request.query_params.get("category")
        featured = self.request.query_params.get("featured")

        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)

        if featured == "1":
            queryset = queryset.filter(is_featured=True)

        return queryset.distinct()


# ==================================================
# PRODUCT DETAIL (PRODUCT PAGE)
# ==================================================
class ProductDetailAPIView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"


# ==================================================
# CREATE ORDER (CHECKOUT)
# ==================================================
class CreateOrderAPIView(APIView):
    """
    HTTP boundary for order creation.

    Guarantees:
    - JSON ONLY responses
    - Stock-safe atomic creation
    - Reference-first public response
    """

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)

        # -------------------------
        # INPUT VALIDATION
        # -------------------------
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            return Response(
                {"errors": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------
        # ORDER CREATION
        # -------------------------
        try:
            order = serializer.save()
        except ValidationError as e:
            # Stock errors / business rules
            return Response(
                {"errors": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DatabaseError:
            # DB failure — never expose internals
            return Response(
                {
                    "detail": (
                        "Unable to process your order right now. "
                        "Please try again later."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            # Absolute safety net
            return Response(
                {
                    "detail": (
                        "Unexpected error occurred while placing order."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # -------------------------
        # SUCCESS (CANONICAL RESPONSE)
        # -------------------------
        return Response(
            {
                "reference": order.reference,   # PUBLIC IDENTIFIER
                "status": order.status,
                "created_at": order.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# TRACK ORDER (PUBLIC, SAFE)
# ==================================================
class OrderTrackingAPIView(APIView):
    """
    Public order tracking.

    Rules:
    - reference is mandatory
    - phone is mandatory
    - order ID is NEVER exposed publicly
    """

    def get(self, request):
        reference = request.query_params.get("reference")
        phone = request.query_params.get("phone")

        if not reference or not phone:
            return Response(
                {
                    "detail": (
                        "Order reference and phone number are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = (
                Order.objects
                .prefetch_related("items")
                .get(reference=reference, phone=phone)
            )
        except Order.DoesNotExist:
            raise NotFound(
                "No order found with the provided reference and phone."
            )

        serializer = OrderTrackingSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)
