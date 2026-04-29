#!/bin/bash

# Crear el directorio de logs si no existe
mkdir -p /var/log

# Crear el archivo de log si no existe
touch /var/log/cron.log

# Añadir las tareas cron al crontab del usuario root
crontab /app/my_cron_jobs

# Mostrar las tareas cron cargadas para verificación
echo "Cron jobs loaded:"
crontab -l

# Iniciar el servicio cron en primer plano
echo "Starting cron service..."
cron -f