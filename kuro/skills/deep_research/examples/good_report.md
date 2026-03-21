# Example: Good Research Report

This is an example of a well-structured research output to guide quality.

---

# How does Kubernetes handle pod scheduling?

## Executive Summary
Kubernetes uses a two-phase scheduling process: filtering (eliminates nodes that can't run the pod) then scoring (ranks remaining nodes by fitness). The default scheduler (kube-scheduler) can be extended with custom plugins.

## Sub-Questions Investigated
1. What is the default scheduling algorithm?
2. How do resource requests and limits affect placement?
3. What role do taints and tolerations play?

## Detailed Findings

### Default Scheduling Algorithm
**Sources:** Article: "K8s Architecture Deep Dive", Entity: kube-scheduler

The default scheduler uses a plugin-based framework with two phases (from article: "K8s Architecture Deep Dive"):
- **Filter phase**: Eliminates nodes that don't meet hard constraints (resource capacity, node selectors, taints)
- **Score phase**: Ranks remaining nodes using weighted scoring (resource balance, affinity rules, topology spread)

### Resource Requests and Limits
**Sources:** Entity: Pod Resources, Article: "K8s Best Practices"

Resource requests are guaranteed allocations; limits are maximums (entity: Pod Resources, fact: "requests define the minimum resources a container needs"). The scheduler only considers requests when making placement decisions — limits are enforced at runtime by the kubelet.

### Taints and Tolerations
**Sources:** Article: "K8s Architecture Deep Dive"

Taints mark nodes to repel pods unless those pods have matching tolerations (from article: "K8s Architecture Deep Dive"). Common use case: dedicating nodes to specific workloads.

## Cross-References & Connections
- Resource requests (finding 2) are evaluated during the filter phase (finding 1) — a pod requesting 4GB RAM won't be scheduled on a node with only 2GB available
- Taints (finding 3) are also evaluated during filtering, not scoring

## Knowledge Gaps
- [ ] Custom scheduler plugins — no articles cover how to write one
- [ ] Priority and preemption — only mentioned in passing, no deep coverage
- [ ] Scheduling across multiple clusters

## Sources Referenced
| Type | Name | Relevance |
|------|------|-----------|
| Article | K8s Architecture Deep Dive | Core scheduling algorithm details |
| Article | K8s Best Practices | Resource management guidance |
| Entity | kube-scheduler | Component description and relations |
| Entity | Pod Resources | Request/limit definitions |
