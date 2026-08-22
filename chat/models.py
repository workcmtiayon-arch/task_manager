import os
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone



class ConversationManager(models.Manager):
    def get_or_create_private(self, user_a, user_b):
        if user_a.pk == user_b.pk:
            raise ValueError("Un utilisateur ne peut pas démarrer une conversation avec lui-même.")
        existing = (
            self.filter(type=Conversation.Type.PRIVATE)
            .filter(memberships__user=user_a)
            .filter(memberships__user=user_b)
            .annotate(member_count=Count("memberships"))
            .filter(member_count=2)
            .first()
        )
        
        if existing is not None:
            return existing

        # user_a est celui qui appelle get_or_create_private (voir conversation_start dans views.py) : c'est donc lui l'initiateur de la conversation....
        
        conversation = self.create(type=Conversation.Type.PRIVATE, initiated_by=user_a)
        ConversationMember.objects.bulk_create([
            ConversationMember(conversation=conversation, user=user_a),
            ConversationMember(conversation=conversation, user=user_b),
        ])
        return conversation

    def for_user_inbox(self, user):
        return (
            self.filter(
                type=Conversation.Type.PRIVATE,
                memberships__user=user,
                memberships__left_at__isnull=True,
            )
            .filter(Q(initiated_by=user) | Q(accepted_at__isnull=False))
            .distinct()
        )

    def invitations_for_user(self, user):
        return (
            self.filter(
                type=Conversation.Type.PRIVATE,
                memberships__user=user,
                memberships__left_at__isnull=True,
                accepted_at__isnull=True,
            )
            .exclude(initiated_by=user)
            .filter(messages__isnull=False)
            .distinct()
        )


class Conversation(models.Model):
    class Type(models.TextChoices):
        PRIVATE = "PRIVATE", "Conversation privée"
        # GROUP = "GROUP", "Groupe"... réservé à une évolution future (hors de ma Versio1)

    type = models.CharField(max_length=20, choices=Type.choices, default=Type.PRIVATE)
    name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiated_conversations",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ConversationMember",
        related_name="conversations",
    )
    
    objects = ConversationManager()
    
    def add_member(self, user):
        membership, created = ConversationMember.objects.get_or_create(
            user=user, conversation=self,
        )
        if not created and membership.left_at is not None:
            membership.rejoin()
        return membership
    
    def remove_member(self, user):
        membership = self.memberships.filter(user=user).first()
        if membership is not None:
            membership.leave()
            
    def is_member(self, user):
        if user.is_anonymous:
            return False
        return self.memberships.filter(user=user, left_at__isnull=True).exists()

    def get_members(self):
        
        return self.members.filter(
            conversation_memberships__conversation=self,
            conversation_memberships__left_at__isnull=True,
        )

    def get_last_message(self):
        return self.messages.order_by("-created_at").first()
    
    def touch(self):
        Conversation.objects.filter(pk=self.pk).update(updated_at=timezone.now())

    def is_invitation_for(self, user):
        if user.is_anonymous or self.initiated_by_id == user.id:
            return False
        return self.accepted_at is None and self.messages.exists()

    def accept(self):
        if self.accepted_at is None:
            self.accepted_at = timezone.now()
            self.save(update_fields=["accepted_at"])

    def __str__(self):
        return self.name or f"Conversation #{self.pk}"


class ConversationMember(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversation_memberships",
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "conversation"], name="unique_member_per_conversation"),
        ]

    def leave(self):
        self.left_at = timezone.now()
        self.save(update_fields=["left_at"])

    def rejoin(self):
        self.left_at = None
        self.save(update_fields=["left_at"])

    def mute(self):
        self.is_muted = True
        self.save(update_fields=["is_muted"])

    def unmute(self):
        self.is_muted = False
        self.save(update_fields=["is_muted"])

    def is_active(self):
        return self.left_at is None

    def __str__(self):
        return f"{self.user} @ conversation #{self.conversation_id}"


class Message(models.Model):
    class MessageType(models.TextChoices):
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
        ordering = ["created_at"]

    def edit(self, new_content):
        if self.is_deleted():
            raise ValidationError("Impossible de modifier un message supprimé.")
        self.content = new_content
        self.edited_at = timezone.now()
        self.save(update_fields=["content", "edited_at", "updated_at"])

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()
        self.content = ""
        self.save(update_fields=["deleted_at", "content", "updated_at"])

    def is_edited(self):
        return self.edited_at is not None

    def is_deleted(self):
        return self.deleted_at is not None

    def has_attachments(self):
        return self.attachments.exists()

    def __str__(self):
        return f"Message #{self.pk} ({self.sender})"




class MessageReceipt(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="receipts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="message_receipts")
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["message", "user"], name="unique_receipt_per_user_message"),
        ]
        
    def mark_as_delivered(self):
        if self.delivered_at is None:
            self.delivered_at = timezone.now()
            self.save(update_fields=["delivered_at"])

    def mark_as_read(self):
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
        return self.delivered_at is not None

    def is_read(self):
        return self.read_at is not None

    def __str__(self):
        return f"Receipt msg#{self.message_id} / {self.user}"



class MessageReaction(models.Model):
    class Reaction(models.TextChoices):
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
        constraints = [
            models.UniqueConstraint(fields=["message", "user"], name="unique_reaction_per_user_message"),
        ]

    def change(self, new_reaction):
        self.reaction = new_reaction
        self.save(update_fields=["reaction"])

    def remove(self):
        self.delete()

    def __str__(self):
        return f"{self.reaction} par {self.user} sur msg#{self.message_id}"



def attachment_upload_path(instance, filename):
    return f"chat_attachments/conversation_{instance.message.conversation_id}/{filename}"


class MessageAttachment(models.Model):
    ALLOWED_CONTENT_TYPES = {
        "image/png": "image",
        "image/jpeg": "image",
        "image/gif": "image",
        "image/webp": "image",
        "application/pdf": "pdf",
        "text/plain": "text",
    }
    MAX_FILE_SIZE = 10 * 1024 * 1024

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=attachment_upload_path)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_file_extension(self):
        return os.path.splitext(self.file_name)[1].lower().lstrip(".")

    def is_image(self):
        return self.content_type.startswith("image/")
    
    def is_pdf(self):
        return self.content_type == "application/pdf"

    def is_text(self):
        return self.content_type == "text/plain"
    
    def clean(self):
        if self.content_type not in self.ALLOWED_CONTENT_TYPES:
            raise ValidationError(f"Type de fichier non autorisé : {self.content_type}")
        if self.file_size > self.MAX_FILE_SIZE:
            raise ValidationError("Fichier trop volumineux (10 Mo maximum).")
        
    def __str__(self):
        return self.file_name