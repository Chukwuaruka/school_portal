# Generated by Django 5.2.2 on 2025-06-15 20:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0004_alter_user_classroom'),
    ]

    operations = [
        migrations.AddField(
            model_name='subjectgrade',
            name='classroom',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='portal.classroom'),
        ),
    ]
