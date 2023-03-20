"""
The openedx_ledger python API.
"""
from django.db.transaction import atomic, get_connection

from openedx_ledger import models, utils


def create_transaction(
    ledger, quantity, idempotency_key,
    lms_user_id=None, content_key=None,
    subsidy_access_policy_uuid=None, state=models.TransactionStateChoices.CREATED,
    **metadata
):
    """
    Create a transaction.

    Should throw an exception when transaction would exceed balance of the ledger.
    Locking and DB transactions?
    (course id, ledger, user) are unique.
    Or support an idempotency key.
    """
    durable = not get_connection().in_atomic_block
    with atomic(durable=durable):
        balance = ledger.balance()
        if (quantity < 0) and ((balance + quantity) < 0):
            # TODO: we definitely have to revisit this logic later to implement ADR 0002.
            raise Exception("d'oh!")  # pylint: disable=broad-exception-raised

        transaction, _ = models.Transaction.objects.get_or_create(
            ledger=ledger,
            idempotency_key=idempotency_key,
            defaults={
                "quantity": quantity,
                "content_key": content_key,
                "lms_user_id": lms_user_id,
                "subsidy_access_policy_uuid": subsidy_access_policy_uuid,
                "state": state,
                "metadata": metadata,
            },
        )
        return transaction


def reverse_full_transaction(transaction, idempotency_key, **metadata):
    """
    Reverse a transaction, in full.

    Idempotency of reversals - reversing the same transaction twice
    produces the same output and has no side effect on the second invocation.
    Support idempotency key here, too.
    """
    with atomic(durable=True):
        # select the transaction and any reversals
        # if there is a reversal: return, no work to do here
        # if not, write a reversal for the transaction
        transaction.refresh_from_db()
        reversal, _ = models.Reversal.objects.get_or_create(
            transaction=transaction,
            idempotency_key=idempotency_key,
            defaults={
                'quantity': transaction.quantity * -1,
                'metadata': metadata,
            },
        )
        return reversal


def create_ledger(unit=None, idempotency_key=None, subsidy_uuid=None, initial_deposit=None, **metadata):
    """
    Primary interface for creating a Ledger record.

    params:
      unit: Optional unit for the ledger, defaults to the model default of USD_CENTS.
      idempotency_key: Optional idempotency key, defaults to result of
        the utility function for creating ledger idempotency key
      subsidy_uuid: Optional subsidy uuid used in above utility function.
      initial_deposit: Optional amount of value to initialize the ledger with.  In units specified by units
        (units by default are USD_CENTS).
      metadata: Optional additional information for the ledger.
    """
    ledger, _ = models.Ledger.objects.get_or_create(
        unit=unit or models.UnitChoices.USD_CENTS,
        idempotency_key=idempotency_key or utils.create_idempotency_key_for_ledger(subsidy_uuid),
        defaults={
            'metadata': metadata,
        },
    )
    if initial_deposit:
        initial_idpk = utils.create_idempotency_key_for_transaction(
            ledger,
            initial_deposit,
            is_initial_deposit=True,
        )
        create_transaction(
            ledger,
            initial_deposit,
            initial_idpk,
            state=models.TransactionStateChoices.COMMITTED,
        )

    return ledger
