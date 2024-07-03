"""
Common utility functions that don't create/update/destroy business objects.
"""
import hashlib
from uuid import uuid4

from django.db.models import F, Window
from django.db.models.functions import FirstValue

from openedx_ledger.models import Transaction

from .constants import (
    INITIAL_DEPOSIT_TRANSACTION_SLUG,
    LEDGER_DEFAULT_IDEMPOTENCY_KEY_PREFIX,
    LEDGERED_SUBSIDY_IDEMPOTENCY_KEY_PREFIX,
)

TRANSACTION_METADATA_KEYS = {
    'lms_user_id',
    'content_key',
    'subsidy_access_policy_uuid',
}


def create_idempotency_key_for_ledger(subsidy_uuid=None):
    """
    Returns an idempotency key for creating a new ledger, given
    the UUID value of some Subsidy record.
    If subsidy_uuid is null, return some prefixed uuid4.
    """
    if subsidy_uuid:
        return f'{LEDGERED_SUBSIDY_IDEMPOTENCY_KEY_PREFIX}-{subsidy_uuid}'
    return f'{LEDGER_DEFAULT_IDEMPOTENCY_KEY_PREFIX}-{uuid4()}'


def create_idempotency_key_for_transaction(ledger, quantity, is_initial_deposit=False, **metadata):
    """
    Create a key that allows a transaction to be executed idempotently.
    """
    if is_initial_deposit:
        return f'{ledger.idempotency_key}-{quantity}-{INITIAL_DEPOSIT_TRANSACTION_SLUG}'

    idpk_data = {
        tx_key: value
        for tx_key, value in metadata.items()
        if tx_key in TRANSACTION_METADATA_KEYS
    }
    if not idpk_data:
        idpk_data = {
            'default_identifier': uuid4(),
        }
    hashed_metadata = hashlib.md5(str(idpk_data).encode()).hexdigest()
    return f'{ledger.idempotency_key}-{quantity}-{hashed_metadata}'


def find_legacy_initial_transactions():
    """
    Heuristic to identify "legacy" initial transactions.

    An initial transaction is one that has the following traits:
    * Is chronologically the first transaction for a Ledger.
    * Contains a hint in its idempotency key which indicates that it is an initial deposit.
    * Has a positive quantity.

    A legacy initial transaction is one that has the following additional traits:
    * does not have a related Deposit.
    """
    # All transactions which are chronologically the first in their respective ledgers.
    first_transactions = Transaction.objects.annotate(
        first_tx_uuid=Window(
            expression=FirstValue('uuid'),
            partition_by=['ledger'],
            order_by=F('created').asc(),  # "first chronologically" above means first created.
        ),
    ).filter(uuid=F('first_tx_uuid'))

    # Further filter first_transactions to find ones that qualify as _initial_ and _legacy_.
    legacy_initial_transactions = first_transactions.filter(
        # Traits of an _initial_ deposit:
        idempotency_key__contains=INITIAL_DEPOSIT_TRANSACTION_SLUG,
        quantity__gte=0,
        # Traits of a _legacy_ initial deposit:
        deposit__isnull=True,
    )
    return legacy_initial_transactions
