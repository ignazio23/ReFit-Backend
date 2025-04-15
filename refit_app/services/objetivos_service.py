from datetime import date
from refit_app.models import Pasos

# ==========================================================================
# OBJETIVOS_SERVICES – ReFit App
# Idioma: Código en inglés / Comentarios y mensajes en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/08
# Descripción: Archivo donde se encuentran los servicios relacionados con los objetivos diarios.
# ==========================================================================

def puede_completar_objetivo(usuario_objetivo):
    """
    Verifica si el usuario tiene los pasos necesarios hoy para completar el objetivo.
    """
    pasos_hoy = Pasos.objects.filter(
        fk_usuarios=usuario_objetivo.fk_usuarios,
        fecha=date.today()
    ).first()

    if not pasos_hoy:
        return False

    return pasos_hoy.pasos >= usuario_objetivo.fk_objetivos_diarios.requisito