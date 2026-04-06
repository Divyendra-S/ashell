# Vector Clocks

Vector clocks are a mechanism used in distributed systems to track causality and the logical ordering of events across multiple nodes. They allow the system to determine whether events happened sequentially (one before the other) or concurrently, which is crucial for managing distributed state and resolving conflicts.

## Key Facts
- **Structure:** Each node maintains a vector (an array or map) of counters, where there is one counter allocated per node in the system.
- **Incrementing:** When a node performs a local event or sends a message, it increments its own designated counter within its vector clock.
- **Merging (Receiving):** When a node receives a message containing a vector clock, it merges the incoming vector with its own by taking the element-wise maximum for each counter, then increments its own counter.
- **Causality Determination:** By comparing two vector clocks, the system can determine the exact relationship between two events: whether event A happened before event B, event A happened after event B, or if events A and B occurred concurrently.
- **Implementations:** They are heavily utilized in Dynamo-style distributed databases, such as Riak, to handle data versioning and to detect conflicting updates that require resolution.

## Connections
- [[Distributed Systems]] — Vector clocks are a foundational tool for handling event ordering without relying on synchronized physical clocks in distributed environments.
- [[Conflict-free Replicated Data Types (CRDT)]] — Both vector clocks and CRDTs deal with distributed state replication, though CRDTs automatically merge data structures natively whereas vector clocks simply track the causality to identify conflicts.

## Notes
- Used to distinguish between causal and concurrent events in systems like Riak and Dynamo.