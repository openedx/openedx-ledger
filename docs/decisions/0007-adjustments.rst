0007 Ledger Adjustments
#######################

Status
******
**Accepted** (October 2023)

Context
*******
We'd like to have the ability to manually adjust the balance of ledgers
in a somewhat unstructured way - that is, in a way that doesn't reverse
an existing transaction.  For example, the manager of a customer account
may need to manually "credit" a ledger when:

* a learner manages to redeem an enrollment via a ledger in a course that our
  system should not have allowed them to access at the time of redemption.
* a learner had unforseen technical challenges in taking the course, but
  is not able to officially unenroll/reverse the redemption.
* some client-relationship building needs to take place.

Decision
********
We'll introduce an ``Adjustment`` model:

* This is somewhat different from our existing pattern of modeling any modification
  to a ledger via models that inherit from ``BaseTransaction`` (like we
  do with ``Reversal``).
* Creating an ``Adjustment`` will cause a new ``Transaction`` to be written
  to the adjustment's ledger object, with the same quantity as the adjustment record.
  This transaction record is the thing that fundamentally changes the
  balance of the related ledger. The transaction will be referred to from a foreign key of the ``Adjustment``
  record.
* An adjustment must define some enumerated ``reason`` for being created.  The ``reason`` should
  be from a fixed set of choices, and those choices should generally **not** overlap
  with the strict notion of reversing a transaction.
* An ``Adjustment`` *may* refer to a ``transaction_of_interest`` - this is a foreign
  key to another transaction of note that is relevant to the reason for the
  creation of the adjustment.  It is not required.
* An adjustment *may* include some free-text ``notes`` that help to further
  explain why the adjustment exists.

Consequences
************
* Adjustments work in kind of the opposite way of reversals: instead of using an
  existing ledger-transaction to instantiate a reversal, we'll have a situation
  where the action of creating an adjustment happens, which has a side-effect
  of creating a transaction to adjust the ledger balance.
* Care must be taken to ensure that adjustments are not over-used.  For one, using them
  to transfer balance from a customer to a ledger upon the expiration of our business
  contracts (i.e. to "renew" a contract) could be inappropriate or destructive from
  a back-office recordkeeping perspective.  And they should never be used in place
  of ``Reversals`` when the latter are applicable.
* It would be beneficial to observe and track the usage of ``Adjustments``
  over time within the system, and perhaps to restrict their usage
  via Django Admin tools or "hard" thresholds.
