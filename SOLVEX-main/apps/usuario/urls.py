# apps/usuario/urls.py (ya existente)
from django.urls import path
from .views import (CambiarContrasenaView, password_change_check, admin_dashboard, tomar_ticket, reasignar_ticket, cerrar_ticket, tickets_page_admin, superadmin_dashboard, reporte_superadmin)


# Puedes definir un namespace aquí también si quieres (opcional pero recomendado)
app_name = 'usuario'

urlpatterns = [
    path('admin_dashboard/', admin_dashboard, name='admin_dashboard'),
    path('superadmin_dashboard/', superadmin_dashboard, name='superadmin_dashboard'),
    path('reporte_superadmin/', reporte_superadmin, name='reporte_superadmin'),
    path('cambiar_contrasena/', CambiarContrasenaView.as_view(), name='cambiar_contrasena'),
    path('password_change_check/', password_change_check, name='password_change_check'),
    path('ticket/<int:ticket_id>/tomar/', tomar_ticket, name='tomar_ticket'),
    path('ticket/<int:ticket_id>/reasignar/', reasignar_ticket, name='reasignar_ticket'),
    path('ticket/<int:ticket_id>/cerrar/', cerrar_ticket, name='cerrar_ticket'),
    path('resueltos_admin/', tickets_page_admin, name='tickets_resueltos'),
]
