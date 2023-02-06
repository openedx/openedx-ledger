"""
edx_ledger models.
"""
from uuid import uuid4

from django.db import models
from django.db.models.functions import Coalesce
from django.db.transaction import atomic
from jsonfield.fields import JSONField
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

# Units on the ledger model - probably yes. TODO: say why
# Unit conversion - price/seat is captured somewhere, is it in here?
# This is currently single-entry - should it be double-entry?
# Do we need an account representing SF, one representing entitlements or enrollments, and the transaction
# moves between those two accounts?
# Are transactions immutable? Yes.
# Let's not persist aggregates - the transactions are the only truth. TODO: say why


class UnitChoices:
    USD_CENTS = 'usd_cents'
    SEATS = 'seats'
    JPY = 'jpy'
    CHOICES = (
        (USD_CENTS, 'U.S. Dollar (Cents)'),
        (SEATS, 'Seats in a course'),
        (JPY, 'Japanese Yen'),
    )


class TimeStampedModelWithUuid(TimeStampedModel):
    """
    Base timestamped model adding a UUID field.
    """

    class Meta:
        """
        Metaclass for TimeStampedModelWithUuid.
        """

        abstract = True

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False,
        unique=True,
    )


class Ledger(TimeStampedModelWithUuid):
    """
    A ledger you can credit and debit, associated with a single subsidy plan.

    .. no_pii:
    """

    # https://docs.djangoproject.com/en/3.2/ref/databases/#mysql-character-fields
    # is why max_length is 255 for the fields below.

    # also note: if you do something that raises an exception and causes the record to not persist,
    # idempotency is not preserved (i.e. you could do an action with the same key in a way that
    # _does not_ raise an exception and get a different, non exception, output).
    idempotency_key = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        unique=True,
    )
    unit = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        choices=UnitChoices.CHOICES,
        default=UnitChoices.USD_CENTS,
        db_index=True,
    )
    metadata = JSONField(
        blank=True,
        null=True,
    )
    history = HistoricalRecords()

    def balance(self):
        """
        Return the current balance of the ledger as an integer.
        """
        with atomic():
            transactions = Transaction.objects.filter(
                ledger=self,
            ).select_related('reversal')
            agg = transactions.annotate(
                row_total=Coalesce(models.Sum('quantity'), 0) + Coalesce(models.Sum('reversal__quantity'), 0)
            )
            agg = agg.aggregate(total_quantity=Coalesce(models.Sum('row_total'), 0))
            return agg['total_quantity']

    def __str__(self):
        """
        Return string representation of this ledger, visible in logs, django admin, etc.
        """
        return self.idempotency_key


class BaseTransaction(TimeStampedModelWithUuid):
    """
    Base class for all models that resemble transactions.
    """

    class Meta:
        """
        Metaclass for BaseTransaction.
        """

        abstract = True

    idempotency_key = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        db_index=True,
    )
    quantity = models.BigIntegerField(
        null=False,
        blank=False,
    )
    metadata = JSONField(
        blank=True,
        null=True,
    )


class Transaction(BaseTransaction):
    """
    Represents a quantity moving in or out of the ledger.  It's purely in USD-cents for now.

    .. no_pii:
    """

    class Meta:
        """
        Metaclass for Transaction.
        """

        unique_together = [('ledger', 'idempotency_key')]

    ledger = models.ForeignKey(
        Ledger,
        related_name='transactions',
        null=True,
        on_delete=models.SET_NULL,
    )
    lms_user_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
    )
    content_uuid = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )
    reference_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text=(
            "The identifier of the item acquired via the transaction."
            "e.g. a course enrollment ID, an entitlement ID, a subscription license ID."
        ),
    )
    history = HistoricalRecords()


class Reversal(BaseTransaction):
    """
    Represents a reversal of some or all of a transaction, but no more.

    .. no_pii:
    """

    class Meta:
        """
        Metaclass for Reversal.
        """

        unique_together = [('transaction', 'idempotency_key')]

    transaction = models.OneToOneField(
        Transaction,
        related_name='reversal',
        null=True,
        on_delete=models.SET_NULL,
    )
    history = HistoricalRecords()
    # Reversal quantities should always have the opposite sign of the transaction (i.e. negative)
    # We have to enforce this somehow...
