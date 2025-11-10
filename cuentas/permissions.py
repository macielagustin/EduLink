from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import SolicitudClase

Usuario = get_user_model()

def _rol(u):
    return str(getattr(u, "rol", "")).upper()

def puede_ver_perfil_alumno(user, alumno_usuario: Usuario) -> bool:
    """
    Permite ver el perfil del alumno si:
    - es superuser / ADMIN,
    - es el propio alumno,
    - es MAESTRO y existe cualquier SolicitudClase con ese alumno.
    (tu FK va a Maestro/Alumno, por eso filtramos por __usuario)
    """
    if not user.is_authenticated:
        return False

    if getattr(user, "is_superuser", False) or _rol(user) in ("ADMIN", "SUPERADMIN"):
        return True

    if user.id == alumno_usuario.id:
        return True

    if _rol(user) in ("MAESTRO", "PROFESOR"):
        return SolicitudClase.objects.filter(
            Q(maestro__usuario=user) & Q(alumno__usuario=alumno_usuario)
        ).exists()

    return False
