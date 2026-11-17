from rest_framework.permissions import BasePermission

from admissions.authentication import LocalStaffAuthentication


class IsStaffUser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)


class StaffAuthMixin:
    authentication_classes = [LocalStaffAuthentication]
    permission_classes = [IsStaffUser]
