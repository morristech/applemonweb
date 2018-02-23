# Generated by Django 2.0.2 on 2018-02-23 07:13

import armgmt.models
import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import localflavor.us.models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=127, unique=True)),
                ('contact_name', models.CharField(max_length=127)),
                ('firm_name', models.CharField(blank=True, max_length=127)),
                ('address1', models.CharField(blank=True, max_length=127)),
                ('address2', models.CharField(max_length=127)),
                ('city', models.CharField(max_length=127)),
                ('state', localflavor.us.models.USStateField(max_length=2)),
                ('zip_code', localflavor.us.models.USZipCodeField(max_length=10)),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128)),
                ('notes', models.TextField(blank=True)),
                ('active', models.BooleanField(default=True)),
                ('address_validation', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('no', armgmt.models.DocumentNoField(unique=True, validators=[armgmt.models.validate_DocumentNo])),
                ('name', models.CharField(blank=True, max_length=127)),
                ('content', models.TextField(blank=True)),
                ('date', models.DateField(default=datetime.date.today)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='armgmt.Client')),
            ],
            options={
                'abstract': False,
                'ordering': ['-no'],
            },
        ),
        migrations.CreateModel(
            name='InvoiceLineAction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=31, unique=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='InvoiceLineItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveSmallIntegerField()),
                ('date', models.DateField(default=datetime.date.today)),
                ('content', models.TextField()),
                ('qty', models.DecimalField(decimal_places=3, max_digits=6)),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=8)),
                ('action', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='armgmt.InvoiceLineAction')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='armgmt.Invoice')),
            ],
            options={
                'ordering': ['invoice', 'position', 'date'],
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=datetime.date.today)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=8)),
                ('notes', models.TextField(blank=True)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='armgmt.Invoice')),
            ],
            options={
                'ordering': ['-date', '-invoice__no'],
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('no', armgmt.models.DocumentNoField(unique=True, validators=[armgmt.models.validate_DocumentNo])),
                ('name', models.CharField(blank=True, max_length=127)),
                ('content', models.TextField(blank=True)),
                ('start_date', models.DateField(default=datetime.date.today)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='armgmt.Client')),
            ],
            options={
                'abstract': False,
                'ordering': ['-no'],
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_opened', models.DateField(default=datetime.date.today)),
                ('date_due', models.DateField(blank=True, null=True)),
                ('date_closed', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('new', 'New'), ('open', 'Open'), ('done', 'Done'), ('archived', 'Archived')], default='new', max_length=8)),
                ('name', models.CharField(max_length=127)),
                ('content', models.TextField(blank=True)),
                ('assignee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks_assigned', to=settings.AUTH_USER_MODEL)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks_authored', to=settings.AUTH_USER_MODEL)),
                ('client', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='armgmt.Client')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='armgmt.Invoice')),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='armgmt.Project')),
            ],
            options={
                'ordering': ['date_due', 'date_opened'],
            },
        ),
        migrations.AddField(
            model_name='invoice',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='armgmt.Project'),
        ),
        migrations.CreateModel(
            name='Biller',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=1, unique=True)),
                ('name', models.CharField(max_length=127, unique=True)),
                ('firm_name', models.CharField(max_length=127)),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128)),
                ('address1', models.CharField(blank=True, max_length=127)),
                ('address2', models.CharField(max_length=127)),
                ('city', models.CharField(max_length=127)),
                ('fax_number', phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128)),
                ('state', localflavor.us.models.USStateField(max_length=2)),
                ('zip_code', localflavor.us.models.USZipCodeField(max_length=10)),
            ],
            options={
                'ordering': ['code'],
            },
        ),
        migrations.AlterField(
            model_name='invoice',
            name='no',
            field=armgmt.models.DocumentNoField(validators=[armgmt.models.validate_DocumentNo]),
        ),
        migrations.AlterField(
            model_name='project',
            name='no',
            field=armgmt.models.DocumentNoField(validators=[armgmt.models.validate_DocumentNo]),
        ),
        migrations.AddField(
            model_name='client',
            name='biller',
            field=models.ForeignKey(default=armgmt.models.get_default_biller_id, on_delete=django.db.models.deletion.CASCADE, to='armgmt.Biller'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='biller',
            field=models.ForeignKey(default=armgmt.models.get_default_biller_id, on_delete=django.db.models.deletion.CASCADE, to='armgmt.Biller'),
        ),
        migrations.AddField(
            model_name='project',
            name='biller',
            field=models.ForeignKey(default=armgmt.models.get_default_biller_id, on_delete=django.db.models.deletion.CASCADE, to='armgmt.Biller'),
        ),
        migrations.AlterUniqueTogether(
            name='invoice',
            unique_together={('biller', 'no')},
        ),
        migrations.AddField(
            model_name='project',
            name='contact_name',
            field=models.CharField(blank=True, max_length=127),
        ),
        migrations.AlterUniqueTogether(
            name='project',
            unique_together={('biller', 'no')},
        ),
        migrations.AddField(
            model_name='task',
            name='biller',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='armgmt.Biller'),
        ),
        migrations.AddField(
            model_name='client',
            name='fax_number',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128),
        ),
    ]
