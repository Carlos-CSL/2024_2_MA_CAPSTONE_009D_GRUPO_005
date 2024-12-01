# naturalworld_d/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailBackend(ModelBackend):
    """
    Autentica al usuario utilizando el correo electrónico.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get('email')
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None
