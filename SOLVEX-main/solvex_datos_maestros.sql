-- ==============================================================================
-- SOLVEX - Scripts de inserción de datos para tablas maestras
-- Ejecutar DESPUÉS de correr: python manage.py migrate
-- Base de datos: MySQL / MariaDB
-- ==============================================================================


-- ==============================================================================
-- 1. TIPOS DE SOPORTE
-- ==============================================================================
-- Debe coincidir con el campo 'categoria' del modelo Usuario
-- para que el filtro del dashboard del admin funcione correctamente.
-- ==============================================================================
INSERT INTO tickets_tiposoporte (nombre) VALUES
('Soporte Técnico'),
('Soporte Operativo'),
('Área de Desarrollo');


-- ==============================================================================
-- 2. AGENCIAS Y CORRESPONSALES
-- ==============================================================================
INSERT INTO tickets_agenciacorresponsal (nombre, activo) VALUES
('No Aplica', 1),
('Agencia Principal', 1),
('Agencia Popular', 1),
('Agencia Catama', 1),
('Agencia Porfía', 1),
('Agencia Montecarlo', 1),
('Agencia Acacías', 1),
('Agencia Vistahermosa', 1),
('Agencia Guayabetal', 1),
('Agencia Barranca de Upía', 1),
('Agencia Cabuyaro', 1),
('Agencia Puerto Gaitán', 1),
('Corresponsal Puerto López', 1),
('Corresponsal El Castillo', 1),
('Corresponsal Lejanías', 1),
('Corresponsal Puerto Lleras', 1),
('Corresponsal Puerto Rico', 1),
('Corresponsal Cumaral', 1),
('Corresponsal Mesetas', 1),
('Corresponsal Uribe', 1),
('Corresponsal Yopal', 1),
('Corresponsal Villanueva', 1);


-- ==============================================================================
-- 3. ÁREAS ADMINISTRATIVAS
-- ==============================================================================
INSERT INTO tickets_areaadministrativa (nombre, activo) VALUES
('No Aplica', 1),
('Gerencia General', 1),
('Gerencia Innovación y Transformación', 1),
('Gerencia Comercial', 1),
('Oficial de Cumplimiento', 1),
('Oficial de Riesgo', 1),
('Servicios Administrativos', 1),
('Talento Humano', 1),
('Operaciones', 1),
('Contabilidad', 1),
('Revisoría', 1),
('Auditoria', 1),
('Credito', 1),
('Cartera', 1),
('Cobranza', 1),
('Garantías', 1),
('Comunicaciones', 1),
('Convenios', 1),
('Canales', 1);


-- ==============================================================================
-- 4. MOTIVOS DE CIERRE
-- ==============================================================================
INSERT INTO tickets_motivocierre (codigo, nombre) VALUES
('resuelto', 'Resuelto'),
('error_aplicativo', 'Error de aplicativo'),
('error_usuario', 'Error de usuario'),
('falta_capacitacion', 'Falta de capacitación'),
('duplicado', 'Ticket duplicado'),
('no_corresponde', 'No corresponde a esta área');


-- ==============================================================================
-- 5. ESTADOS DE TICKET
-- ==============================================================================
INSERT INTO tickets_ticket_estado (id_estado, nombre) VALUES
('abierto', 'Abierto'),
('en_progreso', 'En Progreso'),
('cerrado', 'Cerrado');


-- ==============================================================================
-- 6. PRIORIDADES DE TICKET
-- ==============================================================================
INSERT INTO tickets_ticket_prioridad (id_prioridad, nombre) VALUES
('alta', 'Alta'),
('media', 'Media'),
('baja', 'Baja');


-- ==============================================================================
-- VERIFICACIÓN - Ejecutar para confirmar que los datos se insertaron correctamente
-- ==============================================================================
SELECT 'TipoSoporte' as tabla, COUNT(*) as registros FROM tickets_tiposoporte
UNION ALL
SELECT 'AgenciaCorresponsal', COUNT(*) FROM tickets_agenciacorresponsal
UNION ALL
SELECT 'AreaAdministrativa', COUNT(*) FROM tickets_areaadministrativa
UNION ALL
SELECT 'MotivoCierre', COUNT(*) FROM tickets_motivocierre
UNION ALL
SELECT 'Ticket_estado', COUNT(*) FROM tickets_ticket_estado
UNION ALL
SELECT 'Ticket_prioridad', COUNT(*) FROM tickets_ticket_prioridad;
