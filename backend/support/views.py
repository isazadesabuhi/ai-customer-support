from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.decorators.cache import never_cache
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from accounts.roles import (
    ADD_CONVERSATION,
    ADD_MESSAGE,
    VIEW_CONVERSATION,
    VIEW_MESSAGE,
)
from config.api import api_exception_handler

from .models import Conversation
from .pagination import SupportPagination
from .permissions import HasSupportPermissions
from .serializers import (
    ConversationCreateSerializer,
    ConversationQuerySerializer,
    ConversationSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)


@method_decorator(never_cache, name="dispatch")
class SupportAPIView(generics.GenericAPIView):
    permission_classes = (HasSupportPermissions,)
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)

    def get_exception_handler(self):
        return api_exception_handler


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
    support_permissions = {"GET": (VIEW_CONVERSATION,), "POST": (ADD_CONVERSATION,)}
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
    support_permissions = {"GET": (VIEW_CONVERSATION,)}
    queryset = Conversation.objects.select_related("customer")
    serializer_class = ConversationSerializer


class ConversationMessagesView(SupportListCreateView):
    support_permissions = {
        "GET": (VIEW_CONVERSATION, VIEW_MESSAGE),
        "POST": (VIEW_CONVERSATION, ADD_MESSAGE),
    }
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
