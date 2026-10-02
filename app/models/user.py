from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'lecturer', 'alumni', 'admin'
    is_active_account = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Student(db.Model):
    __tablename__ = "students"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    matric_number = db.Column(db.String(30), nullable=False, unique=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    level_id = db.Column(db.Integer, db.ForeignKey("levels.id"), nullable=False)
    preferred_resource_type = db.Column(db.String(20))  # pdf, video, textbook, notes

    user = db.relationship("User", backref=db.backref("student_profile", uselist=False))
    department = db.relationship("Department", backref="students")
    level = db.relationship("Level", backref="students")


class Lecturer(db.Model):
    __tablename__ = "lecturers"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculties.id"), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    specialization = db.Column(db.String(200))
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    verification_document = db.Column(db.String(500))

    user = db.relationship("User", backref=db.backref("lecturer_profile", uselist=False))
    faculty = db.relationship("Faculty", backref="lecturers")
    department = db.relationship("Department", backref="lecturers")


class Alumni(db.Model):
    __tablename__ = "alumni"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    matric_number = db.Column(db.String(30), nullable=False, unique=True)
    graduation_year = db.Column(db.Integer, nullable=False)
    degree_class = db.Column(db.String(30))
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    verification_document = db.Column(db.String(500))

    user = db.relationship("User", backref=db.backref("alumni_profile", uselist=False))


class Admin(db.Model):
    __tablename__ = "admins"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)

    user = db.relationship("User", backref=db.backref("admin_profile", uselist=False))


class StudentCourse(db.Model):
    __tablename__ = "student_courses"

    student_id = db.Column(db.Integer, db.ForeignKey("students.user_id"), primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), primary_key=True)


class StudentInterest(db.Model):
    __tablename__ = "student_interests"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.user_id"), nullable=False)
    interest_tag = db.Column(db.String(100), nullable=False)