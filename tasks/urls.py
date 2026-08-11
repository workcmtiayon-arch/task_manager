from django.urls import path
from tasks import views

urlpatterns = [
    path('', views.task_list, name='task_list'),
    path('projects/<int:project_id>/add/', views.add_task, name='add_task'),
    path('update/<int:id>/', views.update_task, name='update_task'),
    path('delete/<int:id>/', views.delete_task, name='delete_task'),
    path('show/<int:id>/', views.task_detail, name='show_details'),
    path('update-status/<int:id>/', views.task_update_status, name='task_update_status'),
]