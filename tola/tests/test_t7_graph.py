"""QA T7 -- Dependency and Risk Graph tests.

Covers T7-01..T7-08 as defined in tola_testing_plan_v1_1.md.
Stdlib only: unittest.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

import unittest

from tola.graph.graph import (
    CyclePath,
    DependencyGraph,
    Edge,
    Node,
)
from tola.graph.risks import (
    critical_path_milestones,
    orphaned_risks,
    risk_propagation,
    risk_register_from_snapshot,
    unowned_risks,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_node(entity_id: str, entity_type: str) -> Node:
    return Node(entity_id=entity_id, entity_type=entity_type)


def make_edge(from_id: str, to_id: str, dep_type: str = "depends_on") -> Edge:
    return Edge(from_id=from_id, to_id=to_id, dep_type=dep_type)


def build_simple_chain() -> DependencyGraph:
    """A -> B -> C (A depends on B, B depends on C)."""
    g = DependencyGraph()
    g.add_node(make_node("A", "milestone"))
    g.add_node(make_node("B", "milestone"))
    g.add_node(make_node("C", "milestone"))
    g.add_edge(make_edge("A", "B"))
    g.add_edge(make_edge("B", "C"))
    return g


def build_cycle_graph() -> DependencyGraph:
    """A -> B -> C -> A (cycle)."""
    g = DependencyGraph()
    g.add_node(make_node("A", "milestone"))
    g.add_node(make_node("B", "milestone"))
    g.add_node(make_node("C", "milestone"))
    g.add_edge(make_edge("A", "B"))
    g.add_edge(make_edge("B", "C"))
    g.add_edge(make_edge("C", "A"))
    return g


def build_risk_graph() -> DependencyGraph:
    """Goal G1 -> Milestone M1 -> Task T1.
    Risk R1 attached to M1.
    """
    g = DependencyGraph()
    g.add_node(make_node("G1", "goal"))
    g.add_node(make_node("M1", "milestone"))
    g.add_node(make_node("T1", "task"))
    g.add_edge(make_edge("M1", "G1"))  # M1 depends on G1
    g.add_edge(make_edge("T1", "M1"))  # T1 depends on M1
    g.add_node(make_node("R1", "risk"))
    g.add_edge(make_edge("R1", "M1", "attached_to"))
    return g


def make_snapshot_with(risks_data: list) -> object:
    """Create a minimal mock PortfolioSnapshot with risks."""
    snap = object.__new__(type("PortfolioSnapshot", (), {}))
    snap.risks = risks_data
    snap.active_tasks = []
    snap.milestones = []
    return snap


# ---------------------------------------------------------------------------
# T7-01: Cycle detection raises/flags
# ---------------------------------------------------------------------------

class TestT7_01_CycleDetection(unittest.TestCase):
    def test_cycle_detected_returns_cycle_paths(self):
        g = build_cycle_graph()
        cycles = g.detect_cycles()
        self.assertTrue(len(cycles) >= 1)

    def test_cycle_detected_has_correct_nodes(self):
        g = build_cycle_graph()
        cycles = g.detect_cycles()
        all_nodes: set = set()
        for c in cycles:
            all_nodes.update(c.nodes)
        self.assertIn("A", all_nodes)
        self.assertIn("B", all_nodes)
        self.assertIn("C", all_nodes)

    def test_has_cycle_returns_true_for_cyclic_graph(self):
        g = build_cycle_graph()
        self.assertTrue(g.has_cycle())

    def test_has_cycle_returns_false_for_acyclic_graph(self):
        g = build_simple_chain()
        self.assertFalse(g.has_cycle())

    def test_topological_order_raises_on_cycle(self):
        g = build_cycle_graph()
        with self.assertRaises(ValueError):
            g.topological_order()

    def test_cycle_path_is_tuple_of_strings(self):
        g = build_cycle_graph()
        cycles = g.detect_cycles()
        for c in cycles:
            self.assertIsInstance(c.nodes, tuple)
            for n in c.nodes:
                self.assertIsInstance(n, str)


# ---------------------------------------------------------------------------
# T7-02: Topological order deterministic
# ---------------------------------------------------------------------------

class TestT7_02_TopologicalOrderDeterministic(unittest.TestCase):
    def test_topological_order_returns_all_nodes(self):
        g = build_simple_chain()
        order = g.topological_order()
        self.assertEqual(set(order), {"A", "B", "C"})

    def test_topological_order_respects_dependencies(self):
        """C must come before B, B before A."""
        g = build_simple_chain()
        order = g.topological_order()
        idx = {nid: i for i, nid in enumerate(order)}
        self.assertLess(idx["C"], idx["B"])
        self.assertLess(idx["B"], idx["A"])

    def test_topological_order_is_deterministic_across_runs(self):
        """Same graph produces same order every time."""
        g = build_simple_chain()
        orders = [g.topological_order() for _ in range(5)]
        self.assertTrue(all(o == orders[0] for o in orders))

    def test_topological_order_stable_tie_break_by_id(self):
        """When multiple nodes have zero in-degree, smallest id comes first."""
        g = DependencyGraph()
        g.add_node(make_node("Z", "milestone"))
        g.add_node(make_node("A", "milestone"))
        g.add_node(make_node("M", "milestone"))
        # No edges -- all zero in-degree, sorted by id.
        order = g.topological_order()
        self.assertEqual(order, ["A", "M", "Z"])

    def test_topological_order_empty_graph(self):
        g = DependencyGraph()
        self.assertEqual(g.topological_order(), [])


# ---------------------------------------------------------------------------
# T7-03: Risk propagation follows edges downstream only
# ---------------------------------------------------------------------------

class TestT7_03_RiskPropagation(unittest.TestCase):
    def test_propagation_follows_downstream_only(self):
        """When M1 fails, T1 (which depends on M1) is affected.
        G1 (which M1 depends on) is NOT affected."""
        g = build_risk_graph()
        affected = risk_propagation(g, "R1")
        # R1 -> M1 -> T1.  G1 is upstream of M1, not downstream.
        self.assertIn("M1", affected)
        self.assertIn("T1", affected)
        self.assertNotIn("G1", affected)

    def test_propagation_does_not_include_risk_itself(self):
        """The risk node is not in the affected set; only the entity it
        attaches to and downstream entities are."""
        g = build_risk_graph()
        affected = risk_propagation(g, "R1")
        self.assertNotIn("R1", affected)

    def test_propagation_empty_for_unknown_risk(self):
        g = build_risk_graph()
        self.assertEqual(risk_propagation(g, "NONEXISTENT"), [])

    def test_propagation_empty_when_risk_has_no_attachment(self):
        g = DependencyGraph()
        g.add_node(make_node("R1", "risk"))
        self.assertEqual(risk_propagation(g, "R1"), [])

    def test_propagation_transitive(self):
        """A depends on B depends on C depends on D.
        Risk on B affects A (which depends on B), not C or D.
        B itself is the entity the risk attaches to and is also affected."""
        g = DependencyGraph()
        for nid in ("A", "B", "C", "D"):
            g.add_node(make_node(nid, "milestone"))
        g.add_edge(make_edge("A", "B"))  # A depends on B
        g.add_edge(make_edge("B", "C"))  # B depends on C
        g.add_edge(make_edge("C", "D"))  # C depends on D
        g.add_node(make_node("R1", "risk"))
        g.add_edge(make_edge("R1", "B", "attached_to"))
        affected = risk_propagation(g, "R1")
        self.assertIn("A", affected)
        self.assertIn("B", affected)
        self.assertNotIn("C", affected)
        self.assertNotIn("D", affected)


# ---------------------------------------------------------------------------
# T7-04: Orphaned risks detected
# ---------------------------------------------------------------------------

class TestT7_04_OrphanedRisks(unittest.TestCase):
    def test_orphaned_risk_detected(self):
        """Risk pointing to a missing entity_id is orphaned."""
        g = DependencyGraph()
        g.add_node(make_node("M1", "milestone"))
        register = {
            "R1": {"entity_id": "M1", "title": "ok risk"},
            "R2": {"entity_id": "MISSING", "title": "orphan"},
        }
        orphaned = orphaned_risks(register, g)
        self.assertIn("R2", orphaned)
        self.assertNotIn("R1", orphaned)

    def test_no_orphaned_risks_when_all_attached(self):
        g = build_risk_graph()
        register = {}
        for n in g.nodes():
            if n.entity_type == "risk":
                # Find the entity this risk is attached to.
                eid = n.entity_id
                for edge in g.edges():
                    if edge.from_id == n.entity_id and edge.dep_type == "attached_to":
                        eid = edge.to_id
                        break
                register[n.entity_id] = {"entity_id": eid}
        self.assertEqual(orphaned_risks(register, g), [])

    def test_orphaned_risks_returns_sorted_list(self):
        g = DependencyGraph()
        g.add_node(make_node("M1", "milestone"))
        register = {
            "R3": {"entity_id": "MISSING3", "title": ""},
            "R1": {"entity_id": "MISSING1", "title": ""},
            "R2": {"entity_id": "M1", "title": ""},
        }
        orphaned = orphaned_risks(register, g)
        self.assertEqual(orphaned, ["R1", "R3"])


# ---------------------------------------------------------------------------
# T7-05: Unowned risks detected
# ---------------------------------------------------------------------------

class TestT7_05_UnownedRisks(unittest.TestCase):
    def test_unowned_risks_detected(self):
        register = {
            "R1": {"owner": "alice", "title": "owned"},
            "R2": {"owner": None, "title": "unowned"},
            "R3": {"owner": "", "title": "also unowned"},
        }
        result = unowned_risks(register)
        self.assertIn("R2", result)
        self.assertIn("R3", result)
        self.assertNotIn("R1", result)

    def test_unowned_risks_sorted(self):
        register = {
            "R5": {"owner": None},
            "R2": {"owner": None},
            "R3": {"owner": "bob"},
        }
        result = unowned_risks(register)
        self.assertEqual(result, ["R2", "R5"])

    def test_no_unowned_when_all_have_owners(self):
        register = {
            "R1": {"owner": "alice"},
            "R2": {"owner": "bob"},
        }
        self.assertEqual(unowned_risks(register), [])


# ---------------------------------------------------------------------------
# T7-06: Critical path milestones correct on fixture chain
# ---------------------------------------------------------------------------

class TestT7_06_CriticalPathMilestones(unittest.TestCase):
    def test_critical_path_single_chain(self):
        """A depends on B depends on C.  Critical path: C, B, A."""
        g = build_simple_chain()
        path = critical_path_milestones(g)
        self.assertEqual(path, ["C", "B", "A"])

    def test_critical_path_longest_wins(self):
        """A->B->C (len 3) vs D->E (len 2).  Critical path is C,B,A."""
        g = DependencyGraph()
        for nid in ("A", "B", "C", "D", "E"):
            g.add_node(make_node(nid, "milestone"))
        g.add_edge(make_edge("A", "B"))
        g.add_edge(make_edge("B", "C"))
        g.add_edge(make_edge("D", "E"))
        path = critical_path_milestones(g)
        self.assertEqual(path, ["C", "B", "A"])

    def test_critical_path_empty_graph(self):
        g = DependencyGraph()
        self.assertEqual(critical_path_milestones(g), [])

    def test_critical_path_no_milestones(self):
        g = DependencyGraph()
        g.add_node(make_node("T1", "task"))
        g.add_node(make_node("T2", "task"))
        g.add_edge(make_edge("T1", "T2"))
        self.assertEqual(critical_path_milestones(g), [])

    def test_critical_path_deterministic(self):
        """Same graph produces same critical path every time."""
        g = build_simple_chain()
        paths = [critical_path_milestones(g) for _ in range(5)]
        self.assertTrue(all(p == paths[0] for p in paths))


# ---------------------------------------------------------------------------
# T7-07: Risk register from snapshot
# ---------------------------------------------------------------------------

class TestT7_07_RiskRegisterFromSnapshot(unittest.TestCase):
    def test_register_extracts_risks(self):
        from tola.portfolio.contracts import Risk
        from datetime import datetime

        r = Risk(
            risk_id="R1",
            entity_type="milestone",
            entity_id="M1",
            title="Delay risk",
            severity="high",
            status="open",
        )
        snap = make_snapshot_with([r])
        register = risk_register_from_snapshot(snap)
        self.assertIn("R1", register)
        self.assertEqual(register["R1"]["entity_id"], "M1")
        self.assertEqual(register["R1"]["severity"], "high")

    def test_register_empty_for_no_risks(self):
        snap = make_snapshot_with([])
        register = risk_register_from_snapshot(snap)
        self.assertEqual(register, {})

    def test_register_deterministic(self):
        from tola.portfolio.contracts import Risk
        from datetime import datetime

        r1 = Risk(
            risk_id="R1",
            entity_type="milestone",
            entity_id="M1",
            title="Risk 1",
        )
        r2 = Risk(
            risk_id="R2",
            entity_type="task",
            entity_id="T1",
            title="Risk 2",
        )
        snap = make_snapshot_with([r1, r2])
        register = risk_register_from_snapshot(snap)
        keys = list(register.keys())
        self.assertEqual(keys, ["R1", "R2"])


# ---------------------------------------------------------------------------
# T7-08: from_plans and from_snapshot builders
# ---------------------------------------------------------------------------

class TestT7_08_Builders(unittest.TestCase):
    def test_from_plans_builds_graph(self):
        plans = [
            {
                "milestones": [
                    {"milestone_id": "MS-1", "name": "Design"},
                    {"milestone_id": "MS-2", "name": "Build"},
                ],
                "tasks": [
                    {
                        "task_id": "T1",
                        "parent_task_id": None,
                    },
                    {
                        "task_id": "T2",
                        "parent_task_id": "T1",
                    },
                ],
                "dependencies": [
                    {"from_id": "MS-2", "to_id": "MS-1"},
                ],
                "risks": [
                    {
                        "risk_id": "R1",
                        "entity_type": "milestone",
                        "entity_id": "MS-1",
                    }
                ],
            }
        ]
        g = DependencyGraph.from_plans(plans)
        # MS-1 -> MS-2 (MS-2 depends on MS-1).
        # T1 has no parent.  T2 depends on T1.
        # R1 attached to MS-1.
        order = g.topological_order()
        self.assertIn("MS-1", order)
        self.assertIn("MS-2", order)
        self.assertIn("T1", order)
        self.assertIn("T2", order)
        self.assertIn("R1", order)
        # MS-1 must come before MS-2 (MS-2 depends on MS-1).
        self.assertLess(order.index("MS-1"), order.index("MS-2"))
        # T1 must come before T2 (T2 depends on T1).
        self.assertLess(order.index("T1"), order.index("T2"))

    def test_from_snapshot_builds_graph(self):
        from tola.portfolio.contracts import Risk, Milestone, Task
        from datetime import datetime

        ms = Milestone(
            milestone_id="MS-1",
            goal_id="G1",
            title="Design",
        )
        t = Task(
            task_id="T1",
            idempotency_key="k1",
            title="Write specs",
            parent_task_id=None,
        )
        r = Risk(
            risk_id="R1",
            entity_type="milestone",
            entity_id="MS-1",
            title="Scope creep",
        )

        snap = make_snapshot_with([r])
        snap.milestones = [ms]
        snap.active_tasks = [t]

        g = DependencyGraph.from_snapshot(snap)
        order = g.topological_order()
        self.assertIn("MS-1", order)
        self.assertIn("T1", order)
        self.assertIn("R1", order)

    def test_from_plans_detects_cycle_in_plan(self):
        plans = [
            {
                "milestones": [
                    {"milestone_id": "A", "name": "A"},
                    {"milestone_id": "B", "name": "B"},
                ],
                "dependencies": [
                    {"from_id": "A", "to_id": "B"},
                    {"from_id": "B", "to_id": "A"},
                ],
            }
        ]
        g = DependencyGraph.from_plans(plans)
        self.assertTrue(g.has_cycle())
        with self.assertRaises(ValueError):
            g.topological_order()

    def test_from_plans_empty_list(self):
        g = DependencyGraph.from_plans([])
        self.assertEqual(g.topological_order(), [])


# ---------------------------------------------------------------------------
# Suite
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()