"""DependencyGraph: pure data structure for portfolio entity dependencies.

Stdlib only.  Deterministic with stable tie-break by id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Node:
    """A portfolio entity in the dependency graph."""

    entity_id: str
    entity_type: str  # milestone, task, risk, goal, project, external


# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Edge:
    """Directed dependency: from_node -> to_node (from depends on to)."""

    from_id: str
    to_id: str
    dep_type: str = "depends_on"


# ---------------------------------------------------------------------------
# Cycle
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CyclePath:
    """A directed cycle as an ordered list of entity ids."""

    nodes: Tuple[str, ...]


# ---------------------------------------------------------------------------
# DependencyGraph
# ---------------------------------------------------------------------------

class DependencyGraph:
    """Directed graph over portfolio entities.

    Nodes carry entity type + id.  Edges are dependencies.
    All operations are deterministic with stable tie-break by id.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []
        # Adjacency lists for dependency edges only (excl attached_to).
        self._dep_adj: Dict[str, List[str]] = {}
        self._dep_rev_adj: Dict[str, List[str]] = {}
        # Full adjacency (all edge types).
        self._all_adj: Dict[str, List[str]] = {}
        self._all_rev_adj: Dict[str, List[str]] = {}

    # -- Builders ----------------------------------------------------------

    def add_node(self, node: Node) -> None:
        if node.entity_id not in self._nodes:
            self._nodes[node.entity_id] = node
            self._dep_adj.setdefault(node.entity_id, [])
            self._dep_rev_adj.setdefault(node.entity_id, [])
            self._all_adj.setdefault(node.entity_id, [])
            self._all_rev_adj.setdefault(node.entity_id, [])

    def add_edge(self, edge: Edge) -> None:
        self.add_node(Node(edge.from_id, "unknown"))
        self.add_node(Node(edge.to_id, "unknown"))
        self._edges.append(edge)
        self._all_adj.setdefault(edge.from_id, [])
        if edge.to_id not in self._all_adj[edge.from_id]:
            self._all_adj[edge.from_id].append(edge.to_id)
        self._all_rev_adj.setdefault(edge.to_id, [])
        if edge.from_id not in self._all_rev_adj[edge.to_id]:
            self._all_rev_adj[edge.to_id].append(edge.from_id)
        # Dependency edges only go into dep_adj / dep_rev_adj.
        if edge.dep_type != "attached_to":
            if edge.to_id not in self._dep_adj[edge.from_id]:
                self._dep_adj[edge.from_id].append(edge.to_id)
            if edge.from_id not in self._dep_rev_adj[edge.to_id]:
                self._dep_rev_adj[edge.to_id].append(edge.from_id)

    @classmethod
    def from_plans(
        cls,
        plans: List[Dict[str, object]],
    ) -> "DependencyGraph":
        """Build from decomposition plans (T6 output).

        Each plan dict may contain:
          - milestones: list of milestone dicts with milestone_id
          - tasks: list of task dicts with task_id, parent_task_id
          - dependencies: list of {from_id, to_id}
          - risks: list of risk dicts with risk_id, entity_type, entity_id
        """
        g = cls()
        for plan in plans:
            # Milestones
            for ms in plan.get("milestones", []) or []:
                ms_id = ms.get("milestone_id", "")
                if ms_id:
                    g.add_node(Node(ms_id, "milestone"))
            # Tasks
            for t in plan.get("tasks", []) or []:
                t_id = t.get("task_id", "")
                if t_id:
                    g.add_node(Node(t_id, "task"))
                    parent = t.get("parent_task_id")
                    if parent:
                        g.add_edge(Edge(t_id, parent, "depends_on"))
            # Explicit dependencies
            for dep in plan.get("dependencies", []) or []:
                if isinstance(dep, dict):
                    frm = dep.get("from_id", dep.get("from", ""))
                    to = dep.get("to_id", dep.get("to", ""))
                    if frm and to:
                        g.add_edge(
                            Edge(frm, to, dep.get("dep_type", "depends_on"))
                        )
            # Risks
            for r in plan.get("risks", []) or []:
                r_id = r.get("risk_id", "")
                if r_id:
                    g.add_node(Node(r_id, "risk"))
                    eid = r.get("entity_id", "")
                    if eid:
                        g.add_edge(Edge(r_id, eid, "attached_to"))
        return g

    @classmethod
    def from_snapshot(cls, snapshot: object) -> "DependencyGraph":
        """Build from a PortfolioSnapshot.

        Extracts milestones, tasks, risks and their inter-relations.
        """
        g = cls()

        # Milestones
        milestones = getattr(snapshot, "milestones", None) or []
        for ms in milestones:
            ms_id = getattr(ms, "milestone_id", "")
            if ms_id:
                g.add_node(Node(ms_id, "milestone"))

        # Tasks
        tasks = getattr(snapshot, "active_tasks", None) or []
        for t in tasks:
            t_id = getattr(t, "task_id", "")
            if t_id:
                g.add_node(Node(t_id, "task"))
                parent = getattr(t, "parent_task_id", None)
                if parent:
                    g.add_edge(Edge(t_id, parent, "depends_on"))

        # Risks
        risks = getattr(snapshot, "risks", None) or []
        for r in risks:
            r_id = getattr(r, "risk_id", "")
            if r_id:
                g.add_node(Node(r_id, "risk"))
                eid = getattr(r, "entity_id", "")
                if eid:
                    g.add_edge(Edge(r_id, eid, "attached_to"))

        return g

    # -- Queries ----------------------------------------------------------

    def nodes(self) -> List[Node]:
        """Return all nodes sorted deterministically by id."""
        return [self._nodes[k] for k in sorted(self._nodes.keys())]

    def edges(self) -> List[Edge]:
        """Return all edges sorted deterministically."""
        return list(self._edges)

    def dependents(self, node_id: str) -> List[str]:
        """Return ids of entities that depend on node_id (reverse dep edges).

        If Edge(A, B, 'depends_on') means A depends on B,
        then A is a dependent of B.
        """
        return list(self._dep_rev_adj.get(node_id, []))

    def dependencies(self, node_id: str) -> List[str]:
        """Return ids of entities node_id depends on (forward dep edges)."""
        return list(self._dep_adj.get(node_id, []))

    def topological_order(self) -> List[str]:
        """Return a deterministic topological order of all node ids.

        Uses Kahn's algorithm with a sorted queue for stable tie-break.
        Only follows dependency edges (dep_type != 'attached_to').
        Raises ValueError if a cycle is detected.
        """
        in_degree: Dict[str, int] = {nid: 0 for nid in self._nodes}
        for edge in self._edges:
            if edge.dep_type == "attached_to":
                continue
            if edge.from_id in in_degree and edge.to_id in in_degree:
                in_degree[edge.from_id] += 1

        queue: List[str] = sorted(
            [nid for nid, deg in in_degree.items() if deg == 0]
        )
        result: List[str] = []

        while queue:
            current = queue.pop(0)
            result.append(current)
            for dep in sorted(self._dep_rev_adj.get(current, [])):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)
            queue.sort()

        if len(result) != len(self._nodes):
            remaining = [nid for nid in self._nodes if nid not in result]
            raise ValueError(
                f"Cycle detected involving nodes: {remaining}"
            )

        return result

    def detect_cycles(self) -> List[CyclePath]:
        """Return all elementary cycles found in the graph.

        Only follows dependency edges (dep_type != 'attached_to').
        Results are deterministic (sorted by first node in each cycle).
        """
        cycles: List[CyclePath] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node_id: str) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for succ in sorted(self._dep_adj.get(node_id, [])):
                if succ not in visited:
                    dfs(succ)
                elif succ in rec_stack:
                    idx = path.index(succ)
                    cycle_nodes = tuple(path[idx:])
                    cycles.append(CyclePath(cycle_nodes))

            path.pop()
            rec_stack.discard(node_id)

        for nid in sorted(self._nodes.keys()):
            if nid not in visited:
                dfs(nid)

        # Deduplicate cycles by normalising rotation.
        unique: List[CyclePath] = []
        seen_set: Set[Tuple[str, ...]] = set()
        for c in cycles:
            nodes = c.nodes
            min_idx = nodes.index(min(nodes))
            normalised = tuple(nodes[min_idx:] + nodes[:min_idx])
            if normalised not in seen_set:
                seen_set.add(normalised)
                unique.append(CyclePath(normalised))

        return unique

    def has_cycle(self) -> bool:
        """Quick check whether the graph contains any cycle."""
        return len(self.detect_cycles()) > 0

    def entity_ids(self, entity_type: str) -> List[str]:
        """Return all node ids of a given type, sorted."""
        return sorted(
            n.entity_id
            for n in self._nodes.values()
            if n.entity_type == entity_type
        )