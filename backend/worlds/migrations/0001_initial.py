

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Artifact',
            fields=[
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created Time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated Time')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.TextField()),
                ('kind', models.TextField(default='document')),
                ('position', models.JSONField()),
                ('created_tick', models.PositiveBigIntegerField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ArtifactVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created Time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated Time')),
                ('version', models.PositiveIntegerField()),
                ('content', models.TextField()),
                ('tick', models.PositiveBigIntegerField()),
                ('artifact', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='worlds.artifact')),
            ],
        ),
        migrations.CreateModel(
            name='Entity',
            fields=[
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created Time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated Time')),
                ('id', models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ('name', models.TextField()),
                ('kind', models.TextField()),
                ('material', models.TextField()),
                ('state', models.JSONField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Inhabitant',
            fields=[
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created Time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated Time')),
                ('entity', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='worlds.entity')),
                ('name', models.TextField()),
                ('alive', models.BooleanField(default=True)),
                ('driver', models.TextField(default='scripted')),
                ('state', models.JSONField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='artifact',
            name='location',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='worlds.entity'),
        ),
        migrations.CreateModel(
            name='World',
            fields=[
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created Time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated Time')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.TextField()),
                ('configuration', models.JSONField()),
                ('tick', models.PositiveBigIntegerField(default=0)),
                ('revision', models.PositiveBigIntegerField(default=0)),
                ('event_sequence', models.PositiveBigIntegerField(default=0)),
                ('status', models.TextField(default='paused')),
                ('error', models.TextField(blank=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='entity',
            name='world',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entities', to='worlds.world'),
        ),
        migrations.CreateModel(
            name='Connection',
            fields=[
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created Time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated Time')),
                ('id', models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ('state', models.JSONField()),
                ('entity_a', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='connections_a', to='worlds.entity')),
                ('entity_b', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='connections_b', to='worlds.entity')),
                ('world', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='connections', to='worlds.world')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='artifact',
            name='world',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='artifacts', to='worlds.world'),
        ),
        migrations.CreateModel(
            name='SimulationProgram',
            fields=[
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created Time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated Time')),
                ('artifact_version', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='worlds.artifactversion')),
                ('state', models.JSONField(default=dict)),
                ('enabled', models.BooleanField(default=False)),
                ('next_tick', models.PositiveBigIntegerField(default=0)),
                ('host', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='worlds.entity')),
                ('world', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='programs', to='worlds.world')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='worlds.inhabitant')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Memory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created Time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated Time')),
                ('text', models.TextField()),
                ('tick', models.PositiveBigIntegerField()),
                ('confidence', models.FloatField(default=0.5)),
                ('inhabitant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memories', to='worlds.inhabitant')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='inhabitant',
            name='world',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inhabitants', to='worlds.world'),
        ),
        migrations.CreateModel(
            name='Decision',
            fields=[
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created Time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated Time')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tick', models.PositiveBigIntegerField()),
                ('status', models.TextField(default='queued')),
                ('observation', models.JSONField()),
                ('result', models.JSONField(null=True)),
                ('trace', models.JSONField(default=list)),
                ('error', models.TextField(blank=True)),
                ('model_name', models.TextField(blank=True)),
                ('world', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='decisions', to='worlds.world')),
                ('inhabitant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='decisions', to='worlds.inhabitant')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='artifactversion',
            name='author',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='worlds.inhabitant'),
        ),
        migrations.AddField(
            model_name='artifact',
            name='author',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='worlds.inhabitant'),
        ),
        migrations.CreateModel(
            name='MotionBlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created Time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated Time')),
                ('start_tick', models.PositiveBigIntegerField()),
                ('end_tick', models.PositiveBigIntegerField()),
                ('payload', models.BinaryField()),
                ('checksum', models.TextField()),
                ('world', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='motion_blocks', to='worlds.world')),
            ],
            options={
                'indexes': [models.Index(fields=['world', 'start_tick'], name='worlds_moti_world_i_63580f_idx')],
            },
        ),
        migrations.CreateModel(
            name='Checkpoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created Time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated Time')),
                ('tick', models.PositiveBigIntegerField()),
                ('event_sequence', models.PositiveBigIntegerField()),
                ('payload', models.BinaryField()),
                ('checksum', models.TextField()),
                ('world', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checkpoints', to='worlds.world')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('world', 'tick'), name='world_checkpoint_tick_unique')],
            },
        ),
        migrations.CreateModel(
            name='WorldEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created Time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated Time')),
                ('sequence', models.PositiveBigIntegerField()),
                ('tick', models.PositiveBigIntegerField()),
                ('kind', models.TextField()),
                ('actor_id', models.TextField(null=True)),
                ('subject_id', models.TextField(null=True)),
                ('data', models.JSONField()),
                ('world', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='worlds.world')),
            ],
            options={
                'indexes': [models.Index(fields=['world', 'tick'], name='worlds_worl_world_i_709221_idx')],
                'constraints': [models.UniqueConstraint(fields=('world', 'sequence'), name='world_event_sequence_unique')],
            },
        ),
        migrations.AddConstraint(
            model_name='artifactversion',
            constraint=models.UniqueConstraint(fields=('artifact', 'version'), name='artifact_version_unique'),
        ),
    ]
