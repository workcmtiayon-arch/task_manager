from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("", views.conversation_list, name="conversation_list"),
    path("start/<int:user_id>/", views.conversation_start, name="conversation_start"),
    path("<int:pk>/", views.conversation_detail, name="conversation_detail"),
    path("<int:pk>/messages/", views.conversation_messages_json, name='conversation_messages_json'),
    path("<int:pk>/attachments/", views.conversation_attachment_upload, name='conversation_attachment_upload'),
    path("<int:pk>/leave/", views.conversation_leave, name="conversation_leave"),
]