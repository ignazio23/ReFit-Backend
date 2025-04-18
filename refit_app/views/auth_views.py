import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.status import (
    HTTP_200_OK, HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED
)
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from refit_app.models import User
from refit_app.serializers import (
    UserRegisterSerializer,
    LoginResponseSerializer,
    ChangePasswordSerializer,
)

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

logger = logging.getLogger(__name__)

# ============================================================================
# AUTH VIEWS – ReFit App
# Idioma: Código en inglés / Comentarios en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Este archivo contiene las vistas de autenticación para la API de ReFit.
#              Se incluyen docstrings detallados para cada vista y mensajes de error claros para producción.
# ============================================================================
# --------------------------------------------------------------------------
# Registro de usuario
# --------------------------------------------------------------------------
class RegisterView(APIView):
    """
    Permite registrar un nuevo usuario en la plataforma.
    Retorna la información del usuario en formato LoginResponseSerializer.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Registra un nuevo usuario con los datos proporcionados.
        Valida los datos y crea un nuevo usuario en la base de datos.
        """
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            logger.info("Usuario registrado exitosamente: %s", user.email)

            return Response({"message": "Usuario registrado exitosamente."}, status=HTTP_200_OK)
        
        logger.error("Error al registrar usuario: %s", serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

# --------------------------------------------------------------------------
# Inicio de sesión
# --------------------------------------------------------------------------
class LoginView(APIView):
    """
    Permite a un usuario autenticarse mediante email y contraseña.
    Actualiza 'first_login', 'ultimo_login' y 'lastlogin' con la fecha actual.
    Retorna la información del usuario en formato LoginResponseSerializer.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Autenticación de usuario mediante email y contraseña.
        Valida las credenciales y actualiza la información de inicio de sesión.
        """
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(email=email, password=password)

        if user:
            es_primer_login = user.first_login  # Captura el estado actual

            # Genera tokens de acceso y actualización
            tokens = RefreshToken.for_user(user)
            data = LoginResponseSerializer(user).data

            # Añade los tokens a la respuesta
            data["accessToken"] = str(tokens.access_token)
            data["refreshToken"] = str(tokens)

            # Luego de generar la respuesta, actualizamos
            if es_primer_login:
                user.first_login = False

            user.last_login = timezone.now()
            user.save()

            logger.info("Usuario autenticado: %s", user.email)
            return Response(data, status=HTTP_200_OK)
        
        logger.warning("Credenciales inválidas para el email: %s", email)
        return Response({"detail": "Credenciales inválidas."}, status=HTTP_401_UNAUTHORIZED)


# --------------------------------------------------------------------------
# Cierre de Sesión
# --------------------------------------------------------------------------
class LogOutView(APIView):
    """
    Cierra la sesión del usuario autenticado.
    Nota: Con JWT, la invalidación de tokens se gestiona mediante mecanismos adicionales.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Cierra la sesión del usuario autenticado.
        En el caso de JWT, se recomienda invalidar el token en el cliente.
        """
        logger.info("Cierre de sesión solicitado por: %s", request.user.email)
        return Response({"message": "Sesión cerrada con éxito."}, status=HTTP_200_OK)

# --------------------------------------------------------------------------
# Cambiar contraseña
# --------------------------------------------------------------------------
class ChangePasswordView(APIView):
    """
    Permite a un usuario autenticado cambiar su contraseña.
    Valida que la contraseña nueva sea distinta de la actual y cumpla los requisitos.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Cambia la contraseña del usuario autenticado.
        Valida la contraseña actual y establece la nueva contraseña.
        """
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            oldPassword  = serializer.validated_data['oldPassword ']
            newPassword = serializer.validated_data['newPassword']

            if not request.user.check_password(oldPassword ):
                logger.warning("Intento fallido de cambio de contraseña para: %s", request.user.email)
                return Response({"detail": "Contraseña actual incorrecta"}, status=HTTP_400_BAD_REQUEST)

            request.user.set_password(newPassword)
            request.user.update_password = False
            request.user.save()
            logger.info("Contraseña actualizada para el usuario: %s", request.user.email)
            return Response({"detail": "Contraseña actualizada exitosamente"}, status=HTTP_200_OK)
        logger.error("Error al cambiar contraseña para el usuario %s: %s", request.user.email, serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

# --------------------------------------------------------------------------
# Recuperar contraseña 
# --------------------------------------------------------------------------
class PasswordRecoveryView(APIView):
    """
    View para la recuperación de contraseña:
    - Si recibe solo email: genera nueva contraseña y la envía
    - Si recibe email + newPassword: actualiza la contraseña
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"error": "Debe ingresar un email."}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado."}, status=404)

        newPassword = User.objects.make_random_password()
        user.set_password(newPassword)
        user.update_password = True
        user.save()

        # Enviar email (activar backend real en producción)
        send_mail(
            subject="Recuperación de contraseña - ReFit",
            message=f"Tu nueva contraseña temporal es: {newPassword}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

        return Response({"message": "Se ha enviado una contraseña temporal a tu correo."}, status=200)