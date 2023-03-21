#!/usr/bin/env python
"""
Tests for the `openedx-ledger` models.
"""
import ddt
from django.test import TestCase

from openedx_ledger.models import Transaction
from openedx_ledger.test_utils.factories import LedgerFactory, ReversalFactory, TransactionFactory


@ddt.ddt
class LedgerTests(TestCase):
    """
    Tests for the Ledger model.
    """

    def setUp(self):
        self.ledger = LedgerFactory()
        self.transaction_1 = TransactionFactory(ledger=self.ledger, quantity=100)
        self.transaction_2 = TransactionFactory(
            ledger=self.ledger, lms_user_id=1, content_key="course-v1:edX+test+course.1", quantity=-10
        )
        self.transaction_3 = TransactionFactory(
            ledger=self.ledger, lms_user_id=1, content_key="course-v1:edX+test+course.2", quantity=-10
        )
        self.transaction_4 = TransactionFactory(
            ledger=self.ledger, lms_user_id=2, content_key="course-v1:edX+test+course.2", quantity=-10
        )
        self.reversal_1 = ReversalFactory(
            transaction=self.transaction_4,
            quantity=10,
        )

        self.other_ledger = LedgerFactory()
        self.other_transaction = TransactionFactory(ledger=self.other_ledger, quantity=100)

    def test_balance(self):
        """
        Test Ledger.balance().
        """
        result = self.ledger.balance()
        assert result == 100 - 10 - 10 - 10 + 10

    @ddt.data(
        # Test calculating the balance of the entire ledger.
        {
            "transaction_filters": {},
            "expected_balance": 100 - 10 - 10 - 10 + 10,
        },
        # Test calculating the balance of a user subset.
        {
            "transaction_filters": {"lms_user_id": 1},
            "expected_balance": -10 - 10,
        },
        # Test calculating the balance of a user subset, reversal case.
        {
            "transaction_filters": {"lms_user_id": 2},
            "expected_balance": -10 + 10,
        },
        # Test calculating the balance of a content subset, with a reversal.
        {
            "transaction_filters": {"content_key": "course-v1:edX+test+course.2"},
            "expected_balance": -10 - 10 + 10,
        },
    )
    @ddt.unpack
    def test_subset_balance(self, transaction_filters, expected_balance):
        """
        Test Ledger.subset_balance().
        """
        result = self.ledger.subset_balance(Transaction.objects.filter(ledger=self.ledger, **transaction_filters))
        assert result == expected_balance

    def test_subset_balance_doesnt_fail_superset(self,):
        """
        Test Ledger.subset_balance() doesn't fail when given a set of transactions that are a superset of
        Ledger.transactions.
        """
        assert self.ledger.subset_balance(Transaction.objects.all()) == self.ledger.balance()
