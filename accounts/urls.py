from django.urls import path
from accounts import views

urlpatterns = [
    path('', views.registration, name='registration'),
    path('verify-otp/', views.verify_otp, name='verify-otp'),
    path('verify-otp/resend', views.resend_otp, name='resend-otp'),
    path('login/', views.connection, name='login'),
    path('logout/', views.deconnexion, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('mot-de-passe/oublie/', views.forgot_password, name='forgot-password'),
    path('mot-de-passe/verifier/', views.verify_reset_otp, name='verify-reset-otp'),
    path('mot-de-passe/nouveau/', views.reset_password, name='reset-password'),
]