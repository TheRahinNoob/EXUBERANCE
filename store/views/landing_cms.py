from django.utils.timezone import now

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from store.models import LandingBlock
from store.services.landing_blocks import build_block_payload


class LandingCMSAPIView(APIView):
    """
    🧠 LANDING CMS ORCHESTRATOR (ORDER ONLY)

    RESPONSIBILITY:
    - Return CMS-defined block ORDER
    - Return ONLY lightweight payloads (type + IDs)
    - NEVER fetch heavy data
    - NEVER embed content

    SINGLE SOURCE OF TRUTH:
    - store.services.landing_blocks.build_block_payload
    """

    permission_classes = [AllowAny]

    def get(self, request):
        blocks = (
            LandingBlock.objects
            .filter(is_active=True)
            .select_related(
                "hot_category_block",
                "comfort_editorial_block",
                "comfort_rail",
            )
            .order_by("ordering", "id")
        )

        items = []

        for block in blocks:
            # Resolver enforces ALL CMS rules
            payload = build_block_payload(block)

            # Misconfigured blocks are silently skipped
            if payload:
                items.append(payload)

        return Response({
            "meta": {
                "page": "landing",
                "section": "cms",
                "generated_at": now().isoformat(),
                "total_blocks": len(items),
            },
            "items": items,
        })
