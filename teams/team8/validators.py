"""Reusable domain validators for uploaded media and structured plan data."""

from pathlib import Path

from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_VIDEO_SIZE = 200 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm"}


def _extension(uploaded_file):
    return Path(uploaded_file.name).suffix.lower()


def validate_image(uploaded_file):
    if uploaded_file.size > MAX_IMAGE_SIZE:
        raise ValidationError("حجم تصویر نباید بیشتر از ۵ مگابایت باشد.")
    if _extension(uploaded_file) not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("فرمت تصویر باید JPG، PNG یا WebP باشد.")


def validate_video(uploaded_file):
    if uploaded_file.size > MAX_VIDEO_SIZE:
        raise ValidationError("حجم ویدیو نباید بیشتر از ۲۰۰ مگابایت باشد.")
    if _extension(uploaded_file) not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValidationError("فرمت ویدیو باید MP4 یا WebM باشد.")


def validate_list(value):
    if not isinstance(value, list):
        raise ValidationError("این مقدار باید یک آرایه JSON باشد.")

