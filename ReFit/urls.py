from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# ==============================================================================
# URLS – ReFit
# Idioma: Código en inglés / Comentarios y mensajes en español
# Autor: Ignacio da Rosa – 2025/04/02
# Descripción:
# ==============================================================================

urlpatterns = [
    # Administración de Django
    path('admin/', admin.site.urls),

    # API pública agrupada bajo /api/rest/
    path('api/rest/', include('refit_app.urls')),

    # Endpoints JWT para autenticación por token
    #path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    #path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Configuración de encabezados del Admin de Django
admin.site.site_header = "ReFit"
admin.site.site_title = "ReFit"
admin.site.index_title = "Bienvenidos a ReFit"