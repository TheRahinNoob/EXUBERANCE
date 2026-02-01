from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET


@require_GET
@ensure_csrf_cookie
def get_csrf_token(request):
    """
    CSRF bootstrap endpoint.

    Purpose:
    - Sets the `csrftoken` cookie for cross-domain usage
    - Required for Next.js (Vercel) + Django session auth

    Notes:
    - DOES NOT return the token itself
    - DOES NOT mutate session
    - Cookie is read automatically by the browser
    - Frontend must send it back via `X-CSRFToken` header
    """
    return JsonResponse(
        {"detail": "CSRF cookie set"},
        status=200
    )
