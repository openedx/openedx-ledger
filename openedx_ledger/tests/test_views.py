"""
Tests for the base views in the openedx_ledger app
"""
from unittest.mock import MagicMock

import pytest
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from openedx_ledger.models import Reversal, TransactionStateChoices
from openedx_ledger.signals.signals import TRANSACTION_REVERSED
from openedx_ledger.test_utils.factories import LedgerFactory, ReversalFactory, TransactionFactory


@pytest.mark.django_db
class ViewTestBases(APITestCase, TestCase):
    """
    Base class for view tests, includes helper methods for creating test data and formatting urls
    """

    def setUp(self):
        super().setUp()
        # User.objects.get_or_create(username='testuser')[0]
        self.client.force_login(User.objects.get_or_create(username='testuser', is_superuser=True, is_staff=True)[0])

        self.ledger = LedgerFactory()
        self.fulfillment_identifier = 'foobar'
        self.transaction = TransactionFactory(
            ledger=self.ledger,
            quantity=100,
            fulfillment_identifier=self.fulfillment_identifier
        )

    def get_reverse_transaction_url(self, transaction_id):
        """
        helper method to get the url for the reverse transaction view
        """
        return reverse('admin:reverse_transaction', args=(transaction_id,))


@pytest.mark.django_db
class ReverseTransactionViewTests(ViewTestBases):
    """
    Tests for the reverse transaction view
    """

    def test_reverse_transaction_view_get(self):
        """
        Test expected behaviors of the reverse transaction view get request
        """
        url = self.get_reverse_transaction_url(self.transaction.uuid)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Assert that the reversal confirmation form is returned in the get response
        assert b'This action will unenroll the learner AND refund the credit' in response.content

    def test_reverse_transaction_view_post(self):
        """
        Test expected behaviors of posting to the reverse transaction view
        """
        signal_received = MagicMock()
        TRANSACTION_REVERSED.connect(signal_received)

        # Assert that no Transaction Reversal objects exist
        assert Reversal.objects.count() == 0
        url = self.get_reverse_transaction_url(self.transaction.uuid)
        response = self.client.post(url)
        # Assert that a successful post will redirect to the admin transaction editing page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/admin/openedx_ledger/transaction/{self.transaction.uuid}/change/')

        # Assert that the transaction reversal was created
        self.assertEqual(self.transaction.reversal, Reversal.objects.first())

        # Assert that the transaction reversal signal was sent and received
        signal_received.assert_called()

    def test_reverse_transaction_view_post_with_existing_reversal(self):
        """
        Test expected behaviors of POSTing to the reverse transaction view when a reversal already exists
        """
        signal_received = MagicMock()
        TRANSACTION_REVERSED.connect(signal_received)

        assert Reversal.objects.count() == 0
        ReversalFactory(transaction=self.transaction)

        url = self.get_reverse_transaction_url(self.transaction.uuid)
        response = self.client.post(url)

        # Assert that the post request returns a 400 status code
        self.assertEqual(response.status_code, 400)
        # Assert that the response contains the expected error message
        self.assertEqual(response.content, b'Transaction Reversal already exists')

        # Assert that the transaction reversal signal was not sent or received
        signal_received.assert_not_called()

    def test_reverse_transaction_view_get_with_reversal_already_exists(self):
        """
        Test expected behaviors of the reverse transaction view GET request when a reversal already exists
        """
        assert Reversal.objects.count() == 0
        ReversalFactory(transaction=self.transaction)

        url = self.get_reverse_transaction_url(self.transaction.uuid)
        response = self.client.get(url)

        # Assert that the get request returns a 400 status code
        self.assertEqual(response.status_code, 400)
        # Assert that the response contains the expected error message
        self.assertEqual(response.content, b'Transaction Reversal already exists')

    def test_reverse_transaction_view_post_with_non_committed_transaction(self):
        """
        Test expected behaviors of POSTing to the reverse transaction view
        when the transaction is not committed
        """
        signal_received = MagicMock()
        TRANSACTION_REVERSED.connect(signal_received)

        self.transaction.state = TransactionStateChoices.PENDING
        self.transaction.save()

        assert Reversal.objects.count() == 0

        url = self.get_reverse_transaction_url(self.transaction.uuid)
        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content,
            b'Transaction Reversal failed: '
            b'Cannot reverse transaction because it is not in a committed state.'
        )

        signal_received.assert_not_called()
        assert Reversal.objects.count() == 0
