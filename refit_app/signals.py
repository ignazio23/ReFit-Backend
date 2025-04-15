from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Usuario, Canje

# ==========================================================================
# SIGNALS – ReFit App
# Idioma: Código en inglés / Comentarios y mensajes en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/08
# Descripción: Archivo donde se configurara la posibilidad de auditoría
#              de las acciones realizadas por los usuarios en la aplicación.
# ==========================================================================

# Auditoría de creación de usuario
@receiver(post_save, sender=Usuario)
def log_usuario_creado(sender, instance, created, **kwargs):
    if created:
        print(f"[AUDITORÍA] Usuario creado: {instance.email}")

# Aquí puedes agregar más lógica para registrar la acción en un archivo o base de datos
@receiver(post_save, sender=Canje)
def log_canje_creado(sender, instance, created, **kwargs):
    if created:
        print(f"[AUDITORÍA] Producto canjeado: {instance.fk_productos.nombre}")
