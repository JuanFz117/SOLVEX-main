from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import PasswordChangeView
from django.http import HttpResponseNotAllowed, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import ExpressionWrapper, F, DurationField, Avg, Count
from django.db.models import Q
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy  # REVERSE PARA EL MENSAJE DE POPUP

# --------------------- IMPORTACIONES PARA CHANNELS -------------------- 
import asyncio
from channels.layers import get_channel_layer # type: ignore
from asgiref.sync import async_to_sync
import logging

# -------------------------- IMPORTACIONES ADICIONALES ---------------------------------
from weasyprint import HTML
from django.conf import settings
from apps.tickets.models import Tickets, Ticket_estado, Ticket_comentarios, Ticket_prioridad
import io
import base64
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from collections import defaultdict
import numpy as np
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .forms import CambiarContraseñaForm # Importar el formulario personalizado
from apps.usuario.models import Usuario


logger = logging.getLogger(__name__)


def es_admin_o_superadmin(user):
    # Asegúrate que los roles coincidan con los definidos en tu modelo Usuario
    return user.is_authenticated and user.es_admin_tipo

def es_superadmin(user):
    # Asegúrate que los roles coincidan con los definidos en tu modelo Usuario
    return user.is_authenticated and user.es_superadmin_tipo

def _get_safe_username(user):
    """Devuelve de forma segura el nombre de usuario o un texto alternativo."""
    if user and hasattr(user, 'username') and user.username:
        return str(user.username)
    return "Usuario Desconocido"

def _get_safe_user_nombre(user):
    """Devuelve de forma segura el 'nombre' del usuario o un texto alternativo."""
    if user and hasattr(user, 'nombre') and user.nombre:
        return str(user.nombre)
    return _get_safe_username(user) # Usa el username como fallback


# ------------ FUNCIONES AUXILIARES PARA MENSAJES DE SISTEMA Y ESTADO ----------------
def _save_system_comment_sync(ticket_id, message_text):
    """ Guardar un comentario de sistema de forma síncronica. """
    try:
        ticket = Tickets.objects.get(id=ticket_id)
        comentario_obj = Ticket_comentarios.objects.create(
            id_ticket=ticket,
            autor=None,
            detalle_comentario=message_text
        )
        logger.info(f"Comentario de sistema guardado para ticket {ticket_id}: {message_text}")
        return comentario_obj
    except Tickets.DoesNotExist:
        logger.error(f"Ticket {ticket_id} no encontrado al guardar comentario de sistema.")
    except Exception as e:
        logger.error(f"Error en _save_system_comment_sync para ticket {ticket_id}: {e}", exc_info=True)
    return None

def _send_channel_message(ticket_id, payload_type, data_dict):
    """ Envía un mensaje al grupo del ticket a través del Channels. """
    channel_layer = get_channel_layer()
    group_name = f"ticket_{ticket_id}"
    message_payload = {
        'type': payload_type,
    }
    message_payload.update(data_dict)

    async_to_sync(channel_layer.group_send)(group_name, message_payload)
    logger.info(f"Mensaje tipo '{payload_type}' enviado al grupo {group_name} para ticket {ticket_id}.")

def _send_admin_dashboard_update(target_group_suffix, event_type, data_dict):
    """
    ENVIA UNA ACTUALIZACION AL GRUPO DEL DASHBOARD DE ADMINISTRADORES
    """
    channel_layer = get_channel_layer()
    group_name = f"admin_dashboard_{target_group_suffix}"

    message_payload = {
        'type': event_type,
        'ticket_data': data_dict
    }

    async_to_sync(channel_layer.group_send)(group_name, message_payload)
    ticket_id_log = data_dict.get('id', 'N/A') if isinstance(data_dict, dict) else 'N/A'
    logger.info(f"Mensaje tipo '{event_type}' enviado al grupo {group_name} con datos de ticket {ticket_id_log}.")

def _notify_system_comment(ticket_id, message_text):
    """ Guarda y notifica un comentario de sistema. """
    comentario_obj = _save_system_comment_sync(ticket_id, message_text)
# -- VISTAS -- #

@login_required
@user_passes_test(es_admin_o_superadmin, login_url='login')
def admin_dashboard(request):
    """
    Vista para el panel de administración.
    """

    admin_categoria = request.user.categoria  # Obtiene la categoría del usuario administrador
    
    admin_user_obj = request.user # PARA OBTENER EL USUARIO
    admin_categoria = admin_user_obj.categoria # OBTIENE LA CATEGORIA ADECUADA

    print(f"Admin categoria obtenida: {admin_categoria}")
    print(f"Es superadmin: {es_superadmin(request.user)}")

    try:
        # Filtra tickets abiertos y en progreso por categoría del administrador
        tickets_abiertos_en_progreso = Tickets.objects.filter(
            Q(id_estado="abierto") | Q(id_estado="en_progreso"),
            tipo_soporte=admin_categoria
        ).order_by('-fecha_creacion') # Aseguramos un orden para la paginación
        print("Tickets abiertos: ", tickets_abiertos_en_progreso)  # Para depuración
    except Ticket_estado.DoesNotExist:
        tickets_abiertos_en_progreso = Tickets.objects.none()

    paginator = Paginator(tickets_abiertos_en_progreso, 12) # Paginación: 10 tickets por página
    page_obj = paginator.get_page(request.GET.get('page')) # Obtiene el objeto de página actual

    headers = ['ID', 'Motivo', 'Usuario', 'Tipo de Soporte', 'Estado', 'Prioridad', 'Fecha de Creación']  # Filtra tickets abiertos

    conteos = obtener_tickets_abiertos(request)  # Obtiene conteos de tickets abiertos, en proceso y cerrados
    print("Conteos de tickets: ", conteos)  # Para depuración
    context = {
        'admin_user': request.user,  # Usuario autenticado
        # 'tickets_categoria': admin_categoria,  # Ya no es necesario pasar el queryset completo
        'lista_tickets_abiertos': tickets_abiertos_en_progreso,  # Lista de tickets abiertos
        'dashboard_headers': headers,  # Encabezados de la tabla
        'tickets_abiertos_count': conteos['abiertos'],
        'tickets_en_progreso_count': conteos['en_progreso'],
        'tickets_cerrado_count': conteos['cerrado'],
        'es_superadmin': es_superadmin(request.user), # Add superadmin status to context
    }
    context['page_obj'] = page_obj # Pasa el objeto de página paginado al contexto
    # Aquí puedes agregar lógica para el panel de administración
    return render(request, 'admin/admin.html', context)

@login_required
def post_login_redirect(request):
    """
    Redirige al usuario según su rol después de iniciar sesión.
    """
    user = request.user
    if user.es_superadmin_tipo:
        # Redirige al panel de administración
        return redirect('usuario:superadmin_dashboard')
    elif user.es_admin_tipo:
        # Redirige al panel de administración
        return redirect('usuario:admin_dashboard')
    elif user.rol == Usuario.ROLE_COLABORADOR:
        # Redirige a la vista de tickets usando el namespace
        return redirect('tickets:index')
    else:
        # Rol desconocido, redirige al login como fallback seguro
        messages.warning(request, "Rol de usuario no reconocido.") # Opcional: mensaje al usuario
        return redirect('login')
        

@login_required
def password_change_check(request):
    """
    Vista para verificar el cambio de contraseña del usuario.
    """
    usuario_actual = request.user  # Obtiene el usuario autenticado
    print(f"Verificando cambio de contraseña para: {usuario_actual.username}, "
          f"debe_cambiar_contrasena: {usuario_actual.debe_cambiar_contrasena}")
    
    if usuario_actual and usuario_actual.debe_cambiar_contrasena:
        return redirect('usuario:cambiar_contrasena')
    else:
        return post_login_redirect(request)
    

class CambiarContrasenaView(LoginRequiredMixin, PasswordChangeView):
    """
    Vista para cambiar la contraseña del usuario autenticado.
    """
    template_name = 'usuario/cambiar_contrasena.html'  # Plantilla a usar
    form_class = CambiarContraseñaForm                 # Especificar el formulario personalizado
    success_url = reverse_lazy('login')                # URL a la que se redirigiría si no anulamos

    def form_valid(self, form):
        """
        Marca 'debe_cambiar_contrasena' como False y cierra sesión después de un cambio exitoso.
        """
        # El usuario cuya contraseña se está cambiando está en form.user
        user_to_update = form.user

        # Llama al método padre para guardar la contraseña
        # Esto también actualiza el hash de la sesión para mantener al usuario logueado (temporalmente).
        super().form_valid(form)

        # Actualiza el flag en el usuario actual
        if hasattr(user_to_update, 'debe_cambiar_contrasena'):
            user_to_update.debe_cambiar_contrasena = False
            user_to_update.save(update_fields=['debe_cambiar_contrasena'])

        # Mensaje de éxito
        success_url =  reverse('login') + f'?success_message=Contraseña cambiada con éxito. Por favor, inicie sesión nuevamente.'

        # Redirige a la página de login
        return redirect(success_url)

@login_required
@user_passes_test(es_admin_o_superadmin, login_url='login')
def tomar_ticket(request, ticket_id):
    """
    Vista para tomar un caso.
    """
    ticket = get_object_or_404(Tickets, id=ticket_id)  # Obtiene el ticket por ID
    if ticket.id_estado != "abierto":
        messages.warning(request, "El ticket ya no se encuentra abierto.")
        return redirect('tickets:admin_ticket_detail', ticket_id=ticket_id)

    if request.method == 'POST':

        ticket.id_estado = 'en_progreso'  # Cambia el estado a "en progreso"
        ticket.fecha_asignacion = timezone.now()
        ticket.asignado_a = request.user  # Asigna el ticket al usuario actual
        ticket.save()

        # NOTIFICAR COMENTARIO DE SISTEMA Y ACTUALIZACION DE ESTADO 
        safe_username = _get_safe_username(request.user)
        message = f"Ticket tomado por {safe_username}."
        _notify_system_comment(ticket_id, message)

        # PREPARAMOS EL PAYLOAD PARA EL WEBSOCKET
        system_message_data = {
            'author': 'Sistema',
            'message': message,
            'timestamp': timezone.now().isoformat(),
            'is_system': True,
        }

        _send_channel_message(ticket_id, 'ticket_status_update', {
            'ticket_id': ticket_id, 'new_status_value': ticket.id_estado,
            'new_status_display': str(ticket.get_id_estado_display()), # Convertido a string para seguridad
            'asignado_a_username': _get_safe_username(ticket.asignado_a),
            'system_message': system_message_data,
        })

        base_url = reverse('tickets:admin_ticket_detail', kwargs={'ticket_id': ticket_id})
        success_url = f"{base_url}?success_message=Ticket tomado exitosamente."
        return redirect(success_url)

    else:
        # Si no es POST, no permitir (o redirigir a dashboard)
        # return redirect('usuario:admin_dashboard')
        return HttpResponseNotAllowed(['POST'])
    
@login_required
@user_passes_test(es_admin_o_superadmin, login_url='login')
def reasignar_ticket(request, ticket_id):
    """
    Vista para reasignar un caso.
    """
    ticket = get_object_or_404(Tickets, id=ticket_id)  # Obtiene el ticket por ID
    if ticket.id_estado == 'cerrado':
        messages.warning(request, "No se puede reasignar un ticket que ya se encuentra cerrado.")
        return redirect('tickets:admin_ticket_detail', ticket_id=ticket_id)

    if request.method == 'POST':
        print("Reasignando ticket...")  # Para depuración
        # AQUI VAMOS A REASIGNAR EL TICKET A UN NUEVO TIPO DE SOPORTE
        nuevo_tipo_soporte = request.POST.get('tipo_soporte')
        comentario_reasignacion = request.POST.get('comentario')
        print("Nuevo tipo de soporte: ", nuevo_tipo_soporte)  # Para depuración

        if not nuevo_tipo_soporte:
            messages.error(request, "Por favor, selecciona un nuevo tipo de soporte.")
            return redirect('tickets:admin_ticket_detail', ticket_id=ticket_id)

        tipo_anterior = ticket.tipo_soporte  # Guardamos el tipo de soporte anterior para el historial
        # VAMOS A ACTUALIZAR EL TIPO DE SOPORTE DEL TICKET
        ticket.tipo_soporte = nuevo_tipo_soporte
        ticket.asignado_a = None # Limpiamos el campo de asignado_a para que no esté asignado a nadie
        ticket.id_estado = 'abierto'  # Cambia el estado a "abierto"
        ticket.fecha_asignacion = None  # Limpiamos la fecha de asignación
        ticket.save()

        
        safe_user_nombre = _get_safe_user_nombre(request.user)
        # ENVIAR MENSAJE AL SISTEMA DE CHAT
        detalle_historial_reasignacion = f"Ticket reasignado de '{tipo_anterior}' a '{nuevo_tipo_soporte}' por {safe_user_nombre}"
        if comentario_reasignacion: # Si se proporcionó un comentario, lo añadimos al historial
            detalle_historial_reasignacion += f". Motivo: {comentario_reasignacion}"

        _notify_system_comment(ticket_id, detalle_historial_reasignacion)

        system_message_data = {
            'author': 'Sistema',
            'message': detalle_historial_reasignacion,
            'timestamp': timezone.now().isoformat(),
            'is_system': True,
        }

        _send_channel_message(ticket_id, 'ticket_status_update', {
            'ticket_id': ticket_id, 'new_status_value': ticket.id_estado,           
            'new_status_display': str(ticket.get_id_estado_display()),
            'asignado_a_username': None, # Reasignarlo lo deja sin administrador
            'system_message': system_message_data,
        })

        # base_url = reverse('tickets:admin_ticket_detail', kwargs={'ticket_id': ticket_id})
        success_url = reverse('usuario:admin_dashboard') + f"?success_message=Ticket reasignado exitosamente."
        return redirect(success_url)
    else:
        # Si no es POST, no permitir
        return HttpResponseNotAllowed(['POST'])

@login_required
@user_passes_test(es_admin_o_superadmin, login_url='login')
def cerrar_ticket(request, ticket_id):
    """
    Vista para cerrar un caso.
    """
    ticket = get_object_or_404(Tickets, id=ticket_id)  # Obtiene el ticket por ID
    if ticket.id_estado == 'cerrado':
        messages.warning(request, "El ticket ya se encuentra cerrado.")
        return redirect('tickets:admin_ticket_detail', ticket_id=ticket_id)
    
    if ticket.id_estado == 'abierto':
        messages.warning(request, "No se puede cerrar un ticket sin haberlo tomado anteriormente o en su defecto brindar una respuesta.")
        print("Estado del ticket: ", ticket.id_estado)  # Para depuración
        return redirect('tickets:admin_ticket_detail', ticket_id=ticket_id)
        
    if request.method == 'POST':
        motivo_cierre = request.POST.get('motivo_cierre')
        comentario_adicional_cierre = request.POST.get('comentario-cierre') # Capturamos el comentario adicional
        
        if not motivo_cierre:
            messages.error(request, "Debe seleccionar un motivo de cierre.")
            return redirect('tickets:admin_ticket_detail', ticket_id=ticket_id)
        
        # CAMBIAMOS EL ESTADO DEL CASO A CERRADO
        ticket.id_estado = 'cerrado'  # Cambia el estado a "cerrado"
        ticket.motivo_cierre = motivo_cierre
        ticket.fecha_cierre = timezone.now()
        ticket.save()

        safe_user_nombre = _get_safe_user_nombre(request.user)
        # VAMOS A GUARDAR ESTA ACCION EN COMENTARIOS PARA QUE QUEDE UN HISTORIAL
        # ENVIAR MENSAJE AL SISTEMA DE CHAT
        detalle_historial = f"Ticket cerrado por {safe_user_nombre}. Motivo: {ticket.get_motivo_cierre_display()}"
        if comentario_adicional_cierre: # Si se proporcionó un comentario, lo añadimos al historial
            detalle_historial += f". Comentario de cierre: {comentario_adicional_cierre}"

        _notify_system_comment(ticket_id, detalle_historial)

        system_message_data = {
            'author': 'Sistema',
            'message': detalle_historial,
            'timestamp': timezone.now().isoformat(),
            'is_system': True
        }

        _send_channel_message(ticket_id, 'ticket_status_update', {
            'ticket_id': ticket_id, 'new_status_value': ticket.id_estado,            
            'new_status_display': str(ticket.get_id_estado_display()),
            'asignado_a_username': _get_safe_username(ticket.asignado_a),
            'system_message': system_message_data,
            })

        success_url = reverse('tickets:admin_ticket_detail', kwargs={'ticket_id': ticket_id}) + f"?success_message=Ticket cerrado exitosamente."

        return redirect(success_url)
    
    else:
        # Si no es POST, no permitir
        return HttpResponseNotAllowed(['POST'])
    

def obtener_tickets_abiertos(request):
    """
    Vista para obtener la cantidad tickets abiertos.
    """

    categoria_admin = request.user.categoria  # Obtiene la categoría del usuario administrador
    abiertos_count = Tickets.objects.filter(id_estado="abierto", tipo_soporte=categoria_admin).count()  # Filtra tickets abiertos por categoría del administrador
    en_progreso_count = Tickets.objects.filter(id_estado="en_progreso", tipo_soporte=categoria_admin).count()  # Filtra tickets en progreso por categoría del administrador
    cerrado_count = Tickets.objects.filter(id_estado="cerrado", tipo_soporte=categoria_admin).count() # Filtra tickets cerrados por categoría del administrador

    return {
        'abiertos': abiertos_count,
        'en_progreso': en_progreso_count,
        'cerrado': cerrado_count
    }

# FUNCION DE VISTA DE TICKETS RESUELTOS ( HISTORIAL )
@login_required  # Solo usuarios autenticados pueden acceder a esta vista.
@user_passes_test(es_admin_o_superadmin, login_url='login')
def tickets_page_admin(request):
    """
    Vista para la página de tickets resueltos.
    """
    # Obtenemos el usuario que se encuentra registrado
    usuario_actual = request.user
    # Traemos todos los tickets del usuario solo los cerrados
    tickets_cerrados = Tickets.objects.filter(id_estado="cerrado", tipo_soporte=usuario_actual.categoria)  # Filtra tickets cerrados por categoría del administrador
    print(tickets_cerrados)

    tickets_generales2 = [
        'ID',
        'Motivo',
        'Usuario',
        'Tipo de Soporte',
        'Estado',
        'Fecha de Creación',
        'Fecha de Solución'
    ]

    paginator2 = Paginator(tickets_cerrados, 10) # Creamos la paginación con 12 campos maximo de la sección tickets abiertos
    pagina2 = request.GET.get("page") or 1 # Se le asigna la página actual o el 1
    posts2 = paginator2.get_page(pagina2) # Se guarda la página en posts
    current_page2 = int(pagina2) # Obtiene la página actual
    paginas2 = range(1, posts2.paginator.num_pages + 1)
    
    
    return render(request, 'admin/tickets_admin.html', {
        'posts2': posts2,
        'paginas2': paginas2,
        'current_page2': current_page2,
        'colaborador': usuario_actual, # Pasamos el nuevo objeto porque actualizamos el modelo
        'tickets_generales2': tickets_generales2
    })

def superadmin_dashboard(request):
    """
    Vista para el panel de administración del superadmin.
    """
    tickets_abiertos = Tickets.objects.filter(id_estado="abierto")  # Filtra tickets abiertos
    tickets_en_progreso = Tickets.objects.filter(id_estado="en_progreso")  # Filtra tickets en progreso
    tickets_cerrados = Tickets.objects.filter(id_estado="cerrado")  # Filtra tickets cerrados

    todos_los_tickets = Tickets.objects.all().order_by('-fecha_creacion')  # Trae todos los tickets
    paginator = Paginator(todos_los_tickets, 10)  # Crea la paginación con 10 tickets por página
    page_number = request.GET.get("page") or 1  # Obtiene la página actual o asigna la primera
    page_obj = paginator.get_page(page_number)  # Obtiene la página actual

    abiertos_count = tickets_abiertos.count()  # Cuenta tickets abiertos
    en_progreso_count = tickets_en_progreso.count()  # Cuenta tickets en progreso
    cerrado_count = tickets_cerrados.count()  # Cuenta tickets cerrados

    headers = ['ID', 'Motivo', 'Usuario', 'Tipo de Soporte', 'Estado', 'Prioridad', 'Fecha de Creación', 'Asignado A']  # Encabezados de la tabla

    context = {
        'superadmin_user': request.user,  # Usuario autenticado
        'page_obj': page_obj,  # Página actual de tickets
        'dashboard_headers': headers,  # Encabezados de la tabla
        'tickets_abiertos_count': abiertos_count,  # Conteo de tickets abiertos
        'tickets_en_progreso_count': en_progreso_count,  # Conteo de tickets en progreso
        'tickets_cerrado_count': cerrado_count,  # Conteo de tickets cerrados
    }

    # Aquí puedes agregar lógica para el panel de administración del superadmin
    return render(request, 'superadmin/superadmin_dashboard.html', context)  # Renderiza la plantilla del dashboard del superadmin

# -------- DEFINICION DE COLORES POR ESTADOS PARA LA GRAFICA ------- #

def generar_grafico_mensual(tickets_filtrados, titulo="Dashboard de Tickets por Estado"):
    """
    Genera un dashboard completo que muestra la distribución de tickets por estado
    (abierto, en progreso, cerrado) con múltiples visualizaciones.
    
    Args:
        tickets_filtrados: QuerySet de tickets filtrados
        titulo: Título personalizado del dashboard
        
    Returns:
        String: Imagen del dashboard en formato base64
    """
    
    # Definir colores estándar para estados
    COLORES_ESTADO = {
        'abierto': '#dc3545',      # Rojo
        'en_progreso': '#ffc107',  # Amarillo/Naranja
        'cerrado': '#28a745',      # Verde
        'default': '#6c757d'       # Gris para otros/desconocidos
    }
    
    NOMBRES_ESTADO = {
        'abierto': 'Abierto',
        'en_progreso': 'En Progreso',
        'cerrado': 'Cerrado',
    }
    
    # Validar que haya datos
    if not tickets_filtrados.exists():
        print("No hay tickets para generar el dashboard.")
        return None
    
    # Obtener conteo por estado
    conteo_estados = {
        'abierto': tickets_filtrados.filter(id_estado='abierto').count(),
        'en_progreso': tickets_filtrados.filter(id_estado='en_progreso').count(),
        'cerrado': tickets_filtrados.filter(id_estado='cerrado').count()
    }
    
    # Filtrar estados con conteo cero
    conteo_estados = {k: v for k, v in conteo_estados.items() if v > 0}
    
    if not conteo_estados:
        print("No hay datos de estados para graficar.")
        return None
    
    # Crear layout para el dashboard
    plt.style.use('ggplot')
    fig = plt.figure(figsize=(15, 12))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.5], hspace=0.4, wspace=0.3)
    
    # 1. Panel superior izquierdo: Gráfico de pastel con donut
    ax1 = fig.add_subplot(gs[0, 0])
    
    estados = list(conteo_estados.keys())
    valores = list(conteo_estados.values())
    colores_utilizados = [COLORES_ESTADO[estado] for estado in estados]
    
    total = sum(valores)
    porcentajes = [v/total*100 for v in valores]
    
    # Gráfico tipo donut
    wedges, _, autotexts = ax1.pie(
        valores, 
        labels=None,
        autopct='%1.1f%%',
        startangle=90,
        shadow=False,
        colors=colores_utilizados,
        wedgeprops={'width': 0.5, 'edgecolor': 'w', 'linewidth': 2},
        textprops={'fontsize': 10, 'fontweight': 'bold', 'color': 'white'}
    )
    
    # Crear y posicionar leyenda
    etiquetas_leyenda = [f'{NOMBRES_ESTADO[estado]}: {valor} ({porcentaje:.1f}%)' 
                        for estado, valor, porcentaje in zip(estados, valores, porcentajes)]
    ax1.legend(wedges, etiquetas_leyenda, loc="center left", bbox_to_anchor=(0, 0.5),
                fontsize=9, frameon=True, title="Estados", title_fontsize=10)
    
    # Círculo blanco en el centro para convertirlo en donut
    circle = plt.Circle((0,0), 0.25, fc='white')
    ax1.add_artist(circle)
    
    # Mostrar total en el centro
    ax1.text(0, 0, f'Total\n{total}', ha='center', va='center', fontsize=12, fontweight='bold')
    
    ax1.set_title("Distribución por Estado", fontsize=12, fontweight='bold')
    
    # 2. Panel superior derecho: Barras horizontales comparativas
    ax2 = fig.add_subplot(gs[0, 1])
    
    # Crear barras horizontales
    y_pos = np.arange(len(estados))
    
    bars = ax2.barh(y_pos, valores, color=colores_utilizados, height=0.6, 
                    edgecolor='white', linewidth=1)
    
    # Añadir etiquetas de estados
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([NOMBRES_ESTADO[estado] for estado in estados])
    
    # Añadir valores y porcentajes al final de las barras
    for i, (bar, valor, porcentaje) in enumerate(zip(bars, valores, porcentajes)):
        ax2.text(valor + total*0.01, i, f"{valor} ({porcentaje:.1f}%)", 
                va='center', fontsize=10, fontweight='bold')
    
    # Configuración del gráfico de barras
    ax2.set_xlabel('Cantidad de Tickets', fontsize=10, fontweight='bold')
    ax2.set_title("Comparativa por Estado", fontsize=12, fontweight='bold')
    ax2.grid(axis='x', linestyle='--', alpha=0.7)
    ax2.set_xlim(0, max(valores) * 1.15)
    
    # 3. Panel inferior: Tendencia temporal (líneas)
    ax3 = fig.add_subplot(gs[1, :])
    
    # Obtener tickets con fechas válidas
    tickets_con_fecha = tickets_filtrados.filter(fecha_creacion__isnull=False)
    
    if tickets_con_fecha.exists():
        # Procesar solo tickets con fechas válidas
        tickets_raw = list(tickets_con_fecha.values('id', 'fecha_creacion', 'id_estado'))
        
        # Definir el período para el análisis (últimos 6 meses)
        hoy = timezone.now().date()
        fecha_inicio = (hoy - timedelta(days=180)).replace(day=1)  # 6 meses atrás, corregido
        
        # Crear diccionario para fechas
        fechas = {}
        fecha_actual = fecha_inicio
        while fecha_actual <= hoy:
            key_fecha = fecha_actual.strftime('%Y-%m')
            label_fecha = fecha_actual.strftime('%b %Y')
            fechas[key_fecha] = {
                'label': label_fecha,
                'date': fecha_actual,
                'abierto': 0,
                'en_progreso': 0,
                'cerrado': 0
            }
            # Avanzar al siguiente mes
            if fecha_actual.month == 12:
                fecha_actual = fecha_actual.replace(year=fecha_actual.year + 1, month=1)
            else:
                fecha_actual = fecha_actual.replace(month=fecha_actual.month + 1)
        
        # Contar tickets por mes y estado
        for ticket in tickets_raw:
            fecha = ticket['fecha_creacion'].date()
            if fecha < fecha_inicio:
                continue
                
            key_fecha = fecha.strftime('%Y-%m')
            if key_fecha in fechas:
                estado = ticket['id_estado']
                if estado in ['abierto', 'en_progreso', 'cerrado']:
                    fechas[key_fecha][estado] += 1
        
        # Convertir a listas para graficación
        x_labels = [data['label'] for _, data in sorted(fechas.items())]
        datasets = {}
        for estado in ['abierto', 'en_progreso', 'cerrado']:
            datasets[estado] = [fechas[key][estado] for key, _ in sorted(fechas.items())]
        
        # Dibujar líneas por estado
        for estado, valores_estado in datasets.items():
            ax3.plot(x_labels, valores_estado, marker='o', linewidth=2,
                    label=NOMBRES_ESTADO[estado], color=COLORES_ESTADO[estado])
        
        # Dibujar línea de total
        totales = [sum(data[estado] for estado in ['abierto', 'en_progreso', 'cerrado']) 
                  for _, data in sorted(fechas.items())]
        ax3.plot(x_labels, totales, marker='s', linewidth=3, color='black', label='Total')
        
        # Añadir valores sobre la línea de total
        for i, (x, y) in enumerate(zip(x_labels, totales)):
            ax3.annotate(str(y), (i, y), xytext=(0, 5), 
                        textcoords='offset points', ha='center', fontsize=9)
        
        # Calcular línea de tendencia para el total
        if len(totales) > 1:
            x_num = np.arange(len(totales))
            z = np.polyfit(x_num, totales, 1)
            p = np.poly1d(z)
            ax3.plot(x_labels, p(x_num), "r--", linewidth=1.5, alpha=0.7, label='Tendencia')
            
            # Añadir texto con la tendencia
            pendiente = z[0]
            if abs(pendiente) >= 0.1:
                tendencia_texto = "creciente" if pendiente > 0 else "decreciente"
                ax3.text(0.02, 0.98, f"Tendencia {tendencia_texto}: {abs(pendiente):.1f} tickets/mes", 
                        transform=ax3.transAxes, fontsize=9, va='top', ha='left',
                        bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.5))
        
        # Configuración del gráfico de líneas
        ax3.set_xlabel('Mes', fontsize=10, fontweight='bold')
        ax3.set_ylabel('Cantidad de Tickets', fontsize=10, fontweight='bold')
        ax3.set_title("Evolución Mensual por Estado", fontsize=12, fontweight='bold')
        ax3.grid(True, linestyle='--', alpha=0.7)
        ax3.legend(loc='upper left', fontsize=9)
        
        # Rotar etiquetas del eje X
        plt.setp(ax3.get_xticklabels(), rotation=45, ha="right", fontsize=9)
        
    else:
        ax3.text(0.5, 0.5, "No hay datos con fechas válidas para mostrar tendencia", 
                ha='center', va='center', fontsize=12)
        ax3.axis('off')
    
    # Título general del dashboard
    fig.suptitle(titulo, fontsize=16, fontweight='bold', y=0.98)
    
    # Guardar como imagen base64
    buf = io.BytesIO()
    plt.tight_layout(rect=[0, 0, 1, 0.96])  # Ajustar para el título general
    plt.savefig(buf, format='png', dpi=120)
    plt.close(fig)
    buf.seek(0)

    imagen_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    print("Dashboard de estados generado exitosamente.")
    return f"data:image/png;base64,{imagen_base64}"


@login_required
@user_passes_test(es_superadmin, login_url='login')
def reporte_superadmin(request):
    """
    Vista para descargar el reporte del superadmin.
    Maneja filtros y la generación de gráficos
    """
    # OBTENER VALORES UNICOS DE LAS AGENCIAS / CORRESPONSALES
    agencias = Tickets.objects.values_list('agencia_corresponsal', flat=True).distinct()
    # OBTENER VALORES UNICOS DE ADMINISTRATIVA
    admins = Tickets.objects.values_list('administrativa', flat=True).distinct()
    # COMBINAR LAS LISTAS, PARA HACER UN SOLO CHOICES
    todas_las_areas = set(list(agencias) + list(admins))
    areas_filtradas = {
        area for area in todas_las_areas
        # VALIDAMOS QUE NO ESTE VACIO
        if area and area.strip() and area.strip().lower() != 'no aplica'
    }

    area_choices_combinadas = sorted(list(areas_filtradas))

    context = {
        'superadmin_user': request.user,  # Usuario autenticado
        'fecha_hoy': timezone.now().date(),  # Fecha actual en formato
        'motivo_cierre_choices': Tickets.MOTIVO_CIERRE_CHOICES, # Pasa las opciones a la plantilla
        'area_agencia_choices': area_choices_combinadas, # Pasa las opciones ya combinadas a la plantilla
        'categoria_choices': Tickets.objects.values_list('tipo_soporte', flat=True).distinct().order_by('tipo_soporte'),
    }

    reporte_data = {}
    grafico_mensual_b64 = None

    if request.method == 'GET' and 'generar_pdf' in request.GET:
        # ----- OBTENER FILTROS ----
        fecha_inicio_str = request.GET.get('fecha_inicio')
        fecha_fin_str = request.GET.get('fecha_fin')
        area_seleccionada_filtro = request.GET.get('area_agencia')
        motivo_cierre_filtro = request.GET.get('motivo_cierre')
        categoria_filtro = request.GET.get('categoria')
        generar_grafico = request.GET.get('generar_grafico', '').lower() == 'true'
        
        # Imprimir valores de filtros para depuración
        print(f"Filtros recibidos: fecha_inicio={fecha_inicio_str}, fecha_fin={fecha_fin_str}, area={area_seleccionada_filtro}, motivo={motivo_cierre_filtro}, categoria={categoria_filtro}")
        print(f"Valor de generar_grafico: {generar_grafico}")

        # ---- FILTRADO DE LA BASE ----
        tickets_base = Tickets.objects.all()
        print(f"Total de tickets iniciales: {tickets_base.count()}")

        # --- FILTROS DE FECHA ---
        fecha_inicio = None
        fecha_fin = None

        if fecha_inicio_str:
            try:
                fecha_inicio_date = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                fecha_inicio = fecha_inicio_date
                # Crear un datetime para el inicio del día (00:00:00)
                fecha_inicio_dt = datetime.combine(fecha_inicio_date, datetime.min.time())
                if settings.USE_TZ:
                    # Hacerlo consciente de la zona horaria
                    fecha_inicio_dt = timezone.make_aware(fecha_inicio_dt, timezone.get_default_timezone())
                
                print(f"Filtrando fecha_creacion >= {fecha_inicio_dt}")
                tickets_base = tickets_base.filter(fecha_creacion__gte=fecha_inicio_dt)
                print(f"Tickets después de filtro fecha inicio: {tickets_base.count()}")
            except ValueError as e:
                print(f"Error con el formato de fecha_inicio: {e}")
                messages.error(request, f"Formato de fecha inválido para inicio: {fecha_inicio_str}")
            except Exception as e:
                print(f"Error aplicando filtro fecha_inicio: {e}")
                messages.error(request, f"Error al filtrar por fecha de inicio: {e}")

        if fecha_fin_str:
            try:
                fecha_fin_date = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
                fecha_fin = fecha_fin_date
                # Crear un datetime para el final del día (23:59:59.999999)
                fecha_fin_dt = datetime.combine(fecha_fin_date, datetime.max.time())
                if settings.USE_TZ:
                    # Hacerlo consciente de la zona horaria
                    fecha_fin_dt = timezone.make_aware(fecha_fin_dt, timezone.get_default_timezone())
                
                print(f"Filtrando fecha_creacion <= {fecha_fin_dt}")
                tickets_base = tickets_base.filter(fecha_creacion__lte=fecha_fin_dt)
                print(f"Tickets después de filtro fecha fin: {tickets_base.count()}")
            except ValueError as e:
                print(f"Error con el formato de fecha_fin: {e}")
                messages.error(request, f"Formato de fecha inválido para fin: {fecha_fin_str}")
            except Exception as e:
                print(f"Error aplicando filtro fecha_fin: {e}")
                messages.error(request, f"Error al filtrar por fecha de fin: {e}")

        # --- FILTRO DE ÁREA/AGENCIA ---
        if area_seleccionada_filtro:
            try:
                print(f"Aplicando filtro de área: '{area_seleccionada_filtro}'")
                tickets_base = tickets_base.filter(
                    Q(agencia_corresponsal=area_seleccionada_filtro) |
                    Q(administrativa=area_seleccionada_filtro)
                )
                print(f"Tickets después de filtro área combinada: {tickets_base.count()}")
            except Exception as e:
                print(f"Error aplicando filtro área combinada: {e}")
                messages.error(request, f"Error al filtrar por área/agencia: {e}")

        # --- FILTRO DE CATEGORÍA ---
        if categoria_filtro:
            try:
                tickets_base = tickets_base.filter(tipo_soporte=categoria_filtro)
                print(f"Tickets después de filtro categoría: {tickets_base.count()}")
            except Exception as e:
                print(f"Error aplicando filtro categoría: {e}")
                messages.error(request, f"Error al filtrar por categoría: {e}")

        reporte_data['filtro_aplicados'] = {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'area_agencia': area_seleccionada_filtro,
            'motivo_cierre': motivo_cierre_filtro,
            'categoria': categoria_filtro
        }

        # ---- REPORTE 1: CONTEO POR ESTADO (VAMOS A FILTRAR POR FECHA) ---
        tickets_para_conteo = tickets_base # TOMAMOS LOS TICKETS YA FILTRADOS
        reporte_data['conteo_estados'] = {
            'abierto': tickets_para_conteo.filter(id_estado='abierto').count(),
            'en_progreso': tickets_para_conteo.filter(id_estado='en_progreso').count(),
            'cerrado': tickets_para_conteo.filter(id_estado='cerrado').count()
        }

        # ---- REPORTE 2: PROMEDIO DE SOLUCIÓN ----
        tickets_cerrados_para_promedio = tickets_base.filter(
            id_estado='cerrado', 
            fecha_cierre__isnull=False, 
            fecha_creacion__isnull=False
        )

        # ---- CALCULAMOS DIFERENCIA DE TIEMPO POR CADA UNO DE LOS TICKETS ----
        diferencias_tiempo = ExpressionWrapper(F('fecha_cierre') - F('fecha_creacion'),output_field=DurationField())
        promedio_resultado = tickets_cerrados_para_promedio.annotate(
            tiempo_solucion=diferencias_tiempo).aggregate(promedio=Avg('tiempo_solucion'))
        
        reporte_data['promedio_solucion'] = promedio_resultado['promedio']

        # ---- REPORTE 3: CONSOLIDADO POR AGENCIA O AREA ----
        reporte_data['consolidado_agencia'] = tickets_base.exclude(
            agencia_corresponsal__isnull=True).exclude(
            agencia_corresponsal='').exclude(
            agencia_corresponsal__iexact='No Aplica').values(
            'agencia_corresponsal').annotate(
            count=Count('id')
            ).order_by('-count')
        
        reporte_data['consolidado_administrativa'] = tickets_base.exclude(
            administrativa__isnull=True).exclude(
            administrativa='').exclude(
            administrativa__iexact='No Aplica').values(
            'administrativa').annotate(
            count=Count('id')
            ).order_by('-count')

        # tickets_para_area = tickets_base
        # if area_seleccionada_filtro:
        #     tickets_para_area = tickets_para_area.filter(usuario__area_agencia=area_seleccionada_filtro)

        # reporte_data['consolidado_area'] = tickets_para_area.values(
        #     'usuario__area_agencia').annotate(
        #     count=Count('id')
        #     ).order_by('-count') # ORDENAR POR CANDIDAD DESCENDENTE
        
        # ---- REPORTE 4: FILTRO POR MOTIVO DE CIERRE ----
        tickets_para_motivo = tickets_base.filter(id_estado='cerrado')
        
        if motivo_cierre_filtro:
            tickets_para_motivo = tickets_para_motivo.filter(motivo_cierre=motivo_cierre_filtro)     
            reporte_data['conteo_motivo_cierre'] = {
                'motivo': dict(Tickets.MOTIVO_CIERRE_CHOICES).get(motivo_cierre_filtro, motivo_cierre_filtro), # Mostrar el nombre legible
                'cantidad': tickets_para_motivo.count()
            }
        else:
            # SI PASA UN ERROR Y NO SE FILTRA, MUESTRA CONTEO POR TODOS LOS MOTIVOS
            reporte_data['conteo_todos_motivos'] = tickets_para_motivo.values(
            'motivo_cierre'
            ).annotate(
                cantidad=Count('id')
            ).order_by('motivo_cierre')
            reporte_data['conteo_todos_motivos'] = [
                {'motivo': dict(Tickets.MOTIVO_CIERRE_CHOICES).get(item['motivo_cierre'], item['motivo_cierre']), 'cantidad': item['cantidad']} 
                for item in reporte_data['conteo_todos_motivos'] if item['motivo_cierre']
            ]

        # ---- REPORTE 5: FILTRAR POR CATEGORIA
        tickets_para_categoria = tickets_base
        if categoria_filtro:
            # tickets_para_categoria = tickets_para_categoria.filter(tipo_soporte=categoria_filtro)
            reporte_data['conteo_categoria'] = {
                'categoria': categoria_filtro,
                'cantidad': tickets_para_categoria.count()
            }
        else:
            reporte_data['conteo_todas_categorias'] = tickets_para_categoria.values(
            'tipo_soporte'
            ).annotate(
                cantidad=Count('id')
            ).order_by('tipo_soporte')

        # --- Generar Gráfico (si se solicitó) ---
        if generar_grafico:
            # Usar los tickets filtrados para el gráfico
            tickets_para_grafico = tickets_base
            
            # Aplicar filtro de motivo solo para el gráfico si se especificó
            if motivo_cierre_filtro:
                tickets_para_grafico = tickets_para_grafico.filter(motivo_cierre=motivo_cierre_filtro, id_estado='cerrado')
            
            print(f"Generando gráfico con {tickets_para_grafico.count()} tickets")
            grafico_mensual_b64 = generar_grafico_mensual(tickets_para_grafico)
            
            if grafico_mensual_b64 is None:
                messages.warning(request, "No se pudo generar el gráfico por falta de datos válidos.")

        # --- RENDERIZAR EL HTML A PDF ---
        context['reporte_data'] = reporte_data
        context['grafico_mensual_b64'] = grafico_mensual_b64

        print("Valor del grafico_mensual_b64: ", grafico_mensual_b64[:100] if grafico_mensual_b64 else None)

        html_string = render_to_string('superadmin/reporte_template.html', context)

        try:
            html = HTML(string=html_string, base_url=request.build_absolute_uri())
            result = html.write_pdf()

            # CREAR LA RESPUESTA CON HTTP CON EL PDF
            response = HttpResponse(result, content_type='application/pdf')
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            response['Content-Disposition'] = f'attachment; filename="reporte_{timestamp}.pdf"'
            return response
        except Exception as e:
            print(f"Error al generar el PDF: {e}")
            messages.error(request, f"Error al generar el PDF: {e}")
            return render(request, 'superadmin/superadmin_reportes.html', context)

    # WeasyPrint USAR ESTA LIBRERIA
    return render(request, 'superadmin/superadmin_reportes.html', context)