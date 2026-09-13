"""Modèles et requêtes métier liés aux conversations et à leurs membres."""

from django.conf import settings
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone


class ConversationManager(models.Manager):
    """Expose les requêtes réutilisées pour l'inbox et les invitations."""

    def get_or_create_private(self, user_a, user_b):
        """Retourne la conversation privée existante ou la crée avec ses deux membres."""
        if user_a.pk == user_b.pk:
            raise ValueError("Un utilisateur ne peut pas démarrer une conversation avec lui-même.")
        existing = (
            self.filter(type=Conversation.Type.PRIVATE)
            .filter(
                memberships__user__in=[user_a, user_b],
                memberships__left_at__isnull=True,
            )
            .annotate(member_count=Count("memberships__user", distinct=True))
            .filter(member_count=2)
            .first()
        )
        if existing is not None:
            return existing

        # user_a reste l'initiateur, comme dans la version monolithique d'origine.
        conversation = self.create(type=Conversation.Type.PRIVATE, initiated_by=user_a)
        ConversationMember.objects.bulk_create([
            ConversationMember(conversation=conversation, user=user_a),
            ConversationMember(conversation=conversation, user=user_b),
        ])
        return conversation

    def for_user_inbox(self, user):
        """Sélectionne les conversations actives visibles dans la boîte de réception."""
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
        """Sélectionne les conversations reçues qui attendent encore une acceptation."""
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
    """Représente un espace de discussion privé entre utilisateurs."""

    class Type(models.TextChoices):
        """Définit les types de conversation supportés par le modèle."""

        PRIVATE = "PRIVATE", "Conversation privée"

    type = models.CharField(max_length=20, choices=Type.choices, default=Type.PRIVATE)
    name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="initiated_conversations",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="ConversationMember", related_name="conversations",
    )

    objects = ConversationManager()

    def add_member(self, user):
        """Ajoute un membre ou réactive son adhésion après un départ."""
        membership, created = ConversationMember.objects.get_or_create(user=user, conversation=self)
        if not created and membership.left_at is not None:
            membership.rejoin()
        return membership

    def remove_member(self, user):
        """Marque comme parti le premier membership correspondant à l'utilisateur."""
        membership = self.memberships.filter(user=user).first()
        if membership is not None:
            membership.leave()

    def is_member(self, user):
        """Indique si l'utilisateur authentifié possède une adhésion active."""
        if user.is_anonymous:
            return False
        return self.memberships.filter(user=user, left_at__isnull=True).exists()

    def get_members(self):
        """Retourne les utilisateurs dont l'adhésion à cette conversation est active."""
        return self.members.filter(
            conversation_memberships__conversation=self,
            conversation_memberships__left_at__isnull=True,
        )

    def get_last_message(self):
        """Retourne le message le plus récent de la conversation, s'il existe."""
        return self.messages.order_by("-created_at").first()

    def touch(self):
        """Met à jour l'horodatage de conversation utilisé pour trier l'inbox."""
        Conversation.objects.filter(pk=self.pk).update(updated_at=timezone.now())

    def is_invitation_for(self, user):
        """Indique si la conversation est une invitation reçue par cet utilisateur."""
        if user.is_anonymous or self.initiated_by_id == user.id:
            return False
        return self.accepted_at is None and self.messages.exists()

    def accept(self):
        """Enregistre l'acceptation si la conversation n'a pas encore été acceptée."""
        if self.accepted_at is None:
            self.accepted_at = timezone.now()
            self.save(update_fields=["accepted_at"])

    def __str__(self):
        """Construit le libellé lisible utilisé par l'administration Django."""
        return self.name or f"Conversation #{self.pk}"


class ConversationMember(models.Model):
    """Associe un utilisateur à une conversation avec son état d'adhésion."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversation_memberships")
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="memberships")
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)

    class Meta:
        """Garantit qu'un utilisateur n'a qu'une adhésion par conversation."""

        constraints = [
            models.UniqueConstraint(fields=["user", "conversation"], name="unique_member_per_conversation"),
        ]

    def leave(self):
        """Enregistre le départ sans supprimer l'historique de l'adhésion."""
        self.left_at = timezone.now()
        self.save(update_fields=["left_at"])

    def rejoin(self):
        """Réactive une adhésion précédemment quittée."""
        self.left_at = None
        self.save(update_fields=["left_at"])

    def mute(self):
        """Désactive les notifications de cette conversation pour le membre."""
        self.is_muted = True
        self.save(update_fields=["is_muted"])

    def unmute(self):
        """Réactive les notifications de cette conversation pour le membre."""
        self.is_muted = False
        self.save(update_fields=["is_muted"])

    def is_active(self):
        """Indique si l'adhésion n'a pas été clôturée par un départ."""
        return self.left_at is None

    def __str__(self):
        """Construit le libellé d'administration de l'adhésion."""
        return f"{self.user} @ conversation #{self.conversation_id}"
