# store/services/landing_builder.py

from django.utils.timezone import now

from store.models import LandingBlock
from store.models.landing import FeaturedCategory, HotCategory
from store.models.landing_comfort import ComfortCategoryRail


def build_landing_blocks(request):
    """
    Central CMS builder for landing page.

    Reads LandingBlock ordering and returns
    structured data for frontend rendering.
    """

    blocks = (
        LandingBlock.objects
        .filter(is_active=True)
        .select_related("comfort_rail")
        .order_by("ordering", "id")
    )

    response = []

    for block in blocks:
        if block.block_type == LandingBlock.BlockType.HERO:
            response.append({
                "type": "hero",
            })

        elif block.block_type == LandingBlock.BlockType.FEATURED:
            response.append({
                "type": "featured-categories",
            })

        elif block.block_type == LandingBlock.BlockType.HOT:
            response.append({
                "type": "hot-categories",
            })

        elif block.block_type == LandingBlock.BlockType.COMFORT:
            if not block.comfort_rail:
                continue

            response.append({
                "type": "comfort",
                "comfort_rail_id": block.comfort_rail.id,
            })

    return {
        "meta": {
            "page": "landing",
            "generated_at": now().isoformat(),
        },
        "blocks": response,
    }
