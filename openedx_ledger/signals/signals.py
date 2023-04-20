"""
openedx_ledger related signals.
"""

from django.dispatch import Signal

# Signal that indicates that a transaction object has been reversed.
# providing_args=[
#         'reversal',  # Reversal object
#     ]
TRANSACTION_REVERSED = Signal()
