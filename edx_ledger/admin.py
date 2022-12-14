from django.contrib import admin
from edx_ledger import models

@admin.register(models.Ledger)
class LedgerAdmin(admin.ModelAdmin):
    class Meta:
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
        return obj.balance()


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    class Meta:
        model = models.Transaction
        fields = '__all__'


@admin.register(models.Reversal)
class ReversalAdmin(admin.ModelAdmin):
    class Meta:
        model = models.Reversal
        fields = '__all__'
