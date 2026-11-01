

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worlds', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='checkpoint',
            name='world_checkpoint_tick_unique',
        ),
        migrations.AddConstraint(
            model_name='checkpoint',
            constraint=models.UniqueConstraint(fields=('world', 'tick', 'event_sequence'), name='world_checkpoint_tick_unique'),
        ),
    ]
