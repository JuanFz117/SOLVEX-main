"""
Tests para validar la refactorización Fat Models, Thin Views.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.tickets.models import Tickets, Ticket_prioridad, Ticket_comentarios

Usuario = get_user_model()


class TicketsManagerTest(TestCase):
    """Tests para el manager personalizado de Tickets."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='test_user',
            id_usuario=12345,
            password='testpass',
            rol=Usuario.ROLE_COLABORADOR
        )
        self.admin = Usuario.objects.create_user(
            username='admin_user',
            id_usuario=54321,
            password='adminpass',
            rol=Usuario.ROLE_ADMIN
        )
        # Crear tickets de prueba
        self.ticket_abierto = Tickets.objects.create(
            usuario=self.usuario,
            motivo='Ticket abierto',
            tipo_soporte='Soporte Técnico',
            agencia_corresponsal='No Aplica',
            administrativa='Gerencia General',
            detalle='Detalle del ticket',
            id_estado='abierto'
        )
        self.ticket_en_progreso = Tickets.objects.create(
            usuario=self.usuario,
            motivo='Ticket en progreso',
            tipo_soporte='Soporte Operativo',
            agencia_corresponsal='No Aplica',
            administrativa='Talento Humano',
            detalle='Detalle 2',
            id_estado='en_progreso'
        )
        self.ticket_cerrado = Tickets.objects.create(
            usuario=self.usuario,
            motivo='Ticket cerrado',
            tipo_soporte='Área de Desarrollo',
            agencia_corresponsal='No Aplica',
            administrativa='No Aplica',
            detalle='Detalle 3',
            id_estado='cerrado'
        )
        # Ticket de otro usuario
        self.otro_usuario = Usuario.objects.create_user(
            username='otro_user',
            id_usuario=99999,
            password='pass',
            rol=Usuario.ROLE_COLABORADOR
        )
        self.ticket_otro_usuario = Tickets.objects.create(
            usuario=self.otro_usuario,
            motivo='Ticket de otro usuario',
            tipo_soporte='Soporte Técnico',
            agencia_corresponsal='No Aplica',
            administrativa='No Aplica',
            detalle='Detalle',
            id_estado='abierto'
        )

    def test_abiertos_por_usuario_returns_correct_tickets(self):
        """Verifica que abiertos_por_usuario retorne solo tickets abiertos/en_progreso del usuario."""
        abiertos = Tickets.objects.abiertos_por_usuario(self.usuario)
        ids = list(abiertos.values_list('id', flat=True))
        self.assertIn(self.ticket_abierto.id, ids)
        self.assertIn(self.ticket_en_progreso.id, ids)
        self.assertNotIn(self.ticket_cerrado.id, ids)
        self.assertNotIn(self.ticket_otro_usuario.id, ids)

    def test_cerrados_por_usuario_returns_correct_tickets(self):
        """Verifica que cerrados_por_usuario retorne solo tickets cerrados del usuario."""
        cerrados = Tickets.objects.cerrados_por_usuario(self.usuario)
        ids = list(cerrados.values_list('id', flat=True))
        self.assertIn(self.ticket_cerrado.id, ids)
        self.assertNotIn(self.ticket_abierto.id, ids)
        self.assertNotIn(self.ticket_en_progreso.id, ids)

    def test_con_comentarios_uses_prefetch(self):
        """Verifica que con_comentarios use prefetch_related."""
        from django.db.models.query import Prefetch
        qs = Tickets.objects.con_comentarios()
        # Verificar que prefetch_related está en el queryset
        self.assertIsNotNone(qs.query.prefetch_related)

    def test_select_related_in_manager(self):
        """Verifica que get_queryset use select_related."""
        qs = Tickets.objects.all()
        # select_related debería incluir usuario y asignado_a
        self.assertIn('usuario', str(qs.query))


class TicketsModelMethodsTest(TestCase):
    """Tests para métodos de instancia del modelo Tickets."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='test_user',
            id_usuario=12345,
            password='testpass'
        )
        self.ticket = Tickets.objects.create(
            usuario=self.usuario,
            motivo='Test ticket',
            tipo_soporte='Soporte Técnico',
            agencia_corresponsal='No Aplica',
            administrativa='No Aplica',
            detalle='Detalle'
        )

    def test_preparar_datos_para_websocket_returns_dict(self):
        """Verifica que preparar_datos_para_websocket retorne un diccionario con las claves correctas."""
        data = self.ticket.preparar_datos_para_websocket()
        required_keys = [
            'id', 'motivo', 'usuario_username', 'tipo_soporte',
            'estado_display', 'estado_value', 'prioridad_display',
            'prioridad_value', 'fecha_creacion', 'url_detalle_admin'
        ]
        for key in required_keys:
            self.assertIn(key, data)

    def test_get_opciones_soporte_returns_correct_structure(self):
        """Verifica que get_opciones_soporte retorne el formato correcto."""
        opciones = Tickets.get_opciones_soporte()
        self.assertIn('Tipo_de_Soporte', opciones)
        self.assertIn('Agencia_Corresponsal', opciones)
        self.assertIn('Administrativa', opciones)

    def test_constants_exist(self):
        """Verifica que existen las constantes de headers."""
        self.assertEqual(
            Tickets.TICKET_ABIERTO_HEADERS,
            ['ID', 'Motivo', 'Tipo de Soporte', 'Estado', 'Prioridad', 'Fecha de Creación']
        )
        self.assertEqual(
            Tickets.TICKET_CERRADO_HEADERS,
            ['ID', 'Motivo', 'Tipo de Soporte', 'Estado', 'Fecha de Creación', 'Fecha de Solución']
        )
        self.assertEqual(
            Tickets.TICKET_DETALLE_HEADERS,
            ['ID', 'Tipo de Soporte', 'Area reportada', 'Estado', 'Prioridad', 'Fecha de Creación']
        )


class UsuarioPropertiesTest(TestCase):
    """Tests para las properties del modelo Usuario."""

    def test_es_colaborador_property(self):
        """Verifica la property es_colaborador."""
        colaborador = Usuario.objects.create_user(
            username='colab',
            id_usuario=1,
            password='pass',
            rol=Usuario.ROLE_COLABORADOR
        )
        self.assertTrue(colaborador.es_colaborador)

    def test_es_admin_o_superadmin_property(self):
        """Verifica la property es_admin_o_superadmin para admin."""
        admin = Usuario.objects.create_user(
            username='admin',
            id_usuario=2,
            password='pass',
            rol=Usuario.ROLE_ADMIN
        )
        self.assertTrue(admin.es_admin_o_superadmin)

    def test_es_superadmin_property(self):
        """Verifica la property es_superadmin_tipo."""
        superadmin = Usuario.objects.create_user(
            username='superadmin',
            id_usuario=3,
            password='pass',
            rol=Usuario.ROLE_SUPERADMIN
        )
        self.assertTrue(superadmin.es_superadmin_tipo)
        self.assertTrue(superadmin.es_admin_tipo)

    def test_no_es_admin_colaborador(self):
        """Verifica que colaborador no sea admin."""
        colaborador = Usuario.objects.create_user(
            username='colab',
            id_usuario=4,
            password='pass',
            rol=Usuario.ROLE_COLABORADOR
        )
        self.assertFalse(colaborador.es_admin_o_superadmin)
        self.assertFalse(colaborador.es_admin_tipo)
        self.assertFalse(colaborador.es_superadmin_tipo)


class TicketComentariosMethodsTest(TestCase):
    """Tests para métodos del modelo Ticket_comentarios."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='test_user',
            id_usuario=12345,
            password='testpass'
        )
        self.ticket = Tickets.objects.create(
            usuario=self.usuario,
            motivo='Test',
            tipo_soporte='Soporte Técnico',
            agencia_corresponsal='No Aplica',
            administrativa='No Aplica',
            detalle='Detalle'
        )

    def test_crear_comentario_creates_comment(self):
        """Verifica que crear_comentario cree un comentario."""
        comentario = Ticket_comentarios.crear_comentario(
            ticket=self.ticket,
            autor=self.usuario,
            detalle_comentario='Test comment'
        )
        self.assertEqual(comentario.id_ticket, self.ticket)
        self.assertEqual(comentario.autor, self.usuario)
        self.assertEqual(comentario.detalle_comentario, 'Test comment')

    def test_puede_ser_editado_por_returns_correct_boolean(self):
        """Verifica que puede_ser_editado_por funcione correctamente."""
        comentario = Ticket_comentarios.objects.create(
            id_ticket=self.ticket,
            autor=self.usuario,
            detalle_comentario='Test'
        )
        self.assertTrue(comentario.puede_ser_editado_por(self.usuario))
        otro_usuario = Usuario.objects.create_user(
            username='otro',
            id_usuario=999,
            password='pass'
        )
        self.assertFalse(comentario.puede_ser_editado_por(otro_usuario))