#  Microservicio de Autenticación OTP (Django REST Framework)

Un microservicio de autenticación de código de un solo uso (**OTP**) seguro, escalable y listo para producción, construido con **Python 3.14**, **Django 5** y **PostgreSQL**.

Este servicio expone una API REST versionada (`/api/v1/`) protegida mediante tokens por sistema (`X-System-Token`), desacoplando la generación y verificación de códigos TOTP y comunicándose con un microservicio externo de envío de correos.

---

##  Características Principales

* **Seguridad Criptográfica:** Generación de secretos dinámicos utilizando algoritmos TOTP (`pyotp`) de 5 minutos de validez.
* **Autenticación por Sistema Autorizado:** Acceso restringido mediante encabezado de seguridad `X-System-Token` por aplicación consumidora.
* **Protección contra Fuerza Bruta & DoS:**
  * **Throttling:** Limitación nativa de peticiones por minuto (`3/min` en generación, `5/min` en verificación, `10/min` en status).
  * **Bloqueo Temporal:** Sanción automática de **5 minutos** al acumular 3 intentos fallidos consecutivos por correo electrónico.
  * **Expiración en Cascada:** Al bloquearse un correo, todos los códigos en estado `PENDING` pasan automáticamente a `EXPIRED`.
* **Auditoría de Seguridad Completa (`OTPLog`):** Registro histórico detallado por cada evento (generación, éxitos, fallos, bloqueos e IP del cliente).
* **High Availability & Healthcheck:** Endpoint `/api/v1/health/` para monitorear en tiempo real la conectividad con PostgreSQL.

---

##  Estructura del Proyecto
otp_service/
├── otp_service/
│   ├── settings/
│   │   ├── base.py            # Configuración compartida (DRF, Apps, Throttling)
│   │   ├── local.py           # Entorno de Desarrollo Local
│   │   ├── qa.py              # Entorno de Staging / QA
│   │   └── prod.py            # Entorno de Producción
│   ├── asgi.py                
│   ├── urls.py                # Rutas globales del proyecto
│   └── wsgi.py
│
├── otp/
│   ├── api/
│   │   └── v1/
│   │       ├── authentication.py # Autenticación por X-System-Token
│   │       ├── throttling.py     # Clases de tasa límite por IP
│   │       ├── urls.py           # Rutas versionadas v1
│   │       ├── permissions.py 
│   │       └── views.py          # Controladores REST (Generate, Verify, Status, Health)
│   │
│   ├── templates/             #  PLANTILLAS WEB (HTML)
│   │   └── dashboard/
│   │       ├── index.html     # Panel con tablas y auto-refresco JS
│   │       └── login.html     # Pantalla de Login (Tailwind CSS)
│   │
│   ├── models.py              # Modelos: AuthorizedSystem, UserOTP, OTPLog
│   ├── services.py            # Cliente HTTP para el Email Microservice
│   ├── apps.py 
│   ├── tests.py
│   └── admin.py               # Panel de administración e inspección
│
├── .env.example               # Plantilla de variables de entorno
├── .env.local                 # Plantilla de variables de entorno local
├── .env.prod                  # Plantilla de variables de entorno produccion
├── .env.qa                    # Plantilla de variables de entorno QA
├── OTP Service API (v1).postman_collection.json
├── manage.py
└── requirements.txt

Requisitos Previos
.- Python: 3.10+ (probado en Python 3.14)

.- PostgreSQL: 14+

.- Virtualenv / pip

Instalación y Configuración
1. Clonar el repositorio y crear el entorno virtual
git clone [https://github.com/faar2002/otp-service.git](https://github.com/faar2002/otp-service.git)
cd otp-service

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual (Windows)
venv\Scripts\activate

# Activar entorno virtual (Linux/Mac)
source venv/bin/activate

2. Instalar dependencias
pip install -r requirements.txt

3. Configurar variables de entorno
Copia el archivo .env.example a .env.local:
ENVIRONMENT=local
SECRET_KEY=tu_secret_key_super_segura
DEBUG=True

# Base de datos PostgreSQL
DB_NAME=otp_dev_db
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432

# Integración con el Email Microservice
EMAIL_SERVICE_URL=[https://api.email-service.com/v1/send](https://api.email-service.com/v1/send)
EMAIL_SERVICE_API_KEY=tu_api_key_microservicio_email

4. Aplicar Migraciones

python manage.py makemigrations --settings=otp_service.settings.local
python manage.py migrate --settings=otp_service.settings.local
5. Crear Superusuario (Opcional, para el Admin)

python manage.py createsuperuser --settings=otp_service.settings.local
6. Iniciar Servidor de Desarrollo

python manage.py runserver --settings=otp_service.settings.local

# Intefaz WEB

Interfaz Web / Dashboard Admin
Accede desde el navegador web a:

1.- Login: http://127.0.0.1:8000/login/

2.- Dashboard: http://127.0.0.1:8000/dashboard/

El Dashboard permite:

Visualización en Vivo: Tarjetas con el total de sistemas autorizados, OTPs pendientes y correos actualmente bloqueados.

Auto-Sincronización: Mantiene las tablas actualizadas en tiempo real en segundo plano sin interrumpir la navegación.

Gestión de Bloqueos: Botón de acción 🔓 Desbloquear para restablecer el acceso a un correo bloqueado sin esperar la ventana de 5 minutos.

🔑 Autenticación de Sistemas Consumidores
Cada sistema que requiera consumir el servicio de OTP debe estar registrado en la tabla authorized_systems (vía Django Admin o comando) y enviar su token en el header HTTP:

HTTP
X-System-Token: sys_4f8a9e2b1c3d5e7f9a0b1c2d3e4f5a6b7c8d9e0f
🌐 Endpoints de la API (v1)
1. Monitoreo del Servicio
GET /api/v1/health/

Autenticación: Ninguna (Público)

Respuesta (200 OK):

JSON
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "up",
      "engine": "PostgreSQL"
    }
  }
}
2. Generar Código OTP
POST /api/v1/otp/generate/

Headers: X-System-Token: <TOKEN>

Body (JSON):

JSON
{
  "email": "usuario@ejemplo.com"
}
Respuesta (200 OK):

JSON
{
  "message": "Código OTP generado y enviado con éxito.",
  "system_name": "mobile_app",
  "status": "PENDING"
}
3. Verificar Código OTP
POST /api/v1/otp/verify/

Headers: X-System-Token: <TOKEN>

Body (JSON):

JSON
{
  "email": "usuario@ejemplo.com",
  "otp": "123456"
}
Respuesta Éxito (200 OK):

JSON
{
  "message": "Código OTP verificado correctamente.",
  "status": "VERIFIED"
}
Respuesta Bloqueado por 3 intentos fallidos (403 Forbidden):

JSON
{
  "error": "Ha superado los 3 intentos fallidos. Su correo ha sido bloqueado por 5 minutos.",
  "status": "BLOCKED",
  "retry_after_seconds": 300
}
4. Consultar Estado del OTP
GET /api/v1/otp/status/?email=usuario@ejemplo.com

Headers: X-System-Token: <TOKEN>

Respuesta (200 OK):

JSON
{
  "email": "usuario@ejemplo.com",
  "system_name": "mobile_app",
  "status": "BLOCKED",
  "failed_attempts": 3,
  "created_at": "2026-08-17T17:15:00Z",
  "updated_at": "2026-08-17T17:20:00Z",
  "retry_after_seconds": 240
}
🔒 Respuestas de Error Comunes
Código HTTP	Causa	Ejemplo de Causa
400 Bad Request	Parámetros faltantes o código OTP incorrecto.	{"error": "Código inválido. Le quedan 2 intento(s)."}
401 Unauthorized	Falta la cabecera X-System-Token o el token es inactivo.	{"detail": "Token de sistema inválido o inactivo."}
403 Forbidden	Correo temporalmente bloqueado por superar los 3 intentos.	{"error": "El correo está bloqueado por 4 minuto(s) más."}
429 Too Many Requests	Exceso de límite de peticiones por minuto (Throttling).	{"detail": "Request was throttled. Expected available in 42 seconds."}
503 Service Unavailable	Falla de conexión con la base de datos PostgreSQL en /health/.	{"status": "unhealthy", "components": {...}}
📄 Licencia
Este proyecto se distribuye bajo la licencia MIT.


<ElicitationsGroup message="¿Deseas agregar alguna sección adicional al README o preparar los archivos finales?">

  <Elicitation label="Crear plantilla .env.example" query="Muestra el contenido exacto que debe tener el archivo .env.example para incluirlo en el repositorio."/>

  <Elicitation label="Crear archivo .gitignore para Python y Django" query="Muestra el contenido recomendado para el archivo .gitignore de un proyecto Django en VS Code."/>

</ElicitationsGroup>
