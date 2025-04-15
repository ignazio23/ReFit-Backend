from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext as _

# ==========================================================================
# MANAGERS – ReFit App
# Idioma: Código en inglés / Comentarios y mensajes en español
# Autor: Ignacio da Rosa – MVP 1 – 2025/03/20
# Descripción: Manager personalizado para el modelo de usuario. Permite
#              la creación de usuarios y superusuarios con campos extendidos.
# ==========================================================================

class UserManager(BaseUserManager):
    """
    Manager personalizado para el modelo de usuario.
    Permite la creación de usuarios y superusuarios con campos extendidos.
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Crea y devuelve un usuario con el correo electrónico y la contraseña dados.
        """
        if not email:
            raise ValueError(_('El correo electrónico es obligatorio'))
        if not password:
            raise ValueError(_('La contraseña es obligatoria'))
        if len(password) < 8:
            raise ValueError(_('La contraseña debe tener al menos 8 caracteres'))
        if not extra_fields.get("fecha_nacimiento"):
            raise ValueError(_('La fecha de nacimiento es obligatoria'))
        if not extra_fields.get("genero"):
            raise ValueError(_('El género es obligatorio'))

        # Sanitiza strings vacíos
        for key, value in extra_fields.items():
            if value == '':
                extra_fields[key] = None

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Crea y devuelve un superusuario con el correo electrónico y la contraseña dados.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not extra_fields.get('is_staff'):
            raise ValueError(_('El superusuario debe tener is_staff=True.'))
        if not extra_fields.get('is_superuser'):
            raise ValueError(_('El superusuario debe tener is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)