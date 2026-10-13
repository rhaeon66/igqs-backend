from django.conf import settings
from django.contrib.auth import get_user_model, login


class LocalAdminLoginMiddleware:
    """Sign in the first staff user for /admin/ when local login is disabled."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            settings.ADMIN_LOGIN_DISABLED
            and request.path.startswith("/admin")
            and not request.user.is_authenticated
        ):
            user = (
                get_user_model()
                .objects.filter(is_active=True, is_staff=True)
                .order_by("-is_superuser", "id")
                .first()
            )
            if user is not None:
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return self.get_response(request)
