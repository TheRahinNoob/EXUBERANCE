# store/services/landing_menu_service.py

from django.utils.timezone import now
from django.db.models import Q

from store.models.landing import LandingMenuItem


def get_landing_menu_items():
    current_time = now()

    return (
        LandingMenuItem.objects
        .select_related("category")
        .filter(
            is_active=True,
            category__is_active=True,
        )
        .filter(
            Q(category__is_campaign=False) |
            Q(
                category__is_campaign=True,
                category__starts_at__lte=current_time,
                category__ends_at__gte=current_time,
            )
        )
        .order_by("ordering", "id")
    )
