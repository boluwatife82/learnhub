
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models import (
    Resource,
    UserInteraction,
    Rating,
    Vote,
    Download,
    Bookmark
)
from app.services.recommendation_engine.content_based import build_resource_text


def get_student_interaction_profile(student):
    """
    Builds a behavioural profile from the student's existing interactions.

    Positive signals:
    - Views
    - Downloads
    - Bookmarks
    - Votes
    - Ratings of 4 or 5

    Negative signals:
    - Ratings of 1 or 2

    A rating of 3 is treated as neutral.

    Dedicated tables are used for downloads, votes and ratings
    to avoid counting their mirrored UserInteraction records twice.
    """

    positive_resources = defaultdict(float)
    negative_resources = defaultdict(float)

    # Views: weak interest signal.
    views = UserInteraction.query.filter_by(
        user_id=student.user_id,
        interaction_type="view"
    ).all()

    view_counts = defaultdict(int)

    for interaction in views:
        view_counts[interaction.resource_id] += 1

    for resource_id, count in view_counts.items():
        positive_resources[resource_id] += min(count, 3) * 0.2

    # Downloads: stronger interest signal.
    downloads = Download.query.filter_by(
        user_id=student.user_id
    ).all()

    download_counts = defaultdict(int)

    for download in downloads:
        download_counts[download.resource_id] += 1

    for resource_id, count in download_counts.items():
        positive_resources[resource_id] += min(count, 2) * 0.7

    # Bookmarks: strong indication of saved interest.
    bookmarks = Bookmark.query.filter_by(
        user_id=student.user_id
    ).all()

    for bookmark in bookmarks:
        positive_resources[bookmark.resource_id] += 0.8

    # Votes: positive community feedback from this student.
    votes = Vote.query.filter_by(
        user_id=student.user_id
    ).all()

    for vote in votes:
        positive_resources[vote.resource_id] += 0.6

    # Ratings: positive and negative feedback.
    ratings = Rating.query.filter_by(
        user_id=student.user_id
    ).all()

    for rating in ratings:
        if rating.rating_value >= 4:
            positive_resources[rating.resource_id] += (
                rating.rating_value / 5
            )

        elif rating.rating_value <= 2:
            negative_resources[rating.resource_id] += (
                (3 - rating.rating_value) / 2
            )

    return positive_resources, negative_resources


def normalize_behavioral_scores(scores):
    """
    Applies Min-Max Normalisation to behavioural scores.

    The resulting scores range from 0 to 1.

    If all candidates have identical scores, returns zero
    for every candidate to avoid manufacturing differences.
    """

    if not scores:
        return {}

    minimum = min(scores.values())
    maximum = max(scores.values())

    if maximum == minimum:
        return {
            resource_id: 0.0
            for resource_id in scores
        }

    normalized_scores = {}

    for resource_id, score in scores.items():
        normalized_scores[resource_id] = (
            (score - minimum) / (maximum - minimum)
        )

    return normalized_scores


def get_behavioral_scores(student, resources):
    """
    Measures how closely candidate resources match the student's
    previous positive and negative resource interactions.

    Returns:
        {resource_id: normalized_behavioural_score}

    Scores range from 0 to 1.
    """

    if not resources:
        return {}

    positive_history, negative_history = (
        get_student_interaction_profile(student)
    )

    history_ids = set(positive_history) | set(negative_history)

    if not history_ids:
        return {resource.id: 0.0 for resource in resources}

    history_resources = Resource.query.filter(
        Resource.id.in_(history_ids),
        Resource.status == "approved"
    ).all()

    resource_lookup = {
        resource.id: resource
        for resource in history_resources
    }

    positive_items = [
        (resource_lookup[resource_id], weight)
        for resource_id, weight in positive_history.items()
        if resource_id in resource_lookup
    ]

    negative_items = [
        (resource_lookup[resource_id], weight)
        for resource_id, weight in negative_history.items()
        if resource_id in resource_lookup
    ]

    if not positive_items and not negative_items:
        return {resource.id: 0.0 for resource in resources}

    # Build one TF-IDF space for history and candidate resources.
    history_texts = [
        build_resource_text(resource)
        for resource, _ in positive_items + negative_items
    ]

    candidate_texts = [
        build_resource_text(resource)
        for resource in resources
    ]

    all_texts = history_texts + candidate_texts

    if not any(text.strip() for text in all_texts):
        return {resource.id: 0.0 for resource in resources}

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform(all_texts)
    except ValueError:
        # Handles cases where all words are removed by the vectorizer.
        return {resource.id: 0.0 for resource in resources}

    history_vectors = matrix[:len(history_texts)]
    candidate_vectors = matrix[len(history_texts):]

    similarities = cosine_similarity(
        candidate_vectors,
        history_vectors
    )

    positive_count = len(positive_items)
    scores = {}

    for index, resource in enumerate(resources):
        positive_score = 0.0
        negative_score = 0.0

        # Weighted similarity to positively interacted resources.
        for history_index, (_, weight) in enumerate(positive_items):
            positive_score += (
                similarities[index][history_index] * weight
            )

        if positive_items:
            positive_score /= sum(
                weight for _, weight in positive_items
            )

        # Weighted similarity to negatively rated resources.
        for history_index, (_, weight) in enumerate(negative_items):
            negative_index = positive_count + history_index

            negative_score += (
                similarities[index][negative_index] * weight
            )

        if negative_items:
            negative_score /= sum(
                weight for _, weight in negative_items
            )

        # Negative feedback reduces behavioural relevance.
        behavioral_score = max(
            0.0,
            min(1.0, positive_score - (0.5 * negative_score))
        )

        scores[resource.id] = behavioral_score

    # Normalise scores across the current candidate resources.
    return normalize_behavioral_scores(scores)
