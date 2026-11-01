from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worlds', '0004_resourcearea'),
    ]

    operations = [
        migrations.AddField(
            model_name='decision',
            name='messages',
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name='inhabitant',
            name='agent_context',
            field=models.JSONField(default=dict),
        ),
    ]
