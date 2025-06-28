# forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import * 
from django.core.validators import EmailValidator
from .utils import is_instructor, is_student

User = get_user_model()

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Имя пользователя", 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label="Пароль", 
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), 
        required=True
    )

class TestAnswerForm(forms.Form):
    def __init__(self, *args, **kwargs):
        test_items = kwargs.pop('test_items', [])
        super().__init__(*args, **kwargs)
        
        # Create form fields for each test item
        for item in test_items:
            field_name = f"item_{item.id}"
            if item.question_type == 'single_choice':
                self.fields[field_name] = forms.ChoiceField(
                    label=item.content,
                    choices=[(option.id, option.content) for option in item.options.all()],
                    widget=forms.RadioSelect,
                    required=True,
                )
            elif item.question_type == 'multiple_choice':
                self.fields[field_name] = forms.MultipleChoiceField(
                    label=item.content,
                    choices=[(option.id, option.content) for option in item.options.all()],
                    widget=forms.CheckboxSelectMultiple,
                    required=True,
                )
            elif item.question_type == 'text':
                self.fields[field_name] = forms.CharField(
                    label=item.content,
                    widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
                    required=True,
                )

class TestRetakePermissionForm(forms.ModelForm):
    class Meta:
        model = TestRetakePermission
        fields = ['user', 'allowed']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'allowed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'user': 'Студент',
            'allowed': 'Разрешить повторное прохождение',
        }

    def __init__(self, *args, **kwargs):
        test = kwargs.pop('test', None)
        super().__init__(*args, **kwargs)
        if test:
            self.fields['user'].queryset = User.objects.filter(
                testresult__test=test
            ).distinct()
        else:
            self.fields['user'].queryset = User.objects.none()

class ManageTestRetakesForm(forms.Form):
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Выберите студентов для разрешения повторного прохождения"
    )

    def __init__(self, *args, **kwargs):
        test = kwargs.pop('test', None)
        super().__init__(*args, **kwargs)

        # Фильтрация студентов: только те, кто уже проходил тест, но не имеет активного разрешения на повторное прохождение
        if test:
<<<<<<< Updated upstream
=======
            # Показываем только тех, кто уже сдавал этот тест
>>>>>>> Stashed changes
            self.fields['students'].queryset = User.objects.filter(
                testresult__test=test
            ).exclude(
                testretakepermission__test=test, testretakepermission__allowed=True
            ).distinct()

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        label='Электронная почта', 
        required=True, 
        validators=[EmailValidator()], 
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    surname = forms.CharField(
        label='Фамилия', 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    given_name = forms.CharField(
        label='Имя', 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    patronymic = forms.CharField(
        label='Отчество', 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    date_of_birth = forms.DateField(
        label='Дата рождения', 
        required=False, 
        widget=forms.DateInput(
            format='%Y-%m-%d', 
            attrs={'class': 'form-control', 'type': 'date'}
        )
    )

    class Meta:
        model = User
        fields = (
            'username', 'email', 'surname', 
            'given_name', 'patronymic', 
            'date_of_birth', 'password1', 'password2'
        )

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'name': 'Название курса',
            'description': 'Описание',
        }

class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ['name', 'description', 'parent_topic']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'parent_topic': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Название темы',
            'description': 'Описание темы',
            'parent_topic': 'Родительская тема',
        }

    def __init__(self, *args, **kwargs):
        current_course = kwargs.pop('current_course', None)
        super().__init__(*args, **kwargs)
        if current_course:
            self.fields['parent_topic'].queryset = Topic.objects.filter(course=current_course)
        else:
            self.fields['parent_topic'].queryset = Topic.objects.none()

class UserProfileForm(forms.ModelForm):
    email = forms.EmailField(label='Email')

    class Meta:
        model = User
        fields = ['surname', 'given_name', 'patronymic', 'date_of_birth', 'email', 'username']
        widgets = {
            'surname': forms.TextInput(attrs={'class': 'form-control'}),
            'given_name': forms.TextInput(attrs={'class': 'form-control'}),
            'patronymic': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'surname': 'Фамилия',
            'given_name': 'Имя',
            'patronymic': 'Отчество',
            'date_of_birth': 'Дата рождения',
            'email': 'Email',
            'username': 'Username',
        }

class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': 'Название теста',
        }

class AddGroupMemberForm(forms.ModelForm):
    class Meta:
        model = GroupMember
        fields = ['user']  # Удалено 'is_instructor'
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'user': 'Пользователь',
        }

    def clean_user(self):
        user = self.cleaned_data['user']
        if is_instructor(user):
            raise forms.ValidationError("Нельзя добавить преподавателя в группу.")
        return user

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')

        if user and GroupMember.objects.filter(user=user).exists():
            self.add_error('user', 'Этот студент уже состоит в другой группе.')
        return cleaned_data

class TestItemForm(forms.ModelForm):
    class Meta:
        model = TestItem
        fields = ['question_type', 'content', 'correct_text_answer', 'order_index']
        widgets = {
            'question_type': forms.Select(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'correct_text_answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'order_index': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'question_type': 'Тип вопроса',
            'content': 'Вопрос',
            'correct_text_answer': 'Правильный текстовый ответ',
            'order_index': 'Порядок отображения',
        }

class TestItemOptionForm(forms.ModelForm):
    class Meta:
        model = TestItemOption
        fields = ['content', 'is_correct']
        widgets = {
            'content': forms.TextInput(attrs={'class': 'form-control'}),
            'is_correct': forms.CheckboxInput(),
        }
        labels = {
            'content': 'Вариант ответа',
            'is_correct': 'Правильный ответ',
        }

class TopicContentForm(forms.ModelForm):
    class Meta:
        model = TopicContent
        fields = ['content_type', 'content', 'text_content', 'order_index']

    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('content_type')
        content = cleaned_data.get('content')
        text_content = cleaned_data.get('text_content')

        if content_type == 'text' and not text_content:
            raise forms.ValidationError('Пожалуйста, введите текстовое содержимое.')
        if content_type in ['file', 'image', 'video', 'audio'] and not content:
            raise forms.ValidationError('Пожалуйста, загрузите файл для выбранного типа контента.')

        return cleaned_data

class CourseMaterialPreferenceForm(forms.ModelForm):
    class Meta:
        model = CourseMaterialPreference
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Название предпочтения',
        }

class PsychologicalTestResultForm(forms.ModelForm):
    class Meta:
        model = PsychologicalTestResult
        fields = ['preference']
        widgets = {
            'preference': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'preference': 'Предпочтение',
        }

class GroupForm(forms.ModelForm):
    class Meta:
        model = StudyGroup
        fields = ['name', 'courses']  # Используем 'courses' вместо 'course'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'courses': forms.CheckboxSelectMultiple(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Название группы',
            'courses': 'Курсы',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(GroupForm, self).__init__(*args, **kwargs)
        if user and not user.is_superuser:
            # Преподаватель может связывать группу только со своими курсами
            self.fields['courses'].queryset = Course.objects.filter(instructor=user)
        else:
            self.fields['courses'].queryset = Course.objects.all()

class GroupMemberForm(forms.ModelForm):
    class Meta:
        model = GroupMember
        fields = ['user']  # Удалили 'is_instructor'
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'user': 'Пользователь',
        }

    def clean_user(self):
        user = self.cleaned_data['user']
        if is_instructor(user):
            raise forms.ValidationError("Нельзя добавить преподавателя в группу.")
        return user

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')

        if user and GroupMember.objects.filter(user=user).exists():
            self.add_error('user', 'Этот студент уже состоит в другой группе.')
        return cleaned_data
<<<<<<< Updated upstream
=======

class PsychTestForm(forms.Form):
    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions')
        super().__init__(*args, **kwargs)
        for question in questions:
            choices = [(answer.id, answer.text) for answer in question.answers.all()]
            self.fields[f'question_{question.id}'] = forms.ChoiceField(
                label=question.text,
                choices=choices,
                widget=forms.RadioSelect,
                required=True
            )
>>>>>>> Stashed changes
