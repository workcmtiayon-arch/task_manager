from django.db import migrations, models


def assign_legacy_keys(apps, schema_editor):
    Conversation = apps.get_model("chat", "Conversation")
    database = schema_editor.connection.alias
    for conversation_id in Conversation.objects.using(database).values_list("pk", flat=True):
        Conversation.objects.using(database).filter(pk=conversation_id).update(
            private_key=f"legacy:{conversation_id}"
        )


class Migration(migrations.Migration):
    dependencies = [("chat", "0004_alter_conversation_type_alter_message_message_type")]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="private_key",
            field=models.CharField(blank=True, editable=False, max_length=64, null=True, unique=True),
        ),
        migrations.RunPython(assign_legacy_keys, migrations.RunPython.noop),
    ]
