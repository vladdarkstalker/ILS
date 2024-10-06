# authentication_backends.py

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class CustomAuthBackend(ModelBackend):
    def user_can_authenticate(self, user):
        # Разрешаем аутентификацию для всех пользователей, включая неактивных
        return True
