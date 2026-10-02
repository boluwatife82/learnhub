from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.forms import ResourceUploadForm
from app.models import University, Faculty, Department, Level, Course, Resource, Rating, Vote, Download, UserInteraction, Bookmark
from app.models.interaction import Bookmark
from app.services.storage.file_storage import save_file

resources_bp = Blueprint("resources", __name__)


@resources_bp.route("/resources/upload", methods=["GET", "POST"])
@login_required
def upload():
    form = ResourceUploadForm()

    form.university_id.choices = [(u.id, u.name) for u in University.query.all()]
    form.faculty_id.choices = [(f.id, f.name) for f in Faculty.query.all()]
    form.department_id.choices = [(d.id, d.name) for d in Department.query.all()]
    form.level_id.choices = [(l.id, l.level_number) for l in Level.query.all()]
    form.course_id.choices = [(c.id, f"{c.course_code} - {c.course_title}") for c in Course.query.all()]

    if form.validate_on_submit():
        if form.resource_type.data == "pdf":
            if not form.file.data:
                flash("Please attach a PDF file.", "danger")
                return render_template("upload_resource.html", form=form)
            file_url = save_file(form.file.data)
        else:
            if not form.external_link.data:
                flash("Please provide a link/reference.", "danger")
                return render_template("upload_resource.html", form=form)
            file_url = form.external_link.data

        new_resource = Resource(
            title=form.title.data,
            description=form.description.data,
            resource_type=form.resource_type.data,
            file_url=file_url,
            university_id=form.university_id.data,
            faculty_id=form.faculty_id.data,
            department_id=form.department_id.data,
            level_id=form.level_id.data,
            course_id=form.course_id.data,
            uploaded_by=current_user.id,
            status="pending",
        )
        db.session.add(new_resource)
        db.session.commit()

        flash("Resource submitted for admin review.", "success")
        return redirect(url_for("auth.dashboard"))

    return render_template("upload_resource.html", form=form)


@resources_bp.route("/resources/browse")
@login_required
def browse():
    resource_type = request.args.get("type")

    query = Resource.query.filter_by(status="approved")

    if current_user.role == "student" and current_user.student_profile:
        query = query.filter_by(department_id=current_user.student_profile.department_id)

    if resource_type in ["pdf", "youtube", "textbook"]:
        query = query.filter_by(resource_type=resource_type)

    all_resources = query.order_by(Resource.created_at.desc()).all()

    return render_template("browse_resources.html", resources=all_resources, active_filter=resource_type)


@resources_bp.route("/resources/<int:resource_id>")
@login_required
def view(resource_id):
    resource = Resource.query.get_or_404(resource_id)

    if resource.status != "approved" and resource.uploaded_by != current_user.id:
        flash("This resource is not available.", "danger")
        return redirect(url_for("resources.browse"))

    db.session.add(UserInteraction(
        user_id=current_user.id,
        resource_id=resource.id,
        interaction_type="view",
        weight=1.0,
    ))
    db.session.commit()

    user_rating = Rating.query.filter_by(resource_id=resource.id, user_id=current_user.id).first()
    user_has_voted = Vote.query.filter_by(resource_id=resource.id, user_id=current_user.id).first() is not None
    is_bookmarked = Bookmark.query.filter_by(resource_id=resource.id, user_id=current_user.id).first() is not None
    average_rating = db.session.query(db.func.avg(Rating.rating_value)).filter_by(resource_id=resource.id).scalar()

    return render_template(
        "resource_detail.html",
        resource=resource,
        user_rating=user_rating,
        user_has_voted=user_has_voted,
        is_bookmarked=is_bookmarked,
        average_rating=round(average_rating, 1) if average_rating else None,
    )

@resources_bp.route("/resources/<int:resource_id>/download")
@login_required
def download(resource_id):
    resource = Resource.query.get_or_404(resource_id)

    if resource.status != "approved":
        flash("This resource is not available for download.", "danger")
        return redirect(url_for("resources.browse"))

    db.session.add(Download(resource_id=resource.id, user_id=current_user.id))
    db.session.add(UserInteraction(
        user_id=current_user.id,
        resource_id=resource.id,
        interaction_type="download",
        weight=2.0,
    ))
    db.session.commit()

    return redirect(resource.file_url)


@resources_bp.route("/resources/<int:resource_id>/vote", methods=["POST"])
@login_required
def vote(resource_id):
    resource = Resource.query.get_or_404(resource_id)

    if current_user.role == "alumni":
        if not current_user.alumni_profile or not current_user.alumni_profile.is_verified:
            flash("Your alumni account must be verified by an admin before you can vote.", "danger")
            return redirect(url_for("resources.view", resource_id=resource.id))

    if current_user.role == "student" and current_user.student_profile:
        student_level = current_user.student_profile.level.level_number
        resource_level = resource.level.level_number

        if resource_level >= student_level:
            flash("You can only vote on resources from levels you've already completed.", "danger")
            return redirect(url_for("resources.view", resource_id=resource.id))

    already_voted = Vote.query.filter_by(resource_id=resource.id, user_id=current_user.id).first()
    if already_voted:
        flash("You've already voted on this resource.", "info")
        return redirect(url_for("resources.view", resource_id=resource.id))

    db.session.add(Vote(resource_id=resource.id, user_id=current_user.id))
    db.session.add(UserInteraction(
        user_id=current_user.id,
        resource_id=resource.id,
        interaction_type="vote",
        weight=1.5,
    ))
    db.session.commit()

    flash("Thanks for voting!", "success")
    return redirect(url_for("resources.view", resource_id=resource.id))


@resources_bp.route("/resources/<int:resource_id>/rate", methods=["POST"])
@login_required
def rate(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    rating_value = int(request.form.get("rating_value", 0))

    if rating_value < 1 or rating_value > 5:
        flash("Invalid rating.", "danger")
        return redirect(url_for("resources.view", resource_id=resource.id))

    existing = Rating.query.filter_by(resource_id=resource.id, user_id=current_user.id).first()
    if existing:
        existing.rating_value = rating_value
    else:
        db.session.add(Rating(resource_id=resource.id, user_id=current_user.id, rating_value=rating_value))
        db.session.add(UserInteraction(
            user_id=current_user.id,
            resource_id=resource.id,
            interaction_type="rate",
            weight=1.0,
        ))

    db.session.commit()
    flash("Rating submitted.", "success")
    return redirect(url_for("resources.view", resource_id=resource.id))


@resources_bp.route("/resources/my-downloads")
@login_required
def my_downloads():
    downloads = (
        Download.query.filter_by(user_id=current_user.id)
        .order_by(Download.downloaded_at.desc())
        .all()
    )
    return render_template("my_downloads.html", downloads=downloads)


@resources_bp.route("/resources/my-ratings")
@login_required
def my_ratings():
    ratings = (
        Rating.query.filter_by(user_id=current_user.id)
        .order_by(Rating.created_at.desc())
        .all()
    )
    return render_template("my_ratings.html", ratings=ratings)


@resources_bp.route("/resources/my-votes")
@login_required
def my_votes():
    votes = (
        Vote.query.filter_by(user_id=current_user.id)
        .order_by(Vote.created_at.desc())
        .all()
    )
    return render_template("my_votes.html", votes=votes)


@resources_bp.route("/resources/search")
@login_required
def search():
    query_text = request.args.get("q", "").strip()

    results = []
    if query_text:
        search_pattern = f"%{query_text}%"
        results = Resource.query.filter(
            Resource.status == "approved",
            db.or_(
                Resource.title.ilike(search_pattern),
                Resource.description.ilike(search_pattern),
            )
        ).order_by(Resource.created_at.desc()).all()

    return render_template("search_results.html", resources=results, query_text=query_text)


@resources_bp.route("/resources/<int:resource_id>/bookmark", methods=["POST"])
@login_required
def bookmark(resource_id):
    resource = Resource.query.get_or_404(resource_id)

    existing = Bookmark.query.filter_by(resource_id=resource.id, user_id=current_user.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash("Removed from your library.", "info")
    else:
        db.session.add( Bookmark(resource_id=resource.id, user_id=current_user.id))
        db.session.commit()
        flash("Saved to your library.", "success")

    return redirect(url_for("resources.view", resource_id=resource.id))

@resources_bp.route("/resources/my-library")
@login_required
def my_library():
    bookmarks = (
        Bookmark.query.filter_by(user_id=current_user.id)
        .order_by(Bookmark.created_at.desc())
        .all()
    )
    download_count = Download.query.filter_by(user_id=current_user.id).count()
    rating_count = Rating.query.filter_by(user_id=current_user.id).count()

    recent_downloads = (
        Download.query.filter_by(user_id=current_user.id)
        .order_by(Download.downloaded_at.desc())
        .limit(5)
        .all()
    )
    recent_ratings = (
        Rating.query.filter_by(user_id=current_user.id)
        .order_by(Rating.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "my_library.html",
        bookmarks=bookmarks,
        download_count=download_count,
        rating_count=rating_count,
        recent_downloads=recent_downloads,
        recent_ratings=recent_ratings,
    )