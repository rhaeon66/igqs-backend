from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import TokenAuthentication


class LocalStaffAuthentication(TokenAuthentication):
    """Accept a staff token, or the first staff user when local login is disabled."""

    def authenticate(self, request):
        authenticated = super().authenticate(request)
        if authenticated is not None or not settings.ADMIN_LOGIN_DISABLED:
            return authenticated
        user = (
            get_user_model()
            .objects.filter(is_active=True, is_staff=True)
            .order_by("-is_superuser", "id")
            .first()
        )
        if user is None:
            return None
        return (user, None)
