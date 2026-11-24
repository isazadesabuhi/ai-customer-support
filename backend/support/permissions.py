from accounts.permissions import HasSupportRole


class HasSupportPermissions(HasSupportRole):
    message = "Support permission is required for this operation."

    @staticmethod
    def has_required_permissions(request, view):
        method = "GET" if request.method in {"HEAD", "OPTIONS"} else request.method
        permissions = view.support_permissions.get(method)
        if permissions is None:
            # DRF handles unsupported methods as 405. Deny any new HTTP handler
            # until its permissions are explicitly mapped.
            return not hasattr(view, method.lower())
        return request.user.has_perms(permissions)

    def has_permission(self, request, view):
        return super().has_permission(request, view) and self.has_required_permissions(
            request, view
        )

    def has_object_permission(self, request, view, obj):
        return request.support_role is not None and self.has_required_permissions(
            request, view
        )
