# Generated by Django 2.0.8 on 2018-09-14 11:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('datalogger', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sensor',
            name='datalogger',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='datalogger.Datalogger'),
        ),
    ]
