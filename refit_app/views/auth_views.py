import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.status import (
    HTTP_200_OK, HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND
)
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import uuid
from datetime import timedelta

from refit_app.models import User, PasswordRecovery
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
            # Validación de bloqueos y reactivación automática
            if not user.is_active:
                return Response({"detail": "Cuenta desactivada permanentemente."}, status=HTTP_401_UNAUTHORIZED)

            if user.bloqueated:
                if user.lock_date and timezone.now() - user.lock_date < timedelta(days=30):
                    user.bloqueated = False
                    user.lock_date = None
                    logger.info("Usuario %s reactivado durante el período de gracia.", user.email)
                else:
                    user.is_active = False
                    user.save()
                    logger.warning("Usuario %s intentó iniciar sesión tras el plazo de 30 días.", user.email)
                    return Response({"detail": "Cuenta eliminada permanentemente."}, status=HTTP_401_UNAUTHORIZED)

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
            oldPassword = serializer.validated_data['oldPassword']
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
            return Response({"error": "Debe ingresar un email."}, status=HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email, active=True)
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado o cuenta inactiva."}, status=HTTP_404_NOT_FOUND)

        # Crear token único
        token = uuid.uuid4().hex

        # Eliminar tokens anteriores (opcional, seguridad)
        PasswordRecovery.objects.filter(fk_usuario=user).delete()

        PasswordRecovery.objects.create(fk_usuario=user, token=token)

        # Construir y enviar el deep link
        deep_link = f"refit://reset-password?token={token}"

        subject = "Reestablecer Contraseña – ReFit"
        message = (
            f"Hola {user.nombre},\n\n"
            f"Recibimos una solicitud para restablecer tu contraseña.\n\n"
            f"Presioná el siguiente enlace desde tu dispositivo móvil para continuar:\n\n"
            f"{deep_link}\n\n"
            f"Este enlace expirará en 60 minutos.\n\n"
            f"Si no solicitaste este cambio, podés ignorar este mensaje.\n\n"
            f"El equipo de ReFit."
        )

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
        logger.info("Enlace de recuperación enviado a %s", email)

        return Response({"message": "Se ha enviado un enlace de recuperación a tu correo."}, status=HTTP_200_OK)

# --------------------------------------------------------------------------
# Restablecer contraseña mediante token
# --------------------------------------------------------------------------   
class ResetPasswordView(APIView):
    """
    Permite al usuario establecer una nueva contraseña usando el token enviado por email.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        nueva_password = request.data.get("newPassword")

        if not token or not nueva_password:
            return Response({"error": "Token y nueva contraseña son requeridos."}, status=HTTP_400_BAD_REQUEST)

        try:
            recovery = PasswordRecovery.objects.get(token=token)
        except PasswordRecovery.DoesNotExist:
            return Response({"error": "Token inválido o ya utilizado."}, status=HTTP_400_BAD_REQUEST)

        # Verificar vencimiento de 60 minutos
        tiempo_expiracion = recovery.created_at + timedelta(minutes=60)
        if timezone.now() > tiempo_expiracion:
            recovery.delete()
            return Response({"error": "El token ha expirado."}, status=HTTP_400_BAD_REQUEST)

        # Validaciones básicas de seguridad
        if len(nueva_password) < 8:
            return Response({"error": "La contraseña debe tener al menos 8 caracteres."}, status=HTTP_400_BAD_REQUEST)

        user = recovery.fk_usuario
        user.set_password(nueva_password)
        user.update_password = False
        user.save()

        # Eliminar token tras uso
        recovery.delete()

        logger.info("Contraseña actualizada mediante token para el usuario %s", user.email)
        return Response({"message": "Contraseña actualizada correctamente."}, status=HTTP_200_OK)
   