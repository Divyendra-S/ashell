# Raft Consensus Algorithm

Raft is a leader-based consensus protocol used in distributed systems to manage a replicated log. It was specifically designed to be more understandable than previous consensus algorithms like Paxos, while providing the same fault-tolerance and safety guarantees.

## Key Facts
- **Leader-Based Replication:** In Raft, one node is elected as the leader. The leader accepts client requests and is responsible for replicating log entries across all follower nodes.
- **Understandability:** Raft was created as an alternative to Paxos, with its primary design goal being ease of understanding and practical implementation.
- **Safety Guarantee:** The protocol guarantees safety and progress as long as a strict majority (quorum) of nodes in the cluster remain alive.

## Connections
- [[Distributed Systems]] — Raft provides the fundamental consensus mechanism needed to maintain reliable state across distributed nodes.
- [[Paxos]] — An older, notoriously complex consensus algorithm that Raft was explicitly designed to improve upon in terms of clarity.

## Notes
- Key insight (from Divyendra): Safety is guaranteed as long as a majority of nodes are alive.
