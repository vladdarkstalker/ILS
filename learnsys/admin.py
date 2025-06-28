import csv
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group as AuthGroup
from django.http import HttpResponse
from django.utils.text import Truncator
from .models import (
    User, Course, Topic, StudyGroup, GroupMember,
    CourseMaterialPreference, TopicContent, Test, TestItem, TestItemOption,
    PsychologicalTestResult, TestResult, UserTestAnswer, TopicProgress, TestRetakePermission
)

# -------- Пример экшенов для UserAdmin --------
@admin.action(description="Сделать выбранных пользователей активными")
def make_users_active(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.action(description="Сделать выбранных пользователей staff-пользователями")
def make_users_staff(modeladmin, request, queryset):
    queryset.update(is_staff=True)
# ----------------------------------------------

# Отменяем регистрацию встроенной модели Group (группы прав)
admin.site.unregister(AuthGroup)

@admin.register(TestRetakePermission)
class TestRetakePermissionAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'test_title', 'allowed', 'granted_at')
    list_filter = ('allowed', 'test__topic__course')
    search_fields = ('user__username', 'user__given_name', 'user__surname', 'test__title')

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Пользователь'

    def test_title(self, obj):
        return obj.test.title
    test_title.short_description = 'Тест'

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'date_joined', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'given_name', 'surname')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личная информация', {
            'fields': ('email', 'surname', 'given_name', 'patronymic', 'group_number', 'date_of_birth')
        }),
        ('Разрешения', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ('date_joined',)

    # Ограничение доступа в админку (пример)
    def has_module_permission(self, request):
        # Доступ только для суперпользователей; при необходимости скорректируйте
        return request.user.is_superuser

    # Добавляем экшены к пользователям
    actions = [make_users_active, make_users_staff]

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Полное имя'

@admin.register(TopicProgress)
class TopicProgressAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'topic', 'status', 'started_at', 'completed_at', 'correct_answers', 'total_tests')
    list_filter = ('status', 'topic__course')
    search_fields = ('user__username', 'user__given_name', 'user__surname', 'topic__name', 'topic__course__name')

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Пользователь'

@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_enrolled_courses')
    search_fields = ('name', 'courses__name')
    fields = ('name', 'courses')

    def get_enrolled_courses(self, obj):
        return ", ".join([course.name for course in obj.courses.all()])
    get_enrolled_courses.short_description = 'Курсы'

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_instructor_name', 'description')
    search_fields = ('name', 'instructor__username', 'instructor__given_name', 'instructor__surname')
    list_filter = ('instructor',)

    def get_instructor_name(self, obj):
        return obj.instructor.get_full_name() if obj.instructor else "Нет преподавателя"
    get_instructor_name.short_description = 'Преподаватель'

@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'study_group')
    list_filter = ('study_group',)
    search_fields = ('user__username', 'user__given_name', 'user__surname', 'study_group__name')

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Участник'

@admin.register(CourseMaterialPreference)
class CourseMaterialPreferenceAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

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

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'description')
    list_filter = ('course',)
    search_fields = ('name', 'description')
    autocomplete_fields = ['course']

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic')
    list_filter = ('topic',)
    search_fields = ('title', 'topic__name')

@admin.register(TestItem)
class TestItemAdmin(admin.ModelAdmin):
    list_display = ('formatted_content', 'test', 'question_type', 'order_index')
    list_filter = ('test', 'question_type')
    search_fields = ('content',)

    def formatted_content(self, obj):
        return Truncator(obj.content).chars(50)
    formatted_content.short_description = 'Вопрос'

@admin.register(TestItemOption)
class TestItemOptionAdmin(admin.ModelAdmin):
    list_display = ('item', 'formatted_option', 'is_correct')
    list_filter = ('item__test', 'is_correct')
    search_fields = ('content',)

    def formatted_option(self, obj):
        return Truncator(obj.content).chars(50)
    formatted_option.short_description = 'Вариант ответа'

@admin.register(PsychologicalTestResult)
class PsychologicalTestResultAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'preference')
    list_filter = ('preference',)
    search_fields = ('user__username', 'user__given_name', 'user__surname', 'preference__name')

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Пользователь'

@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'test', 'score', 'total_questions', 'date_taken')
    list_filter = ('test', 'user')
    search_fields = ('user__username', 'user__given_name', 'user__surname', 'test__title')

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Пользователь'

@admin.register(UserTestAnswer)
class UserTestAnswerAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'item', 'text_answer', 'date_answered')
    list_filter = ('item__test', 'user')
    search_fields = ('user__username', 'user__given_name', 'user__surname', 'item__content')

    def user_full_name(self, obj):
        return obj.user.get_full_name()
    user_full_name.short_description = 'Пользователь'
<<<<<<< Updated upstream
=======

# ------------------- PsychTest, PsychQuestion, PsychAnswer, PsychTestResult -------------------

class PsychTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    list_filter = ('name',)

class PsychQuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'factor', 'test')
    search_fields = ('text',)
    list_filter = ('factor', 'test')

class PsychAnswerAdmin(admin.ModelAdmin):
    list_display = ('text', 'score', 'question')
    search_fields = ('text',)
    list_filter = ('score', 'question')

# --- Вот здесь мы добавляем экшен для PsychTestResultAdmin ---
@admin.register(PsychTestResult)
class PsychTestResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'factor', 'result', 'date_taken')
    search_fields = ('user__username',)
    list_filter = ('test', 'factor', 'date_taken')

    # Добавляем список действий
    actions = ['export_psych_test_results_csv']

    def export_psych_test_results_csv(self, request, queryset):
        """
        Экспортировать выбранные результаты из PsychTestResult в CSV.
        """
        if not queryset:
            self.message_user(request, "Не выбрано ни одной записи для экспорта.", level='error')
            return

        # Создаём CSV-ответ
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="psych_test_results.csv"'

        writer = csv.writer(response)
        # Записываем заголовки CSV-столбцов
        writer.writerow(['Пользователь', 'Тест', 'Фактор', 'Результат', 'Дата'])

        for result in queryset.select_related('user', 'test'):
            user_full_name = result.user.get_full_name()
            test_name = result.test.name
            writer.writerow([
                user_full_name,
                test_name,
                result.factor,
                result.result,
                result.date_taken.strftime('%Y-%m-%d %H:%M:%S')
            ])

        return response

    export_psych_test_results_csv.short_description = "Экспортировать выбранные результаты в CSV"

# ---------------------------------------------------------------------------

@admin.register(FactorInterpretation)
class FactorInterpretationAdmin(admin.ModelAdmin):
    list_display = ('factor_code', 'factor_name')
>>>>>>> Stashed changes
