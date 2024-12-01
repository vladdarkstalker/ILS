from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views import generic
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Avg, Count, F
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView, View, TemplateView, FormView
)
from .forms import *
import difflib
from django.db.models import Sum
from .models import *
from django.contrib.auth import login, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.db.models import Avg, Count, F, Q, Prefetch
from django.urls import reverse, reverse_lazy
from .mixins import ActiveUserRequiredMixin
from .utils import is_instructor, is_student
from django.core.exceptions import PermissionDenied
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.views import PasswordChangeView
from django.contrib import messages
from django.db.models import Subquery, OuterRef, Max
from django.template.loader import render_to_string
import csv
from django.shortcuts import redirect
from django.contrib import messages
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Topic, Test, TestItem
from .utils.question_generation import generate_questions_from_text
# from .utils.question_generation import generate_questions_from_texts
import logging
import traceback
from django.utils import timezone
from .utils.content_processing import transcribe_audio, translate_ru_to_en, process_content
from .utils.translate_text import translate_ru_to_en
from .utils.content_processing import process_content
from .utils.question_answer_generation import generate_questions_and_answers
import logging
import traceback
from django.utils.text import Truncator
import logging
from langdetect import detect
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import PsychTest, PsychQuestion, PsychTestResult
from .forms import PsychTestForm
from .utils.calculate_factors import calculate_factors

logger = logging.getLogger('learnsys')

class TestResultDetailView(LoginRequiredMixin, DetailView):
    model = TestResult
    template_name = 'tests/test_result_detail.html'
    context_object_name = 'test_result'
    pk_url_kwarg = 'test_result_id'  # Specify the URL parameter for pk

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.user != self.request.user:
            raise PermissionDenied("У вас нет доступа к этому результату теста.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        test_result = self.object
        test = test_result.test

        # Get user answers
        user_answers = UserTestAnswer.objects.filter(
            user=self.request.user,
            item__test=test
        ).select_related('item')

        # Create a dictionary for quick access to user answers
        user_answers_dict = {answer.item.id: answer for answer in user_answers}

        # Get all test items
        test_items = test.items.prefetch_related('options')

        # Prepare data for display
        results = []
        for item in test_items:
            user_answer = user_answers_dict.get(item.id)
            correct_options = list(item.options.filter(is_correct=True))
            selected_options = user_answer.option.all() if user_answer else []
            correct = False

            if item.question_type in ['single_choice', 'multiple_choice']:
                correct = set(selected_options) == set(correct_options)
            elif item.question_type == 'text':
                correct = self.check_text_answer(
                    user_answer.text_answer,
                    item.correct_text_answer
                ) if user_answer else False

            results.append({
                'item': item,
                'user_answer': user_answer,
                'correct': correct,
                'correct_options': correct_options,  # Add correct options here
            })

        context['results'] = results
        return context

    def check_text_answer(self, user_answer, correct_answer):
        # Normalize and compare text answers
        normalized_user = ' '.join(user_answer.lower().split())
        normalized_correct = ' '.join(correct_answer.lower().split())

        if normalized_user == normalized_correct:
            return True

        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, normalized_user, normalized_correct).ratio()
        return similarity > 0.8  # Adjust similarity threshold if needed

logger = logging.getLogger(__name__)

class GenerateQuestionsView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, *args, **kwargs):
        topic_id = kwargs.get('pk')
        topic = get_object_or_404(Topic, pk=topic_id)

        # Проверяем права доступа
        if not (request.user == topic.course.instructor):
            messages.error(request, "У вас нет прав для выполнения этого действия.")
            logger.warning(f"Пользователь {request.user} попытался сгенерировать тест для темы {topic.id}, но не имеет прав.")
            return redirect('learnsys:topic_detail', pk=topic.id)

        # Собираем все материалы с обработанным текстом
        contents_with_generated_text = topic.contents.filter(generated_text__isnull=False)

        if not contents_with_generated_text.exists():
            messages.error(request, "Нет обработанных материалов для генерации вопросов.")
            logger.info(f"Для темы {topic.id} нет обработанных материалов.")
            return redirect('learnsys:topic_detail', pk=topic.id)

        all_questions_and_answers = []

        # Логируем список контента для отладки
        content_ids = contents_with_generated_text.values_list('id', 'content_type')
        logger.debug(f"Содержимое для генерации вопросов: {list(content_ids)}")

        # Генерируем вопросы и ответы из каждого материала
        for content in contents_with_generated_text:
            text = content.generated_text
            try:
                # Генерируем вопросы и ответы
                questions_and_answers = generate_questions_and_answers(text)
                if not questions_and_answers:
                    logger.info(f"Генерация вопросов для контента {content.id} не дала результатов.")
                    continue

                # Добавляем информацию о контенте к каждому вопросу и ответу
                for qa in questions_and_answers:
                    qa['content_id'] = content.id
                    qa['content_name'] = content.get_content_type_display()

                all_questions_and_answers.extend(questions_and_answers)
            except Exception as e:
                error_message = traceback.format_exc()
                logger.error(f"Ошибка при генерации вопросов для контента ID {content.id}: {error_message}")
                messages.error(request, f"Ошибка при генерации вопросов: {str(e)}")
                return redirect('learnsys:topic_detail', pk=topic.id)

        if not all_questions_and_answers:
            messages.error(request, f"Не удалось сгенерировать вопросы для темы '{topic.name}'.")
            logger.info(f"Генерация вопросов для темы {topic.id} не дала результатов.")
            return redirect('learnsys:topic_detail', pk=topic.id)

        # Создаём новый тест
        test_title = f"Тест по теме '{topic.name}' #{Test.objects.filter(topic=topic).count() + 1}"
        test = Test.objects.create(
            topic=topic,
            title=test_title,
            description='Автоматически сгенерированный тест'
        )
        logger.info(f"Создан новый тест '{test_title}' для темы {topic.id}.")

        # Создаём вопросы и ответы с информацией о контенте
        for idx, qa in enumerate(all_questions_and_answers, start=1):
            question_text = qa.get('question')
            correct_answer = qa.get('answer')
            content_id = qa.get('content_id')
            content_name = qa.get('content_name')

            if question_text and correct_answer:
                test_item = TestItem.objects.create(
                    test=test,
                    content=question_text,
                    question_type='text',
                    correct_text_answer=correct_answer,
                    source_content_id=content_id  # Убедитесь, что это поле существует и является ForeignKey
                )
                logger.debug(f"Создан вопрос {idx} из контента {content_id} ('{content_name}'): '{question_text}' с ответом: '{correct_answer}'.")
            else:
                logger.warning(f"Неполный QA-параметр: {qa}")

        messages.success(request, f"Вопросы и ответы для темы '{topic.name}' успешно сгенерированы и добавлены в тест '{test.title}'.")
        logger.info(f"Генерация вопросов для темы {topic.id} завершена успешно.")
        return redirect('learnsys:test_detail', pk=test.id)

    def test_func(self):
        topic = get_object_or_404(Topic, pk=self.kwargs.get('pk'))
        return self.request.user == topic.course.instructor

    def handle_no_permission(self):
        messages.error(self.request, "У вас нет прав для выполнения этого действия.")
        logger.warning(f"Пользователь {self.request.user} не имеет прав для генерации вопросов для темы {self.kwargs.get('pk')}.")
        return redirect('learnsys:topic_detail', pk=self.kwargs.get('pk'))

# Представления для тестов
# Удаление теста
class TestDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Test
    template_name = 'tests/test_confirm_delete.html'

    def test_func(self):
        test = self.get_object()
        return is_instructor(self.request.user) and test.topic.course.instructor == self.request.user

    def get_success_url(self):
        topic_id = self.object.topic.id
        messages.success(self.request, "Тест успешно удален.")
        return reverse_lazy('learnsys:test_list', kwargs={'topic_id': topic_id})

class TestItemCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = TestItem
    form_class = TestItemForm
    template_name = 'tests/testitem_form.html'

    def test_func(self):
        test = get_object_or_404(Test, id=self.kwargs.get('test_id'))
        return is_instructor(self.request.user) and test.topic.course.instructor == self.request.user

    def form_valid(self, form):
        test = get_object_or_404(Test, id=self.kwargs.get('test_id'))
        form.instance.test = test
        response = super().form_valid(form)
        messages.success(self.request, "Вопрос успешно добавлен.")
        return redirect('learnsys:testitem_add', test_id=test.id)

    def get_success_url(self):
        return reverse('learnsys:test_detail', kwargs={'pk': self.object.test.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        test = get_object_or_404(Test, id=self.kwargs.get('test_id'))
        context['test'] = test
        return context

class TestItemUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = TestItem
    form_class = TestItemForm
    template_name = 'tests/testitem_form.html'

    def test_func(self):
        test_item = self.get_object()
        return is_instructor(self.request.user) and test_item.test.topic.course.instructor == self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Вопрос успешно обновлён.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('learnsys:test_detail', kwargs={'pk': self.object.test.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['test'] = self.object.test
        return context

class TestItemDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = TestItem
    template_name = 'tests/testitem_confirm_delete.html'

    def test_func(self):
        test_item = self.get_object()
        return is_instructor(self.request.user) and test_item.test.topic.course.instructor == self.request.user

    def get_success_url(self):
        messages.success(self.request, "Вопрос успешно удалён.")
        return reverse('learnsys:test_detail', kwargs={'pk': self.object.test.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['test'] = self.object.test
        return context

class TestItemOptionCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = TestItemOption
    form_class = TestItemOptionForm
    template_name = 'tests/testitemoption_form.html'

    def test_func(self):
        test_item = get_object_or_404(TestItem, id=self.kwargs.get('item_id'))
        return is_instructor(self.request.user) and test_item.test.topic.course.instructor == self.request.user

    def form_valid(self, form):
        test_item = get_object_or_404(TestItem, id=self.kwargs.get('item_id'))
        form.instance.item = test_item
        response = super().form_valid(form)
        messages.success(self.request, "Вариант ответа успешно создан.")
        return redirect('learnsys:test_detail', pk=test_item.test.id)

    def get_success_url(self):
        return reverse('learnsys:test_detail', kwargs={'pk': self.object.item.test.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        test_item = get_object_or_404(TestItem, id=self.kwargs.get('item_id'))
        context['test_item'] = test_item
        return context

class TestItemOptionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = TestItemOption
    form_class = TestItemOptionForm
    template_name = 'tests/testitemoption_form.html'

    def test_func(self):
        option = self.get_object()
        return is_instructor(self.request.user) and option.item.test.topic.course.instructor == self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Вариант ответа успешно обновлён.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('learnsys:test_detail', kwargs={'pk': self.object.item.test.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['test_item'] = self.object.item
        return context

class TestItemOptionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = TestItemOption
    template_name = 'tests/testitemoption_confirm_delete.html'

    def test_func(self):
        option = self.get_object()
        return is_instructor(self.request.user) and option.item.test.topic.course.instructor == self.request.user

    def get_success_url(self):
        messages.success(self.request, "Вариант ответа успешно удалён.")
        return reverse('learnsys:test_detail', kwargs={'pk': self.object.item.test.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['test_item'] = self.object.item
        return context

class TestUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Test
    form_class = TestForm
    template_name = 'tests/test_form.html'

    def test_func(self):
        test = self.get_object()
        return is_instructor(self.request.user) and test.topic.course.instructor == self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Тест успешно обновлён.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('learnsys:test_list', kwargs={'topic_id': self.object.topic.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Make sure to pass the topic related to the test
        context['topic'] = self.object.topic
        return context

class TestDetailView(LoginRequiredMixin, DetailView):
    model = Test
    template_name = 'tests/test_detail.html'
    context_object_name = 'test'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if not user.is_staff:
            # Создаем или получаем прогресс по теме
            topic_progress, created = TopicProgress.objects.get_or_create(user=user, topic=obj.topic)  # Передаем obj.topic, чтобы передать объект Topic
            topic_progress.mark_reading_started()
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        test = self.get_object()
        
        # Получаем все вопросы теста
        context['test_items'] = test.items.all()

        # Проверка, является ли пользователь инструктором
        context['is_instructor'] = is_instructor(user) and test.topic.course.instructor == user

        # Проверка, прошел ли студент тест и имеет ли разрешение на ретейк
        has_taken_test = TestResult.objects.filter(user=user, test=test).exists()
        retake_permission = TestRetakePermission.objects.filter(user=user, test=test, allowed=True).exists()
        
        # Логика отображения формы для студента
        context['can_take_test'] = not has_taken_test or retake_permission
        if context['can_take_test']:
            context['form'] = TestAnswerForm(test_items=context['test_items'])
        
        # Последний результат теста для отображения
        context['test_result'] = TestResult.objects.filter(user=user, test=test).order_by('-date_taken').first()
        
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        user = request.user
        test = self.object

        # Проверка возможности прохождения теста студентом
        has_taken_test = TestResult.objects.filter(user=user, test=test).exists()
        retake_permission = TestRetakePermission.objects.filter(user=user, test=test, allowed=True).exists()

        if has_taken_test and not retake_permission:
            messages.error(request, "Вы уже прошли этот тест. Повторное прохождение возможно только с разрешения инструктора.")
            return redirect('learnsys:test_detail', pk=test.id)

        # Получаем вопросы теста и данные формы
        test_items = test.items.all()
        form = TestAnswerForm(request.POST, test_items=test_items)

        if form.is_valid():
            score = 0
            total_questions = test_items.count()

            # Сохраняем ответы и вычисляем баллы
            for item in test_items:
                field_name = f"item_{item.id}"
                user_answer = form.cleaned_data.get(field_name)

                if item.question_type == 'single_choice':
                    selected_options = [user_answer]
                    correct_options_ids = set(item.options.filter(is_correct=True).values_list('id', flat=True))
                    selected_options_ids = set(int(option_id) for option_id in selected_options)

                    if selected_options_ids == correct_options_ids:
                        score += 1

                    for option_id in selected_options:
                        option = item.options.get(id=option_id)
                        UserTestAnswer.objects.create(
                            user=user,
                            item=item,
                            option=option
                        )

                elif item.question_type == 'multiple_choice':
                    selected_options = user_answer
                    correct_options_ids = set(item.options.filter(is_correct=True).values_list('id', flat=True))
                    selected_options_ids = set(int(option_id) for option_id in selected_options)

                    if selected_options_ids == correct_options_ids:
                        score += 1

                    for option_id in selected_options:
                        option = item.options.get(id=option_id)
                        UserTestAnswer.objects.create(
                            user=user,
                            item=item,
                            option=option
                        )

                elif item.question_type == 'text':
                    UserTestAnswer.objects.create(
                        user=user,
                        item=item,
                        text_answer=user_answer
                    )
                    if self.check_text_answer(user_answer, item.correct_text_answer):
                        score += 1

            # Сохранение результата теста
            test_result = TestResult.objects.create(
                user=user,
                test=test,
                score=score,
                total_questions=total_questions,
                date_taken=timezone.now()
            )

            # Обновляем прогресс по теме
            topic_progress, created = TopicProgress.objects.get_or_create(user=user, topic=test.topic)
            topic_progress.mark_test_completed(score, total_questions)

            # Удаляем разрешение на повторное прохождение
            TestRetakePermission.objects.filter(user=user, test=test).delete()

            messages.success(request, f"Ваши ответы были сохранены. Ваш результат: {score}/{total_questions}.")

            # Перенаправляем на страницу результатов теста
            return redirect('learnsys:test_result_detail', test_result_id=test_result.id)

        return self.render_to_response(self.get_context_data(form=form))

    def check_text_answer(self, user_answer, correct_answer):
        """
        Проверка текстовых ответов с учетом регистра и пробелов.
        """
        normalized_user = ' '.join(user_answer.lower().split())
        normalized_correct = ' '.join(correct_answer.lower().split())

        if normalized_user == normalized_correct:
            return True

        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, normalized_user, normalized_correct).ratio()
        return similarity > 0.8  # Порог схожести можно настроить

class TakeTestAgainView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        test = get_object_or_404(Test, id=self.kwargs['test_id'])
        user = self.request.user
        course = test.topic.course
        return is_student(user) and course.study_groups.filter(group_members__user=user).exists()

    def post(self, request, *args, **kwargs):
        test = get_object_or_404(Test, id=self.kwargs['test_id'])
        user = request.user

        # Проверяем, разрешено ли повторное прохождение
        if not test.allow_retakes:
            messages.error(request, "Повторное прохождение этого теста запрещено.")
            return redirect('learnsys:test_detail', pk=test.id)

        # Проверяем, есть ли уже результаты теста
        # (зависит от логики, можно разрешить всегда проходить или ограничить количество попыток)
        # В данном случае разрешаем всегда

        return redirect('learnsys:test_detail', pk=test.id)

class ResetTestPermissionView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        test = get_object_or_404(Test, id=self.kwargs['test_id'])
        return is_instructor(self.request.user) and test.topic.course.instructor == self.request.user

    def post(self, request, *args, **kwargs):
        test = get_object_or_404(Test, id=self.kwargs['test_id'])
        student = get_object_or_404(User, id=self.kwargs['student_id'])

        # Вместо удаления результатов, разрешаем повторное прохождение
        test.allow_retakes = True
        test.save()

        messages.success(request, f"Студенту {student.get_full_name()} разрешено повторно пройти тест.")
        return redirect('learnsys:test_detail', pk=test.id)

class ManageTestRetakesView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'tests/manage_test_retakes.html'
    form_class = ManageTestRetakesForm

    def test_func(self):
        test = get_object_or_404(Test, id=self.kwargs['test_id'])
        return is_instructor(self.request.user) and test.topic.course.instructor == self.request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        test = get_object_or_404(Test, id=self.kwargs['test_id'])
        kwargs['test'] = test
        return kwargs

    def form_valid(self, form):
        test = get_object_or_404(Test, id=self.kwargs['test_id'])
        students = form.cleaned_data['students']

        # Создаем разрешения для выбранных студентов
        for student in students:
            TestRetakePermission.objects.update_or_create(
                user=student,
                test=test,
                defaults={'allowed': True}
            )

        messages.success(self.request, "Разрешение на повторное прохождение выдано выбранным студентам.")
        return redirect('learnsys:test_detail', pk=test.id)

class TestCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Test
    form_class = TestForm
    template_name = 'tests/test_form.html'

    def test_func(self):
        topic = get_object_or_404(Topic, id=self.kwargs['topic_id'])
        return is_instructor(self.request.user) and topic.course.instructor == self.request.user

    def form_valid(self, form):
        topic = get_object_or_404(Topic, id=self.kwargs['topic_id'])
        form.instance.topic = topic
        response = super().form_valid(form)
        messages.success(self.request, "Тест успешно создан. Теперь добавьте вопросы.")
        return redirect('learnsys:testitem_add', test_id=self.object.id)

    # Add or modify this method to ensure redirection
    def get_success_url(self):
        return reverse('learnsys:test_list', kwargs={'topic_id': self.object.topic.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        topic = get_object_or_404(Topic, id=self.kwargs['topic_id'])
        context['topic'] = topic
        return context

class TestListView(LoginRequiredMixin, ListView):
    model = Test
    template_name = 'tests/test_list.html'
    context_object_name = 'tests'

    def get_queryset(self):
        self.topic = get_object_or_404(Topic, id=self.kwargs['topic_id'])
        return Test.objects.filter(topic=self.topic)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['topic'] = self.topic
        return context

class StudentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = User
    template_name = 'instructor/student_detail.html'
    context_object_name = 'student'

    def test_func(self):
        user = self.request.user
        student = self.get_object()

        # Проверяем, что текущий пользователь является преподавателем
        if not is_instructor(user):
            return False

        # Получаем общие курсы между преподавателем и студентом
        common_courses = Course.objects.filter(
            instructor=user,
            study_groups__group_members__user=student
        ).distinct()

        # Проверяем, что есть хотя бы один общий курс
        return common_courses.exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.get_object()
        user = self.request.user

        # Получаем курсы, которые ведет преподаватель и на которые записан студент
        courses = Course.objects.filter(
            instructor=user,
            study_groups__group_members__user=student
        ).distinct()

        course_stats_list = []

        for course in courses:
            # Получаем все тесты курса
            tests = Test.objects.filter(topic__course=course)

            total_tests = tests.count()
            completed_tests = 0
            total_score = 0
            total_questions = 0

            test_results_list = []

            for test in tests:
                test_result = TestResult.objects.filter(user=student, test=test).order_by('-id').first()
                if test_result:
                    completed_tests += 1
                    total_score += test_result.score
                    total_questions += test_result.total_questions
                else:
                    total_questions += test.items.count()

                test_results_list.append({
                    'test': test,
                    'test_result': test_result,
                })

            if total_questions > 0:
                progress_percentage = round((total_score / total_questions) * 100, 2)
            else:
                progress_percentage = 0

            course_stats_list.append({
                'course': course,
                'progress_percentage': progress_percentage,
                'completed_tests': completed_tests,
                'total_tests': total_tests,
                'test_results_list': test_results_list,
            })

        context['course_stats_list'] = course_stats_list

        # Добавляем дополнительные данные о студенте
        context['group_number'] = student.group_number
        context['date_of_birth'] = student.date_of_birth
        context['material_preference'] = "Видео и интерактивные материалы"

        return context

class StudentListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = User
    template_name = 'instructor/student_list.html'
    context_object_name = 'students'

    def test_func(self):
        course = get_object_or_404(Course, id=self.kwargs.get('course_id'))
        return is_instructor(self.request.user) and course.instructor == self.request.user

    def get_queryset(self):
        user = self.request.user
        course_id = self.kwargs.get('course_id')
        course = get_object_or_404(Course, id=course_id, instructor=user)
        return User.objects.filter(
            user_group_memberships__study_group__courses=course
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs.get('course_id'))
        context['course'] = course
        return context

class GroupMembersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'instructor/group_members.html'

    def test_func(self):
        course = get_object_or_404(Course, id=self.kwargs.get('course_id'))
        return is_instructor(self.request.user) and course.instructor == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs.get('course_id'))
        group = get_object_or_404(StudyGroup, id=self.kwargs.get('pk'))
        context['course'] = course
        context['group'] = group
        context['members'] = group.group_members.select_related('user')
        return context

class CourseGroupsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = StudyGroup
    template_name = 'courses/course_groups.html'
    context_object_name = 'groups'

    def test_func(self):
        course = get_object_or_404(Course, id=self.kwargs.get('pk'))
        user = self.request.user
        if is_instructor(user) and course.instructor == user:
            return True
        elif is_student(user) and course.study_groups.filter(group_members__user=user).exists():
            return True
        else:
            return False

    def get_queryset(self):
        course = get_object_or_404(Course, id=self.kwargs.get('pk'))
        return course.study_groups.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs.get('pk'))
        context['course'] = course
        context['is_instructor'] = is_instructor(self.request.user)
        return context

class CourseDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Course
    template_name = 'instructor/course_confirm_delete.html'
    success_url = reverse_lazy('learnsys:instructor_dashboard')

    def test_func(self):
        course = self.get_object()
        return course.instructor == self.request.user

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Курс успешно удалён.")
        return super().delete(request, *args, **kwargs)

class CourseUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'instructor/course_form.html'

    def test_func(self):
        return is_instructor(self.request.user) and self.get_object().instructor == self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Курс успешно обновлён.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('learnsys:instructor_dashboard')

class CourseCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'instructor/course_form.html'

    def test_func(self):
        return is_instructor(self.request.user)

    def form_valid(self, form):
        form.instance.instructor = self.request.user
        messages.success(self.request, "Курс успешно создан.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('learnsys:instructor_dashboard')

class InstructorCoursesView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'

    def test_func(self):
        return is_instructor(self.request.user)

    def get_queryset(self):
        return Course.objects.filter(instructor=self.request.user)

# Представления для дашборда студента
@method_decorator(login_required, name='dispatch')
class StudentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'student/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if not is_student(user):
            messages.error(self.request, "У вас нет доступа к этой странице.")
            return context

        # Получаем курсы, в которых студент состоит через группы
        courses = Course.objects.filter(study_groups__group_members__user=user).distinct()
        context['courses'] = courses

        # Собираем статистику для каждого курса
        course_stats = []
        for course in courses:
            topics = course.topics.all()
            total_topics = topics.count()
            completed_topics = topics.filter(progresses__user=user, progresses__status='completed').distinct().count()

            # Прогресс курса в процентах
            if total_topics > 0:
                progress_percentage = round((completed_topics / total_topics) * 100, 2)
            else:
                progress_percentage = 0

            course_stats.append({
                'course': course,
                'progress_percentage': progress_percentage,
                'completed_topics': completed_topics,
                'total_topics': total_topics,
            })

        context['course_stats'] = course_stats
        return context

# Представления для дашборда преподавателя
@method_decorator(login_required, name='dispatch')
class InstructorDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'instructor/dashboard.html'

    def test_func(self):
        return is_instructor(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Получить все курсы, созданные текущим преподавателем
        courses = Course.objects.filter(instructor=user)

        # Получить все группы, связанные с этими курсами
        groups = StudyGroup.objects.filter(courses__in=courses).distinct()

        context['courses'] = courses
        context['groups'] = groups

        return context

class TopicContentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = TopicContent
    template_name = 'topics/topiccontent_confirm_delete.html'

    def test_func(self):
        topic_content = self.get_object()
        return is_instructor(self.request.user) and topic_content.topic.course.instructor == self.request.user

    def get_success_url(self):
        messages.success(self.request, "Материал успешно удален.")
        return reverse('learnsys:topic_detail', kwargs={'pk': self.object.topic.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['topic'] = self.object.topic
        return context

class TopicContentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = TopicContent
    form_class = TopicContentForm
    template_name = 'topics/topiccontent_form.html'

    def test_func(self):
        topic_content = self.get_object()
        return is_instructor(self.request.user) and topic_content.topic.course.instructor == self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)

        # После сохранения контента выполняем обработку
        try:
            success, message = process_content(form.instance)
            if success:
                messages.success(self.request, message)
                logger.info(f"Контент ID {form.instance.id} успешно обработан.")
            else:
                messages.error(self.request, message)
                logger.error(f"Ошибка при обработке контента ID {form.instance.id}: {message}")
        except Exception as e:
            messages.error(self.request, f"Неизвестная ошибка при обработке контента: {e}")
            logger.error(f"Неизвестная ошибка при обработке контента ID {form.instance.id}: {e}", exc_info=True)

        return response

    def get_success_url(self):
        return reverse('learnsys:topic_detail', kwargs={'pk': self.object.topic.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['topic'] = self.object.topic
        return context

class TopicContentCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = TopicContent
    form_class = TopicContentForm
    template_name = 'topics/topiccontent_form.html'

    def test_func(self):
        topic = get_object_or_404(Topic, id=self.kwargs.get('topic_id'))
        return self.request.user == topic.course.instructor

    def form_valid(self, form):
        topic = get_object_or_404(Topic, id=self.kwargs.get('topic_id'))
        form.instance.topic = topic

        response = super().form_valid(form)

        # После сохранения контента выполняем обработку
        try:
            success, message = process_content(form.instance)
            if success:
                messages.success(self.request, message)
                logger.info(f"Контент ID {form.instance.id} успешно обработан.")
            else:
                messages.error(self.request, message)
                logger.error(f"Ошибка при обработке контента ID {form.instance.id}: {message}")
        except Exception as e:
            messages.error(self.request, f"Неизвестная ошибка при обработке контента: {e}")
            logger.error(f"Неизвестная ошибка при обработке контента ID {form.instance.id}: {e}", exc_info=True)

        return response

    def get_success_url(self):
        return reverse('learnsys:topic_detail', kwargs={'pk': self.object.topic.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        topic = get_object_or_404(Topic, id=self.kwargs.get('topic_id'))
        context['topic'] = topic
        return context

# Представление для домашней страницы
def home_page(request):
    if not request.user.is_authenticated:
        return render(request, 'welcome.html')
    else:
        user = request.user
        if user.is_superuser:
            # Для администратора отображаем страницу welcome.html
            return render(request, 'welcome.html')
        elif is_instructor(user):
            return redirect('learnsys:instructor_dashboard')
        elif is_student(user):
            return redirect('learnsys:student_dashboard')
        else:
            messages.info(request, "Ваш аккаунт ожидает активации.")
            return render(request, 'welcome.html')

# Представление для входа пользователя
class UserLoginView(LoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser:
            return reverse_lazy('admin:index')  # Redirect to the admin panel
        elif is_student(user):
            return reverse_lazy('learnsys:student_dashboard')
        elif is_instructor(user):
            return reverse_lazy('learnsys:instructor_dashboard')
        else:
            return reverse_lazy('learnsys:home')

# Представление для регистрации пользователя
class UserRegisterView(CreateView):
    form_class = UserRegisterForm
    template_name = 'registration/register.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        # Деактивируем пользователя после регистрации
        self.object.is_active = False
        self.object.save()
        messages.success(self.request, "Регистрация прошла успешно. Пожалуйста, дождитесь активации аккаунта администратором.")
        return response

    def get_success_url(self):
        return reverse('learnsys:home')

# Представление профиля пользователя
class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

# Представление профиля пользователя
@method_decorator(login_required, name='dispatch')
class UserProfileView(TemplateView):
    template_name = 'user/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_groups = GroupMember.objects.filter(user=self.request.user).select_related('study_group')
        context['is_instructor'] = is_instructor(self.request.user)
        context['group'] = user_groups.first().study_group if user_groups.exists() else None
        return context

class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'profile/password_change.html'
    success_url = reverse_lazy('learnsys:profile')

    def form_valid(self, form):
        messages.success(self.request, 'Ваш пароль был успешно изменен.')
        return super().form_valid(form)

# Представление для обновления профиля пользователя
@method_decorator(login_required, name='dispatch')
class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = 'profile/profile_update.html'
    success_url = reverse_lazy('learnsys:profile')

    def get_object(self, queryset=None):
        return self.request.user

# Представления для курсов
class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        user = self.request.user
        if is_instructor(user):
            return Course.objects.filter(instructor=user).distinct()
        elif is_student(user):
            return Course.objects.filter(study_groups__group_members__user=user).distinct()
        else:
            return Course.objects.none()

    def get_template_names(self):
        user = self.request.user
        if is_instructor(user):
            return ['instructor/course_list.html']
        elif is_student(user):
            return ['courses/course_list.html']
        else:
            return ['courses/course_list.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if is_instructor(user):
            context['role'] = 'instructor'
        elif is_student(user):
            context['role'] = 'student'
        return context


class GroupCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = StudyGroup
    form_class = GroupForm
    template_name = 'groups/group_form.html'

    def test_func(self):
        user = self.request.user
        return user.is_superuser or is_instructor(user)

    def get_form_kwargs(self):
        kwargs = super(GroupCreateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user  # Передаём пользователя в форму для фильтрации курсов
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Группа успешно создана.")
        return response

    def get_success_url(self):
        return reverse('learnsys:group_detail', kwargs={'pk': self.object.pk})

# Представление для добавления участника в группу
class AddGroupMemberView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = GroupMember
    form_class = AddGroupMemberForm
    template_name = 'groups/add_member.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = get_object_or_404(StudyGroup, id=self.kwargs.get('group_id'))
        context['group'] = group
        context['courses'] = group.courses.all()  # Получаем все связанные курсы
        return context

    def test_func(self):
        user = self.request.user
        group = get_object_or_404(StudyGroup, id=self.kwargs.get('group_id'))
        return user.is_superuser or (is_instructor(user) and group.courses.filter(instructor=user).exists())

    def form_valid(self, form):
        # Проверка, состоит ли студент в какой-либо группе
        student = form.cleaned_data['user']
        if GroupMember.objects.filter(user=student).exists():
            form.add_error('user', 'Этот студент уже состоит в другой группе.')
            return self.form_invalid(form)

        group = get_object_or_404(StudyGroup, id=self.kwargs.get('group_id'))
        form.instance.study_group = group

        messages.success(self.request, "Участник успешно добавлен в группу.")
        return super().form_valid(form)

    def get_success_url(self):
        group_id = self.kwargs.get('group_id')
        return reverse('learnsys:group_detail', kwargs={'pk': group_id})

class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user

        if is_instructor(user) and obj.instructor == user:
            return obj
        elif is_student(user) and obj.study_groups.filter(group_members__user=user).exists():
            return obj
        else:
            raise PermissionDenied("У вас нет доступа к этому курсу.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['topics'] = self.object.topics.all()
        context['is_instructor'] = is_instructor(self.request.user)

        if is_instructor(self.request.user):
            # Получаем группы, связанные с курсом и текущим преподавателем
            context['groups'] = self.object.study_groups.filter(courses__instructor=self.request.user).distinct()
        else:
            # Получаем группы, связанные с курсом, где состоит студент
            context['groups'] = self.object.study_groups.filter(
                group_members__user=self.request.user
            ).distinct()
        return context

class GroupListView(LoginRequiredMixin, ListView):
    model = StudyGroup
    template_name = 'groups/group_list.html'
    context_object_name = 'groups'

    def get_queryset(self):
        user = self.request.user
        if is_instructor(user):
            # Преподаватель видит группы, связанные с его курсами
            return StudyGroup.objects.filter(courses__instructor=user).distinct()
        elif is_student(user):
            return StudyGroup.objects.filter(group_members__user=user).distinct()
        elif user.is_superuser:
            return StudyGroup.objects.all()
        else:
            return StudyGroup.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_instructor'] = is_instructor(self.request.user)
        return context

class GroupDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = StudyGroup
    template_name = 'groups/group_detail.html'
    context_object_name = 'group'

    def test_func(self):
        group = self.get_object()
        user = self.request.user
        if user.is_superuser:
            return True
        elif is_instructor(user):
            # Проверяем, связан ли преподаватель с курсами этой группы
            return group.courses.filter(instructor=user).exists()
        elif is_student(user):
            return group.group_members.filter(user=user).exists()
        else:
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.object
        user = self.request.user
        context['is_instructor'] = is_instructor(user)
        if context['is_instructor']:
            # Отображаем все курсы группы, связанных с преподавателем
            context['courses'] = group.courses.filter(instructor=user)
            # Отображаем всех членов группы без дополнительной фильтрации
            context['members'] = group.group_members.select_related('user')
        else:
            context['courses'] = group.courses.all()
            context['members'] = group.group_members.select_related('user')
        return context

class DownloadStudentInfoView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        user = self.request.user
        student_id = self.kwargs.get('pk')
        student = get_object_or_404(User, id=student_id)

        # Проверяем, что текущий пользователь является преподавателем
        if not is_instructor(user):
            return False

        # Получаем общие курсы между преподавателем и студентом
        common_courses = Course.objects.filter(
            instructor=user,
            study_groups__group_members__user=student
        ).distinct()

        return common_courses.exists()

    def get(self, request, *args, **kwargs):
        student_id = self.kwargs.get('pk')
        student = get_object_or_404(User, id=student_id)

        # Создаём CSV-файл
        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="student_{student.id}_info.csv"'},
        )

        writer = csv.writer(response)
        writer.writerow(['Поле', 'Значение'])
        writer.writerow(['ФИО', student.get_full_name()])
        writer.writerow(['Email', student.email])
        writer.writerow(['Номер группы', student.group_number])

        # Проверка на наличие даты рождения
        formatted_dob = student.date_of_birth.strftime('%d.%m.%Y') if student.date_of_birth else 'Не указано'
        writer.writerow(['Дата рождения', formatted_dob])

        # Отчество
        patronymic = student.patronymic if student.patronymic else 'Не указано'
        writer.writerow(['Отчество', patronymic])

        # Добавляем статистику по тестам
        test_results = TestResult.objects.filter(user=student).select_related('test')
        writer.writerow([])  # Пустая строка для разделения
        writer.writerow(['Тест', 'Баллы', 'Всего вопросов', 'Дата прохождения'])

        for result in test_results:
            writer.writerow([result.test.title, result.score, result.total_questions, result.date_taken.strftime('%d.%m.%Y %H:%M')])

        return response

class GroupUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = StudyGroup
    form_class = GroupForm
    template_name = 'groups/group_form.html'

    def test_func(self):
        user = self.request.user
        group = self.get_object()
        return user.is_superuser or (is_instructor(user) and group.courses.filter(instructor=user).exists())

    def get_form_kwargs(self):
        kwargs = super(GroupUpdateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user  # Передаём пользователя в форму для фильтрации курсов
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Группа успешно обновлена.")
        return response

    def get_success_url(self):
        return reverse('learnsys:group_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_ids = self.object.courses.values_list('id', flat=True)
        context['course_ids'] = list(course_ids)
        return context

class GroupDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = StudyGroup
    template_name = 'groups/group_confirm_delete.html'

    def test_func(self):
        user = self.request.user
        group = self.get_object()
        return user.is_superuser or (is_instructor(user) and group.courses.filter(instructor=user).exists())

    def get_success_url(self):
        messages.success(self.request, "Группа успешно удалена.")
        return reverse('learnsys:group_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.get_object()
        context['group'] = group
        return context

# Представления для тем
class TopicListView(LoginRequiredMixin, ListView):
    model = Topic
    template_name = 'topics/topic_list.html'
    context_object_name = 'topics'

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return Topic.objects.filter(course_id=course_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs.get('course_id')
        course = get_object_or_404(Course, id=course_id)
        context['course'] = course
        context['is_instructor'] = is_instructor(self.request.user) and course.instructor == self.request.user
        context['is_student'] = is_student(self.request.user) and not context['is_instructor']
        return context

class TopicDetailView(LoginRequiredMixin, DetailView):
    model = Topic
    template_name = 'topics/topic_detail.html'
    context_object_name = 'topic'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if not user.is_staff:
            # Создаем или получаем прогресс по теме
            topic_progress, created = TopicProgress.objects.get_or_create(user=user, topic=obj)
            topic_progress.mark_reading_started()
        return obj

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if not user.is_staff:
            # Создаем или получаем прогресс по теме
            topic_progress, created = TopicProgress.objects.get_or_create(user=user, topic=obj)
            topic_progress.mark_reading_started()
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contents'] = self.object.contents.all()
        user = self.request.user
        context['is_instructor'] = is_instructor(user) and self.object.course.instructor == user
        context['is_student'] = is_student(user) and not context['is_instructor']
        
        # Отслеживание начала изучения темы
        if is_student(user):
            progress, created = TopicProgress.objects.get_or_create(user=user, topic=self.object)
            if created or progress.status == 'not_started':
                progress.status = 'in_progress'
                progress.started_at = timezone.now()
                progress.save()

        return context

class TopicCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Topic
    form_class = TopicForm
    template_name = 'topics/topic_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        course = get_object_or_404(Course, id=self.kwargs.get('course_id'))
        kwargs['current_course'] = course
        return kwargs

    def test_func(self):
        course = get_object_or_404(Course, id=self.kwargs.get('course_id'))
        return is_instructor(self.request.user) and course.instructor == self.request.user

    def form_valid(self, form):
        course = get_object_or_404(Course, id=self.kwargs.get('course_id'))
        form.instance.course = course
        return super().form_valid(form)

    def get_success_url(self):
        course_id = self.object.course.id
        return reverse('learnsys:course_detail', kwargs={'pk': course_id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(Course, id=self.kwargs.get('course_id'))
        context['course'] = course
        return context

class RemoveGroupMemberView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = GroupMember
    template_name = 'groups/remove_member_confirm.html'

    def test_func(self):
        user = self.request.user
        group_member = self.get_object()
        group = group_member.study_group
        return user.is_superuser or (is_instructor(user) and group.courses.filter(instructor=user).exists())

    def get_success_url(self):
        messages.success(self.request, "Участник успешно удалён из группы.")
        return reverse('learnsys:group_detail', kwargs={'pk': self.object.study_group.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.object.study_group
        context['group'] = group
        return context

class TopicUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Topic
    form_class = TopicForm
    template_name = 'topics/topic_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        course = self.object.course
        kwargs['current_course'] = course
        return kwargs

    def test_func(self):
        topic = self.get_object()
        return is_instructor(self.request.user) and topic.course.instructor == self.request.user

    def get_success_url(self):
        return reverse('learnsys:course_detail', kwargs={'pk': self.object.course.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.course
        return context

class TopicDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Topic
    template_name = 'topics/topic_confirm_delete.html'

    def test_func(self):
        topic = self.get_object()
        return is_instructor(self.request.user) and topic.course.instructor == self.request.user

    def get_success_url(self):
        messages.success(self.request, "Тема успешно удалена.")
        return reverse('learnsys:course_detail', kwargs={'pk': self.object.course.id})

def psych_test_list(request):
    tests = PsychTest.objects.all()
    return render(request, 'psych/test_list.html', {'tests': tests})

def psych_take_test(request, test_id):
    test = get_object_or_404(PsychTest, id=test_id)
    questions = test.questions.prefetch_related('answers')

    if request.method == 'POST':
        form = PsychTestForm(request.POST, questions=questions)
        if form.is_valid():
            user_answers = {int(key.split('_')[1]): int(value) for key, value in form.cleaned_data.items()}

            # Определяем, какие факторы пересчитать
            target_factors = test.questions.values_list('factor', flat=True).distinct()

            # Вызываем calculate_factors с ограничением на факторы
            result_data = calculate_factors(user_answers, test, target_factors)

            for factor, result in result_data.items():
                existing_result = PsychTestResult.objects.filter(
                    user=request.user, test=test, factor=factor
                ).first()

                if existing_result:
                    existing_result.result = result
                    existing_result.save()
                else:
                    PsychTestResult.objects.create(
                        user=request.user,
                        test=test,
                        factor=factor,
                        result=result
                    )

            return redirect('learnsys:psych_test_result', test_id=test.id)
    else:
        form = PsychTestForm(questions=questions)

    return render(request, 'psych/take_test.html', {'form': form, 'test': test})

def psych_test_results(request, test_id):
    test = get_object_or_404(PsychTest, id=test_id)
    results = PsychTestResult.objects.filter(user=request.user, test=test)
    return render(request, 'psych/test_result.html', {'test': test, 'results': results})