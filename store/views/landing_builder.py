from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from store.services.landing_builder import build_landing_blocks

class LandingPageAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        blocks = build_landing_blocks()

        return Response({
            "page": "landing",
            "blocks": blocks
        })
