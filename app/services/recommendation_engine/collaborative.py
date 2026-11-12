
from app.models import Resource, Rating, Vote, Download


def get_popularity_score(resource):
    """
    Calculates a community popularity score using ratings,
    votes and downloads.
    """
    ratings = Rating.query.filter_by(resource_id=resource.id).all()
    vote_count = Vote.query.filter_by(resource_id=resource.id).count()
    download_count = Download.query.filter_by(resource_id=resource.id).count()

    avg_rating = (
        sum(r.rating_value for r in ratings) / len(ratings)
        if ratings else 0
    )

    rating_component = (avg_rating / 5) * 0.5
    vote_component = min(vote_count / 10, 1.0) * 0.3
    download_component = min(download_count / 20, 1.0) * 0.2

    return (
        rating_component
        + vote_component
        + download_component
    )


def get_community_recommendations(
    department_id=None,
    level_id=None,
    exclude_resource_ids=None,
    limit=10
):
    """
    Returns approved resources ranked by community popularity,
    restricted to the supplied department and academic level.
    """
    exclude_resource_ids = exclude_resource_ids or set()

    query = Resource.query.filter_by(status="approved")

    if department_id is not None:
        query = query.filter_by(department_id=department_id)

    if level_id is not None:
        query = query.filter_by(level_id=level_id)

    approved_resources = query.all()

    scored = [
        (resource, get_popularity_score(resource))
        for resource in approved_resources
        if resource.id not in exclude_resource_ids
    ]

    scored.sort(key=lambda pair: pair[1], reverse=True)

    return scored[:limit]
