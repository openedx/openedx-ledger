0009 The Deposit Model
######################

Status
******

**Accepted** *(May 2026)*

Context
*******

A subsidy ledger begins with zero balance.  To be useful, it must first receive
value from an external source — typically the execution of a sales contract
(e.g. a SalesForce Opportunity) between a customer and the Open edX platform
operator.  Prior to the introduction of the ``Deposit`` model, the initial
value added to a ledger had no first-class representation in the database; the
positive transaction that seeded the balance existed without any structured link
to the underlying commercial agreement.

This made it difficult to:

* Audit which sales contract funded which ledger balance.
* Differentiate "value added via a contract" from ad-hoc ``Adjustment``
  records used for operational corrections.
* Perform accurate "total value deposited" calculations for reporting.

Decision
********

We introduce a ``Deposit`` model that provides a structured, contract-backed
record for every positive value injection into a ledger.

Model definition
================

A ``Deposit``:

* Has a mandatory one-to-one relationship with the ``Transaction`` record that
  actually moves value into the ledger.  **The transaction is the sole source of
  truth for the balance impact; the** ``Deposit`` **record itself is audit
  metadata.**
* Stores a ``desired_deposit_quantity`` field — the amount *requested* by the
  operator.  This field is non-contributing to any balance calculation and must
  not be read in place of ``transaction.quantity``.
* Requires a ``sales_contract_reference_id`` and a
  ``SalesContractReferenceProvider`` FK — together they form a stable pointer
  into the external system-of-record (e.g. SalesForce) that originated the
  contract.
* Carries a ``ledger`` FK for convenient querying; this FK is redundant with
  ``transaction.ledger`` and both must always agree.

Creating a Deposit
==================

Always use ``openedx_ledger.api.create_deposit()``.  This function:

1. Validates that the requested ``quantity`` is positive (negative deposits are
   rejected with ``DepositCreationError``).
2. Opens an atomic database transaction.
3. Calls ``create_transaction()`` with ``state=COMMITTED``, which acquires the
   ledger lock, verifies the balance will remain non-negative, and persists the
   ``Transaction``.
4. Persists the ``Deposit`` record pointing at that transaction.

.. code-block:: python

    from openedx_ledger import api
    from openedx_ledger.models import SalesContractReferenceProvider

    sf_provider = SalesContractReferenceProvider.objects.get(slug='salesforce')

    deposit = api.create_deposit(
        ledger=ledger,
        quantity=100_000,          # 1 000.00 USD expressed in cents
        sales_contract_reference_id='SF-OPP-00012345',
        sales_contract_reference_provider=sf_provider,
    )

    # The deposit's transaction immediately affects the ledger balance.
    assert ledger.balance() == 100_000

Ledger creation with an initial deposit
========================================

``api.create_ledger()`` accepts an ``initial_deposit`` keyword argument.
When supplied, **both** ``sales_contract_reference_id`` and
``sales_contract_reference_provider`` must also be provided; omitting them
raises ``LedgerCreationError``.

.. code-block:: python

    ledger = api.create_ledger(
        subsidy_uuid=subsidy.uuid,
        initial_deposit=100_000,
        sales_contract_reference_id='SF-OPP-00012345',
        sales_contract_reference_provider=sf_provider,
    )

Constraints
===========

* **Deposits must be positive.**  Passing a negative ``quantity`` raises
  ``DepositCreationError`` before any database write occurs.
* **``create_deposit()`` is not idempotent.**  Calling it twice with the same
  ``idempotency_key`` will raise a ``DepositCreationError`` (the underlying
  transaction constraint rejects the duplicate).  Callers that need retry-safe
  semantics should persist and re-use the deposit's UUID and idempotency key
  from the first successful call, rather than relying on automatic deduplication.
* **The Deposit transaction cannot be reversed via ``create_adjustment()``.**
  Reversing the transaction that underpins a deposit would silently remove
  contracted value from the ledger without leaving an auditable trail; use an
  ``Adjustment`` with an appropriate reason instead when manual corrections are
  needed.
* **The** ``desired_deposit_quantity`` **field is informational only.**  Balance
  calculations always read ``transaction.quantity``.  If the two values differ
  (e.g. after a manual data fix), the transaction value governs.
* **Sales contract references are required for all deposits.**  Deposits without
  a traceable commercial origin should be modelled as ``Adjustment`` records
  instead.

Example: a complete ledger
**************************

The following table illustrates what a ledger's transaction history might look
like after an initial deposit, several enrollments, a reversal, and a
goodwill adjustment.  All quantities are in ``usd_cents``.

.. list-table:: Ledger for Subsidy ``aaaaaaaa-…`` (unit: ``usd_cents``)
   :header-rows: 1
   :widths: 6 16 8 12 10 48

   * - #
     - Record type
     - Qty
     - State
     - Running balance
     - Notes
   * - 1
     - **Deposit** → Transaction
     - +100 000
     - committed
     - 100 000
     - SF-OPP-00012345 · ``SalesContractReferenceProvider(slug='salesforce')``
   * - 2
     - Transaction (enrollment)
     - −5 000
     - committed
     - 95 000
     - user 42 → ``course-v1:edX+DemoX+2024``
   * - 3
     - Transaction (enrollment)
     - −7 500
     - committed
     - 87 500
     - user 43 → ``course-v1:edX+ProfX+2024``
   * - 4
     - Reversal of #2
     - +5 000
     - committed
     - 92 500
     - user 42 unenrolled; reversal is a child of Transaction #2
   * - 5
     - **Adjustment** → Transaction
     - +2 500
     - committed
     - 95 000
     - reason: ``good_faith``; notes: "Compensating user 44 for platform outage"

Final ledger balance: **95 000 usd_cents** (950.00 USD).

The ``Ledger.balance()`` method sums ``Transaction.quantity`` plus
``Reversal.quantity`` for all non-``failed`` transactions.  The ``Deposit`` and
``Adjustment`` records are audit metadata; they do not appear directly in the
balance formula.

``Ledger.total_deposits()`` computes the total value deposited by summing only
those committed transactions that are either backed by a ``Deposit`` *or* an
``Adjustment`` record — reflecting the total value ever committed to the ledger
from external sources, net of any reversals applied to those deposit-esque
transactions.

Consequences
************

* A clear paper trail now connects every ledger balance to one or more sales
  contracts.  Back-office and finance tooling can join ``Deposit`` →
  ``sales_contract_reference_id`` to reconcile contracted value against consumed
  value.
* The ``Adjustment`` model retains its role for *operational corrections*
  (unauthorized enrollments, technical challenges, goodwill credits).  ``Deposit``
  is reserved for *commercial value additions*.
* Because ``create_deposit()`` is not idempotent, callers in distributed systems
  must implement their own guard (e.g. check whether a ``Deposit`` already exists
  for the sales contract reference before calling the API).
* Historical ledgers created before this model existed may lack ``Deposit``
  records for their initial transactions.  A backfill is tracked separately
  (ENT-9132); until it is complete, ``Ledger.total_deposits()`` will return
  inaccurate results for those ledgers.

References
**********

* `ADR 0007-adjustments`_
* `ADR 0006-ledger-balance-transaction-states`_
* `Migration 0011_deposit_models`_

.. _ADR 0007-adjustments: https://github.com/openedx/openedx-ledger/blob/main/docs/decisions/0007-adjustments.rst
.. _ADR 0006-ledger-balance-transaction-states: https://github.com/openedx/openedx-ledger/blob/main/docs/decisions/0006-ledger-balance-transaction-states.rst
.. _Migration 0011_deposit_models: https://github.com/openedx/openedx-ledger/blob/main/openedx_ledger/migrations/0011_deposit_models.py
