"""
The openedx_ledger python API.
"""
from django.db.transaction import atomic, get_connection

from openedx_ledger import models, utils
from openedx_ledger.signals.signals import TRANSACTION_REVERSED


class LedgerBalanceExceeded(Exception):
    """
    Exception for when a transaction could not be created because it would exceed the ledger balance.
    """


class NonCommittedTransactionError(Exception):
    """
    Raised when a transaction that is not in a COMMITTED state is used in a reversal.
    """


def create_transaction(
    ledger,
    quantity,
    idempotency_key,
    lms_user_id=None,
    content_key=None,
    subsidy_access_policy_uuid=None,
    state=models.TransactionStateChoices.CREATED,
    **metadata
):
    """
    Create a pending transaction.

    Args:
        ledger (openedx_ledger.models.Ledger): The ledger to which the transaction should be added.
        quantity (int): Negative value representing the desired quantity of the new Transaction.
        idempotency_key (str): The idempotency_key of the new Transaction.
        lms_user_id (int, Optional):
            The lms_user_id representing the learner who is enrolling. Skip if this does not represent a policy
            enrolling a learner into content.
        content_key (str, Optional):
            The identifier of the content into which the learner is enrolling. Skip if this does not represent a policy
            enrolling a learner into content.
        subsidy_access_policy_uuid (str, Optional):
            The policy which permitted the creation of the new Transaction. Skip if this does not represent a policy
            enrolling a learner into content.
        state (str, Optional):
            The initial state of the new transaction. Choice of openedx_ledger.models.TransactionStateChoices.
        **metadata (dict, Optional):
            Optional metadata to add to the transaction, potentially useful for debugging, analytics, or other purposes
            defined by the caller.

    Raises:
        openedx_ledger.models.LedgerLockAttemptFailed:
            Raises this if there's another attempt in process to add a transaction to this Ledger.
        openedx_ledger.api.LedgerBalanceExceeded:
            Raises this if the transaction would cause the balance of the ledger to become negative.
        openedx_ledger.api.NonCommittedTransactionError:
            Raises this if the transaction is not in a COMMITTED state.
    """
    with ledger.lock():
        durable = not get_connection().in_atomic_block
        with atomic(durable=durable):
            balance = ledger.balance()
            if (quantity < 0) and ((balance + quantity) < 0):
                raise LedgerBalanceExceeded("A Transaction was not created because it would exceed the ledger balance.")

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

        if transaction.state != models.TransactionStateChoices.COMMITTED:
            raise NonCommittedTransactionError(
                "Cannot reverse transaction because it is not in a committed state."
            )

        reversal, _ = models.Reversal.objects.get_or_create(
            transaction=transaction,
            idempotency_key=idempotency_key,
            defaults={
                'quantity': transaction.quantity * -1,
                'metadata': metadata,
            },
            state=models.TransactionStateChoices.COMMITTED,
        )
        TRANSACTION_REVERSED.send(sender=models.Reversal, reversal=reversal)
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
