"""Validation helpers for user supplied raster images."""

import warnings

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError


RASTER_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/gif": "GIF",
    "image/webp": "WEBP",
}
MAX_RASTER_PIXELS = 25_000_000


def validate_raster_image(uploaded_file, content_type):
    """Decode and verify an image, matching its MIME type and pixel budget."""
    expected_format = RASTER_FORMATS.get(content_type)
    if expected_format is None:
        raise ValidationError(_("Image type not allowed."))

    try:
        uploaded_file.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(uploaded_file)
            if image.format != expected_format:
                raise ValidationError(_("The image content does not match its type."))
            width, height = image.size
            if width < 1 or height < 1 or width * height > MAX_RASTER_PIXELS:
                raise ValidationError(_("The image dimensions exceed the allowed limit."))
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValidationError(_("The uploaded image is invalid or too large to decode.")) from exc
    finally:
        uploaded_file.seek(0)
