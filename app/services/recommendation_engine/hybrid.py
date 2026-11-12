
from app.models import RecommendationSetting

from app.services.recommendation_engine.content_based import (
    get_content_based_recommendations
)

from app.services.recommendation_engine.collaborative import (
    get_popularity_score
)

from app.services.recommendation_engine.behavioral import (
    get_behavioral_scores
)


def get_hybrid_recommendations(student, limit=10):
    """
    Combines three recommendation components:

    1. Content-based similarity.
    2. Community-driven popularity.
    3. Individual behavioural relevance.

    The existing admin-configured content and collaborative
    weights retain their relative proportions and jointly
    contribute 80% of the final score.

    Individual behaviour contributes the remaining 20%.
    """

    settings = RecommendationSetting.get_current()

    content_weight = float(settings.content_weight)
    collaborative_weight = float(settings.collaborative_weight)

    # Preserve the relative proportions of existing settings.
    total_weight = content_weight + collaborative_weight

    if total_weight > 0:
        effective_content_weight = (
            content_weight / total_weight
        ) * 0.80

        effective_collaborative_weight = (
            collaborative_weight / total_weight
        ) * 0.80
    else:
        # Safe fallback if both configured weights are zero.
        effective_content_weight = 0.32
        effective_collaborative_weight = 0.48

    behavioral_weight = 0.20

    # Get content-based candidate resources.
    content_results = get_content_based_recommendations(
        student,
        limit=50
    )

    if not content_results:
        return []

    # Calculate individual behavioural scores for candidates.
    candidate_resources = [
        resource for resource, score in content_results
    ]

    behavioral_scores = get_behavioral_scores(
        student,
        candidate_resources
    )

    hybrid_scores = []

    for resource, content_score in content_results:

        # Community popularity score.
        popularity_score = get_popularity_score(resource)

        # Individual behavioural relevance.
        behavioral_score = behavioral_scores.get(
            resource.id,
            0.0
        )

        # Combine all three recommendation signals.
        hybrid_score = (
            (float(content_score) * effective_content_weight)
            +
            (float(popularity_score) * effective_collaborative_weight)
            +
            (float(behavioral_score) * behavioral_weight)
        )

        hybrid_scores.append((resource, hybrid_score))

    # Rank resources from highest to lowest score.
    hybrid_scores.sort(
        key=lambda pair: pair[1],
        reverse=True
    )

    return hybrid_scores[:limit]
