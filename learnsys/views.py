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
        course = obj.topic.course

        if is_instructor(user) and course.instructor == user:
            return obj
        elif is_student(user) and course.study_groups.filter(group_members__user=user).exists():
            return obj
        else:
            raise PermissionDenied("У вас нет доступа к этому тесту.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        test_items = self.object.items.all().prefetch_related('options')
        context['test_items'] = test_items

        # Получаем все результаты теста для студента
        test_results = TestResult.objects.filter(user=self.request.user, test=self.object).order_by('-date_taken')
        context['test_results'] = test_results

        # Проверяем, может ли студент пройти тест
        if is_student(self.request.user):
            can_retake_permission = TestRetakePermission.objects.filter(
                user=self.request.user,
                test=self.object,
                can_retake=True
            ).exists()
            if not test_results.exists() or can_retake_permission:
                context['can_take_test'] = True
            else:
                context['can_take_test'] = False
        else:
            context['can_take_test'] = False

        context['is_instructor'] = is_instructor(self.request.user) and self.object.topic.course.instructor == self.request.user
        context['form'] = TestAnswerForm(test_items=test_items) if context['can_take_test'] else None
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        test_items = self.object.items.all()
        form = TestAnswerForm(request.POST, test_items=test_items)

        if form.is_valid():
            score = 0
            total_questions = test_items.count()

            for item in test_items:
                field_name = f"item_{item.id}"
                user_answer = form.cleaned_data[field_name]

                if item.question_type == 'single_choice':
                    selected_options = [user_answer]
                    correct_options_ids = set(item.options.filter(is_correct=True).values_list('id', flat=True))
                    selected_options_ids = set(int(option_id) for option_id in selected_options)

                    if selected_options_ids == correct_options_ids:
                        score += 1

                    # Сохраняем ответы пользователя
                    for option_id in selected_options:
                        option = item.options.get(id=option_id)
                        UserTestAnswer.objects.create(
                            user=request.user,
                            item=item,
                            option=option
                        )

                elif item.question_type == 'multiple_choice':
                    selected_options = user_answer
                    correct_options_ids = set(item.options.filter(is_correct=True).values_list('id', flat=True))
                    selected_options_ids = set(int(option_id) for option_id in selected_options)
    
                    if selected_options_ids == correct_options_ids:
                        score += 1

                    # Сохраняем ответы пользователя
                    for option_id in selected_options:
                        option = item.options.get(id=option_id)
                        UserTestAnswer.objects.create(
                            user=request.user,
                            item=item,
                            option=option
                        )

                elif item.question_type == 'text':
                    UserTestAnswer.objects.create(
                        user=request.user,
                        item=item,
                        text_answer=user_answer
                    )
                    # Проверка правильности текстового ответа
                    if user_answer.strip().lower() == item.correct_text_answer.strip().lower():
                        score += 1

            # Сохраняем результат теста
            TestResult.objects.create(
                user=request.user,
                test=self.object,
                score=score,
                total_questions=total_questions
            )

            # Отзыв разрешения на повторное прохождение теста после прохождения
            TestRetakePermission.objects.filter(user=request.user, test=self.object).update(can_retake=False)
            
            messages.success(request, f"Ваши ответы были сохранены. Ваш результат: {score}/{total_questions}.")
            return redirect('learnsys:course_detail', pk=self.object.topic.course.id)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class ResetTestPermissionView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        test = get_object_or_404(Test, id=self.kwargs['test_id'])
        return is_instructor(self.request.user) and test.topic.course.instructor == self.request.user

    def post(self, request, *args, **kwargs):
        test = get_object_or_404(Test, id=self.kwargs['test_id'])
        student = get_object_or_404(User, id=self.kwargs['student_id'])

        # Предоставляем разрешение на повторное прохождение теста без удаления предыдущих результатов
        TestRetakePermission.objects.update_or_create(
            user=student,
            test=test,
            defaults={'can_retake': True}
        )

        messages.success(request, f"Студенту {student.get_full_name()} разрешено повторно пройти тест.")
        return redirect('learnsys:test_detail', pk=test.id)
        
class ManageTestRetakesView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'tests/manage_test_retakes.html'
    form_class = TestRetakePermissionForm
    
    def test_func(self):
        test = get_object_or_404(Test, id=self.kwargs['test_id'])
        return is_instructor(self.request.user) and test.topic.course.instructor == self.request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        test_id = self.kwargs['test_id']
        test = get_object_or_404(Test, id=test_id)

        # Get students who have completed the test
        completed_students = User.objects.filter(
            testresult__test=test
        ).distinct()

        kwargs['students'] = completed_students
        return kwargs

    def form_valid(self, form):
        student = form.cleaned_data['student']
        test = get_object_or_404(Test, id=self.kwargs['test_id'])

        # Предоставляем разрешение на повторное прохождение теста без удаления предыдущих результатов
        TestRetakePermission.objects.update_or_create(
            user=student,
            test=test,
            defaults={'can_retake': True}
        )

        messages.success(self.request, f"Студенту {student.get_full_name()} разрешено повторно пройти тест.")
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
                test_results = TestResult.objects.filter(user=student, test=test).order_by('-date_taken')
                if test_results.exists():
                    completed_tests += 1
                    latest_result = test_results.first()
                    total_score += latest_result.score
                    total_questions += latest_result.total_questions
                else:
                    total_questions += test.items.count()

                test_results_list.append({
                    'test': test,
                    'test_results': test_results,
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
        
                # Получаем группу студента
        group_membership = GroupMember.objects.filter(user=student).select_related('study_group').first()
        if group_membership:
            context['student_group'] = group_membership.study_group
        else:
            context['student_group'] = None

        # Добавляем дополнительные данные о студенте
        context['group_number'] = student.group_number
        context['date_of_birth'] = student.date_of_birth

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
        messages.success(self.request, "Course updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('learnsys:instructor_dashboard')

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
        course_stats = {}
        for course in courses:
            # Получаем все тесты курса
            tests = Test.objects.filter(topic__course=course)  # Исправлено: topic__course вместо topic__courses

            total_tests = tests.count()
            total_score = 0
            total_questions = 0
            completed_tests = 0

            for test in tests:
                # Получаем последний результат теста для студента
                test_result = TestResult.objects.filter(
                    test=test,
                    user=user
                ).order_by('-id').first()

                if test_result:
                    completed_tests += 1
                    total_score += test_result.score
                    total_questions += test_result.total_questions

            # Вычисляем прогресс
            progress_percentage = (total_score / total_questions * 100) if total_questions > 0 else 0

            course_stats[course.id] = {
                'progress_percentage': round(progress_percentage, 2),
                'completed_tests': completed_tests,
                'total_tests': total_tests,
                'correct_answers': total_score,
                'total_questions': total_questions,
            }

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
        messages.success(self.request, "Материал успешно обновлен.")
        return super().form_valid(form)

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
        return is_instructor(self.request.user) and topic.course.instructor == self.request.user

    def form_valid(self, form):
        topic = get_object_or_404(Topic, id=self.kwargs.get('topic_id'))
        form.instance.topic = topic

        # Если выбран тип контента "Текст", очищаем поле content
        if form.cleaned_data['content_type'] == 'text':
            form.instance.content = None
        else:
            form.instance.text_content = None

        messages.success(self.request, "Материал успешно добавлен.")
        return super().form_valid(form)

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
            # Преподаватели могут видеть только группы своих курсов
            return StudyGroup.objects.filter(courses__instructor=user).distinct()
        elif is_student(user):
            # Студенты могут видеть группы, в которых они состоят
            return StudyGroup.objects.filter(group_members__user=user).distinct()
        elif user.is_superuser:
            # Администраторы могут видеть все группы
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
            # Преподаватель видит группу, если он является инструктором хотя бы одного из связанных курсов
            return group.courses.filter(instructor=user).exists()
        elif is_student(user):
            # Студент может видеть группу, если он состоит в ней
            return group.group_members.filter(user=user).exists()
        else:
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.object
        user = self.request.user
        context['members'] = group.group_members.select_related('user')
        context['is_instructor'] = is_instructor(user)
        context['courses'] = group.courses.all()
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

        # Собираем информацию о студенте (можно добавить информацию по курсам, если необходимо)
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
        if student.date_of_birth:
            formatted_dob = student.date_of_birth.strftime('%d.%m.%Y')
        else:
            formatted_dob = 'Не указано'
        writer.writerow(['Дата рождения', formatted_dob])

        # Пример дополнительных полей с проверкой на None
        # Отчество
        if student.patronymic:
            patronymic = student.patronymic
        else:
            patronymic = 'Не указано'
        writer.writerow(['Отчество', patronymic])

        # Дополнительные поля можно добавить аналогичным образом

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
        course = obj.course

        if is_instructor(user) and course.instructor == user:
            return obj
        elif is_student(user) and course.study_groups.filter(group_members__user=user).exists():
            return obj
        else:
            raise PermissionDenied("У вас нет доступа к этой теме.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contents'] = self.object.contents.order_by('order_index')
        user = self.request.user
        context['is_instructor'] = is_instructor(user) and self.object.course.instructor == user
        context['is_student'] = is_student(user) and not context['is_instructor']
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
