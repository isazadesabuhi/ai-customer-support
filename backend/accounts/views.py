from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.csrf import csrf_failure as django_csrf_failure
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api import api_exception_handler

from .permissions import HasSupportRole
from .roles import SUPPORT_PERMISSIONS, support_role
from .serializers import LoginSerializer
from .throttling import LoginAttemptThrottle


@never_cache
def csrf_failure(request, reason=""):
    if request.path_info.startswith("/api/"):
        return JsonResponse({"detail": "CSRF verification failed."}, status=403)
    return django_csrf_failure(request, reason=reason)


@method_decorator(never_cache, name="dispatch")
class AccountAPIView(APIView):
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)

    def get_exception_handler(self):
        return api_exception_handler


class CSRFView(AccountAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response({"csrfToken": get_token(request._request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(AccountAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (LoginAttemptThrottle,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        django_request = request._request
        user = authenticate(django_request, **serializer.validated_data)
        role = support_role(user) if user is not None else None
        if role is None:
            return Response(
                {"detail": "Invalid credentials or insufficient account access."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        login(django_request, user)
        return Response(
            {
                "id": user.pk,
                "username": user.get_username(),
                "role": role,
                "is_authenticated": True,
            }
        )


class LogoutView(AccountAPIView):
    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(AccountAPIView):
    permission_classes = (HasSupportRole,)

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.pk,
                "username": user.get_username(),
                "role": request.support_role,
                "permissions": [
                    permission
                    for permission in SUPPORT_PERMISSIONS
                    if user.has_perm(permission)
                ],
            }
        )
