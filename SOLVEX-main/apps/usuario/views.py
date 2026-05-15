from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import PasswordChangeView
from django.http import HttpResponseNotAllowed, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import ExpressionWrapper, F, DurationField, Avg, Count, Q
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy

# ---- IMPORTACIONES PARA CHANNELS (WebSockets) ----
from channels.layers import get_channel_layer  # type: ignore
from asgiref.sync import async_to_sync
import logging

# ---- IMPORTACIONES ADICIONALES ----
from weasyprint import HTML
from django.conf import settings
from apps.tickets.models import Tickets, Ticket_comentarios
import io
import base64
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
matplotlib.use('Agg')

from .forms import CambiarContraseñaForm
from apps.usuario.models import Usuario

logger = logging.getLogger(__name__)


# ================================================================
# FUNCIONES DE VERIFICACIÓN DE ROL
# ================================================================
# Usadas como predicado en @user_passes_test.
# Usan las properties del modelo Usuario para no duplicar lógica.
# ================================================================

def es_admin_o_superadmin(user):
    """True si el usuario autenticado es admin o superadmin."""
    return user.is_authenticated and user.es_admin_tipo


def es_superadmin(user):
    """True si el usuario autenticado es superadmin."""
    return user.is_authenticated and user.es_superadmin_tipo


# ================================================================
# FUNCIONES AUXILIARES DE SEGURIDAD
# ================================================================
# Evitan errores al acceder a atributos de usuario que podrían
# ser None o no existir en casos extremos.
# ================================================================

def _get_safe_username(user):
    """Retorna el username del usuario o 'Usuario Desconocido' si falla."""
    if user and hasattr(user, 'username') and user.username:
        return str(user.username)
    return 'Usuario Desconocido'


def _get_safe_user_nombre(user):
    """Retorna el nombre completo del usuario o su username como fallback."""
    if user and hasattr(user, 'nombre') and user.nombre:
        return str(user.nombre)
    return _get_safe_username(user)


# ================================================================
# FUNCIONES AUXILIARES DE WEBSOCKET Y COMENTARIOS DE SISTEMA
# ================================================================
# Centralizan el envío de mensajes por WebSocket y la creación
# de comentarios automáticos del sistema (autor=None).
# ================================================================

def _save_system_comment_sync(ticket_id, message_text):
    """
    Guarda un comentario de sistema (autor=None) de forma síncrona.
    Los comentarios de sistema registran acciones como tomar,
    reasignar o cerrar un ticket en el historial del chat.
    """
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
    """
    Envía un mensaje al grupo WebSocket del ticket específico.
    Usado para notificar cambios de estado en tiempo real
    a todos los usuarios conectados al chat de ese ticket.
    """
    channel_layer = get_channel_layer()
    group_name = f'ticket_{ticket_id}'
    message_payload = {'type': payload_type}
    message_payload.update(data_dict)
    async_to_sync(channel_layer.group_send)(group_name, message_payload)
    logger.info(f"Mensaje tipo '{payload_type}' enviado al grupo {group_name}.")


def _send_admin_dashboard_update(target_group_suffix, event_type, data_dict):
    """
    Envía una notificación al dashboard de administradores vía WebSocket.
    Usado cuando se crea un nuevo ticket para que aparezca en tiempo
    real en el dashboard sin necesidad de recargar la página.
    """
    channel_layer = get_channel_layer()
    group_name = f'admin_dashboard_{target_group_suffix}'
    message_payload = {
        'type': event_type,
        'ticket_data': data_dict
    }
    async_to_sync(channel_layer.group_send)(group_name, message_payload)
    ticket_id_log = data_dict.get('id', 'N/A') if isinstance(data_dict, dict) else 'N/A'
    logger.info(f"Notificación '{event_type}' enviada al grupo {group_name} para ticket {ticket_id_log}.")


def _notify_system_comment(ticket_id, message_text):
    """
    Guarda un comentario de sistema en la base de datos.
    Punto de entrada unificado para registrar acciones automáticas.
    """
    _save_system_comment_sync(ticket_id, message_text)


# ================================================================
# VISTAS DE AUTENTICACIÓN Y REDIRECCIÓN
# ================================================================

@login_required
def post_login_redirect(request):
    """
    Redirige al usuario a su dashboard según su rol después del login.
    Usa la property get_dashboard_url del modelo Usuario para
    eliminar la lógica de redirección quemada con múltiples if/elif.
    """
    return redirect(request.user.get_dashboard_url)


@login_required
def password_change_check(request):
    """
    Verifica si el usuario debe cambiar su contraseña al ingresar.
    Si debe_cambiar_contrasena es True, lo redirige al formulario.
    De lo contrario, lo redirige a su dashboard correspondiente.
    """
    if request.user.debe_cambiar_contrasena:
        return redirect('usuario:cambiar_contrasena')
    return post_login_redirect(request)


class CambiarContrasenaView(LoginRequiredMixin, PasswordChangeView):
    """
    Vista para cambiar la contraseña del usuario autenticado.
    Al cambiar exitosamente, marca debe_cambiar_contrasena=False
    y redirige al login para que inicie sesión con la nueva contraseña.
    """
    template_name = 'usuario/cambiar_contrasena.html'
    form_class = CambiarContraseñaForm
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        user_to_update = form.user
        # Guarda la nueva contraseña
        super().form_valid(form)
        # Marca que ya no necesita cambiar la contraseña
        if hasattr(user_to_update, 'debe_cambiar_contrasena'):
            user_to_update.debe_cambiar_contrasena = False
            user_to_update.save(update_fields=['debe_cambiar_contrasena'])
        success_url = reverse('login') + '?success_message=Contraseña cambiada con éxito. Por favor, inicie sesión nuevamente.'
        return redirect(success_url)


# ================================================================
# VISTAS DEL ADMINISTRADOR
# ================================================================

@login_required
@user_passes_test(es_admin_o_superadmin, login_url='login')
def admin_dashboard(request):
    """
    Dashboard principal del administrador.
    Muestra los tickets activos (abiertos y en progreso) de su categoría.
    Los conteos y la consulta usan métodos del modelo para evitar
    código quemado y queries duplicados.
    """
    admin_user = request.user

    # Una sola línea reemplaza el try/except con filter() quemado
    tickets = Tickets.objects.abiertos_por_categoria(admin_user.categoria)

    # Una sola query con agregaciones reemplaza la función obtener_tickets_abiertos()
    conteos = Tickets.conteos_por_categoria(admin_user.categoria)

    paginator = Paginator(tickets, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/admin.html', {
        'admin_user': admin_user,
        'page_obj': page_obj,
        # Headers desde el modelo
        'dashboard_headers': Tickets.TICKET_ADMIN_HEADERS,
        'tickets_abiertos_count': conteos['abiertos'],
        'tickets_en_progreso_count': conteos['en_progreso'],
        'tickets_cerrado_count': conteos['cerrado'],
        # Property del modelo en vez de llamar es_superadmin(request.user)
        'es_superadmin': admin_user.es_superadmin_tipo,
    })


@login_required
@user_passes_test(es_admin_o_superadmin, login_url='login')
def tickets_page_admin(request):
    """
    Historial de tickets resueltos del administrador.
    Solo muestra tickets cerrados de su categoría.
    """
    usuario_actual = request.user

    # Método del manager 
    tickets_cerrados = Tickets.objects.cerrados_por_categoria(usuario_actual.categoria)

    paginator = Paginator(tickets_cerrados, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/tickets_admin.html', {
        'posts2': page_obj,
        'colaborador': usuario_actual,
        # Headers desde el modelo
        'tickets_generales2': Tickets.TICKET_ADMIN_RESUELTOS_HEADERS,
    })


@login_required
@user_passes_test(es_admin_o_superadmin, login_url='login')
def tomar_ticket(request, ticket_id):
    """
    Permite a un admin tomar un ticket abierto.
    Cambia el estado a en_progreso, lo asigna al admin
    y notifica por WebSocket a todos los usuarios del chat.
    Solo acepta método POST.
    """
    ticket = get_object_or_404(Tickets, id=ticket_id)

    if ticket.id_estado != 'abierto':
        messages.warning(request, 'El ticket ya no se encuentra abierto.')
        return redirect('tickets:admin_ticket_detail', ticket_id=ticket_id)

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # Cambiar estado y asignar al admin actual
    ticket.id_estado = 'en_progreso'
    ticket.fecha_asignacion = timezone.now()
    ticket.asignado_a = request.user
    ticket.save()

    # Registrar acción en el historial del chat
    safe_username = _get_safe_username(request.user)
    message = f'Ticket tomado por {safe_username}.'
    _notify_system_comment(ticket_id, message)

    # Notificar por WebSocket a todos los conectados al chat
    system_message_data = {
        'author': 'Sistema',
        'message': message,
        'timestamp': timezone.now().isoformat(),
        'is_system': True,
    }
    _send_channel_message(ticket_id, 'ticket_status_update', {
        'ticket_id': ticket_id,
        'new_status_value': ticket.id_estado,
        'new_status_display': str(ticket.get_id_estado_display()),
        'asignado_a_username': _get_safe_username(ticket.asignado_a),
        'system_message': system_message_data,
    })

    success_url = reverse('tickets:admin_ticket_detail', kwargs={'ticket_id': ticket_id})
    return redirect(f'{success_url}?success_message=Ticket tomado exitosamente.')


@login_required
@user_passes_test(es_admin_o_superadmin, login_url='login')
def reasignar_ticket(request, ticket_id):
    """
    Permite reasignar un ticket a otro tipo de soporte.
    Limpia la asignación actual y devuelve el ticket a estado abierto
    para que otro admin de la categoría destino lo tome.
    Solo acepta método POST.
    """
    ticket = get_object_or_404(Tickets, id=ticket_id)

    if ticket.id_estado == 'cerrado':
        messages.warning(request, 'No se puede reasignar un ticket cerrado.')
        return redirect('tickets:admin_ticket_detail', ticket_id=ticket_id)

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    nuevo_tipo_soporte = request.POST.get('tipo_soporte')
    comentario_reasignacion = request.POST.get('comentario')

    if not nuevo_tipo_soporte:
        messages.error(request, 'Por favor, selecciona un nuevo tipo de soporte.')
        return redirect('tickets:admin_ticket_detail', ticket_id=ticket_id)

    tipo_anterior = ticket.tipo_soporte

    # Reasignar: cambiar categoría, limpiar asignación y reabrir
    ticket.tipo_soporte = nuevo_tipo_soporte
    ticket.asignado_a = None
    ticket.id_estado = 'abierto'
    ticket.fecha_asignacion = None
    ticket.save()

    # Registrar acción en el historial del chat
    safe_user_nombre = _get_safe_user_nombre(request.user)
    detalle_historial = f"Ticket reasignado de '{tipo_anterior}' a '{nuevo_tipo_soporte}' por {safe_user_nombre}"
    if comentario_reasignacion:
        detalle_historial += f'. Motivo: {comentario_reasignacion}'

    _notify_system_comment(ticket_id, detalle_historial)

    system_message_data = {
        'author': 'Sistema',
        'message': detalle_historial,
        'timestamp': timezone.now().isoformat(),
        'is_system': True,
    }
    _send_channel_message(ticket_id, 'ticket_status_update', {
        'ticket_id': ticket_id,
        'new_status_value': ticket.id_estado,
        'new_status_display': str(ticket.get_id_estado_display()),
        'asignado_a_username': None,
        'system_message': system_message_data,
    })

    success_url = reverse('usuario:admin_dashboard')
    return redirect(f'{success_url}?success_message=Ticket reasignado exitosamente.')


@login_required
@user_passes_test(es_admin_o_superadmin, login_url='login')
def cerrar_ticket(request, ticket_id):
    """
    Permite a un admin cerrar un ticket en progreso.
    Requiere seleccionar un motivo de cierre.
    Solo acepta método POST.
    """
    ticket = get_object_or_404(Tickets, id=ticket_id)

    if ticket.id_estado == 'cerrado':
        messages.warning(request, 'El ticket ya se encuentra cerrado.')
        return redirect('tickets:admin_ticket_detail', ticket_id=ticket_id)

    if ticket.id_estado == 'abierto':
        messages.warning(request, 'No se puede cerrar un ticket sin haberlo tomado primero.')
        return redirect('tickets:admin_ticket_detail', ticket_id=ticket_id)

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    motivo_cierre = request.POST.get('motivo_cierre')
    comentario_adicional = request.POST.get('comentario-cierre')

    if not motivo_cierre:
        messages.error(request, 'Debe seleccionar un motivo de cierre.')
        return redirect('tickets:admin_ticket_detail', ticket_id=ticket_id)

    # Cerrar el ticket
    ticket.id_estado = 'cerrado'
    ticket.motivo_cierre = motivo_cierre
    ticket.fecha_cierre = timezone.now()
    ticket.save()

    # Registrar acción en el historial del chat
    safe_user_nombre = _get_safe_user_nombre(request.user)
    detalle_historial = f'Ticket cerrado por {safe_user_nombre}. Motivo: {ticket.get_motivo_cierre_display()}'
    if comentario_adicional:
        detalle_historial += f'. Comentario de cierre: {comentario_adicional}'

    _notify_system_comment(ticket_id, detalle_historial)

    system_message_data = {
        'author': 'Sistema',
        'message': detalle_historial,
        'timestamp': timezone.now().isoformat(),
        'is_system': True,
    }
    _send_channel_message(ticket_id, 'ticket_status_update', {
        'ticket_id': ticket_id,
        'new_status_value': ticket.id_estado,
        'new_status_display': str(ticket.get_id_estado_display()),
        'asignado_a_username': _get_safe_username(ticket.asignado_a),
        'system_message': system_message_data,
    })

    success_url = reverse('tickets:admin_ticket_detail', kwargs={'ticket_id': ticket_id})
    return redirect(f'{success_url}?success_message=Ticket cerrado exitosamente.')


# ================================================================
# VISTAS DEL SUPERADMIN
# ================================================================

@login_required
@user_passes_test(es_superadmin, login_url='login')
def superadmin_dashboard(request):
    """
    Dashboard del superadmin con visibilidad total de todos los tickets.
    Usa métodos del modelo para conteos y consultas, eliminando
    los múltiples filter().count() quemados que había antes.
    """
    # Una sola query con agregaciones reemplaza 3 queries separados
    conteos = Tickets.conteos_generales()

    # Método del manager reemplaza Tickets.objects.all().order_by(...)
    todos = Tickets.objects.todos_ordenados()

    paginator = Paginator(todos, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'superadmin/superadmin_dashboard.html', {
        'superadmin_user': request.user,
        'page_obj': page_obj,
        # Headers desde el modelo, no quemados en la vista
        'dashboard_headers': Tickets.TICKET_SUPERADMIN_HEADERS,
        'tickets_abiertos_count': conteos['abiertos'],
        'tickets_en_progreso_count': conteos['en_progreso'],
        'tickets_cerrado_count': conteos['cerrado'],
    })


@login_required
@user_passes_test(es_superadmin, login_url='login')
def reporte_superadmin(request):
    """
    Vista para generar y descargar reportes en PDF.
    Usa el método get_areas_para_reporte() del modelo para obtener
    las áreas disponibles en vez de hacer dos queries manuales.
    """
    context = {
        'superadmin_user': request.user,
        'fecha_hoy': timezone.now().date(),
        # Choices desde el modelo, no quemados en la vista
        'motivo_cierre_choices': Tickets.MOTIVO_CIERRE_CHOICES,
        # Método del modelo reemplaza las dos queries manuales de agencias y áreas
        'area_agencia_choices': Tickets.get_areas_para_reporte(),
        'categoria_choices': Tickets.objects.values_list(
            'tipo_soporte', flat=True
        ).distinct().order_by('tipo_soporte'),
    }

    reporte_data = {}
    grafico_mensual_b64 = None

    if request.method == 'GET' and 'generar_pdf' in request.GET:

        # ---- Obtener filtros del request ----
        fecha_inicio_str = request.GET.get('fecha_inicio')
        fecha_fin_str = request.GET.get('fecha_fin')
        area_seleccionada = request.GET.get('area_agencia')
        motivo_cierre_filtro = request.GET.get('motivo_cierre')
        categoria_filtro = request.GET.get('categoria')
        generar_grafico = request.GET.get('generar_grafico', '').lower() == 'true'

        # ---- Base de tickets a filtrar ----
        tickets_base = Tickets.objects.all()

        # ---- Filtro por fecha inicio ----
        fecha_inicio = None
        if fecha_inicio_str:
            try:
                fecha_inicio_date = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                fecha_inicio = fecha_inicio_date
                fecha_inicio_dt = datetime.combine(fecha_inicio_date, datetime.min.time())
                if settings.USE_TZ:
                    fecha_inicio_dt = timezone.make_aware(
                        fecha_inicio_dt, timezone.get_default_timezone()
                    )
                tickets_base = tickets_base.filter(fecha_creacion__gte=fecha_inicio_dt)
            except ValueError:
                messages.error(request, f'Formato de fecha inválido para inicio: {fecha_inicio_str}')
            except Exception as e:
                messages.error(request, f'Error al filtrar por fecha de inicio: {e}')

        # ---- Filtro por fecha fin ----
        fecha_fin = None
        if fecha_fin_str:
            try:
                fecha_fin_date = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
                fecha_fin = fecha_fin_date
                fecha_fin_dt = datetime.combine(fecha_fin_date, datetime.max.time())
                if settings.USE_TZ:
                    fecha_fin_dt = timezone.make_aware(
                        fecha_fin_dt, timezone.get_default_timezone()
                    )
                tickets_base = tickets_base.filter(fecha_creacion__lte=fecha_fin_dt)
            except ValueError:
                messages.error(request, f'Formato de fecha inválido para fin: {fecha_fin_str}')
            except Exception as e:
                messages.error(request, f'Error al filtrar por fecha de fin: {e}')

        # ---- Filtro por área/agencia ----
        if area_seleccionada:
            tickets_base = tickets_base.filter(
                Q(agencia_corresponsal=area_seleccionada) |
                Q(administrativa=area_seleccionada)
            )

        # ---- Filtro por categoría ----
        if categoria_filtro:
            tickets_base = tickets_base.filter(tipo_soporte=categoria_filtro)

        reporte_data['filtro_aplicados'] = {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'area_agencia': area_seleccionada,
            'motivo_cierre': motivo_cierre_filtro,
            'categoria': categoria_filtro,
        }

        # ---- Reporte 1: Conteo por estado ----
        reporte_data['conteo_estados'] = {
            'abierto': tickets_base.filter(id_estado='abierto').count(),
            'en_progreso': tickets_base.filter(id_estado='en_progreso').count(),
            'cerrado': tickets_base.filter(id_estado='cerrado').count(),
        }

        # ---- Reporte 2: Promedio de solución ----
        tickets_cerrados_promedio = tickets_base.filter(
            id_estado='cerrado',
            fecha_cierre__isnull=False,
            fecha_creacion__isnull=False
        )
        diferencias_tiempo = ExpressionWrapper(
            F('fecha_cierre') - F('fecha_creacion'),
            output_field=DurationField()
        )
        promedio_resultado = tickets_cerrados_promedio.annotate(
            tiempo_solucion=diferencias_tiempo
        ).aggregate(promedio=Avg('tiempo_solucion'))
        reporte_data['promedio_solucion'] = promedio_resultado['promedio']

        # ---- Reporte 3: Consolidado por agencia y área ----
        reporte_data['consolidado_agencia'] = tickets_base.exclude(
            agencia_corresponsal__isnull=True
        ).exclude(agencia_corresponsal='').exclude(
            agencia_corresponsal__iexact='No Aplica'
        ).values('agencia_corresponsal').annotate(
            count=Count('id')
        ).order_by('-count')

        reporte_data['consolidado_administrativa'] = tickets_base.exclude(
            administrativa__isnull=True
        ).exclude(administrativa='').exclude(
            administrativa__iexact='No Aplica'
        ).values('administrativa').annotate(
            count=Count('id')
        ).order_by('-count')

        # ---- Reporte 4: Por motivo de cierre ----
        tickets_para_motivo = tickets_base.filter(id_estado='cerrado')
        if motivo_cierre_filtro:
            tickets_para_motivo = tickets_para_motivo.filter(motivo_cierre=motivo_cierre_filtro)
            reporte_data['conteo_motivo_cierre'] = {
                'motivo': dict(Tickets.MOTIVO_CIERRE_CHOICES).get(
                    motivo_cierre_filtro, motivo_cierre_filtro
                ),
                'cantidad': tickets_para_motivo.count(),
            }
        else:
            motivos_raw = tickets_para_motivo.values('motivo_cierre').annotate(
                cantidad=Count('id')
            ).order_by('motivo_cierre')
            reporte_data['conteo_todos_motivos'] = [
                {
                    'motivo': dict(Tickets.MOTIVO_CIERRE_CHOICES).get(
                        item['motivo_cierre'], item['motivo_cierre']
                    ),
                    'cantidad': item['cantidad']
                }
                for item in motivos_raw if item['motivo_cierre']
            ]

        # ---- Reporte 5: Por categoría ----
        if categoria_filtro:
            reporte_data['conteo_categoria'] = {
                'categoria': categoria_filtro,
                'cantidad': tickets_base.count(),
            }
        else:
            reporte_data['conteo_todas_categorias'] = tickets_base.values(
                'tipo_soporte'
            ).annotate(cantidad=Count('id')).order_by('tipo_soporte')

        # ---- Generar gráfico si se solicitó ----
        if generar_grafico:
            tickets_para_grafico = tickets_base
            if motivo_cierre_filtro:
                tickets_para_grafico = tickets_para_grafico.filter(
                    motivo_cierre=motivo_cierre_filtro, id_estado='cerrado'
                )
            grafico_mensual_b64 = generar_grafico_mensual(tickets_para_grafico)
            if grafico_mensual_b64 is None:
                messages.warning(request, 'No se pudo generar el gráfico por falta de datos.')

        # ---- Renderizar a PDF ----
        context['reporte_data'] = reporte_data
        context['grafico_mensual_b64'] = grafico_mensual_b64

        html_string = render_to_string('superadmin/reporte_template.html', context)
        try:
            html = HTML(string=html_string, base_url=request.build_absolute_uri())
            result = html.write_pdf()
            response = HttpResponse(result, content_type='application/pdf')
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            response['Content-Disposition'] = f'attachment; filename="reporte_{timestamp}.pdf"'
            return response
        except Exception as e:
            logger.error(f'Error al generar el PDF: {e}', exc_info=True)
            messages.error(request, f'Error al generar el PDF: {e}')
            return render(request, 'superadmin/superadmin_reportes.html', context)

    return render(request, 'superadmin/superadmin_reportes.html', context)


# ================================================================
# FUNCIÓN DE GENERACIÓN DE GRÁFICOS
# ================================================================
# Se mantiene en views.py porque es lógica de presentación,
# no de negocio. Genera un dashboard visual con matplotlib
# que se convierte a base64 para embeber en el PDF.
# ================================================================

def generar_grafico_mensual(tickets_filtrados, titulo='Dashboard de Tickets por Estado'):
    """
    Genera un dashboard con gráfico de donut, barras horizontales
    y línea de tendencia mensual. Retorna la imagen en base64
    para embeber directamente en el PDF del reporte.

    Args:
        tickets_filtrados: QuerySet de tickets a graficar
        titulo: Título del dashboard

    Returns:
        String base64 de la imagen o None si no hay datos
    """
    COLORES_ESTADO = {
        'abierto': '#dc3545',
        'en_progreso': '#ffc107',
        'cerrado': '#28a745',
        'default': '#6c757d'
    }
    NOMBRES_ESTADO = {
        'abierto': 'Abierto',
        'en_progreso': 'En Progreso',
        'cerrado': 'Cerrado',
    }

    if not tickets_filtrados.exists():
        return None

    conteo_estados = {
        'abierto': tickets_filtrados.filter(id_estado='abierto').count(),
        'en_progreso': tickets_filtrados.filter(id_estado='en_progreso').count(),
        'cerrado': tickets_filtrados.filter(id_estado='cerrado').count()
    }
    conteo_estados = {k: v for k, v in conteo_estados.items() if v > 0}

    if not conteo_estados:
        return None

    plt.style.use('ggplot')
    fig = plt.figure(figsize=(15, 12))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.5], hspace=0.4, wspace=0.3)

    estados = list(conteo_estados.keys())
    valores = list(conteo_estados.values())
    colores_utilizados = [COLORES_ESTADO[estado] for estado in estados]
    total = sum(valores)
    porcentajes = [v / total * 100 for v in valores]

    # Panel 1: Gráfico donut
    ax1 = fig.add_subplot(gs[0, 0])
    wedges, _, _ = ax1.pie(
        valores, labels=None, autopct='%1.1f%%', startangle=90,
        colors=colores_utilizados,
        wedgeprops={'width': 0.5, 'edgecolor': 'w', 'linewidth': 2},
        textprops={'fontsize': 10, 'fontweight': 'bold', 'color': 'white'}
    )
    etiquetas_leyenda = [
        f'{NOMBRES_ESTADO[e]}: {v} ({p:.1f}%)'
        for e, v, p in zip(estados, valores, porcentajes)
    ]
    ax1.legend(wedges, etiquetas_leyenda, loc='center left',
        bbox_to_anchor=(0, 0.5), fontsize=9, frameon=True,
        title='Estados', title_fontsize=10)
    circle = plt.Circle((0, 0), 0.25, fc='white')
    ax1.add_artist(circle)
    ax1.text(0, 0, f'Total\n{total}', ha='center', va='center',
        fontsize=12, fontweight='bold')
    ax1.set_title('Distribución por Estado', fontsize=12, fontweight='bold')

    # Panel 2: Barras horizontales
    ax2 = fig.add_subplot(gs[0, 1])
    y_pos = np.arange(len(estados))
    bars = ax2.barh(y_pos, valores, color=colores_utilizados,
                    height=0.6, edgecolor='white', linewidth=1)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([NOMBRES_ESTADO[e] for e in estados])
    for i, (bar, valor, porcentaje) in enumerate(zip(bars, valores, porcentajes)):
        ax2.text(valor + total * 0.01, i, f'{valor} ({porcentaje:.1f}%)',
            va='center', fontsize=10, fontweight='bold')
    ax2.set_xlabel('Cantidad de Tickets', fontsize=10, fontweight='bold')
    ax2.set_title('Comparativa por Estado', fontsize=12, fontweight='bold')
    ax2.grid(axis='x', linestyle='--', alpha=0.7)
    ax2.set_xlim(0, max(valores) * 1.15)

    # Panel 3: Tendencia mensual
    ax3 = fig.add_subplot(gs[1, :])
    tickets_con_fecha = tickets_filtrados.filter(fecha_creacion__isnull=False)

    if tickets_con_fecha.exists():
        tickets_raw = list(tickets_con_fecha.values('id', 'fecha_creacion', 'id_estado'))
        hoy = timezone.now().date()
        fecha_inicio = (hoy - timedelta(days=180)).replace(day=1)

        fechas = {}
        fecha_actual = fecha_inicio
        while fecha_actual <= hoy:
            key = fecha_actual.strftime('%Y-%m')
            fechas[key] = {
                'label': fecha_actual.strftime('%b %Y'),
                'abierto': 0, 'en_progreso': 0, 'cerrado': 0
            }
            if fecha_actual.month == 12:
                fecha_actual = fecha_actual.replace(year=fecha_actual.year + 1, month=1)
            else:
                fecha_actual = fecha_actual.replace(month=fecha_actual.month + 1)

        for ticket in tickets_raw:
            fecha = ticket['fecha_creacion'].date()
            if fecha < fecha_inicio:
                continue
            key = fecha.strftime('%Y-%m')
            if key in fechas and ticket['id_estado'] in fechas[key]:
                fechas[key][ticket['id_estado']] += 1

        x_labels = [data['label'] for _, data in sorted(fechas.items())]
        for estado in ['abierto', 'en_progreso', 'cerrado']:
            valores_estado = [fechas[k][estado] for k in sorted(fechas.keys())]
            ax3.plot(x_labels, valores_estado, marker='o', linewidth=2,
                label=NOMBRES_ESTADO[estado], color=COLORES_ESTADO[estado])

        totales = [
            sum(fechas[k][e] for e in ['abierto', 'en_progreso', 'cerrado'])
            for k in sorted(fechas.keys())
        ]
        ax3.plot(x_labels, totales, marker='s', linewidth=3,
                color='black', label='Total')

        for i, (x, y) in enumerate(zip(x_labels, totales)):
            ax3.annotate(str(y), (i, y), xytext=(0, 5),
                textcoords='offset points', ha='center', fontsize=9)

        if len(totales) > 1:
            x_num = np.arange(len(totales))
            z = np.polyfit(x_num, totales, 1)
            p = np.poly1d(z)
            ax3.plot(x_labels, p(x_num), 'r--', linewidth=1.5,
                alpha=0.7, label='Tendencia')
            pendiente = z[0]
            if abs(pendiente) >= 0.1:
                tendencia_texto = 'creciente' if pendiente > 0 else 'decreciente'
                ax3.text(0.02, 0.98,
                    f'Tendencia {tendencia_texto}: {abs(pendiente):.1f} tickets/mes',
                    transform=ax3.transAxes, fontsize=9, va='top', ha='left',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.5))

        ax3.set_xlabel('Mes', fontsize=10, fontweight='bold')
        ax3.set_ylabel('Cantidad de Tickets', fontsize=10, fontweight='bold')
        ax3.set_title('Evolución Mensual por Estado', fontsize=12, fontweight='bold')
        ax3.grid(True, linestyle='--', alpha=0.7)
        ax3.legend(loc='upper left', fontsize=9)
        plt.setp(ax3.get_xticklabels(), rotation=45, ha='right', fontsize=9)
    else:
        ax3.text(0.5, 0.5, 'No hay datos con fechas válidas para mostrar tendencia',
            ha='center', va='center', fontsize=12)
        ax3.axis('off')

    fig.suptitle(titulo, fontsize=16, fontweight='bold', y=0.98)

    buf = io.BytesIO()
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(buf, format='png', dpi=120)
    plt.close(fig)
    buf.seek(0)
    imagen_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    return f'data:image/png;base64,{imagen_base64}'