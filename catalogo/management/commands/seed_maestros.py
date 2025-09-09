from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from cuentas.models import Usuario, Maestro
from catalogo.models import Materia
import random

class Command(BaseCommand):
    help = "Crea usuarios Maestro de prueba con materias y precios"

    def handle(self, *args, **options):
        # Materias base (si no existen, las crea)
        materias_base = ["Matemática", "Inglés", "Programación", "Historia", "Física"]
        materias_objs = []
        for m in materias_base:
            obj, _ = Materia.objects.get_or_create(nombre=m)
            materias_objs.append(obj)

        # Lista de nombres de prueba
        nombres = [
            ("profe_mate", "Matías Pérez", "Catamarca"),
            ("profe_ingles", "Lucía Gómez", "Córdoba"),
            ("profe_prog", "Carlos López", "Buenos Aires"),
            ("profe_hist", "Mariana Díaz", "Mendoza"),
            ("profe_fis", "Jorge Sánchez", "Salta"),
        ]

        for username, nombre, ciudad in nombres:
            if Usuario.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f"Usuario {username} ya existe"))
                continue

            # Crear usuario
            u = Usuario.objects.create(
                username=username,
                email=f"{username}@edulink.com",
                password=make_password("12345678"),  # clave fija
                rol="MAESTRO",
            )

            # Crear perfil Maestro
            m = Maestro.objects.create(
                usuario=u,
                bio=f"Soy {nombre}, doy clases de {random.choice(materias_base)}.",
                precio_hora=random.randint(800, 2000),
                online=random.choice([True, False]),
                presencial=random.choice([True, False]),
                ciudad=ciudad,
            )

            # Asignar materias random
            m.materias.set(random.sample(materias_objs, k=random.randint(1, 3)))

            self.stdout.write(self.style.SUCCESS(f"Maestro creado: {username}"))

        self.stdout.write(self.style.SUCCESS("Seed finalizado"))
