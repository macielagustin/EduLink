from django.urls import path
from django.http import HttpResponse
from .views import maestros_list, maestro_detalle

def ping(_):
    return HttpResponse("EduLink OK - catalogo")

urlpatterns = [
    path("ping/", ping, name="catalogo_ping"),
    path("maestros/", maestros_list, name="maestros_list"),
    path("maestros/<int:maestro_id>/", maestro_detalle, name="maestro_detalle"),
]
