from django.core.management.base import BaseCommand
from apps.usuario.email_sengrid import procesar_recordatorios_tickets
import logging
# -------------------------------------------------------------------#
# En el shell de Django
from apps.tickets.models import Ticket_comentarios
from django.utils import timezone
from datetime import timedelta


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Ejecuta manualmente el proceso de envío de correos de recordatorio para tickets.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Preparando datos para la prueba...'))
        try:
            # Reemplaza ID_DEL_TICKET con el ID real o hazlo configurable
            id_ticket_prueba = 1 
            ultimo_comentario_sistema = Ticket_comentarios.objects.filter(id_ticket=id_ticket_prueba, autor__isnull=True).latest('hora_comentario')
            self.stdout.write(f"Comentario original: {ultimo_comentario_sistema.detalle_comentario} - Hora: {ultimo_comentario_sistema.hora_comentario}")
            # Establece la hora del comentario a 10 minutos en el pasado para dar más margen
            ultimo_comentario_sistema.hora_comentario = timezone.now() - timedelta(minutes=10)
            ultimo_comentario_sistema.save(update_fields=['hora_comentario'])
            self.stdout.write(self.style.SUCCESS(f"Nueva hora del comentario para el ticket {id_ticket_prueba}: {ultimo_comentario_sistema.hora_comentario}"))
        except Ticket_comentarios.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'No se encontró el último comentario del sistema para el ticket ID {id_ticket_prueba}. Asegúrate de que exista.'))
            return # No continuar si la preparación falla
        except Exception as e:
            logger.error(f"Error durante la preparación de datos en enviar_recordatorios_test: {e}", exc_info=True)
            self.stderr.write(self.style.ERROR(f'Error durante la preparación de datos: {e}'))
            return # No continuar si la preparación falla

        self.stdout.write(self.style.SUCCESS('Iniciando prueba de envío de recordatorios...'))
        try:
            procesar_recordatorios_tickets()
            self.stdout.write(self.style.SUCCESS('Prueba de envío de recordatorios finalizada.'))
        except Exception as e:
            logger.error(f"Error durante la ejecución del comando enviar_recordatorios_test: {e}", exc_info=True)
            self.stderr.write(self.style.ERROR(f'Error durante la prueba: {e}'))
