# consumers.py
import json
import logging
import base64 
from channels.generic.websocket import AsyncWebsocketConsumer # type: ignore
from channels.db import database_sync_to_async # type: ignore
from django.core.files.base import ContentFile 
 
# IMPORTAR MODELOS
from apps.tickets.models import Tickets, Ticket_comentarios

logger = logging.getLogger(__name__)

class TicketChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            # Obtener ID del ticket desde la URL
            self.ticket_id = self.scope['url_route']['kwargs']['ticket_id']
            self.room_group_name = f'ticket_{self.ticket_id}'
            user = self.scope["user"]
        
            # Verificar autenticación
            if not user.is_authenticated:
                logger.warning(f"Intento de conexión no autenticado al ticket {self.ticket_id}")
                await self.close()
                return
            
            ticket_accessible = await self.check_ticket_access(self.ticket_id, user)
            if not ticket_accessible:
                logger.warning(f"CONEXIÓN RECHAZADA: Acceso denegado para ticket {self.ticket_id} a usuario {user.username}")
                await self.close()
                return
            
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            logger.info(f"Usuario {user.username} conectado al chat del ticket {self.ticket_id}. Grupo: {self.room_group_name}, Canal: {self.channel_name}")
        except Exception as e:
            logger.error(f"ERROR CRÍTICO en connect() para ticket {self.ticket_id}, usuario {self.scope.get('user', 'N/A')}: {e}", exc_info=True)
            await self.close(code=4001) 

    async def disconnect(self, close_code):
        try:
            # Salir del grupo
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"Usuario {self.scope['user'].username} desconectado del ticket {self.ticket_id}. Código: {close_code}")
        except Exception as e:
            logger.error(f"Error en disconnect() para ticket {self.ticket_id}: {e}", exc_info=True)

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get('message', '').strip()
            attachment_base64 = text_data_json.get('attachment')
            attachment_name = text_data_json.get('attachment_name')
            attachment_type = text_data_json.get('attachment_type')
            
            if not message and not attachment_base64:
                await self.send(text_data=json.dumps({
                    'error': 'El mensaje o el adjunto no pueden estar vacíos.'
                }))
                return

            # Validar longitud del mensaje
            if message and len(message) > 1000:
                await self.send(text_data=json.dumps({
                    'error': 'El mensaje es demasiado largo (máximo 1000 caracteres)'
                }))
                return

            # Guardar comentario
            comentario_data = await self.save_comment(
                ticket_id=self.ticket_id,
                user=self.scope["user"],
                message=message,
                attachment_base64=attachment_base64,
                attachment_name=attachment_name,
                attachment_type=attachment_type
            )

            if comentario_data:
                attachment_url = None
                attachment_display_name = None
                if comentario_data.adjunto:
                    attachment_url = comentario_data.adjunto.url
                    attachment_display_name = comentario_data.adjunto.name.split('/')[-1]

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message_data': {
                            'message': comentario_data.detalle_comentario,
                            'author': self.scope["user"].username,
                            'timestamp': comentario_data.hora_comentario.isoformat(),
                            'comment_id': comentario_data.id_comment,
                            'is_system': False,
                            'attachment_url': attachment_url,
                            'attachment_name': attachment_display_name
                        }
                    }
                )
            else:
                await self.send(text_data=json.dumps({
                    'error': 'Error al guardar el comentario'
                }))

        except json.JSONDecodeError:
            logger.warning(f"Error de decodificación JSON en receive para ticket {self.ticket_id}: {text_data}", exc_info=True)
            await self.send(text_data=json.dumps({'error': 'Formato de mensaje inválido'}))
        except Exception as e:
            logger.error(f"Error CRÍTICO en receive() para ticket {self.ticket_id}: {e}", exc_info=True)
            await self.send(text_data=json.dumps({'error': 'Error interno del servidor procesando su mensaje'}))

    async def chat_message(self, event):
        message_data = event['message_data']
        try:
            logger.debug(f"Enviando chat_message al cliente {self.channel_name} para ticket {self.ticket_id}: {event}")
            await self.send(text_data=json.dumps({
                'message': message_data['message'],
                'author': message_data['author'],
                'timestamp': message_data['timestamp'],
                'comment_id': message_data.get('comment_id'),
                'is_system': message_data.get('is_system', False),
                'attachment_url': message_data.get('attachment_url'),
                'attachment_name': message_data.get('attachment_name')
            }))
        except Exception as e:
            logger.error(f"Error CRÍTICO en chat_message() para ticket {self.ticket_id}, evento {event}: {e}", exc_info=True)
            
    async def ticket_status_update(self, event):
        try:
            logger.debug(f"CONSUMER {self.channel_name}: Recibido evento en ticket_status_update: {event}")
            json_payload = json.dumps(event)
            logger.debug(f"CONSUMER {self.channel_name}: Payload serializado correctamente. Enviando al cliente.")
            await self.send(text_data=json_payload)
            logger.info(f"CONSUMER {self.channel_name}: Actualización de estado enviada para ticket {self.ticket_id}")
        except Exception as e:
            logger.error(
                f"CONSUMER {self.channel_name}: ERROR CRÍTICO en ticket_status_update() para ticket {self.ticket_id}. "
                f"Error: {e}", exc_info=True
            )
            await self.close(code=4005)
            
    @database_sync_to_async
    def check_ticket_access(self, ticket_id, user):
        """
        Verifica si un usuario tiene permiso para acceder al chat de un ticket.
        """
        try:
            ticket = Tickets.objects.select_related('usuario', 'asignado_a').get(id=ticket_id)

            is_ticket_creator = (ticket.usuario and ticket.usuario.id == user.id)
            is_assigned_to_user = (ticket.asignado_a and ticket.asignado_a.id == user.id)
            
            is_admin_or_super = user.es_admin_o_superadmin

            if is_ticket_creator or is_assigned_to_user or is_admin_or_super:
                logger.info(f"Acceso PERMITIDO para ticket {ticket_id} a usuario {user.username} (Creador: {is_ticket_creator}, Asignado: {is_assigned_to_user}, Admin: {is_admin_or_super})")
                return True
            else:
                logger.warning(f"Acceso DENEGADO para ticket {ticket_id} a usuario {user.username}")
                return False

        except Tickets.DoesNotExist:
            logger.warning(f"Intento de acceso a ticket inexistente {ticket_id} por usuario {user.username}")
            return False
        except Exception as e:
            logger.error(f"Error en check_ticket_access para ticket {ticket_id}, usuario {user.username}: {e}", exc_info=True)
            return False

    @database_sync_to_async
    def save_comment(self, ticket_id, user, message, attachment_base64=None, attachment_name=None, attachment_type=None):
        """Guardar comentario y adjunto en la base de datos"""
        comentario_obj = None
        try:
            ticket = Tickets.objects.get(id=ticket_id)
            comentario_obj = Ticket_comentarios.crear_comentario(
                ticket=ticket,
                autor=user,
                detalle_comentario=message
            )

            logger.info(f"Comentario guardado ID:{comentario_obj.id_comment} para ticket {ticket_id} por usuario {user.username}")

        except Tickets.DoesNotExist:
            logger.error(f"Ticket con id {ticket_id} no encontrado al intentar guardar comentario.")
            return None
        except Exception as e:
            logger.error(f"Error al crear Comentario para ticket {ticket_id}: {e}", exc_info=True)
            return None

        if comentario_obj and attachment_base64 and attachment_name:
            try:
                if ';base64,' in attachment_base64:
                    _format, _img_str = attachment_base64.split(';base64,')
                else:
                    _img_str = attachment_base64
                
                file_content = base64.b64decode(_img_str)
                django_file = ContentFile(file_content, name=attachment_name)
                comentario_obj.adjunto.save(attachment_name, django_file, save=True)
                logger.info(f"Adjunto guardado para comentario ID:{comentario_obj.id_comment}")
            except Exception as file_save_e:
                logger.error(f"Error al guardar adjunto para comentario ID:{comentario_obj.id_comment}: {file_save_e}", exc_info=True)

        return comentario_obj


class AdminDashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated or not self.user.es_admin_o_superadmin:
            logger.warning(f"Conexión Websocket rechazada para dashboard admin: Usuario no autenticado o sin permisos ({self.user.username})")
            await self.close()
            return
        
        self.room_group_name = 'admin_dashboard_general'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        logger.info(f"Admin {self.user.username} conectado al dashboard Websocket. Grupo: {self.room_group_name}")
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        logger.info(f"Admin {self.user.username if self.user.is_authenticated else 'N/A'} desconectado del dashboard Websocket. Código: {close_code}")

    async def new_ticket_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_ticket',
            'ticket': event['ticket_data']
        }))
        logger.info(f"Enviando new_ticket_notification al admin {self.user.username}: Ticket ID {event['ticket_data']['id']}")