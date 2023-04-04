0003 Explicit External and Internal Transaction References
##########################################################

Status
******

Draft *2023-03-29*

.. Standard statuses
    - **Draft** if the decision is newly proposed and in active discussion
    - **Provisional** if the decision is still preliminary and in experimental phase
    - **Accepted** *(date)* once it is agreed upon
    - **Superseded** *(date)* with a reference to its replacement if a later ADR changes or reverses the decision

Context
*******

Transaction objects, being the connection between financial operations and enrollments, have multiple references to
external objects in different services. These currently include, but are not limited to, GEAG allocation references
and enterprise fulfillment objects. The current implementation of these references is encompassed by a single field
on the Transaction model, ``reference_id``. However, the purpose of these references is not always clear, and may serve
different purposes for a particular Transaction at any given point in the enrollment process. It's also not currently
possible for multiple references to point to the same transaction. Additionally, the current implementation does
not easily allow for additional financial allocation sources without subsequent migrations. We propose to make these
references more explicit by representing each type of external reference as an instance of a fulfillment provider
model.

Decision
********

We will create two new models, ``ExternalTransactionReference`` and ``ExternalFulfillmentProvider``, to store
references to external fulfillment objects and their source providers. ``ExternalFulfillmentProvider`` contains name
and slug values of external fulfillment providers while the ``ExternalTransactionReference`` model will contain an
``external_reference_id`` field, as well as a ``transaction`` foreign key relationship (with a related name of
``external_reference``) to the Transaction model and an ``external_fulfillment_provider`` foreign key relationship to
``ExternalFulfillmentProvider``. The external reference ID will serve as the financial fulfillment reference for a
given Transaction and who's external provider is indicated by the ``external_fulfillment_provider`` value. This will
allow us to handle new, different types of fulfillment in the future other than just GEAG fulfillment.

In regards to the Transaction model, both the ``reference_id`` and ``reference_type`` fields will be removed and
replaced by a single char field; ``fulfillment_identifier``. This field replaces the currently implemented
Transaction reference ID in that it will be used to store the UUID of the enterprise fulfillment object that the
Transaction is associated with. ``fulfillment_identifier`` can be thought of as the identifier associated with the
internal to Open edX fulfillment of a transaction; records in the ExternalTransactionReference model help capture
identifiers (or perhaps other metadata) about the external fulfillment of a transaction.

Rejected Alternatives
*********************

1) split ``reference_id`` into ``fulfillment_identifier`` and ``external_reference_id``.  However that limits our
ability to allow a transaction to have multiple external reference IDs, which has become a soft requirement.

2) As a continuation of the previous bullet point, split ``external_reference_id`` into multiple fields, but that would
have required migrations for every new reference type and product line we add, and that was a long term liability we
did not want to accept at this stage.

3) Shoving all external reference IDs in the metadata (JSON) field, while technically feasible, presents challenges
from an analytics and reporting perspective.

Consequences
************
* We will need to update the Transaction model to remove the ``reference_id`` and ``reference_type`` fields.
