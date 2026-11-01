

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worlds', '0003_world_action_rotation'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResourceArea',
            fields=[
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created Time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated Time')),
                ('id', models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ('name', models.TextField()),
                ('state', models.JSONField()),
                ('world', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resource_areas', to='worlds.world')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
