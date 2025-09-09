from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    ROL_CHOICES = (
        ('USER', 'Usuario'),
        ('ALUMNO', 'Alumno'),
        ('MAESTRO', 'Maestro'),
        ('ADMIN', 'Administrador'),
    )
    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default='USER')
    telefono = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.username} ({self.rol})"

class Alumno(models.Model):
    usuario = models.OneToOneField('Usuario', on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    prefiere_online = models.BooleanField(default=True)
    ciudad = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return f"Alumno: {self.usuario.username}"

class Maestro(models.Model):
    usuario = models.OneToOneField('Usuario', on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    precio_hora = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    online = models.BooleanField(default=True)
    presencial = models.BooleanField(default=False)
    ciudad = models.CharField(max_length=80, blank=True)
    cv = models.FileField(upload_to="cv_maestros/", blank=True, null=True)
    materias = models.ManyToManyField('catalogo.Materia', blank=True, related_name='maestros')

    def __str__(self):
        return f"Maestro: {self.usuario.username}"
