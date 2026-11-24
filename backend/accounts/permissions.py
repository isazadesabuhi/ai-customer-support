from rest_framework.permissions import BasePermission

from .roles import support_role


class HasSupportRole(BasePermission):
    message = "An authorized support role is required."

    def has_permission(self, request, view):
        request.support_role = support_role(request.user)
        return request.support_role is not None
