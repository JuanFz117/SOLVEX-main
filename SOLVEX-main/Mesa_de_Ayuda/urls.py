from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
# from apps.tickets import views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns # Importar para servir estáticos
from apps.usuario import views
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path('admin/', admin.site.urls),  # Panel de administración de Django.
    path('', lambda request: redirect('login')),
    # Redirige la URL raíz a la página de inicio.
    path('post-login-redirect/', views.post_login_redirect, name='post_login_redirect'),  # Redirección después de iniciar sesión.
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),  # Inicio de sesión.
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),  # Cierre de sesión.
    
    #Incluir las URLs de la aplicación de tickets.
    path('tickets/', include('apps.tickets.urls')),  # URLs de la aplicación de tickets.
    # Incluir las URLs de la aplicación de usuario.
    path('usuario/', include('apps.usuario.urls')),  # URLs de la aplicación de usuario.

]

# Servir archivos estáticos y de medios en desarrollo
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns() # Añadir URLs para servir archivos estáticos
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) # Añadir URLs para servir archivos de medios