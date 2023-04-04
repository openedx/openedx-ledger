"""
Admin configuration for openedx_ledger models.
"""
from django.conf import settings
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from openedx_ledger import models


def can_modify():
    getattr(settings, 'ALLOW_LEDGER_MODIFICATION', False)


@admin.register(models.Ledger)
class LedgerAdmin(SimpleHistoryAdmin):
    """
    Admin configuration for the Ledger model.
    """

    class Meta:
        """
        Metaclass for LedgerAdmin.
        """
        model = models.Ledger

    fields = ('uuid', 'idempotency_key', 'unit', 'balance', 'metadata')
    if can_modify():
        readonly_fields = ('uuid', 'balance')
    else:
        readonly_fields = fields

    # Do not add balance here, it's a computed value.
    list_display = ('uuid', 'unit', 'idempotency_key')

    def balance(self, obj):
        """
        Passthrough function to calculate the ledger balance.
        """
        return obj.balance()


@admin.register(models.Transaction)
class TransactionAdmin(SimpleHistoryAdmin):
    """
    Admin configuration for the Transaction model.
    """

    class Meta:
        """
        Metaclass for TransactionAdmin.
        """

        model = models.Transaction
        fields = '__all__'

    search_fields = ('content_key', 'lms_user_id', 'uuid', 'external_reference__external_reference_id',)
    _all_fields = [field.name for field in models.Transaction._meta.get_fields()]
    list_display = ('uuid', 'idempotency_key', 'quantity', 'state',)
    if can_modify():
        readonly_fields = (
            'created',
            'modified',
        )
    else:
        readonly_fields = _all_fields


@admin.register(models.Reversal)
class ReversalAdmin(SimpleHistoryAdmin):
    """
    Admin configuration for the Reversal model.
    """

    class Meta:
        """
        Metaclass for ReversalAdmin.
        """

        model = models.Reversal
        fields = '__all__'
