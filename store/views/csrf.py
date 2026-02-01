from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def get_csrf_token(request):
    """
    Sets the CSRF cookie for cross-domain session authentication.

    This endpoint is REQUIRED for:
    - Next.js admin panel (Vercel)
    - Django session-based auth
    - POST / PATCH / DELETE requests

    It does NOT return the token in JSON.
    It ONLY ensures the `csrftoken` cookie is set.
    """
    return JsonResponse(
        {"detail": "CSRF cookie set"},
        status=200
    )
