import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

STATIC_URL = 'static/'

# ------------------------------------------------------------------------------
# Carga y Validación de SECRET_KEY
# ------------------------------------------------------------------------------
SECRET_KEY = os.getenv('SECRET_KEY')

# Determina el entorno actual (por defecto 'local')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'local').lower()

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# En entornos de QA o Producción, la SECRET_KEY debe existir sí o sí
if not SECRET_KEY:
    if ENVIRONMENT in ['qa', 'prod']:
        raise ImproperlyConfigured(
            f"ERROR CRÍTICO: La variable de entorno 'SECRET_KEY' no está configurada para el entorno {ENVIRONMENT.upper()}."
        )
    else:
        # Clave insegura solo para desarrollo local si se olvida declarar en .env.local
        SECRET_KEY = 'django-insecure-dev-only-key-do-not-use-in-production'

# Validación extra: evitar el uso de claves inseguras por defecto en producción o QA
if ENVIRONMENT in ['qa', 'prod'] and SECRET_KEY.startswith('django-insecure'):
    raise ImproperlyConfigured(
        "ERROR DE SEGURIDAD: Estás usando una clave con prefijo inseguro 'django-insecure' en un entorno de Producción/QA."
    )

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Terceros
    'rest_framework',
    # Apps del proyecto
    'otp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'otp_service.urls'
WSGI_APPLICATION = 'otp_service.wsgi.application'

# Zona horaria estándar (crucial para sincronización OTP)
TIME_ZONE = 'UTC'
USE_TZ = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        # Límites globales predeterminados
        'anon': '100/day',
        
        # Tasas personalizadas para OTP
        'otp_status': '10/minute',  # Máximo 10 consultas por minuto
        'otp_verify': '5/minute',   # Máximo 5 intentos de verificación por minuto (fuerza bruta)
        'otp_generate': '3/minute', # Máximo 3 solicitudes de código por minuto
    }
}

# Parámetros del Microservicio de Email
EMAIL_SERVICE_URL = os.getenv('EMAIL_SERVICE_URL')
EMAIL_SERVICE_API_KEY = os.getenv('EMAIL_SERVICE_API_KEY')