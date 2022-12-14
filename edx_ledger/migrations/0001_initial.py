# Generated by Django 3.2.16 on 2022-12-14 10:03

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import jsonfield.fields
import model_utils.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ledger',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('idempotency_key', models.CharField(max_length=255, unique=True)),
                ('unit', models.CharField(choices=[('usd_cents', 'U.S. Dollar (Cents)'), ('seats', 'Seats in a course'), ('jpy', 'Japanese Yen')], db_index=True, default='usd_cents', max_length=255)),
                ('metadata', jsonfield.fields.JSONField(blank=True, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('idempotency_key', models.CharField(db_index=True, max_length=255)),
                ('quantity', models.BigIntegerField()),
                ('metadata', jsonfield.fields.JSONField(blank=True, null=True)),
                ('lms_user_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('content_uuid', models.UUIDField(blank=True, db_index=True, null=True)),
                ('reference_id', models.CharField(blank=True, db_index=True, help_text='The identifier of the item acquired via the transaction.e.g. a course enrollment ID, an entitlement ID, a subscription license ID.', max_length=255, null=True)),
                ('ledger', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to='edx_ledger.ledger')),
            ],
            options={
                'unique_together': {('ledger', 'idempotency_key')},
            },
        ),
        migrations.CreateModel(
            name='Reversal',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('idempotency_key', models.CharField(db_index=True, max_length=255)),
                ('quantity', models.BigIntegerField()),
                ('metadata', jsonfield.fields.JSONField(blank=True, null=True)),
                ('transaction', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reversal', to='edx_ledger.transaction')),
            ],
            options={
                'unique_together': {('transaction', 'idempotency_key')},
            },
        ),
    ]
