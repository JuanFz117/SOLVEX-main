# ANÁLISIS DE IMPACTO TÉCNICO - Refactorización Fat Models, Thin Views

## Resumen de Cambios

Se realizó una refactorización profunda del archivo `views.py` siguiendo el patrón **"Fat Models, Thin Views"** para mejorar la mantenibilidad, testabilidad y rendimiento del código.

---

## 1. Cambios en la Firma de Métodos (Breaking Changes)

### models.py - Nuevos Métodos Clase/Instancia

| Método | Tipo | Uso en Views | Notas |
|--------|------|--------------|-------|
| `Tickets.objects.abiertos_por_usuario(usuario)` | Manager method | `index()` | Reemplaza `filter(Q(id_estado="abierto") \| Q(id_estado="en_progreso"), usuario_id=usuario_actual)` |
| `Tickets.objects.cerrados_por_usuario(usuario)` | Manager method | `tickets_page()` | Reemplaza `filter(usuario_id=usuario_actual, id_estado="cerrado")` |
| `Tickets.objects.con_comentarios()` | Manager method | `ticket_detalle()`, `admin_ticket_detail()` | Usa `prefetch_related` para evitar N+1 |
| `ticket.preparar_datos_para_websocket()` | Instance method | `index()` | Reemplaza diccionario manual de 10 líneas |
| `Tickets.get_opciones_soporte()` | Class method | `index()` | Reemplaza constante hardcoded de 40+ líneas |
| `Ticket_comentarios.crear_comentario(...)` | Class method | N/A (pendiente implementación) | Nuevo método para creación de comentarios |

### properties en Usuario

| Propiedad | Antes | Después |
|-----------|-------|---------|
| `es_colaborador` | Función en views | `@property es_colaborador` en modelo |
| `es_admin_o_superadmin` | Función en views | `@property es_admin_o_superadmin` en modelo |

---

## 2. Efectos Secundarios en el Sistema

### Signals
- **No hay efectos negativos**. Los signals existentes (si los hay) seguirán funcionando igual ya que los métodos del modelo (`save()`, `create()`) no cambiaron su comportamiento.

### Serializers (si existen)
- **Verificar**: Si existen serializers en DRF, deben actualizarse para usar las nuevas constantes:
  - `Tickets.TICKET_ABIERTO_HEADERS`
  - `Tickets.TICKET_CERRADO_HEADERS`
  - `Tickets.TICKET_DETALLE_HEADERS`

### Admin
- **Sin cambios requeridos**. Las clases `ModelAdmin` siguen funcionando como antes.

### Templates
- **Sin cambios en templates**. Los contextos pasados son equivalentes, solo que con mejor organización:
  - `campos_tabla` → `Tickets.TICKET_ABIERTO_HEADERS` (internamente)
  - `tickets_generales2` → `Tickets.TICKET_CERRADO_HEADERS` (internamente)
  - `tickets_generales3` → `Tickets.TICKET_DETALLE_HEADERS` (internamente)

---

## 3. Riesgos de Rendimiento

### Optimizaciones Implementadas ✅

| Optimización | Antes | Después | Impacto |
|--------------|-------|---------|---------|
| select_related | ❌ No usado | ✅ `usuario`, `asignado_a` | -2 queries por ticket |
| prefetch_related | ❌ N+1 | ✅ `Comentarios` | -1 query por ticket en detalle |
| Paginación | 4 items | 4 items | Sin cambio |

### Queries Antes/Después

**Antes (index con 4 tickets):**
```
1. SELECT tickets (abiertos) - 1 query
2. SELECT usuario para cada ticket (N+1) - 4 queries
```

**Después (index con 4 tickets):**
```
1. SELECT tickets LEFT JOIN usuario LEFT JOIN asignado_a - 1 query
```

---

## 4. Riesgos de Integridad de Datos

| Riesgo | Mitigación | Estado |
|--------|------------|--------|
| Cambios en lógica de queries | Se usó `select_related` que no afecta datos | ✅ Bajo riesgo |
| Reordenamiento de imports | No se eliminaron imports críticos | ✅ Seguro |
| Constantes movidas a modelo | Los valores son idénticos | ✅ Sin cambio |

---

## 5. Plan de Pruebas Recomendado

### Tests Unitarios Requeridos

```python
# tests/test_models.py

class TicketsManagerTest(TestCase):
    def test_abiertos_por_usuario_returns_correct_tickets(self):
        """Verifica que solo retorne tickets abiertos/en_progreso."""
        pass
    
    def test_cerrados_por_usuario_returns_correct_tickets(self):
        """Verifica que solo retorne tickets cerrados."""
        pass

    def test_preparar_datos_para_websocket_format(self):
        """Verifica formato de datos WebSocket."""
        pass


class UsuarioPropertiesTest(TestCase):
    def test_es_colaborador_property(self):
        """Verifica la property es_colaborador."""
        pass
    
    def test_es_admin_o_superadmin_property(self):
        """Verifica la property es_admin_o_superadmin."""
        pass


class ViewsTest(TestCase):
    def test_index_uses_optimized_queryset(self):
        """Verifica que index use select_related."""
        pass
    
    def test_ticket_detalle_uses_prefetch(self):
        """Verifica que detalle use prefetch_related."""
        pass
```

### Tests de Integración

1. **Creación de ticket**: Verificar que el WebSocket reciba los datos correctos.
2. **Paginación**: Verificar que la paginación funcione con los nuevos querysets.
3. **Permisos**: Verificar que `es_colaborador` y `es_admin_o_superadmin` funcionen como decoradores.

### Checklist de Verificación Manual

- [ ] Crear ticket y verificar notificación WebSocket
- [ ] Ver lista de tickets abiertos (index)
- [ ] Ver lista de tickets cerrados (tickets_page)
- [ ] Ver detalle de ticket con comentarios
- [ ] Agregar comentario como admin
- [ ] Verificar que los headers de tabla se rendericen correctamente
- [ ] Probar paginación en ambas listas
- [ ] Verificar funcionalidad de "No Aplica" en formulario

---

## 6. Rollback Plan

Si se detecta un problema crítico:

```bash
# Revertir cambios específicos
git checkout HEAD~1 -- apps/tickets/views.py
git checkout HEAD~1 -- apps/tickets/models.py
git checkout HEAD~1 -- apps/usuario/models.py
```

Los cambios son revertibles sin migraciones adicionales ya que:
- No se modificaron los campos del modelo
- Solo se agregaron métodos y constants
- Las claves primarias y relaciones permanecen igual