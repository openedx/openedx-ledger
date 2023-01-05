"""
Common utility functions that don't create/update/destroy business objects.
"""
import hashlib
from uuid import uuid4

TRANSACTION_METADATA_KEYS = ['opportunity_id', 'request_user', 'request_timestamp', 'etc...']


def create_idempotency_key_for_subsidy(subsidy_record):
    """
    TODO: write docstring.
    """
    return f'subsidy-{subsidy_record.uuid}'


def create_idempotency_key_for_transaction(subsidy_record, quantity, **metadata):
    """
    Create a key that allows a transaction to be executed idempotently.
    """
    idpk_data = {k: metadata[k] for k in TRANSACTION_METADATA_KEYS if k in metadata}
    if not idpk_data:
        idpk_data = {
            'default_identifier': uuid4(),
        }

    key_for_subsidy = create_idempotency_key_for_subsidy(subsidy_record)
    hashed_metadata = hashlib.md5(str(idpk_data).encode()).hexdigest()
    return f'{key_for_subsidy}-{quantity}-{hashed_metadata}'
