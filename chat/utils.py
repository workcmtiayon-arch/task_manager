def serialize_attachment(attachment):
    """Transforme une pièce jointe Django en objet consommable par le client."""
    return {
        "id": attachment.id,
        "file_url": attachment.file.url,
        "file_name": attachment.file_name,
        "file_size": attachment.file_size,
        "content_type": attachment.content_type,
        "is_image": attachment.is_image(),
        "is_pdf": attachment.is_pdf(),
        "is_text": attachment.is_text(),
    }


def serialize_reactions(message):
    """Regroupe les réactions d'un message par type et liste d'utilisateurs."""
    summary = {}
    for reaction in message.reactions.all():
        summary.setdefault(reaction.reaction, []).append(reaction.user_id)
    return summary


def serialize_receipt_status(message):
    """Calcule les indicateurs livré et lu à partir des accusés destinataires."""
    receipts = list(message.receipts.all())
    if not receipts:
        return {"delivered": False, "read": False}
    return {
        "delivered": all(r.is_delivered() for r in receipts),
        "read": all(r.is_read() for r in receipts),
    }


def serialize_message(message):
    """Sérialise un message et toutes les données nécessaires au rendu JavaScript."""
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender": {"id": message.sender_id, "username": message.sender.username},
        "message_type": message.message_type,
        "content": "" if message.is_deleted() else message.content,
        "is_edited": message.is_edited(),
        "is_deleted": message.is_deleted(),
        "created_at": message.created_at.isoformat(),
        "updated_at": message.updated_at.isoformat(),
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "attachments": [serialize_attachment(a) for a in message.attachments.all()],
        "reactions": serialize_reactions(message),
        "receipt_status": serialize_receipt_status(message),
    }
