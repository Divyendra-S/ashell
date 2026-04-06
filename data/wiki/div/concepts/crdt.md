# Conflict-free Replicated Data Types (CRDT)

Conflict-free Replicated Data Types (CRDTs) are data structures designed to be replicated across multiple computers or nodes in a distributed system. They guarantee that all replicas will eventually converge to a consistent state automatically, without requiring coordination or complex consensus protocols.

## Key Facts
- **Automatic Convergence**: They resolve conflicts mathematically, ensuring that concurrent updates eventually result in the same state across all nodes.
- **High Availability**: Since they don't require coordination (like locking) for writes, they allow systems to remain highly available and performant, even during network partitions.
- **Real-world Use Cases**: Frequently used in real-time collaborative editing applications, such as Figma, Google Docs, and offline-first applications.
- **Common Types**:
  - **G-Counter**: Grow-only Counter (can only increment).
  - **PN-Counter**: Positive-Negative Counter (can increment and decrement).
  - **LWW-Register**: Last-Writer-Wins Register (resolves updates using timestamps).
  - **OR-Set**: Observed-Remove Set (allows elements to be added and removed).

## Connections
- [[Distributed Systems]] — CRDTs are a fundamental pattern in distributed systems for achieving eventual consistency without coordination.

## Notes
- User is actively learning about this as part of their broader exploration of distributed systems.