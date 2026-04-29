# apps/tickets/urls.py
from django.urls import path
from . import views # Importa las vistas de la app actual (tickets)

# Define un namespace para evitar colisiones de nombres de URL con otras apps
app_name = 'tickets'

urlpatterns = [
    # Cuando la URL sea /tickets/inicio/, usará la vista views.index
    path('inicio/', views.index, name='index'),
    # Cuando la URL sea /tickets/resueltos/, usará la vista views.tickets_page
    path('resueltos/', views.tickets_page, name='tickets_resueltos'),
    # Cuando la URL sea /tickets/detalle/ticket-<id>/, usará la vista views.ticket_detalle
    path('detalle/ticket-<int:id>/', views.ticket_detalle, name='ticket_detalle'),
    path('admin/ticket-<int:ticket_id>/', views.admin_ticket_detail, name='admin_ticket_detail'),
    # Puedes añadir más URLs específicas de la app tickets aquí
]
