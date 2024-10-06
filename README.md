# LearnSys

LearnSys is a Django-based web application for managing educational courses, study groups, and user assessments. It offers functionality for different user roles, including administrators, instructors, and students.

## Table of Contents

- [Features](#features)
- [Technologies Used](#technologies-used)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
  - [Project Directory (`iis`)](#project-directory-iis)
  - [Application Directory (`learnsys`)](#application-directory-learnsys)
  - [Templates Directory](#templates-directory)
- [License](#license)
- [Contact](#contact)

## Features

- **User Roles and Permissions**
  - **Administrators** manage courses, instructors, students, and study groups.
  - **Instructors** create courses, manage study groups, and handle course materials.
  - **Students** enroll in study groups, view their courses, and complete assessments.

- **Course and Study Group Management**
  - **Courses**: Create, update, delete, and manage content for courses.
  - **Study Groups**: Group students by courses for collaborative learning.

- **Assessments and Progress Tracking**
  - **Tests**: Instructors can create and manage various assessments.
  - **Results**: Students can complete tests and track their progress.

## Technologies Used

- **Backend**: [Django](https://www.djangoproject.com/) (Python-based web framework)
- **Database**: [SQLite](https://www.sqlite.org/index.html) (default for development)
- **Frontend**: HTML5, minimal CSS (no comprehensive styling)

## Installation

### Prerequisites

- Python 3.10
- `pip` package manager

### Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/learnsys.git
   cd learnsys
   ```

2. **Create and Activate a Virtual Environment**

   ```bash
   python -m venv env
   ```

   - **Windows**: `env\Scripts\activate`
   - **macOS/Linux**: `source env/bin/activate`

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Apply Migrations**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a Superuser**

   ```bash
   python manage.py createsuperuser
   ```

6. **Run the Development Server**

   ```bash
   python manage.py runserver
   ```

   Visit `http://127.0.0.1:8000/` to access the application.

## Usage

1. **Admin Panel**: Navigate to `http://127.0.0.1:8000/admin/` to manage users, courses, and groups.
2. **Instructor Dashboard**: Manage course materials, tests, and student groups.
3. **Student Dashboard**: Access study materials, take tests, and track performance.

## Project Structure

### Project Directory (`iis`)

Contains core settings and configuration for the Django project:

- **`settings.py`**: Main configuration for the project.
- **`urls.py`**: URL routing for the project.
- **`wsgi.py` & `asgi.py`**: Deployment settings for web servers.
- **`context_processors.py`**: Custom context processors for templates.

### Application Directory (`learnsys`)

Handles the main application logic:

- **`admin.py`**: Customizes the Django admin interface for models.
- **`models.py`**: Defines models for users, courses, groups, and tests.
- **`views.py`**: Contains view logic for handling requests and responses.
- **`forms.py`**: Forms for user input (e.g., login, group creation).
- **`urls.py`**: URL patterns for routing within the `learnsys` app.
- **`templatetags/`**: Custom template tags and filters to enhance templates.

### Templates Directory

HTML templates used for rendering the web application:

- **`admin/`**: Custom admin interface templates.
- **`groups/`**: Templates for managing study groups (list, create, edit).
- **`courses/`**: Templates for course management (list, detail, create).
- **`instructor/`**: Templates for instructor dashboards and student management.
- **`student/`**: Templates for student dashboards and test views.
- **`welcome.html`**: Home/landing page template for unauthenticated users.

> **Note**: The project is currently minimally styled. Future updates may include enhanced frontend styling and user interfaces.
