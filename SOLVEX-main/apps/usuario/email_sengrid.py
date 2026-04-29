import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from sendgrid import SendGridAPIClient # type: ignore
from sendgrid.helpers.mail import Mail # type: ignore
from apps.tickets.models import Tickets, Ticket_comentarios # Corregida la importación
from django.urls import reverse

logger = logging.getLogger(__name__)

def enviar_correo_recordatorio(destinatario_email, destinatario_nombre, ticket, ultimo_mensaje_relevante, es_para_admin=False):
    """
    Construye y envía un correo de recordatorio usando SendGrid.
    """
    if not settings.SENDGRID_API_KEY:
        logger.error("SENDGRID_API_KEY no configurada en settings.py")
        return False
    
    if not settings.SENDGRID_REMINDER_TEMPLATE_ID:
        logger.error("SENDGRID_REMINDER_TEMPLATE_ID no configurada en settings.py")
        return False

    priority_color_map = {
        'alta': '#d9534f',  # Rojo
        'media': '#f0ad4e', # Naranja/Amarillo
        'baja': '#5cb85c',   # Verde
        None: '#6c757d',     # Gris por defecto
        '': '#6c757d'        # Gris por defecto
    }

    ticket_url = ""
    try:
        if es_para_admin:
            ticket_url = settings.SITE_URL + reverse('tickets:admin_ticket_detail', kwargs={'ticket_id': ticket.id})
        else:
            ticket_url = settings.SITE_URL + reverse('tickets:ticket_detalle', kwargs={'id': ticket.id})
    except Exception as e:
        logger.error(f"Error generando ticket_url para ticket {ticket.id}: {e}")
        ticket_url = settings.SITE_URL # Fallback a la URL base del sitio

    dynamic_template_data = {
        # 'nombre_destinatario': destinatario_nombre, # AUN NO SE AGREGA BIENVENIDA
        'ticket_id': ticket.id,
        'ticket_subject': ticket.motivo,
        'created_date': ticket.fecha_creacion.strftime('%d/%m/%Y %I:%M %p') if ticket.fecha_creacion else 'N/A',
        'priority': ticket.get_id_prioridad_display() if ticket.id_prioridad else 'No asignada',
        'priority_color': priority_color_map.get(ticket.id_prioridad, priority_color_map[None]),
        'ticket_message': ultimo_mensaje_relevante if ultimo_mensaje_relevante else "No hay mensajes recientes del analista.",
        'ticket_url': ticket_url,
    }

    mensaje = Mail(
        from_email=settings.SENDGRID_FROM_EMAIL,
        to_emails=destinatario_email,
    )
    mensaje.template_id = settings.SENDGRID_REMINDER_TEMPLATE_ID
    mensaje.dynamic_template_data = dynamic_template_data

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(mensaje)
        logger.info(f"Correo de recordatorio (plantilla) enviado a {destinatario_email} para ticket {ticket.id}. Status code: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Error al enviar correo de recordatorio (plantilla) a {destinatario_email} para ticket {ticket.id}: {e}", exc_info=True)
        return False

def procesar_recordatorios_tickets():
    """
    Verificar los tickets "En Progreso" Y envia recordatorios si es necesario.
    Esta función debería ser llamada por una tarea programada diariamente.
    """
    print("DEBUG: Iniciando procesar_recordatorios_tickets()")
    ahora = timezone.now()
    # La línea de abajo define el umbral de inactividad.
    limite_tiempo = ahora - timedelta(hours=8) # LIMITE DE 8 HORAS

    tickets_en_progreso = Tickets.objects.filter(id_estado='en_progreso')

    logger.info(f"Procesando recordatorios para {tickets_en_progreso.count()} tickets en progreso.")
    print(f"DEBUG: Tickets en proggreso encontrados: {tickets_en_progreso.count()}")
    
    for ticket in tickets_en_progreso:
        ultima_actividad_fecha = None
        ultimo_comentarista_fue_colaborador = False # PARA SABER A QUIEN NOTIFICAR
        logger.debug(f"Procesando ticket {ticket.id}")

        ultimo_mensaje_texto = "No hay comentarios recientes."

        # OBTENER LOS ÚLTIMOS DOS COMENTARIOS PARA VALIDAR SI ES DEL SISTEMA Y EL CONTEXTO
        comentarios_recientes = Ticket_comentarios.objects.filter(id_ticket=ticket).order_by('-hora_comentario')[:2]

        ultimo_comentario = comentarios_recientes[0] if comentarios_recientes else None
        penultimo_comentario = comentarios_recientes[1] if len(comentarios_recientes) > 1 else None

        if ultimo_comentario:
            ultima_actividad_fecha = ultimo_comentario.hora_comentario
            logger.debug(f"Ticket ID: {ticket.id} - Último comentario encontrado. Fecha: {ultima_actividad_fecha}")
            if ultimo_comentario.autor is None:
                # VALIDAR QUE PERSONA ESCRIBIÓ ANTES DEL MENSAJE DEL SISTEMA
                if penultimo_comentario:
                    if penultimo_comentario.autor == ticket.usuario: #* // EL COLABORADOR ESCRIBIÓ ANTES DEL SISTEMA
                        ultimo_comentarista_fue_colaborador = True #* // EL RECORDATORIO ES PARA EL ADMINISTRADOR
                    elif penultimo_comentario.autor == ticket.asignado_a: #? // EL ADMINISTRADOR ESCRIBIÓ ANTES DEL SISTEMA
                        ultimo_comentarista_fue_colaborador = False #? // EL RECORDATORIO ES PARA EL COLABORADOR
                    else: #? Si el penultimo es default o admin
                        ultimo_comentarista_fue_colaborador = True
                    ultimo_mensaje_texto = penultimo_comentario.detalle_comentario
                else: # SI NO HAY PENULTIMO, SOLO MENSAJE Y DETALLE ORIGINAL
                    ultimo_comentarista_fue_colaborador = True #* // RECORDATORIO PARA EL ADMIN
                    ultimo_mensaje_texto = ticket.detalle
            elif ultimo_comentario.autor == ticket.usuario: #? // EL ULTIMO COMENTARIO ES DEL COLABORADOR
                ultimo_comentarista_fue_colaborador = True
                ultimo_mensaje_texto = ultimo_comentario.detalle_comentario
            elif ultimo_comentario.autor == ticket.asignado_a:
                ultimo_comentarista_fue_colaborador = False
                ultimo_mensaje_texto = ultimo_comentario.detalle_comentario

        # SI NO HAY COMENTARIOS USAR FECHA DE ASIGNACIÓN ( SI EL ADMINISTRADOR LO TOMÓ PERO NO COMENTÓ)
        elif ticket.fecha_asignacion:
            ultima_actividad_fecha = ticket.fecha_asignacion
            logger.debug(f"Ticket ID: {ticket.id} - No hay comentarios, usando fecha_asignacion. Fecha: {ultima_actividad_fecha}")
            # SI EL TOMÓ EL TICKET EL ADMIN DEBERÁ CONTINUAR Y RESPONDER, SI EL ADMIN RESPONDIÓ EL RECORDATORIO ES PARA EL COLABORADOR
            # SI EL ADMINISTRADOR TOMÓ EL CASO PERO NO RESPONDIÓ EL RECORDATORIO ES PARA EL ADMINISTRADOR
            ultimo_comentarista_fue_colaborador = True

        # EN CASO DE NO HABER COMENTARIOS NI FECHA DE ASIGNACIÓN, SE USARÁ LA FECHA DE CREACIÓN
        else:
            ultima_actividad_fecha = ticket.fecha_creacion
            logger.debug(f"Ticket ID: {ticket.id} - No hay comentarios ni fecha_asignacion, usando fecha_creacion. Fecha: {ultima_actividad_fecha}")
            # SI SOLO SE CREÓ Y ESTÁ EN PROCESO EL RECORDATORIO ES PARA EL ADMIN
            ultimo_comentarista_fue_colaborador = True

        logger.debug(f"Ticket ID: {ticket.id} - Última actividad encontrada. Fecha: {ultima_actividad_fecha}")
        logger.debug(f"Ticket ID: {ticket.id} - Limite de tiempo para recordatorio: {limite_tiempo}")

        if ultima_actividad_fecha and ultima_actividad_fecha < limite_tiempo:

            logger.info(f"Ticket ID: {ticket.id} - CALIFICA para recordatorio. Última actividad fue el {ultima_actividad_fecha}, límite: {limite_tiempo}.")
            destinatario_email = None
            destinatario_nombre = None
            es_para_admin = False
            mensaje_para_plantilla = ultimo_mensaje_texto

            if ultimo_comentarista_fue_colaborador:
                # RECORDATORIO PARA EL ADMIN ASIGNADO
                if ticket.asignado_a and ticket.asignado_a.email:
                    destinatario_email = ticket.asignado_a.email
                    #* EL NOMBRE DEL DESTINATARIO ES DEL ADMINISTRADOR
                    destinatario_nombre = ticket.asignado_a.nombre
                    es_para_admin = True
                    # mensaje_para_plantilla = ultimo_mensaje_texto
                    logger.info(f"Ticket {ticket.id}: Recordatorio para admin {destinatario_nombre} enviado a {destinatario_email}. Última actividad del colaborador")
                else:
                    logger.warning(f"Ticket {ticket.id}: Admin asignado no tiene email o no está asignado. No se enviará recordatorio.")
            else:
                # RECORDATORIO PARA EL COLABORADOR
                if ticket.usuario and ticket.usuario.email:
                    destinatario_email = ticket.usuario.email
                    #? EL NOMBRE DEL DESTINATARIO ES DEL COLABORADOR
                    destinatario_nombre = ticket.usuario.nombre
                    es_para_admin = False
                    # mensaje_para_plantilla = ultimo_mensaje_texto
                    logger.info(f"Ticket {ticket.id}: Recordatorio para colaborador {destinatario_nombre} enviado a {destinatario_email}. Última actividad del admin")
                else:
                    logger.warning(f"Ticket {ticket.id}: Usuario creador no tiene email. No se enviará recordatorio.")

            if destinatario_email:
                enviar_correo_recordatorio(
                    destinatario_email,
                    destinatario_nombre,
                    ticket,
                    mensaje_para_plantilla,
                    es_para_admin = es_para_admin
                )
        elif ultima_actividad_fecha:
            # logger.info(f"Ticket {ticket.id}: Última actividad fue el {ultima_actividad_fecha}, dentro del límite de 24 horas.")
            # Ajustar el mensaje de log para reflejar el tiempo de prueba
            logger.info(f"Ticket {ticket.id}: Última actividad ({ultima_actividad_fecha}) es más reciente que el límite ({limite_tiempo}). No se envía recordatorio.")
        else:
            logger.warning(f"Ticket {ticket.id}: No se puede determinar la fecha de última actividad")
