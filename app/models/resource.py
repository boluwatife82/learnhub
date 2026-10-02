from datetime import datetime
from app.extensions import db


class Resource(db.Model):
    __tablename__ = "resources"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text)
    resource_type = db.Column(db.String(20), nullable=False)  # pdf, youtube, textbook
    file_url = db.Column(db.String(500), nullable=False)

    university_id = db.Column(db.Integer, db.ForeignKey("universities.id"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculties.id"), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    level_id = db.Column(db.Integer, db.ForeignKey("levels.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)

    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending, approved, rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)

    uploader = db.relationship("User", foreign_keys=[uploaded_by], backref="uploaded_resources")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by], backref="reviewed_resources")
    course = db.relationship("Course", backref="resources")
    department = db.relationship("Department", backref="resources")
    level = db.relationship("Level", backref="resources")
    faculty = db.relationship("Faculty", backref="resources")