from django.utils.timezone import now

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from store.models.landing_comfort_editorial import ComfortEditorialBlock


# ==================================================
# 🧠 LANDING — COMFORT EDITORIAL (ATOMIC CONTENT API)
# ==================================================
class LandingComfortEditorialAPIView(APIView):
    """
    Atomic Comfort Editorial Block endpoint.

    RESPONSIBILITY:
    - Serve editorial CONTENT only
    - CMS controls placement via LandingBlock
    - Frontend consumes render-ready data

    HARD GUARANTEES:
    - Absolute image URLs
    - SSR-safe
    - No CMS logic
    - No ordering side effects
    - Never throws (homepage-safe)
    """

    permission_classes = [AllowAny]

    def get(self, request):
        blocks = (
            ComfortEditorialBlock.objects
            .filter(is_active=True)
            .only(
                "id",
                "title",
                "subtitle",
                "image",
                "cta_text",
                "cta_url",
                "ordering",
            )
            .order_by("ordering", "id")
        )

        items = []

        for block in blocks:
            # Defensive serialization (NO assumptions)
            items.append({
                "id": block.id,
                "title": block.title,
                "subtitle": block.subtitle or None,
                "image": (
                    request.build_absolute_uri(block.image.url)
                    if getattr(block, "image", None)
                    else None
                ),
                "cta_text": block.cta_text or None,
                "cta_url": block.cta_url or None,
            })

        return Response({
            "meta": {
                "page": "landing",
                "section": "comfort_editorial",
                "generated_at": now().isoformat(),
                "total": len(items),
            },
            "items": items,
        })
