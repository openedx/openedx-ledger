"""
Admin configuration for openedx_ledger models.
"""
from django import forms
from django.conf import settings
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import re_path, reverse
from django_object_actions import DjangoObjectActions
from simple_history.admin import SimpleHistoryAdmin

from openedx_ledger import api, constants, models, views


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
    # The autocomplete_fields of AdjustmentAdmin include the ledger field,
    # which in turn requires that we define here that ledgers are
    # searchable by uuid.
    search_fields = [
        'uuid',
    ]
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


class AdjustmentInlineAdmin(admin.TabularInline):
    """
    Inline admin configuration for the Adjustment model.
    """
    model = models.Adjustment
    fk_name = 'transaction'
    fields = [
        'uuid',
        'get_quantity_usd',
        'reason',
        'created',
        'modified',
    ]
    readonly_fields = fields
    show_change_link = True

    @admin.display(description='Amount in U.S. Dollars')
    def get_quantity_usd(self, obj):
        if not obj._state.adding:  # pylint: disable=protected-access
            return cents_to_usd_string(obj.adjustment_quantity)
        return None


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
        if field.name not in {'external_reference', 'adjustment', 'adjustment_of_interest'}
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

    def get_inlines(self, request, obj):
        if obj and not obj._state.adding:  # pylint: disable=protected-access
            return [AdjustmentInlineAdmin, ExternalTransactionReferenceInlineAdmin]
        return [ExternalTransactionReferenceInlineAdmin]

    @admin.display(ordering='reversal', description='Has a reversal')
    def has_reversal(self, obj):
        return bool(obj.get_reversal())

    change_actions = ('reverse_transaction',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('reversal')

    @admin.action(
        description="Reverse a transaction and unenroll the learner from the platform representation of the course."
    )
    def reverse_transaction(self, request, obj):
        """
        Redirect to the reverse transaction view.
        """
        # url names coming from get_urls are prefixed with 'admin' namespace
        reverse_transaction_url = reverse("admin:reverse_transaction", args=(obj.uuid,))
        return HttpResponseRedirect(reverse_transaction_url)

    reverse_transaction.label = "Unenroll & Refund"

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


class AdjustmentAdminCreateForm(forms.ModelForm):
    """
    Form that allows users to enter adjustment quantities in dollars
    instead of cents.
    """
    class Meta:
        model = models.Adjustment
        fields = [
            'ledger',
            'quantity_usd_input',
            'reason',
            'notes',
            'transaction_of_interest',
            'transaction',
            'adjustment_quantity',
        ]

    quantity_usd_input = forms.FloatField(
        required=True,
        help_text='Amount of adjustment in US Dollars.',
    )


class AdjustmentAdminChangeForm(forms.ModelForm):
    """
    Form for reading and changing only the allowed fields of an existing adjustment record.
    """
    class Meta:
        model = models.Adjustment
        fields = [
            'ledger',
            'reason',
            'notes',
            'transaction_of_interest',
            'transaction',
            'adjustment_quantity',
        ]


@admin.register(models.Adjustment)
class AdjustmentAdmin(SimpleHistoryAdmin):
    """
    Admin configuration for the Adjustment model.
    """
    form = AdjustmentAdminCreateForm

    _readonly_fields = [
        'get_quantity_usd',
        'uuid',
        'transaction',
        'adjustment_quantity',
        'created',
        'modified',
    ]

    list_display = (
        'uuid',
        'get_ledger_uuid',
        'get_quantity_usd',
        'reason',
        'created',
        'modified',
    )
    list_filter = (
        'reason',
    )
    autocomplete_fields = [
        'ledger',
        'transaction_of_interest',
    ]

    def get_readonly_fields(self, request, obj=None):
        """
        Don't allow changing the ledger if we've already saved the adjustment record.
        """
        if obj and not obj._state.adding:  # pylint: disable=protected-access
            return ['ledger'] + self._readonly_fields
        return self._readonly_fields

    def get_fields(self, request, obj=None):
        """
        Don't include the ``quantity_usd_input`` field unless we're creating a new adjustment.
        """
        # When we're adding a new adjustment, use default fields
        if not obj:
            return super().get_fields(request, obj)
        else:
            # Don't show the USD amount input field on read/change
            return [
                field for field in super().get_fields(request, obj)
                if field != 'quantity_usd_input'
            ]

    def get_form(self, request, obj=None, **kwargs):  # pylint: disable=arguments-differ
        """
        Don't worry about validating the ``quantity_usd_input`` unless we're creating a new adjustment.
        """
        if obj and not obj._state.adding:  # pylint: disable=protected-access
            kwargs['form'] = AdjustmentAdminChangeForm
        return super().get_form(request, obj, **kwargs)

    @admin.display(description='Amount in U.S. Dollars')
    def get_quantity_usd(self, obj):
        if not obj._state.adding:  # pylint: disable=protected-access
            return cents_to_usd_string(obj.adjustment_quantity)
        return None

    @admin.display(ordering='uuid', description='Ledger uuid')
    def get_ledger_uuid(self, obj):
        return obj.ledger.uuid

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
        else:
            raw_usd_input = form.cleaned_data.get('quantity_usd_input')
            quantity_usd_cents = raw_usd_input * constants.CENTS_PER_US_DOLLAR
            # AED 2023-10-16: Use the auto-generated "stub" UUID for the Adjustment record
            # to persist the Adjustment record, so that Django Admin doesn't get lost
            # when a user clicks "Save and Continue Editing".
            api.create_adjustment(
                adjustment_uuid=obj.uuid,
                ledger=obj.ledger,
                quantity=quantity_usd_cents,
                reason=obj.reason,
                notes=obj.notes,
                transaction_of_interest=obj.transaction_of_interest,
            )
