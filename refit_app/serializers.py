from rest_framework import serializers
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from refit_app.models import (
    User, Pasos, Producto, Categoria, Imagen, Parametro, UsuarioObjetivoDiario,
    Transaccion, ProductoCategoria, Canje, ProductoImagen, ObjetivoDiario
)
from datetime import date

# ============================================================================
# SERIALIZERS – ReFit App
# Idioma: Código en inglés / Comentarios y mensajes en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Este archivo contiene los serializadores de la aplicación ReFit.
#              Se incluyen validaciones detalladas, mensajes de error claros para producción
#              y docstrings que explican la función de cada serializador.
# ============================================================================
# ------------------------------------------------------------------------------
# Registro de Usuario
# ------------------------------------------------------------------------------
# Serializer para registrar nuevos usuarios. Aplica hash a la contraseña
# y utiliza UserManager para crear el usuario correctamente.

class UserRegisterSerializer(serializers.ModelSerializer):
    """
    Serializador para el registro de nuevos usuarios.
    
    Valida que el email sea único, que las contraseñas cumplan con los requisitos
    y que ambos campos de contraseña coincidan. Se utiliza el UserManager para la creación
    correcta del usuario.
    """
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="El email ingresado ya existe. Por favor, use otro email.")]
    )
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    name = serializers.CharField(source='nombre')
    surname = serializers.CharField(source='apellidos')
    birthDate = serializers.DateField(source='fecha_nacimiento')
    gender = serializers.CharField(source='genero')
    referralCode = serializers.CharField(source='codigo_referido', allow_blank=True, required=False)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'name', 'surname',
                  'birthDate', 'gender', 'referralCode')

    def validate_email(self, value):
        if User.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError("Ya existe un usuario activo con este email.")
        return value
    
    def validate_password(self, value):
        """
        Valida que la contraseña tenga al menos 8 caracteres.
        """
        if len(value) < 8:
            raise serializers.ValidationError("La contraseña debe tener al menos 8 caracteres.")
        return value

    def create(self, validated_data):
        referral_code = validated_data.pop("codigo_referido", "").strip()
        referente = None

        # Buscar usuario referente si se proporcionó un código válido
        if referral_code:
            referente = User.objects.filter(codigo_referido=referral_code).first()

        # Generar código de referido único para el nuevo usuario
        validated_data["codigo_referido"] = self.generar_codigo_unico()

        # Asignar usuario referente si corresponde
        validated_data["fk_usuario_referente"] = referente

        # Normalizar email
        validated_data['email'] = validated_data['email'].lower().strip()

        return User.objects.create_user(**validated_data)

    def generar_codigo_unico(self):
        import string, random
        while True:
            nuevo_codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not User.objects.filter(codigo_referido=nuevo_codigo).exists():
                return nuevo_codigo

# ------------------------------------------------------------------------------
# Registro: Serializador de respuesta - COMENTADO DEBIDO A QUE NO SE ESTA UTILIZANDO MÁS
# ------------------------------------------------------------------------------
# Serializador simple para retornar tras el registro de usuario.
# Incluye campos básicos como id, email, nombre y apellidos.
# Este serializador se utiliza para mostrar la información del usuario
# después de un registro exitoso.
"""
class RegisterResponseSerializer(serializers.ModelSerializer):
    def get_profilePicture(self, obj):
        if obj.image and obj.image.uuid:
            return obj.image.uuid
        return None
    profilePicture = serializers.SerializerMethodField()
    ""
    Serializador simple para retornar tras el registro de usuario.
    ""
    class Meta:
        model = User
        fields = ('id', 'email', 'nombre', 'apellidos', 'fecha_nacimiento', 'genero', 'codigo_referido', 'profilePicture')
"""
# ------------------------------------------------------------------------------
# Login: Serializador de respuesta
# ------------------------------------------------------------------------------
# Serializer personalizado para la respuesta al iniciar sesión.
# Incluye datos calculados como pasos diarios y ranking en el leaderboard.
# Mapea campos del modelo a nombres más amigables para el frontend.

class LoginResponseSerializer(serializers.ModelSerializer):
    """
    Serializador para la respuesta de login.
    
    Mapea campos del modelo a nombres más amigables y calcula datos adicionales como
    la posición en el leaderboard.
    """
    profilePicture = serializers.SerializerMethodField()
    #image_url = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    coins = serializers.IntegerField(source='monedas_actuales')
    dailySteps = serializers.SerializerMethodField()
    dailyGoal = serializers.IntegerField(source='objetivo_diario')
    leaderBoardPosition = serializers.SerializerMethodField()
    monthlySteps = serializers.IntegerField(source='pasos_totales')
    firstLogin = serializers.BooleanField(source='first_login')
    lastLogin  = serializers.DateTimeField(source='last_login', format="%Y-%m-%d %H:%M:%S", read_only=True)
    updatePassword = serializers.BooleanField(source='update_password')
    referred = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'name', 'email', 'coins', 'dailySteps', 'dailyGoal', 'monthlySteps', 
                  'leaderBoardPosition', 'firstLogin', 'profilePicture', 'lastLogin', 'updatePassword', 'referred')
    
    def get_profilePicture(self, obj):
        if obj.image and obj.image.uuid and obj.image.extension:
            return f"http://3.17.152.152/media/public/{obj.image.uuid}.{obj.image.extension.strip('.')}"
        return None

    def get_name(self, obj):
        """
        Concatena el nombre y apellido del usuario.
        """
        return f"{obj.nombre} {obj.apellidos}"

    def get_dailySteps(self, obj):
        """
        Retorna el total de pasos del día actual del usuario.
        """
        pasos = Pasos.objects.filter(fk_usuarios=obj, fecha=date.today()).first()
        return pasos.pasos if pasos else 0

    def get_leaderBoardPosition(self, obj):
        """
        Calcula la posición del usuario en el ranking basado en pasos totales.
        """
        usuarios = User.objects.filter(is_staff=False).order_by('-pasos_totales').values_list('pk', flat=True)
        try:
            return list(usuarios).index(obj.pk) + 1
        except ValueError:
            return None
    
    def get_referred(self, obj):
        return obj.fk_usuario_referente is not None

# ------------------------------------------------------------------------------
# Perfil del Usuario (para ediciones y detalles)
# ------------------------------------------------------------------------------
class UserSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización y edición del perfil de usuario.
    """
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'nombre', 'apellidos', 'genero', 'fecha_nacimiento',
            'objetivo_diario', 'racha', 'monedas_actuales', 'image_url'
        )

    def get_image_url(self, obj):
        """
        Retorna la URL de la imagen asociada al usuario.
        """
        if obj.imagen and obj.imagen.uuid:
            return f"/media/{obj.imagen.uuid}{obj.imagen.extension}"
        return None

# ------------------------------------------------------------------------------
# Leaderboard
# ------------------------------------------------------------------------------
# Devuelve información reducida y relevante para los rankings de usuarios,
# combinando pasos totales, monedas y nombre completo.
class LeaderBoardSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización del Leaderbord.
    """
    name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    coins = serializers.IntegerField(source='monedas_actuales')
    steps = serializers.IntegerField(source='pasos_totales')
    streak = serializers.IntegerField(source='racha')

    class Meta:
        model = User
        fields = ('id', 'name', 'image', 'coins', 'steps', 'streak')

    def get_name(self, obj):
        """
        Retorna los nombres de usuarios para el leaderboard. 
        """
        return f"{obj.nombre} {obj.apellidos}"

    def get_image(self, obj):
        if obj.image:
            return f"http://3.17.152.152/media/public/{obj.image.uuid}.{obj.image.extension.strip('.')}"
        return None

# ------------------------------------------------------------------------------
# Edición de Perfil
# ------------------------------------------------------------------------------
class EditProfilePictureSerializer(serializers.ModelSerializer):
    """
    Serializador para editar la imagen de perfil del usuario.
    """
    class Meta:
        model = User
        fields = ('image',)

# Serializer utilizado para actualizar el objetivo diario del usuario.
# Usa el campo 'objetivo_diario' directamente del modelo.
class EditDailyObjetiveSerializer(serializers.ModelSerializer):
    """
    Serializador para editar el objetivo diario del usuario.
    """
    dailyGoal = serializers.IntegerField(source='objetivo_diario')
    
    class Meta:
        model = User
        fields = ['dailyGoal']
    
    def validate_dailyGoal(self, value):
        """
        Validaciones para el objetivo diario.
        """
        if value <= 0:
            raise serializers.ValidationError("El objetivo diario debe ser mayor a 0.")
        return value


# Serializer para editar los datos básicos del perfil del usuario.
# Incluye: nombre, apellidos y correo electrónico.
class EditPersonalDataSerializer(serializers.ModelSerializer):
    """
    Serializador para editar los datos personales del usuario.
    """
    name = serializers.CharField(source='nombre', required=False)
    surnames = serializers.CharField(source='apellidos', required=False)
    birthDate = serializers.DateField(source='fecha_nacimiento', required=False)
    gender = serializers.CharField(source='genero', required=False)

    class Meta:
        model = User
        fields = ('name', 'surnames', 'birthDate', 'gender')
    
    def validate_email(self, value):
        """
        Validaciones para el correo electrónico.
        """
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("Este email ya está registrado por otro usuario.")
        return value

# ------------------------------------------------------------------------------
# Cambio de contraseña con validación
# ------------------------------------------------------------------------------
# Cambio de contraseña
class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializador para cambiar la contraseña del usuario.
    """
    oldPassword = serializers.CharField(write_only=True)
    newPassword = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        """
        Validaciones para la nueva contraseña.
        """
        if len(value) < 8:
            raise serializers.ValidationError("La nueva contraseña debe tener al menos 8 caracteres.")
        return value

    def validate(self, data):
        """
        Validaciones combinadas para la contraseña.
        """
        if data['oldPassword'] == data['newPassword']:
            raise serializers.ValidationError("La nueva contraseña debe ser distinta de la anterior.")
        return data

# ------------------------------------------------------------------------------
# Contacto
# ------------------------------------------------------------------------------
class ContactUsSerializer(serializers.Serializer):
    """
    Serializador para el formulario de contacto.
    """
    name = serializers.CharField()
    email = serializers.EmailField()
    message = serializers.CharField()

    def validate_message(self, value):
        """
        Validaciones para el mensaje de contacto.
        """
        if len(value) < 10:
            raise serializers.ValidationError("El mensaje debe tener al menos 10 caracteres.")
        return value

# ------------------------------------------------------------------------------
# Productos
# ------------------------------------------------------------------------------
class ProductSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización de productos.
    """
    name = serializers.CharField(source='nombre')
    description = serializers.CharField(source='descripcion')
    price = serializers.IntegerField(source='precio')
    featured = serializers.BooleanField(source='destacado')
    imageUrl = serializers.SerializerMethodField()
    featuredImageUrl = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id', 'name', 'description', 'price',
            'featured', 'imageUrl', 'featuredImageUrl'
        ]

    def get_imageUrl(self, obj):
        if obj.imagen and obj.imagen.uuid:
            return f"/media/public/{obj.imagen.uuid}.{obj.imagen.extension.strip('.')}"
        return None

    def get_featuredImageUrl(self, obj):
        if hasattr(obj, 'imagen_destacada') and obj.imagen_destacada:
            return f"/media/public/{obj.imagen_destacada.uuid}.{obj.imagen_destacada.extension.strip('.')}"
        return None
    
    def get_categoria(self, obj):
        """
        Devuelve la categoría del producto.
        """
        cat = ProductoCategoria.objects.filter(fk_productos=obj).first()
        return cat.fk_categorias.nombre if cat else None

# ------------------------------------------------------------------------------
# Categorias
# ------------------------------------------------------------------------------
class CategoriaSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización de categorías de productos.
    """
    code = serializers.CharField(source='codigo')
    name = serializers.CharField(source='nombre')
    imageUrl = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = ('id', 'code', 'name', 'imageUrl')
    
    def get_imageUrl(self, obj):
        img_rel = obj.imagenes.first()  # Tomamos la primera imagen asociada
        if img_rel and img_rel.fk_imagenes:
            uuid = img_rel.fk_imagenes.uuid
            ext = img_rel.fk_imagenes.extension.strip('.')
            return f"http://3.17.152.152/media/public/{uuid}.{ext}"
        return None

# ----------------------------------------------------------------------------
# Producto - Categorias
# ----------------------------------------------------------------------------
class ProductoCategoriaSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización de productos y sus categorías. 
    """
    id_producto = serializers.IntegerField(source='fk_productos.id', read_only=True)
    id_categoria = serializers.IntegerField(source='fk_categorias.id', read_only=True)
    nombre_producto = serializers.CharField(source='fk_productos.nombre', read_only=True)
    nombre_categoria = serializers.CharField(source='fk_categorias.nombre', read_only=True)

    class Meta:
        model = ProductoCategoria
        fields = ('id', 'id_producto', 'nombre_producto', 'id_categoria', 'nombre_categoria', 'fecha_creacion')

# ------------------------------------------------------------------------------
# Canjeo de Productos
# ------------------------------------------------------------------------------
class CanjeSerializer(serializers.ModelSerializer):
    """
    Serializador para el canjeo de productos. 
    """
    id_usuario = serializers.IntegerField(source='fk_usuarios.id', read_only=True)
    id_producto = serializers.IntegerField(source='fk_productos.id', read_only=True)
    producto = serializers.CharField(source='fk_productos.nombre', read_only=True)

    class Meta:
        model = Canje
        fields = ('id', 'id_usuario', 'id_producto', 'producto', 'monto', 'fecha')

# ------------------------------------------------------------------------------
# Imagenes
# ------------------------------------------------------------------------------
class ImagenSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización de imágenes. 
    """
    url = serializers.SerializerMethodField()

    class Meta:
        model = Imagen
        fields = ('pk_imagenes', 'uuid', 'extension', 'url', 'fecha_creacion')

    def get_url(self, obj):
        """
        Devuelve la URL de la imagen.
        """
        return f"{settings.MEDIA_URL}{obj.uuid}.{obj.extension}"  # Ajustar según cómo sirvas las imágenes
    
# ------------------------------------------------------------------------------
# Producto - Imagenes
# ------------------------------------------------------------------------------
class ProductoImagenSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización de imágenes asociadas a productos. 
    """
    id_producto = serializers.IntegerField(source='fk_productos.id', read_only=True)
    id_imagen = serializers.IntegerField(source='fk_imagenes.id', read_only=True)
    nombre_producto = serializers.CharField(source='fk_productos.nombre', read_only=True)
    url_imagen = serializers.SerializerMethodField()

    class Meta:
        model = ProductoImagen
        fields = ('id', 'id_producto', 'nombre_producto', 'id_imagen', 'url_imagen', 'fecha_creacion')

    def get_url_imagen(self, obj):
        """
        Devuelve la URL de la imagen asociada al producto.
        """
        return f"{settings.MEDIA_URL}{obj.fk_imagenes.uuid}.{obj.fk_imagenes.extension}"

# ------------------------------------------------------------------------------
# Objetivos Diarios
# ------------------------------------------------------------------------------
class ObjetivoDiarioSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización de objetivos diarios. 
    """
    class Meta:
        model = ObjetivoDiario
        fields = ('id', 'nombre', 'descripcion', 'premio', 'fecha_creacion')

    def validate_premio(self, value):
        """
        Valida que el premio sea un valor positivo.
        """
        if value <= 0:
            raise serializers.ValidationError("El premio debe ser positivo.")
        return value

class UsuarioObjetivoDiarioSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización de objetivos diarios asignados a usuarios. 
    """
    objetivo_id = serializers.IntegerField(source='fk_objetivos_diarios.id', read_only=True)
    usuario_id = serializers.IntegerField(source='fk_usuarios.id', read_only=True)
    nombre_objetivo = serializers.CharField(source='fk_objetivos_diarios.nombre_objetivo', read_only=True)
    premio = serializers.IntegerField(source='fk_objetivos_diarios.premio', read_only=True)

    class Meta:
        model = UsuarioObjetivoDiario
        fields = (
            'id', 'usuario_id', 'objetivo_id',
            'nombre_objetivo', 'premio', 'fecha_completado',
            'fecha_canjeado', 'fecha_creacion', 'fecha_modificacion'
        )
    
# ------------------------------------------------------------------------------
# Pasos Diarios
# ------------------------------------------------------------------------------
class PasosSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización de pasos diarios. 
    """
    nombre_usuario = serializers.CharField(source='fk_usuarios.nombre', read_only=True)

    class Meta:
        model = Pasos
        fields = ('id', 'id_usuarios', 'nombre_usuario', 'fecha', 'pasos', 'fecha_creacion')

    def validate_pasos(self, value):
        """
        Valida que el número de pasos sea un valor positivo.
        """
        if value < 0:
            raise serializers.ValidationError("No se permiten pasos negativos.")
        return value

# ------------------------------------------------------------------------------
# Transacciones
# ------------------------------------------------------------------------------
class TransaccionSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización de transacciones. 
    """
    id_usuario = serializers.IntegerField(source='pk_usuarios.id', read_only=True)
    email_usuario = serializers.EmailField(source='pk_usuarios.email', read_only=True)

    class Meta:
        model = Transaccion
        fields = ('id', 'id_usuario', 'email_usuario', 'uuid', 'monto', 'tipo', 'fecha_creacion')

    def validate_monto(self, value):
        """
        Valida que el monto de la transacción sea un valor positivo.
        """
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser positivo.")
        return value

    def validate_tipo(self, value):
        """
        Valida que el tipo de transacción sea válido.
        """
        if value not in ["Ingreso", "Gasto"]:
            raise serializers.ValidationError("Tipo de transacción inválido.")
        return value

# ------------------------------------------------------------------------------
# Parametros
# ------------------------------------------------------------------------------
class ParametroSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización de parámetros del sistema. 
    """
    class Meta:
        model = Parametro
        fields = ('id', 'codigo', 'valor', 'fecha_creacion')

# ------------------------------------------------------------------------------
# Tareas Diarias (placeholders opcionales)
# ------------------------------------------------------------------------------
# Placeholder para funcionalidades futuras relacionadas a tareas diarias.
# Si estas lógicas no están implementadas, se recomienda remover temporalmente.
class CheckDailyTaskSerializer(serializers.Serializer):
    """
    Serializador para verificar el estado de una tarea diaria. 
    """
    tarea_id = serializers.IntegerField()
    nombre_objetivo = serializers.SerializerMethodField()
    premio = serializers.SerializerMethodField()
    fecha_completado = serializers.SerializerMethodField()

    def validate_tarea_id(self, value):
        """
        Valida que la tarea exista y pertenezca al usuario.
        """
        user = self.context["request"].user
        try:
            self.tarea = UsuarioObjetivoDiario.objects.get(pk=value, fk_usuarios=user)
        except UsuarioObjetivoDiario.DoesNotExist:
            raise serializers.ValidationError("La tarea no existe o no pertenece al usuario.")

        if self.tarea.fecha_completado:
            raise serializers.ValidationError("La tarea ya fue completada.")

        return value

    def get_nombre_objetivo(self, obj):
        """
        Devuelve el nombre del objetivo diario asociado a la tarea.
        """
        return self.tarea.fk_objetivos_diarios.nombre

    def get_premio(self, obj):
        """
        Devuelve el premio asociado a la tarea diaria.
        """
        return self.tarea.fk_objetivos_diarios.premio

    def get_fecha_completado(self, obj):
        """
        Devuelve la fecha de completado de la tarea.
        """
        return self.tarea.fecha_completado

class ExchangeDailyTaskSerializer(serializers.Serializer):
    """
    Serializador para canjear una tarea diaria. 
    """
    tarea_id = serializers.IntegerField()
    nombre_objetivo = serializers.SerializerMethodField()
    premio = serializers.SerializerMethodField()
    fecha_canjeado = serializers.SerializerMethodField()

    def validate_tarea_id(self, value):
        """
        Valida que la tarea exista, pertenezca al usuario y no haya sido canjeada.
        """
        user = self.context["request"].user
        try:
            self.tarea = UsuarioObjetivoDiario.objects.get(pk=value, fk_usuarios=user)
        except UsuarioObjetivoDiario.DoesNotExist:
            raise serializers.ValidationError("La tarea no existe o no pertenece al usuario.")

        if not self.tarea.fecha_completado:
            raise serializers.ValidationError("La tarea aún no ha sido completada.")

        if self.tarea.fecha_canjeado:
            raise serializers.ValidationError("La tarea ya fue canjeada.")

        return value

    def get_nombre_objetivo(self, obj):
        """
        Devuelve el nombre del objetivo diario asociado a la tarea.
        """
        return self.tarea.fk_objetivos_diarios.nombre

    def get_premio(self, obj):
        """
        Devuelve el premio asociado a la tarea diaria.
        """
        return self.tarea.fk_objetivos_diarios.premio

    def get_fecha_canjeado(self, obj):
        """
        Devuelve la fecha de canjeo de la tarea.
        """
        return self.tarea.fecha_canjeado

# ------------------------------------------------------------------------------
# Referidos
# ------------------------------------------------------------------------------
class ReferredUserSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización de usuarios referidos. 
    """
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'fecha_registro')

    def get_full_name(self, obj):
        """
        Devuelve el nombre completo del usuario.
        """
        return f"{obj.nombre} {obj.apellidos}"
    
# ------------------------------------------------------------------------------
# Recompensas dinámicas
# ------------------------------------------------------------------------------
class RecompensaParametroSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización de parámetros de recompensas. 
    """
    class Meta:
        model = Parametro
        fields = ('codigo', 'valor')

    def to_representation(self, instance):
        """
        Modifica la representación del serializador para incluir solo
        recompensas específicas. 
        """
        rep = super().to_representation(instance)
        # Se devuelve la representación solo si el código comienza con "RECOMPENSA_"
        if not rep['codigo'].startswith("RECOMPENSA_"):
            return None
        return rep

# ------------------------------------------------------------------------------
# Historial de Pasos
# ------------------------------------------------------------------------------
class HistoricalStepsSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización del historial de pasos diarios. 
    """
    dia = serializers.DateField(source="fecha")
    pasos = serializers.IntegerField()

    class Meta:
        model = Pasos
        fields = ('dia', 'pasos')

# ------------------------------------------------------------------------------
# Historial de Canjes
# ------------------------------------------------------------------------------
class HistoricalCanjeSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización del historial de canjes. 
    """
    producto = serializers.CharField(source='fk_productos.nombre')
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Canje
        fields = ('producto', 'monto', 'fecha', 'imagen_url')

    def get_imagen_url(self, obj):
        """
        Devuelve la URL de la imagen del producto canjeado.
        """
        imagen = obj.fk_productos.imagen_destacada
        if imagen:
            return f"{settings.MEDIA_URL}{imagen.uuid}.{imagen.extension}"
        return None