# Task Manager

A Django-based task management application developed as part of an internship project at **HooYia**.

The project is designed to consolidate and strengthen practical knowledge of Django, particularly **MVT architecture, relational data modeling, authentication, CRUD operations, navigation, user-specific data isolation, and access control**.


## Project Overview

Task Manager allows authenticated users to create and manage their own projects and the tasks associated with those projects.

The main principle of the application is **data ownership**:

> A user can only access the projects they own and the tasks belonging to those projects.

The application also distinguishes between public content and authenticated user content.

### Main application areas

* Public landing page
* User registration
* User authentication
* Email verification
* Scheduled task reminders (daily email digest)
* Private authenticated workspace
* Project management
* Task management
* User profile
* User-specific data isolation
* Administrative permissions


## Project Objectives

This project was assigned to consolidate practical Django knowledge through a progressively structured application.

The main learning objectives are:

* Understand and apply Django's **MVT architecture**
* Work with multiple related database models
* Understand and implement `ForeignKey` relationships
* Implement complete CRUD operations
* Build navigation between related resources
* Implement authentication
* Protect authenticated routes
* Isolate user-owned data
* Implement role-based permissions
* Handle form validation and errors
* Structure a Django project using multiple applications
* Improve backend security practices
* Understand how Django handles requests, forms, sessions, authentication and database queries
* Understand and implement background/asynchronous processing with Celery and Redis
* Understand and implement scheduled/periodic tasks with Celery Beat


## Core Architecture

The project follows Django's MVT architecture:

User
 │
 ▼
URL
 │
 ▼
View
 │
 ├── Form
 ├── Model / ORM
 └── Business Logic
 │
 ▼
Template
 │
 ▼
HTML Response

The project is divided into several Django applications according to their responsibilities.

Task Manager
│
├── accounts/
│   ├── authentication
│   ├── email verification (OTP)
│   ├── registration
│   ├── logout
│   ├── user management
│   └── profile
│
├── core/
│   └── public pages
│
├── projects/
│   └── project management
│
└── tasks/
    ├── task management
    └── scheduled reminder emails


## Data Model

The application is based on related entities rather than a single-table structure.

### User

A custom Django user model is used.

User
│
├── username
├── email
├── password
├── role
├── is_email_verified
└── account status

The custom user model is based on Django's `AbstractUser`.

The project uses:

```python
AUTH_USER_MODEL = "accounts.User"
```

### Project

Each project belongs to one user.

User 1 ──────────── * Project

Conceptually:

User
 │
 ├── Project A
 │    ├── Task 1
 │    └── Task 2
 │
 └── Project B
      └── Task 3

### Task

Each task belongs to one project.

Project 1 ──────────── * Task

A task contains:

* Title
* Description
* Status
* Due date
* Creation date
* Update date

Task statuses currently include:

* `TODO`
* `IN_PROGRESS`
* `DONE`


## Data Ownership and Security

One of the main objectives of the project is to ensure that users cannot access another user's data.

For example:

User A
│
├── Project A1
│   ├── Task A1
│   └── Task A2
│
└── Project A2
    └── Task A3


User B
│
└── Project B1
    ├── Task B1
    └── Task B2

User A must never receive User B's projects or tasks.

This is enforced at the query level.

For projects:

```python
Project.objects.filter(user=request.user)
```

For tasks:

```python
Task.objects.filter(project__user=request.user)
```

This approach ensures that ownership is checked directly when retrieving the objects.

The task creation form also restricts the `project` choices to projects belonging to the authenticated user.


## Authentication

The authentication system is implemented using Django's built-in authentication mechanisms combined with a custom user model.

Current authentication flow:

Registration
     │
     ▼
Create User
     │
     ▼
Email Verification (OTP)
     │
     ▼
Login
     │
     ▼
Authenticated Session
     │
     ▼
Private Workspace

Implemented authentication features include:

* User registration
* Login
* Logout
* Password validation
* Authentication error handling
* Session-based authentication
* Protected authenticated views
* Email verification via one-time password (OTP)


## Email Verification

Email verification is implemented using a one-time password (OTP) sent to the user's email address, generated and validated server-side, and delivered asynchronously through Celery.

Flow:

Registration
     │
     ▼
Generate OTP (hashed, time-limited)
     │
     ▼
Send OTP email (async, via Celery + Redis)
     │
     ▼
User submits code
     │
     ▼
Code validated (attempts and expiration checked)
     │
     ▼
Account marked as verified

Key implementation details:

* The OTP is hashed before being stored (never stored in plain text)
* Each OTP has a configurable expiration (`OTP_TTL_MINUTES`)
* Each OTP has a configurable maximum number of attempts (`OTP_MAX_ATTEMPTS`)
* Sending the OTP email does not block the HTTP request/response cycle, since it is delegated to a Celery task
* Failed email sends are retried automatically (up to 3 attempts)


## Scheduled Tasks (Celery Beat)

In addition to on-demand asynchronous tasks (such as sending the OTP email), the application implements **periodic/scheduled** background processing using Celery Beat.

Every day at a configured time, a scheduled task runs to:

1. Collect all tasks that are not yet marked as `DONE`, grouped by the owning user
2. Send each user a reminder email listing their pending tasks

Architecture:

Celery Beat (scheduler)
     │
     ▼
Pushes "send_daily_task_reminder" to the queue at the scheduled time
     │
     ▼
Celery Worker picks it up
     │
     ▼
Groups pending tasks by user
     │
     ▼
Dispatches one "send_reminder_email_task" per user (async, retryable)
     │
     ▼
Email sent via SMTP

This distinction matters: **Celery** executes tasks asynchronously on demand, while **Celery Beat** is a separate scheduler process responsible for triggering tasks automatically at fixed times, independent of any user action.

The schedule is configured in `settings.py` via `CELERY_BEAT_SCHEDULE`, using `Africa/Douala` as the reference timezone (`TIME_ZONE` / `CELERY_TIMEZONE`), so scheduled times are expressed directly in local time.


## CRUD Operations

The project management system implements the four fundamental CRUD operations.

### Create

Users can create projects and tasks.

### Read

Users can view their own projects and their associated tasks.

### Update

Users can modify their own projects and tasks.

### Delete

Users can delete their own projects and tasks.

The project also includes dedicated detail views for individual resources.


## Project Navigation

The application is designed around resource navigation.

The expected navigation flow is:

Public Landing Page
        │
        ▼
     Register
        │
        ▼
  Email Verification
        │
        ▼
      Login
        │
        ▼
Private Workspace
        │
        ▼
   Project List
        │
        ├──────────► Create Project
        │
        ├──────────► Update Project
        │
        ├──────────► Delete Project
        │
        └──────────► Project Detail
                         │
                         ▼
                     Task List
                         │
                         ├── Create Task
                         ├── Update Task
                         ├── Delete Task
                         └── Task Detail


## Templates Structure

The template architecture follows the application's functional areas.

templates/
│
├── home.html
│
├── base.html
│
├── accounts/
│   ├── emails/
│   │   ├── otp_register.txt
│   │   ├── otp_reset.txt
│   │   └── registration_alert.txt
│   ├── register.html
│   ├── login.html
│   ├── forgot_password.html
│   ├── reset_password.html
│   ├── verify_otp.html
│   └── verify_reset_otp.html
│
├── profile/
│   └── profile.html
│
├── projects/
│   ├── project_list.html
│   ├── project_detail.html
│   ├── project_form.html
│   └── confirm_supp_project.html
│
└── tasks/
    ├── emails/
    │   └── daily_reminder.txt
    ├── task_list.html
    ├── task_detail.html
    ├── task_form.html
    └── confirm_suppr_task.html

`home.html` represents the public landing page.

`base.html` represents the authenticated user's private workspace.


## Forms

The project uses Django `ModelForm` classes to handle user input.

### ProjectForm

Responsible for:

* Project name
* Project description

### TaskForm

Responsible for:

* Project selection
* Task title
* Description
* Status
* Due date

The `TaskForm` receives the authenticated user and dynamically restricts the project queryset:

```python
Project.objects.filter(user=user)
```

This prevents users from selecting projects that do not belong to them through the normal application interface.


## Django ORM

The project uses Django's ORM instead of writing raw SQL for normal database operations.

Examples include:

```python
Project.objects.filter(user=request.user)
```

and:

```python
Task.objects.filter(project__user=request.user)
```

The project therefore provides practical experience with:

* QuerySets
* Filtering
* ForeignKey relationships
* Related-object lookups
* `get_object_or_404()`
* Object creation
* Object modification
* Object deletion


## Background Processing & Scheduling (Celery, Redis, Celery Beat)

The application uses:

* **Redis** as the message broker and result backend
* **Celery** to execute asynchronous tasks (email sending, OTP delivery) without blocking HTTP requests
* **Celery Beat** to trigger periodic tasks (the daily task reminder email)

Running the application locally requires the following processes in parallel:

```bash
redis-server
python manage.py runserver
celery -A config worker -l info
celery -A config beat -l info
```


## Current Development Status

### Authentication

* [x] Custom user model using `AbstractUser`
* [x] `AUTH_USER_MODEL` configuration
* [x] User registration
* [x] Login
* [x] Logout
* [x] Authentication error handling
* [x] Protected authenticated workspace
* [x] Verification by e-mail
* [ ] Complete authentication hardening

### Email Verification

- [x] Email verification code generation (OTP)
- [x] Verification email sending (async via Celery)
- [x] Verification code validation
- [x] Code/token expiration
- [ ] Prevent access to protected features before verification
- [ ] Resend verification email
- [ ] Handle invalid or expired verification links

### Scheduled Tasks

- [x] Celery Beat integration
- [x] Daily task reminder email (per user, pending tasks)
- [x] Configurable schedule via `CELERY_BEAT_SCHEDULE`
- [x] Timezone-aware scheduling (`Africa/Douala`)
- [ ] Filter reminders by due date (currently all non-`DONE` tasks)
- [ ] User-configurable reminder time/opt-out

### Projects

* [x] Project model
* [x] Project form
* [x] Project list
* [x] Project creation
* [x] Project update
* [x] Project deletion
* [x] Project detail
* [x] User ownership filtering
* [ ] Final UI integration
* [ ] Additional validation and testing

### Tasks

* [x] Task model
* [x] Task form
* [x] Task list
* [x] Task creation
* [x] Task update
* [x] Task deletion
* [x] Task detail
* [x] Project/User ownership filtering
* [x] User-specific project selection
* [ ] Final UI integration
* [ ] Additional validation and testing

### User Management

* [ ] User profile
* [ ] `ADMIN / MEMBER` permissions
* [ ] Administrative user management
* [ ] Account activation/deactivation
* [ ] Permission-based access control

### Testing

* [ ] Model tests
* [ ] Form tests
* [ ] View tests
* [ ] Authentication tests
* [ ] Authorization tests
* [ ] User data isolation tests
* [ ] CRUD integration tests


## Security Principles

Security is progressively integrated into the project rather than added only at the end.

The current implementation already considers:

* Authentication
* Email verification
* Session management
* Login-protected views
* User ownership
* Query-level data isolation
* Server-side form validation
* CSRF protection
* Restricted project selection
* Object-level access checks
* Hashed, time-limited, attempt-limited OTP codes

Future security work will include:

* Role-based authorization
* Administrative permissions
* Account activation/deactivation
* More comprehensive authorization tests
* Authentication hardening


## Technology Stack

### Backend

* Python
* Django
* Django ORM
* Django Authentication System
* Django Forms
* Celery
* Celery Beat

### Infrastructure

* Redis (message broker / result backend)

### Database

* SQLite during development
* PostgreSQL planned/available for production-oriented development

### Frontend

* HTML
* CSS
* Django Templates

### Development Tools

* Git
* GitHub
* Linux
* Virtual environments


## Project Structure

task-manager/
│
├── accounts/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── tasks.py
│   └── ...
│
├── core/
│   ├── views.py
│   ├── urls.py
│   └── ...
│
├── projects/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   └── ...
│
├── tasks/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── tasks.py
│   └── ...
│
├── templates/
│   ├── home.html
│   ├── base.html
│   ├── accounts/
│   ├── profile/
│   ├── projects/
│   └── tasks/
│
├── static/
│   └── ...
│
├── config/
│   ├── settings.py
│   ├── celery.py
│   ├── urls.py
│   └── ...
│
├── manage.py
├── celerybeat-schedule  (ignored via .gitignore)
└── README.md


## Development Philosophy

This project is intentionally developed progressively.

The goal is not simply to produce a functional application, but to understand **why each Django mechanism is used and how the different components interact**.

The development progression follows this principle:

Django Fundamentals
        ↓
MVT Architecture
        ↓
Models & Relationships
        ↓
Forms
        ↓
CRUD
        ↓
Authentication
        ↓
Protected Routes
        ↓
User Data Isolation
        ↓
Authorization
        ↓
Background & Scheduled Tasks
        ↓
Testing
        ↓
Optimization
        ↓
Deployment

The project therefore serves both as an application and as a practical foundation for progressing from basic Django development toward more advanced backend engineering practices.


## Future Improvements

Once the core functionality is completed, the project may progressively incorporate more advanced Django/backend concepts, including:

* Advanced QuerySet optimization
* `select_related()`
* `prefetch_related()`
* Pagination
* Caching
* Middleware
* Rate limiting
* Automated testing
* API development with Django REST Framework
* Production deployment
* PostgreSQL optimization
* Logging and monitoring

These features are intentionally kept outside the initial scope until the fundamental Django architecture and application requirements are fully mastered.


### Optimization

The application will progressively implement optimization techniques in order to reduce unnecessary HTTP requests, database queries, processing overhead, and duplicated work.

#### Frontend / HTTP Optimization

- [ ] Reduce unnecessary page reloads
- [ ] Open edit forms directly on the current page
- [ ] Implement inline editing or modal forms where appropriate
- [ ] Avoid unnecessary navigation between pages
- [ ] Load only the required content when possible
- [ ] Reduce unnecessary requests to the server
- [ ] Optimize static assets
- [ ] Minimize unnecessary JavaScript and CSS requests

#### Database / ORM Optimization

- [ ] Avoid unnecessary database queries
- [ ] Avoid evaluating the same QuerySet multiple times
- [ ] Use `exists()` when only checking whether data exists
- [ ] Use `select_related()` for appropriate ForeignKey relationships
- [ ] Use `prefetch_related()` for appropriate reverse/many-to-many relationships
- [ ] Use `only()` and `defer()` when appropriate
- [ ] Use `values()` / `values_list()` when complete model instances are unnecessary
- [ ] Use `bulk_create()` for appropriate batch insert operations
- [ ] Use `bulk_update()` for appropriate batch update operations
- [ ] Implement pagination for large datasets
- [ ] Add appropriate database indexes
- [ ] Analyze slow queries
- [ ] Avoid N+1 query problems

#### Application-Level Optimization

- [ ] Implement caching where appropriate
- [ ] Avoid duplicated computations
- [ ] Avoid repeated QuerySet evaluation
- [ ] Optimize expensive business logic
- [x] Use background tasks for appropriate long-running operations
- [x] Use scheduled tasks where appropriate
- [x] Introduce Redis where justified
- [x] Introduce Celery for asynchronous/background processing where justified

#### Performance Testing

- [ ] Measure the number of HTTP requests
- [ ] Measure the number of database queries
- [ ] Identify slow queries
- [ ] Compare optimized and non-optimized implementations
- [ ] Test application performance with larger datasets


## Project Goal

The ultimate goal is to transform a relatively simple task management application into a solid practical exercise covering the fundamental concepts required for professional Django backend development.

The project emphasizes **understanding, security, maintainability, and progressive complexity** rather than simply implementing features as quickly as possible.