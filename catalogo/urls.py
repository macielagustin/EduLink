from django.urls import path
from django.http import HttpResponse

def ping(_):
    return HttpResponse("EduLink OK - catalogo")

urlpatterns = [
    path("ping/", ping, name="catalogo_ping"),
]
