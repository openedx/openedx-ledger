"""
Admin configuration for openedx_ledger models.
"""
from django.conf import settings
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import re_path, reverse
from django_object_actions import DjangoObjectActions
from simple_history.admin import SimpleHistoryAdmin

from openedx_ledger import constants, models, views


def can_modify():
    return getattr(settings, 'ALLOW_LEDGER_MODIFICATION', False)


def cents_to_usd_string(balance_in_cents):
    """
    Helper to convert cents as in int to dollars as a
    nicely formatted string.
    """
    return "${:,.2f}".format(float(balance_in_cents) / constants.CENTS_PER_US_DOLLAR)


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

    fields = ('uuid', 'idempotency_key', 'unit', 'balance_usd', 'metadata')
    if can_modify():
        readonly_fields = ('uuid', 'balance_usd')
    else:
        readonly_fields = fields

    # Do not add balance here, it's a computed value.
    list_display = ('uuid', 'unit', 'idempotency_key')

    def balance_usd(self, obj):
        """
        Passthrough function to calculate the ledger balance.
        """
        return cents_to_usd_string(obj.balance())


@admin.register(models.ExternalFulfillmentProvider)
class ExternalFulfillmentProviderAdmin(SimpleHistoryAdmin):
    """
    Admin configuration for the ExternalFulfillmentProvider model.
    """
    class Meta:
        """
        Metaclass for ExternalFulfillmentProviderAdmin.
        """

        model = models.ExternalFulfillmentProvider
        fields = '__all__'

    search_fields = ('name', 'slug',)
    list_display = ('name', 'slug',)


class ExternalTransactionReferenceInlineAdmin(admin.TabularInline):
    """
    Inline admin configuration for the ExternalTransactionReference model.
    """
    model = models.ExternalTransactionReference


@admin.register(models.Transaction)
class TransactionAdmin(DjangoObjectActions, SimpleHistoryAdmin):
    """
    Admin configuration for the Transaction model.
    """

    class Meta:
        """
        Metaclass for TransactionAdmin.
        """

        model = models.Transaction
        fields = '__all__'

    search_fields = (
        'content_key',
        'lms_user_id',
        'uuid',
        'external_reference__external_reference_id',
        'subsidy_access_policy_uuid',
    )
    _all_fields = [
        field.name for field in models.Transaction._meta.get_fields()
        if field.name != 'external_reference'
    ]
    _writable_fields = [
        'fulfillment_identifier',
    ]
    list_display = (
        'uuid',
        'lms_user_id',
        'content_key',
        'subsidy_access_policy_uuid',
        'quantity',
        'state',
        'modified',
        'has_reversal',
    )
    list_filter = (
        'state',
    )

    if can_modify():
        readonly_fields = [
            field_name for field_name in _all_fields
            if field_name not in ['fulfillment_identifier']
        ]
    else:
        readonly_fields = _all_fields
    inlines = [ExternalTransactionReferenceInlineAdmin]

    @admin.display(ordering='reversal', description='Has a reversal')
    def has_reversal(self, obj):
        return bool(obj.get_reversal())

    change_actions = ('reverse_transaction',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('reversal')

    def reverse_transaction(self, request, obj):
        """
        Redirect to the reverse transaction view.
        """
        # url names coming from get_urls are prefixed with 'admin' namespace
        reverse_transaction_url = reverse("admin:reverse_transaction", args=(obj.uuid,))
        return HttpResponseRedirect(reverse_transaction_url)

    reverse_transaction.label = "Unenroll & Refund"
    reverse_transaction.short_description = (
        "Reverse a transaction and unenroll the learner from the platform representation of the course."
    )

    def get_urls(self):
        """
        Returns the additional urls used by DjangoObjectActions.
        """
        customer_urls = [
            re_path(
                r"^([^/]+)/reverse_transaction$",
                self.admin_site.admin_view(views.ReverseTransactionView.as_view()),
                name="reverse_transaction"
            )
        ]
        return customer_urls + super().get_urls()


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
