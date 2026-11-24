import logging

from django.http import Http404
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.decorators.cache import never_cache
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .models import Conversation
from .pagination import SupportPagination
from .permissions import IsSupportStaff
from .serializers import (
    ConversationCreateSerializer,
    ConversationQuerySerializer,
    ConversationSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)

logger = logging.getLogger(__name__)


def support_exception_handler(exc, context):
    if isinstance(exc, Http404):
        exc = NotFound()
    response = exception_handler(exc, context)
    if response is not None:
        return response

    logger.error("Unhandled support API error (%s).", type(exc).__name__)
    return Response(
        {"detail": "An unexpected server error occurred."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@method_decorator(never_cache, name="dispatch")
class SupportAPIView(generics.GenericAPIView):
    permission_classes = (IsSupportStaff,)
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)

    def get_exception_handler(self):
        return support_exception_handler


class SupportListCreateView(SupportAPIView, generics.ListCreateAPIView):
    pagination_class = SupportPagination

    def create(self, request, *args, **kwargs):
        context = self.get_serializer_context()
        serializer = self.create_serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            self.get_serializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )


class ConversationListView(SupportListCreateView):
    queryset = Conversation.objects.select_related("customer")
    serializer_class = ConversationSerializer
    create_serializer_class = ConversationCreateSerializer

    def get_queryset(self):
        params = self.request.query_params
        if len(params.getlist("status")) > 1:
            raise ValidationError({"status": ["Provide one status."]})
        query = ConversationQuerySerializer(data=params.dict())
        query.is_valid(raise_exception=True)
        return super().get_queryset().filter(**query.validated_data)


class ConversationDetailView(SupportAPIView, generics.RetrieveAPIView):
    queryset = Conversation.objects.select_related("customer")
    serializer_class = ConversationSerializer


class ConversationMessagesView(SupportListCreateView):
    serializer_class = MessageSerializer
    create_serializer_class = MessageCreateSerializer

    @cached_property
    def conversation(self):
        parent = generics.get_object_or_404(Conversation, pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, parent)
        return parent

    def get_queryset(self):
        return self.conversation.messages.all()

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "conversation": self.conversation}
