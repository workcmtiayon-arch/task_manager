from django.contrib import admin
from .models import Conversation, ConversationMember, Message, MessageAttachment, MessageReaction, MessageReceipt

# Register your models here.

class ConversationMemberInline(admin.TabularInline):
    model = ConversationMember
    extra = 0
    

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "type", 'name', 'created_at', "updated_at"]
    list_filter = ["type"]
    inlines = [ConversationMemberInline]
    

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'message_type', 'created_at', "is_edited", "is_deleted"]
    list_filter = ["message_type", "conversation"]
    search_fields = ["content"]
    
    
admin.site.register(MessageReceipt)
admin.site.register(MessageReaction)
admin.site.register(MessageAttachment)