"""
Backfill initial deposits.

Note this has no reverse migration logic. Attempts to rollback the deployment which includes this PR will not delete
(un-backfill) the deposits created during the forward migration.
"""
from django.db import migrations

from openedx_ledger.utils import find_legacy_initial_transactions


def forwards_func(apps, schema_editor):
    """
    The core logic of this migration.
    """
    # We get the model from the versioned app registry; if we directly import it, it'll be the wrong version.
    Transaction = apps.get_model("openedx_ledger", "Transaction")
    Deposit = apps.get_model("openedx_ledger", "Deposit")

    # Fetch all "legacy" initial transactions
    legacy_initial_transactions = find_legacy_initial_transactions(Transaction).values("uuid", "quantity")
    deposits_to_backfill = (
        Deposit(
            transaction=tx["uuid"],
            desired_deposit_quantity=tx["quantity"],
        )
        for tx in legacy_initial_transactions
    )
    Deposit.bulk_create(deposits_to_backfill)


class Migration(migrations.Migration):
    """
    Migration for backfilling initial deposits.
    """
    dependencies = [
        ("openedx_ledger", "0011_deposit_models"),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
