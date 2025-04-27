import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import IsAuthenticated

from refit_app.serializers import ContactUsSerializer

logger = logging.getLogger(__name__)

# ============================================================================
# CONTACT VIEWS – ReFit App
# Idioma: Código en inglés / Comentarios en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/02
# Descripción: Vista API para contacto con soporte o administración.
# ============================================================================
# --------------------------------------------------------------------------
# Contacto con Soporto o Administración
# --------------------------------------------------------------------------
class ContactUsView(APIView):
    """
    Recibe mensajes de contacto desde el frontend.
    Puede ser usado para soporte o feedback.
    Se ha añadido un placeholder para el envío de correo electrónico o almacenamiento en base de datos.
    Al activarse una dirección de correo electrónico, se enviará un correo al soporte.
    SUPPORT_EMAIL = 'soporte@refit.lat'
    DEFAULT_FROM_EMAIL = 'info@refit.lat'
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Maneja el envío de mensajes de contacto.
        Valida los datos y envía un correo electrónico al soporte.
        """
        serializer = ContactUsSerializer(data=request.data)
        if serializer.is_valid():
            # Aca seteamos de forma segura los datos del usuario autenticado
            user = request.user
            nombre = getattr(user, "nombre", "Usuario")
            apellidos = getattr(user, "apellidos", "")
            email = getattr(user, "email", "Sin email registrado")

            # Mensaje interno a Soporte
            support_subject = "Nuevo mensaje de contacto desde la app"
            support_message = (
                f"Usuario: {nombre} {apellidos}\n"
                f"Email: {email}\n"
                f"Mensaje:\n{serializer.validated_data['message']}"
            )
            send_mail(
                subject=support_subject,
                message=support_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.SUPPORT_EMAIL],
                fail_silently=False,
            )

            # Mensaje de confirmación al usuario
            user_subject = "¡Gracias por contactarte con ReFit!"
            user_message = (
                "Este es un correo automático para confirmar que hemos recibido tu mensaje.\n\n"
                "El equipo de ReFit leerá tu consulta y nos pondremos en contacto contigo a la brevedad posible.\n\n"
                "¡Gracias por confiar en nosotros!"
            )
            send_mail(
                subject=user_subject,
                message=user_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

            return Response({"message": "Mensaje enviado con éxito."}, status=HTTP_200_OK)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)