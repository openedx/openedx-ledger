"""
Common utility functions that don't create/update/destroy business objects.
"""
import hashlib
from uuid import uuid4

from .constants import (
    INITIAL_DEPOSIT_TRANSACTION_SLUG,
    LEDGER_DEFAULT_IDEMPOTENCY_KEY_PREFIX,
    LEDGERED_SUBSIDY_IDEMPOTENCY_KEY_PREFIX,
)
    

TRANSACTION_METADATA_KEYS = ['opportunity_id', 'request_user', 'request_timestamp', 'initial', 'etc...']


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

    May do something like:
    idpk_data = {k: metadata[k] for k in TRANSACTION_METADATA_KEYS if k in metadata}
    if not idpk_data:
        idpk_data = {
            'default_identifier': uuid4(),
        }

    hashed_metadata = hashlib.md5(str(idpk_data).encode()).hexdigest()
    return f'{ledger.idempotency_key}-{quantity}-{hashed_metadata}'
    """
    if is_initial_deposit:
        return f'{ledger.idempotency_key}-{quantity}-{INITIAL_DEPOSIT_TRANSACTION_SLUG}'
    return NotImplementedError
