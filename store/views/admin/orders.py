from django.shortcuts import get_object_or_404
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.exceptions import ValidationError
from rest_framework import status

# 🔐 JWT AUTH
from rest_framework_simplejwt.authentication import JWTAuthentication

from store.models import Order, OrderStatusAuditLog
from store.services.order_service import (
    confirm_order,
    ship_order,
    deliver_order,
    cancel_order,
)

# ==================================================
# CONSTANTS (SINGLE SOURCE OF TRUTH)
# ==================================================

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

VALID_ACTIONS = {
    "confirm",
    "ship",
    "deliver",
    "cancel",
}

VALID_ORDERING_FIELDS = {
    "created_at",
    "-created_at",
    "status",
    "-status",
    "total_price",
    "-total_price",
}


# ==================================================
# BASE ADMIN VIEW (JWT ENFORCED)
# ==================================================

class AdminJWTAPIView(APIView):
    """
    Base class for ALL admin order views.

    Enforces:
    - JWT Authentication
    - Admin-only access
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]


# ==================================================
# ADMIN ORDER LIST
# ==================================================

class AdminOrderListView(AdminJWTAPIView):
    """
    Admin-only list of orders.

    Supports:
    - status filtering
    - search (reference, customer name, phone)
    - ordering
    - pagination

    Read-only.
    """

    def get(self, request):
        qs = Order.objects.all()

        # -----------------------------
        # FILTER: STATUS
        # -----------------------------
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        # -----------------------------
        # SEARCH
        # -----------------------------
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(reference__icontains=search)
                | Q(name__icontains=search)
                | Q(phone__icontains=search)
            )

        # -----------------------------
        # ORDERING
        # -----------------------------
        ordering = request.query_params.get("ordering", "-created_at")
        if ordering not in VALID_ORDERING_FIELDS:
            raise ValidationError({
                "message": f"Invalid ordering field '{ordering}'."
            })

        qs = qs.order_by(ordering)

        # -----------------------------
        # PAGINATION
        # -----------------------------
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(
                request.query_params.get("page_size", DEFAULT_PAGE_SIZE)
            )
        except (TypeError, ValueError):
            raise ValidationError({
                "message": "Invalid pagination parameters."
            })

        page = max(page, 1)
        page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size

        orders = qs[start:end]

        return Response(
            {
                "meta": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "has_next": end < total,
                    "has_prev": start > 0,
                },
                "items": [
                    {
                        "id": order.id,
                        "reference": order.reference,
                        "customer_name": order.name,
                        "customer_phone": order.phone,
                        "status": order.status,
                        "total": str(order.total_price),
                        "created_at": order.created_at.isoformat(),
                    }
                    for order in orders
                ],
            },
            status=status.HTTP_200_OK,
        )


# ==================================================
# ADMIN ORDER DETAIL (READ-ONLY)
# ==================================================

class AdminOrderDetailView(AdminJWTAPIView):
    """
    Admin-only order detail view.
    Read-only.
    """

    def get(self, request, pk: int):
        order = get_object_or_404(
            Order.objects.prefetch_related("items"),
            pk=pk,
        )

        return Response(
            {
                "id": order.id,
                "reference": order.reference,
                "status": order.status,
                "total": str(order.total_price),
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat(),
                "customer": {
                    "name": order.name,
                    "phone": order.phone,
                    "address": order.address,
                },
                "items": [
                    {
                        "id": item.id,
                        "product_name": item.product_name,
                        "size": item.size,
                        "color": item.color,
                        "price": str(item.price),
                        "quantity": item.quantity,
                        "subtotal": str(item.price * item.quantity),
                    }
                    for item in order.items.all()
                ],
            },
            status=status.HTTP_200_OK,
        )


# ==================================================
# ADMIN ORDER STATUS UPDATE (STATE MACHINE SAFE)
# ==================================================

class AdminOrderStatusUpdateView(AdminJWTAPIView):
    """
    Admin-only order status transition endpoint.

    All transitions are enforced via service layer.
    """

    def post(self, request, pk: int):
        order = get_object_or_404(Order, pk=pk)

        action = request.data.get("action")
        if not action:
            raise ValidationError({
                "message": "Action is required."
            })

        if action not in VALID_ACTIONS:
            raise ValidationError({
                "message": f"Invalid action '{action}'."
            })

        actor_type = "admin"
        actor_identifier = f"admin:{request.user.pk}"

        # -----------------------------
        # ROUTE ACTION
        # -----------------------------
        if action == "confirm":
            success = confirm_order(
                order=order,
                actor_type=actor_type,
                actor_identifier=actor_identifier,
            )
            if not success:
                raise ValidationError({
                    "message": "Only pending orders can be confirmed."
                })

        elif action == "ship":
            success = ship_order(
                order=order,
                actor_type=actor_type,
                actor_identifier=actor_identifier,
            )
            if not success:
                raise ValidationError({
                    "message": "Only confirmed orders can be shipped."
                })

        elif action == "deliver":
            success = deliver_order(
                order=order,
                actor_type=actor_type,
                actor_identifier=actor_identifier,
            )
            if not success:
                raise ValidationError({
                    "message": "Only shipped orders can be delivered."
                })

        elif action == "cancel":
            success = cancel_order(
                order=order,
                actor_type=actor_type,
                actor_identifier=actor_identifier,
            )
            if not success:
                raise ValidationError({
                    "message": "This order cannot be cancelled."
                })

        order.refresh_from_db()

        return Response(
            {
                "id": order.id,
                "reference": order.reference,
                "status": order.status,
            },
            status=status.HTTP_200_OK,
        )


# ==================================================
# ADMIN ORDER AUDIT TIMELINE (READ-ONLY)
# ==================================================

class AdminOrderAuditView(AdminJWTAPIView):
    """
    Admin-only order status audit timeline.
    Immutable historical data.
    """

    def get(self, request, pk: int):
        order = get_object_or_404(Order, pk=pk)

        logs = (
            OrderStatusAuditLog.objects
            .filter(order=order)
            .order_by("created_at")
        )

        return Response(
            [
                {
                    "previous_status": log.previous_status,
                    "new_status": log.new_status,
                    "actor_type": log.actor_type,
                    "actor_identifier": log.actor_identifier,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ],
            status=status.HTTP_200_OK,
        )
