def serialize_attachment(attachment):
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
    summary = {}
    for reaction in message.reactions.all():
        summary.setdefault(reaction.reaction, []).append(reaction.user_id)
    return summary

def serialize_message(message, for_user=None):
    data = {
        "id" : message.id,
        "conversation_id": message.conversation_id,
        "sender": {"id": message.sender_id, "username": message.sender.username},
        "message_type": message.message_type,
        "content": "" if message.is_deleted() else message.content,
        "is_edited": message.is_edited(),
        "is_deleted": message.is_deleted(),
        "created_at": message.created_at.isoformat(),
        "updated_at": message.updated_at.isoformat(),
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "attachment": [serialize_attachment(a) for a in message.attachments.all()],
        "reactions": serialize_reactions(message),
    }
    
    if for_user is not None:
        receipt = message.receipts.filter(user=for_user).first()
        data["receipt"] = (
            {"delivered": receipt.is_delivered(), "read": receipt.is_read()}
            if receipt is not None else None
        )
        
    return data