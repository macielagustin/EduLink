from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

# 🔹 Si ya tenés modelos Provincia/Departamento/Municipio/Localidad definidos en otra app, importa desde allí.
# from ubicaciones.models import Provincia, Departamento, Municipio, Localidad


class Usuario(AbstractUser):
    ROL_CHOICES = (
        ('USER', 'Usuario'),
        ('ALUMNO', 'Alumno'),
        ('MAESTRO', 'Maestro'),
        ('ADMIN', 'Administrador'),
    )

    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default='USER')
    telefono = models.CharField(max_length=30, blank=True)

    nombre = models.CharField(max_length=50, blank=False)
    apellido = models.CharField(max_length=50, blank=False)

    # Campos adicionales de tu amigo
    fecha_nacimiento = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True)  # unifica con "descripcion"
    ciudad = models.CharField(max_length=80, blank=True)  # mantenemos compatibilidad
    verificado = models.BooleanField(default=False)
    foto_perfil = models.ImageField(upload_to='perfiles/', null=True, blank=True)

    institucion = models.ForeignKey('Institucion', on_delete=models.SET_NULL, null=True, blank=True)

    # Geolocalización (usa FK a tablas auxiliares si existen)
    provincia = models.ForeignKey("Provincia", on_delete=models.SET_NULL, null=True, blank=True)
    departamento = models.ForeignKey("Departamento", on_delete=models.SET_NULL, null=True, blank=True)
    municipio = models.ForeignKey("Municipio", on_delete=models.SET_NULL, null=True, blank=True)
    localidad = models.ForeignKey("Localidad", on_delete=models.SET_NULL, null=True, blank=True)
    calle = models.CharField(max_length=255, blank=True)
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)

    # Automáticos
    fecha_creacion = models.DateTimeField(auto_now_add=True)  # similar a date_joined
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.rol})"


class Alumno(models.Model):
    usuario = models.OneToOneField('Usuario', on_delete=models.CASCADE)
    nivel_educativo = models.ForeignKey('NivelEducativo', on_delete=models.SET_NULL, null=True, blank=True)
    materias_interes = models.ManyToManyField('catalogo.Materia', blank=True, related_name='alumnos')
    objetivo = models.TextField(blank=True, null=True)
    disponibilidad = models.ManyToManyField('Disponibilidad', blank=True, related_name='alumnos')
    prefiere_online = models.BooleanField(default=True)

    @property
    def promedio_reseñas(self):
        reseñas = self.reseñas_recibidas.all()
        if reseñas.exists():
            return round(sum(r.puntuacion for r in reseñas) / reseñas.count(), 1)
        return None

    @property
    def total_reseñas(self):
        return self.reseñas_recibidas.count()

    def __str__(self):
        return f"Alumno: {self.usuario.username}"


class Maestro(models.Model):
    usuario = models.OneToOneField('Usuario', on_delete=models.CASCADE)
    precio_hora = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    modalidad = models.CharField(
        max_length=20,
        choices=[
            ("Online", "Online"),
            ("Presencial", "Presencial"),
            ("Ambos", "Ambos"),
        ],
        default="Online",
    )
    descripcion = models.TextField(blank=True, null=True)
    cv = models.FileField(upload_to="cv_maestros/", blank=True, null=True)
    materias = models.ManyToManyField('catalogo.Materia', blank=True, related_name='maestros')
    idiomas = models.ManyToManyField('Idioma', blank=True, related_name='maestros')
    # Nuevo campo para datos de pago
    cbu_cvu_alias = models.CharField(max_length=100, blank=True, null=True, verbose_name="CBU/CVU o Alias")

    @property
    def promedio_reseñas(self):
        reseñas = self.reseñas.all()
        if reseñas.exists():
            return round(sum(r.puntuacion for r in reseñas) / reseñas.count(), 1)
        return None

    @property
    def total_reseñas(self):
        return self.reseñas.count()

    def __str__(self):
        return f"Maestro: {self.usuario.username}"


# Tabla de idiomas
class Idioma(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


# Tabla de niveles educativos (opcional, si no querés usar choices)
class NivelEducativo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


# Tabla de disponibilidades horarias (opcional, si no querés usar choices)
class Disponibilidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre



# Nuevo modelo para disponibilidad de usuarios
class DisponibilidadUsuario(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='disponibilidades')
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(
        max_length=20,
        choices=[
            ('clase', 'Clase'),
            ('ocupacion', 'Ocupación Personal'),
            ('disponible', 'Disponible'),
        ],
        default='ocupacion'
    )
    descripcion = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['fecha_inicio']
    
    def __str__(self):
        return f"{self.titulo} - {self.usuario.username}"



class Provincia(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Departamento(models.Model):
    nombre = models.CharField(max_length=100)
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre

class Municipio(models.Model):
    nombre = models.CharField(max_length=100)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre

class Localidad(models.Model):
    nombre = models.CharField(max_length=100)
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre



class SolicitudClase(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('propuesta', 'Propuesta'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
        ('cancelada', 'Cancelada'),
        ('completada', 'Completada'),
    ]
    
    ESTADOS_PAGO = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('reembolsado', 'Reembolsado'),
        ('cancelado', 'Cancelado'),
    ]
    
    alumno = models.ForeignKey('Alumno', on_delete=models.CASCADE)
    maestro = models.ForeignKey('Maestro', on_delete=models.CASCADE)
    materia = models.ForeignKey('catalogo.Materia', on_delete=models.CASCADE)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_clase_propuesta = models.DateTimeField(null=True, blank=True)
    fecha_clase_confirmada = models.DateTimeField(null=True, blank=True)
    duracion_minutos = models.PositiveIntegerField(default=60)
    mensaje = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    
    # Campos para pago - MEJORADOS
    monto_acordado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    metodo_pago = models.CharField(
        max_length=20,
        choices=[
            ('efectivo', 'Efectivo'),
            ('transferencia', 'Transferencia'),
            ('mercadopago', 'Mercado Pago'),
        ],
        default='efectivo'
    )
    estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='pendiente')
    fecha_pago = models.DateTimeField(null=True, blank=True)
    codigo_pago = models.CharField(max_length=255, blank=True, null=True)
    
    
    promocion_aplicada = models.ForeignKey('Promocion', on_delete=models.SET_NULL, null=True, blank=True)
    voucher_usado = models.ForeignKey('Voucher', on_delete=models.SET_NULL, null=True, blank=True)
    monto_original = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    monto_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)


    # Propiedad para compatibilidad
    @property
    def pago_realizado(self):
        return self.estado_pago == 'pagado'
    
    @pago_realizado.setter
    def pago_realizado(self, value):
        if value:
            self.estado_pago = 'pagado'
            self.fecha_pago = timezone.now()
        else:
            self.estado_pago = 'pendiente'
            self.fecha_pago = None
    

    # Método para aplicar descuento en SolicitudClase
    def aplicar_descuento(self, promocion=None, voucher=None):
        if self.monto_acordado:
            self.monto_original = self.monto_acordado
            self.monto_final = self.monto_acordado
        
            if promocion and promocion.activa:
                self.promocion_aplicada = promocion
                if promocion.tipo == 'descuento_porcentaje':
                    descuento = (self.monto_acordado * promocion.valor) / 100
                    self.monto_final = self.monto_acordado - descuento
                elif promocion.tipo == 'descuento_monto':
                    self.monto_final = self.monto_acordado - promocion.valor
                elif promocion.tipo == 'clase_gratuita':
                    self.monto_final = 0
        
            if voucher and not voucher.usado:
                self.voucher_usado = voucher
            # Aplicar lógica adicional del voucher si es necesario
        
            self.save()


    def __str__(self):
        return f"Solicitud de {self.alumno.usuario.username} a {self.maestro.usuario.username}"
    
    class Meta:
        ordering = ['-fecha_solicitud']



class Conversacion(models.Model):
    maestro = models.ForeignKey('Maestro', on_delete=models.CASCADE, related_name='conversaciones')
    alumno = models.ForeignKey('Alumno', on_delete=models.CASCADE, related_name='conversaciones')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultimo_mensaje = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['maestro', 'alumno']
    
    def __str__(self):
        return f"Conversación: {self.maestro.usuario.username} - {self.alumno.usuario.username}"

class Mensaje(models.Model):
    conversacion = models.ForeignKey('Conversacion', on_delete=models.CASCADE, related_name='mensajes')
    remitente = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    contenido = models.TextField()
    archivo = models.FileField(upload_to='mensajes/archivos/', blank=True, null=True)
    imagen = models.ImageField(upload_to='mensajes/imagenes/', blank=True, null=True)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)
    
    # Nuevo campo para tipo de mensaje
    tipo = models.CharField(max_length=10, default='texto', choices=[
        ('texto', 'Texto'),
        ('imagen', 'Imagen'),
        ('archivo', 'Archivo'),
    ])
    
    # Nombre original del archivo
    nombre_archivo = models.CharField(max_length=255, blank=True, null=True)
    
    # Tamaño del archivo (en bytes)
    tamano_archivo = models.IntegerField(default=0)

    def __str__(self):
        return f"Mensaje de {self.remitente.username} - {self.fecha_envio.strftime('%Y-%m-%d %H:%M')}"
    
    def obtener_tipo_archivo(self):
        """Determinar el tipo de archivo basado en la extensión"""
        if self.archivo:
            nombre = self.archivo.name.lower()
            if nombre.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                return 'imagen'
            elif nombre.endswith(('.pdf', '.doc', '.docx', '.txt')):
                return 'documento'
            elif nombre.endswith(('.zip', '.rar', '.7z')):
                return 'comprimido'
            else:
                return 'archivo'
        return None
    
    def formatear_tamano(self):
        """Formatear tamaño del archivo a formato legible"""
        bytes = self.tamano_archivo
        if bytes < 1024:
            return f"{bytes} B"
        elif bytes < 1024 * 1024:
            return f"{bytes/1024:.1f} KB"
        else:
            return f"{bytes/(1024*1024):.1f} MB"




class Notificacion(models.Model):
    TIPOS = (
        ('solicitud', 'Nueva Solicitud'),
        ('mensaje', 'Mensaje Nuevo'),
        ('clase_aceptada', 'Clase Aceptada'),
        ('clase_rechazada', 'Clase Rechazada'),
        ('review', 'Nueva Reseña'),
    )
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    mensaje = models.TextField()
    enlace = models.CharField(max_length=255, blank=True)
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notificación para {self.usuario.username}: {self.mensaje}"

""" class Resena(models.Model):
    clase = models.ForeignKey(SolicitudClase, on_delete=models.CASCADE, related_name='resenas')
    autor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='resenas_escritas')
    destinatario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='resenas_recibidas')
    calificacion = models.PositiveSmallIntegerField(choices=[(1,1), (2,2), (3,3), (4,4), (5,5)])
    comentario = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['clase', 'autor']  # Una reseña por clase por autor

    def __str__(self):
        return f"Reseña de {self.autor.username} para {self.destinatario.username} - {self.calificacion} estrellas" """


class Reseña(models.Model):
    alumno = models.ForeignKey('Alumno', on_delete=models.SET_NULL, null=True, blank=True)
    maestro = models.ForeignKey('Maestro', on_delete=models.CASCADE, related_name='reseñas')
    solicitud = models.OneToOneField('SolicitudClase', on_delete=models.CASCADE, related_name='reseña')
    puntuacion = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comentario = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.puntuacion} ⭐ - {self.maestro.usuario.username}"

    class Meta:
        verbose_name = "Reseña"
        verbose_name_plural = "Reseñas"
        ordering = ['-fecha_creacion']



class ReseñaAlumno(models.Model):
    maestro = models.ForeignKey('Maestro', on_delete=models.SET_NULL, null=True, blank=True)
    alumno = models.ForeignKey('Alumno', on_delete=models.CASCADE, related_name='reseñas_recibidas')
    solicitud = models.OneToOneField('SolicitudClase', on_delete=models.CASCADE, related_name='reseña_alumno')

    puntuacion = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comentario = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    def _str_(self):
        return f"{self.puntuacion} ⭐ - alumno {self.alumno.usuario.username}"

    class Meta:
        verbose_name = "Reseña de Alumno"
        verbose_name_plural = "Reseñas de Alumnos"
        ordering = ['-fecha_creacion']


# HERRAMIENTAS
# Modelos para las herramientas
class BlocNotas(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    """ contenido = models.TextField(blank=True, null=True) """
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Bloc de {self.usuario.username}"

class Tarea(models.Model):
    PRIORIDAD_CHOICES = [
        ('baja', '🔵 Baja'),
        ('media', '🟡 Media'),
        ('alta', '🔴 Alta'),
    ]
    
    ESTADO_CHOICES = [
        ('pendiente', '⏳ Pendiente'),
        ('en_progreso', '🔄 En Progreso'),
        ('completada', '✅ Completada'),
    ]
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateTimeField(null=True, blank=True)
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default='media')
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    completada = models.BooleanField(default=False)
    fecha_completada = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.titulo} - {self.usuario.username}"

class SesionEstudio(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    duracion_minutos = models.IntegerField(default=0)
    tipo = models.CharField(max_length=20, choices=[('pomodoro', 'Pomodoro'), ('estudio_libre', 'Estudio Libre')])
    descripcion = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Sesión de {self.usuario.username} - {self.duracion_minutos}min"



# Después de los modelos existentes, agregar:

class Institucion(models.Model):
    nombre = models.CharField(max_length=200)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    activa = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nombre

class Promocion(models.Model):
    TIPO_CHOICES = [
        ('descuento_porcentaje', 'Descuento Porcentaje'),
        ('descuento_monto', 'Descuento Monto Fijo'),
        ('clase_gratuita', 'Clase Gratuita'),
        ('grupo', 'Descuento Grupo'),
    ]
    
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # % o monto fijo
    descripcion = models.TextField()
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    activa = models.BooleanField(default=True)
    max_usos = models.IntegerField(default=100)
    usos_actuales = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

class Voucher(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    promocion = models.ForeignKey(Promocion, on_delete=models.CASCADE)
    alumno = models.ForeignKey('Alumno', on_delete=models.CASCADE, null=True, blank=True)
    maestro = models.ForeignKey('Maestro', on_delete=models.CASCADE, null=True, blank=True)
    usado = models.BooleanField(default=False)
    fecha_uso = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Voucher {self.codigo} - {self.promocion.nombre}"

class Nota(models.Model):
    bloc_notas = models.ForeignKey('BlocNotas', on_delete=models.CASCADE, related_name='notas')
    titulo = models.CharField(max_length=200, default="Nueva nota")
    contenido = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_actualizacion']
    
    def __str__(self):
        return f"{self.titulo} - {self.bloc_notas.usuario.username}"





# Modificar el modelo Usuario para agregar institución
# Agregar este campo al modelo Usuario existente:
# institucion = models.ForeignKey(Institucion, on_delete=models.SET_NULL, null=True, blank=True)

# Modificar el modelo SolicitudClase para soportar promociones
# Agregar estos campos al modelo SolicitudClase existente:
# promocion_aplicada = models.ForeignKey(Promocion, on_delete=models.SET_NULL, null=True, blank=True)
# voucher_usado = models.ForeignKey(Voucher, on_delete=models.SET_NULL, null=True, blank=True)
# monto_original = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
# monto_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)