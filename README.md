# Task Manager

A Django-based task management application developed as part of an internship project at **HooYia**.

The project is designed to consolidate and strengthen practical knowledge of Django, particularly **MVT architecture, relational data modeling, authentication, CRUD operations, navigation, user-specific data isolation, and access control**.

---

## Project Overview

Task Manager allows authenticated users to create and manage their own projects and the tasks associated with those projects.

The main principle of the application is **data ownership**:

> A user can only access the projects they own and the tasks belonging to those projects.

The application also distinguishes between public content and authenticated user content.

### Main application areas

* Public landing page
* User registration
* User authentication
* Private authenticated workspace
* Project management
* Task management
* User profile
* User-specific data isolation
* Administrative permissions

---

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

---

## Core Architecture

The project follows Django's MVT architecture:

```text
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
```

The project is divided into several Django applications according to their responsibilities.

```text
Task Manager
│
├── accounts/
│   ├── authentication
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
    └── task management
```

---

## Data Model

The application is based on related entities rather than a single-table structure.

### User

A custom Django user model is used.

```text
User
│
├── username
├── email
├── password
├── role
└── account status
```

The custom user model is based on Django's `AbstractUser`.

The project uses:

```python
AUTH_USER_MODEL = "accounts.User"
```

### Project

Each project belongs to one user.

```text
User 1 ──────────── * Project
```

Conceptually:

```text
User
 │
 ├── Project A
 │    ├── Task 1
 │    └── Task 2
 │
 └── Project B
      └── Task 3
```

### Task

Each task belongs to one project.

```text
Project 1 ──────────── * Task
```

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

---

## Data Ownership and Security

One of the main objectives of the project is to ensure that users cannot access another user's data.

For example:

```text
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
```

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

---

## Authentication

The authentication system is implemented using Django's built-in authentication mechanisms combined with a custom user model.

Current authentication flow:

```text
Registration
     │
     ▼
Create User
     │
     ▼
Login
     │
     ▼
Authenticated Session
     │
     ▼
Private Workspace
```

Implemented authentication features include:

* User registration
* Login
* Logout
* Password validation
* Authentication error handling
* Session-based authentication
* Protected authenticated views

---

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

---

## Project Navigation

The application is designed around resource navigation.

The expected navigation flow is:

```text
Public Landing Page
        │
        ▼
     Register
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
```

---

## Templates Structure

The template architecture follows the application's functional areas.

```text
templates/
│
├── home.html
│
├── base.html
│
├── accounts/
│   ├── register.html
│   └── login.html
│
├── profile/
│   └── profile.html
│
├── projects/
│   ├── project_list.html
│   ├── project_detail.html
│   └── project_form.html
│
└── tasks/
    ├── task_list.html
    ├── task_detail.html
    └── task_form.html
```

`home.html` represents the public landing page.

`base.html` represents the authenticated user's private workspace.

---

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

---

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

---

## Current Development Status

### Authentication

* [x] Custom user model using `AbstractUser`
* [x] `AUTH_USER_MODEL` configuration
* [x] User registration
* [x] Login
* [x] Logout
* [x] Authentication error handling
* [x] Protected authenticated workspace
* [ ] Complete authentication hardening

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

---

## Security Principles

Security is progressively integrated into the project rather than added only at the end.

The current implementation already considers:

* Authentication
* Session management
* Login-protected views
* User ownership
* Query-level data isolation
* Server-side form validation
* CSRF protection
* Restricted project selection
* Object-level access checks

Future security work will include:

* Role-based authorization
* Administrative permissions
* Account activation/deactivation
* More comprehensive authorization tests
* Authentication hardening

---

## Technology Stack

### Backend

* Python
* Django
* Django ORM
* Django Authentication System
* Django Forms

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

---

## Project Structure

```text
task-manager/
│
├── accounts/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
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
│   ├── urls.py
│   └── ...
│
├── manage.py
└── README.md
```

---

## Development Philosophy

This project is intentionally developed progressively.

The goal is not simply to produce a functional application, but to understand **why each Django mechanism is used and how the different components interact**.

The development progression follows this principle:

```text
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
Testing
        ↓
Optimization
        ↓
Deployment
```

The project therefore serves both as an application and as a practical foundation for progressing from basic Django development toward more advanced backend engineering practices.

---

## Future Improvements

Once the core functionality is completed, the project may progressively incorporate more advanced Django/backend concepts, including:

* Advanced QuerySet optimization
* `select_related()`
* `prefetch_related()`
* Pagination
* Caching
* Middleware
* Rate limiting
* Background tasks
* Scheduled tasks
* Redis
* Celery
* Automated testing
* API development with Django REST Framework
* Production deployment
* PostgreSQL optimization
* Logging and monitoring

These features are intentionally kept outside the initial scope until the fundamental Django architecture and application requirements are fully mastered.

---

## Project Goal

The ultimate goal is to transform a relatively simple task management application into a solid practical exercise covering the fundamental concepts required for professional Django backend development.

The project emphasizes **understanding, security, maintainability, and progressive complexity** rather than simply implementing features as quickly as possible.


<!-- PITCHER_START -->

# task_manager

## Overview

task_manager is a Python Application documented automatically by Pitcher.

---

## Project Information

| Property | Value |
|----------|--------|
| Project Name | task_manager |
| Project Type | Python Application |
| Total Folders | 5615 |
| Total Files | 11451 |
| Empty Folders | 3 |

---

## Technology Stack

- HTML
- CSS
- JavaScript
- Python
- Environment Variables

---