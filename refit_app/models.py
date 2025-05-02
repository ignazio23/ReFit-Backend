
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from refit_app.managers import UserManager
from django.utils.translation import gettext as _
import uuid

# ==========================================================================
# MODELS – ReFit App (reestructurado según SQL)
# Idioma: Código en inglés / Comentarios y mensajes en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/03/25
# Descripción: Modelos ajustados a la estructura real de base de datos SQL
# ==========================================================================
# --------------------------------------------------------------------------
# Constantes de opciones
# --------------------------------------------------------------------------
GENDER_CHOICES = ( ("Masculino", "Masculino"), ("Femenino", "Femenino"), ("Prefiero no decir", "Prefiero no decir"), )

CHALLENGE_TYPE_CHOICES = ( ("D", "Diario"), ("S", "Semanal"), )

TIPO_TRANSACCIONES_CHOICES = ( ("Ingreso", "Ingreso"), ("Gasto", "Gasto"), )

TIPO_ESTADOS_CHOICES = (('aprobado', 'Aprobado'), ('pendiente', 'Pendiente'), ('rechazado', 'Rechazado'))

TIPO_OBJETIVO_CHOICES = [('cuantitativo', 'Cuantitativo'), ('cualitativo', 'Cualitativo')]

# --------------------------------------------------------------------------
# IMAGENES
# --------------------------------------------------------------------------
class Imagen(models.Model):
    """
    Modelo para almacenar imágenes en la base de datos.
    Se utiliza un UUID para identificar cada imagen de forma única.
    """
    pk_imagenes = models.AutoField(primary_key=True, verbose_name="ID imagen")
    uuid = models.CharField(max_length=100, unique=True, verbose_name="UUID")
    extension = models.CharField(max_length=10)
    nombre_logico = models.CharField(max_length=255, null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    

    class Meta:
        db_table = '"IMAGENES"'

    @property
    def id(self):
        return self.pk_imagenes

# --------------------------------------------------------------------------
# Modelo de Usuario personalizado (USUARIOS)
# --------------------------------------------------------------------------
class User(AbstractBaseUser, PermissionsMixin):
    """
    Modelo de usuario personalizado que extiende AbstractBaseUser y PermissionsMixin.
    Permite la autenticación y gestión de permisos de usuarios.
    """
    id = models.AutoField(primary_key=True, db_column='pk_usuarios', verbose_name="ID usuario")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    apellidos = models.CharField(max_length=100, verbose_name="Apellidos")
    email = models.EmailField(unique=True, max_length=100, verbose_name="Email")
    password = models.CharField(max_length=128, verbose_name="Contraseña")
    fecha_nacimiento = models.DateField()
    genero = models.CharField(max_length=20, choices=GENDER_CHOICES, verbose_name="Género")
    codigo_referido = models.CharField(max_length=10, unique=True, null=True, blank=True)
    fk_usuario_referente = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referidos'
    )
    objetivo_diario = models.IntegerField(default=10000, verbose_name="Objetivo diario")
    image = models.ForeignKey('Imagen', null=True, blank=True, on_delete=models.SET_NULL)
    racha = models.IntegerField(default=0, verbose_name="Racha")
    racha_updated_at = models.DateTimeField(null=True, blank=True)

    update_password = models.BooleanField(default=False)

    pasos_totales = models.IntegerField(default=0, verbose_name="Pasos totales")
    monedas_actuales = models.IntegerField(default=0, verbose_name="Monedas actuales")

    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    first_login = models.BooleanField(default=True)  # Campo agregado para marcar el primer inicio de sesión
    last_login = models.DateTimeField(null=True, blank=True)

    last_sync = models.DateTimeField(null=True, blank=True, verbose_name="Última sincronización")

    blocked = models.BooleanField(default=False)
    lock_date = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellidos', 'fecha_nacimiento', 'genero']

    objects = UserManager()

    class Meta:
        db_table = '"USUARIOS"'

# --------------------------------------------------------------------------
# Modelo de Recuperación de Contraseña (PASSWORD_RECOVERY)
# --------------------------------------------------------------------------
class PasswordRecovery(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    def __str__(self):
        return f"Token para {self.usuario.email}"
    
    class Meta:
        db_table = '"PASSWORD_RECOVERY"'
    
# --------------------------------------------------------------------------
# PRODUCTOS
# --------------------------------------------------------------------------
class Producto(models.Model):
    """
    Modelo para almacenar productos que pueden ser canjeados por los usuarios.
    Incluye campos para nombre, descripción, imagen destacada, precio y disponibilidad.
    """
    pk_productos = models.AutoField(primary_key=True, verbose_name="ID producto")
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    descripcion = models.TextField(null=True, blank=True, verbose_name="Descripción")
    imagen_destacada = models.ForeignKey(
        Imagen, null=True, on_delete=models.SET_NULL, related_name="productos_destacados"
    )
    precio_monedas = models.IntegerField(verbose_name="Precio en monedas")
    disponible = models.BooleanField(default=True)
    destacado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"PRODUCTOS"'
    
    @property
    def id(self):
        return self.pk_productos

# --------------------------------------------------------------------------
# PRODUCTOS_IMAGENES
# --------------------------------------------------------------------------
class ProductoImagen(models.Model):
    """
    Modelo para almacenar la relación entre productos e imágenes.
    Permite asociar múltiples imágenes a un producto.
    """
    pk_productos_imagenes = models.AutoField(primary_key=True, verbose_name="ID producto-imagen")
    fk_productos = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="imagenes"
    )
    fk_imagenes = models.ForeignKey(
        Imagen, on_delete=models.CASCADE, related_name="producto_imagenes"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"PRODUCTOS_IMAGENES"'
    
    @property
    def id(self):
        return self.pk_productos_imagenes

# --------------------------------------------------------------------------
# CATEGORIAS
# --------------------------------------------------------------------------
class Categoria(models.Model):
    """
    Modelo para almacenar las categorías de productos.
    Cada categoría tiene un nombre único y una imagen asociada.
    """
    pk_categorias = models.AutoField(primary_key=True, verbose_name="ID Categoría")
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    imagen = models.ForeignKey(
        Imagen, null=True, on_delete=models.SET_NULL, related_name="categorias"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"CATEGORIAS"'

    @property
    def id(self):
        return self.pk_categorias

# --------------------------------------------------------------------------
# PRODUCTOS_CATEGORIAS
# --------------------------------------------------------------------------
class ProductoCategoria(models.Model):
    """
    Modelo para almacenar la relación entre productos y categorías.
    Permite asociar múltiples categorías a un producto y viceversa.
    """
    pk_productos_categorias = models.AutoField(primary_key=True, verbose_name="ID producto-categoría")
    
    fk_productos = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="categorias_relacionadas"
    )

    fk_categorias = models.ForeignKey(
        Categoria, on_delete=models.CASCADE, related_name="productos_asociados"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"PRODUCTOS_CATEGORIAS"'

    def __str__(self):
        return f"{self.fk_producto.nombre} - {self.fk_categoria.nombre}"

# --------------------------------------------------------------------------
# HISTORIAL DE CANJE DE PRODUCTOS
# --------------------------------------------------------------------------
class RedeemProduct(models.Model):
    """
    Modelo para almacenar el historial de canje de productos por parte de los usuarios.
    Incluye campos para el usuario, producto canjeado y la fecha de canje.
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="productos_canjeados"
    )
    product = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="canjes_realizados"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '"PRODUCTOS_CANJEADOS"'
        verbose_name_plural = 'Productos Canjeados'
        db_table = '"HISTORIAL_PRODUCTOS_CANJEADOS"'

    def __str__(self):
        return f"Producto: {self.product}, Usuario: {self.user.email}"
    
# --------------------------------------------------------------------------
# PARAMETROS
# --------------------------------------------------------------------------
class Parametro(models.Model):
    """
    Modelo para almacenar parámetros de configuración del sistema.
    Permite ajustar diferentes aspectos del funcionamiento de la aplicación.
    """
    pk_parametros = models.AutoField(primary_key=True, verbose_name="ID parámetro")
    descripcion = models.TextField(null=True, blank=True, verbose_name="Descripción")
    codigo = models.CharField(max_length=100, verbose_name="Código")
    valor = models.TextField(null=True, blank=True, verbose_name="Valor")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"PARAMETROS"'

# --------------------------------------------------------------------------
# OBJETIVOS_DIARIOS
# --------------------------------------------------------------------------
class ObjetivoDiario(models.Model):
    """
    Modelo para almacenar objetivos diarios que los usuarios pueden completar.
    Incluye campos para nombre, descripción, premio y fecha de creación.
    """
    pk_objetivos_diarios = models.AutoField(primary_key=True, verbose_name="ID objetivo diario")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    descripcion = models.TextField(null=True, blank=True, verbose_name="Descripción")
    tipo = models.CharField(max_length=20, choices=TIPO_OBJETIVO_CHOICES, default='cuantitativo')
    requisito = models.CharField(max_length=255, verbose_name="Requisito del objetivo")
    valor_requerido = models.IntegerField(default=10000, verbose_name="Cantidad requerida (solo para cuantitativos)")
    premio = models.IntegerField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name="Objetivo activo")
    
    class Meta:
        db_table = '"OBJETIVOS_DIARIOS"'
    
    @property
    def id(self):
        return self.pk_objetivos_diarios

# --------------------------------------------------------------------------
# USUARIOS_OBJETIVOS_DIARIOS
# --------------------------------------------------------------------------
class UsuarioObjetivoDiario(models.Model):
    """
    Modelo para almacenar la relación entre usuarios y objetivos diarios.
    Permite registrar qué objetivos ha completado cada usuario y cuándo.
    """
    pk_usuarios_objetivos_diarios = models.AutoField(primary_key=True, verbose_name="ID usuario-objetivo diario")

    fk_usuarios = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="objetivos_diarios_usuario"
    )

    fk_objetivos_diarios = models.ForeignKey(
        ObjetivoDiario, on_delete=models.CASCADE, related_name="usuarios_objetivos"
    )

    fecha_completado = models.DateTimeField(null=True, blank=True)
    fecha_canjeado = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = '"USUARIOS_OBJETIVOS_DIARIOS"'
        indexes = [
            models.Index(fields=['fk_usuarios']),
            models.Index(fields=['fk_objetivos_diarios']),
        ]
        unique_together = ('fk_usuarios', 'fk_objetivos_diarios', 'fecha_creacion') # Evita múltiples registros del mismo objetivo para el mismo
    
    @property
    def id(self):
        return self.pk_usuarios_objetivos_diarios

# --------------------------------------------------------------------------
# PASOS
# --------------------------------------------------------------------------
class Pasos(models.Model):
    """
    Modelo para almacenar el conteo de pasos diarios de los usuarios.
    Incluye campos para el usuario, fecha y cantidad de pasos registrados.
    """
    pk_pasos = models.BigAutoField(primary_key=True, verbose_name="ID pasos")
    fk_usuarios = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="pasos_diarios"
    )
    fecha = models.DateField()
    pasos = models.IntegerField(verbose_name="Pasos")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"PASOS"'
        # Se agrega la restricción para que "pasos" sea siempre >= 0
        constraints = [
            models.CheckConstraint(check=models.Q(pasos__gte=0), name='check_pasos_non_negative')
        ]


# --------------------------------------------------------------------------
# TRANSACCIONES
# --------------------------------------------------------------------------
class Transaccion(models.Model):
    """
    Modelo para almacenar transacciones de ingresos y gastos de los usuarios.
    Incluye campos para el usuario, monto, tipo de transacción y fecha de creación.
    """
    pk_transacciones = models.BigAutoField(primary_key=True, verbose_name="ID transacción")
    pk_usuarios = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="transacciones"
    )
    uuid = models.CharField(max_length=100, unique=True, verbose_name="UUID")
    monto = models.IntegerField(verbose_name="Cantidad")
    tipo = models.CharField(max_length=50, choices=TIPO_TRANSACCIONES_CHOICES) # Se agrega choices para limitar los valores a "Ingreso" o "Gasto"
    estado = models.CharField(max_length=20, choices=TIPO_ESTADOS_CHOICES) # Se agrega choices para limitar los valores a "Pendiente", "Completado" o "Rechazado"
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"TRANSACCIONES"'

# --------------------------------------------------------------------------
# CANJES
# --------------------------------------------------------------------------
class Canje(models.Model):
    """
    Modelo para almacenar el historial de canjes de productos por parte de los usuarios.
    Incluye campos para el usuario, producto canjeado, monto y fecha de canje.
    """
    pk_canjes = models.BigAutoField(primary_key=True, verbose_name="ID canje")

    fk_usuarios = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="canjes_usuario"
    )

    fk_productos = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="canjes_producto"
    )
    
    monto = models.IntegerField(verbose_name="Cantidad")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"CANJES"'

# --------------------------------------------------------------------------
# SEGUIMIENTO DE USUARIOS
# --------------------------------------------------------------------------
class UserFollowing(models.Model):
    """
    Modelo para almacenar la relación de seguimiento entre usuarios.
    Permite que un usuario siga a otro y viceversa.
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="seguidores"
    )
    following = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="seguidos"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Usuario que sigue'
        verbose_name_plural = 'Seguimientos'
        db_table = '"USER_FOLLOWING"'

    def __str__(self):
        return f"{self.user.email} sigue a {self.following.email}"
    
# --------------------------------------------------------------------------
# FAQS
# --------------------------------------------------------------------------
class FAQ(models.Model):
    """
    Modelo para almacenar preguntas frecuentes (FAQ).
    """
    id = models.AutoField(primary_key=True)
    question = models.TextField(verbose_name="Pregunta")
    answer = models.TextField(verbose_name="Respuesta")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"FAQS"'