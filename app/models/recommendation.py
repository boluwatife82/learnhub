from app.extensions import db


class RecommendationSetting(db.Model):
    __tablename__ = "recommendation_settings"

    id = db.Column(db.Integer, primary_key=True)
    content_weight = db.Column(db.Numeric(3, 2), nullable=False, default=0.40)
    collaborative_weight = db.Column(db.Numeric(3, 2), nullable=False, default=0.60)

    @staticmethod
    def get_current():
        setting = RecommendationSetting.query.first()
        if not setting:
            setting = RecommendationSetting(content_weight=0.40, collaborative_weight=0.60)
            db.session.add(setting)
            db.session.commit()
        return setting