import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.status import (
    HTTP_200_OK, HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND
)
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import AccessToken
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
    Permite registrar un nuevo usuario con validación de código de referido.
    Envía un mail de activación tras un registro exitoso.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data.copy()

        # Validar código de referido (si viene)
        referral_code = data.get("referralCode")
        if referral_code:
            try:
                referente = User.objects.get(codigo_referido=referral_code, is_active=True)
                data["fk_usuario_referente"] = referente.pk
            except User.DoesNotExist:
                return Response({"error": "Código de referido inexistente."}, status=HTTP_400_BAD_REQUEST)

        serializer = UserRegisterSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()

            # Marcar cuenta como no verificada por email
            user.is_authenticated = False
            user.save()

            # Generar token y link de activación
            token = RefreshToken.for_user(user).access_token
            activation_link = f"https://refit.lat/activate-account?token={str(token)}"

            # Enviar mail de activación
            try:
                send_mail(
                    subject="Confirmá tu cuenta en ReFit",
                    message=(
                        f"¡Hola {user.nombre}!\n\n"
                        "Gracias por registrarte en ReFit.\n\n"
                        "Para activar tu cuenta, hacé clic en el siguiente enlace:\n\n"
                        f"{activation_link}\n\n"
                        "Si no te registraste, podés ignorar este mensaje."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )
            except Exception as e:
                logger.error(f"Error al enviar mail de activación: {e}")

            logger.info("Usuario registrado correctamente: %s", user.email)
            return Response({
                "message": "Registro exitoso. Por favor, activá tu cuenta desde el enlace enviado por correo."
            }, status=HTTP_200_OK)

        logger.warning("Error en el registro: %s | Errores: %s", request.data, serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

# --------------------------------------------------------------------------
# Activación de cuenta
# --------------------------------------------------------------------------
class ActivateAccountView(APIView):
    """
    Activa la cuenta del usuario mediante el token enviado por mail.
    Envía un segundo correo de bienvenida tras la activación.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token")

        if not token:
            return Response({"error": "Token faltante."}, status=HTTP_400_BAD_REQUEST)

        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            user = User.objects.get(pk=user_id)

            if user.is_authenticated:
                return Response({"message": "La cuenta ya fue activada."}, status=HTTP_200_OK)

            user.is_authenticated = True
            user.save()

            # Enviar mail de bienvenida
            try:
                send_mail(
                    subject="¡Bienvenido a ReFit!",
                    message=(
                        f"¡Hola {user.nombre}!\n\n"
                        "Tu cuenta fue activada con éxito.\n\n"
                        "Recordá tener instalada alguna app de seguimiento de pasos como:\n"
                        "- Google Fit (Android)\n"
                        "- Apple Health (iOS)\n"
                        "- Strava o Garmin (opcional)\n\n"
                        "⚠️ IMPORTANTE: Si no utilizás la app durante más de 30 días, tu cuenta puede ser desactivada automáticamente por seguridad.\n\n"
                        "¡Ya podés empezar a sumar pasos y ganar recompensas!"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )
            except Exception as e:
                logger.error(f"Error al enviar mail de bienvenida: {e}")

            logger.info("Cuenta activada para el usuario: %s", user.email)
            return Response({"message": "Cuenta activada correctamente."}, status=HTTP_200_OK)

        except Exception as e:
            logger.warning(f"Token inválido o expirado: {e}")
            return Response({"error": "Token inválido o expirado."}, status=HTTP_400_BAD_REQUEST)
        
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
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(email=email, password=password)

        if user:
            # Caso 1: Cuenta ya desactivada definitivamente
            if not user.is_active:
                logger.warning("Intento de login con cuenta desactivada: %s", user.email)
                return Response({"detail": "Cuenta eliminada permanentemente."}, status=HTTP_401_UNAUTHORIZED)

            # Caso 2: Usuario en proceso de eliminación lógica
            if user.blocked and user.lock_date:
                dias_pasados = timezone.now() - user.lock_date
                if dias_pasados < timedelta(days=30):
                    # Reactivación dentro del período de gracia
                    user.blocked = False
                    user.lock_date = None
                    user.save()
                    logger.info("Usuario %s reactivado dentro de los 30 días de gracia.", user.email)
                else:
                    # Eliminación definitiva
                    original_email = user.email
                    contador = 0
                    while True:
                        prefijo = f"UserInactive{contador}_" if contador > 0 else "UserInactive_"
                        nuevo_email = f"{prefijo}{original_email}"
                        if not User.objects.filter(email=nuevo_email).exists():
                            user.email = nuevo_email
                            break
                        contador += 1

                    user.is_active = False
                    user.save()

                    logger.warning("Usuario %s eliminado definitivamente tras 30 días.", original_email)
                    return Response({"detail": "Cuenta eliminada permanentemente. Deberás generar una nueva."}, status=HTTP_401_UNAUTHORIZED)

            # Resto del flujo normal
            es_primer_login = user.first_login

            tokens = RefreshToken.for_user(user)
            serializer = LoginResponseSerializer(user, context={'request': request})
            data = serializer.data
            data["accessToken"] = str(tokens.access_token)
            data["refreshToken"] = str(tokens)

            # Marcar objetivo cualitativo si corresponde
            try:
                obj_serializer = QualitativeObjectiveSerializer(data={"requisito": "login"}, context={"request": request})
                if obj_serializer.is_valid():
                    for tarea in obj_serializer.tareas_qualitativas:
                        tarea.fecha_completado = date.today()
                        tarea.save()
            except Exception as e:
                logger.warning("No se pudo completar objetivo cualitativo: %s", e)

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

            # Generar deep link
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