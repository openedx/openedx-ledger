"""
Test factories for openedx-ledger models.
"""
from uuid import uuid4

import factory

from openedx_ledger.models import (
    Adjustment,
    ExternalFulfillmentProvider,
    ExternalTransactionReference,
    Ledger,
    Reversal,
    Transaction,
    TransactionStateChoices,
    UnitChoices,
)


class LedgerFactory(factory.django.DjangoModelFactory):
    """
    Test factory for the `Ledger` model.

    By default, no transactions are created for this test Ledger.
    """
    class Meta:
        model = Ledger

    uuid = factory.LazyFunction(uuid4)
    idempotency_key = factory.Faker("lexify", text="subsidy-????")
    unit = UnitChoices.USD_CENTS


class TransactionFactory(factory.django.DjangoModelFactory):
    """
    Test factory for the `Transaction` model.
    """
    class Meta:
        model = Transaction

    uuid = factory.LazyFunction(uuid4)
    idempotency_key = factory.LazyFunction(uuid4)
    state = TransactionStateChoices.COMMITTED
    quantity = factory.Faker("random_int", min=-100000, max=-100)
    ledger = factory.Iterator(Ledger.objects.all())
    lms_user_id = factory.Faker("random_int", min=1, max=1000)
    lms_user_email = factory.Faker("email")
    content_key = factory.Faker("lexify", text="???+?????101")
    content_title = factory.Faker("lexify", text="???: ?????? ???")


class ExternalFulfillmentProviderFactory(factory.django.DjangoModelFactory):
    """
    Test factory for the `ExternalFulfillmentProvider` model.
    """
    class Meta:
        model = ExternalFulfillmentProvider

    name = factory.Faker("company")
    slug = factory.Faker("slug")


class ExternalTransactionReferenceFactory(factory.django.DjangoModelFactory):
    """
    Test factory for the `ExternalTransactionReferenceFactory` model.
    """
    class Meta:
        model = ExternalTransactionReference

    external_reference_id = factory.Faker("lexify", text="????-????-????-????")
    transaction = factory.Iterator(Transaction.objects.all())
    external_fulfillment_provider = factory.Iterator(ExternalFulfillmentProvider.objects.all())


class ReversalFactory(factory.django.DjangoModelFactory):
    """
    Test factory for the `Reversal` model.
    """
    class Meta:
        model = Reversal

    uuid = factory.LazyFunction(uuid4)
    transaction = factory.Iterator(Transaction.objects.all())
    idempotency_key = factory.LazyFunction(uuid4)
    state = TransactionStateChoices.COMMITTED
    quantity = factory.Faker("random_int", min=100, max=10000)


class AdjustmentFactory(factory.django.DjangoModelFactory):
    """
    Test factory for the `Adjustment` model.
    """
    class Meta:
        model = Adjustment

    ledger = factory.SubFactory(LedgerFactory)
    transaction = factory.SubFactory(TransactionFactory)
    adjustment_quantity = factory.Faker("random_int", min=100, max=10000)
