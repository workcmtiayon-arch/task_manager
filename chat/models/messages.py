"""Modèles représentant les messages, accusés de réception et réactions."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .conversations import Conversation


class Message(models.Model):
    """Message textuel ou porteur d'une pièce jointe dans une conversation."""

    class MessageType(models.TextChoices):
        """Décrit les deux formes de contenu actuellement supportées."""

        TEXT = "TEXT", "Texte"
        ATTACHMENT = "ATTACHMENT", "Pièce jointe"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField(blank=True)
    message_type = models.CharField(max_length=20, choices=MessageType.choices, default=MessageType.TEXT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Définit l'ordre naturel et l'index de consultation des messages."""

        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "-created_at"])]

    def edit(self, new_content):
        """Modifie le contenu d'un message non supprimé et horodate la modification."""
        if self.is_deleted():
            raise ValidationError("Impossible de modifier un message supprimé.")
        self.content = new_content
        self.edited_at = timezone.now()
        self.save(update_fields=["content", "edited_at", "updated_at"])

    def delete(self, *args, **kwargs):
        """Effectue une suppression logique en conservant le message en base."""
        self.deleted_at = timezone.now()
        self.content = ""
        self.save(update_fields=["deleted_at", "content", "updated_at"])

    def is_edited(self):
        """Indique si le contenu a déjà été modifié."""
        return self.edited_at is not None

    def is_deleted(self):
        """Indique si le message a été supprimé logiquement."""
        return self.deleted_at is not None

    def has_attachments(self):
        """Indique si au moins une pièce jointe est associée au message."""
        return self.attachments.exists()

    def __str__(self):
        """Construit le libellé lisible du message."""
        return f"Message #{self.pk} ({self.sender})"


class MessageReceipt(models.Model):
    """Stocke les états livré et lu d'un message pour un destinataire."""

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="receipts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="message_receipts")
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Empêche de créer deux accusés pour un même utilisateur et message."""

        constraints = [models.UniqueConstraint(fields=["message", "user"], name="unique_receipt_per_user_message")]

    def mark_as_delivered(self):
        """Marque le message comme livré uniquement s'il ne l'était pas encore."""
        if self.delivered_at is None:
            self.delivered_at = timezone.now()
            self.save(update_fields=["delivered_at"])

    def mark_as_read(self):
        """Marque le message comme lu et le livre implicitement si nécessaire."""
        now = timezone.now()
        update_fields = []
        if self.delivered_at is None:
            self.delivered_at = now
            update_fields.append("delivered_at")
        if self.read_at is None:
            self.read_at = now
            update_fields.append("read_at")
        if update_fields:
            self.save(update_fields=update_fields)

    def is_delivered(self):
        """Indique si l'accusé de livraison est renseigné."""
        return self.delivered_at is not None

    def is_read(self):
        """Indique si l'accusé de lecture est renseigné."""
        return self.read_at is not None

    def __str__(self):
        """Construit le libellé d'administration de l'accusé."""
        return f"Receipt msg#{self.message_id} / {self.user}"


class MessageReaction(models.Model):
    """Représente la réaction unique d'un utilisateur à un message."""

    class Reaction(models.TextChoices):
        """Liste les réactions exposées par l'interface du chat."""

        LIKE = "LIKE", "like"
        LOVE = "LOVE", "love"
        LAUGH = "LAUGH", "laugh"
        WOW = "WOW", "wow"
        SAD = "SAD", "sad"
        ANGRY = "ANGRY", "angry"

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="message_reactions")
    reaction = models.CharField(max_length=10, choices=Reaction.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Garantit une réaction par utilisateur et indexe ses regroupements."""

        constraints = [models.UniqueConstraint(fields=["message", "user"], name="unique_reaction_per_user_message")]
        indexes = [models.Index(fields=["message", "reaction"])]

    def change(self, new_reaction):
        """Remplace la réaction existante de l'utilisateur."""
        self.reaction = new_reaction
        self.save(update_fields=["reaction"])

    def remove(self):
        """Supprime cette réaction de la base."""
        self.delete()

    def __str__(self):
        """Construit le libellé lisible de la réaction."""
        return f"{self.reaction} par {self.user} sur msg#{self.message_id}"
