0006 Ledger balance and transaction states
##########################################

Status
******

**Accepted** (May 2023)

Context
*******

We will take a strong position on the states of transactions that should count when
computing the balance of a ledger.  Specifically, we don't want to count known-failed
transactions toward the balance of a ledger.

Decision
********

We'll consider only the non-failed states when computing the balance of a ledger. Those states are:

- ``committed``
- ``pending``
- ``created``

Any transaction with a state of ``failed`` will not be considered for the balance
of a ledger.  We choose these states because they represent all transactions which have succeeded,
or which may succeed in the future.  ``failed`` is a terminal state from which
transactions my not transition.

Consequences
************

Consumers of the ledger/transactions API must be able to (and are required to)
fetch data about failed transactions separately from the context of a ledger's balance.

We should also consider using a sentinel job, or some other mechanism, to move transactions
out of the non-committed states of ``created`` and ``pending``.  This could involve
introducing a new transaction state, but that's a decision for the future.
