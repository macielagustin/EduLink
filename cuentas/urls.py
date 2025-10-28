from django.urls import path
from .views import (
    home_view,
    registro_persona, elegir_rol, registro_alumno, registro_maestro,
    CustomLoginView, logout_view,
    dashboard_alumno, dashboard_maestro,
    load_departamentos, load_municipios, load_localidades, test_geocoding, buscar_clases, detalle_maestro, perfil_alumno,perfil_publico,
)

from .views import editar_perfil_maestro  # Agrega esta importación
from .views import solicitudes_para_maestro, cambiar_estado_solicitud
from .views import agenda_maestro
from .views import perfil_publico_maestro, perfil_maestro_publico
from .views import mis_solicitudes_alumno, enviar_solicitud_clase
from .views import lista_conversaciones, ver_conversacion, iniciar_conversacion
from .views import proponer_fecha_solicitud, confirmar_fecha_solicitud, generar_qr_pago, agenda_usuario
from .views import debug_eventos

from django.contrib.auth import views as auth_views

from . import views  # Para las notificaciones y otras vistas generales

urlpatterns = [
    path("", home_view, name="home"),

    # Registro y roles
    path("registro/", registro_persona, name="registro_persona"),
    path("elegir-rol/", elegir_rol, name="elegir_rol"),
    path("registro/alumno/", registro_alumno, name="registro_alumno"),
    path("registro/maestro/", registro_maestro, name="registro_maestro"),

    # Rutas AJAX para geolocalización
    path("departamentos/", load_departamentos, name="departamentos"),
    path("municipios/", load_municipios, name="municipios"),
    path("localidades/", load_localidades, name="localidades"),

    # Login y logout
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),

    # Dashboards
    path("alumno/", dashboard_alumno, name="dashboard_alumno"),
    path("maestro/", dashboard_maestro, name="dashboard_maestro"),

    path("test-geocoding/", test_geocoding, name="test_geocoding"),

    #Alumno
    path("alumno/buscar/", buscar_clases, name="buscar_clases"),
    path("alumno/maestro/<int:maestro_id>/", detalle_maestro, name="detalle_maestro"),
    path("alumno/perfil", perfil_alumno, name="perfil_alumno"),
    path("alumno/perfil/publico/", perfil_publico, name="perfil_publico"),


    #Maestro
     # Nueva ruta para editar perfil de maestro
    path("maestro/editar-perfil/", editar_perfil_maestro, name="editar_perfil_maestro"),


     # Solicitudes para maestros
    path("maestro/solicitudes/", views.solicitudes_para_maestro, name="solicitudes_para_maestro"),
    path("maestro/solicitud/<int:solicitud_id>/proponer-fecha/", proponer_fecha_solicitud, name="proponer_fecha_solicitud"),
    path("maestro/solicitud/<int:solicitud_id>/<str:nuevo_estado>/", cambiar_estado_solicitud, name="cambiar_estado_solicitud"),
    


    path("maestro/agenda/", agenda_maestro, name="agenda_maestro"),



    path("maestro/perfil/publico/", perfil_publico_maestro, name="perfil_publico_maestro"),
    path("maestro/<int:maestro_id>/", perfil_maestro_publico, name="perfil_maestro_publico"),


    # Alumno - Solicitudes
    path("alumno/solicitudes/", mis_solicitudes_alumno, name="mis_solicitudes_alumno"),
    path("alumno/solicitar-clase/<int:maestro_id>/", enviar_solicitud_clase, name="enviar_solicitud_clase"),

    # Mensajes
    path("mensajes/", lista_conversaciones, name="lista_conversaciones"),
    path("mensajes/<int:conversacion_id>/", ver_conversacion, name="ver_conversacion"),
    path("mensajes/iniciar/<int:usuario_id>/", iniciar_conversacion, name="iniciar_conversacion"),


    # Notificaciones
    path('notificaciones/', views.obtener_notificaciones, name='obtener_notificaciones'),
    path('notificaciones/<int:notificacion_id>/leida/', views.marcar_notificacion_leida, name='marcar_notificacion_leida'),
    
    # Calendario
    path('maestro/calendario/', views.calendario_maestro, name='calendario_maestro'),
    
    # Reseñas


    # Recuperar Contraseña

    path('password_reset/', views.custom_password_reset, name='password_reset'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Agregar estas rutas a urlpatterns
    path("alumno/solicitud/<int:solicitud_id>/confirmar-fecha/", confirmar_fecha_solicitud, name="confirmar_fecha_solicitud"),
    path("solicitud/<int:solicitud_id>/qr-pago/", generar_qr_pago, name="generar_qr_pago"),
    path("agenda/", agenda_usuario, name="agenda_usuario"),

    # Marcar clase como completada (para maestro)
    path('solicitud/<int:solicitud_id>/completar/', views.marcar_completada, name='marcar_completada'),

    # Dejar reseña (para alumno)
    path('reseñas/<int:solicitud_id>/dejar/', views.dejar_reseña, name='dejar_reseña'),


    # Agregar esta ruta a urlpatterns
    path("agenda/exportar-ics/", views.exportar_calendario_ics, name="exportar_calendario_ics"),



    path("agenda/imprimir/<str:vista>/", views.imprimir_agenda, name="imprimir_agenda"),



    path("debug/eventos/", debug_eventos, name="debug_eventos"),


    # Control de gastos
    path("alumno/gastos/", views.control_gastos_alumno, name="control_gastos_alumno"),
    path("alumno/gastos/maestro/<int:maestro_id>/", views.detalle_gastos_maestro, name="detalle_gastos_maestro"),

]
