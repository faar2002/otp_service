#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def main():
    # 1. Definir la ruta base del proyecto (donde están los archivos .env)
    base_dir = Path(__file__).resolve().parent

    # 2. Determinar el entorno actual (por defecto: 'local')
    # Puedes cambiarlo ejecutando en la terminal: export ENVIRONMENT=qa o ENVIRONMENT=prod
    env_name = os.getenv('ENVIRONMENT', 'local').lower()

    # 3. Mapear entorno con su archivo .env y su módulo de settings
    env_files = {
        'local': '.env.local',
        'qa': '.env.qa',
        'prod': '.env.prod',
    }

    env_file_name = env_files.get(env_name, '.env.local')
    env_path = base_dir / env_file_name

    # 4. Cargar el archivo .env correspondiente si existe
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        print(f"⚠️  Advertencia: No se encontró el archivo {env_file_name}, se usarán las variables del sistema.")

    # 5. Establecer dinámicamente el DJANGO_SETTINGS_MODULE según el entorno
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'otp.settings.{env_name}')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
