from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

# ============================================================================
# STATUS VIEWS – ReFit App
# Idioma: Código en inglés / Comentarios en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/06
# Descripción: 
# ============================================================================

class RefreshTimestampView(APIView):
    """
    Actualiza el campo 'ultimo_login' del usuario con la hora actual
    y retorna el valor actualizado.
    Este endpoint se puede llamar para mantener actualizada la sesión
    y devolver la fecha/hora de última actividad.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Actualiza el campo 'ultimo_login' del usuario con la hora actual.
        """
        request.user.last_login  = timezone.now()
        request.user.save()
        return Response({
            "ultimo_login": request.user.ultimo_login
        })
