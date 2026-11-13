
from app.models import RecommendationSetting

from app.services.recommendation_engine.content_based import (
    get_content_based_recommendations
)

from app.services.recommendation_engine.collaborative import (
    get_popularity_score
)

from app.services.recommendation_engine.behavioral import (
    get_behavioral_scores,
    get_student_interaction_profile
)


def get_hybrid_recommendations(student, limit=10):

    settings = RecommendationSetting.get_current()

    content_weight = float(settings.content_weight)
    collaborative_weight = float(settings.collaborative_weight)

    total_weight = content_weight + collaborative_weight

    if total_weight > 0:
        content_ratio = content_weight / total_weight
        popularity_ratio = collaborative_weight / total_weight
    else:
        content_ratio = 0.4
        popularity_ratio = 0.6

    # Measure the student's existing interaction history.
    positive_history, negative_history = (
        get_student_interaction_profile(student)
    )

    activity = (
        sum(positive_history.values())
        + sum(negative_history.values())
    )

    # Gradually introduce behavioural personalisation.
    progress = min(activity / 5.0, 1.0)

    behavioral_weight = 0.20 * progress

    # Start with content-based relevance and community popularity.
    content_effective_weight = (
        0.80 - (0.48 * progress)
    )

    popularity_effective_weight = (
        0.20 + (0.28 * progress)
    )

    # Get a wider pool of academically eligible resources.
    content_results = get_content_based_recommendations(
        student,
        limit=500
    )

    if not content_results:
        return []

    candidate_resources = [
        resource for resource, score in content_results
    ]

    behavioral_scores = get_behavioral_scores(
        student,
        candidate_resources
    )

    hybrid_scores = []

    for resource, content_score in content_results:

        popularity_score = get_popularity_score(resource)

        behavioral_score = behavioral_scores.get(
            resource.id,
            0.0
        )

        final_score = (
            float(content_score) * content_effective_weight
            + float(popularity_score) * popularity_effective_weight
            + float(behavioral_score) * behavioral_weight
        )

        hybrid_scores.append((resource, final_score))

    hybrid_scores.sort(
        key=lambda pair: pair[1],
        reverse=True
    )

    return hybrid_scores[:limit]
