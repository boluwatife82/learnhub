from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.forms import RegisterForm, LoginForm
from app.models import (
    User, Student, Lecturer, Alumni, Department, Level, Faculty, Course,
    StudentCourse, StudentInterest,
)
from app.models.academic import Course

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register")
def register_choice():
    return render_template("register_choice.html")


@auth_bp.route("/register/student", methods=["GET", "POST"])
def register_student():
    form = RegisterForm()
    form.department_id.choices = [(d.id, d.name) for d in Department.query.all()]
    form.level_id.choices = [(l.id, l.level_number) for l in Level.query.all()]
    form.faculty_id.choices = [(f.id, f.name) for f in Faculty.query.all()]

    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("An account with this email already exists.", "danger")
            return redirect(url_for("auth.register_student"))

        new_user = User(full_name=form.full_name.data, email=form.email.data, role="student")
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.flush()

        student = Student(
            user_id=new_user.id,
            matric_number=form.matric_number.data,
            department_id=form.department_id.data,
            level_id=form.level_id.data,
            preferred_resource_type=form.preferred_resource_type.data,
        )
        db.session.add(student)
        db.session.flush()

        for tag in form.interest_tags.data:
            db.session.add(StudentInterest(student_id=student.user_id, interest_tag=tag))

        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register_student.html", form=form)


@auth_bp.route("/register/lecturer", methods=["GET", "POST"])
def register_lecturer():
    form = RegisterForm()
    form.department_id.choices = [(d.id, d.name) for d in Department.query.all()]
    form.faculty_id.choices = [(f.id, f.name) for f in Faculty.query.all()]

    form.level_id.choices = []

    if form.validate_on_submit():
        if not form.verification_document.data:
            flash("Please upload a verification document to register as Lecturer.", "danger")
            return render_template("register_lecturer.html", form=form)

        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("An account with this email already exists.", "danger")
            return redirect(url_for("auth.register_lecturer"))

        new_user = User(full_name=form.full_name.data, email=form.email.data, role="lecturer")
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.flush()
        doc_path = None
        if form.verification_document.data:
            from app.services.storage.file_storage import save_file
            doc_path = save_file(form.verification_document.data)

        lecturer = Lecturer(
            user_id=new_user.id,
            faculty_id=form.faculty_id.data,
            department_id=form.department_id.data,
            specialization=form.specialization.data,
            is_verified=False,
            verification_document=doc_path,
        )

        db.session.add(lecturer)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register_lecturer.html", form=form)
    


@auth_bp.route("/register/alumni", methods=["GET", "POST"])
def register_alumni():
    form = RegisterForm()
    form.department_id.choices = []
    form.faculty_id.choices = []
    form.level_id.choices = []

    if form.validate_on_submit():
        if not form.verification_document.data:
            flash("Please upload a verification document to register as Alumni.", "danger")
            return render_template("register_alumni.html", form=form)

        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("An account with this email already exists.", "danger")
            return redirect(url_for("auth.register_alumni"))

        new_user = User(full_name=form.full_name.data, email=form.email.data, role="alumni")
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.flush()

        alumni = Alumni(
            user_id=new_user.id,
            matric_number=form.matric_number.data,
            graduation_year=form.graduation_year.data,
            degree_class=form.degree_class.data,
            is_verified=False,
        )
        db.session.add(alumni)
        db.session.commit()

        flash("Registration successful! Your account will need admin verification before you can vote.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register_alumni.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.check_password(form.password.data):
            if not user.is_active_account:
                flash("This account has been deactivated. Contact an administrator.", "danger")
                return redirect(url_for("auth.login"))

            login_user(user, remember=(form.remember_me.data == "yes"))
            flash("Logged in successfully.", "success")

            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("auth.dashboard"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html", form=form)


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    from app.models import Resource, Download, Rating, Vote

    if current_user.role == "admin":
        from flask import redirect, url_for as _url_for
        return redirect(url_for("admin.dashboard"))

    if current_user.role == "alumni":
        my_uploads = Resource.query.filter_by(uploaded_by=current_user.id).order_by(Resource.created_at.desc()).all()
        my_votes = Vote.query.filter_by(user_id=current_user.id).all()
        return render_template(
            "dashboard_alumni.html",
            my_uploads=my_uploads,
            upload_count=len(my_uploads),
            vote_count=len(my_votes),
            is_verified=current_user.alumni_profile.is_verified if current_user.alumni_profile else False,
        )

    if current_user.role == "lecturer":
        from app.models import UserInteraction

        my_uploads = Resource.query.filter_by(uploaded_by=current_user.id).order_by(Resource.created_at.desc()).all()
        pending_count = len([r for r in my_uploads if r.status == "pending"])
        approved_count = len([r for r in my_uploads if r.status == "approved"])

        total_views = 0
        total_downloads = 0
        total_ratings = 0
        rating_sum = 0

        resource_stats = {}
        for resource in my_uploads:
            views = UserInteraction.query.filter_by(resource_id=resource.id, interaction_type="view").count()
            downloads = len(resource.downloads)
            ratings = resource.ratings
            avg = round(sum(r.rating_value for r in ratings) / len(ratings), 1) if ratings else None

            resource_stats[resource.id] = {"views": views, "downloads": downloads, "avg_rating": avg}
            total_views += views
            total_downloads += downloads
            total_ratings += len(ratings)
            rating_sum += sum(r.rating_value for r in ratings)

        overall_avg_rating = round(rating_sum / total_ratings, 1) if total_ratings else None

        return render_template(
            "dashboard_lecturer.html",
            my_uploads=my_uploads,
            upload_count=len(my_uploads),
            pending_count=pending_count,
            approved_count=approved_count,
            total_views=total_views,
            total_downloads=total_downloads,
            total_ratings=total_ratings,
            overall_avg_rating=overall_avg_rating,
            resource_stats=resource_stats,
        )
    # Default: student dashboard
    recommendations = []
    community_recs = []
    total_resources = 0
    download_count = 0
    rating_count = 0

    if current_user.role == "student" and current_user.student_profile:
        from app.services.recommendation_engine.hybrid import get_hybrid_recommendations
        from app.services.recommendation_engine.collaborative import get_community_recommendations

        recommendations = get_hybrid_recommendations(current_user.student_profile, limit=6)
        community_recs = get_community_recommendations(
            department_id=current_user.student_profile.department_id,
            limit=6
        )

        total_resources = Resource.query.filter_by(
            status="approved",
            department_id=current_user.student_profile.department_id
        ).count()

    download_count = Download.query.filter_by(user_id=current_user.id).count()
    rating_count = Rating.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "dashboard.html",
        recommendations=recommendations,
        community_recs=community_recs,
        total_resources=total_resources,
        download_count=download_count,
        rating_count=rating_count,
    )

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/recommended")
@login_required
def recommended():
    recommendations = []

    if current_user.role == "student" and current_user.student_profile:
        from app.services.recommendation_engine.hybrid import get_hybrid_recommendations
        recommendations = get_hybrid_recommendations(current_user.student_profile, limit=20)

    return render_template("recommended.html", recommendations=recommendations)


@auth_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    from app.forms import ProfileForm, ChangePasswordForm

    profile_form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()

    # Default empty choices so validation never crashes on fields not used by this role
    profile_form.department_id.choices = []
    profile_form.level_id.choices = []
    profile_form.faculty_id.choices = []

    if current_user.role == "student" and current_user.student_profile:
        profile_form.department_id.choices = [(d.id, d.name) for d in Department.query.all()]
        profile_form.level_id.choices = [(l.id, l.level_number) for l in Level.query.all()]
        if request.method == "GET":
            profile_form.department_id.data = current_user.student_profile.department_id
            profile_form.level_id.data = current_user.student_profile.level_id
            profile_form.preferred_resource_type.data = current_user.student_profile.preferred_resource_type

    if current_user.role == "lecturer" and current_user.lecturer_profile:
        profile_form.faculty_id.choices = [(f.id, f.name) for f in Faculty.query.all()]
        profile_form.department_id.choices = [(d.id, d.name) for d in Department.query.all()]
        if request.method == "GET":
            profile_form.faculty_id.data = current_user.lecturer_profile.faculty_id
            profile_form.department_id.data = current_user.lecturer_profile.department_id
            profile_form.specialization.data = current_user.lecturer_profile.specialization

    if current_user.role == "alumni" and current_user.alumni_profile:
        if request.method == "GET":
            profile_form.degree_class.data = current_user.alumni_profile.degree_class

    if "submit_profile" in request.form and profile_form.validate_on_submit():
        current_user.full_name = profile_form.full_name.data
        current_user.email = profile_form.email.data

        if current_user.role == "student" and current_user.student_profile:
            current_user.student_profile.department_id = profile_form.department_id.data
            current_user.student_profile.level_id = profile_form.level_id.data
            current_user.student_profile.preferred_resource_type = profile_form.preferred_resource_type.data

        if current_user.role == "lecturer" and current_user.lecturer_profile:
            current_user.lecturer_profile.faculty_id = profile_form.faculty_id.data
            current_user.lecturer_profile.department_id = profile_form.department_id.data
            current_user.lecturer_profile.specialization = profile_form.specialization.data

        if current_user.role == "alumni" and current_user.alumni_profile:
            current_user.alumni_profile.degree_class = profile_form.degree_class.data

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("auth.settings"))

    if "submit_password" in request.form and password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("auth.settings"))

        current_user.set_password(password_form.new_password.data)
        db.session.commit()
        flash("Password changed successfully.", "success")
        return redirect(url_for("auth.settings"))

    return render_template("settings.html", profile_form=profile_form, password_form=password_form)


@auth_bp.route("/help")
@login_required
def help_page():
    return render_template("help.html")

@auth_bp.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    from app.models import Resource, University, Student

    total_resources = Resource.query.filter_by(status="approved").count()
    total_universities = University.query.count()
    total_students = Student.query.count()

    recent_resources = (
        Resource.query.filter_by(status="approved")
        .order_by(Resource.created_at.desc())
        .limit(6)
        .all()
    )

    return render_template(
        "landing.html",
        total_resources=total_resources,
        total_universities=total_universities,
        total_students=total_students,
        recent_resources=recent_resources,
    )