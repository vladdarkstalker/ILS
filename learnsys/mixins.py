# learnsys/mixins.py

from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy

class ActiveUserRequiredMixin(AccessMixin):
    """Миксин для проверки, что пользователь активен или является сотрудником."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            # Если пользователь не аутентифицирован, перенаправляем на страницу входа
            return self.handle_no_permission()
        if not (request.user.is_active or request.user.is_staff):
            # Если пользователь не активен и не является сотрудником, перенаправляем на главную
            messages.info(request, "Ваш аккаунт ожидает активации.")
            return redirect('learnsys:home')
        return super().dispatch(request, *args, **kwargs)
