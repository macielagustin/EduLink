from django.urls import path
from .views import (
    home_view,
    registro_persona, elegir_rol, registro_alumno, registro_maestro,
    CustomLoginView, logout_view,
    dashboard_alumno, dashboard_maestro,
    load_departamentos, load_municipios, load_localidades, test_geocoding, buscar_clases, detalle_maestro, perfil_alumno,perfil_publico,
)

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

]
