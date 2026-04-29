from django.core.management.base import BaseCommand
from apps.usuario.email_sengrid import procesar_recordatorios_tickets
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Ejecuta la lógica para procesar y enviar correos de recordatorio de tickets.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando el procesamiento de recordatorios de tickets...'))
        procesar_recordatorios_tickets()
        self.stdout.write(self.style.SUCCESS('Procesamiento de recordatorios de tickets finalizado.'))