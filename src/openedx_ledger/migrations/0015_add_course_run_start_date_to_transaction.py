from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openedx_ledger', '0014_rename_transaction_ledger_content_key_openedx_led_ledger__4c90f0_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicaltransaction',
            name='course_run_start_date',
            field=models.DateTimeField(blank=True, db_index=True, help_text='The start date of the course run associated with this Transaction. The start date is captured at the time the Transaction is created and may not be up to date.', null=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='course_run_start_date',
            field=models.DateTimeField(blank=True, db_index=True, help_text='The start date of the course run associated with this Transaction. The start date is captured at the time the Transaction is created and may not be up to date.', null=True),
        ),
    ]
