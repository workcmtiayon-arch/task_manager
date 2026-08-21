from django.urls import path
from accounts import views

urlpatterns = [
    path('', views.registration, name='registration'),
    path('verify-otp/', views.verify_otp, name='verify-otp'),
    path('verify-otp/resend', views.resend_otp, name='resend-otp'),
    path('login/', views.connection, name='login'),
    path('logout/', views.deconnexion, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profil/', views.profile, name='profile'),
    path('utilisateurs/', views.user_list, name='user_list'),
    path('utilisateurs/<int:user_id>/statut/', views.toggle_user_status, name='toggle_user_status'),
    path('configuration/', views.system_settings, name='system_settings'),
    path('mot-de-passe/oublie/', views.forgot_password, name='forgot-password'),
    path('mot-de-passe/verifier/', views.verify_reset_otp, name='verify-reset-otp'),
    path('mot-de-passe/nouveau/', views.reset_password, name='reset-password'),
]
