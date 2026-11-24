from rest_framework.permissions import IsAuthenticated


class IsSupportStaff(IsAuthenticated):
    """Interim authorization for this single-company application."""

    message = "Support staff access is required."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
