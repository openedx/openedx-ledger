# Generated by Django 3.2.16 on 2023-02-16 16:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openedx_ledger', '0002_historicalledger_historicalreversal_historicaltransaction'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicaltransaction',
            name='content_uuid',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='content_uuid',
        ),
        migrations.AddField(
            model_name='historicalreversal',
            name='state',
            field=models.CharField(choices=[('created', 'Created'), ('pending', 'Pending'), ('committed', 'Committed')], db_index=True, default='created', max_length=255),
        ),
        migrations.AddField(
            model_name='historicaltransaction',
            name='content_key',
            field=models.CharField(blank=True, db_index=True, help_text='The globally unique content identifier.  Joinable with ContentMetadata.content_key in enterprise-catalog.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicaltransaction',
            name='reference_type',
            field=models.CharField(blank=True, choices=[('learner_credit_enterprise_course_enrollment_id', 'LearnerCreditEnterpriseCourseEnrollment ID')], db_index=True, help_text='The type of identifier used for `reference_id`.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='historicaltransaction',
            name='state',
            field=models.CharField(choices=[('created', 'Created'), ('pending', 'Pending'), ('committed', 'Committed')], db_index=True, default='created', max_length=255),
        ),
        migrations.AddField(
            model_name='historicaltransaction',
            name='subsidy_access_policy_uuid',
            field=models.UUIDField(blank=True, help_text='A reference to the subsidy access policy which was used to create a transaction for the content.', null=True),
        ),
        migrations.AddField(
            model_name='reversal',
            name='state',
            field=models.CharField(choices=[('created', 'Created'), ('pending', 'Pending'), ('committed', 'Committed')], db_index=True, default='created', max_length=255),
        ),
        migrations.AddField(
            model_name='transaction',
            name='content_key',
            field=models.CharField(blank=True, db_index=True, help_text='The globally unique content identifier.  Joinable with ContentMetadata.content_key in enterprise-catalog.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='reference_type',
            field=models.CharField(blank=True, choices=[('learner_credit_enterprise_course_enrollment_id', 'LearnerCreditEnterpriseCourseEnrollment ID')], db_index=True, help_text='The type of identifier used for `reference_id`.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='state',
            field=models.CharField(choices=[('created', 'Created'), ('pending', 'Pending'), ('committed', 'Committed')], db_index=True, default='created', max_length=255),
        ),
        migrations.AddField(
            model_name='transaction',
            name='subsidy_access_policy_uuid',
            field=models.UUIDField(blank=True, help_text='A reference to the subsidy access policy which was used to create a transaction for the content.', null=True),
        ),
        migrations.AlterField(
            model_name='historicaltransaction',
            name='reference_id',
            field=models.CharField(blank=True, db_index=True, help_text='The identifier of the item acquired via the transaction. e.g. a LearnerCreditEnterpriseCourseEnrollment ID.', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='reference_id',
            field=models.CharField(blank=True, db_index=True, help_text='The identifier of the item acquired via the transaction. e.g. a LearnerCreditEnterpriseCourseEnrollment ID.', max_length=255, null=True),
        ),
    ]