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

from openedx_ledger.utils import create_idempotency_key_for_ledger


class UnitChoices:
    USD_CENTS = 'usd_cents'
    SEATS = 'seats'
    CHOICES = (
        (USD_CENTS, 'U.S. Dollar (Cents)'),
        (SEATS, 'Seats in a course'),
    )


class TransactionStateChoices:
    """
    Lifecycle states for a ledger transaction.

    CREATED
        Indicates that the transaction has only just been created, and should be the default state.

    PENDING
        Indicates that an attempt is being made to redeem the content in the target LMS.

    COMMITTED
        Indicates that the content has been redeemed, and a reference to the redemption result (often an enrollment ID)
        is stored in the reference_id field of the transaction.
    """

    CREATED = 'created'
    PENDING = 'pending'
    COMMITTED = 'committed'
    CHOICES = (
        (CREATED, 'Created'),
        (PENDING, 'Pending'),
        (COMMITTED, 'Committed'),
    )


class TransactionReferenceTypeChoices:
    """
    Enumerate different choices for the type of Transaction reference_id.

    The reference_id of a Transaction may refer to different things depending on the type of content being enrolled and
    the time of enrollment.  These options allow us to be explicit about the type of identifier used for that redeption
    result.
    """

    LEARNER_CREDIT_ENTERPRISE_COURSE_ENROLLMENT_ID = 'learner_credit_enterprise_course_enrollment_id'
    CHOICES = (
        (LEARNER_CREDIT_ENTERPRISE_COURSE_ENROLLMENT_ID, 'LearnerCreditEnterpriseCourseEnrollment ID'),
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
    A ledger to which you can add or remove value, associated with a single subsidy plan.

    All value quantities associated with this ledger uniformly share the same unit, established in the `unit` field of
    the ledger.  This enables simple balancing using `sum()` functions, helping to prevent bugs caused by unit
    conversions, and improving performance on the critical balance() method.

    .. no_pii:
    """

    # https://docs.djangoproject.com/en/3.2/ref/databases/#mysql-character-fields
    # is why max_length is 255 for the fields below.

    # also note: if you do something that raises an exception and causes the record to not persist,
    # idempotency is not preserved (i.e. you could do an action with the same key in a way that
    # _does not_ raise an exception and get a different, non exception, output).
    idempotency_key = models.CharField(
        max_length=255,
        blank=True,
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

    def subset_balance(self, transactions_queryset):
        """
        Calculate the current balance of the ledger, optionally on a subset of transactions.

        WARNING: The queryset must be a strict subset of self.transactions.  If not, then the return value will
        represent only the set intersection of the given transactions_queryset and self.transactions.

        Args:
            transaction_subset (queryset of openedx_ledger.models.Transaction):
                Transactions to evaluate for the balance calculation.

        Returns:
            int: The total balance of all or a subset of transactions in this ledger.  Possibly a negative value if the
            only transactions evaluated are ones that represent un-reversed enrollment fulfillments.
        """
        with atomic():
            transactions_queryset = transactions_queryset.filter(ledger=self).select_related('reversal')
            agg = transactions_queryset.annotate(
                row_total=Coalesce(models.Sum('quantity'), 0) + Coalesce(models.Sum('reversal__quantity'), 0)
            )
            agg = agg.aggregate(total_quantity=Coalesce(models.Sum('row_total'), 0))
            return agg['total_quantity']

    def balance(self):
        """
        Calculate the current balance of the ledger.

        Returns:
            int: The total balance of all transactions in this ledger.  Always positive.
        """
        return self.subset_balance(Transaction.objects.filter(ledger=self))

    def save(self, *args, **kwags):
        """
        Sets the idempotency_key for the ledger if it is currently null.
        """
        if not self.idempotency_key:
            self.idempotency_key = create_idempotency_key_for_ledger()
        super().save(*args, **kwags)

    def __str__(self):
        """
        Return string representation of this ledger, visible in logs, django admin, etc.
        """
        return f'<Ledger uuid={self.uuid},\nidempotency_key={self.idempotency_key}>'


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
    state = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        choices=TransactionStateChoices.CHOICES,
        default=TransactionStateChoices.CREATED,
        db_index=True,
    )


class Transaction(BaseTransaction):
    """
    Represents value moving in or out of the ledger.

    Transactions (and reversals) are immutable after entering the committed state.  This immutability helps maintain a
    complete and robust history of value changes to the ledger, a trait which we rely on to calculate the ledger
    balance.

    Relatedly, we intentionally avoid persisting aggregates, reinforcing the transactions themselves as the
    only source of truth.

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
    content_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text=(
            "The globally unique content identifier.  Joinable with ContentMetadata.content_key in enterprise-catalog."
        )
    )
    reference_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text=(
            "The identifier of the item acquired via the transaction. "
            "e.g. a LearnerCreditEnterpriseCourseEnrollment ID."
        ),
    )
    reference_type = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        # Since null=True we do not need a default choice.  Furthermore, a default doesn't make sense anyway because
        # there's no reasonable heuristic to guess the type before runtime.
        choices=TransactionReferenceTypeChoices.CHOICES,
        db_index=True,
        help_text="The type of identifier used for `reference_id`.",
    )
    subsidy_access_policy_uuid = models.UUIDField(
        blank=True,
        null=True,
        help_text="A reference to the subsidy access policy which was used to create a transaction for the content."
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
