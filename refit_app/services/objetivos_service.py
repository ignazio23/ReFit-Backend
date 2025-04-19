from datetime import date
from refit_app.models import Pasos, UsuarioObjetivoDiario

# ==========================================================================
# OBJETIVOS_SERVICES – ReFit App
# Idioma: Código en inglés / Comentarios y mensajes en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/04/08
# Descripción: Archivo donde se encuentran los servicios relacionados con los objetivos diarios.
# ==========================================================================

def puede_completar_objetivo(usuario_objetivo):
    """
    Verifica si el usuario ha cumplido con el requisito del objetivo diario.
    Se separan las lógicas cuantitativas y cualitativas.
    """
    objetivo = usuario_objetivo.fk_objetivos_diarios
    tipo = getattr(objetivo, "tipo", "cuantitativo")  # fallback a cuantitativo

    if tipo == "cuantitativo":
        return evaluar_objetivo_cuantitativo(usuario_objetivo)
    
    elif tipo == "cualitativo":
        # No se valida directamente, queda para verificación externa
        return evaluar_objetivo_cualitativo(usuario_objetivo)

    return False  # Tipo desconocido

# --------------------------------------------------------------------------
# CUANTITATIVOS
# --------------------------------------------------------------------------
def evaluar_objetivo_cuantitativo(usuario_objetivo):
    """
    Evalúa si el usuario ha cumplido un objetivo cuantitativo (ej. pasos).
    """
    objetivo = usuario_objetivo.fk_objetivos_diarios
    usuario = usuario_objetivo.fk_usuarios

    if objetivo.requisito == "pasos":
        pasos_hoy = Pasos.objects.filter(fk_usuarios=usuario, fecha=date.today()).first()
        return pasos_hoy and pasos_hoy.pasos >= objetivo.valor_requerido

    # Podés agregar aquí otros tipos cuantitativos si se extiende el sistema
    # elif objetivo.requisito == "km":
    #     return distancia_hoy >= objetivo.valor_requerido

    return False


# --------------------------------------------------------------------------
# CUALITATIVOS
# --------------------------------------------------------------------------
def evaluar_objetivo_cualitativo(usuario_objetivo):
    """
    Evalúa un objetivo cualitativo (requiere que otro módulo confirme que se cumplió).
    Siempre devuelve False por defecto. El cumplimiento lo marca otro sistema.
    """
    return False


def marcar_objetivo_cualitativo_como_completado(user, codigo_requisito):
    """
    Marca como completado el objetivo cualitativo del día que coincide con el requisito.

    Uso:
        marcar_objetivo_cualitativo_como_completado(user, "login")
        marcar_objetivo_cualitativo_como_completado(user, "foto_perfil")
    """
    hoy = date.today()
    tareas = UsuarioObjetivoDiario.objects.filter(
        fk_usuarios=user,
        fecha_creacion=hoy,
        fk_objetivos_diarios__tipo="cualitativo",
        fk_objetivos_diarios__requisito=codigo_requisito,
        fecha_completado__isnull=True
    )

    for tarea in tareas:
        tarea.fecha_completado = date.today()
        tarea.save()