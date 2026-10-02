from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, redirect, request, url_for, flash, abort, request
from flask_login import login_required, current_user
from wtforms import StringField, SubmitField
from app.models import Resource, User, Alumni, Faculty, Department

from app.extensions import db
from app.models import Resource, User
from app.models.user import Alumni

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    from datetime import timedelta
    from app.models import Student, Lecturer, UserInteraction, User

    # Top-level counts
    total_students = Student.query.count()
    total_lecturers = Lecturer.query.count()
    total_resources = Resource.query.filter_by(status="approved").count()
    total_interactions = UserInteraction.query.count()

    # Pending approval queue (kept from before — core admin task)
    pending_resources = Resource.query.filter_by(status="pending").order_by(Resource.created_at.desc()).all()
    pending_count = len(pending_resources)
    approved_count = Resource.query.filter_by(status="approved").count()
    rejected_count = Resource.query.filter_by(status="rejected").count()

    total_reviewed = pending_count + approved_count + rejected_count
    approval_rate = round((approved_count / total_reviewed) * 100) if total_reviewed > 0 else 0

    # Weekly interaction activity (last 7 days)
    today = datetime.utcnow().date()
    chart_labels = []
    chart_values = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = UserInteraction.query.filter(db.func.date(UserInteraction.created_at) == day).count()
        chart_labels.append(day.strftime("%a"))
        chart_values.append(count)
    max_chart_value = max(chart_values) if max(chart_values) > 0 else 1

    # Recent registrations
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    # User breakdown by role
    role_counts = {
        "student": total_students,
        "lecturer": total_lecturers,
        "alumni": Alumni.query.count(),
        "admin": User.query.filter_by(role="admin").count(),
    }
    total_users = sum(role_counts.values())
    student_pct = round((role_counts["student"] / total_users) * 100) if total_users else 0

       # Top resources by view count (single aggregated query instead of one-per-resource)
    view_counts_subquery = (
        db.session.query(
            UserInteraction.resource_id,
            db.func.count(UserInteraction.id).label("view_count")
        )
        .filter(UserInteraction.interaction_type == "view")
        .group_by(UserInteraction.resource_id)
        .subquery()
    )

    top_resources_query = (
        db.session.query(Resource, db.func.coalesce(view_counts_subquery.c.view_count, 0).label("views"))
        .outerjoin(view_counts_subquery, Resource.id == view_counts_subquery.c.resource_id)
        .filter(Resource.status == "approved")
        .order_by(db.desc("views"))
        .limit(5)
        .all()
    )
    top_resources = [r for r, views in top_resources_query]

     # Most active students by total interaction count (single aggregated query)
    activity_counts = (
        db.session.query(
            UserInteraction.user_id,
            db.func.count(UserInteraction.id).label("activity_count")
        )
        .group_by(UserInteraction.user_id)
        .subquery()
    )

    most_active_query = (
        db.session.query(Student, activity_counts.c.activity_count)
        .join(activity_counts, Student.user_id == activity_counts.c.user_id)
        .order_by(db.desc("activity_count"))
        .limit(5)
        .all()
    )
    most_active_students = [(student, count) for student, count in most_active_query]

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        total_lecturers=total_lecturers,
        total_resources=total_resources,
        total_interactions=total_interactions,
        pending_resources=pending_resources,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        approval_rate=approval_rate,
        chart_labels=chart_labels,
        chart_values=chart_values,
        max_chart_value=max_chart_value,
        recent_users=recent_users,
        role_counts=role_counts,
        student_pct=student_pct,
        top_resources=top_resources,
        most_active_students=most_active_students,
    )


@admin_bp.route("/resources/<int:resource_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    resource.status = "approved"
    resource.reviewed_by = current_user.id
    resource.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash(f'"{resource.title}" was approved.', "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/resources/<int:resource_id>/reject", methods=["POST"])
@login_required
@admin_required
def reject_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    resource.status = "rejected"
    resource.reviewed_by = current_user.id
    resource.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash(f'"{resource.title}" was rejected.', "info")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/users")
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=all_users)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You can't deactivate your own account.", "danger")
        return redirect(url_for("admin.users"))

    user.is_active_account = not user.is_active_account
    db.session.commit()

    status = "activated" if user.is_active_account else "deactivated"
    flash(f'"{user.full_name}" was {status}.', "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/verifications")
@login_required
@admin_required
def verifications():
    from app.models import Lecturer
    unverified_alumni = Alumni.query.filter_by(is_verified=False).all()
    unverified_lecturers = Lecturer.query.filter_by(is_verified=False).all()
    return render_template(
        "admin_verifications.html",
        unverified_alumni=unverified_alumni,
        unverified_lecturers=unverified_lecturers,
    )


@admin_bp.route("/alumni/<int:user_id>/verify", methods=["POST"])
@login_required
@admin_required
def verify_alumni(user_id):
    alumni = Alumni.query.get_or_404(user_id)
    alumni.is_verified = True
    db.session.commit()
    flash(f'"{alumni.user.full_name}" has been verified.', "success")
    return redirect(url_for("admin.verifications"))


@admin_bp.route("/lecturer/<int:user_id>/verify", methods=["POST"])
@login_required
@admin_required
def verify_lecturer(user_id):
    from app.models import Lecturer
    lecturer = Lecturer.query.get_or_404(user_id)
    lecturer.is_verified = True
    db.session.commit()
    flash(f'"{lecturer.user.full_name}" has been verified.', "success")
    return redirect(url_for("admin.verifications"))
from app.forms import FacultyForm, DepartmentForm, CourseForm, UniversityForm
from app.models import University, Faculty, Department, Level, Course


@admin_bp.route("/academic", methods=["GET", "POST"])
@login_required
@admin_required
def academic():
    university_form = UniversityForm()
    faculty_form = FacultyForm()
    department_form = DepartmentForm()
    course_form = CourseForm()

    faculty_form.university_id.choices = [(u.id, u.name) for u in University.query.all()]
    department_form.faculty_id.choices = [(f.id, f.name) for f in Faculty.query.all()]
    course_form.department_id.choices = [(d.id, d.name) for d in Department.query.all()]
    course_form.level_id.choices = [(l.id, l.level_number) for l in Level.query.all()]

    if "submit_university" in request.form and university_form.validate_on_submit():
        db.session.add(University(name=university_form.name.data))
        db.session.commit()
        flash("University added.", "success")
        return redirect(url_for("admin.academic"))

    if "submit_faculty" in request.form and faculty_form.validate_on_submit():
        db.session.add(Faculty(name=faculty_form.name.data, university_id=faculty_form.university_id.data))
        db.session.commit()
        flash("Faculty added.", "success")
        return redirect(url_for("admin.academic"))

    if "submit_department" in request.form and department_form.validate_on_submit():
        db.session.add(Department(name=department_form.name.data, faculty_id=department_form.faculty_id.data))
        db.session.commit()
        flash("Department added.", "success")
        return redirect(url_for("admin.academic"))

    if "submit_course" in request.form and course_form.validate_on_submit():
        db.session.add(Course(
            course_code=course_form.course_code.data,
            course_title=course_form.course_title.data,
            department_id=course_form.department_id.data,
            level_id=course_form.level_id.data,
        ))
        db.session.commit()
        flash("Course added.", "success")
        return redirect(url_for("admin.academic"))

    return render_template(
        "admin_academic.html",
        university_form=university_form,
        faculty_form=faculty_form,
        department_form=department_form,
        course_form=course_form,
        universities=University.query.all(),
        faculties=Faculty.query.all(),
        departments=Department.query.all(),
        courses=Course.query.all(),
    )

from app.forms import RecommendationSettingsForm
from app.models import RecommendationSetting


@admin_bp.route("/recommendation-settings", methods=["GET", "POST"])
@login_required
@admin_required
def recommendation_settings():
    settings = RecommendationSetting.get_current()
    form = RecommendationSettingsForm(
        content_weight=str(settings.content_weight),
        collaborative_weight=str(settings.collaborative_weight),
    )

    if form.validate_on_submit():
        try:
            content_w = float(form.content_weight.data)
            collab_w = float(form.collaborative_weight.data)
        except ValueError:
            flash("Weights must be valid numbers.", "danger")
            return redirect(url_for("admin.recommendation_settings"))

        if round(content_w + collab_w, 2) != 1.0:
            flash("Weights must sum to 1.0 (e.g. 0.40 and 0.60).", "danger")
            return redirect(url_for("admin.recommendation_settings"))

        settings.content_weight = content_w
        settings.collaborative_weight = collab_w
        db.session.commit()
        flash("Recommendation weights updated.", "success")
        return redirect(url_for("admin.recommendation_settings"))

    return render_template("admin_recommendation_settings.html", form=form, settings=settings)

@admin_bp.route("/resources")
@login_required
@admin_required
def all_resources():
    faculty_filter = request.args.get("faculty_id", type=int)
    department_filter = request.args.get("department_id", type=int)

    query = Resource.query.filter_by(status="approved")

    if faculty_filter:
        query = query.filter_by(faculty_id=faculty_filter)
    if department_filter:
        query = query.filter_by(department_id=department_filter)

    resources = query.order_by(Resource.faculty_id, Resource.department_id, Resource.created_at.desc()).all()

    all_faculties = Faculty.query.order_by(Faculty.name).all()
    all_departments = Department.query.order_by(Department.name).all()
    if faculty_filter:
        all_departments = Department.query.filter_by(faculty_id=faculty_filter).order_by(Department.name).all()

    return render_template(
        "admin_resources.html",
        resources=resources,
        all_faculties=all_faculties,
        all_departments=all_departments,
        faculty_filter=faculty_filter,
        department_filter=department_filter,
    )