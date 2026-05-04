from pathlib import Path
import os
from dotenv import load_dotenv # type: ignore

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno desde el archivo .env
load_dotenv(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')

ALLOWED_HOSTS = ['192.168.15.215', 'localhost', '127.0.0.1', '0.0.0.0']
SITE_URL = 'http://localhost:8000'


MEDIA_URL = '/adjuntos/' # Creamos una carpeta predeterminada para guardar los adjuntos
MEDIA_ROOT = os.path.join(BASE_DIR, 'adjuntos')

# Application definition

INSTALLED_APPS = [
    'daphne',  # Añadimos Daphne para manejar ASGI
    'channels',  # Añadimos Channels para WebSockets
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # APLICACIONES PERSONALIZADAS
    'apps.tickets',  # Aplicación de tickets
    'apps.usuario',  # Aplicación de usuario
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

ROOT_URLCONF = 'Mesa_de_Ayuda.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
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

WSGI_APPLICATION = 'Mesa_de_Ayuda.wsgi.application'
ASGI_APPLICATION = 'Mesa_de_Ayuda.asgi.application'


# CONFIGURACIÓN DE CHANNELS
CHANNEL_LAYERS = {
    'default': {
        # Configuración para desarrollo (en memoria)
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
        
        # Para producción, usar Redis:
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# Para producción con Redis (instalar: pip install channels-redis)
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             "hosts": [('redis', 6379)],  # O la dirección de tu servidor Redis
#             "capacity": 1500,
#             "expiry": 60,
#         },
#     },
# }

# CONFIGURACION DOCKER
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': os.environ.get('DB_NAME'),
#         'USER': os.environ.get('DB_USER'),
#         'PASSWORD': os.environ.get('DB_PASSWORD'),
#         'HOST': os.environ.get('DB_HOST'),
#         'PORT': os.environ.get('DB_PORT'),
#     }
# }

# CONFIGURACIÓN LOCAL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'helpdesk',
        'USER': 'root',
        'PASSWORD': '',
        'HOST':'localhost',
        'PORT':'3307'
    }
}

AUTH_USER_MODEL = 'usuario.Usuario'  # MODELO A AUTORIZAR

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGIN_REDIRECT_URL = '/usuario/password_change_check/'  # Redirige al una funcion para evaluar los roles
LOGOUT_REDIRECT_URL = 'login'  # Redirige al login después del logout
LOGIN_URL = '/accounts/login/'  # Redirige al login si el usuario no está autenticado

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'websocket.log',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'apps.tickets.consumers': {
            'handlers': ['file', 'console'], # Asegúrate de que 'file' y 'console' estén definidos
            'level': 'DEBUG', # Cambiado a DEBUG para ver todos los mensajes de depuración
            'propagate': True,
        },
        'apps.usuario': {  # Logger para tu app de usuario
            'handlers': ['console', 'file'], # O solo 'console' si prefieres
            'level': 'DEBUG', # Cambiado a DEBUG para ver más detalle durante la prueba
            'propagate': True,
        },
        'django': { # Añadido para ver logs generales de Django
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

LANGUAGE_CODE = 'es-co'

TIME_ZONE = 'America/Bogota'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# ------- CONFIGURACIONES ADICIONALES AL SETTINGS ------

#IMPORTACIONES DE SENDGRID
import os
from sendgrid import SendGridAPIClient # type: ignore

# Configuración de SendGrid
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = 'aprendiz.ti@congente.coop'  # Tu email verificado en SendGrid
SENDGRID_REMINDER_TEMPLATE_ID = 'd-e5163493f1db4909b597291ef56b410d' # ID DE PLANTILLA DE RECORDATORIO


STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')    # Donde Django copiará todo al correr collectstatic


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
