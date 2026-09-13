"""Modèle et règles de validation des pièces jointes du chat."""

import os

from django.core.exceptions import ValidationError
from django.db import models

from .messages import Message


def attachment_upload_path(instance, filename):
    """Construit le chemin de stockage regroupé par conversation."""
    return f"chat_attachments/conversation_{instance.message.conversation_id}/{filename}"


class MessageAttachment(models.Model):
    """Fichier attaché à un message avec ses métadonnées de validation."""

    ALLOWED_CONTENT_TYPES = {
        "image/png": "image", "image/jpeg": "image", "image/gif": "image", "image/webp": "image",
        "application/pdf": "pdf", "text/plain": "text",
    }
    MAX_FILE_SIZE = 10 * 1024 * 1024

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
            raise ValidationError(f"Type de fichier non autorisé : {self.content_type}")
        if self.file_size > self.MAX_FILE_SIZE:
            raise ValidationError("Fichier trop volumineux (10 Mo maximum).")

    def __str__(self):
        """Retourne le nom original affiché à l'utilisateur."""
        return self.file_name
