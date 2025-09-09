from django.urls import path
from .views import (
    home_view,
    registro_persona, elegir_rol, registro_alumno, registro_maestro,
    CustomLoginView, logout_view,
    dashboard_alumno, dashboard_maestro
)

urlpatterns = [
    path("", home_view, name="home"),

    path("registro/", registro_persona, name="registro_persona"),
    path("elegir-rol/", elegir_rol, name="elegir_rol"),
    path("registro/alumno/", registro_alumno, name="registro_alumno"),
    path("registro/maestro/", registro_maestro, name="registro_maestro"),

    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),

    path("alumno/", dashboard_alumno, name="dashboard_alumno"),
    path("maestro/", dashboard_maestro, name="dashboard_maestro"),
]
