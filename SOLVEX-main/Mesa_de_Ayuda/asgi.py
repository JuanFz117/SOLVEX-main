"""
ASGI config for Mesa_de_Ayuda project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack # type: ignore
from channels.routing import ProtocolTypeRouter, URLRouter # type: ignore
from channels.security.websocket import AllowedHostsOriginValidator # type: ignore
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Mesa_de_Ayuda.settings')

# Obtiene la aplicación ASGI de Django para manejar peticiones HTTP
# Esta llamada también ejecuta django.setup(), que configura los settings.
django_asgi_app = get_asgi_application()

# Ahora que Django está configurado (settings cargados),
# podemos importar de forma segura los módulos que dependen de ello,
# como nuestro routing de Channels que a su vez importa consumers y modelos.
from apps.tickets.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})