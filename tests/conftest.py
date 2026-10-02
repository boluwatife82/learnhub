import os

# CRITICAL: this must run before ANY import from the `app` package,
# because app/config.py reads DATABASE_URL at import time, not at
# runtime. If this line runs even one line too late, tests will
# silently connect to your REAL PostgreSQL database instead.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from app import create_app
from app.extensions import db as _db
from app.models import (
    University, Faculty, Department, Level, Course,
    User, Student, Resource, Rating, Vote, Download
)


@pytest.fixture
def app():
    """Creates a Flask app configured for testing, using an in-memory SQLite database."""
    app = create_app("development")

    # Safety check: never allow tests to run against a real database
    assert "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"], \
        "SAFETY ABORT: test is not using SQLite — refusing to run to protect your real data!"

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    """A test client that can simulate browser requests (GET/POST) without a real browser."""
    return app.test_client()


@pytest.fixture
def sample_data(app):
    """
    Creates a minimal, known set of academic + resource data so tests
    have something predictable to work against.
    """
    university = University(name="Test University")
    _db.session.add(university)
    _db.session.flush()

    faculty = Faculty(name="Faculty of Computing", university_id=university.id)
    _db.session.add(faculty)
    _db.session.flush()

    department = Department(name="Computer Science", faculty_id=faculty.id)
    _db.session.add(department)
    _db.session.flush()

    level_300 = Level(level_number=300)
    level_100 = Level(level_number=100)
    _db.session.add_all([level_300, level_100])
    _db.session.flush()

    course = Course(course_code="CSC301", course_title="Algorithms", department_id=department.id, level_id=level_300.id)
    _db.session.add(course)
    _db.session.flush()

    student_user = User(full_name="Test Student", email="student@test.com", role="student")
    student_user.set_password("password123")
    _db.session.add(student_user)
    _db.session.flush()

    student = Student(
        user_id=student_user.id,
        matric_number="TEST/001",
        department_id=department.id,
        level_id=level_300.id,
        preferred_resource_type="pdf",
    )
    _db.session.add(student)
    _db.session.flush()

    admin_user = User(full_name="Test Admin", email="admin@test.com", role="admin")
    admin_user.set_password("password123")
    _db.session.add(admin_user)
    _db.session.flush()

    resource = Resource(
        title="Algorithms Notes",
        description="Sorting and searching algorithms",
        resource_type="pdf",
        file_url="uploads/test.pdf",
        university_id=university.id,
        faculty_id=faculty.id,
        department_id=department.id,
        level_id=level_300.id,
        course_id=course.id,
        uploaded_by=admin_user.id,
        status="approved",
    )
    _db.session.add(resource)
    _db.session.commit()

    return {
        "university": university,
        "department": department,
        "level_300": level_300,
        "level_100": level_100,
        "course": course,
        "student": student,
        "student_user": student_user,
        "admin_user": admin_user,
        "resource": resource,
    }