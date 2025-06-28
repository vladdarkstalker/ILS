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
from .models import TestItem, TestItemOption
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
from django.contrib.auth.decorators import login_required, user_passes_test
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
#from .utils.question_answer_generation import generate_questions_and_answers
import logging
import traceback
from django.utils.text import Truncator
import logging
from .utils.question_generation_full import *
from langdetect import detect
<<<<<<< Updated upstream
=======
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import PsychTest, PsychQuestion, PsychTestResult
from .forms import PsychTestForm
from .utils.calculate_factors import calculate_factors
from .utils.interpretation_utils import interpret_educational_guidance
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from .models import Test
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Test, TestItem, TestItemOption
import re
import random
from django.views.decorators.http import require_POST
from .models import TestItem, TestItemOption
>>>>>>> Stashed changes

logger = logging.getLogger('learnsys')
logger = logging.getLogger(__name__)

def test_detail(request, pk):
    test = get_object_or_404(Test, pk=pk)
    question_forms = []

    for item in test.items.all().order_by('order_index'):
        form = TestItemForm(instance=item)
        irt = get_item_irt(item) if 'get_item_irt' in globals() else None
        question_forms.append({'form': form, 'irt': irt, 'item': item})

    return render(request, 'test_detail.html', {
        'test': test,
        'question_forms': question_forms,
        'can_edit': request.user.is_staff,
    })

@require_POST
@login_required
def generate_single_question(request, pk):
    test = get_object_or_404(Test, id=pk)
    topic = test.topic

    # Получаем все текстовые блоки контента
    content_blocks = topic.contents.filter(content_type='text')

    found_question = False  # Флаг, чтобы знать — был ли вопрос создан

    for content in content_blocks:
        # Пытаемся взять текст из поля generated_text, если нет — из text_content
        full_text = (getattr(content, 'generated_text', '') or getattr(content, 'text_content', '')).strip()

        if len(full_text) < 50:
            continue

        # Разбиваем текст на чанки
        chunks = [p.strip() for p in re.split(r'(?<=\.)\s+', full_text) if len(p.strip().split()) >= 8]

        for chunk in chunks:
            questions = generate_questions_from_text(chunk, content_id=content.id, original_language='ru')
            if not questions:
                continue

            for q in questions:
                question_text = q.get("question", "").strip()
                correct_answer = q.get("answer", "").strip()
                q_type = q.get("question_type", "text")

                if not question_text or not correct_answer:
                    continue

                # Создание вопроса
                test_item = TestItem.objects.create(
                    test=test,
                    content=question_text,
                    question_type=q_type,
                    correct_text_answer=correct_answer if q_type == 'text' else '',
                    order_index=test.items.count(),
                    source_content_id=q.get("content_id")  # <- это content.id
                )

                distractors = q.get("distractors", [])
                if q_type != 'text' and distractors:
                    all_answers = [correct_answer] + distractors
                    random.shuffle(all_answers)
                    for option_text in all_answers:
                        TestItemOption.objects.create(
                            test_item=test_item,
                            content=option_text,
                            is_correct=(option_text == correct_answer)
                        )

                found_question = True  # хотя бы один вопрос добавлен

    if found_question:
        messages.success(request, "Вопрос(ы) успешно сгенерированы и добавлены.")
    else:
        messages.error(request, "Не удалось сгенерировать вопрос по теме.")

    return redirect('learnsys:test_detail', pk=pk)

class AppendGeneratedQuestionsView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        test = get_object_or_404(Test, pk=self.kwargs['pk'])
        return is_instructor(self.request.user) and test.topic.course.instructor == self.request.user

    def post(self, request, *args, **kwargs):
        test = get_object_or_404(Test, pk=self.kwargs['pk'])
        topic = test.topic
        contents = topic.contents.filter(generated_text__isnull=False)

        if not contents.exists():
            messages.error(request, "Нет обработанных материалов для генерации.")
            return redirect('learnsys:test_detail', pk=test.id)

        added = 0
        for content in contents:
            try:
                questions = generate_questions_from_text(content.generated_text, content_id=content.id, original_language='ru')
                for q in questions:
                    if not q.get('question') or not q.get('answer'):
                        continue

                    question_type = q.get('question_type', 'text')
                    item = TestItem.objects.create(
                        test=test,
                        content=q['question'],
                        question_type=question_type,
                        correct_text_answer=q['answer'] if question_type == 'text' else '',
                        source_content_id=q.get('content_id')
                    )

                    if question_type in ['single_choice', 'multiple_choice']:
                        TestItemOption.objects.create(item=item, content=q['answer'], is_correct=True)
                        for distractor in q.get('distractors', []):
                            TestItemOption.objects.create(item=item, content=distractor, is_correct=False)

                    added += 1
            except Exception as e:
                logger.error(f"Ошибка генерации для контента {content.id}: {e}")

        if added:
            messages.success(request, f"Добавлено {added} новых вопрос(ов) к тесту.")
        else:
            messages.warning(request, "Новых вопросов не добавлено.")

        return redirect('learnsys:test_detail', pk=test.id)

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

class GenerateTestView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return is_instructor(self.request.user)

    def post(self, request, *args, **kwargs):
        topic_id = kwargs.get('pk')
        topic = get_object_or_404(Topic, id=topic_id)

        # создаём новый тест
        count = Test.objects.filter(topic=topic).count() + 1
        title = f"Тест по теме '{topic.name}' #{count}"
        new_test = Test.objects.create(topic=topic, title=title)

        # запускаем генерацию вопросов
        contents = topic.contents.filter(generated_text__isnull=False)
        added = 0

        for content in contents:
            questions = generate_questions_from_text(content.generated_text, content_id=content.id)
            for q in questions:
                if not q.get('question') or not (q.get('answer') or q.get('answers')):
                    continue

                q_type = q.get('type', 'text')
                item = TestItem.objects.create(
                    test=new_test,
                    content=q['question'],
                    question_type=q_type,
                    correct_text_answer=q.get('answer', '') if q_type == 'text' else '',
                    source_content_id=content.id
                )

                if q_type in ['single_choice', 'multiple_choice']:
                    corrects = [q['answer']] if q_type == 'single_choice' else q.get('answers', [])
                    for c in corrects:
                        TestItemOption.objects.create(item=item, content=c, is_correct=True)
                    for d in q.get('distractors', []):
                        TestItemOption.objects.create(item=item, content=d, is_correct=False)

                added += 1

        if added:
            messages.success(request, f"Тест создан и добавлено {added} вопрос(ов).")
        else:
            messages.warning(request, "Тест создан, но вопросы не были добавлены.")

        return redirect('learnsys:test_detail', pk=new_test.id)

class GenerateQuestionsView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        test = get_object_or_404(Test, pk=self.kwargs['pk'])
        return is_instructor(self.request.user) and test.topic.course.instructor == self.request.user

    def post(self, request, *args, **kwargs):
        test = get_object_or_404(Test, pk=self.kwargs['pk'])
        topic = test.topic
        contents = topic.contents.filter(generated_text__isnull=False)

        added = 0
        for content in contents:
            try:
                questions = generate_questions_from_text(content.generated_text, content_id=content.id)
                for q in questions:
                    if not q.get('question') or not (q.get('answer') or q.get('answers')):
                        continue

                    q_type = q.get('type', 'text')
                    item = TestItem.objects.create(
                        test=test,
                        content=q['question'],
                        question_type=q_type,
                        correct_text_answer=q.get('answer', '') if q_type == 'text' else '',
                        source_content_id=content.id
                    )

                    if q_type in ['single_choice', 'multiple_choice']:
                        corrects = [q['answer']] if q_type == 'single_choice' else q.get('answers', [])
                        for c in corrects:
                            TestItemOption.objects.create(item=item, content=c, is_correct=True)
                        for d in q.get('distractors', []):
                            TestItemOption.objects.create(item=item, content=d, is_correct=False)

                    added += 1
            except Exception as e:
                logger.error(f"Ошибка генерации вопросов: {e}")

        if added:
            messages.success(request, f"Добавлено {added} новых вопрос(ов) к тесту.")
        else:
            messages.warning(request, "Вопросы не были добавлены.")

        return redirect('learnsys:test_detail', pk=test.id)

'''class GenerateQuestionsView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, *args, **kwargs):
        topic_id = kwargs.get('pk')
        topic = get_object_or_404(Topic, id=topic_id)
        content_items = topic.contents.all()

        test = topic.tests.first()  # <-- Подразумевается, что у темы есть хотя бы один тест
        if not test:
            messages.error(request, "Нет теста для добавления вопросов.")
            return redirect('learnsys:topic_detail', pk=topic.id)

        total_questions = 0

        for content in content_items:
            text = content.generated_text or content.text_content or ''
            questions_data = generate_questions_from_text(text, content_id=content.id)

            for q_data in questions_data:
                question_type = q_data.get('type')
                question_text = q_data.get('question')

                if question_type == 'single_choice':
                    question_obj = TestItem.objects.create(
                        test=test,
                        question_type='single_choice',
                        content=question_text,
                        correct_text_answer=q_data.get('answer', ''),
                        source_content=content
                    )
                    # Добавляем правильный ответ
                    TestItemOption.objects.create(
                        item=question_obj,
                        content=q_data.get('answer', ''),
                        is_correct=True
                    )
                    # Добавляем дистракторы
                    for distractor_text in q_data.get('distractors', []):
                        TestItemOption.objects.create(
                            item=question_obj,
                            content=distractor_text,
                            is_correct=False
                        )
                    total_questions += 1

                elif question_type == 'multiple_choice':
                    question_obj = TestItem.objects.create(
                        test=test,
                        question_type='multiple_choice',
                        content=question_text,
                        source_content=content
                    )
                    # Добавляем правильные ответы
                    for correct_answer in q_data.get('answers', []):
                        TestItemOption.objects.create(
                            item=question_obj,
                            content=correct_answer,
                            is_correct=True
                        )
                    # Добавляем дистракторы
                    for distractor_text in q_data.get('distractors', []):
                        TestItemOption.objects.create(
                            item=question_obj,
                            content=distractor_text,
                            is_correct=False
                        )
                    total_questions += 1

        if total_questions > 0:
            messages.success(request, f"Сгенерировано вопросов: {total_questions}")
        else:
            messages.warning(request, "Вопросы не были сгенерированы.")

        return redirect('learnsys:topic_detail', pk=topic.id)

    def test_func(self):
        topic = get_object_or_404(Topic, pk=self.kwargs.get('pk'))
        return self.request.user == topic.course.instructor

    def handle_no_permission(self):
        messages.error(self.request, "У вас нет прав для выполнения этого действия.")
        logger.warning(f"Пользователь {self.request.user} не имеет прав для генерации вопросов для темы {self.kwargs.get('pk')}.")
        return redirect('learnsys:topic_detail', pk=self.kwargs.get('pk'))'''

'''    def post(self, request, *args, **kwargs):
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
                questions_and_answers = generate_questions_from_text(text, content_id=content.id)

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
                question_type = qa.get('question_type', 'text')

                test_item = TestItem.objects.create(
                    test=test,
                    content=qa['question'],
                    question_type=question_type,
                    correct_text_answer=qa['answer'] if question_type == 'text' else '',
                    source_content_id=qa.get('content_id')
                )

                if question_type in ['single_choice', 'multiple_choice']:
                    from learnsys.models import TestItemOption
                    # Добавим правильный вариант
                    TestItemOption.objects.create(item=test_item, content=qa['answer'], is_correct=True)
                    # Добавим дистракторы
                    for distractor in qa.get('distractors', []):
                        TestItemOption.objects.create(item=test_item, content=distractor, is_correct=False)
            else:
                logger.warning(f"Неполный QA-параметр: {qa}")
        messages.success(request, f"Вопросы и ответы для темы '{topic.name}' успешно сгенерированы и добавлены в тест '{test.title}'.")
        logger.info(f"Генерация вопросов для темы {topic.id} завершена успешно.")
        return redirect('learnsys:test_detail', pk=test.id)

    def test_func(self):
        topic = get_object_or_404(Topic, pk=self.kwargs.get('pk'))
        return self.request.user == topic.course.instructor'''

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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['prefix'] = f"item_{self.object.id}"  # вот это ключ
        return kwargs

    def get_success_url(self):
        return reverse('learnsys:test_detail', kwargs={'pk': self.object.test.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['test'] = self.object.test
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            form.save()
            messages.success(request, "Вопрос успешно обновлён.")
        else:
            messages.error(request, "Ошибка при обновлении вопроса.")
        return redirect('learnsys:test_detail', pk=self.object.test.id)

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

<<<<<<< Updated upstream
=======
class AdaptiveTestView(LoginRequiredMixin, View):
    template_name = 'tests/adaptive_test.html'
    MAX_QUESTIONS = 10
    COMPLEXITY_ORDER = ['easy', 'medium', 'hard']

    def get(self, request, *args, **kwargs):
        test_id = kwargs.get('test_id')
        test = get_object_or_404(Test, id=test_id)
        user = request.user

        if is_instructor(user) and test.topic.course.instructor != user:
            raise PermissionDenied("У вас нет доступа к этому тесту.")
        if not (is_instructor(user) or is_student(user)):
            messages.error(request, "Нет доступа.")
            return redirect('learnsys:home')

        session, created = AdaptiveTestSession.objects.get_or_create(user=user, test=test)
        if session.finished:
            messages.info(request, "Тест уже завершён.")
            result = TestResult.objects.filter(user=user, test=test).order_by('-date_taken').first()
            if result:
                return redirect('learnsys:test_result_detail', test_result_id=result.id)
            return redirect('learnsys:home')

        if session.asked_items.count() >= self.MAX_QUESTIONS:
            self.finish_test(session)
            return self.redirect_to_results(user, test)

        next_item = self.select_next_item(test, session)
        if not next_item:
            self.finish_test(session)
            return self.redirect_to_results(user, test)

        form = TestAnswerForm(test_items=[next_item])
        return render(request, self.template_name, {
            'form': form,
            'question': next_item,
            'test': test,
            'current_complexity': session.current_complexity
        })

    def post(self, request, *args, **kwargs):
        test_id = kwargs.get('test_id')
        test = get_object_or_404(Test, id=test_id)
        user = request.user
        session = get_object_or_404(AdaptiveTestSession, user=user, test=test, finished=False)

        item_id = request.POST.get('item_id')
        item = get_object_or_404(TestItem, id=item_id, test=test)

        form = TestAnswerForm(request.POST, test_items=[item])
        if form.is_valid():
            correct = self.process_answer(user, item, form)
            # Пересчитываем θ:
            session.theta = self.estimate_theta(session)
            # Обновляем сложность
            session.current_complexity = self.update_complexity(session.current_complexity, correct)

            session.asked_items.add(item)
            session.save()
            return redirect('learnsys:adaptive_test', test_id=test_id)
        else:
            return render(request, self.template_name, {
                'form': form,
                'question': item,
                'test': test,
                'current_complexity': session.current_complexity
            })

    def process_answer(self, user, item, form):
        user_answer = form.cleaned_data.get(f"item_{item.id}")
        uta = UserTestAnswer.objects.create(
            user=user,
            item=item
        )
        if item.question_type == 'single_choice':
            selected_options = [int(user_answer)]
            for oid in selected_options:
                uta.option.add(item.options.get(id=oid))
            correct_options = set(item.options.filter(is_correct=True))
            selected_set = set(uta.option.all())
            return selected_set == correct_options
        elif item.question_type == 'multiple_choice':
            selected_options = [int(i) for i in user_answer]
            for oid in selected_options:
                uta.option.add(item.options.get(id=oid))
            correct_options = set(item.options.filter(is_correct=True))
            selected_set = set(uta.option.all())
            return selected_set == correct_options
        elif item.question_type == 'text':
            user_text = user_answer
            uta.text_answer = user_text
            uta.save()
            return self.check_text_answer(user_text, item.correct_text_answer)
        return False

    def check_text_answer(self, user_answer, correct_answer):
        normalized_user = ' '.join(user_answer.lower().split())
        normalized_correct = ' '.join(correct_answer.lower().split())
        if normalized_user == normalized_correct:
            return True
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, normalized_user, normalized_correct).ratio()
        return similarity > 0.8

    def select_next_item(self, test, session):
        """
        Выбирает следующее задание для адаптивного тестирования на основе Rasch-модели.
        """
        theta = session.theta
        answered_item_ids = session.asked_items.values_list('id', flat=True)
        available_items = test.items.exclude(id__in=answered_item_ids)

        if not available_items.exists():
            return None

        # Выбор по минимальному |θ - b|
        min_diff = float('inf')
        next_item = None
        for item in available_items:
            diff = abs(theta - item.b)
            if diff < min_diff:
                min_diff = diff
                next_item = item

        return next_item

    def update_complexity(self, current_complexity, correct):
        idx = self.COMPLEXITY_ORDER.index(current_complexity)
        if correct and idx < len(self.COMPLEXITY_ORDER)-1:
            idx += 1
        elif not correct and idx > 0:
            idx -= 1
        return self.COMPLEXITY_ORDER[idx]

    def estimate_theta(self, session, max_iter=10, step=0.1):
        user = session.user
        test = session.test
        answered_items = session.asked_items.all()
        answers = UserTestAnswer.objects.filter(user=user, item__in=answered_items)

        results = []
        for ans in answers:
            if ans.item.question_type in ['single_choice', 'multiple_choice']:
                correct_options = set(ans.item.options.filter(is_correct=True))
                selected = set(ans.option.all())
                correct = (correct_options == selected)
            elif ans.item.question_type == 'text':
                correct = self.check_text_answer(ans.text_answer, ans.item.correct_text_answer)
            else:
                correct = False
            results.append((ans.item, correct))

        theta = session.theta

        # Градиентный шаг: для Rasch-модели a=1,c=0, p=1/(1+exp(-(θ-b)))
        # ln(L)=Σ[correct*ln(p)+(1-correct)*ln(1-p)]
        # d/dθ ln(L)=Σ[correct - p]

        # Для вычисления градиента:
        # grad = Σ(correct - p)
        # Обновим θ: θ = θ + step*grad

        for _ in range(max_iter):
            grad = 0.0
            for (item, correct) in results:
                p = item.probability_of_correct_answer(theta)
                grad += (1.0 if correct else 0.0) - p
            # Обновляем θ:
            theta = theta + step*grad
            # Если grad мал, можно было бы выйти, но для простоты оставим так.

        return theta

    def finish_test(self, session):
        session.finished = True
        session.save()
        user = session.user
        test = session.test
        asked_items = session.asked_items.all()
        answers = UserTestAnswer.objects.filter(user=user, item__in=asked_items)
        correct_count = 0
        total = asked_items.count()
        for ans in answers:
            if ans.item.question_type in ['single_choice', 'multiple_choice']:
                correct_options = set(ans.item.options.filter(is_correct=True))
                selected = set(ans.option.all())
                if correct_options == selected:
                    correct_count += 1
            elif ans.item.question_type == 'text':
                if self.check_text_answer(ans.text_answer, ans.item.correct_text_answer):
                    correct_count += 1

        TestResult.objects.create(
            user=user,
            test=test,
            score=correct_count,
            total_questions=total,
            date_taken=timezone.now(),
            theta=session.theta
        )

        # ВАЖНО: добавляем обновление прогресса темы
        topic_progress, _ = TopicProgress.objects.get_or_create(user=user, topic=test.topic)
        topic_progress.mark_test_completed(correct_count, total)

        # Посчитать, сколько теперь результатов по этому тесту.
        count = TestResult.objects.filter(test=test).count()
        if count % 10 == 0:
            from .views import calibrate_item_parameters
            calibrate_item_parameters(test, max_iter=20, tol=1e-3)

    def redirect_to_results(self, user, test):
        result = TestResult.objects.filter(user=user, test=test).order_by('-date_taken').first()
        if result:
            return redirect('learnsys:test_result_detail', test_result_id=result.id)
        return redirect('learnsys:home')

>>>>>>> Stashed changes
class TestDetailView(LoginRequiredMixin, DetailView):
    model = Test
    template_name = 'tests/test_detail.html'
    context_object_name = 'test'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if not user.is_staff:
<<<<<<< Updated upstream
            # Создаем или получаем прогресс по теме
            topic_progress, created = TopicProgress.objects.get_or_create(user=user, topic=obj.topic)  # Передаем obj.topic, чтобы передать объект Topic
            topic_progress.mark_reading_started()
        return obj

=======
            TopicProgress.objects.get_or_create(user=user, topic=obj.topic)
        return obj

    def check_text_answer(self, user_answer, correct_answer):
        from difflib import SequenceMatcher

        if not user_answer or not correct_answer:
            return False  # Один из ответов отсутствует — не сравниваем

        norm_user = ' '.join(user_answer.lower().split())
        norm_correct = ' '.join(correct_answer.lower().split())

        return norm_user == norm_correct or SequenceMatcher(None, norm_user, norm_correct).ratio() > 0.8

>>>>>>> Stashed changes
    def get_context_data(self, **kwargs):
        from .forms import TestItemForm
        context = super().get_context_data(**kwargs)
        test = self.object
        user = self.request.user
<<<<<<< Updated upstream
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
        
=======
        theta = 0.0
        question_forms = []

        for item in test.items.all():
            answers = UserTestAnswer.objects.filter(item=item)
            correct = sum(
                1 for ans in answers
                if (item.question_type in ['single_choice', 'multiple_choice'] and set(ans.option.all()) == set(item.options.filter(is_correct=True)))
                or (item.question_type == 'text' and self.check_text_answer(ans.text_answer, item.correct_text_answer))
            )
            empirical_p = correct / answers.count() if answers.exists() else 0.0
            model_p = item.probability_of_correct_answer(theta)

            question_forms.append({
                'form': TestItemForm(instance=item, prefix=f"item_{item.id}"),
                'irt': {
                    'a': item.a,
                    'b': item.b,
                    'c': item.c,
                    'empirical_p': empirical_p,
                    'model_p': model_p
                }
            })

        context['is_instructor'] = is_instructor(user) and test.topic.course.instructor == user
        context['question_forms'] = question_forms
        context['total_test_results'] = TestResult.objects.filter(test=test).count()

        if not context['is_instructor']:
            has_taken = TestResult.objects.filter(user=user, test=test).exists()
            retake_permission = TestRetakePermission.objects.filter(user=user, test=test, allowed=True).exists() if test.allow_retakes else False
            context['can_take_test'] = not has_taken or retake_permission
            context['test_result'] = TestResult.objects.filter(user=user, test=test).order_by('-date_taken').first()

>>>>>>> Stashed changes
        return context

    def post(self, request, *args, **kwargs):
        from .forms import TestItemForm
        self.object = self.get_object()
        test = self.object

        if not is_instructor(request.user) or test.topic.course.instructor != request.user:
            raise PermissionDenied()

        updated = False
        for item in test.items.all():
            prefix = f"item_{item.id}"
            form = TestItemForm(request.POST, instance=item, prefix=prefix)
            if form.is_valid():
                form.save()
                updated = True

<<<<<<< Updated upstream
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
=======
        if updated:
            messages.success(request, "Изменения сохранены.")
        else:
            messages.info(request, "Изменения не были внесены.")

        return redirect('learnsys:test_detail', pk=test.id)
>>>>>>> Stashed changes

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

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        test = get_object_or_404(Test, id=self.kwargs['test_id'])

        # Правильная фильтрация студентов
        form.fields['students'].queryset = User.objects.filter(
            testresult__test=test
        ).distinct().exclude(
            testretakepermission__test=test,
            testretakepermission__allowed=True
        )

        return form

    def test_func(self):
        test = get_object_or_404(Test, id=self.kwargs['test_id'])
        return is_instructor(self.request.user) and test.topic.course.instructor == self.request.user

    def get_form_kwargs(self):
        # Передаём test в форму, чтобы она знала, по какому тесту фильтровать студентов
        kwargs = super().get_form_kwargs()
        test = get_object_or_404(Test, id=self.kwargs['test_id'])
        kwargs['test'] = test
        return kwargs

    def form_valid(self, form):
        test = get_object_or_404(Test, id=self.kwargs['test_id'])
        # Ставим "test.allow_retakes = True", чтобы не блокировалась повторная сдача
        test.allow_retakes = True
        test.save()

        # Берём всех выбранных в чекбоксах студентов
        students = form.cleaned_data['students']

        # Создаем разрешения для выбранных студентов
        for student in students:
<<<<<<< Updated upstream
=======
            # Разрешаем повторное прохождение (или обновляем)
>>>>>>> Stashed changes
            TestRetakePermission.objects.update_or_create(
                user=student,
                test=test,
                defaults={'allowed': True}
            )
<<<<<<< Updated upstream
=======
            # Если используем адаптивный тест, сбросим сессию
            session, _ = AdaptiveTestSession.objects.get_or_create(user=student, test=test)
            session.reset_for_retake()
>>>>>>> Stashed changes

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

        # Если нужно запрещать просмотр дашборда всем, кто не студент:
        if not is_student(user):
            messages.error(self.request, "У вас нет доступа к этой странице.")
            return context

        # Находим все курсы, на которые записан студент (через учебные группы)
        courses = Course.objects.filter(
            study_groups__group_members__user=user
        ).distinct()

        course_stats = []
        for course in courses:
            topics = course.topics.all()
            total_topics = topics.count()

            # Сколько тем имеет статус 'completed'
            completed_topics = topics.filter(
                progresses__user=user,
                progresses__status='completed'
            ).count()

            # Прогресс по курсу в процентах (если тем нет, то 0)
            if total_topics > 0:
                progress_percentage = round((completed_topics / total_topics) * 100, 2)
            else:
                progress_percentage = 0

            # Суммируем правильно отвеченные вопросы и общее кол-во вопросов
            total_correct = 0
            total_q = 0
            for t in topics:
                tprog = t.progresses.filter(user=user).first()
                if tprog and tprog.total_questions > 0:
                    total_correct += tprog.correct_answers
                    total_q += tprog.total_questions

            # Средний процент правильных ответов по курсу
            if total_q > 0:
                average_score_percent = round((total_correct / total_q) * 100, 2)
            else:
                average_score_percent = 0

            # Пример перевода среднего процента в оценку по 5-балльной шкале
            def five_point_grade(score_percent):
                if score_percent >= 90:
                    return 5
                elif score_percent >= 75:
                    return 4
                elif score_percent >= 60:
                    return 3
                else:
                    return 2  # Можно поставить 1, если хотите более жёсткую градацию

            grade_5scale = five_point_grade(average_score_percent)

            # Дополнительно: собираем статусы по каждой теме для детального отображения
            topic_progresses = []
            for t in topics:
                tprog = t.progresses.filter(user=user).first()
                if tprog:
                    topic_progresses.append({
                        'topic': t,
                        'status': tprog.status,
                        'score_percentage': tprog.test_score_percentage(),  # % правильных по теме
                    })
                else:
                    topic_progresses.append({
                        'topic': t,
                        'status': 'not_started',
                        'score_percentage': 0,
                    })

            # Собираем данные для одной «карточки» курса
            course_stats.append({
                'course': course,
                'progress_percentage': progress_percentage,
                'completed_topics': completed_topics,
                'total_topics': total_topics,
                'average_score_percent': average_score_percent,
                'grade_5scale': grade_5scale,
                'topic_progresses': topic_progresses,
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
<<<<<<< Updated upstream
=======

def simulate_test_passes(test, n=10):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    for i in range(n):
        username = f"sim_user_{uuid.uuid4().hex[:8]}"
        student = User.objects.create(username=username, is_active=True)
        
        theta_true = random.gauss(0, 1)
        session, created = AdaptiveTestSession.objects.get_or_create(user=student, test=test)
        simulate_one_pass(test, session, theta_true)

def simulate_one_pass(test, session, theta_true):
    view = AdaptiveTestView()
    max_q = view.MAX_QUESTIONS

    while not session.finished and session.asked_items.count() < max_q:
        next_item = view.select_next_item(test, session)
        if not next_item:
            view.finish_test(session)
            break
        
        p = next_item.probability_of_correct_answer(theta_true)
        # Добавим имитацию "волнения" или "усталости": 
        # Раз в каждом вопросе пусть истинная θ сдвигается случайно на 0..0.3.
        # 0.3 - просто пример, можно меньше
        local_theta = theta_true + random.gauss(0, 0.3)
        p = next_item.probability_of_correct_answer(local_theta)
        correct = (random.random() < p)

        # Подготовим ответы:
        user_answer_data = {}
        field_name = f"item_{next_item.id}"

        if next_item.question_type == 'text':
            user_text = next_item.correct_text_answer if correct else "Wrong answer"
            user_answer_data[field_name] = user_text
        elif next_item.question_type in ['single_choice', 'multiple_choice']:
            correct_options = next_item.options.filter(is_correct=True)
            all_options = list(next_item.options.all())
            if correct:
                if next_item.question_type == 'single_choice':
                    user_answer_data[field_name] = str(correct_options.first().id)
                else:
                    user_answer_data[field_name] = [str(o.id) for o in correct_options]
            else:
                wrong_opts = [o for o in all_options if not o.is_correct]
                if not wrong_opts:
                    # Если нет неверных, выберем случайные варианты
                    if next_item.question_type == 'single_choice':
                        user_answer_data[field_name] = str(random.choice(all_options).id)
                    else:
                        chosen = [str(o.id) for o in all_options if random.random()<0.5]
                        if not chosen:
                            chosen = [str(all_options[0].id)]
                        user_answer_data[field_name] = chosen
                else:
                    if next_item.question_type == 'single_choice':
                        user_answer_data[field_name] = str(random.choice(wrong_opts).id)
                    else:
                        chosen = [str(o.id) for o in wrong_opts if random.random()<0.5]
                        if not chosen:
                            chosen = [str(random.choice(wrong_opts).id)]
                        user_answer_data[field_name] = chosen

        form = TestAnswerForm(user_answer_data, test_items=[next_item])
        if form.is_valid():
            c = view.process_answer(session.user, next_item, form)
            session.theta = view.estimate_theta(session)
            session.current_complexity = view.update_complexity(session.current_complexity, c)
            session.asked_items.add(next_item)
            session.save()
        else:
            view.finish_test(session)
            break

    if not session.finished:
        view.finish_test(session)

def recalibrate_irt_parameters(test, step=0.01):
    from collections import defaultdict
    answers = UserTestAnswer.objects.filter(item__test=test)
    item_answers = defaultdict(list)
    for ans in answers:
        correct = False
        if ans.item.question_type in ['single_choice', 'multiple_choice']:
            correct_options = set(ans.item.options.filter(is_correct=True))
            selected = set(ans.option.all())
            correct = (correct_options == selected)
        elif ans.item.question_type == 'text':
            correct = AdaptiveTestView.check_text_answer(None, ans.text_answer, ans.item.correct_text_answer)
        item_answers[ans.item.id].append(correct)

    theta=0.0
    for item_id, results in item_answers.items():
        item = TestItem.objects.get(id=item_id)
        if len(results)==0:
            continue
        empirical_p = sum(results)/len(results)
        model_p = item.probability_of_correct_answer(theta)
        diff = empirical_p - model_p
        # Если diff очень маленький (меньше 0.01), игнорируем
        if abs(diff)<0.01:
            continue

        if diff>0:
            # упрощённо снижаем b 
            item.b -= step
        else:
            item.b += step

        # Корректируем a
        item.a = max(min(item.a + diff*step, 3.0), 0.1)
        # c оставляем как есть или слегка меняем:
        # Если emp_p > model_p, можно снизить c, 
        # но делаем это крайне осторожно:
        item.c = max(min(item.c + (-diff)*step*0.5, 0.3), 0.05)

        # Ограничения на b, чтобы b не уходил слишком далеко:
        item.b = max(min(item.b, 3.0), -3.0)

        item.save()

def calibrate_item_parameters(test, max_iter=20, tol=1e-3):
    from collections import defaultdict
    import math
    import logging
    
    logger = logging.getLogger(__name__)
    
    results = TestResult.objects.filter(test=test).only('user_id', 'theta')
    theta_map = {res.user_id: res.theta for res in results if res.theta is not None}

    # Словарь для ответов
    item_answers = defaultdict(list)

    # Используем iterator и chunk_size для избежания больших запросов
    all_answers = (UserTestAnswer.objects
                                .filter(item__test=test)
                                .select_related('item')
                                .only('id', 'user_id', 'item_id', 'text_answer'))

    for ans in all_answers.iterator(chunk_size=1000):
        theta_j = theta_map.get(ans.user_id, None)
        if theta_j is None:
            continue

        correct = False
        if ans.item.question_type in ['single_choice', 'multiple_choice']:
            correct_options = set(ans.item.options.filter(is_correct=True))
            selected = set(ans.option.all())
            correct = (correct_options == selected)
        elif ans.item.question_type == 'text':
            correct = AdaptiveTestView.check_text_answer(None, ans.text_answer, ans.item.correct_text_answer)

        item_answers[ans.item_id].append((theta_j, correct))

    for item_id, data in item_answers.items():
        item = TestItem.objects.get(id=item_id)
        b = item.b

        for _ in range(max_iter):
            grad = 0.0
            hess = 0.0
            for (theta_j, correct_j) in data:
                theta_j = max(min(theta_j, 4.0), -4.0)
                x = theta_j - b
                try:
                    p = 1.0 / (1.0 + math.exp(-x))
                except OverflowError:
                    p = 1.0 if x > 0 else 0.0

                grad += (1.0 if correct_j else 0.0) - p
                hess += -p*(1-p)

            if abs(hess) < 1e-9:
                logger.warning(f"Hessian слишком мал для элемента {item_id}. Пропуск обновления.")
                break

            if abs(grad) < tol:
                break

            delta = grad / hess
            b_new = b + delta
            b_new = max(min(b_new, 3.0), -3.0)
            if abs(b_new - b) < tol:
                b = b_new
                break
            b = b_new

        item.b = b
        item.save()
        logger.info(f"Параметр b для элемента {item_id} откалиброван до {b}.")

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


def interpret_factor(factor_code, result):
    try:
        interpretation = FactorInterpretation.objects.get(factor_code=factor_code)
        for value_range in interpretation.value_interpretations:
            if value_range['min_value'] <= result <= value_range['max_value']:
                return interpretation.factor_name, value_range['text']
    except FactorInterpretation.DoesNotExist:
        return factor_code, "Интерпретация отсутствует"
    return factor_code, "Неизвестное значение"


def all_test_results(request):
    user = request.user
    results = PsychTestResult.objects.filter(user=user).order_by('test', 'factor')

    factor_results = {}  # Основные результаты (A1, A2, A3...)
    guidance_results = {}  # Рекомендации (A1T, A1R, A1C...)

    # Разделяем факторы и рекомендации
    for result in results:
        if result.factor.endswith(("T", "R", "C")):
            guidance_results[result.factor] = result.result
        else:
            factor_results[result.factor] = result.result

    # Обрабатываем основную интерпретацию (таблица 1)
    interpreted_results = [
        {
            'test_name': result.test.name,
            'factor_code': result.factor,
            'factor_name': interpret_factor(result.factor, result.result)[0],  # Имя фактора
            'result': result.result,
            'interpretation': interpret_factor(result.factor, result.result)[1],  # Интерпретация значения
            'date_taken': result.date_taken
        }
        for result in results if result.factor in factor_results
    ]

    # Обрабатываем образовательные рекомендации (таблица 2)
    guidance_interpretation = interpret_educational_guidance(guidance_results)
    guidance_list = list(guidance_interpretation.values())

    context = {
        'results': interpreted_results,
        'guidance': guidance_list,  # Передаём рекомендации в шаблон
    }
    return render(request, 'psych/all_test_results.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def export_psych_test_csv(request, test_id):
    """
    Генерирует CSV-файл с результатами теста PsychTestResult.
    Доступно только для админ-пользователей.
    """
    test = get_object_or_404(PsychTest, id=test_id)
    results = PsychTestResult.objects.filter(test=test).select_related('user')

    # Создаём HTTP-ответ в виде CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    # Формируем имя файла
    filename = f"{test.name}_results.csv".replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    # Записываем заголовки столбцов
    writer.writerow(['ФИО пользователя', 'Factor', 'Result', 'Дата прохождения'])

    for result in results:
        full_name = result.user.get_full_name()  # Например, "Иванов Иван Иванович"
        writer.writerow([
            full_name,
            result.factor,
            result.result,
            result.date_taken.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response

>>>>>>> Stashed changes
