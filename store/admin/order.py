from django.contrib import admin, messages
from django.db import transaction
from django.utils.html import format_html

from store.models import (
    Order,
    OrderItem,
    OrderStatusAuditLog,
)

from store.services.order_service import (
    confirm_order,
    ship_order,
    deliver_order,
    cancel_order,
)


# ==================================================
# ORDER ITEM INLINE (READ-ONLY SNAPSHOT)
# ==================================================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False

    fields = (
        "product_name",
        "size",
        "color",
        "price",
        "quantity",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


# ==================================================
# ORDER STATUS AUDIT INLINE (READ-ONLY, FIXED)
# ==================================================
class OrderStatusAuditInline(admin.TabularInline):
    model = OrderStatusAuditLog
    extra = 0
    can_delete = False
    show_change_link = False

    fields = (
        "previous_status",
        "new_status",
        "actor_type",
        "actor_identifier",
        "created_at",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


# ==================================================
# ORDER ADMIN
# ==================================================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # -----------------------------
    # LIST VIEW
    # -----------------------------
    list_display = (
        "reference",
        "name",
        "phone",
        "status_badge",
        "total_price",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "reference",
        "name",
        "phone",
    )

    ordering = ("-created_at",)

    # -----------------------------
    # DETAIL VIEW (READ-ONLY)
    # -----------------------------
    readonly_fields = (
        "reference",
        "name",
        "phone",
        "address",
        "status",
        "total_price",
        "created_at",
        "updated_at",
    )

    inlines = (
        OrderItemInline,
        OrderStatusAuditInline,
    )

    # -----------------------------
    # ADMIN ACTIONS
    # -----------------------------
    actions = (
        "action_confirm_orders",
        "action_ship_orders",
        "action_deliver_orders",
        "action_cancel_orders",
    )

    # -----------------------------
    # PERMISSIONS
    # -----------------------------
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # -----------------------------
    # STATUS BADGE (UX)
    # -----------------------------
    def status_badge(self, obj: Order):
        colors = {
            Order.STATUS_PENDING: "#f59e0b",     # amber
            Order.STATUS_CONFIRMED: "#3b82f6",   # blue
            Order.STATUS_SHIPPED: "#8b5cf6",     # purple
            Order.STATUS_DELIVERED: "#22c55e",   # green
            Order.STATUS_CANCELLED: "#ef4444",   # red
        }

        return format_html(
            (
                '<span style="'
                'background:{};'
                'color:white;'
                'padding:4px 10px;'
                'border-radius:999px;'
                'font-size:12px;'
                'font-weight:600;">{}</span>'
            ),
            colors.get(obj.status, "#6b7280"),
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    # ==================================================
    # ACTIONS
    # ==================================================
    @admin.action(description="✅ Confirm selected orders")
    def action_confirm_orders(self, request, queryset):
        self._run_action(
            request=request,
            queryset=queryset,
            fn=confirm_order,
            label="confirmed",
        )

    @admin.action(description="📦 Ship selected orders")
    def action_ship_orders(self, request, queryset):
        self._run_action(
            request=request,
            queryset=queryset,
            fn=ship_order,
            label="shipped",
        )

    @admin.action(description="🚚 Deliver selected orders")
    def action_deliver_orders(self, request, queryset):
        self._run_action(
            request=request,
            queryset=queryset,
            fn=deliver_order,
            label="delivered",
        )

    @admin.action(description="❌ Cancel selected orders")
    def action_cancel_orders(self, request, queryset):
        self._run_action(
            request=request,
            queryset=queryset,
            fn=cancel_order,
            label="cancelled",
        )

    # ==================================================
    # INTERNAL: SAFE ACTION RUNNER
    # ==================================================
    def _run_action(self, *, request, queryset, fn, label: str):
        """
        Runs a bulk order action safely.

        - Row-level locking
        - Atomic execution
        - Graceful skips
        - Clear admin feedback
        """

        success = 0
        skipped = 0

        with transaction.atomic():
            for order in queryset.select_for_update():
                try:
                    ok = fn(
                        order=order,
                        actor_type="admin",
                        actor_identifier=f"admin:{request.user.pk}",
                    )
                    if ok:
                        success += 1
                    else:
                        skipped += 1
                except Exception:
                    skipped += 1

        if success:
            self.message_user(
                request,
                f"{success} order(s) {label}.",
                level=messages.SUCCESS,
            )

        if skipped:
            self.message_user(
                request,
                f"{skipped} order(s) skipped (invalid state).",
                level=messages.WARNING,
            )
