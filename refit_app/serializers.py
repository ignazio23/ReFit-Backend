from rest_framework import serializers
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.validators import UniqueValidator
from refit_app.models import (
    User, Pasos, Producto, Categoria, Imagen, Parametro, UsuarioObjetivoDiario,
    Transaccion, ProductoCategoria, Canje, ProductoImagen, ObjetivoDiario, FAQ
)
from datetime import date
from django.utils import timezone
from django.shortcuts import get_object_or_404

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
    password = serializers.CharField(write_only=True, required=True)
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
        Valida la contraseña usando los validadores de Django,
        incluyendo validadores que dependen de los datos del usuario.
        """
        user_data = {
            'email': self.initial_data.get('email', ''),
            'nombre': self.initial_data.get('name', ''),
            'apellidos': self.initial_data.get('surname', '')
        }

        try:
            validate_password(value, user=User(**user_data))
        except DjangoValidationError as e:
            raise serializers.ValidationError([self.traducir_mensaje(msg) for msg in e.messages])
        
        return value

    def traducir_mensaje(self, msg):
        traducciones = {
            "This password is too common.": "La contraseña es demasiado común.",
            "This password is entirely numeric.": "La contraseña no puede ser solo números.",
            "This password is too short. It must contain at least 8 characters.":
                "La contraseña debe tener al menos 8 caracteres.",
            "The password is too similar to the email address.": "La contraseña es muy similar al correo.",
            "The password is too similar to the first name.": "La contraseña es muy similar al nombre.",
            "The password is too similar to the last name.": "La contraseña es muy similar al apellido.",
            "This password is too similar to the username.": "La contraseña es muy similar al nombre de usuario.",
        }
        return traducciones.get(msg, msg)
    
    def create(self, validated_data):
        referral_code = validated_data.pop("codigo_referido", "").strip()
        referente = None

        # Buscar usuario referente si se proporcionó un código válido
        if referral_code:
            referente = User.objects.filter(codigo_referido=referral_code.upper()).first()

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
    name = serializers.CharField(source='nombre')
    surname = serializers.CharField(source='apellidos')
    birthDate = serializers.DateField(source='fecha_nacimiento', format="%Y-%m-%d", required=False)
    gender = serializers.CharField(source='genero', required=False)
    firstLogin = serializers.BooleanField(source='first_login')
    lastLogin  = serializers.DateTimeField(source='last_login', format="%Y-%m-%d %H:%M:%S", read_only=True)
    updatePassword = serializers.BooleanField(source='update_password')
    referred = serializers.SerializerMethodField()
    referralCode = serializers.CharField(source='codigo_referido')
    profilePicture = serializers.SerializerMethodField()
    coins = serializers.IntegerField(source='monedas_actuales')
    dailySteps = serializers.SerializerMethodField()
    dailyGoal = serializers.IntegerField(source='objetivo_diario')
    leaderBoardPosition = serializers.SerializerMethodField()
    monthlySteps = serializers.IntegerField(source='pasos_totales')
    lastSync = serializers.DateTimeField(source='last_sync', format="%Y-%m-%d %H:%M:%S", required=False)

    class Meta:
        model = User
        fields = (
            'id', 'name', 'surname', 'email', 'coins', 'dailySteps', 'dailyGoal',
            'monthlySteps', 'leaderBoardPosition', 'firstLogin', 'profilePicture', 'lastSync',
            'lastLogin', 'updatePassword', 'referralCode', 'referred', 'birthDate', 'gender'
        )
    
    def get_profilePicture(self, obj):
        request = self.context.get('request')
        if obj.image:
            nombre_logico = obj.image.nombre_logico
            extension = obj.image.extension.strip('.') if obj.image.extension else 'jpg'
            uuid_str = str(obj.image.uuid) if obj.image.uuid else ''
            if nombre_logico:
                return f"http://3.17.152.152/media/public/{nombre_logico}.{extension}?v={uuid_str}"
        return None

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
    
    def get_lastSync(self, obj):
        return obj.last_sync.isoformat() if obj.last_sync else None

# ------------------------------------------------------------------------------
# Perfil del Usuario (para ediciones y detalles)
# ------------------------------------------------------------------------------
class UserSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización y edición del perfil de usuario.
    """
    name = serializers.CharField(source='nombre')
    surname = serializers.CharField(source='apellidos')
    birthDate = serializers.DateField(source='fecha_nacimiento', format="%Y-%m-%d", required=False)
    gender = serializers.CharField(source='genero', required=False)
    profilePicture = serializers.SerializerMethodField()
    referralCode = serializers.CharField(source='codigo_referido')
    coins = serializers.IntegerField(source='monedas_actuales')
    dailySteps = serializers.SerializerMethodField()
    dailyGoal = serializers.IntegerField(source='objetivo_diario')
    leaderBoardPosition = serializers.SerializerMethodField()
    monthlySteps = serializers.IntegerField(source='pasos_totales')
    lastSync = serializers.DateTimeField(source='last_sync', format="%Y-%m-%d %H:%M:%S", required=False)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'name', 'surname', 'birthDate', 'gender', 'referralCode',
            'profilePicture', 'coins', 'dailySteps', 'dailyGoal', 
            'leaderBoardPosition', 'monthlySteps' , 'lastSync'
            )

    def get_profilePicture(self, obj):
        request = self.context.get('request')
        if obj.image:
            nombre_logico = obj.image.nombre_logico
            extension = obj.image.extension.strip('.') if obj.image.extension else 'jpg'
            uuid_str = str(obj.image.uuid) if obj.image.uuid else ''
            if nombre_logico:
                return f"http://3.17.152.152/media/public/{nombre_logico}.{extension}?v={uuid_str}"
        return None

    
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
        
    def get_lastSync(self, obj):
        return obj.last_sync.isoformat() if obj.last_sync else None

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
    steps = serializers.IntegerField(source='pasos_totales')

    class Meta:
        model = User
        fields = ('id',  'image', 'name', 'steps')

    def get_name(self, obj):
        """
        Retorna los nombres de usuarios para el leaderboard. 
        """
        return f"{obj.nombre} {obj.apellidos}"

    def get_image(self, obj):
        """
        Devuelve la URL pública completa de la imagen de perfil del usuario.
        """
        request = self.context.get('request')  # para que la URL sea siempre completa
        if obj.image and obj.image.nombre_logico:
            filename = f"{obj.image.nombre_logico}{obj.image.extension}"
            url = f"/media/public/{filename}"
            if request is not None:
                return request.build_absolute_uri(url)
            return f"http://3.17.152.152{url}"
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
    surname = serializers.CharField(source='apellidos', required=False)
    birthDate = serializers.DateField(source='fecha_nacimiento', required=False)
    gender = serializers.CharField(source='genero', required=False)

    class Meta:
        model = User
        fields = ('name', 'surname', 'birthDate', 'gender')
    
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
    #name = serializers.CharField()
    #email = serializers.EmailField()
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
    code = serializers.CharField(source='codigo')
    name = serializers.CharField(source='nombre')
    description = serializers.CharField(source='descripcion')
    price = serializers.IntegerField(source='precio_monedas')
    featured = serializers.BooleanField(source='destacado')
    imageUrl = serializers.SerializerMethodField()
    featuredImageUrl = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id', 'code', 'name', 'description', 'price',
            'featured', 'imageUrl', 'featuredImageUrl'
        ]

    def get_imageUrl(self, obj):
        """
        Retorna la URL de la primera imagen vinculada en la tabla PRODUCTOS_IMAGENES.
        """
        from refit_app.models import ProductoImagen

        primera = ProductoImagen.objects.filter(fk_productos=obj).select_related('fk_imagenes').first()
        if primera and primera.fk_imagenes:
            imagen = primera.fk_imagenes
            return f"/media/public/{imagen.uuid}.{imagen.extension.strip('.')}"
        return None

    def get_featuredImageUrl(self, obj):
        """
        Retorna la URL de la imagen destacada asociada directamente al producto.
        """
        if obj.imagen_destacada and obj.imagen_destacada.nombre_logico and obj.imagen_destacada.extension:
            return f"http://3.17.152.152/media/public/assets/{obj.imagen_destacada.nombre_logico}{obj.imagen_destacada.extension}"
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
        if obj.imagen and obj.imagen.nombre_logico and obj.imagen.extension:
            return f"http://3.17.152.152/media/public/assets/{obj.imagen.nombre_logico}{obj.imagen.extension}"
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
        fields = (
            'id', 'nombre', 'descripcion', 'tipo', 'requisito',
            'valor_requerido','premio', 'fecha_creacion'
        )

        read_only_fields = ['id', 'fecha_creacion']

    def validate_premio(self, value):
        """
        Valida que el premio sea un valor positivo.
        """
        if value <= 0:
            raise serializers.ValidationError("El premio debe ser positivo.")
        return value

class SimpleObjetivoDiarioSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='nombre')
    prize = serializers.IntegerField(source='premio')

    class Meta:
        model = ObjetivoDiario
        fields = ('id', 'name', 'prize')

# ------------------------------------------------------------------------------
# Serializador para la visualización de objetivos diarios asignados a usuarios.
# ------------------------------------------------------------------------------
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
# Check de Tareas Diarias
# ------------------------------------------------------------------------------
# Serializador para verificar el estado de una tarea diaria.
# Se utiliza para comprobar si una tarea ha sido completada o no.
# Incluye validaciones para asegurarse de que la tarea existe y pertenece al usuario.
class CheckDailyTaskSerializer(serializers.Serializer):
    """
    Serializador para verificar el estado de una tarea diaria. 
    """
    tarea_id = serializers.IntegerField()
    nombre_objetivo = serializers.SerializerMethodField()
    premio = serializers.SerializerMethodField()
    fecha_completado = serializers.SerializerMethodField()

    # ------------------------------------------------------------------------------
    # Validaciones alineadas con Objetivos de Tipo Cuantitativo
    # ------------------------------------------------------------------------------
    def validate_tarea_id(self, value):
        """
        Valida que la tarea exista y pertenezca al usuario.
        """
        user = self.context["request"].user
        hoy = date.today()

        objetivo = get_object_or_404(ObjetivoDiario, pk_objetivos_diarios=value, is_active=True)

        self.tarea, created = UsuarioObjetivoDiario.objects.get_or_create(
            fk_usuarios=user,
            fk_objetivos_diarios=objetivo,
            fecha_creacion=hoy
        )

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

# ------------------------------------------------------------------------------
# Canjeo de Tareas Diarias
# ------------------------------------------------------------------------------
# Serializador para canjear una tarea diaria.
class ExchangeDailyTaskSerializer(serializers.Serializer):
    """
    Serializador para canjear una tarea diaria. 
    """
    tarea_id = serializers.IntegerField()
    nombre_objetivo = serializers.SerializerMethodField()
    premio = serializers.SerializerMethodField()
    fecha_canjeado = serializers.SerializerMethodField()

    # ------------------------------------------------------------------------------
    # Validaciones alineadas con Objetivos de Tipo Cuantitativo
    # ------------------------------------------------------------------------------
    def validate_tarea_id(self, value):
        """
        Valida que la tarea exista, pertenezca al usuario y no haya sido canjeada.
        """
        user = self.context["request"].user
        hoy = date.today()

        objetivo = get_object_or_404(ObjetivoDiario, pk_objetivos_diarios=value, is_active=True)

        self.tarea = UsuarioObjetivoDiario.objects.filter(
            fk_usuarios=user,
            fk_objetivos_diarios=objetivo,
            fecha_creacion=hoy
        ).first()

        if not self.tarea:
            raise serializers.ValidationError("La tarea aún no ha sido registrada como completada.")
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
# # Objetivos Cualitativos
# ------------------------------------------------------------------------------
# Serializador para validar el cumplimiento de un objetivo cualitativo.
# Se utiliza para marcar como completado un objetivo cualitativo
# desde una acción externa (ej: login, subir foto).
class QualitativeObjectiveSerializer(serializers.Serializer):
    """
    Serializer para validar el cumplimiento de un objetivo cualitativo
    desde una acción externa (ej: login, subir foto).
    """
    requisito = serializers.CharField()

    def validate_requisito(self, value):
        user = self.context["request"].user

        # Buscar si existe un objetivo cualitativo activo para el usuario con ese requisito
        tarea = UsuarioObjetivoDiario.objects.filter(
            fk_usuarios=user,
            fecha_creacion=date.today(),
            fk_objetivos_diarios__tipo="cualitativo",
            fk_objetivos_diarios__requisito=value,
            fecha_completado__isnull=True
        ).first()

        if not tarea:
            raise serializers.ValidationError("No hay objetivo activo para este requisito.")

        self.tarea = tarea
        return value

    def completar(self):
        self.tarea.fecha_completado = timezone.now()
        self.tarea.save()
        return self.tarea

# ------------------------------------------------------------------------------
# Referidos
# ------------------------------------------------------------------------------
class ReferredUserSerializer(serializers.ModelSerializer):
    """
    Serializador para la visualización de usuarios referidos. 
    """
    fullName = serializers.SerializerMethodField()
    createdAt = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'fullName', 'createdAt')

    def get_fullName(self, obj):
        """
        Devuelve el nombre completo del usuario.
        """
        return f"{obj.nombre} {obj.apellidos}"
    
    def get_createdAt(self, obj):
        """
        Convertir datetime a date en formato dd/MM/yyyy
        """
        if obj.fecha_registro:
            return obj.fecha_registro.strftime("%d/%m/%Y")
        return None
    
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
    date = serializers.DateField(source="fecha")
    steps = serializers.IntegerField(source="pasos")

    class Meta:
        model = Pasos
        fields = ('date', 'steps')

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

# ------------------------------------------------------------------------------
# Perfil Público
# ------------------------------------------------------------------------------   
class PublicUserProfileSerializer(serializers.ModelSerializer):
    profilePicture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "name", "surname", "profilePicture", "monthlySteps", "leaderBoardPosition")

    name = serializers.CharField(source="nombre")
    surname = serializers.CharField(source="apellidos")
    monthlySteps = serializers.IntegerField(source="pasos_totales")

    leaderBoardPosition = serializers.SerializerMethodField()

    def get_profilePicture(self, obj):
        request = self.context.get("request")
        if obj.image and obj.image.nombre_logico:
            return f"http://3.17.152.152/media/public/{obj.image.nombre_logico}{obj.image.extension.strip('.') and '.' or ''}{obj.image.extension}"
        return None

    def get_leaderBoardPosition(self, obj):
        usuarios = User.objects.filter(is_staff=False).order_by('-pasos_totales').values_list('pk', flat=True)
        try:
            return list(usuarios).index(obj.pk) + 1
        except ValueError:
            return None

# ------------------------------------------------------------------------------
# FAQ
# ------------------------------------------------------------------------------
class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ("id", "question", "answer")

