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
from datetime import timedelta, date
from django.core.mail import EmailMultiAlternatives

from refit_app.models import User, PasswordRecovery
from refit_app.serializers import (
    UserRegisterSerializer,
    LoginResponseSerializer,
    ChangePasswordSerializer,
    QualitativeObjectiveSerializer
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

            if user.blocked:
                if user.lock_date and timezone.now() - user.lock_date < timedelta(days=30):
                    user.blocked = False
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

            # Serializar datos del usuario
            serializer = LoginResponseSerializer(user)
            data = serializer.data

            data["accessToken"] = str(tokens.access_token)
            data["refreshToken"] = str(tokens)

            # Intentar marcar objetivo cualitativo como completado
            try:
                serializer = QualitativeObjectiveSerializer(
                    data={"requisito": "login"},
                    context={"request": request}
                )
                if serializer.is_valid():
                    for tarea in serializer.tareas_qualitativas:
                        tarea.fecha_completado = date.today()
                        tarea.save()
                    logger.info("Objetivo cualitativo 'login' completado para %s", user.email)
            except Exception as e:
                logger.warning("No se pudo completar objetivo cualitativo: %s", e)

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
# Recuperar Contraseña 
# --------------------------------------------------------------------------
class PasswordRecoveryView(APIView):
    """
    View para recuperación de contraseña:
    - Si recibe solo email: envía deep link por correo.
    - Si recibe email + newPassword + token: actualiza la contraseña.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        new_password = request.data.get("newPassword")
        token = request.data.get("token")

        # Recuperar contraseña: generación de deep link
        if email and not new_password and not token:
            try:
                user = User.objects.get(email=email, is_active=True)
            except User.DoesNotExist:
                return Response({"error": "Usuario no encontrado o cuenta inactiva."}, status=HTTP_404_NOT_FOUND)

            recovery_token = uuid.uuid4().hex
            PasswordRecovery.objects.filter(user=user).delete()
            PasswordRecovery.objects.create(user=user, token=recovery_token)

            # Nueva construcción del deep_link para mails
            deep_link = f"https://refit.lat/reset-password?token={recovery_token}"


            # Preparar el mail HTML
            subject = "Solicitud de restablecimiento de contraseña"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [email]

            text_content = (
                f"Este es un correo automático generado por ReFit.\n\n"
                f"Para restablecer tu contraseña, usa este enlace:\n{deep_link}\n\n"
                f"Si no solicitaste restablecer tu contraseña, puedes ignorar este mensaje.\n\n"
                f"¡Gracias por confiar en ReFit!"
            )

            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #333;">
                    <h2>Recuperación de contraseña</h2>
                    <p>Este es un correo automático generado por ReFit.</p>
                    <p>Hemos recibido tu solicitud para restablecer la contraseña de tu cuenta.</p>
                    <p>Para continuar, por favor haz clic en el siguiente botón:</p>
                    <p>
                        <a href="{deep_link}" 
                            style="display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; 
                                    text-decoration: none; border-radius: 5px;">
                            Restablecer contraseña
                        </a>
                    </p>
                    <p>Si no solicitaste este cambio, puedes ignorar este mensaje.</p>
                    <p>¡Gracias por confiar en ReFit!</p>
                </body>
            </html>
            """

            # Enviar email
            email_message = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
            email_message.attach_alternative(html_content, "text/html")
            email_message.send(fail_silently=False)

            logger.info("Deep link de recuperación enviado por correo HTML a %s", email)
            return Response(status=HTTP_200_OK)

        # Resetear contraseña usando token
        elif email and new_password and token:
            try:
                recovery = PasswordRecovery.objects.get(token=token)
            except PasswordRecovery.DoesNotExist:
                return Response({"error": "Token inválido o expirado."}, status=HTTP_400_BAD_REQUEST)

            if timezone.now() > (recovery.created_at + timedelta(minutes=60)):
                recovery.delete()
                return Response({"error": "El token ha expirado."}, status=HTTP_400_BAD_REQUEST)

            user = recovery.user

            if user.email != email:
                return Response({"error": "Email no coincide con el token."}, status=HTTP_400_BAD_REQUEST)

            if len(new_password) < 8:
                return Response({"error": "La nueva contraseña debe tener al menos 8 caracteres."}, status=HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.update_password = False
            user.save()

            recovery.delete()

            logger.info("Contraseña actualizada exitosamente para %s", email)
            return Response({"message": "Contraseña actualizada correctamente."}, status=HTTP_200_OK)

        else:
            return Response({"error": "Parámetros inválidos."}, status=HTTP_400_BAD_REQUEST)