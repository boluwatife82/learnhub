from app.extensions import db
from app.models import StudentInterest
from app.services.recommendation_engine.content_based import get_content_based_recommendations


def test_matching_resource_scores_higher_than_unrelated_one(app, sample_data):
    """
    A resource whose title/description closely matches the student's
    interests should score HIGHER than a resource with completely
    unrelated content.
    """
    student = sample_data["student"]

    # Give the student a clear interest that matches the existing resource
    interest = StudentInterest(student_id=student.user_id, interest_tag="Interest: Technology")
    db.session.add(interest)
    db.session.commit()

    from app.models import Resource
    unrelated_resource = Resource(
        title="History of Ancient Rome",
        description="A textbook covering Roman civilization and politics",
        resource_type="textbook",
        file_url="Some Textbook Reference",
        university_id=sample_data["university"].id,
        faculty_id=sample_data["resource"].faculty_id,
        department_id=sample_data["department"].id,
        level_id=sample_data["level_300"].id,
        course_id=sample_data["course"].id,
        uploaded_by=sample_data["admin_user"].id,
        status="approved",
    )
    db.session.add(unrelated_resource)
    db.session.commit()

    results = get_content_based_recommendations(student, limit=10)
    results_dict = {resource.id: score for resource, score in results}

    matching_resource_id = sample_data["resource"].id
    unrelated_resource_id = unrelated_resource.id

    assert matching_resource_id in results_dict
    assert results_dict[matching_resource_id] > results_dict.get(unrelated_resource_id, 0)


def test_no_resources_returns_empty_list(app, sample_data):
    """
    If there are no approved resources at all, the function should
    return an empty list, not crash.
    """
    from app.models import Resource
    Resource.query.delete()
    db.session.commit()

    results = get_content_based_recommendations(sample_data["student"], limit=10)
    assert results == []