"""
Configures the Cloudinary SDK once, at import time, using the keys from .env.
Import this module (directly or indirectly) before making any Cloudinary
calls - app/routers/files.py imports it at the top for exactly that reason.
"""
import cloudinary
from app.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)