"""
Tests for the openedx_ledger Python API.
"""
import uuid

import pytest

from openedx_ledger import api
from openedx_ledger.models import AdjustmentReasonChoices, TransactionStateChoices, UnitChoices


@pytest.mark.django_db
def test_create_ledger_happy_path():
    ledger = api.create_ledger(unit=UnitChoices.USD_CENTS, idempotency_key='my-happy-ledger')
    assert ledger.balance() == 0

    api.create_transaction(ledger, quantity=5000, idempotency_key='tx-1', state=TransactionStateChoices.CREATED)
    assert ledger.balance() == 5000

    tx_2 = api.create_transaction(ledger, quantity=5000, idempotency_key='tx-2', state=TransactionStateChoices.CREATED)
    assert ledger.balance() == 10000

    tx_2.state = TransactionStateChoices.COMMITTED
    tx_2.save()

    api.reverse_full_transaction(tx_2, idempotency_key='reversal-1')
    assert ledger.balance() == 5000

    other_ledger = api.create_ledger(unit=UnitChoices.USD_CENTS, idempotency_key='my-happy-ledger')
    assert ledger == other_ledger


@pytest.mark.django_db
def test_no_negative_balance():
    ledger = api.create_ledger(unit=UnitChoices.USD_CENTS, idempotency_key='my-other-ledger')
    assert ledger.balance() == 0

    with pytest.raises(
        api.LedgerBalanceExceeded,
        match="A Transaction was not created because it would exceed the ledger balance."
    ):
        api.create_transaction(ledger, quantity=-1, idempotency_key='tx-1', state=TransactionStateChoices.CREATED)

    api.create_transaction(ledger, quantity=999, idempotency_key='tx-2', state=TransactionStateChoices.CREATED)
    with pytest.raises(
        api.LedgerBalanceExceeded,
        match="A Transaction was not created because it would exceed the ledger balance."
    ):
        api.create_transaction(ledger, quantity=-1000, idempotency_key='tx-3', state=TransactionStateChoices.CREATED)


@pytest.mark.django_db
def test_multiple_reversals():
    ledger = api.create_ledger(unit=UnitChoices.USD_CENTS, idempotency_key='my-other-ledger')
    assert ledger.balance() == 0

    tx_1 = api.create_transaction(ledger, quantity=5000, idempotency_key='tx-1', state=TransactionStateChoices.CREATED)
    assert ledger.balance() == 5000

    tx_1.state = TransactionStateChoices.COMMITTED
    tx_1.save()

    reversal = api.reverse_full_transaction(tx_1, idempotency_key='reversal-1')
    assert ledger.balance() == 0

    with pytest.raises(Exception):
        api.reverse_full_transaction(tx_1, idempotency_key='reversal-2')

    third_reversal = api.reverse_full_transaction(tx_1, idempotency_key='reversal-1')
    assert ledger.balance() == 0
    assert reversal == third_reversal


@pytest.mark.django_db
def test_adjustment_creation_happy_path():
    ledger = api.create_ledger(unit=UnitChoices.USD_CENTS, idempotency_key='my-happy-ledger')
    assert ledger.balance() == 0

    tx_of_interest = api.create_transaction(
        ledger,
        quantity=5000,
        idempotency_key='tx_of_interest',
        state=TransactionStateChoices.COMMITTED,
    )

    assert ledger.balance() == 5000

    test_uuid = uuid.uuid4()

    adjustment = api.create_adjustment(
        ledger,
        adjustment_uuid=test_uuid,
        quantity=-100,
        idempotency_key='unique-string-for-transaction',
        reason=AdjustmentReasonChoices.POOR_CONTENT_FIT,
        notes='Long form notes about this record',
        transaction_of_interest=tx_of_interest,
        some_key='some_value',  # tests that metadata is recorded on the adjustment's transaction
    )

    assert adjustment.uuid == test_uuid
    assert adjustment.transaction.state == TransactionStateChoices.COMMITTED
    assert adjustment.transaction.uuid != tx_of_interest.uuid
    assert adjustment.transaction.idempotency_key == 'unique-string-for-transaction'
    assert adjustment.adjustment_quantity == -100
    assert adjustment.reason == AdjustmentReasonChoices.POOR_CONTENT_FIT
    assert adjustment.notes == 'Long form notes about this record'
    assert adjustment.transaction_of_interest == tx_of_interest
    assert adjustment.transaction.metadata == {
        'some_key': 'some_value',
    }
    assert ledger.balance() == 4900


@pytest.mark.django_db
def test_adjustment_creation_balance_exceeded():
    ledger = api.create_ledger(unit=UnitChoices.USD_CENTS, idempotency_key='my-happy-ledger')

    # Add a little bit of adjustment balance first
    first_adjustment = api.create_adjustment(
        ledger,
        quantity=50,
        reason=AdjustmentReasonChoices.POOR_CONTENT_FIT,
        notes='Long form notes about this record',
    )
    assert ledger.balance() == 50
    assert f'{ledger.uuid}' in str(first_adjustment.transaction.idempotency_key)

    with pytest.raises(
        api.AdjustmentCreationError,
        match="A Transaction was not created because it would exceed the ledger balance."
    ):
        api.create_adjustment(
            ledger,
            quantity=-100,
            reason=AdjustmentReasonChoices.POOR_CONTENT_FIT,
            notes='Long form notes about this record',
        )
    assert ledger.balance() == 50
    assert ledger.transactions.all().count() == 1
