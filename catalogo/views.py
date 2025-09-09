from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from cuentas.models import Maestro
from .models import Materia

def maestros_list(request):
    qs = (Maestro.objects
          .select_related("usuario")
          .prefetch_related("materias")
          .all())

    # Filtros
    materia = request.GET.get("materia") or ""
    ciudad = request.GET.get("ciudad") or ""
    modalidad = request.GET.get("modalidad") or ""   # online | presencial | (vacío)
    ordenar = request.GET.get("ordenar") or ""       # precio_asc | precio_desc

    if materia:
        qs = qs.filter(materias__nombre__icontains=materia)
    if ciudad:
        qs = qs.filter(ciudad__icontains=ciudad)
    if modalidad == "online":
        qs = qs.filter(online=True)
    elif modalidad == "presencial":
        qs = qs.filter(presencial=True)

    if ordenar == "precio_asc":
        qs = qs.order_by("precio_hora")
    elif ordenar == "precio_desc":
        qs = qs.order_by("-precio_hora")
    else:
        qs = qs.order_by("usuario__username")

    # Paginación
    paginator = Paginator(qs, 8)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Para el selector de materias (opcional)
    materias = Materia.objects.all().order_by("nombre")

    ctx = {
        "page_obj": page_obj,
        "materias": materias,
        "materia_val": materia,
        "ciudad_val": ciudad,
        "modalidad_val": modalidad,
        "ordenar_val": ordenar,
    }
    return render(request, "catalogo/maestros_list.html", ctx)

def maestro_detalle(request, maestro_id):
    m = get_object_or_404(
        Maestro.objects.select_related("usuario").prefetch_related("materias"),
        pk=maestro_id
    )
    return render(request, "catalogo/maestro_detalle.html", {"maestro": m})

