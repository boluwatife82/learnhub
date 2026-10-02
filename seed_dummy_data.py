"""
DUMMY DATA SEED SCRIPT — for demonstrating Collaborative Filtering.

All accounts use @dummy.test emails and names prefixed "Dummy" so they're
easy to identify and delete later via flask shell or the admin panel.

Run with: flask shell < seed_dummy_data.py   (or paste into flask shell manually)
Actually easiest: run as a script via `python seed_dummy_data.py`
"""

from app import create_app
from app.extensions import db
from app.models import (
    User, Student, Department, Level, Faculty, University, Course,
    Resource, Rating, Vote, Download, UserInteraction, StudentInterest
)
import random
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    # ---- Get existing academic structure (reuse what you already seeded) ----
    department = Department.query.first()
    level = Level.query.filter_by(level_number=300).first() or Level.query.first()
    university = University.query.first()
    faculty = Faculty.query.first()
    course = Course.query.first()

    if not all([department, level, university, faculty, course]):
        print("ERROR: You need at least one Department, Level, Faculty, University, and Course seeded first.")
        exit()

    admin_user = User.query.filter_by(role="admin").first()
    if not admin_user:
        print("ERROR: No admin user found — needed to mark dummy resources as uploaded/approved.")
        exit()

    print("Using department:", department.name, "| course:", course.course_code)

    # ---- Create 6 dummy students with varied profiles ----
    dummy_students_data = [
        {"name": "Dummy Tobi Adekunle", "email": "dummy1@dummy.test", "interests": ["Goal: Exam Preparation", "Style: Reading Notes", "Interest: Technology"], "pref": "pdf"},
        {"name": "Dummy Chiamaka Okafor", "email": "dummy2@dummy.test", "interests": ["Goal: Exam Preparation", "Style: Reading Notes", "Interest: Technology"], "pref": "pdf"},
        {"name": "Dummy Segun Bello", "email": "dummy3@dummy.test", "interests": ["Goal: Practical Skills", "Style: Video Tutorials", "Interest: Technology"], "pref": "video"},
        {"name": "Dummy Amaka Nwosu", "email": "dummy4@dummy.test", "interests": ["Goal: Practical Skills", "Style: Video Tutorials", "Interest: Technology"], "pref": "video"},
        {"name": "Dummy Yusuf Ibrahim", "email": "dummy5@dummy.test", "interests": ["Goal: Research", "Style: Research-based", "Interest: Business"], "pref": "textbook"},
        {"name": "Dummy Grace Effiong", "email": "dummy6@dummy.test", "interests": ["Goal: Research", "Style: Research-based", "Interest: Business"], "pref": "textbook"},
    ]

    created_students = []
    for data in dummy_students_data:
        existing = User.query.filter_by(email=data["email"]).first()
        if existing:
            print(f"Skipping {data['email']} — already exists.")
            student = Student.query.filter_by(user_id=existing.id).first()
            created_students.append(student)
            continue

        user = User(full_name=data["name"], email=data["email"], role="student")
        user.set_password("dummy1234")
        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id=user.id,
            matric_number=f"DUMMY/{user.id:04d}",
            department_id=department.id,
            level_id=level.id,
            preferred_resource_type=data["pref"],
        )
        db.session.add(student)
        db.session.flush()

        for tag in data["interests"]:
            db.session.add(StudentInterest(student_id=student.user_id, interest_tag=tag))

        created_students.append(student)
        print(f"Created dummy student: {data['name']} ({data['email']})")

    db.session.commit()

    # ---- Create dummy resources: PDFs, YouTube links, Textbook references ----
    dummy_resources_data = [
        {"title": "Dummy - Intro to Data Structures (PDF Notes)", "type": "pdf", "desc": "Comprehensive notes covering arrays, linked lists, stacks and queues."},
        {"title": "Dummy - Algorithms Crash Course PDF", "type": "pdf", "desc": "Exam-focused summary of sorting and searching algorithms."},
        {"title": "Dummy - Data Structures Full Course (YouTube)", "type": "youtube", "desc": "Full video walkthrough of data structures with coding examples."},
        {"title": "Dummy - Practical Coding Tutorial (YouTube)", "type": "youtube", "desc": "Hands-on tutorial building a project step by step."},
        {"title": "Dummy - Research Methods in Computing (Textbook Ref)", "type": "textbook", "desc": "Reference textbook for academic research methodology."},
        {"title": "Dummy - Business Analytics Case Studies (Textbook Ref)", "type": "textbook", "desc": "Case study collection for business and analytics research."},
    ]

    created_resources = []
    for data in dummy_resources_data:
        existing = Resource.query.filter_by(title=data["title"]).first()
        if existing:
            print(f"Skipping resource '{data['title']}' — already exists.")
            created_resources.append(existing)
            continue

        file_url = "https://www.youtube.com/watch?v=dummy" if data["type"] == "youtube" else \
                   "Dummy Textbook Reference, Chapter 1-3" if data["type"] == "textbook" else \
                   "uploads/dummy_placeholder.pdf"

        resource = Resource(
            title=data["title"],
            description=data["desc"],
            resource_type=data["type"],
            file_url=file_url,
            university_id=university.id,
            faculty_id=faculty.id,
            department_id=department.id,
            level_id=level.id,
            course_id=course.id,
            uploaded_by=admin_user.id,
            status="approved",
            reviewed_by=admin_user.id,
            reviewed_at=datetime.utcnow(),
        )
        db.session.add(resource)
        created_resources.append(resource)
        print(f"Created dummy resource: {data['title']}")

    db.session.commit()

    # ---- Create realistic interaction clusters ----
    # Group A (students 0,1 - "pdf" lovers) interact heavily with the two PDF resources
    # Group B (students 2,3 - "video" lovers) interact heavily with the two YouTube resources
    # Group C (students 4,5 - "textbook" lovers) interact heavily with the two textbook resources
    groups = [
        (created_students[0:2], created_resources[0:2]),
        (created_students[2:4], created_resources[2:4]),
        (created_students[4:6], created_resources[4:6]),
    ]

    interaction_count = 0
    for student_group, resource_group in groups:
        for student in student_group:
            for resource in resource_group:
                # Rating
                if not Rating.query.filter_by(resource_id=resource.id, user_id=student.user_id).first():
                    db.session.add(Rating(resource_id=resource.id, user_id=student.user_id, rating_value=random.randint(4, 5)))
                    db.session.add(UserInteraction(user_id=student.user_id, resource_id=resource.id, interaction_type="rate", weight=1.0))
                    interaction_count += 1

                # Download
                if not Download.query.filter_by(resource_id=resource.id, user_id=student.user_id).first():
                    db.session.add(Download(resource_id=resource.id, user_id=student.user_id))
                    db.session.add(UserInteraction(user_id=student.user_id, resource_id=resource.id, interaction_type="download", weight=2.0))
                    interaction_count += 1

    db.session.commit()
    print(f"\nDone. Created {len(created_students)} dummy students, {len(created_resources)} dummy resources, and {interaction_count} interactions.")
    print("All dummy accounts use password: dummy1234")