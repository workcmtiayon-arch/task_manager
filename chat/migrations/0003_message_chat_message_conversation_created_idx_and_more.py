from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chat", "0002_conversation_accepted_at_conversation_initiated_by")]

    operations = [
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["conversation", "-created_at"], name="chat_messag_convers_4de8a5_idx"),
        ),
        migrations.AddIndex(
            model_name="messagereaction",
            index=models.Index(fields=["message", "reaction"], name="chat_messag_message_43be72_idx"),
        ),
    ]
