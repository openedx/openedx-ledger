"""
Tests for the openedx_ledger Python API.
"""
import uuid

import pytest

from openedx_ledger import api
from openedx_ledger.models import AdjustmentReasonChoices, Deposit, Transaction, TransactionStateChoices, UnitChoices
from openedx_ledger.test_utils.factories import SalesContractReferenceProviderFactory


@pytest.mark.django_db
def test_create_ledger_happy_path():
    sales_reference_kwargs = {
        "sales_contract_reference_id": str(uuid.uuid4()),
        "sales_contract_reference_provider": SalesContractReferenceProviderFactory(),
    }

    ledger = api.create_ledger(unit=UnitChoices.USD_CENTS, idempotency_key='my-happy-ledger', **sales_reference_kwargs)
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
def test_create_ledger_with_initial_deposit():
    """
    Simple test case to make sure ledger creation API is capable of creating initial Deposit and Transaction objects.
    """
    ledger = api.create_ledger(
        unit=UnitChoices.USD_CENTS,
        idempotency_key='my-happy-ledger',
        initial_deposit=100,
        sales_contract_reference_id=str(uuid.uuid4()),
        sales_contract_reference_provider=SalesContractReferenceProviderFactory(),
    )
    assert ledger.balance() == 100
    assert ledger.total_deposits() == 100

    # Check that a transaction was created.
    assert len(Transaction.objects.filter(ledger=ledger)) == 1
    assert Transaction.objects.filter(ledger=ledger)[0].quantity == 100

    # Check that a deposit was created.
    assert len(Deposit.objects.filter(ledger=ledger)) == 1
    assert Deposit.objects.filter(ledger=ledger)[0].desired_deposit_quantity == 100


@pytest.mark.django_db
def test_create_ledger_missing_sales_contract_reference():
    """
    Ledger creation API fails if initial_deposit is non-zero but no sales contract reference is provided.
    """
    with pytest.raises(
        api.LedgerCreationError,
        match="both sales_contract_reference_id/provider are required when creating an initial deposit"
    ):
        api.create_ledger(
            unit=UnitChoices.USD_CENTS,
            idempotency_key='my-happy-ledger',
            initial_deposit=100,
        )


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

    # This function is unfortunately not idempotent. But at least it rolls back any unwanted changes and maintains
    # database integrity.
    with pytest.raises(
        api.AdjustmentCreationError,
        match="UNIQUE constraint failed: openedx_ledger_adjustment",
    ):
        api.create_adjustment(
            ledger,
            adjustment_uuid=test_uuid,
            quantity=-100,
            idempotency_key='unique-string-for-transaction',
            reason=AdjustmentReasonChoices.POOR_CONTENT_FIT,
            notes='Long form notes about this record',
            transaction_of_interest=tx_of_interest,
            some_key='some_value',  # tests that metadata is recorded on the adjustment's transaction
        )

    # No change after 2nd attempt.
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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "idempotency_key,expected_idempotency_key_substring",
    [
        ('foo-bar', 'foo-bar'),
        (None, 'sales-contract'),
    ],
)
def test_deposit_creation_happy_path(idempotency_key, expected_idempotency_key_substring):
    ledger = api.create_ledger(unit=UnitChoices.USD_CENTS, idempotency_key='my-happy-ledger')
    assert ledger.balance() == 0

    test_deposit_uuid = uuid.uuid4()
    test_sales_contract_reference_id = str(uuid.uuid4())
    test_sales_contract_reference_provider = SalesContractReferenceProviderFactory()

    deposit = api.create_deposit(
        ledger,
        deposit_uuid=test_deposit_uuid,
        quantity=100,
        sales_contract_reference_id=test_sales_contract_reference_id,
        sales_contract_reference_provider=test_sales_contract_reference_provider,
        idempotency_key=idempotency_key,
        some_key='some_value',  # tests that metadata is recorded on the adjustment's transaction
    )

    assert deposit.uuid == test_deposit_uuid
    assert deposit.transaction.quantity == 100
    assert deposit.transaction.state == TransactionStateChoices.COMMITTED
    assert expected_idempotency_key_substring in deposit.transaction.idempotency_key
    assert deposit.desired_deposit_quantity == 100
    assert deposit.sales_contract_reference_id == test_sales_contract_reference_id
    assert deposit.sales_contract_reference_provider == test_sales_contract_reference_provider
    assert deposit.transaction.metadata == {
        'some_key': 'some_value',
    }
    assert ledger.balance() == 100

    # This function is unfortunately not idempotent. But at least it rolls back any unwanted changes and maintains
    # database integrity.
    with pytest.raises(
        api.DepositCreationError,
        match="UNIQUE constraint failed: openedx_ledger_deposit.transaction_id",
    ):
        api.create_deposit(
            ledger,
            deposit_uuid=test_deposit_uuid,
            quantity=100,
            sales_contract_reference_id=test_sales_contract_reference_id,
            sales_contract_reference_provider=test_sales_contract_reference_provider,
            idempotency_key=idempotency_key,
            some_key='some_value',  # tests that metadata is recorded on the adjustment's transaction
        )

    # No change after 2nd attempt.
    assert ledger.balance() == 100


@pytest.mark.django_db
def test_deposit_creation_error():
    ledger = api.create_ledger(unit=UnitChoices.USD_CENTS, idempotency_key='my-happy-ledger')
    assert ledger.balance() == 0

    test_deposit_uuid = uuid.uuid4()
    test_sales_contract_reference_id = str(uuid.uuid4())
    test_sales_contract_reference_provider = SalesContractReferenceProviderFactory()

    with pytest.raises(
        api.DepositCreationError,
        match="Deposits must be positive"
    ):
        api.create_deposit(
            ledger,
            deposit_uuid=test_deposit_uuid,
            quantity=-100,  # negative deposits not allowed, so we expect this to throw an exception.
            sales_contract_reference_id=test_sales_contract_reference_id,
            sales_contract_reference_provider=test_sales_contract_reference_provider,
            idempotency_key='unique-string-for-transaction',
            some_key='some_value',  # tests that metadata is recorded on the adjustment's transaction
        )

    # Make sure the ledger balance did not change.
    assert ledger.balance() == 0
