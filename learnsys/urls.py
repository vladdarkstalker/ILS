# learnsys/urls.py

from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'learnsys'  # Пространство имён приложения

urlpatterns = [
    # Главная страница и аутентификация
    path('', views.home_page, name='home'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='learnsys:home'), name='logout'),
    path('register/', views.UserRegisterView.as_view(), name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    path('profile/password/', views.CustomPasswordChangeView.as_view(), name='password_change'),

    # Дашборд студента
    path('student/dashboard/', views.StudentDashboardView.as_view(), name='student_dashboard'),

    # Дашборд и управление для преподавателя
    path('instructor/dashboard/', views.InstructorDashboardView.as_view(), name='instructor_dashboard'),
    path('instructor/courses/', views.InstructorCoursesView.as_view(), name='instructor_courses'),
    path('courses/create/', views.CourseCreateView.as_view(), name='course_create'),
    path('instructor/courses/add/', views.CourseCreateView.as_view(), name='course_add'),
    path('instructor/courses/<int:pk>/edit/', views.CourseUpdateView.as_view(), name='course_edit'),
    path('courses/<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    path('instructor/courses/<int:pk>/groups/', views.CourseGroupsView.as_view(), name='course_groups'),

    # Группы
    path('groups/', views.GroupListView.as_view(), name='group_list'),
    path('groups/create/', views.GroupCreateView.as_view(), name='group_create'),
    path('groups/<int:pk>/', views.GroupDetailView.as_view(), name='group_detail'),
    path('groups/<int:pk>/edit/', views.GroupUpdateView.as_view(), name='group_edit'),
    path('groups/<int:pk>/delete/', views.GroupDeleteView.as_view(), name='group_delete'),

    # Добавление и удаление участников группы
    path('groups/<int:group_id>/add_member/', views.AddGroupMemberView.as_view(), name='add_group_member'),
    path('groups/<int:group_id>/remove_member/<int:pk>/', views.RemoveGroupMemberView.as_view(), name='remove_group_member'),

    # Студенты
    path('instructor/students/<int:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('instructor/students/<int:course_id>/list/', views.StudentListView.as_view(), name='student_list'),

    # Курсы и темы
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('instructor/courses/<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('courses/<int:course_id>/topics/', views.TopicListView.as_view(), name='topic_list'),
    path('courses/<int:course_id>/topics/add/', views.TopicCreateView.as_view(), name='topic_add'),
    path('topics/<int:pk>/', views.TopicDetailView.as_view(), name='topic_detail'),
    path('topics/<int:pk>/edit/', views.TopicUpdateView.as_view(), name='topic_edit'),
    path('topics/<int:pk>/delete/', views.TopicDeleteView.as_view(), name='topic_delete'),

    # Управление контентом темы
    path('topics/<int:topic_id>/contents/add/', views.TopicContentCreateView.as_view(), name='topiccontent_add'),
    path('topiccontents/<int:pk>/edit/', views.TopicContentUpdateView.as_view(), name='topic_content_edit'),
    path('topiccontents/<int:pk>/delete/', views.TopicContentDeleteView.as_view(), name='topic_content_delete'),

    # Тесты
    path('topics/<int:topic_id>/tests/', views.TestListView.as_view(), name='test_list'),
    path('topics/<int:topic_id>/tests/create/', views.TestCreateView.as_view(), name='test_create'),
    path('tests/<int:pk>/', views.TestDetailView.as_view(), name='test_detail'),
    path('tests/<int:pk>/edit/', views.TestUpdateView.as_view(), name='test_update'),
    path('tests/<int:pk>/delete/', views.TestDeleteView.as_view(), name='test_delete'),
    path('tests/<int:test_id>/manage_retakes/', views.ManageTestRetakesView.as_view(), name='manage_test_retakes'),
    path('tests/<int:test_id>/take_again/', views.TakeTestAgainView.as_view(), name='take_test_again'),
    path('test_results/<int:test_result_id>/', views.TestResultDetailView.as_view(), name='test_result_detail'),

    # Управление вопросами теста
    path('tests/<int:test_id>/items/add/', views.TestItemCreateView.as_view(), name='testitem_add'),
    path('testitems/<int:pk>/edit/', views.TestItemUpdateView.as_view(), name='testitem_edit'),
    path('testitems/<int:pk>/delete/', views.TestItemDeleteView.as_view(), name='testitem_delete'),

    # Управление вариантами ответов
    path('testitems/<int:item_id>/options/add/', views.TestItemOptionCreateView.as_view(), name='testitemoption_add'),
    path('testitemoptions/<int:pk>/edit/', views.TestItemOptionUpdateView.as_view(), name='testitemoption_edit'),
    path('testitemoptions/<int:pk>/delete/', views.TestItemOptionDeleteView.as_view(), name='testitemoption_delete'),

    # Дополнительные пути для загрузки информации о студенте
    path('instructor/students/<int:pk>/download/', views.DownloadStudentInfoView.as_view(), name='download_student_info'),

    path('topics/<int:pk>/generate_questions/', views.GenerateQuestionsView.as_view(), name='generate_questions'),

    # Психтесты
    path('psych_tests/', views.psych_test_list, name='psych_test_list'),
    path('psych_tests/<int:test_id>/', views.psych_take_test, name='psych_take_test'),
    path('psych_tests/<int:test_id>/results/', views.psych_test_results, name='psych_test_result'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
