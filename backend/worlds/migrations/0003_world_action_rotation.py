

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worlds', '0002_remove_checkpoint_world_checkpoint_tick_unique_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='world',
            name='action_rotation',
            field=models.PositiveBigIntegerField(default=0),
        ),
    ]
