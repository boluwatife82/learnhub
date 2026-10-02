from app.models import Resource, RecommendationSetting
from app.services.recommendation_engine.content_based import get_content_based_recommendations
from app.services.recommendation_engine.collaborative import get_popularity_score


def get_hybrid_recommendations(student, limit=10):
    """
    Combines Content-Based Filtering (personalized to the student's profile)
    with Community-Driven popularity (aggregate ratings/votes/downloads),
    using the admin-configured weights from RecommendationSetting.

    Hybrid Score = (Content Score x Content Weight) + (Popularity Score x Collaborative Weight)
    """
    settings = RecommendationSetting.get_current()
    content_weight = float(settings.content_weight)
    collaborative_weight = float(settings.collaborative_weight)

    # Content-based gives us (resource, content_score) pairs, already ranked
    content_results = get_content_based_recommendations(student, limit=50)

    if not content_results:
        return []

    hybrid_scores = []
    for resource, content_score in content_results:
        popularity_score = get_popularity_score(resource)

        hybrid_score = (content_score * content_weight) + (popularity_score * collaborative_weight)
        hybrid_scores.append((resource, hybrid_score))

    hybrid_scores.sort(key=lambda pair: pair[1], reverse=True)
    return hybrid_scores[:limit]