from django.urls import path
from .views import GenerateOTPView, VerifyOTPView, OTPStatusView, HealthCheckView

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='otp-health-v1'),
    path('generate/', GenerateOTPView.as_view(), name='otp-generate-v1'),
    path('verify/', VerifyOTPView.as_view(), name='otp-verify-v1'),
    path('status/', OTPStatusView.as_view(), name='otp-status-v1'),
]
