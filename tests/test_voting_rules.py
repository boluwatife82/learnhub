from app.extensions import db
from app.models import Vote, Resource


def test_student_cannot_vote_on_resource_at_own_level(client, sample_data, app):
    """
    A 300 Level student should NOT be able to vote on a resource
    that is also at 300 Level (their own level).
    """
    student_user = sample_data["student_user"]
    resource = sample_data["resource"]  # this resource is at level_300

    with client.session_transaction() as session:
        session["_user_id"] = str(student_user.id)
        session["_fresh"] = True

    response = client.post(f"/resources/{resource.id}/vote", follow_redirects=True)

    vote_exists = Vote.query.filter_by(resource_id=resource.id, user_id=student_user.id).first()
    assert vote_exists is None


def test_student_can_vote_on_resource_below_own_level(client, sample_data, app):
    """
    A 300 Level student SHOULD be able to vote on a resource
    from a level they've already completed (e.g. 100 Level).
    """
    student_user = sample_data["student_user"]
    level_100 = sample_data["level_100"]

    lower_level_resource = Resource(
        title="Intro Notes",
        description="Basic introductory material",
        resource_type="pdf",
        file_url="uploads/intro.pdf",
        university_id=sample_data["university"].id,
        faculty_id=sample_data["resource"].faculty_id,
        department_id=sample_data["department"].id,
        level_id=level_100.id,
        course_id=sample_data["course"].id,
        uploaded_by=sample_data["admin_user"].id,
        status="approved",
    )
    db.session.add(lower_level_resource)
    db.session.commit()

    with client.session_transaction() as session:
        session["_user_id"] = str(student_user.id)
        session["_fresh"] = True

    response = client.post(f"/resources/{lower_level_resource.id}/vote", follow_redirects=True)

    vote_exists = Vote.query.filter_by(resource_id=lower_level_resource.id, user_id=student_user.id).first()
    assert vote_exists is not None