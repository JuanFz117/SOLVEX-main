import csv
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

class Command(BaseCommand):
    help = 'Importar Usuarios apartir de un archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file.')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        User = get_user_model()
        
        # Obtener los roles válidos directamente del modelo para evitar errores
        valid_roles = {choice[0] for choice in User.ROLE_CHOICES}
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                created_count = 0
                skipped_count = 0
                
                for i, row in enumerate(reader, 1):
                    username = row.get('username')
                    password = row.get('password')
                    email = row.get('email')
                    rol = row.get('rol')
                    id_usuario = row.get('id_usuario')
                    nombre = row.get('nombre')
                    cargo = row.get('cargo')
                    area_agencia = row.get('area_agencia')

                    # Validación de campos obligatorios
                    required_fields = [username, password, email, rol, id_usuario, nombre, cargo, area_agencia]
                    if not all(required_fields):
                        self.stdout.write(self.style.WARNING(f"Fila {i}: Saltando. Faltan datos obligatorios. Fila: {row}"))
                        skipped_count += 1
                        continue

                    # Validación del rol
                    if rol not in valid_roles:
                        self.stdout.write(self.style.WARNING(f"Fila {i}: Saltando. Rol '{rol}' no es válido. Roles válidos: {', '.join(valid_roles)}"))
                        skipped_count += 1
                        continue

                    try:
                        # Validación de unicidad
                        if User.objects.filter(username=username).exists():
                            self.stdout.write(self.style.WARNING(f"Fila {i}: Saltando. El nombre de usuario '{username}' ya existe."))
                            skipped_count += 1
                            continue
                        if User.objects.filter(email=email).exists():
                            self.stdout.write(self.style.WARNING(f"Fila {i}: Saltando. El email '{email}' ya existe."))
                            skipped_count += 1
                            continue
                        if User.objects.filter(id_usuario=id_usuario).exists():
                            self.stdout.write(self.style.WARNING(f"Fila {i}: Saltando. El ID (cédula) '{id_usuario}' ya existe."))
                            skipped_count += 1
                            continue
                        
                        # Crear el usuario con todos los campos
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            password=password,
                            rol=rol,
                            id_usuario=id_usuario,
                            nombre=nombre,
                            cargo=cargo,
                            area_agencia=area_agencia,
                            # Forzar cambio de contraseña en el primer login
                            debe_cambiar_contrasena=True
                        )
                        self.stdout.write(self.style.SUCCESS(f"Fila {i}: Usuario '{user.username}' creado exitosamente."))
                        created_count += 1
                    
                    except ValidationError as e:
                        self.stdout.write(self.style.ERROR(f"Fila {i}: Error de validación al crear usuario {username}: {e.messages}"))
                        skipped_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Fila {i}: Error inesperado al crear usuario {username}: {e}"))
                        skipped_count += 1
            
            self.stdout.write(self.style.SUCCESS(f"\n--- Resumen de Importación ---"))
            self.stdout.write(self.style.SUCCESS(f"Usuarios creados: {created_count}"))
            self.stdout.write(self.style.WARNING(f"Filas saltadas (datos duplicados, inválidos o faltantes): {skipped_count}"))

        except FileNotFoundError:
            raise CommandError(f'El archivo "{csv_file_path}" no fue encontrado.')
        except Exception as e:
            raise CommandError(f'Ocurrió un error al procesar el archivo: {e}')