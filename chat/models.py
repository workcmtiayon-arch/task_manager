from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.utils import timezone

# Create your models here.

class ConversationManager(models.Manager):
    def get_or_create_private(self, user_a, user_b):
        if user_a.pk == user_b.pk:
            raise ValueError('Un utilisateur ne peut pas demarer une conversation avec lui-meme')
        
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
        
        conversation = self.create(type=Conversation.Type.PRIVATE)
        ConversationMember.objects.bulk_create([
            ConversationMember(conversation=conversation, user=user_a),
            ConversationMember(conversation=conversation, user=user_b),
        ])
        return conversation
    
class Conversation(models.Model):
    class Type(models.TextChoices):
        PRIVATE = "PRIVATE", "Conversation privée"

    type = models.CharField(max_length=20, choices=Type.choices, default=Type.PRIVATE)
    name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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
        User = settings.AUTH_USER_MODEL
        return self.members.filter(
            conversation_memberships__conversation=self,
            conversation_memberships__left_at__isnull=True,
        )

    def get_last_message(self):
        return self.messages.order_by("-created_at").first()
    
    def touch(self):
        Conversation.objects.filter(pk=self.pk).update(updated_at=timezone.now())

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