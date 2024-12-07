# models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import Truncator
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone

class User(AbstractUser):
    surname = models.CharField("Фамилия", max_length=255, blank=True)
    given_name = models.CharField("Имя", max_length=255, blank=True)
    patronymic = models.CharField("Отчество", max_length=255, blank=True)
    group_number = models.CharField("Номер группы", max_length=50, blank=True)
    date_of_birth = models.DateField("Дата рождения", null=True, blank=True)

    def get_full_name(self):
        full_name = f"{self.surname} {self.given_name} {self.patronymic}".strip()
        return full_name or self.username

    def __str__(self):
        return self.get_full_name()

class Course(models.Model):
    name = models.CharField("Название курса", max_length=255, unique=True)
    description = models.TextField("Описание")
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')

    def calculate_progress(self, user):
        total_topics = self.topics.count()
        if total_topics == 0:
            return 0

        progress_sum = 0
        for topic in self.topics.all():
            topic_progress = TopicProgress.objects.filter(user=user, topic=topic).first()
            if topic_progress:
                reading_progress = 0.5 if topic_progress.started_reading else 0
                test_progress = (topic_progress.test_score_percentage() / 100) * 0.5 if topic_progress.test_completed else 0
                progress_sum += reading_progress + test_progress

        return round((progress_sum / total_topics) * 100, 2)

class StudyGroup(models.Model):
    name = models.CharField(max_length=100)
    courses = models.ManyToManyField(
        Course,
        related_name='study_groups',
        blank=True,
        verbose_name="Курсы"
    )

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        # Удалить всех участников группы
        self.group_members.all().delete()
        super().delete(*args, **kwargs)

class GroupMember(models.Model):
    study_group = models.ForeignKey(
        StudyGroup,
        on_delete=models.CASCADE,
        related_name='group_members',
        verbose_name="Учебная группа"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_group_memberships',
        verbose_name="Пользователь"
    )

    class Meta:
        unique_together = ('study_group', 'user')
        verbose_name = "Участник учебной группы"
        verbose_name_plural = "Участники учебных групп"

    def __str__(self):
        return f"{self.user.get_full_name()} (Студент) - {self.study_group.name}"

class Topic(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='topics', verbose_name="Курс")
    name = models.CharField("Название темы", max_length=255)
    description = models.TextField("Описание")
    parent_topic = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='subtopics', verbose_name="Родительская тема"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тема"
        verbose_name_plural = "Темы"

class TopicContent(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('text', 'Текст'),
        ('file', 'Файл'),
        ('image', 'Изображение'),
        ('video', 'Видео'),
        ('audio', 'Аудио'),
    ]

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='contents')
    content_type = models.CharField("Тип контента", max_length=50, choices=CONTENT_TYPE_CHOICES)
    content = models.FileField("Файл", upload_to='topic_contents/', blank=True, null=True)
    text_content = models.TextField("Текстовое содержимое", blank=True, null=True)
    order_index = models.PositiveIntegerField("Порядок отображения", default=0)
    generated_text = models.TextField("Сгенерированный текст", blank=True, null=True)  # Новое поле

    def __str__(self):
        return f"{self.get_content_type_display()} - {self.topic.name}"

    def clean(self):
        super().clean()
        if self.content_type == 'text' and not self.text_content:
            raise ValidationError('Пожалуйста, введите текстовое содержимое.')
        if self.content_type != 'text' and not self.content:
            raise ValidationError('Пожалуйста, загрузите файл для выбранного типа контента.')
        if self.content:
            if self.content_type == 'image' and not self.content.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                raise ValidationError('Пожалуйста, загрузите файл изображения.')
            elif self.content_type == 'video' and not self.content.name.lower().endswith(('.mp4', '.avi', '.mov')):
                raise ValidationError('Пожалуйста, загрузите видеофайл.')
            elif self.content_type == 'audio' and not self.content.name.lower().endswith(('.mp3', '.wav')):
                raise ValidationError('Пожалуйста, загрузите аудиофайл.')

    class Meta:
        verbose_name = "Материал темы"
        verbose_name_plural = "Материалы тем"

class Test(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='tests', verbose_name="Тема")
    title = models.CharField("Название теста", max_length=255)
    description = models.TextField("Описание теста", blank=True, null=True)
    allow_retakes = models.BooleanField("Разрешить повторное прохождение", default=False)  # Новое поле

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Тест"
        verbose_name_plural = "Тесты"

class TestItem(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('single_choice', 'Один вариант'),
        ('multiple_choice', 'Несколько вариантов'),
        ('text', 'Текстовый ответ'),
    ]

    source_content = models.ForeignKey(TopicContent, null=True, blank=True, on_delete=models.SET_NULL)
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='items', verbose_name="Тест")
    question_type = models.CharField("Тип вопроса", max_length=50, choices=QUESTION_TYPE_CHOICES)
    content = models.TextField("Вопрос")
    correct_text_answer = models.TextField("Правильный текстовый ответ", blank=True, null=True)
    order_index = models.PositiveIntegerField("Порядок отображения", default=0)

    def __str__(self):
        return f"{Truncator(self.content).chars(50)} (Тип: {self.get_question_type_display()})"

    class Meta:
        verbose_name = "Вопрос теста"
        verbose_name_plural = "Вопросы тестов"
        ordering = ['order_index']

class TestItemOption(models.Model):
    item = models.ForeignKey(TestItem, on_delete=models.CASCADE, related_name='options', verbose_name="Вопрос")
    content = models.CharField("Вариант ответа", max_length=255)
    is_correct = models.BooleanField("Правильный ответ", default=False)

    def __str__(self):
        return self.content

    class Meta:
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответов"

class UserTestAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    item = models.ForeignKey(TestItem, on_delete=models.CASCADE, verbose_name="Вопрос")
    option = models.ManyToManyField(TestItemOption, verbose_name="Выбранные варианты", blank=True)
    text_answer = models.TextField("Текстовый ответ", blank=True, null=True)
    date_answered = models.DateTimeField("Дата ответа", auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.item}"

    class Meta:
        verbose_name = "Ответ пользователя"
        verbose_name_plural = "Ответы пользователей"

class CourseMaterialPreference(models.Model):
    name = models.CharField("Название предпочтения", max_length=255, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Предпочтение учебного материала"
        verbose_name_plural = "Предпочтения учебных материалов"

class PsychologicalTestResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    preference = models.ForeignKey(CourseMaterialPreference, on_delete=models.CASCADE, verbose_name="Предпочтение")

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.preference.name}"

    class Meta:
        verbose_name = "Результат психологического теста"
        verbose_name_plural = "Результаты психологических тестов"
        unique_together = ('user', 'preference')

class TestResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, verbose_name="Тест", related_name='test_results')
    score = models.IntegerField("Количество правильных ответов", default=0)
    total_questions = models.IntegerField("Общее количество вопросов в тесте", default=0)
    date_taken = models.DateTimeField("Дата прохождения", auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.test.title}: {self.score}/{self.total_questions}"

    class Meta:
        verbose_name = "Результат теста"
        verbose_name_plural = "Результаты тестов"

class TopicProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='topic_progresses')
    topic = models.ForeignKey('Topic', on_delete=models.CASCADE, related_name='progress')
    started_reading = models.DateTimeField(null=True, blank=True)
    test_completed = models.BooleanField(default=False)
    correct_answers = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)

    STATUS_CHOICES = [
        ('not_started', 'Не начато'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершено'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='topic_progresses',
        verbose_name="Пользователь"
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='progresses',
        verbose_name="Тема"
    )
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started'
    )
    started_at = models.DateTimeField("Дата начала", auto_now_add=True)
    completed_at = models.DateTimeField("Дата завершения", null=True, blank=True)
    correct_answers = models.PositiveIntegerField("Количество правильных ответов", default=0)
    total_tests = models.PositiveIntegerField("Количество пройденных тестов", default=0)

    class Meta:
        unique_together = ('user', 'topic')
        verbose_name = "Прогресс по теме"
        verbose_name_plural = "Прогрессы по темам"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.topic.name} - {self.get_status_display()}"

    def mark_reading_started(self):
        if not self.started_reading:
            self.started_reading = timezone.now()
            self.save()

    def mark_test_completed(self, correct, total):
        self.test_completed = True
        self.correct_answers = correct
        self.total_questions = total
        self.save()

    def test_score_percentage(self):
        if self.total_questions > 0:
            return (self.correct_answers / self.total_questions) * 100
        return 0

class TestRetakePermission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )
    test = models.ForeignKey(
        'Test',
        on_delete=models.CASCADE,
        related_name='testretakepermission',  # Убедитесь, что related_name установлен как 'testretakepermission'
        verbose_name="Тест"
    )
    allowed = models.BooleanField("Разрешено повторное прохождение", default=False)
    granted_at = models.DateTimeField("Дата разрешения", default=timezone.now)

    class Meta:
        unique_together = ('user', 'test')
        verbose_name = "Разрешение на повторное прохождение теста"
        verbose_name_plural = "Разрешения на повторные прохождения тестов"

    def __str__(self):
        status = "Разрешено" if self.allowed else "Запрещено"
        return f"{self.user.get_full_name()} - {self.test.title}: {status}"


class PsychTest(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True)

class PsychQuestion(models.Model):
    test = models.ForeignKey(PsychTest, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    factor = models.CharField(max_length=2)  # Например, A, B, C, D...

class PsychAnswer(models.Model):
    question = models.ForeignKey(PsychQuestion, on_delete=models.CASCADE, related_name='answers')
    text = models.TextField()
    score = models.IntegerField()

class PsychTestResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results')
    test = models.ForeignKey(PsychTest, on_delete=models.CASCADE, related_name='results')
    factor = models.CharField(max_length=2)
    result = models.FloatField()
    date_taken = models.DateTimeField(auto_now_add=True)

    from django.db import models

from django.db import models

from django.db import models

class FactorInterpretation(models.Model):
    factor_code = models.CharField(max_length=10, unique=True)
    factor_name = models.CharField(max_length=100)
    value_interpretations = models.JSONField(default=dict)

    def get_interpretation(self, value):
        for interpretation in self.value_interpretations:
            min_value = interpretation['min_value']
            max_value = interpretation['max_value']
            if min_value <= value <= max_value:
                return interpretation['text']
        return "Интерпретация не найдена"