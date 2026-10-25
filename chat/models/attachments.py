"""Modèle et règles de validation des pièces jointes du chat."""

import os
import uuid

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from core.uploads import validate_raster_image
from .messages import Message


def attachment_upload_path(instance, filename):
    """Store uploads under opaque names so user filenames never form paths."""
    extension = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
        "text/plain": ".txt",
    }.get(instance.content_type, "")
    return f"chat_attachments/conversation_{instance.message.conversation_id}/{uuid.uuid4().hex}{extension}"


class MessageAttachment(models.Model):
    """Fichier attaché à un message avec ses métadonnées de validation."""

    ALLOWED_CONTENT_TYPES = {
        "image/png": "image", "image/jpeg": "image", "image/gif": "image", "image/webp": "image",
        "application/pdf": "pdf", "text/plain": "text",
    }
    MAX_FILE_SIZE = 10 * 1024 * 1024

    @classmethod
    def validate_upload(cls, uploaded_file):
        """Validate the declared MIME type against a small file signature."""
        if uploaded_file.content_type not in cls.ALLOWED_CONTENT_TYPES:
            raise ValidationError(_("File type not allowed."))
        if uploaded_file.size > cls.MAX_FILE_SIZE:
            raise ValidationError(_("File too large (10 MB maximum)."))

        if uploaded_file.content_type.startswith("image/"):
            validate_raster_image(uploaded_file, uploaded_file.content_type)
            return

        header = uploaded_file.read(16)
        uploaded_file.seek(0)
        if uploaded_file.content_type == "application/pdf":
            valid = header.startswith(b"%PDF-")
        else:
            try:
                content = uploaded_file.read()
                uploaded_file.seek(0)
                content.decode("utf-8")
                valid = b"\x00" not in content
            except UnicodeDecodeError:
                valid = False
        if not valid:
            raise ValidationError(_("The file content does not match its type."))

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=attachment_upload_path)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_file_extension(self):
        """Retourne l'extension normalisée du nom de fichier."""
        return os.path.splitext(self.file_name)[1].lower().lstrip(".")

    def is_image(self):
        """Indique si la pièce jointe est une image affichable dans le chat."""
        return self.content_type.startswith("image/")

    def is_pdf(self):
        """Indique si la pièce jointe est un document PDF."""
        return self.content_type == "application/pdf"

    def is_text(self):
        """Indique si la pièce jointe est un fichier texte simple."""
        return self.content_type == "text/plain"

    def clean(self):
        """Valide le type MIME et la taille avant l'enregistrement du fichier."""
        if self.content_type not in self.ALLOWED_CONTENT_TYPES:
            raise ValidationError(_("File type not allowed: %(content_type)s") % {"content_type": self.content_type})
        if self.file_size > self.MAX_FILE_SIZE:
            raise ValidationError(_("File too large (10 MB maximum)."))

    def __str__(self):
        """Retourne le nom original affiché à l'utilisateur."""
        return self.file_name


@receiver(post_delete, sender=MessageAttachment)
def delete_attachment_file_after_commit(sender, instance, **kwargs):
    """Remove stored bytes after the database deletion has committed."""
    file_name = instance.file.name
    storage = instance.file.storage
    if file_name:
        transaction.on_commit(lambda: storage.delete(file_name))
