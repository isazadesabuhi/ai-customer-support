from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListView,
    ConversationMessagesView,
)

app_name = "support"

# DRF validates UUID lookups after permission checks and returns JSON 404s.
urlpatterns = [
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path(
        "conversations/<str:pk>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
    path(
        "conversations/<str:pk>/messages/",
        ConversationMessagesView.as_view(),
        name="conversation-messages",
    ),
]
