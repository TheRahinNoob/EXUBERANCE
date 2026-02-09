import time
import hashlib
import logging
from typing import Optional

import requests
from django.conf import settings

from store.models import Order

logger = logging.getLogger(__name__)


# ==================================================
# INTERNAL HELPERS
# ==================================================
def _sha256(value: Optional[str]) -> Optional[str]:
    """
    Hashes a value using SHA-256 as required by Meta.
    Returns None if value is empty.
    """
    if not value:
        return None

    value = value.strip().lower()
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _get_meta_endpoint() -> str:
    """
    Returns the Meta Conversions API endpoint URL.
    """
    return f"https://graph.facebook.com/v18.0/{settings.META_PIXEL_ID}/events"


# ==================================================
# MAIN ENTRY POINT
# ==================================================
def send_meta_purchase_event(order: Order) -> None:
    """
    Sends a Purchase event to Meta Conversions API.

    CRITICAL GUARANTEES:
    - Called ONLY after order is CONFIRMED
    - Uses order.reference as event_id (dedup safe)
    - Never raises exceptions upstream
    """

    # -----------------------------
    # SAFETY CHECKS
    # -----------------------------
    if order.status != Order.STATUS_CONFIRMED:
        logger.warning(
            "Meta Purchase skipped: order %s not confirmed",
            order.reference,
        )
        return

    if not getattr(settings, "META_PIXEL_ID", None):
        logger.error("META_PIXEL_ID not configured")
        return

    if not getattr(settings, "META_ACCESS_TOKEN", None):
        logger.error("META_ACCESS_TOKEN not configured")
        return

    # -----------------------------
    # BUILD USER DATA
    # -----------------------------
    user_data = {
        "fn": _sha256(getattr(order, "name", "").split(" ")[0] if order.name else None),
        "ln": _sha256(" ".join(getattr(order, "name", "").split(" ")[1:]) if order.name else None),
        "ph": _sha256(order.phone),
    }

    # Remove empty values
    user_data = {k: v for k, v in user_data.items() if v}

    # -----------------------------
    # BUILD CONTENTS
    # -----------------------------
    contents = []
    total_quantity = 0

    for item in order.items.all():
        contents.append({
            "id": str(item.variant.id),
            "quantity": item.quantity,
            "item_price": float(item.price),
        })
        total_quantity += item.quantity

    # -----------------------------
    # BUILD EVENT PAYLOAD
    # -----------------------------
    payload = {
        "data": [
            {
                "event_name": "Purchase",
                "event_time": int(time.time()),
                "event_id": order.reference,  # 🔑 Dedup key
                "action_source": "website",
                "user_data": user_data,
                "custom_data": {
                    "currency": "BDT",
                    "value": float(order.total_price),
                    "contents": contents,
                    "num_items": total_quantity,
                },
            }
        ],
        "access_token": settings.META_ACCESS_TOKEN,
    }

    # -----------------------------
    # SEND TO META (FAIL-SAFE)
    # -----------------------------
    try:
        response = requests.post(
            _get_meta_endpoint(),
            json=payload,
            timeout=5,
        )

        if response.status_code >= 400:
            logger.error(
                "Meta CAPI error (%s) for order %s: %s",
                response.status_code,
                order.reference,
                response.text,
            )
        else:
            logger.info("Meta Purchase sent for order %s", order.reference)

    except requests.RequestException:
        logger.exception("Meta CAPI request failed for order %s", order.reference)
