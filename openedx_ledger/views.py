"""
Views for the openedx_ledger app.
"""
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

from openedx_ledger.api import NonCommittedTransactionError, reverse_full_transaction
from openedx_ledger.models import Transaction

logger = logging.getLogger(__name__)


class ReverseTransactionView(View):
    """
    Admin view for the form responsible for reversing transaction objects and emitting an unenrollment signal.
    """
    template = "edx_ledger/admin/reverse_transaction.html"

    def get(self, request, transaction_id):
        """
        Handle GET request - render "Reverse Transaction" form.

        Arguments:
            request (django.http.request.HttpRequest): Request instance
            transaction_uuid (str): Enterprise Customer UUID

        Returns:
            django.http.response.HttpResponse: HttpResponse
        """
        transaction = Transaction.objects.get(uuid=transaction_id)
        try:
            if transaction.reversal:
                logger.info(
                    f"ReverseTransactionView Error: transaction reversal already exists: {transaction_id}"
                )
                return HttpResponseBadRequest('Transaction Reversal already exists')
        except ObjectDoesNotExist:
            pass

        return render(
            request,
            self.template,
            {'transaction': transaction}
        )

    def post(self, request, transaction_id):
        """
        Handle POST request - handle form submissions.
        """
        logger.info(
            "Reversing transaction and sending admin invoked transaction unenroll signal for transaction: "
            f"{transaction_id}"
        )
        transaction = Transaction.objects.get(uuid=transaction_id)
        # TODO: determine how to generate idempotency key
        try:
            reverse_full_transaction(
                transaction,
                idempotency_key=f"admin-invoked-reverse-{str(transaction.uuid)}"
            )
        except IntegrityError:
            logger.exception(
                f"ReverseTransactionView Error: transaction reversal already exists: {transaction_id}"
            )
            return HttpResponseBadRequest('Transaction Reversal already exists')
        except NonCommittedTransactionError as error:
            logger.exception(
                f"ReverseTransactionView Error: transaction is not in a committed state: {transaction_id}"
            )
            return HttpResponseBadRequest(f'Transaction Reversal failed: {error}')
        url = reverse("admin:openedx_ledger_transaction_change", args=(transaction_id,))
        return HttpResponseRedirect(url)
