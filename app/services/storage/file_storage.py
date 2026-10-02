import uuid
import cloudinary.uploader


def save_file(file_storage):
    """
    Uploads a file to Cloudinary and returns its full public URL.
    """
    result = cloudinary.uploader.upload(
        file_storage,
        resource_type="auto",
        public_id=f"learnhub/{uuid.uuid4().hex}",
    )
    return result["secure_url"]