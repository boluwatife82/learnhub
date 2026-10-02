from flask import Flask, app
from app.config import config_by_name
from app.extensions import db, migrate, login_manager
import cloudinary


def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    cloudinary.config(
        cloud_name=app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=app.config["CLOUDINARY_API_KEY"],
        api_secret=app.config["CLOUDINARY_API_SECRET"],
        
    )
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    with app.app_context():
        from app import models  # noqa: F401
        
    from app.routes.auth import auth_bp
    from app.routes.resources import resources_bp
    from app.routes.admin import admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(admin_bp)

    return app