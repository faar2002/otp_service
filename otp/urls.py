from django.urls import path
from .views import dashboard_index_view, unblock_email_view, custom_login_view, custom_logout_view

urlpatterns = [
    path('login/', custom_login_view, name='web-login'),
    path('logout/', custom_logout_view, name='web-logout'),
    path('dashboard/', dashboard_index_view, name='web-dashboard'),
    path('dashboard/unblock/<int:otp_id>/', unblock_email_view, name='web-unblock-email'),
]