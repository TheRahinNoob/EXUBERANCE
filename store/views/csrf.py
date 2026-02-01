from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache


@require_GET
@never_cache
@ensure_csrf_cookie
def get_csrf_token(request):
    """
    CSRF bootstrap endpoint (CROSS-DOMAIN SAFE).

    Purpose:
    - Forces Django to SET the `csrftoken` cookie
    - Required for Next.js (Vercel) + Django SessionAuthentication

    IMPORTANT:
    - Does NOT return the token in JSON
    - Browser stores the cookie automatically
    - Frontend must read cookie and send it back as:
        X-CSRFToken: <csrftoken>
    """

    return JsonResponse(
        {"detail": "CSRF cookie set"},
        status=200,
    )
