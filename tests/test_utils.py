"""
Tests for the utils.py module.
"""
from itertools import chain, combinations

from django.test import TestCase

from openedx_ledger import utils
from openedx_ledger.constants import INITIAL_DEPOSIT_TRANSACTION_SLUG
from openedx_ledger.test_utils.factories import AdjustmentFactory, DepositFactory, LedgerFactory, TransactionFactory


def powerset(iterable):
    """
    https://docs.python.org/3/library/itertools.html#itertools-recipes
    powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)

    Be warned, this gets very big, very fast, with higher
    cardinatlities of `iterable`.  This function asserts that
    no more than 7 things are provided as input.
    """
    s = list(iterable)
    assert len(s) < 8, 'This powerset will be too big'
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))


class TransactionIdempotencyKeyTests(TestCase):
    """
    Tests for the create_idempotency_key_for_transaction function.
    """
    def test_transaction_idempotency_key_varies(self):
        """
        Test that we get unique idempotency keys for
        transactions when changing any of the possible
        subsets of keys against some baseline transaction.
        """
        ledger = LedgerFactory()
        baseline_metadata = {
            key: f'{key}-value-1'
            for key in utils.TRANSACTION_METADATA_KEYS
        }
        baseline_key = utils.create_idempotency_key_for_transaction(
            ledger, 10, **baseline_metadata,
        )

        combos = list(powerset(utils.TRANSACTION_METADATA_KEYS))
        generated_keys = set()
        for combo in combos:
            comparison_metadata = baseline_metadata.copy()
            comparison_metadata.update({
                key: f'{key}-value-2'
                for key in combo
            })
            generated_key = utils.create_idempotency_key_for_transaction(
                ledger=ledger, quantity=10, **comparison_metadata,
            )
            if combo:
                assert baseline_key != generated_key
            else:
                assert baseline_key == generated_key
            generated_keys.add(generated_key)

        assert len(combos) == len(generated_keys)

    def test_initial_deposit_transaction(self):
        """
        Test we get an expected key for the initial transaction of a ledger.
        """
        ledger = LedgerFactory(idempotency_key='ledger-key')

        key = utils.create_idempotency_key_for_transaction(
            ledger, quantity=100, is_initial_deposit=True,
        )
        assert 'ledger-key-100-initial-deposit' == key


class MigrationUtilsTests(TestCase):
    """
    Tests for utils used for migrations.
    """
    def test_find_legacy_initial_transactions(self):
        """
        Test find_legacy_initial_transactions(), used for a data migration to backfill initial deposits.
        """
        ledgers = [
            (LedgerFactory(), False),
            (LedgerFactory(), False),
            (LedgerFactory(), True),
            (LedgerFactory(), False),
            (LedgerFactory(), True),
        ]
        expected_legacy_initial_transactions = []
        for ledger, create_initial_deposit in ledgers:
            # Simulate a legacy initial transaction (i.e. transaction WITHOUT a deposit).
            initial_transaction = TransactionFactory(
                ledger=ledger,
                idempotency_key=INITIAL_DEPOSIT_TRANSACTION_SLUG,
                quantity=100,
            )
            if create_initial_deposit:
                # Make it a modern initial deposit by creating a related Deposit.
                DepositFactory(
                    ledger=ledger,
                    transaction=initial_transaction,
                    desired_deposit_quantity=initial_transaction.quantity,
                )
            else:
                # Keep it a legacy initial deposit by NOT creating a related Deposit.
                expected_legacy_initial_transactions.append(initial_transaction)
            # Throw in a few spend, deposit, and adjustment transactions for fun.
            TransactionFactory(ledger=ledger, quantity=-10)
            TransactionFactory(ledger=ledger, quantity=-10)
            DepositFactory(ledger=ledger, desired_deposit_quantity=50)
            tx_to_adjust = TransactionFactory(ledger=ledger, quantity=-5)
            AdjustmentFactory(ledger=ledger, adjustment_quantity=5, transaction_of_interest=tx_to_adjust)

        actual_legacy_initial_transactions = utils.find_legacy_initial_transactions()
        assert set(actual_legacy_initial_transactions) == set(expected_legacy_initial_transactions)
