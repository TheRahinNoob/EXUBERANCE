from django.db import transaction
from .models import Order


@transaction.atomic
def cancel_order_and_restore_stock(order: Order):
    if not order.can_cancel():
        raise ValueError("Order cannot be cancelled")

    for item in order.items.select_related("variant"):
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save()

    order.status = Order.STATUS_CANCELLED
    order.save()
