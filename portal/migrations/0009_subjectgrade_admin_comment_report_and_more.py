# Generated by Django 5.2.4 on 2025-07-21 18:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0008_delete_studentreport'),
    ]

    operations = [
        migrations.AddField(
            model_name='subjectgrade',
            name='admin_comment_report',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='subjectgrade',
            name='overall_average',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='subjectgrade',
            name='overall_position',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='subjectgrade',
            name='overall_score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='subjectgrade',
            name='total_available_score',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
