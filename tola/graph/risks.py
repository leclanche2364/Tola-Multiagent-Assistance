"""Risk graph analysis for Batch T7.

Functions operate on DependencyGraph + PortfolioSnapshot.
Stdlib only.  Deterministic.  Plain ASCII.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from tola.graph.graph import DependencyGraph, Node


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

def risk_register_from_snapshot(snapshot) -> Dict[str, dict]:
    """Build a risk register dict from a PortfolioSnapshot.

    Returns {risk_id: {entity_type, entity_id, title, severity, status,
    owner, description}}.
    """
    register: Dict[str, dict] = {}
    risks = getattr(snapshot, "risks", None) or []
    for r in risks:
        rid = getattr(r, "risk_id", "")
        if not rid:
            continue
        register[rid] = {
            "entity_type": getattr(r, "entity_type", ""),
            "entity_id": getattr(r, "entity_id", ""),
            "title": getattr(r, "title", ""),
            "description": getattr(r, "description", None),
            "severity": getattr(r, "severity", "medium"),
            "status": getattr(r, "status", "open"),
            "owner": getattr(r, "owner", None),
        }
    return register


# ---------------------------------------------------------------------------
# Orphaned risks
# ---------------------------------------------------------------------------

def orphaned_risks(
    register: Dict[str, dict],
    graph: DependencyGraph,
) -> List[str]:
    """Return risk ids whose entity_id does not exist as a node in the graph.

    A risk is orphaned when its target entity is not present in the
    portfolio snapshot (e.g. the entity was deleted or never created).
    """
    all_entity_ids: Set[str] = {
        n.entity_id for n in graph.nodes() if n.entity_type != "risk"
    }
    orphaned: List[str] = []
    for rid, info in sorted(register.items()):
        eid = info.get("entity_id", "")
        if eid and eid not in all_entity_ids:
            orphaned.append(rid)
    return orphaned


# ---------------------------------------------------------------------------
# Unowned risks
# ---------------------------------------------------------------------------

def unowned_risks(register: Dict[str, dict]) -> List[str]:
    """Return risk ids that have no owner field set."""
    result: List[str] = []
    for rid, info in sorted(register.items()):
        owner = info.get("owner")
        if owner is None or owner == "":
            result.append(rid)
    return result


# ---------------------------------------------------------------------------
# Risk propagation
# ---------------------------------------------------------------------------

def risk_propagation(
    graph: DependencyGraph,
    risk_id: str,
) -> List[str]:
    """Return entities affected downstream when the risk's entity fails.

    Propagation follows the reverse of dependency edges:
    if A depends on B (Edge(A, B)), and B fails, then A is affected.
    The risk's own entity is the starting point; we walk
    dependents (entities that depend on it) transitively.

    Returns a sorted list of entity ids (deterministic, stable tie-break).
    """
    # Find the entity the risk is attached to.
    risk_node = None
    for n in graph.nodes():
        if n.entity_id == risk_id and n.entity_type == "risk":
            risk_node = n
            break

    if risk_node is None:
        return []

    # Find the entity this risk is attached to via edges.
    target_entities: Set[str] = set()
    for edge in graph.edges():
        if edge.from_id == risk_id and edge.dep_type == "attached_to":
            target_entities.add(edge.to_id)

    if not target_entities:
        return []

    # BFS downstream from each target entity.
    # downstream = dependents (entities that depend on the target).
    affected: Set[str] = set()
    queue: List[str] = sorted(target_entities)

    while queue:
        current = queue.pop(0)
        if current in affected:
            continue
        affected.add(current)
        for dep in sorted(graph.dependents(current)):
            if dep not in affected:
                queue.append(dep)

    return sorted(affected)


# ---------------------------------------------------------------------------
# Critical path milestones
# ---------------------------------------------------------------------------

def critical_path_milestones(graph: DependencyGraph) -> List[str]:
    """Return milestone ids on the longest dependency chain.

    Uses longest-path in a DAG (topological order + dynamic programming).
    Only considers milestone-to-milestone dependency edges.
    Returns the milestone ids on the critical path, sorted in
    dependency order (earliest first).
    """
    milestones = graph.entity_ids("milestone")
    if not milestones:
        return []

    # Build adjacency restricted to milestone nodes.
    ms_set: Set[str] = set(milestones)
    topo = graph.topological_order()
    ms_in_topo = [nid for nid in topo if nid in ms_set]

    if not ms_in_topo:
        return []

    # Longest path DP: dist[nid] = longest chain ending at nid.
    dist: Dict[str, int] = {nid: 0 for nid in ms_in_topo}
    prev: Dict[str, Optional[str]] = {nid: None for nid in ms_in_topo}

    for nid in ms_in_topo:
        # Predecessors that are also milestones (via dep edges).
        preds = [p for p in graph.dependencies(nid) if p in ms_set]
        for p in sorted(preds):
            if dist[p] + 1 > dist[nid]:
                dist[nid] = dist[p] + 1
                prev[nid] = p

    # Find the milestone with the longest chain.
    end_id = max(ms_in_topo, key=lambda nid: (dist[nid], nid))

    # Reconstruct path.
    path: List[str] = []
    current: Optional[str] = end_id
    while current is not None:
        path.append(current)
        current = prev.get(current)
    path.reverse()

    return path