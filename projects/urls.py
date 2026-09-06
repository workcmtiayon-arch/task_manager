from django.urls import path
from projects import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('completed/', views.completed_project_list, name='completed_projects'),
    path('upcoming/', views.upcoming_project_list, name='upcoming_projects'),
    path('add/', views.add_project, name='project_add'),
    path('update/<int:id>/', views.update_project, name="project_update"),
    path('delete/<int:id>/', views.delete_project, name="project_delete"),
    path('show/<int:id>/', views.project_detail, name='project_detail'),
]
