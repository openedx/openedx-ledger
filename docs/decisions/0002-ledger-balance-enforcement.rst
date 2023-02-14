0001 Ledger Balance Enforcement
###############################

Status
******

**Provisional**

.. TODO: When ready, update the status to Accepted.

.. Standard statuses
    - **Draft** if the decision is newly proposed and in active discussion
    - **Provisional** if the decision is still preliminary and in experimental phase
    - **Accepted** *(date)* once it is agreed upon
    - **Superseded** *(date)* with a reference to its replacement if a later ADR changes or reverses the decision

    If an ADR has Draft status and the PR is under review, you can either use the intended final status (e.g. Provisional, Accepted, etc.), or you can clarify both the current and intended status using something like the following: "Draft (=> Provisional)". Either of these options is especially useful if the merged status is not intended to be Accepted.

Context
*******

The Ledger model enables the bookkeeping of all value ins/outs for a given subsidy; value can be added and removed from
a Ledger via the creation of positive-, or negative-value Transactions.  The "balance" of a Ledger is simply the sum of
all of its Transactions.  One critical requirement for the Ledger is that it not be allowed to enter a state of negative
balance, which is enforced via the following code pattern:

.. code-block:: python

  with atomic(durable=True):
      if (quantity < 0) and ((ledger.balance() + quantity) < 0):
          # throw error
      # create a transaction with the given quantity

However, without leveraging any database or other guardrails to prevent race conditions, the sample code alone does not
guarantee an always-positive balance.  For example, two requests may attempt a subsidy redemption close in time:

+-----------------+-----------------------+-----------------------+
| Ledger Balance  |  Request 1            | Request 2             |
+=================+=======================+=======================+
|             10  |                       |                       |
+-----------------+-----------------------+-----------------------+
|                 | check balance         |                       |
+-----------------+-----------------------+-----------------------+
|                 |                       | check balance         |
+-----------------+-----------------------+-----------------------+
|                 | create -7 transaction |                       |
+-----------------+-----------------------+-----------------------+
|              3  |                                               |
+-----------------+-----------------------+-----------------------+
|                 |                       | create -4 transaction |
+-----------------+-----------------------+-----------------------+
|             -1  |                       |                       |
+-----------------+-----------------------+-----------------------+

Guardrails provided by Django and MySQL by default are insufficient to prevent this scenario.  Django may implicitly
wrap the request in a MySQL database transaction (or we may explicitly do so via `atomic()` context manager), but a
MySQL transaction will at most implicitly grab a row-level lock.  Simple row-level locks, however, are insufficient in
this case because we must actually defend against the creation of a new transaction entirely.

Another relevant base fact is that our expected data volume for the Transaction table is on the order of 10s of thousands of
records for most installations, and queries against the table will always leverage an indexed column with low
cardinality (the subsidy FK).  Also, this database, as it is recommended to be deployed, runs on a dedicated DB instance
rather than a shared one.  Therefore, full table scans should perform swiftly.

Approach 1: Table Locking
*************************

A combination of explicit transactions and explicit whole-table locking provides the required guardrails at the expense
of some performance:

.. code-block:: python

  with atomic_with_table_lock(Transaction):
          if (quantity < 0) and ((ledger.balance() + quantity) < 0):
              # throw error
          # create a transaction with the given quantity

Here's one possible implementation of atomic_with_table_lock(), inspired by a `StackOverflow question about table locking via Django ORM`_:

.. code-block:: python

  @contextmanager
  def atomic_with_table_lock(model):
      """
      Lock whole table associated with given model.  Contending transactions that attempt to read the table will block
      until the first transaction commits or rolls back.
      """
      skip_locking = False
      if connection.vendor == "mysql":
          logger.warn(
              "Failed to grab row lock due to the detected database not being mysql. Explicit locking will not be used "
              "in this transaction."
          )
          skip_locking = True
      with transaction.atomic(durable=True):
          if not skip_locking:
              cursor = get_connection().cursor()
              cursor.execute(f"LOCK TABLES {model._meta.db_table} WRITE")  # MySQL syntax.
              try:
                  yield
              finally:
                  # Just make sure to close, regardless of whether transaction.atmoic already handles this.  Avoid a
                  # dangling lock.
                  cursor.close()
          else:
              yield

Below is a revised sequence of events for the same two redemption requests, but locking the Transaction table:

+-----------------+-----------------------+-----------------------------------+
| Ledger Balance  |  Request 1            | Request 2                         |
+=================+=======================+===================================+
|             10  |                       |                                   |
+-----------------+-----------------------+-----------------------------------+
|                 | BEGIN                 |                                   |
+-----------------+-----------------------+-----------------------------------+
|                 | grab table lock       |                                   |
+-----------------+-----------------------+-----------------------------------+
|                 | check balance         |                                   |
+-----------------+-----------------------+-----------------------------------+
|                 |                       | BEGIN                             |
+-----------------+-----------------------+-----------------------------------+
|                 |                       | grab table lock, begin blocking   |
+-----------------+-----------------------+-----------------------------------+
|                 | create -7 transaction |                                   |
+-----------------+-----------------------+-----------------------------------+
|                 | COMMIT                |                                   |
+-----------------+-----------------------+-----------------------------------+
|              3  |                       |                                   |
+-----------------+-----------------------+-----------------------------------+
|                 |                       | table lock grabbed!               |
+-----------------+-----------------------+-----------------------------------+
|                 |                       | check balance                     |
+-----------------+-----------------------+-----------------------------------+
|                 |                       | throw exception                   |
+-----------------+-----------------------+-----------------------------------+
|                 |                       | ROLLBACK                          |
+-----------------+-----------------------+-----------------------------------+
|              3  |                       |                                   |
+-----------------+-----------------------+-----------------------------------+

The second request to deduct from the same ledger is blocked from checking the balance until after the first request is
complete, which is made possible by locking the entire table.

The `MySQL Transaction Isolation Levels`_ are not relevant in this case because table locking is so coarse that no two
ledger transaction reads in the same DB transaction have any opportunity to read different values.  That said, it may
benefit us to upgrade from the Django default of `read committed` to `repeatable read` which may protect against phantom
reads in other code paths that don't leverage explicit table locking.  It's worth noting that under `repeatable read` a
snapshot of the records are made at the first read rather than the beginning of the transaction, so in the above
sequence diagram request 2 takes a snapshot after the COMMIT of request 1, thus reading a ledger balance of 3.

Approach 2: Proxy Row Locking
*****************************

This approach also leverages MySQL locking features, but locks only Transactions related to a single Subsidy/Ledger
rather than ALL Transactions.  This approach uses a row in a table other than the one being modified to hold a lock,
hence the made-up term "proxy row locking".  This is definitely a hack because it leverages a MySQL feture `SELECT *
FROM ... FOR UPDATE` which is intended for updating rows being selected, as the command name suggests, but we will never
update rows being explicitly read-locked.

This is similar to whole-table locking described in approach 1, except a row in the Subsidy model is used for locking
during a Transaction insert:

.. code-block:: python

  with atomic_with_row_lock(Subsidy, "uuid", subsidy_uuid):
          if (quantity < 0) and ((ledger.balance() + quantity) < 0):
              # throw error
          # create a transaction with the given quantity

Here's one possible implementation of atomic_with_table_lock():

.. code-block:: python

  @contextmanager
  def atomic_with_row_read_lock(model, field_name, field_value):
      """
      Grab a row lock using `SELECT * FROM ... FOR UPDATE`.
      """
      skip_locking = False
      try:
          model._meta.get_field(field_name)
      except FieldDoesNotExist:
          logger.warn(
              "Failed to grab row lock due to a non-existent field name being supplied: "
              "{model._meta.object_name}.{field_name}.  Explicit locking will not be used in this transaction."
          )
          skip_locking = True
      if connection.vendor == "mysql":
          logger.warn(
              "Failed to grab row lock due to the detected database not being mysql. Explicit locking will not be used "
              "in this transaction."
          )
          skip_locking = True
      with transaction.atomic(durable=True):
          if not skip_locking:
              cursor = get_connection().cursor()
              table_name = model._meta.db_table
              cursor.execute(f"SELECT * FROM {table_name} WHERE {field_name} = {field_value} FOR UPDATE")  # MySQL syntax.
              try:
                  yield
              finally:
                  # Just make sure to close, regardless of whether transaction.atmoic already handles this.  Avoid a
                  # dangling lock.
                  cursor.close()
          else:
              yield

Below is a revised sequence of events, but locking rows in the Subsidy table:

+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
| Ledger A Balance | Ledger B Balance |  Request 1              | Request 2                               | Request 3               |
+==================+==================+=========================+=========================================+=========================+
|               10 |               70 |                         |                                         |                         |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                  |                  | BEGIN                   |                                         |                         |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                  |                  | grab Subsidy A row lock |                                         |                         |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                  |                  | check balance           |                                         |                         |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                  |                  |                         | BEGIN                                   | BEGIN                   |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                  |                  |                         | grab Subsidy A row lock, begin blocking | grab Subsidy B row lock |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                  |                  | create -7 transaction   |                                         | row lock grabbed!       |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                  |                  | COMMIT                  |                                         | check ledger B balance  |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                3 |                  |                         |                                         | create -20 transaction  |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                  |                  |                         | row lock grabbed!                       | COMMIT                  |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                  |               50 |                         |                                         |                         |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                  |                  |                         | check ledger A balance                  |                         |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                  |                  |                         | throw exception                         |                         |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                  |                  |                         | ROLLBACK                                |                         |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+
|                3 |               50 |                         |                                         |                         |
+------------------+------------------+-------------------------+-----------------------------------------+-------------------------+

Note that this approach prevents blocking the 3rd request because the lock is Subsidy-/Ledger-specific rather than
locking the entire Transaction table.  Performance is improved over coarser table-locking, however it uses a MySQL
feature in an unintended way which may have unintended consequences after implementation and testing.

Approach 3: Distributed Locks Using Redis
*****************************************

This approach is similar Proxy Row Locking in that the lock corresponds only to a single Subsidy/Ledger, however it is
implemented using Redis rather than MySQL:

.. code-block:: python

  with atomic_with_redis_lock(f"lock-subsidy-{subsidy_uuid}"):
          if (quantity < 0) and ((ledger.balance() + quantity) < 0):
              # throw error
          # create a transaction with the given quantity

Here's one possible implementation of atomic_with_redis_lock() using `python-redis-lock`_:

.. code-block:: python

  from redis import Redis
  import redis_lock

  conn = Redis()

  @contextmanager
  def atomic_with_redis_lock(lock_name):
      """
      Grab a redis lock.

      The lock auto-expires after 60 seconds to prevent an app crash from orphaning locks.  auto_renewal=True handles
      the edge case of the yielded logic actually needing more than 60 seconds to complete by automatically renewing the
      expiration timer.

      TODO: skip locking during unit testing.
      """
      with redis_lock.Lock(conn, lock_name, expire=60, auto_renewal=True):
          with transaction.atomic(durable=True):
              yield

Overview
********

Table Locking Advantages:

* Relatively easy to conceptualize.

Table Locking Disadvantages:

* Potentially poor performance.
* Not available during unit tests. (Common disadvantage)

Proxy Row Locking Advantages:

* Good performance.

Proxy Row Locking Disadvantages:

* Non-trivial code, hard to understand and potentially debug.
* Uses MySQL features in unintended ways which could have unintended consequences.
* Not available during unit tests. (Common disadvantage)

Distributed Locks Using Redis Advantages:

* Good performance, but sensitive to Redis response time.
* Simple code.  Easy for future engineers to understand.

Distributed Locks Using Redis Disadvantages:

* Sensitive to Redis going down.

  * Across edX codebases, Redis is only used as a Celery and/or Caching backend, two instances where Redis cannot
    hard-stop the application.  In other words, we have prior-art of using Redis for mission-critical functionality, but
    nothing that would ever block the app completely.

* Not available during unit tests. (Common disadvantage)

Consequences
************

Adding any additional locking decreases performance, by nature.  However, as mentioned in the Context section,
the data volume of the Ledger table is relatively low, the columns being grouped by will be indexed and have low
cardinality, and the database should be deployed to a dedicated DB instance.  All of these factors should allow us to
tolerate a slight performance hit.  We may be able to tolerate the performance of the full table locking approach, but
there's no doubt the 2nd and 3rd approaches will have adequate performance.

Alternatives
************

I'm not aware of any more alternatives aside from the 3 approaches described above.

References
**********

* `MySQL Transaction Isolation Levels`_
* `StackOverflow question about table locking via Django ORM`_
* `python-redis-lock`_

.. _MySQL Transaction Isolation Levels: https://dev.mysql.com/doc/refman/8.0/en/innodb-transaction-isolation-levels.html
.. _StackOverflow question about table locking via Django ORM: https://stackoverflow.com/questions/19686204/django-orm-and-locking-table
.. _python-redis-lock: https://github.com/ionelmc/python-redis-lock
