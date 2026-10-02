from app.extensions import db


class University(db.Model):
    __tablename__ = "universities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    faculties = db.relationship("Faculty", backref="university", lazy=True)


class Faculty(db.Model):
    __tablename__ = "faculties"

    id = db.Column(db.Integer, primary_key=True)
    university_id = db.Column(db.Integer, db.ForeignKey("universities.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)

    departments = db.relationship("Department", backref="faculty", lazy=True)


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculties.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)

    courses = db.relationship("Course", backref="department", lazy=True)


class Level(db.Model):
    __tablename__ = "levels"

    id = db.Column(db.Integer, primary_key=True)
    level_number = db.Column(db.Integer, nullable=False, unique=True)  # e.g. 100, 200, 300, 400


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    level_id = db.Column(db.Integer, db.ForeignKey("levels.id"), nullable=False)
    course_code = db.Column(db.String(20), nullable=False)
    course_title = db.Column(db.String(200), nullable=False)

    level = db.relationship("Level", backref="courses")