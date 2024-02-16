0008 ``parent_content_key`` Field
#################################

Status
******
**Accepted** (February 2024)

Context
*******
Today, we store a ``Transaction.content_key`` field which points at the content into which a learner is enrolled.
Currently in the openedx ecosystem that would be a "course run key". However, we'd also like to know the parent
identifier for the content, most often the "course key" associated with a "course run key" within the openedx ecosystem.
In some downstream systems and frontends which consume transaction data it is essential to know the parent content key,
but dynamically fetching it from APIs can be slow when working with many transactions.

Decision
********
We'll introduce a ``parent_content_key`` field to the ``Transaction`` model. Similarly to ``content_title``, this new
field will essentially locally cache slow-changing data (content keys are arguably the slowest of slow-changing).

Consequences
************
* Creating transactions will additionally be required to pass a ``parent_content_key``, but this should be
  straightforward since they already pass ``content_title``, which is already co-located with the parent content key
  (``course_key``) within the system of record.
