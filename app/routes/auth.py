from flask import Blueprint, current_app, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.forms import RegisterForm, LoginForm
from app.models import (
    User, Student, Lecturer, Alumni, Department, Level, Faculty, Course,
    StudentCourse, StudentInterest, University,
)
from app.models.academic import Course

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register")
def register_choice():
    return render_template("register_choice.html")



@auth_bp.route("/register/student", methods=["GET", "POST"])
def register_student():
    form = RegisterForm()

    # University choices
    universities = University.query.order_by(University.name).all()
    form.university_id.choices = [
        (u.id, u.name) for u in universities
    ]

    # Read submitted parent selections before WTForms validates choices
    selected_university_id = (
        request.form.get("university_id", type=int)
        if request.method == "POST" else None
    )

    selected_faculty_id = (
        request.form.get("faculty_id", type=int)
        if request.method == "POST" else None
    )

    # Only show faculties belonging to the selected university
    faculties_query = Faculty.query

    if selected_university_id:
        faculties_query = faculties_query.filter_by(
            university_id=selected_university_id
        )

    faculties = faculties_query.order_by(Faculty.name).all()

    form.faculty_id.choices = [
        (f.id, f.name) for f in faculties
    ]

    # Only show departments belonging to the selected faculty
    departments_query = Department.query.join(Faculty)

    if selected_faculty_id and selected_university_id:
        departments_query = departments_query.filter(
            Department.faculty_id == selected_faculty_id,
            Faculty.university_id == selected_university_id
        )
    else:
        departments_query = departments_query.filter(False)

    departments = departments_query.order_by(Department.name).all()

    form.department_id.choices = [
        (d.id, d.name) for d in departments
    ]

    # Academic levels
    levels = Level.query.order_by(Level.level_number).all()

    form.level_id.choices = [
        (level.id, level.level_number) for level in levels
    ]

    if form.validate_on_submit():

        # Verify the complete academic hierarchy again on the server
        faculty = Faculty.query.filter_by(
            id=form.faculty_id.data,
            university_id=form.university_id.data
        ).first()

        department = Department.query.filter_by(
            id=form.department_id.data,
            faculty_id=form.faculty_id.data
        ).first()

        if not faculty or not department:
            flash(
                "Invalid academic selection. Please select your university, faculty and department again.",
                "danger"
            )
            return render_template(
                "register_student.html",
                form=form
            )

        existing_user = User.query.filter_by(
            email=form.email.data
        ).first()

        if existing_user:
            flash(
                "An account with this email already exists.",
                "danger"
            )
            return redirect(url_for("auth.register_student"))

        new_user = User(
            full_name=form.full_name.data,
            email=form.email.data,
            role="student"
        )

        new_user.set_password(form.password.data)

        db.session.add(new_user)
        db.session.flush()

        student = Student(
            user_id=new_user.id,
            matric_number=form.matric_number.data,
            department_id=department.id,
            level_id=form.level_id.data,
            preferred_resource_type=form.preferred_resource_type.data,
        )

        db.session.add(student)
        db.session.flush()

        for tag in form.interest_tags.data:
            db.session.add(
                StudentInterest(
                    student_id=student.user_id,
                    interest_tag=tag
                )
            )

        db.session.commit()

        flash(
            "Registration successful! Please log in.",
            "success"
        )

        return redirect(url_for("auth.login"))

    return render_template(
        "register_student.html",
        form=form
    )


    return render_template("register_student.html", form=form)



@auth_bp.route("/register/lecturer", methods=["GET", "POST"])
def register_lecturer():
    form = RegisterForm()

    # Populate academic dropdown choices
    universities = University.query.order_by(University.name).all()
    faculties = Faculty.query.order_by(Faculty.name).all()
    departments = Department.query.order_by(Department.name).all()

    form.university_id.choices = [
        (u.id, u.name) for u in universities
    ]

    form.faculty_id.choices = [
        (f.id, f.name) for f in faculties
    ]

    form.department_id.choices = [
        (d.id, d.name) for d in departments
    ]

    form.level_id.choices = []

    if form.validate_on_submit():

        # Require verification document
        if not form.verification_document.data:
            flash(
                "Please upload a verification document to register as Lecturer.",
                "danger"
            )
            return render_template("register_lecturer.html", form=form)

        # Check whether email already exists
        existing_user = User.query.filter_by(
            email=form.email.data
        ).first()

        if existing_user:
            flash(
                "An account with this email already exists.",
                "danger"
            )
            return redirect(url_for("auth.register_lecturer"))

        # Validate faculty and department relationship
        faculty = Faculty.query.filter_by(
            id=form.faculty_id.data
        ).first()

        department = Department.query.filter_by(
            id=form.department_id.data
        ).first()

        if not faculty or not department:
            flash("Invalid faculty or department selection.", "danger")
            return render_template("register_lecturer.html", form=form)

        if department.faculty_id != faculty.id:
            flash(
                "The selected department does not belong to the selected faculty.",
                "danger"
            )
            return render_template("register_lecturer.html", form=form)

        # If a university was selected, verify faculty ownership
        if form.university_id.data:
            if faculty.university_id != form.university_id.data:
                flash(
                    "The selected faculty does not belong to the selected university.",
                    "danger"
                )
                return render_template("register_lecturer.html", form=form)

        # Create lecturer account only after validation
        new_user = User(
            full_name=form.full_name.data,
            email=form.email.data,
            role="lecturer"
        )

        new_user.set_password(form.password.data)

        db.session.add(new_user)
        db.session.flush()

        try:
            from app.services.storage.file_storage import save_file

            doc_path = save_file(form.verification_document.data)

            lecturer = Lecturer(
                user_id=new_user.id,
                faculty_id=faculty.id,
                department_id=department.id,
                specialization=form.specialization.data,
                is_verified=False,
                verification_document=doc_path,
            )

            db.session.add(lecturer)
            db.session.commit()

        except Exception:
            db.session.rollback()
            raise

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register_lecturer.html", form=form)



@auth_bp.route("/register/alumni", methods=["GET", "POST"])
def register_alumni():
    form = RegisterForm()

    # Academic fields are not required for alumni registration
    form.university_id.choices = []
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

        from app.services.storage.file_storage import save_file

        try:
            doc_path = save_file(form.verification_document.data)
        except Exception as e:
            current_app.logger.error(f"Alumni document upload failed: {e}")
            flash("We could not upload your document. Please try again.", "danger")
            return render_template("register_alumni.html", form=form)

        new_user = User(
            full_name=form.full_name.data,
            email=form.email.data,
            role="alumni"
        )
        new_user.set_password(form.password.data)

        db.session.add(new_user)
        db.session.flush()

        alumni = Alumni(
            user_id=new_user.id,
            matric_number=form.matric_number.data,
            graduation_year=form.graduation_year.data,
            degree_class=form.degree_class.data,
            is_verified=False,
            verification_document=doc_path,
        )

        db.session.add(alumni)
        db.session.commit()

        flash(
            "Registration successful! Your account will need admin verification before you can vote.",
            "success"
        )
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
        level_id=current_user.student_profile.level_id,
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

    # Initialize dropdown choices
    profile_form.department_id.choices = []
    profile_form.level_id.choices = []
    profile_form.faculty_id.choices = []

    departments = Department.query.order_by(Department.name).all()
    faculties = Faculty.query.order_by(Faculty.name).all()
    levels = Level.query.order_by(Level.level_number).all()

    # STUDENT PROFILE
    if current_user.role == "student" and current_user.student_profile:

        profile_form.department_id.choices = [
            (d.id, d.name) for d in departments
        ]

        profile_form.level_id.choices = [
            (l.id, l.level_number) for l in levels
        ]

        if request.method == "GET":
            profile_form.department_id.data = (
                current_user.student_profile.department_id
            )
            profile_form.level_id.data = (
                current_user.student_profile.level_id
            )
            profile_form.preferred_resource_type.data = (
                current_user.student_profile.preferred_resource_type
            )

    # LECTURER PROFILE
    if current_user.role == "lecturer" and current_user.lecturer_profile:

        profile_form.faculty_id.choices = [
            (f.id, f.name) for f in faculties
        ]

        profile_form.department_id.choices = [
            (d.id, d.name) for d in departments
        ]

        if request.method == "GET":
            profile_form.faculty_id.data = (
                current_user.lecturer_profile.faculty_id
            )
            profile_form.department_id.data = (
                current_user.lecturer_profile.department_id
            )
            profile_form.specialization.data = (
                current_user.lecturer_profile.specialization
            )

    # ALUMNI PROFILE
    if current_user.role == "alumni" and current_user.alumni_profile:
        if request.method == "GET":
            profile_form.degree_class.data = (
                current_user.alumni_profile.degree_class
            )

    # UPDATE PROFILE
    if "submit_profile" in request.form and profile_form.validate_on_submit():

        # Check whether email is already used by another account
        existing_email = User.query.filter(
            User.email == profile_form.email.data,
            User.id != current_user.id
        ).first()

        if existing_email:
            flash("This email address is already in use.", "danger")
            return render_template(
                "settings.html",
                profile_form=profile_form,
                password_form=password_form
            )

        # Validate student academic selections
        if current_user.role == "student" and current_user.student_profile:

            department = Department.query.filter_by(
                id=profile_form.department_id.data
            ).first()

            level = Level.query.filter_by(
                id=profile_form.level_id.data
            ).first()

            if not department or not level:
                flash("Invalid department or level selection.", "danger")
                return render_template(
                    "settings.html",
                    profile_form=profile_form,
                    password_form=password_form
                )

        # Validate lecturer academic selections
        if current_user.role == "lecturer" and current_user.lecturer_profile:

            faculty = Faculty.query.filter_by(
                id=profile_form.faculty_id.data
            ).first()

            department = Department.query.filter_by(
                id=profile_form.department_id.data
            ).first()

            if not faculty or not department:
                flash("Invalid faculty or department selection.", "danger")
                return render_template(
                    "settings.html",
                    profile_form=profile_form,
                    password_form=password_form
                )

            if department.faculty_id != faculty.id:
                flash(
                    "The selected department does not belong to the selected faculty.",
                    "danger"
                )
                return render_template(
                    "settings.html",
                    profile_form=profile_form,
                    password_form=password_form
                )

        # Save common account information
        current_user.full_name = profile_form.full_name.data
        current_user.email = profile_form.email.data

        # Save student information
        if current_user.role == "student" and current_user.student_profile:
            current_user.student_profile.department_id = department.id
            current_user.student_profile.level_id = level.id
            current_user.student_profile.preferred_resource_type = (
                profile_form.preferred_resource_type.data
            )

        # Save lecturer information
        if current_user.role == "lecturer" and current_user.lecturer_profile:
            current_user.lecturer_profile.faculty_id = faculty.id
            current_user.lecturer_profile.department_id = department.id
            current_user.lecturer_profile.specialization = (
                profile_form.specialization.data
            )

        # Save alumni information
        if current_user.role == "alumni" and current_user.alumni_profile:
            current_user.alumni_profile.degree_class = (
                profile_form.degree_class.data
            )

        db.session.commit()

        flash("Profile updated successfully.", "success")
        return redirect(url_for("auth.settings"))

    # CHANGE PASSWORD
    if "submit_password" in request.form and password_form.validate_on_submit():

        if not current_user.check_password(
            password_form.current_password.data
        ):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("auth.settings"))

        current_user.set_password(password_form.new_password.data)
        db.session.commit()

        flash("Password changed successfully.", "success")
        return redirect(url_for("auth.settings"))

    return render_template(
        "settings.html",
        profile_form=profile_form,
        password_form=password_form
    )


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

    # ==========================================
# ACADEMIC DROPDOWN API
# ==========================================

@auth_bp.route("/api/universities/<int:university_id>/faculties")
def api_university_faculties(university_id):

    university = University.query.get_or_404(university_id)

    faculties = Faculty.query.filter_by(
        university_id=university.id
    ).order_by(Faculty.name).all()

    return jsonify([
        {
            "id": faculty.id,
            "name": faculty.name
        }
        for faculty in faculties
    ])


@auth_bp.route("/api/faculties/<int:faculty_id>/departments")
def api_faculty_departments(faculty_id):

    faculty = Faculty.query.get_or_404(faculty_id)

    departments = Department.query.filter_by(
        faculty_id=faculty.id
    ).order_by(Department.name).all()

    return jsonify([
        {
            "id": department.id,
            "name": department.name
        }
        for department in departments
    ])



@auth_bp.route("/api/departments/<int:department_id>/courses")
def api_department_courses(department_id):
    level_id = request.args.get("level_id", type=int)

    department = Department.query.get_or_404(department_id)

    if not level_id:
        return jsonify([])

    courses = Course.query.filter_by(
        department_id=department.id,
        level_id=level_id
    ).order_by(Course.course_code).all()

    return jsonify([
        {
            "id": course.id,
            "name": f"{course.course_code} - {course.course_title}"
        }
        for course in courses
    ])
