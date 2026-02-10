from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError

from django.db import DatabaseError
import traceback
import logging

from store.models import Order
from store.serializers import (
    OrderCreateSerializer,
    OrderTrackingSerializer,
)
from store.services.order_service import confirm_order

logger = logging.getLogger(__name__)

# ==================================================
# CREATE ORDER (CHECKOUT)
# ==================================================
class CreateOrderAPIView(APIView):
    """
    HTTP boundary for order creation.

    Responsibilities:
    - Validate input via serializer
    - Persist order atomically
    - Confirm order
    - Return safe, user-facing response
    """

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            order = serializer.save()

            # ✅ Confirm order (business logic hook)
            confirm_order(
                order=order,
                actor_type="system",
                actor_identifier="checkout",
            )

        except ValidationError as e:
            return Response(
                {"errors": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except DatabaseError:
            logger.error(
                "Database error while creating order",
                exc_info=True,
            )
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
            logger.critical(
                "Unhandled exception during order creation",
                exc_info=True,
            )
            traceback.print_exc()
            return Response(
                {
                    "detail": (
                        "Unexpected error occurred while placing order."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # -----------------------------
        # SUCCESS
        # -----------------------------
        return Response(
            {
                "reference": order.reference,
                "status": order.status,
                "total_price": float(order.total_price),
                "created_at": order.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# TRACK ORDER (PUBLIC — PHONE VERIFIED)
# ==================================================
class OrderTrackingAPIView(APIView):
    """
    Public order tracking endpoint.
    Requires reference + phone number.
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
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# ==================================================
# PUBLIC ORDER LOOKUP (ANALYTICS / META PIXEL)
# ==================================================
class PublicOrderByReferenceAPIView(APIView):
    """
    Public read-only order lookup.

    Purpose:
    - Analytics
    - Meta Pixel Purchase event
    - No PII
    - No authentication
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, reference):
        try:
            order = Order.objects.get(reference=reference)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "reference": order.reference,
                "total": float(order.total_price),
                "currency": "BDT",
            },
            status=status.HTTP_200_OK,
        )
