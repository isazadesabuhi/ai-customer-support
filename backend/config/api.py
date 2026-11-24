import logging

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    if isinstance(exc, Http404):
        exc = NotFound()
    response = exception_handler(exc, context)
    if response is not None:
        return response

    logger.error("Unhandled API error (%s).", type(exc).__name__)
    return Response(
        {"detail": "An unexpected server error occurred."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
