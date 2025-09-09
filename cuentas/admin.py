from django.contrib import admin
from .models import Usuario, Alumno, Maestro

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "rol", "is_active", "is_staff", "date_joined")
    search_fields = ("username", "email")
    list_filter = ("rol", "is_staff", "is_superuser", "is_active")

@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "ciudad", "prefiere_online")
    search_fields = ("usuario__username", "ciudad")

@admin.register(Maestro)
class MaestroAdmin(admin.ModelAdmin):
    list_display = ("usuario", "ciudad", "online", "presencial", "precio_hora")
    search_fields = ("usuario__username", "ciudad")
    filter_horizontal = ("materias",)

