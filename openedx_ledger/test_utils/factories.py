"""
Test factories for openedx-ledger models.
"""
from uuid import uuid4

import factory

from openedx_ledger.models import Ledger, Transaction, TransactionStateChoices, UnitChoices


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
    state = TransactionStateChoices.CREATED
    quantity = factory.Faker("random_int", min=-100000, max=-100)
    ledger = factory.Iterator(Ledger.objects.all())
