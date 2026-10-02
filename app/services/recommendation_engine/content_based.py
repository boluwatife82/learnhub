from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models import Resource, StudentInterest


def build_student_profile_text(student):
    """
    Combines everything we know about a student into one text string,
    so it can be compared against resource text using TF-IDF.
    """
    parts = []

    if student.department:
        parts.append(student.department.name)

    if student.preferred_resource_type:
        parts.append(student.preferred_resource_type)

    interests = StudentInterest.query.filter_by(student_id=student.user_id).all()
    for i in interests:
        # strip the "Goal: " / "Style: " / "Format: " / "Interest: " prefix, keep the keyword itself
        tag_text = i.interest_tag.split(":")[-1].strip()
        parts.append(tag_text)

    return " ".join(parts)


def build_resource_text(resource):
    """
    Combines a resource's metadata into one text string for comparison.
    """
    parts = [
        resource.title or "",
        resource.description or "",
        resource.resource_type or "",
        resource.course.course_title if resource.course else "",
        resource.course.course_code if resource.course else "",
        resource.department.name if resource.department else "",
    ]
    return " ".join(parts)


def get_content_based_recommendations(student, limit=10):
    """
    Returns a list of (Resource, score) tuples, ranked by relevance
    to the given student's profile, using TF-IDF + cosine similarity.
    """
    approved_resources = Resource.query.filter_by(status="approved").all()

    if not approved_resources:
        return []

    student_text = build_student_profile_text(student)
    resource_texts = [build_resource_text(r) for r in approved_resources]

    # The student profile goes in as the FIRST "document", so after vectorizing
    # we can compare it (index 0) against every resource (index 1 onward)
    all_texts = [student_text] + resource_texts

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    student_vector = tfidf_matrix[0:1]
    resource_vectors = tfidf_matrix[1:]

    similarity_scores = cosine_similarity(student_vector, resource_vectors)[0]

    scored_resources = list(zip(approved_resources, similarity_scores))
    scored_resources.sort(key=lambda pair: pair[1], reverse=True)

    return scored_resources[:limit]