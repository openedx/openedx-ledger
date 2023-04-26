0005 LEDGER EVENT SIGNALS
#########################

Status
******

**Accepted**

.. Standard statuses
    - **Draft** if the decision is newly proposed and in active discussion
    - **Provisional** if the decision is still preliminary and in experimental phase
    - **Accepted** *(date)* once it is agreed upon
    - **Superseded** *(date)* with a reference to its replacement if a later ADR changes or reverses the decision

Context
*******

Consumers of the openedx-ledger need to be have the ability to perform specific actions when certain events are 
invoked, such as a transaction reversal. The most common use case is to hook up new django signals for each needed 
event. These signals can be used to broadcast any particular action to any and all downstream consumers. 


Decision
********

We will use the `Django Signals` framework to provide a mechanism for consumers to hook into the transaction reversal 
process (the successful invokation of the `reverse_full_transaction` method). We will establish a pattern of signals 
definitions within the `signals` dir of the openedx-ledger app. Starting out, the only signal defined will be named 
`TRANSACTION_REVERSED` and it will set the pattern for any future signal usage should the need for a change arise.

Consequences
************

* Consumers of the ledger service will be able to hook into the reversal process and perform any actions they need to.
* Patterns for signal events will be established and documented in the openedx ledger and subsidy service.
