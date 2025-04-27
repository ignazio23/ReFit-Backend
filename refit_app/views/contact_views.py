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

            subject = "Nuevo mensaje de contacto"
            user = request.user
            message = (
                f"Usuario: {user.nombre} {user.apellidos}\n"
                f"Email: {user.email}\n"
                f"Mensaje: {serializer.validated_data['message']}"
            )

            # (Aquí iría send_mail si tuvieras SMTP configurado)
            # send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [settings.SUPPORT_EMAIL])

            return Response({"message": "Mensaje enviado con éxito."}, status=HTTP_200_OK)
        
        logger.error("Error en el envío de contacto: %s", serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)