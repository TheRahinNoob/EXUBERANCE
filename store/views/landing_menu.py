# store/api/views/landing_menu.py

from rest_framework.response import Response
from rest_framework.views import APIView

from store.services.landing_menu_service import get_landing_menu_items


class LandingMenuAPIView(APIView):
    def get(self, request):
        items = get_landing_menu_items()

        data = [
            {
                "name": item.category.name,
                "slug": item.category.slug,
                "seo_title": item.effective_seo_title,
                "seo_description": item.effective_seo_description,
            }
            for item in items
        ]

        return Response(data)
