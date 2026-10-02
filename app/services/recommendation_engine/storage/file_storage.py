import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app


def save_file(file_storage):
    """
    Saves an uploaded file to the local upload folder and returns
    the relative path to store in the database.

    Designed so that swapping this function's internals for
    Cloudinary/AWS S3 later won't require changing any code
    that calls save_file() elsewhere in the app.
    """
    original_filename = secure_filename(file_storage.filename)
    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, unique_filename)
    file_storage.save(file_path)

    # relative path, so it works regardless of the machine's absolute file structure
    return f"uploads/{unique_filename}"