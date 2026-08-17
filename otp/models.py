import secrets
import pyotp
from django.db import models
from django.utils import timezone
from datetime import timedelta

class AuthorizedSystem(models.Model):
    name = models.CharField(max_length=50, unique=True)
    api_key = models.CharField(max_length=64, unique=True, db_index=True, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # 🔹 Añadir esta propiedad para ser compatible con IsAuthenticated de DRF
    @property
    def is_authenticated(self):
        return True

    class Meta:
        db_table = 'authorized_systems'

    def __str__(self):
        return self.name

class UserOTP(models.Model):
    class OTPStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        VERIFIED = 'VERIFIED', 'Verificado'
        EXPIRED = 'EXPIRED', 'Expirado'
        BLOCKED = 'BLOCKED', 'Bloqueado'

    MAX_FAILED_ATTEMPTS = 3  # Límite de intentos permitidos
    BLOCK_DURATION_MINUTES = 5  # Tiempo de bloqueo en minutos

    email = models.EmailField(db_index=True)
    system_name = models.CharField(max_length=50, default='default', db_index=True)
    secret_key = models.CharField(max_length=32, default=pyotp.random_base32)
    status = models.CharField(
        max_length=10, 
        choices=OTPStatus.choices, 
        default=OTPStatus.PENDING
    )
    failed_attempts = models.IntegerField(default=0)  # Conteo de intentos fallidos
    blocked_until = models.DateTimeField(null=True, blank=True)  # Expiración del bloqueo
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_otps'
        # Un usuario puede tener un OTP por cada sistema o se busca la combinación email + sistema
        indexes = [
            models.Index(fields=['email', 'system_name']),
        ]
    def is_currently_blocked(self) -> bool:
        """Verifica si el usuario se encuentra dentro de su ventana de bloqueo."""
        if self.status == self.OTPStatus.BLOCKED and self.blocked_until:
            if timezone.now() < self.blocked_until:
                return True
        return False

    def get_remaining_block_time_seconds(self) -> int:
        """Devuelve el tiempo restante de bloqueo en segundos."""
        if self.is_currently_blocked():
            delta = self.blocked_until - timezone.now()
            return max(0, int(delta.total_seconds()))
        return 0
    def __str__(self):
        return f"OTP [{self.system_name}] - {self.email} ({self.status})"

class OTPLog(models.Model):
    """
    Tabla de auditoría para guardar el historial de cada OTP generado.
    """
    email = models.EmailField(db_index=True)
    system_name = models.CharField(max_length=50, db_index=True)
    otp_code = models.CharField(max_length=10)
    status = models.CharField(max_length=30, default='GENERATED')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'otp_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"Log [{self.system_name}] - {self.email} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"