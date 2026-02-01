from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache


@require_GET
@never_cache
def get_csrf_token(request):
    """
    CSRF bootstrap endpoint (PRODUCTION SAFE).

    WHAT THIS DOES:
    - Forces Django to generate a CSRF token
    - Sets the `csrftoken` cookie (HttpOnly=False)
    - RETURNS the token in JSON (🔥 critical 🔥)

    WHY THIS WORKS:
    - Cookies alone are unreliable cross-site
    - Returning token in JSON is the ONLY
      stable solution for Vercel → Render

    FRONTEND MUST:
    - Call GET /api/csrf/
    - Store token in memory
    - Send it as X-CSRFToken on mutations
    """

    csrf_token = get_token(request)

    return JsonResponse(
        {
            "csrfToken": csrf_token
        },
        status=200
    )
