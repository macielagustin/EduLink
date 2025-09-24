from django.contrib.auth.models import AbstractUser
from django.db import models

# 🔹 Si ya tenés modelos Provincia/Departamento/Municipio/Localidad definidos en otra app, importa desde allí.
# from ubicaciones.models import Provincia, Departamento, Municipio, Localidad


class Usuario(AbstractUser):
    ROL_CHOICES = (
        ('USER', 'Usuario'),
        ('ALUMNO', 'Alumno'),
        ('MAESTRO', 'Maestro'),
        ('ADMIN', 'Administrador'),
    )

    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default='USER')
    telefono = models.CharField(max_length=30, blank=True)

    nombre = models.CharField(max_length=50, blank=False)
    apellido = models.CharField(max_length=50, blank=False)

    # Campos adicionales de tu amigo
    fecha_nacimiento = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True)  # unifica con "descripcion"
    ciudad = models.CharField(max_length=80, blank=True)  # mantenemos compatibilidad
    verificado = models.BooleanField(default=False)
    foto_perfil = models.ImageField(upload_to='perfiles/', null=True, blank=True)

    # Geolocalización (usa FK a tablas auxiliares si existen)
    provincia = models.ForeignKey("Provincia", on_delete=models.SET_NULL, null=True, blank=True)
    departamento = models.ForeignKey("Departamento", on_delete=models.SET_NULL, null=True, blank=True)
    municipio = models.ForeignKey("Municipio", on_delete=models.SET_NULL, null=True, blank=True)
    localidad = models.ForeignKey("Localidad", on_delete=models.SET_NULL, null=True, blank=True)
    calle = models.CharField(max_length=255, blank=True)
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)

    # Automáticos
    fecha_creacion = models.DateTimeField(auto_now_add=True)  # similar a date_joined
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.rol})"


class Alumno(models.Model):
    usuario = models.OneToOneField('Usuario', on_delete=models.CASCADE)
    nivel_educativo = models.ForeignKey('NivelEducativo', on_delete=models.SET_NULL, null=True, blank=True)
    materias_interes = models.ManyToManyField('catalogo.Materia', blank=True, related_name='alumnos')
    objetivo = models.TextField(blank=True, null=True)
    disponibilidad = models.ManyToManyField('Disponibilidad', blank=True, related_name='alumnos')
    prefiere_online = models.BooleanField(default=True)

    def __str__(self):
        return f"Alumno: {self.usuario.username}"


class Maestro(models.Model):
    usuario = models.OneToOneField('Usuario', on_delete=models.CASCADE)
    precio_hora = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    modalidad = models.CharField(
        max_length=20,
        choices=[
            ("Online", "Online"),
            ("Presencial", "Presencial"),
            ("Ambos", "Ambos"),
        ],
        default="Online",
    )
    descripcion = models.TextField(blank=True, null=True)
    cv = models.FileField(upload_to="cv_maestros/", blank=True, null=True)
    materias = models.ManyToManyField('catalogo.Materia', blank=True, related_name='maestros')
    idiomas = models.ManyToManyField('Idioma', blank=True, related_name='maestros')

    def __str__(self):
        return f"Maestro: {self.usuario.username}"


# Tabla de idiomas
class Idioma(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


# Tabla de niveles educativos (opcional, si no querés usar choices)
class NivelEducativo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


# Tabla de disponibilidades horarias (opcional, si no querés usar choices)
class Disponibilidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre



class Provincia(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Departamento(models.Model):
    nombre = models.CharField(max_length=100)
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre

class Municipio(models.Model):
    nombre = models.CharField(max_length=100)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre

class Localidad(models.Model):
    nombre = models.CharField(max_length=100)
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre

