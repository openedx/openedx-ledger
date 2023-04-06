0004 Ledger Balance Enforcement Revised
#######################################

Status
******

**Accepted** *April 2023*

.. Standard statuses
    - **Draft** if the decision is newly proposed and in active discussion
    - **Provisional** if the decision is still preliminary and in experimental phase
    - **Accepted** *(date)* once it is agreed upon
    - **Superseded** *(date)* with a reference to its replacement if a later ADR changes or reverses the decision

Context
*******

For context on why we need a distinct mechanism to enforce a positive ledger balance, see previous
`ADR 0002-ledger-balance-enforcement`_.  In ADR 0002, we describe various approaches to lock the subsidy, including:

* DB table-locking on the whole Ledger table
* DB row-locking on the Subsidy table (proxy-row locking)
* Redis-based locking using a Subsidy-scoped key
* Explicit row-level locking read with gap locking
* DynamoDB-based locking using a Subsidy-coped key

However, perhaps the simplest approach of all was not evaluated: Memcache via django cache using a Subsidy-scoped cache
key.  This has all the upsides of not relying on clever MySQL DB tricks, while also being a tried and tested approach of
distributed caching within the openedx ecosystem.  Fore more detail explanation of the merits of using Memcached for
locking a resource, see `ADR 0005-access-policy-locks`_.

Note about the proposal in `ADR 0005-access-policy-locks`_ to use `TieredCache`_: code patterns that leverage Memcached for
locking rely on the add() function, but TieredCache only exposes get() and set().  We can reduce the chances of a race
condition by using add() directly from django cache, bypassing TieredCache.

Note about what object to lock: The Transaction being created is more closely related to a Ledger object than a Subsidy
object; in fact, while there is currently a 1:1 relationship between the Subsidy and Ledger, that is liable to change in
the future.  Therefore, locking on the Subsidy rather than the Ledger could result in excessive performance impact.
It's also just easier to rationalize locking the Ledger, and keeps all the locking code consolidated in this
openedx_ledger repo.

Decision
********

We will use a Memcached-backed django cache to perform Ledger-level locking during creation of a new Transaction.
Acquire and release functionality can be implemented as Ledger model methods to help ensure the correct resource keys
are used. E.g.:

.. code-block:: python

  from edx_django_utils.cache.utils import get_cache_key

  class Ledger:

      [...]

      @property
      def lock_resource_key(self):
          return get_cache_key(resource=LEDGER_LOCK_RESOURCE_NAME, uuid=self.uuid)

      def acquire_lock(self):
          return django_cache.add(self.lock_resource_key, "acquired"):

      def release_lock(self):
          django_cache.delete(self.lock_resource_key)

Consequences
************

Same considerations as described in previous `ADR 0002-ledger-balance-enforcement`_.

Additionally, Memcached developers suggest that using it for locking should only be considered for non-critical
applications because add() is still susceptible to race conditions (see `Memcached Ghetto Central Locking`_).  That
said, we have decided this is a decent compromise between complexity of implementation and robustness, especially given
that we have other safeguards in place, such as idempotency keys which prevent the creation of multiple transactions
that represent the same enrollment attempt.

Rejected Alternatives
*********************

All approaches described in `ADR 0002-ledger-balance-enforcement`_.

References
**********

* `ADR 0002-ledger-balance-enforcement`_
* `TieredCache`_
* `ADR 0005-access-policy-locks`_
* `Example locking from enterprise-access`_
* `Memcached Ghetto Central Locking`_

.. _ADR 0002-ledger-balance-enforcement: https://github.com/openedx/openedx-ledger/blob/main/docs/decisions/0002-ledger-balance-enforcement.rst
.. _TieredCache: https://github.com/openedx/edx-django-utils/tree/master/edx_django_utils/cache#tieredcache
.. _ADR 0005-access-policy-locks: https://github.com/openedx/enterprise-access/blob/main/docs/decisions/0005-access-policy-locks.rst`
.. _Example locking from enterprise-access: https://github.com/openedx/enterprise-access/blob/39d2d026ae7489eff1d82b8ceece78ace5195af4/enterprise_access/apps/api/utils.py#L53-L73
.. _Memcached Ghetto Central Locking: https://github.com/memcached/memcached/wiki/ProgrammingTricks#ghetto-central-locking
