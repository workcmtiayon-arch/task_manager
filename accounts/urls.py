from django.urls import path
from accounts import views

urlpatterns = [
    path('', views.registration, name='registration'),
    path('login/', views.connection, name='login'),
    path('logout/', views.deconnection, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard')
]