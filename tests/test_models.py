#!/usr/bin/env python
"""
Tests for the `openedx-ledger` models.
"""
import uuid

import ddt
import pytest
from django.test import TestCase

from openedx_ledger import models
from openedx_ledger.test_utils.factories import LedgerFactory, ReversalFactory, TransactionFactory


@ddt.ddt
class LedgerBalanceTests(TestCase):
    """
    Tests for the balance of the Ledger model.
    """

    def setUp(self):
        super().setUp()
        self.ledger = LedgerFactory()
        self.initial_transaction = TransactionFactory(
            ledger=self.ledger,
            quantity=100,
        )
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
        self.transaction_5 = TransactionFactory(
            ledger=self.ledger,
            lms_user_id=3,
            content_key="course-v1:edX+test+course.3",
            quantity=-10,
            state=models.TransactionStateChoices.PENDING,
        )

    def test_balance(self):
        """
        Test ``Ledger.balance()``.

        ``committed_only`` is implicitly False.
        """
        result = self.ledger.balance()
        assert result == 100 - 10 - 10 - 10 + 10 - 10

    def test_balance_committed_only(self):
        """
        Test ``Ledger.balance(committed_only=True)``.

        One of the setUp transactions is still pending.
        """
        result = self.ledger.balance(committed_only=True)
        assert result == 100 - 10 - 10 - 10 + 10

    @ddt.data(
        # Test calculating the balance of the entire ledger.
        {
            "transaction_filters": {},
            "expected_balance": 100 - 10 - 10 - 10 + 10 - 10,
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
        queryset = models.Transaction.objects.filter(ledger=self.ledger, **transaction_filters)
        result = self.ledger.subset_balance(queryset)

        assert result == expected_balance

    def test_subset_balance_doesnt_fail_superset(self,):
        """
        Test Ledger.subset_balance() doesn't fail when given a set of transactions that are a superset of
        Ledger.transactions.
        """
        assert self.ledger.subset_balance(models.Transaction.objects.all()) == self.ledger.balance()

    def test_balance_excludes_failed_transactions(self):
        """
        Failed transations should not be included in the balance calculation.
        """
        _ = TransactionFactory(
            ledger=self.ledger,
            lms_user_id=2,
            content_key="course-v1:edX+test+course.2",
            quantity=-55,
            state=models.TransactionStateChoices.FAILED,
        )
        expected_balance = 100 - 10 - 10 - 10 + 10 - 10

        self.assertEqual(self.ledger.balance(), expected_balance)

    def test_idempotency_key_is_generated(self):
        """
        Tests that Ledger.save() will create an idempotency_key
        if none exists.
        """
        my_ledger = LedgerFactory(idempotency_key=None)
        my_ledger.save()

        self.assertIsNotNone(my_ledger.idempotency_key)


class LedgerLockTests(TestCase):
    """
    Test the locking mechanisms for ledgers.
    """
    def setUp(self):
        super().setUp()

        self.ledger = LedgerFactory()
        self.other_ledger = LedgerFactory()

    def test_acquire_lock_release_lock(self):
        """
        Create one hypothetical sequence consisting of three actors and two ledgers.  Each Ledger should only allow one
        lock to be grabbed at a time.
        """
        # Simple case, acquire lock on first ledger.
        lock_1 = self.ledger.acquire_lock()
        assert lock_1  # Non-null means the lock was successfully acquired.
        # A second actor attempts to acquire lock on first ledger, but it's already locked.
        lock_2 = self.ledger.acquire_lock()
        assert lock_2 is None
        # A third actor attempts to acquire lock on second ledger, should work even though first ledger is locked.
        lock_3 = self.other_ledger.acquire_lock()
        assert lock_3
        assert lock_3 != lock_1
        # After releasing the first lock, the second actor should have success.
        self.ledger.release_lock()
        lock_2 = self.ledger.acquire_lock()
        assert lock_2
        # Finally, the third actor releases the lock on the second ledger.
        self.other_ledger.release_lock()

    def test_lock_contextmanager_happy(self):
        """
        Ensure the lock contextmanager does not raise an exception if the ledger is not locked.
        """
        with self.ledger.lock():
            pass

    def test_lock_contextmanager_already_locked(self):
        """
        Ensure the lock contextmanager raises LedgerLockAttemptFailed if the ledger is locked.
        """
        self.ledger.acquire_lock()
        with pytest.raises(models.LedgerLockAttemptFailed, match=r"Failed to acquire lock.*"):
            with self.ledger.lock():
                pass


class TestExternalFulfillmentAndReference(TestCase):
    """
    Tests for the ExternalFulillmentProvider and ExternalTransactionReference models.
    """
    @classmethod
    def setUpTestData(cls):
        """
        Set up some test objects.
        """
        super().setUpTestData()

        cls.provider = models.ExternalFulfillmentProvider.objects.create(
            name='My provider',
            slug='my-provider',
        )
        cls.ledger = LedgerFactory()
        cls.initial_transaction = TransactionFactory(
            ledger=cls.ledger,
            quantity=100,
        )

    def test_simple_provider_stuff(self):
        """
        Test we can str() these.
        """
        self.assertIn('my-provider', str(self.provider))
        self.assertIn('My provider', str(self.provider))

    def test_external_reference(self):
        """
        Test that we can create an external transaction reference.
        """
        transaction = TransactionFactory(
            ledger=self.ledger,
        )
        external_id = str(uuid.uuid4())
        external_reference = models.ExternalTransactionReference.objects.create(
            transaction=transaction,
            external_fulfillment_provider=self.provider,
            external_reference_id=external_id,
        )

        self.assertIn(external_id, str(external_reference))
