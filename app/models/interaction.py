from datetime import datetime
from app.extensions import db


class Rating(db.Model):
    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating_value = db.Column(db.SmallInteger, nullable=False)  # 1 to 5
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("resource_id", "user_id", name="uq_rating_per_user"),)

    resource = db.relationship("Resource", backref="ratings")
    user = db.relationship("User", backref="ratings")


class Vote(db.Model):
    __tablename__ = "votes"

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("resource_id", "user_id", name="uq_vote_per_user"),)

    resource = db.relationship("Resource", backref="votes")
    user = db.relationship("User", backref="votes")


class Download(db.Model):
    __tablename__ = "downloads"

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    resource = db.relationship("Resource", backref="downloads")
    user = db.relationship("User", backref="downloads")


class UserInteraction(db.Model):
    __tablename__ = "user_interactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id"), nullable=False)
    interaction_type = db.Column(db.String(20), nullable=False)
    weight = db.Column(db.Numeric(4, 2), nullable=False, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="interactions")
    resource = db.relationship("Resource", backref="interactions")


class Bookmark(db.Model):
    __tablename__ = "bookmarks"

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("resource_id", "user_id", name="uq_bookmark_per_user"),)

    resource = db.relationship("Resource", backref="bookmarks")
    user = db.relationship("User", backref="bookmarks")