# learnsys/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group as AuthGroup
from django.utils.text import Truncator
from .models import (
    User, Course, Topic, StudyGroup, GroupMember,
    CourseMaterialPreference, TopicContent, Test, TestItem, TestItemOption,
    PsychologicalTestResult, TestResult, UserTestAnswer
)

# Отменяем регистрацию встроенной модели Group (группы прав)
admin.site.unregister(AuthGroup)

# Регистрация модели пользователя с настройкой отображения
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'date_joined', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'given_name', 'surname')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личная информация', {'fields': ('email', 'surname', 'given_name', 'patronymic', 'group_number', 'date_of_birth')}),
        ('Разрешения', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ('date_joined',)
    
    # Ограничение доступа в админку
    def has_module_permission(self, request):
        # Доступ только для суперпользователей
        return request.user.is_superuser

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Полное имя'

# Регистрация модели учебной группы
@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_enrolled_courses')
    search_fields = ('name', 'courses__name')  # Обновлено для поиска по связанным курсам

    def get_enrolled_courses(self, obj):
        return ", ".join([course.name for course in obj.courses.all()])
    get_enrolled_courses.short_description = 'Курсы'

# Регистрация модели курса
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_instructor_name', 'description')
    search_fields = ('name', 'instructor__username', 'instructor__given_name', 'instructor__surname')
    list_filter = ('instructor',)

    def get_instructor_name(self, obj):
        return obj.instructor.get_full_name() if obj.instructor else "Нет преподавателя"
    get_instructor_name.short_description = 'Преподаватель'

# Регистрация модели участника учебной группы
@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'study_group')  # Удалено 'is_instructor'
    list_filter = ('study_group',)  # Удалено 'is_instructor'
    search_fields = ('user__username', 'user__given_name', 'user__surname', 'study_group__name')

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Участник'

# Регистрация модели предпочтений учебных материалов
@admin.register(CourseMaterialPreference)
class CourseMaterialPreferenceAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Регистрация модели содержания темы
@admin.register(TopicContent)
class TopicContentAdmin(admin.ModelAdmin):
    list_display = ('topic', 'content_type', 'order_index', 'get_short_content')
    list_filter = ('content_type', 'topic__course')
    search_fields = ('content', 'topic__name', 'topic__course__name')

    def get_short_content(self, obj):
        if obj.content:
            return Truncator(obj.content.name).chars(50)
        elif obj.text_content:
            return Truncator(obj.text_content).chars(50)
        return "Нет содержимого"
    get_short_content.short_description = 'Содержимое'

# Регистрация модели темы
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'description')
    list_filter = ('course',)
    search_fields = ('name', 'description')
    autocomplete_fields = ['course']

# Регистрация модели теста
@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic')
    list_filter = ('topic',)
    search_fields = ('title', 'topic__name')

# Регистрация модели вопроса теста
@admin.register(TestItem)
class TestItemAdmin(admin.ModelAdmin):
    list_display = ('formatted_content', 'test', 'question_type', 'order_index')
    list_filter = ('test', 'question_type')
    search_fields = ('content',)

    def formatted_content(self, obj):
        return Truncator(obj.content).chars(50)
    formatted_content.short_description = 'Вопрос'

# Регистрация модели вариантов ответов на вопросы теста
@admin.register(TestItemOption)
class TestItemOptionAdmin(admin.ModelAdmin):
    list_display = ('item', 'formatted_option', 'is_correct')
    list_filter = ('item__test', 'is_correct')
    search_fields = ('content',)

    def formatted_option(self, obj):
        return Truncator(obj.content).chars(50)
    formatted_option.short_description = 'Вариант ответа'

# Регистрация модели результатов психологического теста
@admin.register(PsychologicalTestResult)
class PsychologicalTestResultAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'preference')
    list_filter = ('preference',)
    search_fields = ('user__username', 'user__given_name', 'user__surname', 'preference__name')

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Пользователь'

# Регистрация модели результатов теста
@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'test', 'score', 'total_questions', 'date_taken')
    list_filter = ('test', 'user')
    search_fields = ('user__username', 'user__given_name', 'user__surname', 'test__title')

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Пользователь'

# Регистрация модели ответов пользователя на вопросы теста
@admin.register(UserTestAnswer)
class UserTestAnswerAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'item', 'option', 'text_answer', 'date_answered')
    list_filter = ('item__test', 'user')
    search_fields = ('user__username', 'user__given_name', 'user__surname', 'item__content')

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Пользователь'
