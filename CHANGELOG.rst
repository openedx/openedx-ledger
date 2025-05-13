Change Log
##########

..
   All enhancements and patches to openedx_ledger will be documented
   in this file.  It adheres to the structure of https://keepachangelog.com/ ,
   but in reStructuredText instead of Markdown (for ease of incorporation into
   Sphinx documentation and the PyPI description).

   This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Unreleased" section for changes pending release.

Unreleased
**********
* Nothing unreleased

[1.6.0]
*******
* feat: Add support for Django 5.2
* feat!: Dropped support for Python 3.8 and 3.9

[1.5.24]
********
* chore: Increase version to 1.5.24 for dependency updates.

[1.5.23]
********
* chore: Increase version to 1.5.23 for dependency updates.

[1.5.22]
********
* chore: Update python requirements job source to openedx

[1.5.21]
********
* chore: Increase version to 1.5.21 for dependency updates.

[1.5.20]
********
* chore: Increase version to 1.5.20 for dependency updates.

[1.5.19]
********
* chore: Increase version to 1.5.19 for dependency updates.

[1.5.18]
********
* chore: Increase version to 1.5.18 for dependency updates.

[1.5.17]
********
* chore: Increase version to 1.5.17 for dependency updates.

[1.5.16]
********
* chore: Increase version to 1.5.16 for dependency updates.

[1.5.15]
********
* chore: Increase version to 1.5.15 for dependency updates.

[1.5.14]
********
* chore: Increase version to 1.5.14 for dependency updates.

[1.5.13]
********
* chore: Increase version to 1.5.13 for dependency updates.

[1.5.12]
********
* chore: Increase version to 1.5.12 for dependency updates.

[1.5.11]
********
* chore: Increase version to 1.5.11 for dependency updates.

[1.5.10]
********
* chore: Increase version to 1.5.10 for dependency updates.

[1.5.9]
*******
* chore: Increase version to 1.5.9 for dependency updates.
* chore: Use Node 20 in Dockerfile.

[1.5.8]
*******
* chore: Increase version to 1.5.8 for dependency updates.

[1.5.7]
*******
* chore: Increase version to 1.5.7 for dependency updates.

[1.5.6]
*******
* chore: Increase version to 1.5.5 for dependency updates.

[1.5.5]
*******
* chore: Increase version to 1.5.5 for dependency updates.

[1.5.4]
*******
* chore: Increase version to 1.5.4 for dependency updates.

[1.5.3]
*******
* fix: deposit sales references should be optional

[1.5.2]
*******
* feat: Ledger creation is now capable of initial Deposit creation

[1.5.1]
*******
* chore: Increase version to 1.5.1 for dependency updates.

[1.5.0]
*******
* feat: Deposit model and supporting functionality

[1.4.5]
*******
* chore: Increase version to 1.4.5 for dependency updates.

[1.4.4]
*******
* feat: the Reversal django admin field now autocompletes.

[1.4.3]
*******
* feat: Update help text for adjustments

[1.4.2]
*******
* feat: Dependency updates

[1.4.1]
*******
* feat: Add python 3.12 support

[1.4.0]
*******
* feat: Add parent_content_key field to Transaction model (ENT-8389)

[1.3.3]
*******
* Upgrade requirements

[1.3.2]
*******
* Fixing a kwarg typo

[1.3.1]
*******
* Update requirements

[1.3.0]
*******
* Add optional ``lms_user_email`` and ``content_title`` to the ``Transaction`` model

[1.2.0]
*******
* Add an ``Adjustment`` model

[1.1.0]
*******
* Add support for Django 4.2

[1.0.2]
*******
* only allow reversals of committed transactions

[1.0.1]
*******
* make transaction and ledger admins friendlier

[1.0.0]
*******
* Look for an ``lms_user_id`` key when generating transaction idempotency keys, not ``learner_id``.

[0.4.0]
*******
* include only non-failed transactions in ledger balance calculation by default

[0.3.3]
*******
* drop `ExternalFulfillmentProvider` name constraints
* Switch from ``edx-sphinx-theme`` to ``sphinx-book-theme`` since the former is
  deprecated.  See https://github.com/openedx/edx-sphinx-theme/issues/184 for
  more details.

[0.2.2]
*******
* Add many help_text fields to model fields.
* Add some useful composite table indices.
* Add a "failed" transaction state.

[0.2.0]
*******
* Some small developer QOL stuff.
* Better local development instructions in README.
* Remove docs from quality checks and ci.yml.
* Reasonable first pass at allowing for weak/strong admin editing ability depending on environment settings.
* Simple, first attempt at an idempotency key utility methods for ledgers and transactions that optionally take a subsidy and initial deposit, resp.
* Allow blank idp keys on the Ledger model, and set to a sane default if not provided on save().
* Remove JPY as an allowed unit.
* ``api.create_ledger()`` now seeds the ledger with an optional initial deposit.
* Check if we're already inside a transaction when setting ``durable=True`` in ``create_transaction()``.

[0.1.1] - 2023-01-05
********************

Added
=====

* Package renamed from `edx-ledger` to `openedx-ledger`

[0.1.0] - 2023-01-04
************************************************

Added
=====

* First release on PyPI.
