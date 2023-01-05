"""
Admin configuration for openedx_ledger models.
"""
from django.contrib import admin

from openedx_ledger import models


@admin.register(models.Ledger)
class LedgerAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Ledger model.
    """

    class Meta:
        """
        Metaclass for LedgerAdmin.
        """

        model = models.Ledger

    readonly_fields = ('idempotency_key', 'unit', 'balance')
    list_display = ('idempotency_key', 'unit', 'uuid')
    fieldsets = (
        (None, {
            'fields': ('idempotency_key', 'unit',)
        }),
        ('Advanced options, yo!', {
            'classes': ('collapse',),
            'fields': ('balance', 'metadata'),
        }),
    )

    def balance(self, obj):
        """
        Passthrough function to calculate the ledger balance.
        """
        return obj.balance()


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Transaction model.
    """

    class Meta:
        """
        Metaclass for TransactionAdmin.
        """

        model = models.Transaction
        fields = '__all__'


@admin.register(models.Reversal)
class ReversalAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Reversal model.
    """

    class Meta:
        """
        Metaclass for ReversalAdmin.
        """

        model = models.Reversal
        fields = '__all__'
