from django.contrib import admin
from .models import Usuario, Alumno, Maestro, Provincia, Departamento, Municipio, Localidad

@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'provincia')
    list_filter = ('provincia',)
    search_fields = ('nombre', 'provincia__nombre')

@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'departamento')
    list_filter = ('departamento__provincia', 'departamento')
    search_fields = ('nombre', 'departamento__nombre')

@admin.register(Localidad)
class LocalidadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'municipio')
    list_filter = ('municipio__departamento__provincia', 'municipio__departamento', 'municipio')
    search_fields = ('nombre', 'municipio__nombre')

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "rol", "is_active", "is_staff", "date_joined")
    search_fields = ("username", "email")
    list_filter = ("rol", "is_staff", "is_superuser", "is_active", "provincia")
    readonly_fields = ('fecha_creacion', 'ultima_actualizacion')

@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "prefiere_online")
    search_fields = ("usuario__username",)

@admin.register(Maestro)
class MaestroAdmin(admin.ModelAdmin):
    list_display = ("usuario", "online", "presencial", "precio_hora")
    search_fields = ("usuario__username",)
    filter_horizontal = ("materias",)


