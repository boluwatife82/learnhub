from app.models import Resource, Rating, Vote, Download


def get_popularity_score(resource):
    """
    Calculates a community popularity score for one resource, based on
    aggregate ratings, votes, and downloads from ALL students — this is
    the 'Netflix Top 10' style signal: resources proven popular across
    the whole community, not tailored to any one student.

    Weighting rationale:
    - Average rating matters most (quality signal) — scaled 0-1 (rating/5)
    - Votes count next (community endorsement)
    - Downloads count least on their own (someone might download without it being good)
    """
    ratings = Rating.query.filter_by(resource_id=resource.id).all()
    vote_count = Vote.query.filter_by(resource_id=resource.id).count()
    download_count = Download.query.filter_by(resource_id=resource.id).count()

    avg_rating = (sum(r.rating_value for r in ratings) / len(ratings)) if ratings else 0

    # Normalize each signal to a comparable scale, then combine with weights
    rating_component = (avg_rating / 5) * 0.5
    vote_component = min(vote_count / 10, 1.0) * 0.3   # cap at 10 votes = full score
    download_component = min(download_count / 20, 1.0) * 0.2  # cap at 20 downloads = full score

    return rating_component + vote_component + download_component


def get_community_recommendations(department_id=None, exclude_resource_ids=None, limit=10):
    """
    Returns a list of (Resource, score) tuples ranked by community
    popularity. If department_id is given, only resources from that
    department are considered — 'Trending in Your Department' instead
    of platform-wide trending.
    """
    exclude_resource_ids = exclude_resource_ids or set()

    query = Resource.query.filter_by(status="approved")
    if department_id:
        query = query.filter_by(department_id=department_id)

    approved_resources = query.all()
    scored = [
        (r, get_popularity_score(r))
        for r in approved_resources
        if r.id not in exclude_resource_ids
    ]

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]