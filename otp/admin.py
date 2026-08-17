from django.contrib import admin
from .models import AuthorizedSystem, UserOTP, OTPLog

@admin.register(OTPLog)
class OTPLogAdmin(admin.ModelAdmin):
    list_display = ('email', 'system_name', 'otp_code', 'status', 'ip_address', 'created_at')
    list_filter = ('system_name', 'status', 'created_at')
    search_fields = ('email', 'otp_code', 'ip_address')
    readonly_fields = ('email', 'system_name', 'otp_code', 'status', 'ip_address', 'created_at')

    def has_add_permission(self, request):
        return False  # Los logs solo se leen, no se agregan manualmente
    
@admin.register(AuthorizedSystem)
class AuthorizedSystemAdmin(admin.ModelAdmin):
    list_display = ('name', 'api_key', 'is_active', 'created_at')
    search_fields = ('name', 'api_key')
    readonly_fields = ('api_key',)


@admin.register(UserOTP)
class UserOTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'system_name', 'status', 'created_at')
    list_filter = ('status', 'system_name')
    search_fields = ('email', 'system_name')