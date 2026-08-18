from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from .models import AuthorizedSystem, UserOTP, OTPLog


@staff_member_required
def dashboard_index_view(request):
    """
    Vista principal del Dashboard con paginación independiente para UserOTP y OTPLog.
    """
    systems = AuthorizedSystem.objects.all().order_by('-created_at')

    # 1. Paginación para UserOTP (10 por página)
    user_otps_queryset = UserOTP.objects.all().order_by('-updated_at')
    otps_paginator = Paginator(user_otps_queryset, 10)
    otps_page_number = request.GET.get('otps_page', 1)
    user_otps_page = otps_paginator.get_page(otps_page_number)

    # 2. Paginación para OTPLog (10 por página)
    logs_queryset = OTPLog.objects.all().order_by('-created_at')
    logs_paginator = Paginator(logs_queryset, 10)
    logs_page_number = request.GET.get('logs_page', 1)
    logs_page = logs_paginator.get_page(logs_page_number)

    # Métricas generales
    metrics = {
        'total_systems': systems.count(),
        'total_otps': UserOTP.objects.count(),
        'active_otps': UserOTP.objects.filter(status='PENDING').count(),
        'blocked_otps': UserOTP.objects.filter(status='BLOCKED').count(),
    }

    context = {
        'metrics': metrics,
        'systems': systems,
        'user_otps': user_otps_page,  # Objeto Page de UserOTP
        'logs': logs_page,            # Objeto Page de OTPLog
    }
    return render(request, 'dashboard/index.html', context)

@staff_member_required
@require_POST
def unblock_email_view(request, otp_id):
    """
    Desbloquea manualmente un correo cambiando su estado de BLOCKED a PENDING.
    """
    try:
        user_otp = UserOTP.objects.get(id=otp_id)
        email = user_otp.email

        # Restablecer todos los registros bloqueados del correo
        UserOTP.objects.filter(email=email, status=UserOTP.OTPStatus.BLOCKED).update(
            status=UserOTP.OTPStatus.PENDING,
            failed_attempts=0,
            blocked_until=None
        )

        # Registrar el evento en el historial de auditoría
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()

        OTPLog.objects.create(
            email=email,
            system_name=user_otp.system_name,
            otp_code='MANUAL',
            status='MANUAL_UNBLOCKED',
            ip_address=client_ip
        )

        messages.success(request, f"El correo {email} ha sido desbloqueado correctamente.")
    except UserOTP.DoesNotExist:
        messages.error(request, "No se encontró el registro indicado.")

    return redirect('web-dashboard')

def custom_login_view(request):
    """
    Vista personalizada para el inicio de sesión de administradores.
    """
    if request.user.is_authenticated:
        return redirect('web-dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"¡Bienvenido de nuevo, {user.username}!")
            # Redirigir a la URL que intentaba acceder o al Dashboard
            next_url = request.GET.get('next', 'web-dashboard')
            return redirect(next_url)
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()

    return render(request, 'dashboard/login.html', {'form': form})


def custom_logout_view(request):
    """
    Vista para cerrar sesión y redirigir al login personalizado.
    """
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('web-login')