from app.extensions import db
from app.models import RecommendationSetting, StudentInterest, Rating
from app.services.recommendation_engine.hybrid import get_hybrid_recommendations


def test_hybrid_score_uses_configured_weights(app, sample_data):
    """
    The Hybrid Score should genuinely combine Content-Based and
    Community popularity using the weights stored in
    RecommendationSetting — not hardcoded values.
    """
    student = sample_data["student"]
    resource = sample_data["resource"]

    # Give the student an interest matching the resource
    db.session.add(StudentInterest(student_id=student.user_id, interest_tag="Interest: Technology"))

    # Give the resource some ratings, so it has a non-zero popularity score too
    db.session.add(Rating(resource_id=resource.id, user_id=sample_data["admin_user"].id, rating_value=5))
    db.session.commit()

    # Set explicit, known weights: 70% content, 30% collaborative
    settings = RecommendationSetting.get_current()
    settings.content_weight = 0.70
    settings.collaborative_weight = 0.30
    db.session.commit()

    results_70_30 = get_hybrid_recommendations(student, limit=10)
    score_70_30 = dict(results_70_30).get(resource)

    # Now flip the weights: 30% content, 70% collaborative
    settings.content_weight = 0.30
    settings.collaborative_weight = 0.70
    db.session.commit()

    results_30_70 = get_hybrid_recommendations(student, limit=10)
    score_30_70 = dict(results_30_70).get(resource)

    # The two scores should be DIFFERENT — proving the weights genuinely
    # change the outcome, rather than the function ignoring them.
    assert score_70_30 is not None
    assert score_30_70 is not None
    assert score_70_30 != score_30_70


def test_hybrid_weights_always_reflect_database_not_hardcoded_defaults(app, sample_data):
    """
    Confirms RecommendationSetting.get_current() actually returns
    whatever is stored, not a hardcoded 0.40/0.60 every time.
    """
    settings = RecommendationSetting.get_current()
    settings.content_weight = 0.55
    settings.collaborative_weight = 0.45
    db.session.commit()

    refetched = RecommendationSetting.get_current()
    assert float(refetched.content_weight) == 0.55
    assert float(refetched.collaborative_weight) == 0.45