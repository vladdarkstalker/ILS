# learnsys/context_processors.py

from .utils import is_instructor, is_student

def user_role(request):
    return {
        'is_instructor': is_instructor(request.user) if request.user.is_authenticated else False,
        'is_student': is_student(request.user) if request.user.is_authenticated else False,
    }
