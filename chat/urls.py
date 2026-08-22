from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("", views.conversation_list, name="conversation_list"),
    path("start/<int:user_id>/", views.conversation_start, name="conversation_start"),
    path("users/search/", views.user_search, name="user_search"),
    path("invitations", views.invitations_list, name='invitations_list'),
    path("<int:pk>/", views.conversation_detail, name="conversation_detail"),
    path("<int:pk>/messages/", views.conversation_messages_json, name='conversation_messages_json'),
    path("<int:pk>/messages/send/", views.conversation_message_send, name='conversation_message_send'),
    path("<int:pk>/attachments/", views.conversation_attachment_upload, name='conversation_attachment_upload'),
    path("<int:pk>/leave/", views.conversation_leave, name="conversation_leave"),
]
